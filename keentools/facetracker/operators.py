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

from bpy.types import Operator, Object
from bpy.props import (BoolProperty,
                       IntProperty,
                       FloatProperty,
                       FloatVectorProperty,
                       StringProperty,
                       EnumProperty,
                       PointerProperty)

from ..utils.kt_logging import KTLogger
from ..addon_config import ProductType
from ..facetracker_config import FTConfig, get_ft_settings
from .ui_strings import buttons
from .ftloader import FTLoader
from ..geotracker.utils.prechecks import common_checks
from ..utils.bpy_common import bpy_call_menu
from ..utils.manipulate import force_undo_push
from ..geotracker.utils.calc_timer import (FTTrackTimer,
                                           FTRefineTimer)
from ..geotracker.utils.precalc import PrecalcTimer
from ..geotracker.utils.geotracker_acts import (create_tracker_action,
                                                delete_tracker_action,
                                                select_tracker_objects_action,
                                                prev_keyframe_action,
                                                next_keyframe_action,
                                                add_keyframe_action,
                                                remove_keyframe_action,
                                                clear_all_action,
                                                clear_all_except_keyframes_action,
                                                clear_direction_action,
                                                clear_between_keyframes_action,
                                                toggle_lock_view_action,
                                                center_geo_action,
                                                remove_pins_action,
                                                toggle_pins_action,
                                                track_to,
                                                track_next_frame_action,
                                                refine_async_action,
                                                refine_all_async_action)


_log = KTLogger(__name__)


def product_name(product: int) -> str:
    if product == ProductType.GEOTRACKER:
        return 'GeoTracker'
    if product == ProductType.FACETRACKER:
        return 'FaceTracker'
    else:
        assert False, f'get_loader: Improper product {product}'


class ButtonOperator:
    bl_options = {'REGISTER', 'UNDO'}
    def draw(self, context):
        pass


