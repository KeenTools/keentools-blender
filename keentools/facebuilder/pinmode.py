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

import logging
from typing import Any
from uuid import uuid4
import numpy as np

import bpy

from ..addon_config import Config, get_operator, ErrorType
from ..facebuilder_config import FBConfig, get_fb_settings
from ..utils.bpy_common import operator_with_context
from ..utils import coords
from .utils.manipulate import push_head_in_undo_history
from .fbloader import FBLoader
from ..utils.focal_length import update_camera_focal
from ..utils.ui_redraw import force_ui_redraw
from ..utils.other import hide_viewport_ui_elements_and_store_on_object
from ..utils.html import split_long_string
from ..utils.localview import exit_area_localview, check_area_active_problem
from ..utils.manipulate import switch_to_camera, center_viewports_on_object


_logger: Any = logging.getLogger(__name__)


def _log_output(message: str) -> None:
    global _logger
    _logger.debug(message)


def _log_warning(message: str) -> None:
    global _logger
    _logger.warning(message)


def _log_error(message: str) -> None:
    global _logger
    _logger.error(message)


_undo_handler = None


def undo_handler(scene):
    _log_output('undo_handler')
    try:
        settings = get_fb_settings()
        if not settings.pinmode or settings.current_headnum < 0:
            unregister_undo_handler()
            return
        head = settings.get_head(settings.current_headnum)
        head.need_update = True
    except Exception as err:
        _log_error(f'undo_handler {str(err)}')
        unregister_undo_handler()


def unregister_undo_handler():
    global _undo_handler
    if _undo_handler is not None:
        if _undo_handler in bpy.app.handlers.undo_post:
            bpy.app.handlers.undo_post.remove(_undo_handler)
    _undo_handler = None


def register_undo_handler():
    global _undo_handler
    unregister_undo_handler()
    _undo_handler = undo_handler
    bpy.app.handlers.undo_post.append(_undo_handler)


