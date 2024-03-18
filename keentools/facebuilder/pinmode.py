# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2019  KeenTools

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# ##### END GPL LICENSE BLOCK #####

from typing import Any, Optional, Callable, Tuple, Set
from uuid import uuid4
import numpy as np
from copy import deepcopy

import bpy
from bpy.props import IntProperty, StringProperty
from bpy.types import Operator, Area

from ..utils.kt_logging import KTLogger
from ..addon_config import (Config,
                            fb_settings,
                            get_operator,
                            ErrorType,
                            show_user_preferences,
                            supported_gpu_backend)
from ..facebuilder_config import FBConfig
from ..utils.bpy_common import (operator_with_context,
                                bpy_view_camera,
                                bpy_render_frame)
from ..utils.coords import (update_head_mesh_non_neutral,
                            get_image_space_coord,
                            nearest_point,
                            point_is_in_area,
                            point_is_in_service_region,
                            get_area_region,
                            get_area_region_3d,
                            get_camera_border)
from .utils.manipulate import push_head_in_undo_history
from .fbloader import FBLoader
from ..utils.focal_length import update_camera_focal
from ..utils.html import split_long_string
from ..utils.localview import (exit_area_localview,
                               check_area_active_problem,
                               check_context_localview)
from ..utils.manipulate import switch_to_camera, center_viewports_on_object
from .ui_strings import buttons
from ..preferences.hotkeys import (facebuilder_keymaps_register,
                                   facebuilder_keymaps_unregister)
from .prechecks import common_fb_checks


_log = KTLogger(__name__)


_undo_handler: Optional[Callable] = None


def fb_undo_handler(scene: Any) -> None:
    _log.green('fb_undo_handler start')
    try:
        settings = fb_settings()
        if not settings.pinmode or settings.current_headnum < 0:
            unregister_fb_undo_handler()
            _log.red(f'fb_undo_handler not in pinmode end >>>')
            return
        head = settings.get_head(settings.current_headnum)
        if not head:
            unregister_fb_undo_handler()
            _log.red(f'fb_undo_handler not in pinmode end >>>')
            return
        head.need_update = True
    except Exception as err:
        _log.error(f'fb_undo_handler:\n{str(err)}')
        unregister_fb_undo_handler()
    _log.output('fb_undo_handler end >>>')


def unregister_fb_undo_handler() -> None:
    _log.yellow('unregister_fb_undo_handler start')
    global _undo_handler
    if _undo_handler is not None:
        if _undo_handler in bpy.app.handlers.undo_post:
            bpy.app.handlers.undo_post.remove(_undo_handler)
    _undo_handler = None
    _log.output('unregister_fb_undo_handler end >>>')


def register_fb_undo_handler() -> None:
    _log.yellow('register_fb_undo_handler start')
    global _undo_handler
    unregister_fb_undo_handler()
    _undo_handler = fb_undo_handler
    bpy.app.handlers.undo_post.append(_undo_handler)
    _log.output('register_fb_undo_handler end >>>')


