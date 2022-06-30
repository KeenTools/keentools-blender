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
from uuid import uuid4

import bpy

from ..addon_config import Config, get_operator, ErrorType
from ..geotracker_config import GTConfig, get_gt_settings
from .gtloader import GTLoader
from ..utils.localview import exit_area_localview
from ..utils import coords

from ..utils.manipulate import force_undo_push, switch_to_camera
from ..utils.other import (hide_viewport_ui_elements_and_store_on_object,
                           unhide_viewport_ui_elements_from_object)
from ..utils.images import set_background_image_by_movieclip
from ..utils.animation import create_locrot_keyframe


def depsgraph_update_handler(scene, depsgraph):
    def _check_updated(depsgraph, name):
        logger = logging.getLogger(__name__)
        log_output = logger.debug
        log_output('COUNT UPDATES: {}'.format(len(depsgraph.updates)))
        log_output('ids: {}'.format([update.id.name for update in depsgraph.updates]))
        for update in depsgraph.updates:
            if update.id.name != name:
                continue
            if not update.is_updated_transform:
                continue
            log_output(f'update.id: {update.id.name}')
            log_output(f'update.is_updated_geometry: {update.is_updated_geometry}')
            log_output(f'update.is_updated_transform: {update.is_updated_transform}')
            log_output(f'update.is_updated_shading: {update.is_updated_shading}')
            return True
        return False

    settings = get_gt_settings()
    if not settings.pinmode:
        unregister_undo_redo_handlers()
        return
    if settings.move_pin_mode:
        return
    geotracker = settings.get_current_geotracker_item()
    if not geotracker:
        return
    obj = geotracker.animatable_object()
    if not obj:
        return

    if _check_updated(depsgraph, obj.name):
        GTLoader.update_all_viewport_shaders()


def undo_redo_handler(scene):
    logger = logging.getLogger(__name__)
    logger.debug('gt_undo_handler')
    try:
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()
        vp = GTLoader.viewport()
        area = vp.get_work_area()
        if not settings.pinmode or not geotracker or not area:
            unregister_undo_redo_handlers()
            return

        GTLoader.load_geotracker()
        GTLoader.update_all_viewport_shaders(area)

    except Exception as err:
        logger.error('gt_undo_handler {}'.format(str(err)))
        unregister_undo_redo_handlers()


def unregister_depsgraph_update():
    unregister_app_handler(bpy.app.handlers.depsgraph_update_post,
                           depsgraph_update_handler)


def unregister_undo_redo_handlers():
    unregister_app_handler(bpy.app.handlers.undo_post, undo_redo_handler)
    unregister_app_handler(bpy.app.handlers.redo_post, undo_redo_handler)
    unregister_depsgraph_update()


def register_app_handler(app_handlers, handler):
    if handler is not None:
        if handler not in app_handlers:
            app_handlers.append(handler)


def unregister_app_handler(app_handlers, handler):
    if handler is not None:
        if handler in app_handlers:
            app_handlers.remove(handler)


def register_undo_redo_handlers():
    unregister_undo_redo_handlers()
    register_app_handler(bpy.app.handlers.undo_post, undo_redo_handler)
    register_app_handler(bpy.app.handlers.redo_post, undo_redo_handler)
    register_app_handler(bpy.app.handlers.depsgraph_update_post,
                         depsgraph_update_handler)


