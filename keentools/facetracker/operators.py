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

from typing import Any, List, Set
import os
from copy import deepcopy

from bpy.types import Operator, Object
from bpy.props import (BoolProperty,
                       IntProperty,
                       FloatProperty,
                       FloatVectorProperty,
                       StringProperty,
                       EnumProperty,
                       PointerProperty)
from bpy_extras.io_utils import ExportHelper
from bpy.path import ensure_ext

from ..utils.kt_logging import KTLogger
from ..addon_config import (Config,
                            get_settings,
                            fb_settings,
                            ft_settings,
                            get_operator,
                            ProductType,
                            product_name,
                            calculation_in_progress,
                            show_user_preferences,
                            show_tool_preferences,
                            common_loader)
from ..facebuilder_config import FBConfig
from ..facetracker_config import FTConfig
from ..geotracker_config import GTConfig
from .ui_strings import buttons
from .ftloader import FTLoader
from ..geotracker.utils.prechecks import common_checks
from ..utils.bpy_common import (bpy_call_menu,
                                bpy_background_mode,
                                bpy_show_addon_preferences,
                                bpy_start_frame,
                                bpy_end_frame,
                                bpy_view_camera,
                                bpy_current_frame,
                                bpy_new_image,
                                bpy_context)
from ..utils.manipulate import force_undo_push, switch_to_camera
from ..utils.video import get_movieclip_duration
from ..geotracker.utils.precalc import PrecalcTimer
from ..geotracker.utils.geotracker_acts import (create_facetracker_action,
                                                delete_tracker_action,
                                                select_tracker_objects_action,
                                                prev_keyframe_action,
                                                next_keyframe_action,
                                                add_keyframe_action,
                                                remove_keyframe_action,
                                                remove_focal_keyframe_action,
                                                remove_focal_keyframes_action,
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
                                                refine_all_async_action,
                                                create_animated_empty_action,
                                                create_soft_empties_from_selected_pins_action,
                                                save_facs_as_csv_action,
                                                save_facs_as_animation_action)
from ..tracker.calc_timer import FTTrackTimer, FTRefineTimer
from ..preferences.hotkeys import (pan_keymaps_register,
                                   all_keymaps_unregister)
from ..utils.localview import exit_area_localview
from ..utils.viewport_state import force_show_ui_overlays
from ..facetracker.rig import transfer_animation_to_rig


_log = KTLogger(__name__)


class ButtonOperator:
    bl_options = {'REGISTER', 'UNDO'}
    def draw(self, context):
        pass


