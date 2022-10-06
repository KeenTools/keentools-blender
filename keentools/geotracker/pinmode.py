# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2019-2022  KeenTools

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

import bpy

from ..addon_config import get_operator
from ..geotracker_config import GTConfig, get_gt_settings, get_current_geotracker_item
from .gtloader import GTLoader
from ..utils import coords

from ..utils.manipulate import force_undo_push, switch_to_camera
from ..utils.other import (hide_viewport_ui_elements_and_store_on_object,
                           unhide_viewport_ui_elements_from_object)
from ..utils.images import set_background_image_by_movieclip
from ..utils.bpy_common import bpy_current_frame
from ..utils.video import fit_render_size


_logger: Any = logging.getLogger(__name__)


def _log_output(message: str) -> None:
    global _logger
    _logger.debug(message)


def _log_error(message: str) -> None:
    global _logger
    _logger.error(message)


class GT_OT_PinMode(bpy.types.Operator):
    bl_idname = GTConfig.gt_pinmode_idname
    bl_label = 'GeoTracker Pinmode'
    bl_description = 'Operator for in-Viewport drawing'
    bl_options = {'REGISTER', 'INTERNAL'}

    geotracker_num: bpy.props.IntProperty(default=-1)

    pinmode_id: bpy.props.StringProperty(default='')

    _shift_pressed = False
    _prev_camera_state = ()

    @classmethod
    def _check_camera_state_changed(cls, rv3d):
        camera_state = (rv3d.view_camera_zoom, *rv3d.view_camera_offset)

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

    def _on_left_mouse_press(self, area, event):
        mouse_x, mouse_y = event.mouse_region_x, event.mouse_region_y
        GTLoader.viewport().update_view_relative_pixel_size(area)

        if not coords.is_in_area(area, mouse_x, mouse_y):
            return {'PASS_THROUGH'}

        if coords.is_safe_region(area, mouse_x, mouse_y):
            op = get_operator(GTConfig.gt_movepin_idname)
            op('INVOKE_DEFAULT', pinx=mouse_x, piny=mouse_y)
            return {'PASS_THROUGH'}

        return {'PASS_THROUGH'}

    def _on_right_mouse_press(self, area, event):
        mouse_x, mouse_y = event.mouse_region_x, event.mouse_region_y
        vp = GTLoader.viewport()
        vp.update_view_relative_pixel_size(area)

        x, y = coords.get_image_space_coord(mouse_x, mouse_y, area)

        nearest, dist2 = coords.nearest_point(x, y, vp.pins().arr())
        if nearest >= 0 and dist2 < vp.tolerance_dist2():
            return self._delete_found_pin(nearest, area)

        vp.create_batch_2d(area)
        return {'RUNNING_MODAL'}

    def _delete_found_pin(self, nearest, area):
        gt = GTLoader.kt_geotracker()
        gt.remove_pin(nearest)
        GTLoader.viewport().pins().remove_pin(nearest)
        _log_output('PIN REMOVED {}'.format(nearest))

        geotracker = get_current_geotracker_item()
        if not geotracker:
            return {'FINISHED'}

        kid = bpy_current_frame()
        GTLoader.safe_keyframe_add(kid)

        if not GTLoader.solve():
            _log_error('DELETE PIN PROBLEM')
            return {'FINISHED'}

        GTLoader.load_pins_into_viewport()
        GTLoader.place_object_or_camera()

        vp = GTLoader.viewport()
        vp.update_surface_points(gt, geotracker.geomobj, kid)

        if not geotracker.camera_mode():
            wf = vp.wireframer()
            wf.init_geom_data_from_mesh(geotracker.geomobj)
            wf.create_batches()

        vp.create_batch_2d(area)
        vp.update_residuals(gt, area, kid)
        vp.tag_redraw()

        force_undo_push('Delete GeoTracker pin')
        return {'RUNNING_MODAL'}

    def _new_pinmode_id(self):
        settings = get_gt_settings()
        self.pinmode_id = str(uuid4())
        settings.pinmode_id = self.pinmode_id

    def _init_pinmode(self, area, context=None):
        if not GTLoader.load_geotracker():
            _log_output('NEW KT_GEOTRACKER')
            GTLoader.new_kt_geotracker()

        _log_output('START SHADERS')
        GTLoader.load_pins_into_viewport()
        vp = GTLoader.viewport()
        vp.create_batch_2d(area)
        _log_output('REGISTER SHADER HANDLERS')
        GTLoader.update_all_viewport_shaders(area)
        if context is not None:
            vp.register_handlers(context)
        vp.tag_redraw()

    def _start_new_pinmode(self, context):
        _log_output('_start_new_pinmode')
        settings = get_gt_settings()
        settings.pinmode = True
        self._new_pinmode_id()
        _log_output(f'_new_pinmode_id: {settings.pinmode_id}')

        self._set_new_geotracker(context.area)
        self._init_pinmode(context.area, context)

    def _set_new_geotracker(self, area, num=None):
        _log_output(f'_set_new_geotracker: area={id(area)} num={num}')
        settings = get_gt_settings()
        if num is not None:
            settings.change_current_geotracker(num)
        geotracker = settings.get_current_geotracker_item()

        set_background_image_by_movieclip(geotracker.camobj,
                                          geotracker.movie_clip)

        GTLoader.place_object_or_camera()
        switch_to_camera(area, geotracker.camobj,
                         geotracker.animatable_object())

        hide_viewport_ui_elements_and_store_on_object(area, geotracker.geomobj)

    def _switch_to_new_geotracker(self, num):
        _log_output('_switch_to_new_geotracker')
        settings = get_gt_settings()
        settings.pinmode = True

        area = GTLoader.get_work_area()
        old_geotracker = settings.get_current_geotracker_item()
        unhide_viewport_ui_elements_from_object(area, old_geotracker.geomobj)

        self._set_new_geotracker(area, num)
        self._init_pinmode(area)

    def invoke(self, context, event):
        _log_output(f'INVOKE PINMODE: {self.geotracker_num}')

        settings = get_gt_settings()
        settings.fix_geotrackers()
        old_geotracker_num = settings.current_geotracker_num
        new_geotracker_num = old_geotracker_num if \
            self.geotracker_num == -1 else self.geotracker_num

        if not settings.is_proper_geotracker_number(new_geotracker_num):
            _log_error(f'WRONG GEOTRACKER NUMBER: {new_geotracker_num}')
            return {'CANCELLED'}

        vp = GTLoader.viewport()
        vp.pins().on_start()

        if settings.pinmode and not vp.is_working():
            _log_error(f'VIEWPORT DOES NOT WORK IN PINMODE -- FIX IT')
            settings.pinmode = False

        if settings.pinmode and old_geotracker_num == new_geotracker_num and vp.is_working():
            _log_output(f'SAME GEOTRACKER. NOTHING TO DO: {new_geotracker_num}')
            return {'CANCELLED'}

        new_geotracker = settings.get_geotracker_item(new_geotracker_num)

        if not new_geotracker.geomobj:
            _log_error(f'NO GEOMETRY OBJECT: {new_geotracker_num}')
            return {'CANCELLED'}

        if not new_geotracker.camobj:
            _log_error(f'NO CAMERA OBJECT: {new_geotracker_num}')
            return {'CANCELLED'}

        _log_output('GEOTRACKER PINMODE CHECKS PASSED')

        fit_render_size(new_geotracker.movie_clip)
        if settings.pinmode:
            self._switch_to_new_geotracker(new_geotracker_num)
            return {'FINISHED'}

        settings.change_current_geotracker(new_geotracker_num)
        _log_output(f'START GEOTRACKER PINMODE: {new_geotracker_num}')

        self._start_new_pinmode(context)
        GTLoader.start_shader_timer(settings.pinmode_id)
        context.window_manager.modal_handler_add(self)
        GTLoader.register_undo_redo_handlers()
        _log_output('PINMODE STARTED')
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        settings = get_gt_settings()

        if self.pinmode_id != settings.pinmode_id:
            _log_error('Extreme GeoTracker pinmode operator stop')
            _log_error('{} != {}'.format(self.pinmode_id, settings.pinmode_id))
            return {'FINISHED'}

        if not context.space_data:
            _log_output('VIEWPORT IS CLOSED')
            GTLoader.out_pinmode()
            return {'FINISHED'}

        if context.space_data.region_3d.view_perspective != 'CAMERA':
            if GTConfig.prevent_view_rotation:
                # Return back to the camera view
                bpy.ops.view3d.view_camera()
            else:
                _log_output('CAMERA ROTATED PINMODE OUT')
                GTLoader.out_pinmode()
                return {'FINISHED'}

        if event.type in {'LEFT_SHIFT', 'RIGHT_SHIFT'} \
                and event.value == 'PRESS':
            self._set_shift_pressed(True)
            if not settings.selection_mode:
                vp = GTLoader.viewport()
                vp.pins().set_add_selection_mode(True)

        if event.type in {'LEFT_SHIFT', 'RIGHT_SHIFT'} \
                and event.value == 'RELEASE':
            self._set_shift_pressed(False)
            if not settings.selection_mode:
                vp = GTLoader.viewport()
                vp.pins().set_add_selection_mode(False)

        if settings.selection_mode:
            if event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
                settings.end_selection(context.area, event.mouse_region_x, event.mouse_region_y)
            else:
                settings.do_selection(event.mouse_region_x, event.mouse_region_y)
            vp = GTLoader.viewport()
            vp.tag_redraw()
            return {'RUNNING_MODAL'}

        if event.type == 'ESC' and event.value == 'PRESS':
            if settings.selection_mode:
                settings.cancel_selection()
                vp = GTLoader.viewport()
                vp.tag_redraw()
                return {'RUNNING_MODAL'}
            if not bpy.app.background and bpy.context.screen.is_animation_playing:
                _log_output('STOP ANIMATION PLAYBACK')
                return {'PASS_THROUGH'}
            _log_output('Exit pinmode by ESC')
            GTLoader.out_pinmode()
            return {'FINISHED'}

        if GTLoader.geomobj_mode_changed_to_object():
            _log_output('RETURNED TO OBJECT_MODE')
            GTLoader.save_geotracker()
            GTLoader.load_geotracker()
            GTLoader.update_all_viewport_shaders(context.area)
            return {'PASS_THROUGH'}

        if event.type == 'TIMER' and GTLoader.get_stored_geomobj_mode() == 'EDIT':
            _log_output('TIMER IN EDIT_MODE')
            GTLoader.update_geomobj_mesh()
            GTLoader.save_geotracker()
            GTLoader.load_geotracker()
            GTLoader.update_all_viewport_shaders(context.area)
            return {'PASS_THROUGH'}

        if self._check_camera_state_changed(context.space_data.region_3d) or event.type == 'TIMER':
            if event.type != 'TIMER':
                _log_output('FORCE TAG REDRAW BY VIEWPORT ZOOM/OFFSET')
            vp = GTLoader.viewport()
            vp.create_batch_2d(context.area)
            vp.update_residuals(GTLoader.kt_geotracker(), context.area,
                                bpy_current_frame())
            vp.tag_redraw()

        if event.value == 'PRESS' and event.type == 'LEFTMOUSE':
            return self._on_left_mouse_press(context.area, event)

        if event.value == 'PRESS' and event.type == 'RIGHTMOUSE':
            return self._on_right_mouse_press(context.area, event)

        return {'PASS_THROUGH'}  # {'RUNNING_MODAL'}