class GT_OT_PinMode(bpy.types.Operator):
    bl_idname = GTConfig.gt_pinmode_idname
    bl_label = 'GeoTracker Pinmode'
    bl_description = 'Operator for in-Viewport drawing'
    bl_options = {'REGISTER', 'INTERNAL'}

    geotracker_num: bpy.props.IntProperty(default=-1)

    pinmode_id: bpy.props.StringProperty(default='')
    pinmode_keyframe: bpy.props.IntProperty(default=-1)

    _shift_pressed = False
    _prev_camera_state = ()

    def _current_frame_updated(self):
        settings = get_gt_settings()
        keyframe = settings.current_frame()
        if keyframe != self.pinmode_keyframe:
            self.pinmode_keyframe = keyframe
            return True
        return False

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

    @classmethod
    def _exit_pinmode(cls):
        settings = get_gt_settings()
        settings.pinmode = False
        geotracker = settings.get_current_geotracker_item()
        geotracker.reset_focal_length_estimation()
        area = GTLoader.get_work_area()
        GTLoader.stop_viewport_shaders()
        exit_area_localview(area)
        if geotracker.geomobj:
            unhide_viewport_ui_elements_from_object(area, geotracker.geomobj)
        GTLoader.save_geotracker()
        unregister_undo_redo_handlers()

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
        settings = get_gt_settings()
        kid = settings.current_frame()

        gt = GTLoader.kt_geotracker()
        gt.remove_pin(nearest)
        del GTLoader.viewport().pins().arr()[nearest]
        logger = logging.getLogger(__name__)
        logging.debug('PIN REMOVED {}'.format(nearest))

        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return {'FINISHED'}

        gt = GTLoader.kt_geotracker()
        if not gt.is_key_at(kid):
            mat = GTLoader.calc_model_matrix()
            gt.set_keyframe(kid, mat)
            create_locrot_keyframe(geotracker.animatable_object(), 'KEYFRAME')
        if not GTLoader.solve(geotracker.focal_length_estimation):
            logger.error('DELETE PIN PROBLEM')
            return {'FINISHED'}

        GTLoader.load_pins_into_viewport()
        GTLoader.place_camera()

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
        logger = logging.getLogger(__name__)
        log_output = logger.debug
        if not GTLoader.load_geotracker():
            log_output('NEW KT_GEOTRACKER')
            GTLoader.new_kt_geotracker()

        log_output('START SHADERS')
        GTLoader.load_pins_into_viewport()
        vp = GTLoader.viewport()
        vp.create_batch_2d(area)
        log_output('REGISTER SHADER HANDLERS')
        GTLoader.update_all_viewport_shaders(area)
        if context is not None:
            vp.register_handlers(context)
        vp.tag_redraw()

    def _start_new_pinmode(self, context):
        logger = logging.getLogger(__name__)
        log_output = logger.debug
        log_output('_start_new_pinmode')
        settings = get_gt_settings()
        settings.pinmode = True
        self._new_pinmode_id()
        log_output(f'_new_pinmode_id: {settings.pinmode_id}')

        self._set_new_geotracker(context.area)
        self._init_pinmode(context.area, context)

    def _set_new_geotracker(self, area, num=None):
        logger = logging.getLogger(__name__)
        log_output = logger.debug
        log_output(f'_set_new_geotracker: area={id(area)} num={num}')
        settings = get_gt_settings()
        if num is not None:
            settings.change_current_geotracker(num)
        geotracker = settings.get_current_geotracker_item()

        set_background_image_by_movieclip(geotracker.camobj,
                                          geotracker.movie_clip)

        GTLoader.place_camera()
        switch_to_camera(area, geotracker.camobj,
                         geotracker.animatable_object())

        hide_viewport_ui_elements_and_store_on_object(area, geotracker.geomobj)

    def _switch_to_new_geotracker(self, num):
        logger = logging.getLogger(__name__)
        log_output = logger.debug
        log_output('_switch_to_new_geotracker')
        settings = get_gt_settings()
        settings.pinmode = True

        area = GTLoader.get_work_area()
        old_geotracker = settings.get_current_geotracker_item()
        unhide_viewport_ui_elements_from_object(area, old_geotracker.geomobj)

        self._set_new_geotracker(area, num)
        self._init_pinmode(area)

    def invoke(self, context, event):
        logger = logging.getLogger(__name__)
        log_output = logger.debug
        log_error = logger.error
        log_output(f'INVOKE PINMODE: {self.geotracker_num}')

        settings = get_gt_settings()
        old_geotracker_num = settings.current_geotracker_num
        new_geotracker_num = old_geotracker_num if \
            self.geotracker_num == -1 else self.geotracker_num

        if not settings.is_proper_geotracker_number(new_geotracker_num):
            log_error(f'WRONG GEOTRACKER NUMBER: {new_geotracker_num}')
            return {'CANCELLED'}

        vp = GTLoader.viewport()

        if settings.pinmode and not vp.is_working():
            log_error(f'VIEWPORT DOES NOT WORK IN PINMODE -- FIX IT')
            settings.pinmode = False

        if settings.pinmode and old_geotracker_num == new_geotracker_num and vp.is_working():
            log_output(f'SAME GEOTRACKER. NOTHING TO DO: {new_geotracker_num}')
            return {'CANCELLED'}

        new_geotracker = settings.get_geotracker_item(new_geotracker_num)

        if not new_geotracker.geomobj:
            log_error(f'NO GEOMETRY OBJECT: {new_geotracker_num}')
            return {'CANCELLED'}

        if not new_geotracker.camobj:
            log_error(f'NO CAMERA OBJECT: {new_geotracker_num}')
            return {'CANCELLED'}

        log_output('GEOTRACKER PINMODE CHECKS PASSED')

        if settings.pinmode:
            self._switch_to_new_geotracker(new_geotracker_num)
            return {'FINISHED'}

        settings.change_current_geotracker(new_geotracker_num)
        log_output(f'START GEOTRACKER PINMODE: {new_geotracker_num}')

        self._start_new_pinmode(context)
        GTLoader.start_shader_timer(settings.pinmode_id)
        context.window_manager.modal_handler_add(self)
        register_undo_redo_handlers()
        log_output('PINMODE STARTED')
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        logger = logging.getLogger(__name__)
        log_output = logger.debug
        log_error = logger.error
        settings = get_gt_settings()

        if self.pinmode_id != settings.pinmode_id:
            log_error('Extreme GeoTracker pinmode operator stop')
            log_error('{} != {}'.format(self.pinmode_id, settings.pinmode_id))
            return {'FINISHED'}

        if not context.space_data:
            log_output('VIEWPORT IS CLOSED')
            self._exit_pinmode()
            return {'FINISHED'}

        if context.space_data.region_3d.view_perspective != 'CAMERA':
            if GTConfig.prevent_view_rotation:
                # Return back to the camera view
                bpy.ops.view3d.view_camera()
            else:
                log_output('CAMERA ROTATED PINMODE OUT')
                self._exit_pinmode()
                return {'FINISHED'}

        if settings.force_out_pinmode:
            logger.debug('GT FORCE PINMODE OUT')
            self._exit_pinmode()
            settings.force_out_pinmode = False
            if settings.license_error:
                warn = get_operator(Config.kt_warning_idname)
                warn('INVOKE_DEFAULT', msg=ErrorType.NoLicense)
                settings.license_error = False
                settings.hide_user_preferences()
            return {'FINISHED'}

        if event.type in {'LEFT_SHIFT', 'RIGHT_SHIFT'} \
                and event.value == 'PRESS':
            self._set_shift_pressed(True)

        if event.type in {'LEFT_SHIFT', 'RIGHT_SHIFT'} \
                and event.value == 'RELEASE':
            self._set_shift_pressed(False)

        if settings.selection_mode:
            if (event.type == 'ESC' and event.value == 'RELEASE') or \
                    (event.type == 'LEFTMOUSE' and event.value == 'RELEASE'):
                settings.end_selection()
            else:
                settings.do_selection(event.mouse_region_x, event.mouse_region_y)
            vp = GTLoader.viewport()
            vp.tag_redraw()
            return {'RUNNING_MODAL'}

        if event.type == 'ESC' and event.value == 'RELEASE':
            log_output('Exit pinmode by ESC')
            self._exit_pinmode()
            return {'FINISHED'}

        if self._current_frame_updated():
            geotracker = settings.get_current_geotracker_item()
            geotracker.reset_focal_length_estimation()
            log_output('KEYFRAME UPDATED')
            coords.update_depsgraph()
            GTLoader.place_camera()
            GTLoader.update_all_viewport_shaders(context.area)
            vp = GTLoader.viewport()
            vp.tag_redraw()
            return {'PASS_THROUGH'}

        if GTLoader.geomobj_mode_changed_to_object():
            log_output('RETURNED TO OBJECT_MODE')
            GTLoader.save_geotracker()
            GTLoader.load_geotracker()
            GTLoader.update_all_viewport_shaders(context.area)
            return {'PASS_THROUGH'}

        if event.type == 'TIMER' and GTLoader.get_stored_geomobj_mode() == 'EDIT':
            log_output('TIMER IN EDIT_MODE')
            GTLoader.update_geomobj_mesh()
            GTLoader.save_geotracker()
            GTLoader.load_geotracker()
            GTLoader.update_all_viewport_shaders(context.area)
            return {'PASS_THROUGH'}

        if self._check_camera_state_changed(context.space_data.region_3d):
            log_output('FORCE TAG REDRAW BY VIEWPORT ZOOM/OFFSET')
            vp = GTLoader.viewport()
            vp.create_batch_2d(context.area)
            vp.update_residuals(GTLoader.kt_geotracker(), context.area,
                                settings.current_frame())
            vp.tag_redraw()

        if event.value == 'PRESS' and event.type == 'LEFTMOUSE':
            return self._on_left_mouse_press(context.area, event)

        if event.value == 'PRESS' and event.type == 'RIGHTMOUSE':
            return self._on_right_mouse_press(context.area, event)

        return {'PASS_THROUGH'}  # {'RUNNING_MODAL'}