class FT_OT_CreateFaceTracker(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_create_facetracker_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        product = ProductType.FACETRACKER
        act_status = create_facetracker_action()
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FT_OT_DeleteFaceTracker(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_delete_facetracker_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    geotracker_num: IntProperty(default=-1)

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        product = ProductType.FACETRACKER
        act_status = delete_tracker_action(self.geotracker_num,
                                           product=product)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FT_OT_SelectGeotrackerObjects(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_select_facetracker_objects_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    geotracker_num: IntProperty(default=0)

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        product = ProductType.FACETRACKER
        act_status = select_tracker_objects_action(self.geotracker_num,
                                                   product=product)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FT_OT_ExitPinMode(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_exit_pinmode_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        check_status = calculation_in_progress()
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}
        FTLoader.out_pinmode()
        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FT_OT_SwitchToCameraMode(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_switch_to_camera_mode_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        product = ProductType.FACETRACKER
        check_status = common_checks(product=product,
                                     object_mode=False, is_calculating=True,
                                     reload_geotracker=False, geotracker=True,
                                     camera=False, geometry=False,
                                     movie_clip=False)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        settings = ft_settings()
        geotracker = settings.get_current_geotracker_item()
        geotracker.solve_for_camera = True
        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FT_OT_SwitchToGeometryMode(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_switch_to_geometry_mode_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        product = ProductType.FACETRACKER
        check_status = common_checks(product=product,
                                     object_mode=False, is_calculating=True,
                                     reload_geotracker=False, geotracker=True,
                                     camera=False, geometry=False,
                                     movie_clip=False)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        settings = ft_settings()
        geotracker = settings.get_current_geotracker_item()
        geotracker.solve_for_camera = False
        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FT_OT_TrackToStart(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_track_to_start_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        product = ProductType.FACETRACKER
        act_status = track_to(forward=False, product=product)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FT_OT_TrackToEnd(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_track_to_end_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        product = ProductType.FACETRACKER
        act_status = track_to(forward=True, product=product)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FT_OT_TrackNext(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_track_next_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        product = ProductType.FACETRACKER
        act_status = track_next_frame_action(forward=True, product=product)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FT_OT_TrackPrev(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_track_prev_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        product = ProductType.FACETRACKER
        act_status = track_next_frame_action(forward=False, product=product)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FT_OT_Refine(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_refine_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        product = ProductType.FACETRACKER
        act_status = refine_async_action(product=product)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FT_OT_RefineAll(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_refine_all_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        product = ProductType.FACETRACKER
        act_status = refine_all_async_action(product=product)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FT_OT_PrevKeyframe(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_prev_keyframe_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        product = ProductType.FACETRACKER
        settings = ft_settings()
        check_status = common_checks(product=product,
                                     object_mode=False, is_calculating=True,
                                     reload_geotracker=not settings.pinmode,
                                     geotracker=True, camera=True,
                                     geometry=True)
        if not check_status.success:
            self.report({'INFO'}, check_status.error_message)
            return {'CANCELLED'}

        settings.start_calculating('JUMP')
        act_status = prev_keyframe_action(product=product)
        settings.stop_calculating()
        if not act_status.success:
            self.report({'INFO'}, act_status.error_message)
            return {'CANCELLED'}

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FT_OT_NextKeyframe(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_next_keyframe_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        product = ProductType.FACETRACKER
        settings = ft_settings()
        check_status = common_checks(product=product,
                                     object_mode=False, is_calculating=True,
                                     reload_geotracker=not settings.pinmode,
                                     geotracker=True, camera=True,
                                     geometry=True)
        if not check_status.success:
            self.report({'INFO'}, check_status.error_message)
            return {'CANCELLED'}

        settings.start_calculating('JUMP')
        act_status = next_keyframe_action(product=product)
        settings.stop_calculating()
        if not act_status.success:
            self.report({'INFO'}, act_status.error_message)
            return {'CANCELLED'}

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FT_OT_AddKeyframe(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_add_keyframe_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER'}

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        product = ProductType.FACETRACKER
        act_status = add_keyframe_action(product=product)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        FTLoader.update_viewport_shaders(timeline=True)
        force_undo_push(f'Add {product_name(product)} keyframe')
        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FT_OT_RemoveKeyframe(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_remove_keyframe_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER'}

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        product = ProductType.FACETRACKER
        act_status = remove_keyframe_action(product=product)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        force_undo_push(f'Remove {product_name(product)} keyframe')
        FTLoader.update_viewport_shaders(wireframe_data=True,
                                         geomobj_matrix=True,
                                         wireframe=True,
                                         pins_and_residuals=True,
                                         timeline=True)
        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FT_OT_ClearAllTracking(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_clear_all_tracking_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        product = ProductType.FACETRACKER
        act_status = clear_all_action(product=product)
        FTLoader.update_viewport_shaders(timeline=True)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FT_OT_ClearTrackingExceptKeyframes(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_clear_tracking_except_keyframes_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        product = ProductType.FACETRACKER
        act_status = clear_all_except_keyframes_action(product=product)
        FTLoader.update_viewport_shaders(timeline=True)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FT_OT_ClearTrackingForward(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_clear_tracking_forward_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        product = ProductType.FACETRACKER
        act_status = clear_direction_action(forward=True, product=product)
        FTLoader.update_viewport_shaders(timeline=True)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FT_OT_ClearTrackingBackward(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_clear_tracking_backward_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        product = ProductType.FACETRACKER
        act_status = clear_direction_action(forward=False, product=product)
        FTLoader.update_viewport_shaders(timeline=True)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FT_OT_ClearTrackingBetween(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_clear_tracking_between_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        product = ProductType.FACETRACKER
        act_status = clear_between_keyframes_action(product=product)
        FTLoader.update_viewport_shaders(timeline=True)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FT_OT_ClearAllTrackingMenuExec(Operator):
    bl_idname = FTConfig.ft_clear_tracking_menu_exec_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'UNDO'}

    def draw(self, context):
        pass

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        bpy_call_menu('INVOKE_DEFAULT',
                      name=FTConfig.ft_clear_tracking_menu_idname)
        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FT_OT_CenterGeo(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_center_geo_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        product = ProductType.FACETRACKER
        act_status = center_geo_action(product=product)
        FTLoader.update_viewport_shaders(timeline=True, pins_and_residuals=True)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FT_OT_RemovePins(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_remove_pins_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        product = ProductType.FACETRACKER
        act_status = remove_pins_action(product=product)
        FTLoader.update_viewport_shaders(pins_and_residuals=True)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FT_OT_TogglePins(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_toggle_pins_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        product = ProductType.FACETRACKER
        act_status = toggle_pins_action(product=product)
        FTLoader.update_viewport_shaders(pins_and_residuals=True)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FT_OT_LockView(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_toggle_lock_view_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        product = ProductType.FACETRACKER
        act_status = toggle_lock_view_action(product=product)
        if not act_status.success:
            self.report({'INFO'}, act_status.error_message)
            return {'CANCELLED'}

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FT_OT_StopCalculating(Operator):
    bl_idname = FTConfig.ft_stop_calculating_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    attempts: IntProperty(default=0)

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        settings = ft_settings()
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

        if settings.is_calculating('PRECALC'):
            _log.output(f'PrecalcTimer: {PrecalcTimer.active_timers()}')
            if len(PrecalcTimer.active_timers()) == 0:
                settings.stop_calculating()
        elif settings.is_calculating('TRACKING'):
            _log.output(f'TrackTimer: {FTTrackTimer.active_timers()}')
            if len(FTTrackTimer.active_timers()) == 0:
                settings.stop_calculating()
        elif settings.is_calculating('REFINE'):
            _log.output(f'RefineTimer: {FTRefineTimer.active_timers()}')
            if len(FTRefineTimer.active_timers()) == 0:
                settings.stop_calculating()

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FT_OT_AutoNamePrecalc(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_auto_name_precalc_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        settings = ft_settings()
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


class FT_OT_SplitVideoExec(Operator):
    bl_idname = FTConfig.ft_split_video_to_frames_exec_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'INTERNAL'}

    def draw(self, context):
        pass

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        settings = ft_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker or not geotracker.movie_clip:
            return {'CANCELLED'}

        op = get_operator(GTConfig.gt_split_video_to_frames_idname)
        op('INVOKE_DEFAULT', from_frame=1,
           to_frame=get_movieclip_duration(geotracker.movie_clip),
           filepath=os.path.join(os.path.dirname(geotracker.movie_clip.filepath), ''),
           product=ProductType.FACETRACKER)
        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FT_OT_DefaultPinSettings(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_default_pin_settings_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        settings = ft_settings()
        settings.pin_size = Config.pin_size
        settings.pin_sensitivity = Config.pin_sensitivity
        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FT_OT_DefaultWireframeSettings(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_default_wireframe_settings_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        settings = ft_settings()
        settings.wireframe_color = Config.ft_color_schemes['default'][0]
        settings.wireframe_special_color = Config.ft_color_schemes['default'][1]
        settings.wireframe_midline_color = Config.ft_midline_color
        settings.wireframe_opacity = Config.ft_wireframe_opacity
        settings.show_specials = True
        settings.wireframe_backface_culling = True
        settings.use_adaptive_opacity = True
        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FT_OT_AddonSetupDefaults(Operator):
    bl_idname = FTConfig.ft_addon_setup_defaults_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER'}

    def draw(self, context):
        pass

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        show_user_preferences(facebuilder=False, geotracker=False,
                              facetracker=True)
        show_tool_preferences(facebuilder=False, geotracker=False,
                              facetracker=True)
        bpy_show_addon_preferences()
        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FT_OT_WireframeColor(Operator):
    bl_idname = FTConfig.ft_wireframe_color_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    action: StringProperty(name="Action Name")

    def draw(self, context):
        pass

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute action={self.action}')
        def _setup_colors_from_scheme(name):
            settings = ft_settings()
            settings.wireframe_color = Config.ft_color_schemes[name][0]
            settings.wireframe_special_color = Config.ft_color_schemes[name][1]

        if self.action == 'wireframe_red':
            _setup_colors_from_scheme('red')
        elif self.action == 'wireframe_green':
            _setup_colors_from_scheme('green')
        elif self.action == 'wireframe_blue':
            _setup_colors_from_scheme('blue')
        elif self.action == 'wireframe_cyan':
            _setup_colors_from_scheme('cyan')
        elif self.action == 'wireframe_magenta':
            _setup_colors_from_scheme('magenta')
        elif self.action == 'wireframe_yellow':
            _setup_colors_from_scheme('yellow')
        elif self.action == 'wireframe_black':
            _setup_colors_from_scheme('black')
        elif self.action == 'wireframe_white':
            _setup_colors_from_scheme('white')

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FT_OT_RemoveFocalKeyframe(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_remove_focal_keyframe_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        product = ProductType.FACETRACKER
        act_status = remove_focal_keyframe_action(product=product)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FT_OT_RemoveFocalKeyframes(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_remove_focal_keyframes_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        product = ProductType.FACETRACKER
        act_status = remove_focal_keyframes_action(product=product)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FT_OT_ExportAnimatedEmpty(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_export_animated_empty_idname
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

            act_status = create_soft_empties_from_selected_pins_action(
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


class FT_OT_SaveFACS(Operator, ExportHelper):
    bl_idname = FTConfig.ft_save_facs_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    filter_glob: StringProperty(
        default='*.csv',
        options={'HIDDEN'}
    )

    check_existing: BoolProperty(
        name='Check Existing',
        description='Check and warn on overwriting existing files',
        default=True,
        options={'HIDDEN'},
    )

    filename_ext: StringProperty(default='.csv')

    filepath: StringProperty(
        default='',
        subtype='FILE_PATH'
    )

    from_frame: IntProperty(name='from', default=1)
    to_frame: IntProperty(name='to', default=1)

    use_tracked_only: BoolProperty(name='Tracked frames only', default=False)

    def check(self, context):
        change_ext = False

        filepath = self.filepath
        sp = os.path.splitext(filepath)

        if sp[1] in {'.csv', '.'}:
            filepath = sp[0]

        filepath = ensure_ext(filepath, self.filename_ext)

        if filepath != self.filepath:
            self.filepath = filepath
            change_ext = True

        return change_ext

    def draw(self, context):
        layout = self.layout
        layout.label(text='Frame range:')
        row = layout.row()
        row.prop(self, 'from_frame', expand=True)
        row.prop(self, 'to_frame', expand=True)

        layout.prop(self, 'use_tracked_only', expand=True)

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        _log.info(f'FACS path: {self.filepath}')
        settings = ft_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            _log.error('Current FaceTracker is wrong')
            return {'CANCELLED'}

        if os.path.exists(self.filepath) and os.path.isdir(self.filepath):
            _log.error(f'Wrong file destination: {self.filepath}')
            self.report({'ERROR'}, 'Wrong file destination!')
            return {'CANCELLED'}

        if self.to_frame < self.from_frame:
            msg = 'Wrong frame range'
            _log.error(msg)
            self.report({'ERROR'}, msg)
            return {'CANCELLED'}

        act_status = save_facs_as_csv_action(filepath=self.filepath,
                                             from_frame=self.from_frame,
                                             to_frame=self.to_frame,
                                             use_tracked_only=self.use_tracked_only)

        if not act_status:
            msg = act_status.error_message
            _log.error(msg)
            self.report({'ERROR'}, msg)

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}

    def invoke(self, context, event):
        _log.output(f'{self.__class__.__name__} invoke')
        self.from_frame = bpy_start_frame()
        self.to_frame = bpy_end_frame()
        return super().invoke(context, event)


class FT_OT_ChooseFrameMode(Operator):
    bl_idname = FTConfig.ft_choose_frame_mode_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'INTERNAL'}

    bus_id: IntProperty(default=-1)

    def init_bus(self) -> None:
        message_bus = common_loader().message_bus()
        self.bus_id = message_bus.register_item(FTConfig.ft_choose_frame_mode_idname)
        _log.output(f'{self.__class__.__name__} bus_id={self.bus_id}')

    def release_bus(self) -> None:
        message_bus = common_loader().message_bus()
        item = message_bus.remove_by_id(self.bus_id)
        _log.output(f'release_bus: {self.bus_id} -> {item}')

    def invoke(self, context: Any, event: Any) -> Set:
        _log.red(f'{self.__class__.__name__} invoke')

        product = ProductType.FACETRACKER
        check_status = common_checks(product=product, reload_geotracker=True,
                                     object_mode=True, is_calculating=True,
                                     geotracker=True, geometry=True,
                                     camera=True, movie_clip=True)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        settings = ft_settings()
        geotracker = settings.get_current_geotracker_item()

        common_loader().stop_fb_viewport()
        common_loader().stop_fb_pinmode()
        fb_settings().pinmode = False

        vp = common_loader().text_viewport()
        default_txt = deepcopy(vp.texter().get_default_text())
        default_txt[0]['text'] = 'Take a snapshot of a video frame'
        default_txt[0]['color'] = (1., 0., 1., 0.85)
        vp.message_to_screen(default_txt)

        area = context.area
        switch_to_camera(area, geotracker.camobj,
                         geotracker.animatable_object())

        common_loader().text_viewport().start_viewport(area=area)
        pan_keymaps_register()
        common_loader().set_ft_head_mode('CHOOSE_FRAME')

        _log.red(f'{self.__class__.__name__} start pinmode modal >>>')
        self.init_bus()
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def on_finish(self) -> None:
        _log.yellow(f'{self.__class__.__name__}.on_finish start')
        common_loader().text_viewport().stop_viewport()
        self.release_bus()
        _log.output(f'{self.__class__.__name__}.on_finish end >>>')

    def cancel(self, context) -> None:
        _log.magenta(f'{self.__class__.__name__} cancel ***')
        all_keymaps_unregister()
        self.on_finish()

    def modal(self, context: Any, event: Any) -> Set:
        message_bus = common_loader().message_bus()
        if not message_bus.check_id(self.bus_id):
            _log.red(f'{self.__class__.__name__} bus stop modal end *** >>>')
            return {'FINISHED'}

        if common_loader().ft_head_mode() != 'CHOOSE_FRAME':
            self.on_finish()
            return {'FINISHED'}

        if context.space_data.region_3d.view_perspective != 'CAMERA':
            bpy_view_camera()

        if event.value == 'RELEASE' and event.type == 'ESC':
            _log.red(f'ESC pressed in {self.__class__.__name__}')
            _log.green(f'{self.__class__.__name__} calls '
                       f'FTConfig.ft_cancel_choose_frame_idname')
            op = get_operator(FTConfig.ft_cancel_choose_frame_idname)
            op('EXEC_DEFAULT')
            return {'FINISHED'}

        return {'PASS_THROUGH'}


class FT_OT_CreateNewHead(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_create_new_head_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')

        product = ProductType.FACETRACKER
        check_status = common_checks(product=product, reload_geotracker=True,
                                     object_mode=True, is_calculating=True,
                                     geotracker=True)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        settings_ft = ft_settings()
        geotracker = settings_ft.get_current_geotracker_item()
        if not geotracker:
            return {'CANCELLED'}

        if not geotracker.camobj:
            self.report({'INFO'}, 'No Camera in FaceTracker')
            return {'CANCELLED'}

        op = get_operator(FBConfig.fb_add_head_operator_idname)
        op('EXEC_DEFAULT')

        settings_fb = fb_settings()
        headnum = settings_fb.get_last_headnum()
        head = settings_fb.get_head(headnum)
        geotracker.geomobj = head.headobj
        head.use_emotions = True

        if geotracker.movie_clip:
            op = get_operator(FTConfig.ft_choose_frame_mode_idname)
            op('INVOKE_DEFAULT')
        else:
            self.report({'INFO'}, 'New FBHead has been created')

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FT_OT_CancelChooseFrame(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_cancel_choose_frame_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')

        product = ProductType.FACETRACKER
        check_status = common_checks(product=product, reload_geotracker=True,
                                     object_mode=True, is_calculating=True,
                                     geotracker=True)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            common_loader().text_viewport().stop_viewport()
            common_loader().set_ft_head_mode('NONE')
            return {'CANCELLED'}

        area = common_loader().text_viewport().get_work_area()
        exit_area_localview(area)
        force_show_ui_overlays(area)

        common_loader().text_viewport().stop_viewport()
        common_loader().set_ft_head_mode('NONE')
        all_keymaps_unregister()

        settings_ft = ft_settings()
        geotracker = settings_ft.get_current_geotracker_item()

        settings_fb = fb_settings()
        headnum = settings_fb.head_by_obj(geotracker.geomobj)
        head = settings_fb.get_head(headnum)
        if headnum >= 0 and head and len(head.cameras) > 0:
            _log.green(f'{self.__class__.__name__} calls '
                       f'FTConfig.ft_edit_head_idname')
            op = get_operator(FTConfig.ft_edit_head_idname)
            op('EXEC_DEFAULT')

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FT_OT_EditHead(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_edit_head_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')

        product = ProductType.FACETRACKER
        check_status = common_checks(product=product, reload_geotracker=True,
                                     object_mode=True, is_calculating=True,
                                     geotracker=True, geometry=True,
                                     camera=True)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        settings_ft = ft_settings()

        if settings_ft.pinmode:
            loader = settings_ft.loader()
            loader.out_pinmode()

        geotracker = settings_ft.get_current_geotracker_item()

        settings_fb = fb_settings()
        headnum = settings_fb.head_by_obj(geotracker.geomobj)
        if headnum < 0:
            msg = 'No FaceBuilder object found'
            _log.error(msg)
            self.report({'INFO'}, msg)
            return {'CANCELLED'}

        head = settings_fb.get_head(headnum)

        if len(head.cameras) == 0:
            if geotracker.movie_clip:
                _log.green(f'{self.__class__.__name__} calls '
                           f'FTConfig.ft_choose_frame_mode_idname')
                op = get_operator(FTConfig.ft_choose_frame_mode_idname)
                op('INVOKE_DEFAULT')
            else:
                self.report({'ERROR'}, 'Please, load a clip first')
            return {'CANCELLED'}

        if headnum == settings_fb.current_headnum:
            camnum = settings_fb.current_camnum
        else:
            camnum = 0

        if camnum < 0 or camnum >= len(head.cameras):
            camnum = 0

        camera = head.get_camera(camnum)
        if not camera:
            self.report({'INFO'}, 'No Camera in FaceBuilder')
            return {'CANCELLED'}

        _log.green(f'{self.__class__.__name__} calls '
                   f'FBConfig.fb_select_camera_idname')
        op = get_operator(FBConfig.fb_select_camera_idname)
        op('EXEC_DEFAULT', headnum=headnum, camnum=camnum,
           detect_face=False)

        common_loader().set_ft_head_mode('EDIT_HEAD')

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FT_OT_AddChosenFrame(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_add_chosen_frame_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')

        product = ProductType.FACETRACKER
        check_status = common_checks(product=product, reload_geotracker=True,
                                     object_mode=True, is_calculating=True,
                                     geotracker=True, geometry=True,
                                     camera=True, movie_clip=True)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        settings_ft = ft_settings()
        geotracker = settings_ft.get_current_geotracker_item()

        settings_fb = fb_settings()
        loader_fb = settings_fb.loader()
        headnum = settings_fb.head_by_obj(geotracker.geomobj)
        if headnum < 0:
            msg = 'No FaceBuilder object found'
            _log.error(msg)
            self.report({'ERROR'}, msg)
            return {'CANCELLED'}

        frame = bpy_current_frame()

        movie_clip = geotracker.movie_clip

        name = movie_clip.name
        w, h = movie_clip.size[:]
        if w <= 0 or h <= 0:
            msg = 'Wrong MovieClip size'
            _log.error(msg)
            self.report({'ERROR'}, msg)
            return {'CANCELLED'}

        if not bpy_start_frame() <= bpy_current_frame() <= bpy_end_frame():
            msg = 'Selected frame should be in Scene playback range'
            _log.error(msg)
            self.report({'ERROR'}, msg)
            return {'CANCELLED'}

        img = bpy_new_image(name, width=w, height=h, alpha=True,
                            float_buffer=False)
        img.use_view_as_render = True

        if movie_clip.source == 'MOVIE':
            img.source = 'MOVIE'
        else:
            img.source = 'SEQUENCE' if movie_clip.frame_duration > 1 else 'FILE'

        img.filepath = movie_clip.filepath

        loader_fb.add_new_camera(headnum, img, frame)
        loader_fb.save_fb_serial_str(headnum)

        settings_fb.current_camnum = settings_fb.get_last_camnum(headnum)

        op = get_operator(FTConfig.ft_edit_head_idname)
        op('EXEC_DEFAULT')

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FT_OT_TransferFACSAnimation(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_transfer_facs_animation_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')

        product = ProductType.FACETRACKER
        check_status = common_checks(product=product, reload_geotracker=True,
                                     object_mode=True, is_calculating=True,
                                     geotracker=True, geometry=True)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        obj = bpy_context().object
        if not obj or obj.type != 'MESH':
            msg = 'Target object should be a Mesh object'
            _log.error(msg)
            self.report({'ERROR'}, msg)
            return {'CANCELLED'}

        settings = ft_settings()
        for geotracker in settings.trackers():
            if obj == geotracker.geomobj:
                msg = 'Target object should not be a FaceTracker Geometry'
                _log.error(msg)
                self.report({'ERROR'}, msg)
                return {'CANCELLED'}

        save_facs_as_animation_action(from_frame=bpy_start_frame(),
                                      to_frame=bpy_end_frame(),
                                      use_tracked_only=True, obj=obj)

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FT_OT_TransferAnimationToRig(ButtonOperator, Operator):
    bl_idname = FTConfig.ft_transfer_animation_to_rig_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    detect_scale: BoolProperty(
        name='Detect scale',
        default=True)
    scale: FloatVectorProperty(
        description='Scale movement data',
        name='Scale', subtype='XYZ',
        default=(1.0, 1.0, 1.0),
        min=0.001, max=1000.0)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, 'detect_scale')
        layout.prop(self, 'scale')

    def invoke(self, context, event):
        _log.green(f'{self.__class__.__name__} invoke')
        return self.execute(context)

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')

        product = ProductType.FACETRACKER
        check_status = common_checks(product=product, reload_geotracker=True,
                                     object_mode=True, is_calculating=True,
                                     geotracker=True, geometry=True)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        obj = bpy_context().object
        if not obj or obj.type != 'ARMATURE':
            msg = 'Target object should be an Armature object'
            _log.error(msg)
            self.report({'ERROR'}, msg)
            return {'CANCELLED'}

        settings = ft_settings()
        geotracker = settings.get_current_geotracker_item()
        ft = settings.loader().kt_geotracker()

        transfer_status = transfer_animation_to_rig(operator=self,
                                                    obj=geotracker.geomobj,
                                                    arm_obj=obj,
                                                    facetracker=ft,
                                                    use_tracked_only=True,
                                                    detect_scale=self.detect_scale,
                                                    from_frame=bpy_start_frame(),
                                                    to_frame=bpy_end_frame(),
                                                    scale=self.scale)
        if not transfer_status.success:
            self.report({'ERROR'}, transfer_status.error_message)
            return {'CANCELLED'}

        _log.output(f'{self.__class__.__name__} execute end >>>')
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
                  FT_OT_AutoNamePrecalc,
                  FT_OT_SplitVideoExec,
                  FT_OT_ExitPinMode,
                  FT_OT_AddonSetupDefaults,
                  FT_OT_DefaultPinSettings,
                  FT_OT_DefaultWireframeSettings,
                  FT_OT_WireframeColor,
                  FT_OT_RemoveFocalKeyframe,
                  FT_OT_RemoveFocalKeyframes,
                  FT_OT_ExportAnimatedEmpty,
                  FT_OT_SaveFACS,
                  FT_OT_ChooseFrameMode,
                  FT_OT_CreateNewHead,
                  FT_OT_EditHead,
                  FT_OT_CancelChooseFrame,
                  FT_OT_AddChosenFrame,
                  FT_OT_TransferFACSAnimation,
                  FT_OT_TransferAnimationToRig)
