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

from typing import Any, Optional, Callable, List, Tuple, Set
from uuid import uuid4
import numpy as np
from copy import deepcopy

import bpy
from bpy.props import IntProperty, StringProperty, BoolProperty
from bpy.types import Operator, Area

from ..utils.kt_logging import KTLogger
from ..addon_config import (Config,
                            fb_settings,
                            get_operator,
                            ErrorType,
                            show_user_preferences,
                            supported_gpu_backend,
                            common_loader)
from ..facebuilder_config import FBConfig
from ..utils.bpy_common import (operator_with_context,
                                bpy_view_camera,
                                get_scene_camera_shift)
from ..utils.coords import (update_head_mesh_non_neutral,
                            get_image_space_coord,
                            nearest_point,
                            point_is_in_area,
                            point_is_in_service_region,
                            get_area_region,
                            get_area_region_3d,
                            get_camera_border)
from .utils.manipulate import push_head_in_undo_history
from ..utils.focal_length import update_camera_focal
from ..utils.html import split_long_string
from ..utils.localview import (exit_area_localview,
                               check_area_active_problem,
                               check_context_localview)
from ..utils.manipulate import switch_to_camera, center_viewports_on_object
from .ui_strings import buttons
from ..preferences.hotkeys import (facebuilder_keymaps_register,
                                   all_keymaps_unregister)