class FB_OT_PinMode(Operator):
    bl_idname = FBConfig.fb_pinmode_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'INTERNAL'}

    headnum: IntProperty(default=0)
    camnum: IntProperty(default=0)

    pinmode_id: StringProperty(default='')

    _shift_pressed: bool = False
    _prev_camera_state: Tuple[float, Tuple[float, float]] = ()
    _prev_area_state: Tuple[int, int, int, int] = ()

    @classmethod
    def _check_camera_state_changed(cls, rv3d: Any) -> bool:
        if not rv3d:
            return False
        camera_state = (rv3d.view_camera_zoom, rv3d.view_camera_offset)
        if camera_state != cls._prev_camera_state:
            cls._prev_camera_state = camera_state
            return True
        return False

    @classmethod
    def _check_area_state_changed(cls, area: Area) -> bool:
        if not area:
            return False
        area_state = (area.x, area.y, area.width, area.height)
        if area_state != cls._prev_area_state:
            cls._prev_area_state = area_state
            return True
        return False

    @classmethod
    def _set_shift_pressed(cls, val: bool) -> None:
        cls._shift_pressed = val

    @classmethod
    def _is_shift_pressed(cls) -> bool:
        return cls._shift_pressed

    def _fix_heads_with_warning(self) -> None:
        settings = fb_settings()
        heads_deleted, cams_deleted = settings.fix_heads()
        if heads_deleted > 0 or cams_deleted > 0:
            _log.warning('HEADS AND CAMERAS FIXED')
        if heads_deleted == 0:
            warn = get_operator(Config.kt_warning_idname)
            warn('INVOKE_DEFAULT', msg=ErrorType.SceneDamaged)

    def _change_wireframe_visibility(self, *, toggle: bool=True,
                                     value: bool=True) -> None:
        vp = FBLoader.viewport()
        flag = not vp.wireframer().is_visible() if toggle else value
        vp.set_visible(flag)
        if flag:
            vp.revert_default_screen_message(unregister=False)
        else:
            default_txt = deepcopy(vp.texter().get_default_text())
            default_txt[0]['text'] = 'Press TAB to show wireframe'
            default_txt[0]['color'] = (1., 0., 1., 0.85)
            vp.message_to_screen(default_txt)

    def _delete_found_pin(self, nearest: int, area: Area) -> Set:
        _log.yellow('_delete_found_pin call')
        settings = fb_settings()
        headnum = settings.current_headnum
        camnum = settings.current_camnum
        head = settings.get_head(headnum)
        kid = settings.get_keyframe(headnum, camnum)

        fb = FBLoader.get_builder()
        fb.remove_pin(kid, nearest)
        del FBLoader.viewport().pins().arr()[nearest]
        _log.output('FB PIN REMOVED {}'.format(nearest))

        if not FBLoader.solve(headnum, camnum):
            _log.error('FB DELETE PIN PROBLEM')
            unregister_fb_undo_handler()

            facebuilder_keymaps_unregister()
            return {'FINISHED'}

        update_head_mesh_non_neutral(fb, head)
        FBLoader.update_camera_pins_count(headnum, camnum)

        FBLoader.update_all_camera_positions(headnum)
        # Save result
        FBLoader.save_fb_serial_and_image_pathes(headnum)
        push_head_in_undo_history(head, 'Pin Remove')

        FBLoader.load_pins_into_viewport(headnum, camnum)
        vp = FBLoader.viewport()
        _log.output(f'before FBLoader.update_fb_viewport_shaders '
                    f'{vp.wireframer().get_statistics()}')
        FBLoader.update_fb_viewport_shaders(area=area,
                                            headnum=headnum, camnum=camnum,
                                            wireframe=True,
                                            pins_and_residuals=True)

        _log.output('_delete_found_pin end >>>')

        return {'RUNNING_MODAL'}

    def _undo_detected(self, area: Area) -> None:
        _log.magenta(f'{self.__class__.__name__} _undo_detected')
        settings = fb_settings()
        if not settings or not settings.pinmode:
            unregister_fb_undo_handler()
            _log.red(f'_undo_detected not in pinmode end >>>')
            return

        headnum = settings.current_headnum
        camnum = settings.current_camnum
        head = settings.get_head(headnum)
        if not head:
            unregister_fb_undo_handler()
            _log.red(f'_undo_detected no head end >>>')
            return

        head.need_update = False
        FBLoader.load_model(headnum)
        FBLoader.place_camera(headnum, camnum)
        FBLoader.load_pins_into_viewport(headnum, camnum)
        FBLoader.update_fb_viewport_shaders(area=area,
                                            wireframe=True,
                                            pins_and_residuals=True,
                                            camera_pos=True,
                                            tag_redraw=True)
        _log.output(f'{self.__class__.__name__} _undo_detected end >>>')

    def _on_right_mouse_press(self, area: Area,
                              mouse_x: float, mouse_y: float) -> Set:
        vp = FBLoader.viewport()
        vp.update_view_relative_pixel_size(area)

        x, y = get_image_space_coord(mouse_x, mouse_y, area)

        nearest, dist2 = nearest_point(x, y, vp.pins().arr())
        if nearest >= 0 and dist2 < FBLoader.viewport().tolerance_dist2():
            return self._delete_found_pin(nearest, area)

        FBLoader.viewport().create_batch_2d(area)
        return {'RUNNING_MODAL'}

    def _on_left_mouse_press(self, area: Area,
                             mouse_x: float, mouse_y: float) -> Set:
        FBLoader.viewport().update_view_relative_pixel_size(area)

        if not point_is_in_area(area, mouse_x, mouse_y):
            return {'PASS_THROUGH'}

        if not point_is_in_service_region(area, mouse_x, mouse_y):
            settings = fb_settings()
            op = get_operator(FBConfig.fb_movepin_idname)
            op('INVOKE_DEFAULT', pinx=mouse_x, piny=mouse_y,
               headnum=settings.current_headnum,
               camnum=settings.current_camnum)
            return {'PASS_THROUGH'}

        return {'PASS_THROUGH'}

    def _check_keyframes(self, fb: Any, head: Any) -> bool:
        for cam in head.cameras:
            if not fb.is_key_at(cam.get_keyframe()):
                return False
        return True

    def execute(self, context: Any) -> Set:  # Testing purpose only
        _log.green('PinMode execute call')
        FBLoader.update_fb_viewport_shaders(wireframe_colors=True,
                                            wireframe_image=True,
                                            camera_pos=True,
                                            wireframe=True)
        return {'FINISHED'}

    def invoke(self, context: Any, event: Any) -> Set:
        _log.green(f'{self.__class__.__name__} invoke')
        settings = fb_settings()

        _log.output(f'current_headnum: {settings.current_headnum} '
                    f'current_camnum: {settings.current_camnum}')

        check_status = common_fb_checks(object_mode=True,
                                        is_calculating=True,
                                        stop_another_pinmode=True,
                                        fix_facebuilders=True,
                                        head_and_camera=True,
                                        headnum=self.headnum,
                                        camnum=self.camnum)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            _log.red(f'{self.__class__.__name__} 1 cancelled >>>')
            return {'CANCELLED'}

        _log.output('common checks passed')

        if not supported_gpu_backend():
            warn = get_operator(Config.kt_warning_idname)
            warn('INVOKE_DEFAULT', msg=ErrorType.UnsupportedGPUBackend)
            _log.red(f'{self.__class__.__name__} 2 cancelled >>>')
            return {'CANCELLED'}

        head = settings.get_head(self.headnum)
        headobj = head.headobj
        first_start = True

        vp = FBLoader.viewport()
        if not vp.load_all_shaders() and Config.strict_shader_check:
            _log.red(f'{self.__class__.__name__} 3 cancelled >>>')
            return {'CANCELLED'}

        # Stopped shaders mean that we need to restart pinmode
        if not vp.wireframer().is_working():
            settings.pinmode = False

        if settings.wrong_pinmode_id():
            settings.pinmode = False

        # We have to fix last operation if we are in Pinmode
        if settings.pinmode and \
                settings.current_headnum >= 0 and settings.current_camnum >= 0:

            old_head = settings.get_head(settings.current_headnum)
            old_camera = old_head.get_camera(settings.current_camnum)
            old_camera.reset_tone_mapping()

            FBLoader.save_pinmode_state(settings.current_headnum)
            _log.output(f'FB PINMODE FORCE FINISH: H{settings.current_headnum} '
                        f'C{settings.current_camnum}')
            first_start = False
        else:
            FBLoader.update_cameras_from_old_version(self.headnum)

        area = context.area if first_start else FBLoader.get_work_area()
        if not area:
            _log.error(f'{self.__class__.__name__} area error 4 cancelled >>>')
            return {'CANCELLED'}

        settings.current_headnum = self.headnum
        settings.current_camnum = self.camnum
        settings.pinmode = True

        camera = head.get_camera(settings.current_camnum)
        camera.update_scene_frame_size()
        camera.update_background_image_scale()
        kid = camera.get_keyframe()

        camera.apply_tone_mapping()

        if first_start:
            center_viewports_on_object(headobj)
        switch_to_camera(area, camera.camobj)
        camera.show_background_image()

        _log.output(f'FB PINMODE START H{settings.current_headnum} '
                    f'C{settings.current_camnum}')
        # Start working with current model
        try:
            if not FBLoader.load_model_throw_exception(settings.current_headnum):
                raise Exception('Cannot load the model data from '
                                'the serialised string. Perhaps your file '
                                'or the scene data got corrupted.')
        except Exception as err:
            _log.red('FB MODEL CANNOT BE LOADED IN PINMODE')

            FBLoader.out_pinmode_without_save(self.headnum)
            exit_area_localview(area)

            _log.error(f'DESERIALIZE load_model_throw_exception: \n{str(err)}')
            error_message = '\n'.join(split_long_string(str(err), limit=64))
            warn = get_operator(Config.kt_warning_idname)
            warn('INVOKE_DEFAULT', msg=ErrorType.CustomMessage,
                 msg_content=error_message)
            _log.red(f'{self.__class__.__name__} cannot load 5 cancelled >>>')
            return {'CANCELLED'}

        _log.output('model loaded')

        if not FBLoader.check_mesh(headobj):
            fb = FBLoader.get_builder()
            _log.error(f'FB MESH IS CORRUPTED '
                       f'{len(headobj.data.vertices)} != '
                       f'{len(fb.applied_args_vertices())}')

            FBLoader.out_pinmode_without_save(self.headnum)
            exit_area_localview(area)

            warn = get_operator(Config.kt_warning_idname)
            warn('INVOKE_DEFAULT', msg=ErrorType.MeshCorrupted)
            _log.red(f'{self.__class__.__name__} check mesh 6 cancelled >>>')
            return {'CANCELLED'}

        fb = FBLoader.get_builder()
        fb.set_use_emotions(head.should_use_emotions())

        if not self._check_keyframes(fb, head):
            _log.output('FB PINMODE NO KEYFRAME')
            for cam in head.cameras:
                kid = cam.get_keyframe()
                _log.output(f'FB UPDATE KEYFRAME: {kid}')
                if not fb.is_key_at(kid):
                    _log.error(f'\nFB UNKNOWN KEYFRAME: {kid}\n')
                    fb.set_keyframe(kid, np.eye(4))
        try:
            FBLoader.place_camera(settings.current_headnum,
                                  settings.current_camnum)
        except Exception:
            _log.output('FB UPDATE KEYFRAME PROBLEM')
            _log.red(f'{self.__class__.__name__} keyframe error 7 cancelled >>>')
            return {'CANCELLED'}

        update_head_mesh_non_neutral(fb, head)
        _log.output('before update_camera_focal')
        update_camera_focal(camera, fb)
        _log.output('after update_camera_focal')

        self._check_camera_state_changed(get_area_region_3d(area))
        self._check_area_state_changed(area)

        FBLoader.update_fb_viewport_shaders(adaptive_opacity=True,
                                            wireframe_colors=True,
                                            wireframe_image=True,
                                            camera_pos=True,
                                            load_pins=True,
                                            wireframe=True)
        if first_start:
            settings.viewport_state.hide_ui_elements(area)

            _log.output('START FB SHADERS')
            self._change_wireframe_visibility(toggle=False, value=True)
            vp.create_batch_2d(area)
            vp.register_handlers(area=area)

            context.window_manager.modal_handler_add(self)

            _log.output('START FB SHADER STOPPER')
            self.pinmode_id = str(uuid4())
            settings.pinmode_id = self.pinmode_id
            FBLoader.start_shader_timer(self.pinmode_id)
            _log.output(f'pinmode_id: {self.pinmode_id}')
        else:
            _log.output('FB SHADER UPDATE ONLY')

        if not check_area_active_problem(area):
            assert area.spaces.active.region_3d.view_perspective == 'CAMERA'
            _log.output('bpy.ops.view3d.view_center_camera call')
            operator_with_context(bpy.ops.view3d.view_center_camera,
                {'area': area, 'region': get_area_region(area)})

        vp.update_surface_points(FBLoader.get_builder(), headobj, kid)

        if first_start:
            if len(head.cameras) == 1 and not camera.has_pins():
                op = get_operator(FBConfig.fb_pickmode_starter_idname)
                op('INVOKE_DEFAULT',
                   headnum=settings.current_headnum,
                   camnum=settings.current_camnum,
                   auto_detect_single=True)

            push_head_in_undo_history(head, 'Pin Mode Start')

            if settings.preferences().prevent_fb_view_rotation:
                facebuilder_keymaps_register()
        else:
            push_head_in_undo_history(head, 'Pin Mode Switch')
            _log.red(f'{self.__class__.__name__} Switch only finished >>>')
            return {'FINISHED'}

        register_fb_undo_handler()
        _log.red(f'{self.__class__.__name__} Start pinmode modal >>>')
        return {'RUNNING_MODAL'}

    def _modal_should_finish(self, context: Any, event: Any) -> bool:
        settings = fb_settings()
        headnum = settings.current_headnum

        # Quit if Screen changed or out from localview
        if context.area is None or not check_context_localview(context):
            _log.output('CONTEXT LOST')
            FBLoader.out_pinmode(headnum)
            return True

        if headnum < 0:
            _log.error('HEAD LOST')
            FBLoader.out_pinmode(headnum)
            return True

        # Quit if Force Pinmode Out flag is set (by ex. license, pin problem)
        if settings.force_out_pinmode:
            _log.output('FORCE PINMODE OUT')
            FBLoader.out_pinmode(headnum)
            settings.force_out_pinmode = False
            if settings.license_error:
                # Show License Warning
                warn = get_operator(Config.kt_warning_idname)
                warn('INVOKE_DEFAULT', msg=ErrorType.NoLicense)
                settings.license_error = False
                show_user_preferences(facebuilder=False, geotracker=False)
            return True

        # Quit when camera rotated by user
        if context.space_data.region_3d.view_perspective != 'CAMERA':
            if settings.preferences().prevent_fb_view_rotation:
                # Return back to the camera view
                bpy_view_camera()
            else:
                _log.output('CAMERA ROTATED PINMODE OUT')
                _log.output(context.space_data.region_3d.view_perspective)
                FBLoader.out_pinmode(headnum)
                return True

        if event.type == 'ESC' and event.value == 'RELEASE':
            FBLoader.out_pinmode(headnum)
            # --- PROFILING ---
            if FBLoader.viewport().profiling:
                pr = FBLoader.viewport().pr
                pr.dump_stats('facebuilder.pstat')
            # --- PROFILING ---
            bpy_view_camera()
            return True

        return False

    def modal(self, context: Any, event: Any) -> Set:
        settings = fb_settings()

        if self.pinmode_id != settings.pinmode_id:
            _log.error('Extreme pinmode operator stop')
            _log.error(f'{self.pinmode_id} != {settings.pinmode_id}')
            unregister_fb_undo_handler()
            exit_area_localview(context.area)

            facebuilder_keymaps_unregister()
            return {'FINISHED'}

        headnum = settings.current_headnum
        head = settings.get_head(headnum)

        if self._modal_should_finish(context, event):
            unregister_fb_undo_handler()
            exit_area_localview(context.area)

            facebuilder_keymaps_unregister()
            return {'FINISHED'}

        region_check = self._check_camera_state_changed(context.space_data.region_3d)
        area_check = self._check_area_state_changed(FBLoader.get_work_area())
        if region_check or area_check:
            _log.output('CAMERA STATE CHANGED. FORCE TAG REDRAW')
            FBLoader.update_fb_viewport_shaders(adaptive_opacity=True,
                                                tag_redraw=True)

        if event.value == 'PRESS' and event.type == 'TAB':
            self._change_wireframe_visibility()
            context.area.tag_redraw()
            return {'RUNNING_MODAL'}

        if event.value == 'PRESS' and event.type == 'LEFTMOUSE':
            return self._on_left_mouse_press(
                context.area, event.mouse_region_x, event.mouse_region_y)

        if event.value == 'PRESS' and event.type == 'RIGHTMOUSE':
            return self._on_right_mouse_press(
                context.area, event.mouse_region_x, event.mouse_region_y)

        if event.type in {'LEFT_SHIFT', 'RIGHT_SHIFT'} \
                and event.value == 'PRESS':
            self._set_shift_pressed(True)

        if event.type in {'LEFT_SHIFT', 'RIGHT_SHIFT'} \
                and event.value == 'RELEASE':
            self._set_shift_pressed(False)

        camnum = settings.current_camnum
        kid = settings.get_keyframe(headnum, camnum)

        if head.need_update:
            self._undo_detected(context.area)

        vp = FBLoader.viewport()
        if not (vp.wireframer().is_working()):
            _log.error('WIREFRAME IS OFF')
            unregister_fb_undo_handler()
            FBLoader.out_pinmode(headnum)

            facebuilder_keymaps_unregister()
            return {'FINISHED'}

        vp.create_batch_2d(context.area)
        vp.update_residuals(FBLoader.get_builder(), kid, context.area)

        if vp.pins().current_pin() is not None:
            return {'RUNNING_MODAL'}
        else:
            return {'PASS_THROUGH'}