class FB_OT_PinMode(bpy.types.Operator):
    bl_idname = FBConfig.fb_pinmode_idname
    bl_label = 'FaceBuilder Pinmode'
    bl_description = 'Operator for in-Viewport drawing'
    bl_options = {'REGISTER', 'INTERNAL'}

    headnum: bpy.props.IntProperty(default=0)
    camnum: bpy.props.IntProperty(default=0)

    pinmode_id: bpy.props.StringProperty(default='')

    _shift_pressed = False
    _prev_camera_state = ()

    @classmethod
    def _check_camera_state_changed(cls, rv3d):
        camera_state = (rv3d.view_camera_zoom, rv3d.view_camera_offset)

        if camera_state != cls._prev_camera_state:
            cls._prev_camera_state = camera_state
            return True

        return False

    @classmethod
    def _set_shift_pressed(cls, val):
        cls._shift_pressed = val

    @classmethod
    def _is_shift_pressed(cls):
        return cls._shift_pressed

    def _fix_heads_with_warning(self):
        settings = get_fb_settings()
        heads_deleted, cams_deleted = settings.fix_heads()
        if heads_deleted > 0 or cams_deleted > 0:
            _log_warning('HEADS AND CAMERAS FIXED')
        if heads_deleted == 0:
            warn = get_operator(Config.kt_warning_idname)
            warn('INVOKE_DEFAULT', msg=ErrorType.SceneDamaged)

    def _init_wireframer_colors(self, opacity):
        settings = get_fb_settings()
        head = settings.get_head(settings.current_headnum)

        wf = FBLoader.viewport().wireframer()
        wf.init_colors((settings.wireframe_color,
                       settings.wireframe_special_color,
                       settings.wireframe_midline_color),
                       settings.wireframe_opacity * opacity)

        fb = FBLoader.get_builder()
        if not wf.init_wireframe_image(fb, settings.show_specials):
            wf.switch_to_simple_shader()

        wf.init_geom_data_from_fb(fb, head.headobj,
                                  head.get_keyframe(settings.current_camnum))
        wf.init_edge_indices(fb)
        wf.create_batches()

    def _delete_found_pin(self, nearest, area):
        settings = get_fb_settings()
        headnum = settings.current_headnum
        camnum = settings.current_camnum
        head = settings.get_head(headnum)
        kid = settings.get_keyframe(headnum, camnum)

        fb = FBLoader.get_builder()
        fb.remove_pin(kid, nearest)
        del FBLoader.viewport().pins().arr()[nearest]
        logging.debug('PIN REMOVED {}'.format(nearest))

        if not FBLoader.solve(headnum, camnum):
            _log_error('DELETE PIN PROBLEM')
            unregister_undo_handler()
            return {'FINISHED'}

        coords.update_head_mesh_non_neutral(fb, head)
        FBLoader.update_camera_pins_count(headnum, camnum)

        FBLoader.update_all_camera_positions(headnum)
        # Save result
        FBLoader.save_fb_serial_and_image_pathes(headnum)
        push_head_in_undo_history(head, 'Pin Remove')

        FBLoader.load_pins_into_viewport(headnum, camnum)
        FBLoader.update_viewport_shaders(area, headnum, camnum)

        return {"RUNNING_MODAL"}

    def _undo_detected(self, area):
        _log_output('UNDO DETECTED')
        settings = get_fb_settings()
        headnum = settings.current_headnum
        camnum = settings.current_camnum
        head = settings.get_head(headnum)

        head.need_update = False
        FBLoader.load_model(headnum)
        FBLoader.place_camera(headnum, camnum)
        FBLoader.load_pins_into_viewport(headnum, camnum)
        FBLoader.update_viewport_shaders(area, headnum, camnum)

    def _on_right_mouse_press(self, area, mouse_x, mouse_y):
        vp = FBLoader.viewport()
        vp.update_view_relative_pixel_size(area)

        x, y = coords.get_image_space_coord(mouse_x, mouse_y, area)

        nearest, dist2 = coords.nearest_point(x, y, vp.pins().arr())
        if nearest >= 0 and dist2 < FBLoader.viewport().tolerance_dist2():
            return self._delete_found_pin(nearest, area)

        FBLoader.viewport().create_batch_2d(area)
        return {'RUNNING_MODAL'}

    def _on_left_mouse_press(self, area, mouse_x, mouse_y):
        FBLoader.viewport().update_view_relative_pixel_size(area)

        if not coords.is_in_area(area, mouse_x, mouse_y):
            return {'PASS_THROUGH'}

        if coords.is_safe_region(area, mouse_x, mouse_y):
            settings = get_fb_settings()
            op = get_operator(FBConfig.fb_movepin_idname)
            op('INVOKE_DEFAULT', pinx=mouse_x, piny=mouse_y,
               headnum=settings.current_headnum,
               camnum=settings.current_camnum)
            return {'PASS_THROUGH'}

        return {'PASS_THROUGH'}

    def _check_keyframes(self, fb, head):
        for cam in head.cameras:
            if not fb.is_key_at(cam.get_keyframe()):
                return False
        return True

    def invoke(self, context, event):
        settings = get_fb_settings()

        _log_output(f'PINMODE ENTER. CURRENT_HEAD: {settings.current_headnum} '
                    f'CURRENT_CAM: {settings.current_camnum}')

        if not settings.check_heads_and_cams():
            self._fix_heads_with_warning()
            return {'CANCELLED'}

        head = settings.get_head(self.headnum)
        if not head or not head.headobj:
            _log_error('CANNOT FIND head or headobj')
            return {'CANCELLED'}
        headobj = head.headobj
        first_start = True

        vp = FBLoader.viewport()
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
            _log_output(f'PINMODE FORCE FINISH: H{settings.current_headnum} '
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

        _log_output(f'PINMODE START H{settings.current_headnum} '
                    f'C{settings.current_camnum}')
        # Start working with current model
        try:
            if not FBLoader.load_model_throw_exception(settings.current_headnum):
                raise Exception('Cannot load the model data from '
                                'the serialised string. Perhaps your file '
                                'or the scene data got corrupted.')
        except Exception as err:
            _log_error('MODEL CANNOT BE LOADED IN PINMODE')

            FBLoader.out_pinmode_without_save(self.headnum)
            exit_area_localview(area)

            _log_error(f'DESERIALIZE load_model_throw_exception: \n{str(err)}')
            error_message = '\n'.join(split_long_string(str(err), limit=64))
            warn = get_operator(Config.kt_warning_idname)
            warn('INVOKE_DEFAULT', msg=ErrorType.CustomMessage,
                 msg_content=error_message)
            return {'CANCELLED'}

        if not FBLoader.check_mesh(headobj):
            fb = FBLoader.get_builder()
            _log_error('MESH IS CORRUPTED {} != {}'.format(
                len(headobj.data.vertices), len(fb.applied_args_vertices())))

            FBLoader.out_pinmode_without_save(self.headnum)
            exit_area_localview(area)

            warn = get_operator(Config.kt_warning_idname)
            warn('INVOKE_DEFAULT', msg=ErrorType.MeshCorrupted)
            return {'CANCELLED'}

        fb = FBLoader.get_builder()
        fb.set_use_emotions(head.should_use_emotions())

        if not self._check_keyframes(fb, head):
            _log_output('PINMODE NO KEYFRAME')
            for cam in head.cameras:
                kfnum = cam.get_keyframe()
                _log_output(f'UPDATE KEYFRAME: {kfnum}')
                if not fb.is_key_at(kfnum):
                    _log_error('\nUNKNOWN KEYFRAME: {kfnum}\n')
                    fb.set_keyframe(kfnum, np.eye(4))
        try:
            FBLoader.place_camera(settings.current_headnum,
                                  settings.current_camnum)
        except Exception:
            _log_output('UPDATE KEYFRAME PROBLEM')
            return {'CANCELLED'}

        FBLoader.load_pins_into_viewport(settings.current_headnum, settings.current_camnum)
        coords.update_head_mesh_non_neutral(FBLoader.get_builder(), head)

        update_camera_focal(camera, fb)

        if first_start:
            hide_viewport_ui_elements_and_store_on_object(context.area, headobj)

            _log_output('START SHADERS')
            self._init_wireframer_colors(settings.overall_opacity)
            vp.create_batch_2d(context.area)
            _log_output('REGISTER SHADER HANDLERS')
            vp.register_handlers(context)

            context.window_manager.modal_handler_add(self)

            _log_output('SHADER STOPPER START')
            self.pinmode_id = str(uuid4())
            settings.pinmode_id = self.pinmode_id
            FBLoader.start_shader_timer(self.pinmode_id)
            _log_output(f'pinmode_id: {self.pinmode_id}')
        else:
            _log_output('SHADER UPDATE ONLY')
            self._init_wireframer_colors(settings.overall_opacity)

        if not check_area_active_problem(area):
            assert area.spaces.active.region_3d.view_perspective == 'CAMERA'
            _log_output('bpy.ops.view3d.view_center_camera call')
            operator_with_context(bpy.ops.view3d.view_center_camera,
                {'area': area, 'region': coords.get_area_region(area)})

        vp.update_surface_points(FBLoader.get_builder(), headobj, kid)
        push_head_in_undo_history(head, 'Pin Mode Start.')
        if not first_start:
            _log_output('PINMODE SWITCH ONLY')
            return {'FINISHED'}

        register_undo_handler()
        _log_output('PINMODE STARTED')
        return {'RUNNING_MODAL'}

    def _wireframe_view_toggle(self):
        settings = get_fb_settings()

        settings.overall_opacity = \
            0.0 if settings.overall_opacity > 0.5 else 1.0
        _log_output(f'OVERALL_OPACITY BY TAB {settings.overall_opacity}')
        self._init_wireframer_colors(settings.overall_opacity)
        force_ui_redraw('VIEW_3D')

    def _modal_should_finish(self, context, event):
        settings = get_fb_settings()
        headnum = settings.current_headnum

        # Quit if Screen changed
        if context.area is None:  # Different operation Space
            _log_output('CONTEXT LOST')
            FBLoader.out_pinmode(headnum)
            return True

        if headnum < 0:
            _log_error('HEAD LOST')
            FBLoader.out_pinmode(headnum)
            return True

        # Quit if Force Pinmode Out flag is set (by ex. license, pin problem)
        if settings.force_out_pinmode:
            _log_output('FORCE PINMODE OUT')
            FBLoader.out_pinmode(headnum)
            settings.force_out_pinmode = False
            if settings.license_error:
                # Show License Warning
                warn = get_operator(Config.kt_warning_idname)
                warn('INVOKE_DEFAULT', msg=ErrorType.NoLicense)
                settings.license_error = False
                settings.hide_user_preferences()
            return True

        # Quit when camera rotated by user
        if context.space_data.region_3d.view_perspective != 'CAMERA':
            if settings.preferences().prevent_view_rotation:
                # Return back to the camera view
                bpy.ops.view3d.view_camera()
            else:
                _log_output('CAMERA ROTATED PINMODE OUT')
                _log_output(context.space_data.region_3d.view_perspective)
                FBLoader.out_pinmode(headnum)
                return True

        if event.type == 'ESC' and event.value == 'RELEASE':
            FBLoader.out_pinmode(headnum)
            # --- PROFILING ---
            if FBLoader.viewport().profiling:
                pr = FBLoader.viewport().pr
                pr.dump_stats('facebuilder.pstat')
            # --- PROFILING ---
            bpy.ops.view3d.view_camera()
            return True

        return False

    def modal(self, context, event):
        settings = get_fb_settings()

        if self.pinmode_id != settings.pinmode_id:
            _log_error('Extreme pinmode operator stop')
            _log_error(f'{self.pinmode_id} != {settings.pinmode_id}')
            unregister_undo_handler()
            exit_area_localview(context.area)
            return {'FINISHED'}

        headnum = settings.current_headnum
        head = settings.get_head(headnum)

        if self._modal_should_finish(context, event):
            unregister_undo_handler()
            exit_area_localview(context.area)
            return {'FINISHED'}

        if self._check_camera_state_changed(context.space_data.region_3d):
            _log_output('CAMERA STATE CHANGED. FORCE TAG REDRAW')
            context.area.tag_redraw()

        if event.value == 'PRESS' and event.type == 'TAB':
            self._wireframe_view_toggle()
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
            _log_output('UNDO CALL DETECTED')
            self._undo_detected(context.area)

        vp = FBLoader.viewport()
        if not (vp.wireframer().is_working()):
            _log_output('WIREFRAME IS OFF')
            unregister_undo_handler()
            FBLoader.out_pinmode(headnum)
            return {'FINISHED'}

        vp.create_batch_2d(context.area)
        vp.update_residuals(FBLoader.get_builder(), kid, context.area)

        if vp.pins().current_pin() is not None:
            return {'RUNNING_MODAL'}
        else:
            return {'PASS_THROUGH'}