from .prechecks import common_fb_checks
from ..utils.ui_redraw import total_redraw_ui
from .facebuilder_acts import solve_head


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

    detect_face: BoolProperty(default=False)

    _shift_pressed: bool = False

    bus_id: IntProperty(default=-1)

    def init_bus(self) -> None:
        message_bus = common_loader().message_bus()
        self.bus_id = message_bus.register_item(FBConfig.fb_pinmode_idname)
        _log.output(f'{self.__class__.__name__} bus_id={self.bus_id}')

    def release_bus(self) -> None:
        message_bus = common_loader().message_bus()
        item = message_bus.remove_by_id(self.bus_id)
        _log.output(f'release_bus: {self.bus_id} -> {item}')

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
        settings = fb_settings()
        loader = settings.loader()
        vp = loader.viewport()
        flag = not vp.wireframer().is_visible() if toggle else value
        vp.set_shaders_visible(flag)
        vp.texter().set_shader_visible(True)
        if flag:
            vp.revert_default_screen_message(unregister=False)
        else:
            default_txt = deepcopy(vp.texter().get_default_text())
            default_txt[0]['text'] = 'Press TAB to show wireframe'
            default_txt[0]['color'] = (1., 0., 1., 0.85)
            vp.message_to_screen(default_txt)

    def _delete_pins(self, pin_index_list: List[int]) -> Set:
        _log.yellow('_delete_pins start')
        if len(pin_index_list) == 0:
            _log.red('_delete_pins: no pins to remove >>>')
            return {'RUNNING_MODAL'}

        settings = fb_settings()
        loader = settings.loader()
        headnum = settings.current_headnum
        camnum = settings.current_camnum
        head = settings.get_head(headnum)
        kid = head.get_keyframe(camnum)

        vp = loader.viewport()
        pins = vp.pins()
        fb = loader.get_builder()
        pin_index_list.sort()
        for i in reversed(pin_index_list):
            fb.remove_pin(kid, i)
            pins.remove_pin(i)
            _log.output(f'FB PIN REMOVED {i}')

        if not loader.solve(headnum, camnum):
            _log.error('FB DELETE PIN PROBLEM')
            unregister_fb_undo_handler()
            self.on_finish()
            return {'FINISHED'}

        if fb.pins_count(kid) < 4:
            _log.output('_delete_pins FB solve_head call')
            solve_head(headnum)

        update_head_mesh_non_neutral(fb, head)
        loader.update_camera_pins_count(headnum, camnum)

        loader.update_all_camera_positions(headnum)
        # Save result
        loader.save_fb_serial_and_image_pathes(headnum)
        push_head_in_undo_history(
            head, 'Remove pin' if len(pin_index_list) == 1 else 'Remove pins')

        loader.update_fb_viewport_shaders(wireframe=True,
                                          load_pins=True,
                                          pins_and_residuals=True)

        _log.output('_delete_pins end >>>')
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
        loader = settings.loader()
        loader.load_model(headnum)
        loader.place_camera(headnum, camnum)
        loader.load_pins_into_viewport(headnum, camnum)
        loader.update_fb_viewport_shaders(area=area,
                                          wireframe=True,
                                          pins_and_residuals=True,
                                          camera_pos=True,
                                          tag_redraw=True)
        _log.output(f'{self.__class__.__name__} _undo_detected end >>>')

    def _on_right_mouse_press(self, area: Area,
                              mouse_x: float, mouse_y: float) -> Set:
        settings = fb_settings()
        loader = settings.loader()
        vp = loader.viewport()
        vp.update_view_relative_pixel_size(area)

        x, y = get_image_space_coord(mouse_x, mouse_y, area)

        nearest, dist2 = nearest_point(x, y, vp.pins().arr())
        if nearest >= 0 and dist2 < vp.tolerance_dist2():
            return self._delete_pins([nearest])

        loader.viewport().create_batch_2d(area)
        return {'RUNNING_MODAL'}

    def _on_left_mouse_press(self, area: Area, event: Any) -> Set:
        mouse_x, mouse_y = event.mouse_region_x, event.mouse_region_y
        settings = fb_settings()
        loader = settings.loader()
        vp = loader.viewport()
        vp.update_view_relative_pixel_size(area)

        if not vp.points2d().is_visible():
            _log.output('OBJECT IS IN EDIT MODE. LEFT CLICK HAS BEEN IGNORED')
            return {'PASS_THROUGH'}

        if not point_is_in_area(area, mouse_x, mouse_y,
                                bottom_limit=Config.area_bottom_limit):
            _log.output('LEFT CLICK OUTSIDE OF VIEWPORT AREA')
            return {'PASS_THROUGH'}

        if point_is_in_service_region(area, mouse_x, mouse_y):
            _log.output('LEFT CLICK IN SERVICE REGION OF AREA')
            return {'PASS_THROUGH'}

        pins = vp.pins()
        if not pins.get_add_selection_mode():
            op = get_operator(FBConfig.fb_movepin_idname)
            op('INVOKE_DEFAULT', pinx=mouse_x, piny=mouse_y,
               headnum=settings.current_headnum,
               camnum=settings.current_camnum)
            return {'PASS_THROUGH'}

        x, y = get_image_space_coord(mouse_x, mouse_y, area,
                                     *get_scene_camera_shift())
        nearest, dist2 = nearest_point(x, y, vp.pins().arr())
        if nearest >= 0 and dist2 < vp.tolerance_dist2():
            _log.output(f'CHANGE SELECTION PIN FOUND: {nearest}')
            pins.set_current_pin_num(nearest)
            selected_pins = pins.get_selected_pins()

            if nearest in selected_pins:
                pins.exclude_selected_pin(nearest)
            else:
                pins.add_selected_pins([nearest])
        else:
            settings.start_selection(mouse_x, mouse_y)
        loader.update_fb_viewport_shaders(area=area,
                                          wireframe=True,
                                          pins_and_residuals=True,
                                          camera_pos=True,
                                          tag_redraw=True)
        vp.tag_redraw()
        return {'PASS_THROUGH'}

    def _check_keyframes(self, fb: Any, head: Any) -> bool:
        for cam in head.cameras:
            if not fb.is_key_at(cam.get_keyframe()):
                return False
        return True

    def execute(self, context: Any) -> Set:  # Testing purpose only
        _log.green('PinMode execute call')
        settings = fb_settings()
        loader = settings.loader()
        loader.update_fb_viewport_shaders(wireframe_colors=True,
                                          wireframe_image=True,
                                          camera_pos=True,
                                          wireframe=True)
        return {'FINISHED'}

    def invoke(self, context: Any, event: Any) -> Set:
        _log.green(f'{self.__class__.__name__} invoke')
        settings = fb_settings()
        loader = settings.loader()

        _log.output(f'current_headnum: {settings.current_headnum} '
                    f'current_camnum: {settings.current_camnum}')

        check_status = common_fb_checks(object_mode=True,
                                        is_calculating=True,
                                        stop_other_pinmode=True,
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

        vp = loader.viewport()
        if not vp.load_all_shaders() and Config.strict_shader_check:
            _log.red(f'{self.__class__.__name__} 3 cancelled >>>')
            return {'CANCELLED'}

        vp.pins().on_start()

        # Stopped shaders mean that we need to restart pinmode
        if not vp.viewport_is_working():
            settings.pinmode = False

        if settings.wrong_pinmode_id():
            settings.pinmode = False

        # We have to fix last operation if we are in Pinmode
        if settings.pinmode and \
                settings.current_headnum >= 0 and settings.current_camnum >= 0:

            old_head = settings.get_head(settings.current_headnum)
            old_camera = old_head.get_camera(settings.current_camnum)
            old_camera.reset_tone_mapping()

            loader.save_pinmode_state(settings.current_headnum)
            _log.output(f'FB PINMODE FORCE FINISH: H{settings.current_headnum} '
                        f'C{settings.current_camnum}')
            first_start = False
        else:
            loader.update_cameras_from_old_version(self.headnum)

        area = context.area if first_start else loader.get_work_area()
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
            if not loader.load_model_throw_exception(settings.current_headnum):
                raise Exception('Cannot load the model data from '
                                'the serialised string. Perhaps your file '
                                'or the scene data got corrupted.')
        except Exception as err:
            _log.red('FB MODEL CANNOT BE LOADED IN PINMODE')

            loader.out_pinmode_without_save()
            exit_area_localview(area)

            _log.error(f'DESERIALIZE load_model_throw_exception: \n{str(err)}')
            error_message = '\n'.join(split_long_string(str(err), limit=64))
            warn = get_operator(Config.kt_warning_idname)
            warn('INVOKE_DEFAULT', msg=ErrorType.CustomMessage,
                 msg_content=error_message)
            _log.red(f'{self.__class__.__name__} cannot load 5 cancelled >>>')
            return {'CANCELLED'}

        _log.output('model loaded')

        if not loader.check_mesh(headobj):
            fb = loader.get_builder()
            _log.error(f'FB MESH IS CORRUPTED '
                       f'{len(headobj.data.vertices)} != '
                       f'{len(fb.applied_args_vertices())}')

            loader.out_pinmode_without_save()
            exit_area_localview(area)

            warn = get_operator(Config.kt_warning_idname)
            warn('INVOKE_DEFAULT', msg=ErrorType.MeshCorrupted)
            _log.red(f'{self.__class__.__name__} check mesh 6 cancelled >>>')
            return {'CANCELLED'}

        fb = loader.get_builder()
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
            loader.place_camera(settings.current_headnum,
                                settings.current_camnum)
        except Exception:
            _log.output('FB UPDATE KEYFRAME PROBLEM')
            _log.red(f'{self.__class__.__name__} keyframe error 7 cancelled >>>')
            return {'CANCELLED'}

        update_head_mesh_non_neutral(fb, head)
        _log.output('before update_camera_focal')
        update_camera_focal(camera, fb)
        _log.output('after update_camera_focal')

        vp.check_camera_state_changed(get_area_region_3d(area))
        vp.check_area_state_changed(area)

        loader.update_fb_viewport_shaders(adaptive_opacity=True,
                                          wireframe_colors=True,
                                          wireframe_image=True,
                                          camera_pos=True,
                                          ui_scale=True,
                                          load_pins=True,
                                          wireframe=True)
        if first_start:
            settings.viewport_state.hide_ui_elements(area)

            _log.output('START FB SHADERS')
            self._change_wireframe_visibility(toggle=False, value=True)
            vp.create_batch_2d(area)
            vp.register_handlers(area=area)

            self.init_bus()
            context.window_manager.modal_handler_add(self)

            _log.output('START FB SHADER STOPPER')
            self.pinmode_id = str(uuid4())
            settings.pinmode_id = self.pinmode_id
            loader.start_shader_timer(self.pinmode_id)
            _log.output(f'pinmode_id: {self.pinmode_id}')
        else:
            _log.output('FB SHADER UPDATE ONLY')

        if not check_area_active_problem(area):
            assert area.spaces.active.region_3d.view_perspective == 'CAMERA'
            _log.output('bpy.ops.view3d.view_center_camera call')
            operator_with_context(bpy.ops.view3d.view_center_camera,
                {'area': area, 'region': get_area_region(area)})

        vp.update_surface_points(loader.get_builder(), headobj, kid)

        if settings.preferences().prevent_fb_view_rotation:
            facebuilder_keymaps_register()

        if first_start:
            if (len(head.cameras) == 1 and not camera.has_pins()) or self.detect_face:
                total_redraw_ui()  # for proper background image data loading
                _log.green(f'{self.__class__.__name__} calls '
                           f'FBConfig.fb_pickmode_starter_idname')
                op = get_operator(FBConfig.fb_pickmode_starter_idname)
                op('INVOKE_DEFAULT',
                   headnum=settings.current_headnum,
                   camnum=settings.current_camnum,
                   auto_detect_single=True)

            push_head_in_undo_history(head, 'Pin Mode Start')
        else:
            push_head_in_undo_history(head, 'Pin Mode Switch')
            _log.red(f'{self.__class__.__name__} Switch only finished >>>')
            return {'FINISHED'}

        register_fb_undo_handler()
        _log.red(f'{self.__class__.__name__} Start pinmode modal >>>')
        return {'RUNNING_MODAL'}

    def _modal_should_finish(self, context: Any, event: Any) -> bool:
        settings = fb_settings()
        loader = settings.loader()

        # Quit if Screen changed or out from localview
        if context.area is None or not check_context_localview(context):
            _log.output('CONTEXT LOST')
            loader.out_pinmode_without_save()
            return True

        if not settings.is_proper_headnum(settings.current_headnum):
            _log.error('HEAD LOST')
            loader.out_pinmode_without_save()
            return True

        # Quit if Force Pinmode Out flag is set (by ex. license, pin problem)
        if settings.force_out_pinmode:
            _log.output('FORCE PINMODE OUT')
            loader.out_pinmode_without_save()
            settings.force_out_pinmode = False
            if settings.license_error:
                # Show License Warning
                warn = get_operator(Config.kt_warning_idname)
                warn('INVOKE_DEFAULT', msg=ErrorType.NoFaceBuilderLicense)
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
                loader.out_pinmode_without_save()
                return True

        if event.type == 'ESC' and event.value == 'RELEASE':
            if settings.selection_mode:
                settings.cancel_selection()
                loader.viewport().tag_redraw()
                _log.red(f'{self.__class__.__name__} selection ESC -- finished >>>')
                return False

            loader.out_pinmode_without_save()
            # --- PROFILING ---
            if loader.viewport().profiling:
                pr = loader.viewport().pr
                pr.dump_stats('facebuilder.pstat')
            # --- PROFILING ---
            bpy_view_camera()
            return True

        return False

    def on_finish(self) -> None:
        _log.yellow(f'{self.__class__.__name__}.on_finish start')
        all_keymaps_unregister()
        self.release_bus()
        settings = fb_settings()
        if settings.selection_mode:
            settings.cancel_selection()
        _log.output(f'{self.__class__.__name__}.on_finish end >>>')

    def cancel(self, context) -> None:
        _log.magenta(f'{self.__class__.__name__} cancel ***')
        self.on_finish()

    def modal(self, context: Any, event: Any) -> Set:
        message_bus = common_loader().message_bus()
        if not message_bus.check_id(self.bus_id):
            _log.red(f'{self.__class__.__name__} bus stop modal end *** >>>')
            return {'FINISHED'}

        settings = fb_settings()
        loader = settings.loader()
        vp = loader.viewport()

        if self.pinmode_id != settings.pinmode_id:
            _log.error('Extreme pinmode operator stop')
            _log.error(f'{self.pinmode_id} != {settings.pinmode_id}')
            unregister_fb_undo_handler()
            exit_area_localview(context.area)

            self.on_finish()
            return {'FINISHED'}

        if not vp.viewport_is_working():
            _log.error('VIEWPORT DOES NOT WORK')
            unregister_fb_undo_handler()
            loader.out_pinmode_without_save()

            self.on_finish()
            return {'FINISHED'}

        if self._modal_should_finish(context, event):
            unregister_fb_undo_handler()
            exit_area_localview(context.area)

            self.on_finish()
            return {'FINISHED'}

        region_check = vp.check_camera_state_changed(context.space_data.region_3d)
        area_check = vp.check_area_state_changed(vp.get_work_area())
        if region_check or area_check:
            _log.output('CAMERA STATE CHANGED. FORCE TAG REDRAW')
            loader.update_fb_viewport_shaders(adaptive_opacity=True,
                                              ui_scale=True,
                                              tag_redraw=True)

        if event.value == 'PRESS' and event.type == 'TAB':
            self._change_wireframe_visibility()
            context.area.tag_redraw()
            return {'RUNNING_MODAL'}

        if event.type in {'LEFT_SHIFT', 'RIGHT_SHIFT'} \
                and event.value == 'PRESS':
            self._set_shift_pressed(True)
            if not settings.selection_mode:
                vp.pins().set_add_selection_mode(True)

        if event.type in {'LEFT_SHIFT', 'RIGHT_SHIFT'} \
                and event.value == 'RELEASE':
            self._set_shift_pressed(False)
            if not settings.selection_mode:
                vp.pins().set_add_selection_mode(False)

        if settings.selection_mode:
            if event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
                settings.end_selection(context.area, event.mouse_region_x, event.mouse_region_y)
                loader.update_fb_viewport_shaders(pins_and_residuals=True)
            else:
                settings.do_selection(event.mouse_region_x, event.mouse_region_y)
            vp.tag_redraw()
            _log.red(f'{self.__class__.__name__} mouse selection -- modal >>>')
            return {'RUNNING_MODAL'}

        if event.value == 'PRESS' and event.type == 'LEFTMOUSE':
            return self._on_left_mouse_press(context.area, event)

        if event.value == 'PRESS' and event.type == 'RIGHTMOUSE':
            return self._on_right_mouse_press(
                context.area, event.mouse_region_x, event.mouse_region_y)

        if event.value == 'PRESS' and event.type in {'BACK_SPACE', 'DEL'}:
            return self._delete_pins(vp.pins().get_selected_pins())

        head = settings.get_head(settings.current_headnum)
        if head.need_update:
            self._undo_detected(context.area)

        kid = head.get_keyframe(settings.current_camnum)
        vp.create_batch_2d(context.area)
        vp.update_residuals(loader.get_builder(), kid, context.area)

        return {'PASS_THROUGH'}
