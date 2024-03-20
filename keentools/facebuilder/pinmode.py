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
                            gt_pinmode,
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


_log = KTLogger(__name__)


_undo_handler: Optional[Callable] = None


def undo_handler(scene: Any) -> None:
    _log.output('undo_handler')
    try:
        settings = fb_settings()
        if not settings.pinmode or settings.current_headnum < 0:
            unregister_undo_handler()
            return
        head = settings.get_head(settings.current_headnum)
        head.need_update = True
    except Exception as err:
        _log.error(f'undo_handler {str(err)}')
        unregister_undo_handler()


def unregister_undo_handler() -> None:
    global _undo_handler
    if _undo_handler is not None:
        if _undo_handler in bpy.app.handlers.undo_post:
            bpy.app.handlers.undo_post.remove(_undo_handler)
    _undo_handler = None


def register_undo_handler() -> None:
    global _undo_handler
    unregister_undo_handler()
    _undo_handler = undo_handler
    bpy.app.handlers.undo_post.append(_undo_handler)


def _calc_adaptive_opacity(area: Area) -> None:
    settings = fb_settings()
    if not settings.use_adaptive_opacity:
        return
    settings.calc_adaptive_opacity(area)
    vp = FBLoader.viewport()
    vp.update_wireframe_colors()


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

    def _init_wireframer_colors_and_batches(self) -> None:
        settings = fb_settings()
        head = settings.get_head(settings.current_headnum)

        vp = FBLoader.viewport()
        vp.update_wireframe_colors()
        wf = vp.wireframer()
        fb = FBLoader.get_builder()
        wf.init_wireframe_image(settings.show_specials)

        keyframe = head.get_keyframe(settings.current_camnum)
        wf.init_edge_indices()

        wf.set_object_world_matrix(head.headobj.matrix_world)
        camobj = head.get_camera(settings.current_camnum).camobj
        wf.set_camera_pos(camobj, head.headobj)
        geo = fb.applied_args_model_at(keyframe)
        wf.init_geom_data_from_core(*FBLoader.get_geo_shader_data(geo))

        wf.create_batches()

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
            unregister_undo_handler()

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
        _log.output('UNDO DETECTED')
        settings = fb_settings()
        headnum = settings.current_headnum
        camnum = settings.current_camnum
        head = settings.get_head(headnum)

        head.need_update = False
        FBLoader.load_model(headnum)
        FBLoader.place_camera(headnum, camnum)
        FBLoader.load_pins_into_viewport(headnum, camnum)
        FBLoader.update_fb_viewport_shaders(area=area,
                                            wireframe=True,
                                            camera_pos=True,
                                            pins_and_residuals=True)

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
        self._init_wireframer_colors_and_batches()
        return {'FINISHED'}

    def invoke(self, context: Any, event: Any) -> Set:
        _log.green(f'{self.__class__.__name__} invoke')
        settings = fb_settings()

        _log.output(f'FB PINMODE ENTER. CURRENT_HEAD: {settings.current_headnum} '
                    f'FB CURRENT_CAM: {settings.current_camnum}')

        if not settings.check_heads_and_cams():
            self._fix_heads_with_warning()
            return {'CANCELLED'}

        if gt_pinmode():
            msg = 'Cannot start while GeoTracker is in Pin mode!'
            _log.error(msg)
            self.report({'ERROR'}, msg)
            return {'CANCELLED'}

        head = settings.get_head(self.headnum)
        if not head or not head.headobj:
            _log.error('FB CANNOT FIND head or headobj')
            return {'CANCELLED'}

        if not supported_gpu_backend():
            warn = get_operator(Config.kt_warning_idname)
            warn('INVOKE_DEFAULT', msg=ErrorType.UnsupportedGPUBackend)
            return {'CANCELLED'}

        headobj = head.headobj
        first_start = True

        vp = FBLoader.viewport()
        if not vp.load_all_shaders() and Config.strict_shader_check:
            return {'CANCELLED'}

        # Stopped shaders means that we need to restart pinmode
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

        settings.current_headnum = self.headnum
        settings.current_camnum = self.camnum
        settings.pinmode = True

        camera = head.get_camera(settings.current_camnum)
        camera.update_scene_frame_size()
        camera.update_background_image_scale()
        kid = camera.get_keyframe()

        camera.apply_tone_mapping()

        area = context.area if first_start else FBLoader.get_work_area()
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
            _log.error('FB MODEL CANNOT BE LOADED IN PINMODE')

            FBLoader.out_pinmode_without_save(self.headnum)
            exit_area_localview(area)

            _log.error(f'DESERIALIZE load_model_throw_exception: \n{str(err)}')
            error_message = '\n'.join(split_long_string(str(err), limit=64))
            warn = get_operator(Config.kt_warning_idname)
            warn('INVOKE_DEFAULT', msg=ErrorType.CustomMessage,
                 msg_content=error_message)
            return {'CANCELLED'}

        _log.output('model loaded')

        if not FBLoader.check_mesh(headobj):
            fb = FBLoader.get_builder()
            _log.error('FB MESH IS CORRUPTED {} != {}'.format(
                len(headobj.data.vertices), len(fb.applied_args_vertices())))

            FBLoader.out_pinmode_without_save(self.headnum)
            exit_area_localview(area)

            warn = get_operator(Config.kt_warning_idname)
            warn('INVOKE_DEFAULT', msg=ErrorType.MeshCorrupted)
            return {'CANCELLED'}

        fb = FBLoader.get_builder()
        fb.set_use_emotions(head.should_use_emotions())

        if not self._check_keyframes(fb, head):
            _log.output('FB PINMODE NO KEYFRAME')
            for cam in head.cameras:
                kfnum = cam.get_keyframe()
                _log.output(f'FB UPDATE KEYFRAME: {kfnum}')
                if not fb.is_key_at(kfnum):
                    _log.error(f'\nFB UNKNOWN KEYFRAME: {kfnum}\n')
                    fb.set_keyframe(kfnum, np.eye(4))
        try:
            FBLoader.place_camera(settings.current_headnum,
                                  settings.current_camnum)
        except Exception:
            _log.output('FB UPDATE KEYFRAME PROBLEM')
            return {'CANCELLED'}

        update_head_mesh_non_neutral(FBLoader.get_builder(), head)
        _log.output('before update_camera_focal')
        update_camera_focal(camera, fb)
        _log.output('after update_camera_focal')

        self._check_camera_state_changed(get_area_region_3d(area))
        self._check_area_state_changed(area)
        _log.output('pinmode invoke _calc_adaptive_opacity')
        _calc_adaptive_opacity(area)

        FBLoader.load_pins_into_viewport(settings.current_headnum,
                                         settings.current_camnum)

        self._init_wireframer_colors_and_batches()
        if first_start:
            settings.viewport_state.hide_ui_elements(area)

            _log.output('START FB SHADERS')
            self._change_wireframe_visibility(toggle=False, value=True)
            vp.create_batch_2d(area)
            _log.output('REGISTER FB SHADER HANDLERS')
            vp.register_handlers(context)

            context.window_manager.modal_handler_add(self)

            _log.output('FB SHADER STOPPER START')
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
            _log.output('FB PINMODE SWITCH ONLY')
            return {'FINISHED'}

        register_undo_handler()
        _log.output('FB PINMODE STARTED')
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
            unregister_undo_handler()
            exit_area_localview(context.area)

            facebuilder_keymaps_unregister()
            return {'FINISHED'}

        headnum = settings.current_headnum
        head = settings.get_head(headnum)

        if self._modal_should_finish(context, event):
            unregister_undo_handler()
            exit_area_localview(context.area)

            facebuilder_keymaps_unregister()
            return {'FINISHED'}

        region_check = self._check_camera_state_changed(context.space_data.region_3d)
        area_check = self._check_area_state_changed(FBLoader.get_work_area())
        if region_check or area_check:
            _log.output('CAMERA STATE CHANGED. FORCE TAG REDRAW')
            _calc_adaptive_opacity(context.area)
            context.area.tag_redraw()

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
            _log.output('UNDO CALL DETECTED')
            self._undo_detected(context.area)

        vp = FBLoader.viewport()
        if not (vp.wireframer().is_working()):
            _log.output('WIREFRAME IS OFF')
            unregister_undo_handler()
            FBLoader.out_pinmode(headnum)

            facebuilder_keymaps_unregister()
            return {'FINISHED'}

        vp.create_batch_2d(context.area)
        vp.update_residuals(FBLoader.get_builder(), kid, context.area)

        if vp.pins().current_pin() is not None:
            return {'RUNNING_MODAL'}
        else:
            return {'PASS_THROUGH'}
