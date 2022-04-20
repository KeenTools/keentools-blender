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

from ..addon_config import get_operator
from ..geotracker_config import GTConfig, get_gt_settings
from .gtloader import GTLoader
from ..utils.manipulate import exit_context_localview, set_overlays
from ..utils import coords
from .utils.animation import create_locrot_keyframe
from ..utils.other import unhide_viewport_ui_element_from_object


class GT_OT_PinMode(bpy.types.Operator):
    bl_idname = GTConfig.gt_pinmode_idname
    bl_label = 'GeoTracker Pinmode'
    bl_description = 'Operator for in-Viewport drawing'
    bl_options = {'REGISTER', 'INTERNAL'}

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
    def _exit_pinmode(cls, context):
        settings = get_gt_settings()
        settings.pinmode = False
        geotracker = settings.get_current_geotracker_item()
        geotracker.reset_focal_length_estimation()
        vp = GTLoader.viewport()
        vp.unregister_handlers()
        exit_context_localview(context)
        if geotracker.geomobj:
            unhide_viewport_ui_element_from_object(geotracker.geomobj)
        GTLoader.save_geotracker()

    def _on_left_mouse_press(self, context, event):
        mouse_x, mouse_y = event.mouse_region_x, event.mouse_region_y
        GTLoader.viewport().update_view_relative_pixel_size(context)

        if not coords.is_in_area(context, mouse_x, mouse_y):
            return {'PASS_THROUGH'}

        if coords.is_safe_region(context, mouse_x, mouse_y):
            op = get_operator(GTConfig.gt_movepin_idname)
            op('INVOKE_DEFAULT', pinx=mouse_x, piny=mouse_y)
            return {'PASS_THROUGH'}

        return {'PASS_THROUGH'}

    def _on_right_mouse_press(self, context, event):
        mouse_x, mouse_y = event.mouse_region_x, event.mouse_region_y
        vp = GTLoader.viewport()
        vp.update_view_relative_pixel_size(context)

        x, y = coords.get_image_space_coord(mouse_x, mouse_y, context)

        nearest, dist2 = coords.nearest_point(x, y, vp.pins().arr())
        if nearest >= 0 and dist2 < vp.tolerance_dist2():
            return self._delete_found_pin(nearest, context)

        vp.create_batch_2d(context)
        return {"RUNNING_MODAL"}

    def _delete_found_pin(self, nearest, context):
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

        if not GTLoader.solve(geotracker.focal_length_estimation):
            logger.error('DELETE PIN PROBLEM')
            return {'FINISHED'}

        GTLoader.load_pins_into_viewport()
        GTLoader.place_camera()

        vp = GTLoader.viewport()
        vp.update_surface_points(gt, geotracker.geomobj, kid)

        if not geotracker.solve_for_camera_mode():
            wf = vp.wireframer()
            wf.init_geom_data_from_mesh(geotracker.geomobj)
            wf.create_batches()

        vp.create_batch_2d(context)
        vp.update_residuals(gt, context, kid)

        GTLoader.tag_redraw(context)

        return {"RUNNING_MODAL"}

    def invoke(self, context, event):
        logger = logging.getLogger(__name__)
        settings = get_gt_settings()

        logger.debug('GEOTRACKER PINMODE ENTER')

        vp = GTLoader.viewport()
        if settings.pinmode:
            vp.unregister_handlers()

        settings.pinmode = True
        self.pinmode_id = str(uuid4())
        settings.pinmode_id = self.pinmode_id

        if not GTLoader.load_geotracker():
            GTLoader.new_kt_geotracker()

        logger.debug('START SHADERS')
        GTLoader.load_pins_into_viewport()
        vp.create_batch_2d(context)
        logger.debug('REGISTER SHADER HANDLERS')
        GTLoader.update_all_viewport_shaders(context)
        vp.register_handlers(context)

        GTLoader.store_geomobj_world_matrix(*GTLoader.get_geomobj_world_matrix())

        context.window_manager.modal_handler_add(self)

        logger.debug('PINMODE STARTED')
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        logger = logging.getLogger(__name__)
        settings = get_gt_settings()

        if self.pinmode_id != settings.pinmode_id:
            logger.error('Extreme GeoTracker pinmode operator stop')
            logger.error('{} != {}'.format(self.pinmode_id, settings.pinmode_id))
            return {'FINISHED'}

        if not context.space_data:
            logger.debug('VIEWPORT IS CLOSED')
            self._exit_pinmode(context)
            return {'FINISHED'}

        if context.space_data.region_3d.view_perspective != 'CAMERA':
            logger.debug('CAMERA ROTATED PINMODE OUT')
            self._exit_pinmode(context)
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
            GTLoader.tag_redraw(context)
            return {'RUNNING_MODAL'}

        if event.type == 'ESC' and event.value == 'RELEASE':
            logger.debug('Exit pinmode by ESC')
            self._exit_pinmode(context)
            return {'FINISHED'}

        if self._current_frame_updated():
            geotracker = settings.get_current_geotracker_item()
            geotracker.reset_focal_length_estimation()
            logger.debug('KEYFRAME UPDATED')
            coords.update_depsgraph()
            GTLoader.place_camera()
            GTLoader.update_all_viewport_shaders(context)
            GTLoader.geomobj_world_matrix_changed(update=True)
            GTLoader.tag_redraw(context)
            return {'PASS_THROUGH'}

        if GTLoader.geomobj_mode_changed_to_object():
            logger.debug('RETURNED TO OBJECT_MODE')
            GTLoader.save_geotracker()
            GTLoader.load_geotracker()
            GTLoader.update_all_viewport_shaders(context)
            return {'PASS_THROUGH'}

        if event.type == 'TIMER' and GTLoader.get_stored_geomobj_mode() == 'EDIT':
            logger.debug('TIMER IN EDIT_MODE')
            GTLoader.update_geomobj_mesh()
            GTLoader.save_geotracker()
            GTLoader.load_geotracker()
            GTLoader.update_all_viewport_shaders(context)
            return {'PASS_THROUGH'}

        if self._check_camera_state_changed(context.space_data.region_3d):
            logger.debug('FORCE TAG REDRAW BY VIEWPORT ZOOM/OFFSET')
            vp = GTLoader.viewport()
            vp.create_batch_2d(context)
            vp.update_residuals(GTLoader.kt_geotracker(), context,
                                settings.current_frame())
            GTLoader.tag_redraw(context)

        if GTLoader.geomobj_world_matrix_changed(update=True) is True and not settings.pin_move_mode:
            logger.debug('GEOMOBJ MOVED')
            GTLoader.safe_keyframe_add(settings.current_frame(),
                                       GTLoader.calc_model_matrix())
            GTLoader.save_geotracker()
            geotracker = settings.get_current_geotracker_item()
            create_locrot_keyframe(geotracker.geomobj, 'KEYFRAME')

            GTLoader.load_geotracker()
            GTLoader.update_all_viewport_shaders(context)
            GTLoader.tag_redraw(context)

        if event.value == 'PRESS' and event.type == 'LEFTMOUSE':
            return self._on_left_mouse_press(context, event)

        if event.value == 'PRESS' and event.type == 'RIGHTMOUSE':
            return self._on_right_mouse_press(context, event)

        return {'PASS_THROUGH'}  # {'RUNNING_MODAL'}
