# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2022 KeenTools

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

from typing import List
from math import radians
import platform
from urllib.parse import urlencode

from bpy.types import Operator, Object
from bpy.props import (BoolProperty,
                       IntProperty,
                       FloatProperty,
                       FloatVectorProperty,
                       StringProperty,
                       EnumProperty,
                       PointerProperty)
from mathutils import Matrix, Quaternion

from ..utils.kt_logging import KTLogger
from ..utils.version import BVersion
from ..addon_config import (Config,
                            gt_settings,
                            get_settings,
                            product_name,
                            get_operator,
                            ProductType,
                            show_user_preferences,
                            show_tool_preferences)
from ..geotracker_config import GTConfig
from ..utils.bpy_common import (bpy_current_frame,
                                bpy_set_current_frame,
                                bpy_start_frame,
                                bpy_end_frame,
                                bpy_background_mode,
                                bpy_show_addon_preferences,
                                bpy_scene,
                                create_empty_object,
                                bpy_remove_object,
                                bpy_url_open)
from ..tracker.calc_timer import TrackTimer, RefineTimer

from .utils.precalc import precalc_with_runner_act, PrecalcTimer
from .gtloader import GTLoader
from .ui_strings import buttons
from .utils.prechecks import common_checks
from ..utils.coords import LocRotScale
from ..utils.manipulate import select_object_only, force_undo_push
from ..utils.animation import count_fcurve_points, remove_fcurve_from_object
from .interface.screen_mesages import (revert_default_screen_message,
                                       single_line_screen_message)
from ..utils.images import (remove_bpy_image_by_name,
                            check_background_image_absent_frames)
from ..utils.materials import remove_mat_by_name
from .utils.geotracker_acts import (create_geotracker_action,
                                    delete_tracker_action,
                                    add_keyframe_action,
                                    remove_keyframe_action,
                                    prev_keyframe_action,
                                    next_keyframe_action,
                                    toggle_lock_view_action,
                                    track_to,
                                    track_next_frame_action,
                                    refine_async_action,
                                    refine_all_async_action,
                                    clear_between_keyframes_action,
                                    clear_direction_action,
                                    clear_all_action,
                                    clear_all_except_keyframes_action,
                                    remove_pins_action,
                                    toggle_pins_action,
                                    center_geo_action,
                                    create_animated_empty_action,
                                    create_empty_from_selected_pins_action,
                                    bake_texture_from_frames_action,
                                    transfer_tracking_to_camera_action,
                                    transfer_tracking_to_geometry_action,
                                    remove_focal_keyframe_action,
                                    remove_focal_keyframes_action,
                                    select_tracker_objects_action,
                                    render_with_background_action,
                                    revert_default_render_action,
                                    store_camobj_state,
                                    store_geomobj_state,
                                    get_stored_data,
                                    scale_scene_tracking_preview_func,
                                    revert_object_states,
                                    scale_scene_tracking_action,
                                    scale_scene_trajectory_act,
                                    check_uv_exists,
                                    check_uv_overlapping_with_status,
                                    create_non_overlapping_uv_action,
                                    repack_uv_action,
                                    bake_locrot_action,
                                    get_operator_reposition_matrix,
                                    move_scene_tracking_action,
                                    unbreak_rotation_act)


_log = KTLogger(__name__)


class ButtonOperator:
    bl_options = {'REGISTER', 'UNDO'}

    def draw(self, context):
        pass