class FT_OT_CreateFaceTracker(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_create_facetracker_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.output(f'{self.__class__.__name__} execute')
        product = ProductType.FACETRACKER
        act_status = create_tracker_action(product=product)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
        return {'FINISHED'}


class FT_OT_DeleteFaceTracker(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_delete_facetracker_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    geotracker_num: IntProperty(default=-1)

    def execute(self, context):
        _log.output(f'{self.__class__.__name__} execute')
        product = ProductType.FACETRACKER
        act_status = delete_tracker_action(self.geotracker_num,
                                           product=product)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
        return {'FINISHED'}


class FT_OT_SelectGeotrackerObjects(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_select_facetracker_objects_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    geotracker_num: IntProperty(default=0)

    def execute(self, context):
        _log.output(f'{self.__class__.__name__} execute')
        product = ProductType.FACETRACKER
        act_status = select_tracker_objects_action(self.geotracker_num,
                                                   product=product)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class FT_OT_ExitPinMode(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_exit_pinmode_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        FTLoader.out_pinmode()
        return {'FINISHED'}


class FT_OT_SwitchToCameraMode(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_switch_to_camera_mode_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.output(f'{self.__class__.__name__} execute')
        product = ProductType.FACETRACKER
        check_status = common_checks(product=product,
                                     object_mode=False, is_calculating=True,
                                     reload_geotracker=False, geotracker=True,
                                     camera=False, geometry=False,
                                     movie_clip=False)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        settings = get_ft_settings()
        geotracker = settings.get_current_geotracker_item()
        geotracker.solve_for_camera = True
        return {'FINISHED'}


class FT_OT_SwitchToGeometryMode(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_switch_to_geometry_mode_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.output(f'{self.__class__.__name__} execute')
        product = ProductType.FACETRACKER
        check_status = common_checks(product=product,
                                     object_mode=False, is_calculating=True,
                                     reload_geotracker=False, geotracker=True,
                                     camera=False, geometry=False,
                                     movie_clip=False)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        settings = get_ft_settings()
        geotracker = settings.get_current_geotracker_item()
        geotracker.solve_for_camera = False
        return {'FINISHED'}


class FT_OT_TrackToStart(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_track_to_start_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.output(f'{self.__class__.__name__} execute')
        product = ProductType.FACETRACKER
        act_status = track_to(forward=False, product=product)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class FT_OT_TrackToEnd(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_track_to_end_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.output(f'{self.__class__.__name__} execute')
        product = ProductType.FACETRACKER
        act_status = track_to(forward=True, product=product)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class FT_OT_TrackNext(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_track_next_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.output(f'{self.__class__.__name__} execute')
        product = ProductType.FACETRACKER
        act_status = track_next_frame_action(forward=True, product=product)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class FT_OT_TrackPrev(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_track_prev_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.output(f'{self.__class__.__name__} execute')
        product = ProductType.FACETRACKER
        act_status = track_next_frame_action(forward=False, product=product)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class FT_OT_Refine(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_refine_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.output(f'{self.__class__.__name__} execute')
        product = ProductType.FACETRACKER
        act_status = refine_async_action(product=product)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class FT_OT_RefineAll(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_refine_all_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.output(f'{self.__class__.__name__} execute')
        product = ProductType.FACETRACKER
        act_status = refine_all_async_action(product=product)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class FT_OT_PrevKeyframe(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_prev_keyframe_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        _log.output(f'{self.__class__.__name__} execute')
        product = ProductType.FACETRACKER
        settings = get_ft_settings()
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

        return {'FINISHED'}


class FT_OT_NextKeyframe(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_next_keyframe_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        _log.output(f'{self.__class__.__name__} execute')
        product = ProductType.FACETRACKER
        settings = get_ft_settings()
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

        return {'FINISHED'}


class FT_OT_AddKeyframe(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_add_keyframe_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER'}

    def execute(self, context):
        _log.output(f'{self.__class__.__name__} execute')
        product = ProductType.FACETRACKER
        act_status = add_keyframe_action(product=product)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        FTLoader.update_viewport_shaders(timeline=True)
        force_undo_push(f'Add {product_name(product)} keyframe')
        return {'FINISHED'}


class FT_OT_RemoveKeyframe(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_remove_keyframe_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER'}

    def execute(self, context):
        _log.output(f'{self.__class__.__name__} execute')
        product = ProductType.FACETRACKER
        act_status = remove_keyframe_action(product=product)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        FTLoader.update_viewport_shaders(timeline=True)
        force_undo_push(f'Remove {product_name(product)} keyframe')
        return {'FINISHED'}


class FT_OT_ClearAllTracking(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_clear_all_tracking_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.output(f'{self.__class__.__name__} execute')
        product = ProductType.FACETRACKER
        act_status = clear_all_action(product=product)
        FTLoader.update_viewport_shaders(timeline=True)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class FT_OT_ClearTrackingExceptKeyframes(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_clear_tracking_except_keyframes_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.output(f'{self.__class__.__name__} execute')
        product = ProductType.FACETRACKER
        act_status = clear_all_except_keyframes_action(product=product)
        FTLoader.update_viewport_shaders(timeline=True)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class FT_OT_ClearTrackingForward(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_clear_tracking_forward_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.output(f'{self.__class__.__name__} execute')
        product = ProductType.FACETRACKER
        act_status = clear_direction_action(forward=True, product=product)
        FTLoader.update_viewport_shaders(timeline=True)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class FT_OT_ClearTrackingBackward(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_clear_tracking_backward_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.output(f'{self.__class__.__name__} execute')
        product = ProductType.FACETRACKER
        act_status = clear_direction_action(forward=False, product=product)
        FTLoader.update_viewport_shaders(timeline=True)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class FT_OT_ClearTrackingBetween(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_clear_tracking_between_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.output(f'{self.__class__.__name__} execute')
        product = ProductType.FACETRACKER
        act_status = clear_between_keyframes_action(product=product)
        FTLoader.update_viewport_shaders(timeline=True)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class FT_OT_ClearAllTrackingMenuExec(Operator):
    bl_idname = FTConfig.ft_clear_tracking_menu_exec_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'UNDO'}

    def draw(self, context):
        pass

    def execute(self, context):
        bpy_call_menu('INVOKE_DEFAULT',
                      name=FTConfig.ft_clear_tracking_menu_idname)
        return {'FINISHED'}


class FT_OT_CenterGeo(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_center_geo_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.output(f'{self.__class__.__name__} execute')
        product = ProductType.FACETRACKER
        act_status = center_geo_action(product=product)
        FTLoader.update_viewport_shaders(timeline=True, pins_and_residuals=True)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class FT_OT_RemovePins(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_remove_pins_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.output(f'{self.__class__.__name__} execute')
        product = ProductType.FACETRACKER
        act_status = remove_pins_action(product=product)
        FTLoader.update_viewport_shaders(pins_and_residuals=True)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class FT_OT_TogglePins(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_toggle_pins_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.output(f'{self.__class__.__name__} execute')
        product = ProductType.FACETRACKER
        act_status = toggle_pins_action(product=product)
        FTLoader.update_viewport_shaders(pins_and_residuals=True)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class FT_OT_LockView(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_toggle_lock_view_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.output(f'{self.__class__.__name__} execute')
        product = ProductType.FACETRACKER
        act_status = toggle_lock_view_action(product=product)
        if not act_status.success:
            self.report({'INFO'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class FT_OT_StopCalculating(Operator):
    bl_idname = FTConfig.ft_stop_calculating_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    attempts: IntProperty(default=0)

    def execute(self, context):
        _log.output(f'{self.__class__.__name__} execute')
        settings = get_ft_settings()
        _log.output(f'StopCalculating btn: {settings.user_interrupts}')

        if not settings.user_interrupts:
            settings.user_interrupts = True
            self.attempts = 0
            return {'FINISHED'}

        self.attempts += 1
        if self.attempts > 1:
            _log.error(f'Extreme calculation stop')
            settings.stop_calculating()
            self.attempts = 0
            return {'FINISHED'}

        if settings.calculating_mode == 'PRECALC':
            _log.output(f'PrecalcTimer: {PrecalcTimer.active_timers()}')
            if len(PrecalcTimer.active_timers()) == 0:
                settings.stop_calculating()
        elif settings.calculating_mode == 'TRACKING':
            _log.output(f'TrackTimer: {FTTrackTimer.active_timers()}')
            if len(FTTrackTimer.active_timers()) == 0:
                settings.stop_calculating()
        elif settings.calculating_mode == 'REFINE':
            _log.output(f'RefineTimer: {FTRefineTimer.active_timers()}')
            if len(FTRefineTimer.active_timers()) == 0:
                settings.stop_calculating()

        return {'FINISHED'}


BUTTON_CLASSES = (FT_OT_CreateFaceTracker,
                  FT_OT_DeleteFaceTracker,
                  FT_OT_SelectGeotrackerObjects,
                  FT_OT_SwitchToCameraMode,
                  FT_OT_SwitchToGeometryMode,
                  FT_OT_TrackToStart,
                  FT_OT_TrackToEnd,
                  FT_OT_TrackNext,
                  FT_OT_TrackPrev,
                  FT_OT_Refine,
                  FT_OT_RefineAll,
                  FT_OT_PrevKeyframe,
                  FT_OT_NextKeyframe,
                  FT_OT_AddKeyframe,
                  FT_OT_RemoveKeyframe,
                  FT_OT_ClearAllTracking,
                  FT_OT_ClearTrackingExceptKeyframes,
                  FT_OT_ClearTrackingForward,
                  FT_OT_ClearTrackingBackward,
                  FT_OT_ClearTrackingBetween,
                  FT_OT_ClearAllTrackingMenuExec,
                  FT_OT_CenterGeo,
                  FT_OT_RemovePins,
                  FT_OT_TogglePins,
                  FT_OT_LockView,
                  FT_OT_StopCalculating,
                  FT_OT_ExitPinMode)