class GT_OT_CreateGeoTracker(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_create_geotracker_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        act_status = create_geotracker_action()
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class GT_OT_DeleteGeoTracker(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_delete_geotracker_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    geotracker_num: IntProperty(default=-1)

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        product = ProductType.GEOTRACKER
        act_status = delete_tracker_action(self.geotracker_num,
                                           product=product)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class GT_OT_SwitchToCameraMode(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_switch_to_camera_mode_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        product = ProductType.GEOTRACKER
        check_status = common_checks(product=product,
                                     object_mode=False, is_calculating=True,
                                     reload_geotracker=False, geotracker=True,
                                     camera=False, geometry=False,
                                     movie_clip=False)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        settings = gt_settings()
        geotracker = settings.get_current_geotracker_item()
        geotracker.solve_for_camera = True
        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class GT_OT_SwitchToGeometryMode(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_switch_to_geometry_mode_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        product = ProductType.GEOTRACKER
        check_status = common_checks(product=product,
                                     object_mode=False, is_calculating=True,
                                     reload_geotracker=False, geotracker=True,
                                     camera=False, geometry=False,
                                     movie_clip=False)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        settings = gt_settings()
        geotracker = settings.get_current_geotracker_item()
        geotracker.solve_for_camera = False
        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class GT_OT_CreatePrecalc(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_create_precalc_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    product: IntProperty(default=ProductType.UNDEFINED)

    def execute(self, context):
        _log.output(f'{self.__class__.__name__} execute '
                    f'[{product_name(self.product)}]')
        check_status = common_checks(product=self.product,
                                     object_mode=False, is_calculating=True,
                                     reload_geotracker=False, geotracker=True,
                                     camera=True, geometry=False,
                                     movie_clip=True)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        act_status = precalc_with_runner_act(context, product=self.product)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class GT_OT_PrevKeyframe(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_prev_keyframe_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        product = ProductType.GEOTRACKER
        settings = gt_settings()
        check_status = common_checks(product=product,
                                     object_mode=False, is_calculating=True,
                                     reload_geotracker=not settings.pinmode,
                                     geotracker=True, camera=True,
                                     geometry=True)
        if not check_status.success:
            self.report({'INFO'}, check_status.error_message)
            return {'CANCELLED'}

        settings.calculating_mode = 'JUMP'
        act_status = prev_keyframe_action(product=product)
        settings.stop_calculating()
        if not act_status.success:
            self.report({'INFO'}, act_status.error_message)
            return {'CANCELLED'}

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class GT_OT_NextKeyframe(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_next_keyframe_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        product = ProductType.GEOTRACKER
        settings = gt_settings()
        check_status = common_checks(product=product,
                                     object_mode=False, is_calculating=True,
                                     reload_geotracker=not settings.pinmode,
                                     geotracker=True, camera=True,
                                     geometry=True)
        if not check_status.success:
            self.report({'INFO'}, check_status.error_message)
            return {'CANCELLED'}

        settings.calculating_mode = 'JUMP'
        act_status = next_keyframe_action(product=product)
        settings.stop_calculating()
        if not act_status.success:
            self.report({'INFO'}, act_status.error_message)
            return {'CANCELLED'}

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class GT_OT_LockView(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_toggle_lock_view_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        product = ProductType.GEOTRACKER
        act_status = toggle_lock_view_action(product=product)
        if not act_status.success:
            self.report({'INFO'}, act_status.error_message)
            return {'CANCELLED'}

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class GT_OT_TrackToStart(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_track_to_start_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        product = ProductType.GEOTRACKER
        act_status = track_to(forward=False, product=product)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class GT_OT_TrackToEnd(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_track_to_end_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        product = ProductType.GEOTRACKER
        act_status = track_to(forward=True, product=product)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class GT_OT_TrackNext(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_track_next_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        product = ProductType.GEOTRACKER
        act_status = track_next_frame_action(forward=True, product=product)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class GT_OT_TrackPrev(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_track_prev_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        product = ProductType.GEOTRACKER
        act_status = track_next_frame_action(forward=False, product=product)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class GT_OT_AddKeyframe(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_add_keyframe_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER'}

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        product = ProductType.GEOTRACKER
        act_status = add_keyframe_action(product=product)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        GTLoader.update_viewport_shaders(timeline=True)
        force_undo_push('Add GeoTracker keyframe')
        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class GT_OT_RemoveKeyframe(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_remove_keyframe_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER'}

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        product = ProductType.GEOTRACKER
        act_status = remove_keyframe_action(product=product)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        GTLoader.update_viewport_shaders(timeline=True)
        force_undo_push('Remove GeoTracker keyframe')
        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class GT_OT_ClearAllTracking(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_clear_all_tracking_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        product = ProductType.GEOTRACKER
        act_status = clear_all_action(product=product)
        GTLoader.update_viewport_shaders(timeline=True)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class GT_OT_ClearTrackingExceptKeyframes(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_clear_tracking_except_keyframes_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        product = ProductType.GEOTRACKER
        act_status = clear_all_except_keyframes_action(product=product)
        GTLoader.update_viewport_shaders(timeline=True)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class GT_OT_ClearTrackingForward(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_clear_tracking_forward_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        product = ProductType.GEOTRACKER
        act_status = clear_direction_action(forward=True, product=product)
        GTLoader.update_viewport_shaders(timeline=True)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class GT_OT_ClearTrackingBackward(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_clear_tracking_backward_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        product = ProductType.GEOTRACKER
        act_status = clear_direction_action(forward=False, product=product)
        GTLoader.update_viewport_shaders(timeline=True)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class GT_OT_ClearTrackingBetween(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_clear_tracking_between_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        product = ProductType.GEOTRACKER
        act_status = clear_between_keyframes_action(product=product)
        GTLoader.update_viewport_shaders(timeline=True)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class GT_OT_Refine(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_refine_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        product = ProductType.GEOTRACKER
        act_status = refine_async_action(product=product)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class GT_OT_RefineAll(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_refine_all_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        product = ProductType.GEOTRACKER
        act_status = refine_all_async_action(product=product)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class GT_OT_CenterGeo(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_center_geo_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        product = ProductType.GEOTRACKER
        act_status = center_geo_action(product=product)
        GTLoader.update_viewport_shaders(timeline=True, pins_and_residuals=True)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class GT_OT_BtnMagicKeyframe(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_magic_keyframe_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        op = get_operator(GTConfig.gt_actor_idname)
        op('EXEC_DEFAULT', action='magic_keyframe')
        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class GT_OT_RemovePins(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_remove_pins_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        product = ProductType.GEOTRACKER
        act_status = remove_pins_action(product=product)
        GTLoader.update_viewport_shaders(pins_and_residuals=True)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class GT_OT_TogglePins(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_toggle_pins_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        product = ProductType.GEOTRACKER
        act_status = toggle_pins_action(product=product)
        GTLoader.update_viewport_shaders(pins_and_residuals=True)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class GT_OT_ExportAnimatedEmpty(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_export_animated_empty_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    product: IntProperty(default=ProductType.UNDEFINED)

    def draw(self, context):
        return

    def invoke(self, context, event):
        _log.green(f'{self.__class__.__name__} invoke '
                   f'[{product_name(self.product)}]')

        check_status = common_checks(product=self.product,
                                     object_mode=True, is_calculating=True,
                                     geotracker=True)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        settings = get_settings(self.product)
        if settings.export_locator_selector == 'SELECTED_PINS':
            check_status = common_checks(product=self.product,
                                         pinmode=True, geotracker=True,
                                         geometry=True, camera=True,
                                         reload_geotracker=True)
            if not check_status.success:
                self.report({'ERROR'}, check_status.error_message)
                return {'CANCELLED'}

        _log.output(f'{self.__class__.__name__} invoke end >>>')
        return self.execute(context)

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute '
                   f'[{product_name(self.product)}]')
        settings = get_settings(self.product)
        geotracker = settings.get_current_geotracker_item()

        if settings.export_locator_selector == 'GEOMETRY':
            act_status = create_animated_empty_action(
                geotracker.geomobj, settings.export_linked_locator)
            if not act_status.success:
                self.report({'ERROR'}, act_status.error_message)
                return {'CANCELLED'}
            _log.output(f'{self.__class__.__name__} execute end >>>')
            return {'FINISHED'}

        elif settings.export_locator_selector == 'CAMERA':
            act_status = create_animated_empty_action(
                geotracker.camobj, settings.export_linked_locator)
            if not act_status.success:
                self.report({'ERROR'}, act_status.error_message)
                return {'CANCELLED'}
            _log.output(f'{self.__class__.__name__} execute end >>>')
            return {'FINISHED'}

        elif settings.export_locator_selector == 'SELECTED_PINS':
            if len(settings.loader().viewport().pins().get_selected_pins()) == 0:
                msg = 'No pins selected'
                _log.error(msg)
                self.report({'ERROR'}, msg)
                return {'CANCELLED'}

            act_status = create_empty_from_selected_pins_action(
                bpy_start_frame(), bpy_end_frame(),
                linked=settings.export_linked_locator,
                orientation=settings.export_locator_orientation,
                product=self.product)
            if not act_status.success:
                _log.error(act_status.error_message)
                self.report({'ERROR'}, act_status.error_message)
                return {'CANCELLED'}
            _log.output(f'{self.__class__.__name__} execute end >>>')
            return {'FINISHED'}

        msg = 'Unknown selector state'
        _log.error(msg)
        self.report({'ERROR'}, msg)
        return {'CANCELLED'}


class GT_OT_ExitPinMode(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_exit_pinmode_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        GTLoader.out_pinmode()
        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class GT_OT_StopCalculating(Operator):
    bl_idname = GTConfig.gt_stop_calculating_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    attempts: IntProperty(default=0)

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        settings = gt_settings()
        _log.output(f'StopCalculating btn: {settings.user_interrupts}')

        if not settings.user_interrupts:
            settings.user_interrupts = True
            self.attempts = 0
            _log.output(f'{self.__class__.__name__} execute end >>>')
            return {'FINISHED'}

        self.attempts += 1
        if self.attempts > 1:
            _log.error(f'Extreme calculation stop')
            settings.stop_calculating()
            self.attempts = 0
            _log.output(f'{self.__class__.__name__} execute end >>>')
            return {'FINISHED'}

        if settings.calculating_mode == 'PRECALC':
            _log.output(f'PrecalcTimer: {PrecalcTimer.active_timers()}')
            if len(PrecalcTimer.active_timers()) == 0:
                settings.stop_calculating()
        elif settings.calculating_mode == 'TRACKING':
            _log.output(f'TrackTimer: {TrackTimer.active_timers()}')
            if len(TrackTimer.active_timers()) == 0:
                settings.stop_calculating()
        elif settings.calculating_mode == 'REFINE':
            _log.output(f'RefineTimer: {RefineTimer.active_timers()}')
            if len(RefineTimer.active_timers()) == 0:
                settings.stop_calculating()

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class GT_OT_InterruptModal(Operator):
    bl_idname = GTConfig.gt_interrupt_modal_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'INTERNAL'}

    def invoke(self, context, event):
        _log.green(f'{self.__class__.__name__} invoke')
        settings = gt_settings()
        settings.user_interrupts = False

        if not bpy_background_mode():
            context.window_manager.modal_handler_add(self)
            _log.output('GT INTERRUPTOR START')
        else:
            _log.info('GeoTracker Interruptor skipped by background mode')
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        settings = gt_settings()

        if settings.user_interrupts:
            _log.output('GT Interruptor has been stopped by value')
            settings.user_interrupts = True
            _log.output(f'{self.__class__.__name__} execute end >>>')
            return {'FINISHED'}

        if event.type == 'ESC' and event.value == 'PRESS':
            _log.output('Exit GT Interruptor by ESC')
            settings.user_interrupts = True
            _log.output(f'{self.__class__.__name__} execute end >>>')
            return {'FINISHED'}

        return {'PASS_THROUGH'}


class GT_OT_ResetToneGain(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_reset_tone_exposure_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        settings = gt_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return {'CANCELLED'}
        geotracker.tone_exposure = Config.default_tone_exposure
        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class GT_OT_ResetToneGamma(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_reset_tone_gamma_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        settings = gt_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return {'CANCELLED'}
        geotracker.tone_gamma = Config.default_tone_gamma
        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class GT_OT_ResetToneMapping(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_reset_tone_mapping_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        settings = gt_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return {'CANCELLED'}
        geotracker.tone_exposure = Config.default_tone_exposure
        geotracker.tone_gamma = Config.default_tone_gamma
        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class GT_OT_ResetTextureResolution(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_reset_texture_resolution_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    product: IntProperty(default=ProductType.UNDEFINED)

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute '
                   f'[{product_name(self.product)}]')
        settings = get_settings(self.product)
        if not settings:
            return {'CANCELLED'}
        settings.tex_width = Config.default_tex_width
        settings.tex_height = Config.default_tex_height
        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class GT_OT_ResetTextureSettings(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_reset_advanced_settings_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    product: IntProperty(default=ProductType.UNDEFINED)

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute '
                   f'[{product_name(self.product)}]')
        settings = get_settings(self.product)
        if not settings:
            return {'CANCELLED'}
        settings.tex_face_angles_affection = Config.default_tex_face_angles_affection
        settings.tex_uv_expand_percents = Config.default_tex_uv_expand_percents
        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class GT_OT_DefaultWireframeSettings(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_default_wireframe_settings_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        settings = gt_settings()
        prefs = settings.preferences()
        settings.wireframe_color = prefs.gt_wireframe_color
        settings.wireframe_opacity = prefs.gt_wireframe_opacity
        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class GT_OT_DefaultPinSettings(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_default_pin_settings_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        settings = gt_settings()
        prefs = settings.preferences()
        settings.pin_size = prefs.pin_size
        settings.pin_sensitivity = prefs.pin_sensitivity
        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class GT_OT_CheckUVOverlapping(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_check_uv_overlapping_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    product: IntProperty(default=ProductType.UNDEFINED)

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute '
                   f'[{product_name(self.product)}]')
        check_status = common_checks(product=self.product,
                                     object_mode=True, is_calculating=True,
                                     reload_geotracker=True, geotracker=True,
                                     camera=True, geometry=True)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        settings = get_settings(self.product)
        geotracker = settings.get_current_geotracker_item()

        check_status = check_uv_exists(geotracker.geomobj)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        check_status = check_uv_overlapping_with_status(geotracker)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        self.report({'INFO'}, 'UV check success!')
        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class GT_OT_RepackOverlappingUV(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_repack_overlapping_uv_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    done: BoolProperty(default=False)
    product: IntProperty(default=ProductType.UNDEFINED)

    def cancel(self, context):
        _log.green(f'{self.__class__.__name__} cancel '
                   f'[{product_name(self.product)}]')
        self.done = True

    def draw(self, context):
        layout = self.layout
        if self.done:
            layout.label(text='Operation has been done')
            return

        warning_message = [
            f'Warning! There\'s a bug in Blender {BVersion.version_string} ',
            'that makes this operation unstable.',
            ' ',
            'If you continue, there\'s a chance Blender',
            'will crash and ALL UNSAVED DATA WILL BE LOST!',
            ' ',
            'Click outside of this window to cancel repack',
            'or press OK to continue at your own risk.']
        col = layout.column(align=True)
        col.scale_y = Config.text_scale_y
        for txt in warning_message:
            col.label(text=txt)

    def invoke(self, context, event):
        _log.green(f'{self.__class__.__name__} invoke '
                   f'[{product_name(self.product)}]')
        self.done = False
        if BVersion.pack_uv_problem_exists:
            return context.window_manager.invoke_props_dialog(self, width=400)
        return self.execute(context)

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute '
                   f'[{product_name(self.product)}]')
        self.done = True
        check_status = common_checks(product=self.product,
                                     pinmode_out=True,
                                     object_mode=False, is_calculating=True,
                                     reload_geotracker=True, geotracker=True,
                                     camera=True, geometry=True)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        act_status = repack_uv_action(product=self.product)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}

        settings = get_settings(self.product)
        geotracker = settings.get_current_geotracker_item()
        check_status = check_uv_overlapping_with_status(geotracker)
        if not check_status.success:
            self.report({'ERROR'}, f'Done but {check_status.error_message}')
            _log.output(f'{self.__class__.__name__} execute end >>>')
            return {'FINISHED'}

        self.report({'INFO'}, 'Non-overlapping UVs successfully created')
        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class GT_OT_CreateNonOverlappingUV(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_create_non_overlapping_uv_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    product: IntProperty(default=ProductType.UNDEFINED)

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute '
                   f'[{product_name(self.product)}]')
        check_status = common_checks(product=self.product,
                                     pinmode_out=True,
                                     object_mode=False, is_calculating=True,
                                     reload_geotracker=True, geotracker=True,
                                     camera=True, geometry=True)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        act_status = create_non_overlapping_uv_action(product=self.product)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        self.report({'INFO'}, 'Non-overlapping UVs successfully created')
        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


_overlapping_warning_message: List[str] = [
    'Warning: Overlapping UVs detected!',
    'This may result in artifacts in texture.',
    ' ',
    'Do you want to project texture without fixing UVs?']


class GT_OT_BakeFromSelected(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_bake_from_selected_frames_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    warning: BoolProperty(default=False)
    product: IntProperty(default=ProductType.UNDEFINED)

    def _draw_overlapping_warning(self, context):
        global _overlapping_warning_message
        layout = self.layout
        col = layout.column(align=True)
        col.scale_y = Config.text_scale_y
        for txt in _overlapping_warning_message:
            col.label(text=txt)

    def draw(self, context):
        layout = self.layout
        if self.warning:
            self._draw_overlapping_warning(context)
        else:
            layout.label(text='Operation has been done')

    def invoke(self, context, event):
        _log.green(f'{self.__class__.__name__} invoke '
                   f'product={product_name(self.product)}')
        self.warning = False
        check_status = common_checks(product=self.product,
                                     object_mode=True, is_calculating=True,
                                     reload_geotracker=True, geotracker=True,
                                     camera=True, geometry=True,
                                     movie_clip=True)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        settings = get_settings(self.product)
        geotracker = settings.get_current_geotracker_item()
        geotracker.geomobj.hide_set(False)

        check_status = check_uv_exists(geotracker.geomobj)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        if len(geotracker.selected_frames) == 0:
            self.report({'ERROR'}, 'No selected frames found')
            return {'CANCELLED'}

        check_status = check_uv_overlapping_with_status(geotracker)
        if not check_status.success:
            self.warning = True
            return context.window_manager.invoke_props_dialog(self, width=400)
        return self.execute(context)

    def start_text_on_screen(self, context):
        settings = get_settings(self.product)
        single_line_screen_message('Projecting and baking… Please wait',
                                   register=not settings.pinmode,
                                   context=context, product=self.product)

    def finish_text_on_screen(self):
        settings = get_settings(self.product)
        revert_default_screen_message(unregister=not settings.pinmode,
                                      product=self.product)

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        self.warning = False

        check_status = common_checks(product=self.product,
                                     object_mode=True, is_calculating=True,
                                     geotracker=True, camera=True,
                                     geometry=True, movie_clip=True)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        settings = get_settings(self.product)
        geotracker = settings.get_current_geotracker_item()
        selected_keyframes = [x.num for x in geotracker.selected_frames]
        if len(selected_keyframes) == 0:
            self.report({'ERROR'}, 'No frames have been selected')
            return {'CANCELLED'}

        _log.output('GT START TEXTURE CREATION')
        self.start_text_on_screen(context)
        act_status = bake_texture_from_frames_action(context.area,
                                                     selected_keyframes,
                                                     product=self.product)
        self.finish_text_on_screen()

        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            _log.output(f'{self.__class__.__name__} execute end 2')
            return {'FINISHED'}

        if settings.pinmode:
            settings.loader().out_pinmode()

        _log.output(f'{self.__class__.__name__} execute end 1')
        return {'FINISHED'}


class GT_OT_AddBakeFrame(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_add_bake_frame_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    product: IntProperty(default=ProductType.UNDEFINED)

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute '
                   f'product={product_name(self.product)}]')
        settings = get_settings(self.product)
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return {'CANCELLED'}

        frame = bpy_current_frame()
        res = check_background_image_absent_frames(geotracker.camobj, index=0,
                                                   frames=[frame])
        if len(res) > 0:
            msg = f'Frame [{frame}] is outside of Clip range'
            self.report({'ERROR'}, msg)
            return {'CANCELLED'}

        frames = [item.num for item in geotracker.selected_frames]
        if frame in frames:
            geotracker.selected_frame_index = frames.index(frame)
            return {'CANCELLED'}

        frames.append(frame)
        frames.sort()

        geotracker.selected_frames.clear()
        for i in frames:
            item = geotracker.selected_frames.add()
            item.num = i

        geotracker.selected_frame_index = frames.index(frame)

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class GT_OT_RemoveBakeFrame(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_remove_bake_frame_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    product: IntProperty(default=ProductType.UNDEFINED)

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute '
                   f'product={product_name(self.product)}]')
        settings = get_settings(self.product)
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return {'CANCELLED'}

        index = geotracker.selected_frame_index
        if index >= len(geotracker.selected_frames):
            return {'CANCELLED'}

        if index == len(geotracker.selected_frames) - 1:
            geotracker.selected_frame_index -= 1
        geotracker.selected_frames.remove(index)

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class GT_OT_GoToBakeFrame(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_go_to_bake_frame_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    num: IntProperty(default=0)

    product: IntProperty(default=ProductType.UNDEFINED)

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute '
                   f'product={product_name(self.product)}]')
        settings = get_settings(self.product)
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return {'CANCELLED'}

        index = self.num
        if index >= len(geotracker.selected_frames):
            return {'CANCELLED'}

        frame = geotracker.selected_frames[index].num
        bpy_set_current_frame(frame)
        geotracker.selected_frame_index = index

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class GT_OT_TransferTracking(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_transfer_tracking_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    product: IntProperty(default=ProductType.UNDEFINED)

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute '
                   f'[{product_name(self.product)}]')
        settings = get_settings(self.product)
        if settings.transfer_animation_selector == 'CAMERA_TO_GEOMETRY':
            act_status = transfer_tracking_to_geometry_action(product=self.product)
        elif settings.transfer_animation_selector == 'GEOMETRY_TO_CAMERA':
            act_status = transfer_tracking_to_camera_action(product=self.product)
        else:
            act_status = (False, 'Unknown selector state')

        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class GT_OT_BakeAnimationToWorld(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_bake_animation_to_world_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    product: IntProperty(default=ProductType.UNDEFINED)

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute '
                   f'[{product_name(self.product)}]')
        check_status = common_checks(product=self.product,
                                     object_mode=True, is_calculating=True,
                                     reload_geotracker=True, geotracker=True,
                                     camera=True, geometry=True,
                                     movie_clip=False)

        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        settings = get_settings(self.product)
        geotracker = settings.get_current_geotracker_item()

        if settings.bake_animation_selector == 'GEOMETRY':
            act_status = bake_locrot_action(geotracker.geomobj,
                                            product=self.product)
        elif settings.bake_animation_selector == 'CAMERA':
            act_status = bake_locrot_action(geotracker.camobj,
                                            product=self.product)
        elif settings.bake_animation_selector == 'GEOMETRY_AND_CAMERA':
            act_status = None
            if geotracker.geomobj and geotracker.geomobj.parent:
                act_status = bake_locrot_action(geotracker.geomobj,
                                                product=self.product)
            if act_status is None or (act_status.success and geotracker.camobj
                    and geotracker.camobj.parent):
                act_status = bake_locrot_action(geotracker.camobj,
                                                product=self.product)
            if act_status is None:
                self.report({'ERROR'}, 'Unknown error with both objects')
                return {'CANCELLED'}
        else:
            msg = f'Wrong bake selector identifier: ' \
                  f'{settings.bake_animation_selector}'
            self.report({'ERROR'}, msg)
            return {'CANCELLED'}

        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class GT_OT_RemoveFocalKeyframe(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_remove_focal_keyframe_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        product = ProductType.GEOTRACKER
        act_status = remove_focal_keyframe_action(product=product)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class GT_OT_RemoveFocalKeyframes(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_remove_focal_keyframes_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        product = ProductType.GEOTRACKER
        act_status = remove_focal_keyframes_action(product=product)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class GT_OT_SelectGeotrackerObjects(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_select_geotracker_objects_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    geotracker_num: IntProperty(default=0)

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        product = ProductType.GEOTRACKER
        act_status = select_tracker_objects_action(self.geotracker_num,
                                                   product=product)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class GT_OT_RenderWithBackground(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_render_with_background_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        product = ProductType.GEOTRACKER
        act_status = render_with_background_action(product=product)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class GT_OT_RevertDefaultRender(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_revert_default_render_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        product = ProductType.GEOTRACKER
        act_status = revert_default_render_action(product=product)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class GT_OT_AddonSetupDefaults(Operator):
    bl_idname = GTConfig.gt_addon_setup_defaults_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER'}

    def draw(self, context):
        pass

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        show_user_preferences(facebuilder=False, geotracker=True)
        show_tool_preferences(facebuilder=False, geotracker=True)
        bpy_show_addon_preferences()
        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class GT_OT_AutoNamePrecalc(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_auto_name_precalc_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        settings = gt_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker or not geotracker.movie_clip:
            self.report({'ERROR'}, 'No movie clip')
            return {'CANCELLED'}
        geotracker.precalc_path = f'{GTConfig.gt_precalc_folder}' \
                                  f'{geotracker.movie_clip.name}'
        status, msg, _ = geotracker.reload_precalc()
        if not status:
            _log.error(msg)
            self.report({'INFO'}, msg)

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class GT_OT_UnbreakRotation(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_unbreak_rotation_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    product: IntProperty(default=ProductType.UNDEFINED)

    def execute(self, context):
        _log.output(f'{self.__class__.__name__} execute '
                    f'[{product_name(self.product)}]')
        check_status = common_checks(product=self.product,
                                     object_mode=True, is_calculating=True,
                                     reload_geotracker=True, geotracker=True,
                                     camera=True, geometry=True)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        act_status = unbreak_rotation_act(product=self.product)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}

        self.report({'INFO'}, 'Unbreak Rotation has been done')
        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class GT_OT_DeleteTexture(Operator):
    bl_idname = GTConfig.gt_delete_texture_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'UNDO'}

    product: IntProperty(default=ProductType.UNDEFINED)

    def draw(self, context):
        pass

    def execute(self, context):
        _log.green(f'{self.__class__.__name__}.execute '
                   f'[{product_name(self.product)}]')
        settings = get_settings(self.product)
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return {'CANCELLED'}
        remove_bpy_image_by_name(geotracker.preview_texture_name())
        remove_mat_by_name(geotracker.preview_material_name())
        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


def _rescale_preview_func(operator, context):
    scale_scene_tracking_preview_func(operator, context)


def _update_rescale_mode(operator, context):
    if operator.mode == 'GEOMETRY':
        operator.origin_point = 'CAMERA'
        operator.keep_geom_scale = False
        operator.keep_cam_scale = True
    elif operator.mode == 'CAMERA':
        operator.origin_point = 'GEOMETRY'
        operator.keep_geom_scale = False
        operator.keep_cam_scale = True
    else:
        operator.keep_geom_scale = False
        operator.keep_cam_scale = True


def draw_constraint_warning_message(layout, warning_message):
    col = layout.column(align=True)
    col.scale_y = Config.text_scale_y
    col.alert = True
    col.label(text=warning_message)
    info = ['Objects with constraints can lead to unpredictable results.',
            'Click outside operator window to safe cancel this operation.']
    for txt in info:
        col.label(text=txt)


class GT_OT_RescaleWindow(Operator):
    bl_idname = GTConfig.gt_rescale_window_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'UNDO', 'REGISTER', 'INTERNAL'}

    mode: EnumProperty(name='Mode', items=[
        ('BOTH', 'Scene',
         'Scale both Camera and Geometry relative to pivot point', 0),
        ('GEOMETRY', 'Geometry',
         'Scale Geometry relative to Camera. '
         'Lock Camera scale and animation', 1),
        ('CAMERA', 'Camera',
         'Scale Camera relative to Geometry. '
         'Lock Geometry scale and animation', 2),
    ], update=_update_rescale_mode)

    value: FloatProperty(default=1.0, precision=4, min=0.0001,
                         update=_rescale_preview_func)
    geom_scale: FloatVectorProperty(default=(1, 1, 1))
    cam_scale:  FloatVectorProperty(default=(1, 1, 1))
    keep_cam_scale: BoolProperty(default=True,
                                 name='Lock Camera (visualization) scale',
                                 update=_rescale_preview_func)
    keep_geom_scale: BoolProperty(default=False, name='Lock Geometry scale',
                                  update=_rescale_preview_func)

    origin_point: EnumProperty(name='Pivot point', items=[
        ('WORLD', 'World Origin', 'Use world center (0, 0, 0)', 0),
        ('GEOMETRY', 'Geometry', 'Use Geometry pivot as center', 1),
        ('CAMERA', 'Camera', 'Use Camera pivot as center', 2),
        ('3D_CURSOR', '3D Cursor', 'Use 3D cursor', 3),
    ], update=_rescale_preview_func)

    done: BoolProperty(default=False)
    warning_message: StringProperty(default='')

    product: IntProperty(default=ProductType.UNDEFINED)

    def _draw_scale_slider(self, layout):
        row = layout.row()
        row.scale_y = 1.5
        row.prop(self, 'value', text='Scale:')

    def _draw_geometry_scale(self, layout):
        self._draw_scale_slider(layout)

    def _draw_camera_scale(self, layout):
        layout.prop(self, 'keep_cam_scale')
        self._draw_scale_slider(layout)

    def _draw_both_scale(self, layout):
        row = layout.split(factor=0.5)
        col = row.column(align=True)
        row2 = col.split(factor=0.4, align=True)
        row2.label(text='Pivot point:')
        row2.prop(self, 'origin_point', text='')

        col = row.column(align=True)
        col.prop(self, 'keep_cam_scale')
        col.prop(self, 'keep_geom_scale')

        self._draw_scale_slider(layout)

    def draw(self, context) -> None:
        layout = self.layout
        if self.done:
            layout.label(text='Operator has been done')
            return

        if self.warning_message != '':
            draw_constraint_warning_message(layout, self.warning_message)
        else:
            layout.separator()

        layout.prop(self, 'mode', expand=True)

        if self.mode == 'GEOMETRY':
            self._draw_geometry_scale(layout)
        elif self.mode == 'CAMERA':
            self._draw_camera_scale(layout)
        else:
            self._draw_both_scale(layout)

        layout.separator()

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute '
                   f'[{product_name(self.product)}]')
        self.done = True
        act_status = scale_scene_tracking_action(self, product=self.product)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}

    def cancel(self, context):
        _log.green(f'{self.__class__.__name__} cancel '
                   f'[{product_name(self.product)}]')
        self.done = True
        revert_object_states(product=self.product)

    def invoke(self, context, event):
        _log.output(f'{self.__class__.__name__} invoke '
                    f'[{product_name(self.product)}]')
        check_status = common_checks(product=self.product,
                                     object_mode=True, is_calculating=True,
                                     reload_geotracker=True, geotracker=True,
                                     camera=True, geometry=True,
                                     movie_clip=False)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        check_status = common_checks(product=self.product,
                                     constraints=True)
        self.warning_message = '' if check_status.success else \
            check_status.error_message

        settings = get_settings(self.product)
        geotracker = settings.get_current_geotracker_item()
        store_camobj_state(self, geotracker.camobj)
        store_geomobj_state(self, geotracker.geomobj)
        self.value = 1.0
        self.keep_cam_scale = True
        self.keep_geom_scale = False
        self.done = False
        return context.window_manager.invoke_props_dialog(self, width=400)


def _move_preview_func(operator, context):
    _log.output('_move_preview_func')
    settings = get_settings(operator.product)
    revert_object_states(product=operator.product)
    transform_matrix = get_operator_reposition_matrix(operator, product=operator.product)

    geotracker = settings.get_current_geotracker_item()
    geomobj = geotracker.geomobj
    camobj = geotracker.camobj

    geomobj.matrix_world = transform_matrix @ geomobj.matrix_world
    camobj.matrix_world = transform_matrix @ camobj.matrix_world


def _update_move_target_point(operator, context):
    _log.output('_update_move_target_point')
    if operator.no_updates:
        return
    operator.no_updates = True
    if operator.target_point == 'WORLD':
        operator.location = (0, 0, 0)
        operator.euler_rotation = (radians(90), 0, 0) \
            if operator.mode == 'CAMERA' else (0, 0, 0)
    elif operator.target_point == '3D_CURSOR':
        cursor = bpy_scene().cursor
        operator.location = cursor.location
        operator.euler_rotation = (0, 0, 0)
    operator.no_updates = False
    _move_preview_func(operator, context)


def _update_move_mode(operator, context):
    _log.output('_update_move_mode')
    if operator.no_updates:
        return
    mat = get_stored_data('camobj_matrix_world') if operator.mode == 'CAMERA' else \
        get_stored_data('geomobj_matrix_world')
    t, r, s = mat.decompose()
    operator.location = t
    operator.euler_rotation = r.to_euler()


def _update_move_coords(operator, context):
    _log.output('_update_move_coords')
    if operator.no_updates:
        return
    operator.target_point = 'CUSTOM'
    _move_preview_func(operator, context)


class GT_OT_MoveWindow(Operator):
    bl_idname = GTConfig.gt_move_window_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'UNDO', 'REGISTER', 'INTERNAL'}

    no_updates: BoolProperty(default=False)

    mode: EnumProperty(name='Mode', items=[
        ('CAMERA', 'by Camera', 'Origin point is Camera', 0),
        ('GEOMETRY', 'by Geometry', 'Origin point is Geometry', 1),
    ], update=_update_move_mode)

    target_point: EnumProperty(name='Target point', items=[
        ('WORLD', 'World Origin', 'Use world center', 0),
        ('3D_CURSOR', '3D Cursor', 'Use 3D cursor', 1),
        ('CUSTOM', 'Custom', 'Custom position', 2)
    ], update=_update_move_target_point)

    location: FloatVectorProperty(name='Location',
                                  subtype='TRANSLATION',
                                  update=_update_move_coords)
    euler_rotation: FloatVectorProperty(name='Rotation',
                                        subtype='EULER',
                                        update=_update_move_coords)
    done: BoolProperty(default=False)
    warning_message: StringProperty(default='')

    product: IntProperty(default=ProductType.UNDEFINED)

    def draw(self, context) -> None:
        layout = self.layout
        if self.done:
            layout.label(text='Operator has been done')
            return

        if self.warning_message != '':
            draw_constraint_warning_message(layout, self.warning_message)
        else:
            layout.separator()

        layout.prop(self, 'mode', expand=True)

        layout.prop(self, 'target_point', text='Preset')

        row = layout.row()
        col = row.column()
        col.prop(self, 'location')

        col = row.column()
        col.prop(self, 'euler_rotation')

        layout.separator()

    def execute(self, context):
        _log.output(f'{self.__class__.__name__} execute '
                    f'[{product_name(self.product)}]')
        self.done = True
        act_status = move_scene_tracking_action(self, product=self.product)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}

    def cancel(self, context):
        _log.green(f'{self.__class__.__name__} cancel '
                   f'[{product_name(self.product)}]')
        self.done = True
        revert_object_states(product=self.product)

    def invoke(self, context, event):
        _log.green(f'{self.__class__.__name__} invoke '
                   f'[{product_name(self.product)}]')
        check_status = common_checks(product=self.product,
                                     object_mode=True, is_calculating=True,
                                     reload_geotracker=True, geotracker=True,
                                     camera=True, geometry=True,
                                     movie_clip=False)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        check_status = common_checks(product=self.product,
                                     constraints=True)
        self.warning_message = '' if check_status.success else \
            check_status.error_message

        settings = get_settings(self.product)
        geotracker = settings.get_current_geotracker_item()
        store_camobj_state(self, geotracker.camobj)
        store_geomobj_state(self, geotracker.geomobj)

        _update_move_mode(self, context)
        self.done = False
        return context.window_manager.invoke_props_dialog(self, width=350)


_rig_empty = None


def _rig_preview_func(operator, context):
    settings = gt_settings()
    geotracker = settings.get_current_geotracker_item()

    mat = Matrix.Identity(4)
    if operator.target_point == 'GEOMETRY' and geotracker.geomobj:
        mat = geotracker.geomobj.matrix_world
    elif operator.target_point == 'CAMERA' and geotracker.camobj:
        mat = geotracker.camobj.matrix_world
    elif operator.target_point == '3D_CURSOR':
        mat = bpy_scene().cursor.matrix

    global _rig_empty
    if _rig_empty is None:
        return

    if not operator.reset_scale and operator.keep_orientation:
        _rig_empty.matrix_world = mat
        return

    t, r, s = mat.decompose()
    if operator.reset_scale:
        s = (1, 1, 1)
    if not operator.keep_orientation:
        r = Quaternion((1, 0, 0, 0))
    _rig_empty.matrix_world = LocRotScale(t, r, s)


class GT_OT_RigWindow(Operator):
    bl_idname = GTConfig.gt_rig_window_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'UNDO', 'REGISTER', 'INTERNAL'}

    target_point: EnumProperty(name='Target point', items=[
        ('WORLD', 'World Origin', 'Use world center', 0),
        ('CAMERA', 'Camera', 'Use Camera Origin', 1),
        ('GEOMETRY', 'Geometry', 'Use Geometry Origin', 2),
        ('3D_CURSOR', '3D Cursor', 'Use 3D cursor', 3),
    ], update=_rig_preview_func)

    reset_scale: BoolProperty(name='Reset Scale', default=True,
                              update=_rig_preview_func)
    keep_orientation: BoolProperty(name='Keep Orientation', default=True,
                                   update=_rig_preview_func)

    parent_geometry: BoolProperty(name='Parent Geometry', default=True)
    parent_camera: BoolProperty(name='Parent Camera', default=True)

    parent_camera_active: BoolProperty(default=True)
    parent_geometry_active: BoolProperty(default=True)
    done: BoolProperty(default=False)

    product: IntProperty(default=ProductType.UNDEFINED)

    def draw(self, context) -> None:
        layout = self.layout
        if self.done:
            layout.label(text='Operator has been done')
            return

        layout.separator()
        layout.prop(self, 'target_point', text='Empty location')

        row = layout.row()
        row.label(text='Match')
        row.prop(self, 'keep_orientation', text='Rotation')
        row.prop(self, 'reset_scale', text='Scale', invert_checkbox=True)

        row = layout.row()
        row.label(text='Parent')

        btn = row.column()
        btn.enabled = self.parent_geometry_active
        btn.prop(self, 'parent_geometry', text='Geometry')

        btn = row.column()
        btn.enabled = self.parent_camera_active
        btn.prop(self, 'parent_camera', text='Camera')

        if not self.parent_geometry_active or not self.parent_camera_active:
            box = layout.box()
            col = box.column()
            col.alert = True
            col.scale_y = Config.text_scale_y
            msg = ['Parenting disabled for already parented objects.',
                   'You can use \'Bake\' button to safely remove parenting.']
            for txt in msg:
                col.label(text=txt)

        layout.separator()

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute '
                   f'[{product_name(self.product)}]')
        self.done = True
        global _rig_empty

        if not _rig_empty:
            return {'CANCELLED'}

        if _rig_empty:
            _rig_empty.show_in_front = False
            _rig_empty.show_name = False

        settings = gt_settings()
        geotracker = settings.get_current_geotracker_item()

        objects = []
        if self.parent_camera and geotracker.camobj:
            objects.append(geotracker.camobj)
        if self.parent_geometry and geotracker.geomobj:
            objects.append(geotracker.geomobj)

        for obj in objects:
            obj.parent = _rig_empty
            obj.matrix_parent_inverse = _rig_empty.matrix_world.inverted()

        select_object_only(_rig_empty)
        if geotracker.geomobj:
            geotracker.geomobj.select_set(state=False)

        _rig_empty = None
        return {'FINISHED'}

    def cancel(self, context):
        _log.green(f'{self.__class__.__name__} cancel '
                   f'[{product_name(self.product)}]')
        self.done = True
        global _rig_empty
        if _rig_empty is None:
            return
        bpy_remove_object(_rig_empty)
        _rig_empty = None

    def _reset_to_default_options(self):
        self.reset_scale = True
        self.keep_orientation = True
        self.parent_geometry = True
        self.parent_geometry_active = True
        self.parent_camera = True
        self.parent_camera_active = True

    def invoke(self, context, event):
        _log.green(f'{self.__class__.__name__} invoke '
                   f'[{product_name(self.product)}]')
        check_status = common_checks(product=self.product,
                                     object_mode=True, is_calculating=True,
                                     reload_geotracker=True, geotracker=True)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        settings = get_settings(self.product)
        geotracker = settings.get_current_geotracker_item()

        global _rig_empty
        _rig_empty = create_empty_object(GTConfig.gt_empty_name)
        _rig_empty.show_in_front = True
        _rig_empty.show_name = True

        self._reset_to_default_options()
        if not geotracker.geomobj or geotracker.geomobj.parent:
            self.parent_geometry = False
            self.parent_geometry_active = False
        if not geotracker.camobj or geotracker.camobj.parent:
            self.parent_camera = False
            self.parent_camera_active = False

        self.done = False
        return context.window_manager.invoke_props_dialog(self, width=400)


class GT_OT_SwitchCameraToFixedWarning(Operator):
    bl_idname = GTConfig.gt_switch_camera_to_fixed_warning_idname
    bl_label = 'Remove focal length animation'
    bl_options = {'REGISTER', 'INTERNAL'}

    def draw(self, context) -> None:
        layout = self.layout
        col = layout.column(align=True)
        col.scale_y = Config.text_scale_y
        info = ['All your focal length animation will be lost!',
                'Do you really want to switch to Fixed mode?',
                ' ',
                'Click outside of this window to keep your animation data',
                'or press Ok to remove the animation data '
                'and switch to Fixed mode.']
        for txt in info:
            col.label(text=txt)

    def invoke(self, context, event):
        _log.green(f'{self.__class__.__name__} invoke')
        check_status = common_checks(product=ProductType.GEOTRACKER,
                                     is_calculating=True)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            self.cancel(context)
            return {'CANCELLED'}

        return context.window_manager.invoke_props_dialog(self, width=400)

    def cancel(self, context):
        _log.green(f'{self.__class__.__name__} cancel')
        settings = gt_settings()
        geotracker = settings.get_current_geotracker_item()
        with settings.ui_write_mode_context():
            geotracker.lens_mode = 'ZOOM'

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        settings = gt_settings()
        geotracker = settings.get_current_geotracker_item()
        if geotracker.camobj:
            remove_fcurve_from_object(geotracker.camobj.data, 'lens')

            if geotracker.focal_length_estimation:
                geotracker.focal_length_mode = 'STATIC_FOCAL_LENGTH'
            else:
                count = count_fcurve_points(geotracker.camobj.data, 'lens')
                if count > 0:
                    geotracker.focal_length_mode = 'STATIC_FOCAL_LENGTH'
                else:
                    geotracker.focal_length_mode = 'CAMERA_FOCAL_LENGTH'

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


BUTTON_CLASSES = (GT_OT_CreateGeoTracker,
                  GT_OT_DeleteGeoTracker,
                  GT_OT_SwitchToCameraMode,
                  GT_OT_SwitchToGeometryMode,
                  GT_OT_CreatePrecalc,
                  GT_OT_AddKeyframe,
                  GT_OT_RemoveKeyframe,
                  GT_OT_NextKeyframe,
                  GT_OT_PrevKeyframe,
                  GT_OT_LockView,
                  GT_OT_TrackToStart,
                  GT_OT_TrackPrev,
                  GT_OT_TrackNext,
                  GT_OT_TrackToEnd,
                  GT_OT_ClearAllTracking,
                  GT_OT_ClearTrackingExceptKeyframes,
                  GT_OT_ClearTrackingForward,
                  GT_OT_ClearTrackingBackward,
                  GT_OT_ClearTrackingBetween,
                  GT_OT_Refine,
                  GT_OT_RefineAll,
                  GT_OT_CenterGeo,
                  GT_OT_BtnMagicKeyframe,
                  GT_OT_RemovePins,
                  GT_OT_TogglePins,
                  GT_OT_ExportAnimatedEmpty,
                  GT_OT_ExitPinMode,
                  GT_OT_InterruptModal,
                  GT_OT_StopCalculating,
                  GT_OT_ResetToneGain,
                  GT_OT_ResetToneGamma,
                  GT_OT_ResetToneMapping,
                  GT_OT_ResetTextureResolution,
                  GT_OT_ResetTextureSettings,
                  GT_OT_DefaultWireframeSettings,
                  GT_OT_DefaultPinSettings,
                  GT_OT_CheckUVOverlapping,
                  GT_OT_RepackOverlappingUV,
                  GT_OT_CreateNonOverlappingUV,
                  GT_OT_BakeFromSelected,
                  GT_OT_AddBakeFrame,
                  GT_OT_RemoveBakeFrame,
                  GT_OT_GoToBakeFrame,
                  GT_OT_TransferTracking,
                  GT_OT_BakeAnimationToWorld,
                  GT_OT_RemoveFocalKeyframe,
                  GT_OT_RemoveFocalKeyframes,
                  GT_OT_SelectGeotrackerObjects,
                  GT_OT_RenderWithBackground,
                  GT_OT_RevertDefaultRender,
                  GT_OT_AddonSetupDefaults,
                  GT_OT_AutoNamePrecalc,
                  GT_OT_UnbreakRotation,
                  GT_OT_DeleteTexture,
                  GT_OT_RescaleWindow,
                  GT_OT_MoveWindow,
                  GT_OT_RigWindow,
                  GT_OT_SwitchCameraToFixedWarning)
