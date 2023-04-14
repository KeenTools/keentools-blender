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
                       EnumProperty,
                       PointerProperty)
from math import radians

import bpy
from mathutils import Matrix, Quaternion

from ..utils.kt_logging import KTLogger
from ..addon_config import (get_operator,
                            Config,
                            show_user_preferences,
                            show_tool_preferences)
from ..geotracker_config import (GTConfig,
                                 get_gt_settings,
                                 get_current_geotracker_item)
from ..utils.bpy_common import (bpy_current_frame,
                                bpy_background_mode,
                                bpy_show_addon_preferences,
                                bpy_scene,
                                create_empty_object,
                                bpy_remove_object,
                                operator_with_context)
from .utils.geotracker_acts import (create_geotracker_act,
                                    delete_geotracker_act,
                                    add_keyframe_act,
                                    remove_keyframe_act,
                                    prev_keyframe_act,
                                    next_keyframe_act,
                                    track_to,
                                    track_next_frame_act,
                                    refine_async_act,
                                    refine_all_async_act,
                                    clear_between_keyframes_act,
                                    clear_direction_act,
                                    clear_all_act,
                                    clear_all_except_keyframes_act,
                                    remove_pins_act,
                                    toggle_pins_act,
                                    center_geo_act,
                                    create_animated_empty_act,
                                    create_empty_act,
                                    bake_texture_from_frames_act,
                                    relative_to_camera_act,
                                    relative_to_geometry_act,
                                    geometry_repositioning_act,
                                    camera_repositioning_act,
                                    transfer_tracking_to_camera_act,
                                    transfer_tracking_to_geometry_act,
                                    remove_focal_keyframe_act,
                                    remove_focal_keyframes_act,
                                    select_geotracker_objects_act,
                                    render_with_background_act,
                                    revert_default_render_act,
                                    store_camobj_state,
                                    store_geomobj_state,
                                    get_stored_camobj_matrix,
                                    get_stored_geomobj_matrix,
                                    scale_scene_tracking_preview_func,
                                    revert_object_states,
                                    scale_scene_tracking_act,
                                    scale_scene_trajectory_act,
                                    create_non_overlapping_uv_act,
                                    bake_locrot_act,
                                    get_operator_reposition_matrix,
                                    move_scene_tracking_act)
from .utils.calc_timer import TrackTimer, RefineTimer
from .utils.precalc import precalc_with_runner_act, PrecalcTimer
from .gtloader import GTLoader
from .ui_strings import buttons
from .utils.prechecks import common_checks
from ..utils.coords import LocRotScale


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
        act_status = create_geotracker_act()
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
        return {'FINISHED'}


class GT_OT_DeleteGeoTracker(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_delete_geotracker_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    geotracker_num: IntProperty(default=-1)

    def execute(self, context):
        act_status = delete_geotracker_act(self.geotracker_num)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
        return {'FINISHED'}


class GT_OT_CreatePrecalc(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_create_precalc_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        check_status = common_checks(object_mode=False, is_calculating=True,
                                     reload_geotracker=False, geotracker=True,
                                     camera=True, geometry=False,
                                     movie_clip=True)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        act_status = precalc_with_runner_act(context)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
        return {'FINISHED'}


class GT_OT_PrevKeyframe(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_prev_keyframe_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        act_status = prev_keyframe_act()
        if not act_status.success:
            self.report({'INFO'}, act_status.error_message)
        return {'FINISHED'}


class GT_OT_NextKeyframe(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_next_keyframe_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        act_status = next_keyframe_act()
        if not act_status.success:
            self.report({'INFO'}, act_status.error_message)
        return {'FINISHED'}


class GT_OT_TrackToStart(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_track_to_start_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        act_status = track_to(forward=False)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class GT_OT_TrackToEnd(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_track_to_end_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        act_status = track_to(forward=True)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class GT_OT_TrackNext(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_track_next_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        act_status = track_next_frame_act(forward=True)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class GT_OT_TrackPrev(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_track_prev_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        act_status = track_next_frame_act(forward=False)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class GT_OT_AddKeyframe(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_add_keyframe_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        act_status = add_keyframe_act()
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class GT_OT_RemoveKeyframe(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_remove_keyframe_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        act_status = remove_keyframe_act()
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class GT_OT_ClearAllTracking(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_clear_all_tracking_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        act_status = clear_all_act()
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class GT_OT_ClearTrackingExceptKeyframes(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_clear_tracking_except_keyframes_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        act_status = clear_all_except_keyframes_act()
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class GT_OT_ClearTrackingForward(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_clear_tracking_forward_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        act_status = clear_direction_act(forward=True)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class GT_OT_ClearTrackingBackward(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_clear_tracking_backward_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        act_status = clear_direction_act(forward=False)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class GT_OT_ClearTrackingBetween(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_clear_tracking_between_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        act_status = clear_between_keyframes_act()
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class GT_OT_Refine(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_refine_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        act_status = refine_async_act()
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class GT_OT_RefineAll(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_refine_all_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        act_status = refine_all_async_act()
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class GT_OT_CenterGeo(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_center_geo_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        act_status = center_geo_act()
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class GT_OT_BtnMagicKeyframe(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_magic_keyframe_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        op = get_operator(GTConfig.gt_actor_idname)
        op('EXEC_DEFAULT', action='magic_keyframe')
        return {'FINISHED'}


class GT_OT_RemovePins(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_remove_pins_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        act_status = remove_pins_act()
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class GT_OT_TogglePins(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_toggle_pins_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        act_status = toggle_pins_act()
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class GT_OT_ExportAnimatedEmpty(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_export_animated_empty_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        check_status = common_checks(object_mode=True, is_calculating=True,
                                     geotracker=True)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()

        obj = geotracker.geomobj \
            if settings.export_locator_selector == 'GEOMETRY' \
            else geotracker.camobj

        act_status = create_animated_empty_act(obj,
                                               settings.export_linked_locator)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class GT_OT_CreateAnimatedEmpty(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_create_animated_empty_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        act_status = create_animated_empty_act(bpy.context.object)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class GT_OT_CreateEmpty(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_create_empty_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        act_status = create_empty_act()
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class GT_OT_ExitPinMode(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_exit_pinmode_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        GTLoader.out_pinmode()
        return {'FINISHED'}


class GT_OT_StopCalculating(Operator):
    bl_idname = GTConfig.gt_stop_calculating_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        settings = get_gt_settings()
        _log.output(f'StopCalculating btn: {settings.user_interrupts}')

        if not settings.user_interrupts:
            settings.user_interrupts = True
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

        return {'FINISHED'}


class GT_OT_InterruptModal(Operator):
    bl_idname = GTConfig.gt_interrupt_modal_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'INTERNAL'}

    def invoke(self, context, event):
        settings = get_gt_settings()
        settings.user_interrupts = False

        if not bpy_background_mode():
            context.window_manager.modal_handler_add(self)
            _log.output('INTERRUPTOR START')
        else:
            _log.info('GeoTracker Interruptor skipped by background mode')
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        settings = get_gt_settings()

        if settings.user_interrupts:
            _log.output('Interruptor has been stopped by value')
            settings.user_interrupts = True
            return {'FINISHED'}

        if event.type == 'ESC' and event.value == 'PRESS':
            _log.output('Exit Interruptor by ESC')
            settings.user_interrupts = True
            return {'FINISHED'}

        return {'PASS_THROUGH'}


class GT_OT_ResetToneGain(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_reset_tone_exposure_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        geotracker = get_current_geotracker_item()
        if not geotracker:
            return {'CANCELLED'}
        geotracker.tone_exposure = Config.default_tone_exposure
        return {'FINISHED'}


class GT_OT_ResetToneGamma(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_reset_tone_gamma_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        geotracker = get_current_geotracker_item()
        if not geotracker:
            return {'CANCELLED'}
        geotracker.tone_gamma = Config.default_tone_gamma
        return {'FINISHED'}


class GT_OT_ResetToneMapping(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_reset_tone_mapping_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        geotracker = get_current_geotracker_item()
        if not geotracker:
            return {'CANCELLED'}
        geotracker.tone_exposure = Config.default_tone_exposure
        geotracker.tone_gamma = Config.default_tone_gamma
        return {'FINISHED'}


class GT_OT_DefaultWireframeSettings(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_default_wireframe_settings_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        settings = get_gt_settings()
        prefs = settings.preferences()
        settings.wireframe_color = prefs.gt_wireframe_color
        settings.wireframe_opacity = prefs.gt_wireframe_opacity
        return {'FINISHED'}


class GT_OT_DefaultPinSettings(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_default_pin_settings_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        settings = get_gt_settings()
        prefs = settings.preferences()
        settings.pin_size = prefs.pin_size
        settings.pin_sensitivity = prefs.pin_sensitivity
        return {'FINISHED'}


class GT_OT_CreateNonOverlappingUV(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_create_non_overlapping_uv_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        act_status = create_non_overlapping_uv_act()
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        self.report({'INFO'}, 'Non-overlapping UV has been created')
        return {'FINISHED'}


class GT_OT_ReprojectFrame(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_reproject_frame_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        act_status = bake_texture_from_frames_act([bpy_current_frame()])
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class GT_OT_SelectAllFrames(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_select_all_frames_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        geotracker = get_current_geotracker_item()
        if not geotracker:
            return {'CANCELLED'}
        for item in geotracker.selected_frames:
            item.selected = True
        return {'FINISHED'}


class GT_OT_DeselectAllFrames(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_deselect_all_frames_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        geotracker = get_current_geotracker_item()
        if not geotracker:
            return {'CANCELLED'}
        for item in geotracker.selected_frames:
            item.selected = False
        return {'FINISHED'}


class GT_OT_RelativeToCamera(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_relative_to_camera_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        act_status = relative_to_camera_act()
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class GT_OT_RelativeToGeometry(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_relative_to_geometry_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        act_status = relative_to_geometry_act()
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class GT_OT_GeometryRepositioning(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_geometry_repositioning_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        act_status = geometry_repositioning_act()
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class GT_OT_CameraRepositioning(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_camera_repositioning_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        act_status = camera_repositioning_act()
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class GT_OT_TransferTracking(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_transfer_tracking_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        settings = get_gt_settings()
        if settings.transfer_animation_selector == 'CAMERA_TO_GEOMETRY':
            act_status = transfer_tracking_to_geometry_act()
        elif settings.transfer_animation_selector == 'GEOMETRY_TO_CAMERA':
            act_status = transfer_tracking_to_camera_act()
        else:
            act_status = (False, 'Unknown selector state')

        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class GT_OT_TransferTrackingToCamera(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_transfer_tracking_to_camera_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        act_status = transfer_tracking_to_camera_act()
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class GT_OT_TransferTrackingToGeometry(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_transfer_tracking_to_geometry_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        act_status = transfer_tracking_to_geometry_act()
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class GT_OT_BakeAnimationToWorld(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_bake_animation_to_world_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        check_status = common_checks(object_mode=True, is_calculating=True,
                                     reload_geotracker=True, geotracker=True,
                                     camera=True, geometry=True,
                                     movie_clip=False)

        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()

        if settings.bake_animation_selector == 'GEOMETRY':
            act_status = bake_locrot_act(geotracker.geomobj)
        elif settings.bake_animation_selector == 'CAMERA':
            act_status = bake_locrot_act(geotracker.camobj)
        elif settings.bake_animation_selector == 'GEOMETRY_AND_CAMERA':
            act_status = None
            if geotracker.geomobj and geotracker.geomobj.parent:
                act_status = bake_locrot_act(geotracker.geomobj)
            if act_status is None or (act_status.success and geotracker.camobj
                    and geotracker.camobj.parent):
                act_status = bake_locrot_act(geotracker.camobj)
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
        return {'FINISHED'}


class GT_OT_BakeLocrotAnimation(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_bake_locrot_animation_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        act_status = bake_locrot_act(bpy.context.object)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class GT_OT_RemoveFocalKeyframe(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_remove_focal_keyframe_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        act_status = remove_focal_keyframe_act()
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class GT_OT_RemoveFocalKeyframes(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_remove_focal_keyframes_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        act_status = remove_focal_keyframes_act()
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class GT_OT_SelectGeotrackerObjects(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_select_geotracker_objects_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    geotracker_num: IntProperty(default=0)

    def execute(self, context):
        act_status = select_geotracker_objects_act(self.geotracker_num)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class GT_OT_RenderWithBackground(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_render_with_background_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        act_status = render_with_background_act()
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class GT_OT_RevertDefaultRender(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_revert_default_render_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        act_status = revert_default_render_act()
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class GT_OT_AddonSetupDefaults(Operator):
    bl_idname = GTConfig.gt_addon_setup_defaults_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER'}

    def draw(self, context):
        pass

    def execute(self, context):
        show_user_preferences(facebuilder=False, geotracker=True)
        show_tool_preferences(facebuilder=False, geotracker=True)
        bpy_show_addon_preferences()
        return {'FINISHED'}


class GT_OT_AutoNamePrecalc(ButtonOperator, Operator):
    bl_idname = GTConfig.gt_auto_name_precalc_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        geotracker = get_current_geotracker_item()
        if not geotracker or not geotracker.movie_clip:
            self.report({'ERROR'}, 'No movie clip')
            return {'CANCELLED'}
        geotracker.precalc_path = f'{GTConfig.gt_precalc_folder}' \
                                  f'{geotracker.movie_clip.name}'
        status, msg, _ = geotracker.reload_precalc()
        if not status:
            _log.error(msg)
            self.report({'INFO'}, msg)
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


class GT_OT_RescaleWindow(Operator):
    bl_idname = GTConfig.gt_rescale_window_idname
    bl_label = 'Scale'
    bl_options = {'UNDO', 'REGISTER', 'INTERNAL'}

    mode: EnumProperty(name='Mode', items=[
        ('BOTH', 'Scene', 'Use both camera and geometry', 0),
        ('GEOMETRY', 'Geometry', 'Affect geometry only according to camera', 1),
        ('CAMERA', 'Camera', 'Affect camera only according to geometry', 2),
    ], update=_update_rescale_mode)

    value: FloatProperty(default=1.0, precision=4, min=0.0001,
                         update=_rescale_preview_func)
    geom_scale: FloatVectorProperty(default=(1, 1, 1))
    cam_scale:  FloatVectorProperty(default=(1, 1, 1))
    keep_cam_scale: BoolProperty(default=True, name='Keep camera scale',
                                 update=_rescale_preview_func)
    keep_geom_scale: BoolProperty(default=False, name='Keep object scale',
                                  update=_rescale_preview_func)

    origin_point: EnumProperty(name='Pivot point', items=[
        ('WORLD', 'World Origin', 'Use a world center (0, 0, 0)', 0),
        ('GEOMETRY', 'Geometry', 'Use a geometry pivot as a center', 1),
        ('CAMERA', 'Camera', 'Use a camera pivot as a center', 2),
        ('3D_CURSOR', '3D Cursor', 'Use 3D cursor', 3),
    ], update=_rescale_preview_func)

    done: BoolProperty(default=False)

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
        self.done = True
        act_status = scale_scene_tracking_act(self)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}

    def cancel(self, context):
        self.done = True
        revert_object_states()

    def invoke(self, context, event):
        check_status = common_checks(object_mode=True, is_calculating=True,
                                     reload_geotracker=True, geotracker=True,
                                     camera=True, geometry=True,
                                     movie_clip=False)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        geotracker = get_current_geotracker_item()
        store_camobj_state(self, geotracker.camobj)
        store_geomobj_state(self, geotracker.geomobj)
        self.value = 1.0
        self.keep_cam_scale = True
        self.keep_geom_scale = False
        self.done = False
        return context.window_manager.invoke_props_dialog(self, width=350)


def _move_preview_func(operator, context):
    revert_object_states()
    transform_matrix = get_operator_reposition_matrix(operator)

    settings = get_gt_settings()
    geotracker = settings.get_current_geotracker_item()
    geomobj = geotracker.geomobj
    camobj = geotracker.camobj

    geomobj.matrix_world = transform_matrix @ geomobj.matrix_world
    camobj.matrix_world = transform_matrix @ camobj.matrix_world


def _update_move_target_point(operator, context):
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
    if operator.no_updates:
        return
    mat = get_stored_camobj_matrix() if operator.mode == 'CAMERA' else \
        get_stored_geomobj_matrix()
    t, r, s = mat.decompose()
    operator.location = t
    operator.euler_rotation = r.to_euler()


def _update_move_coords(operator, context):
    if operator.no_updates:
        return
    operator.target_point = 'CUSTOM'
    _move_preview_func(operator, context)


class GT_OT_MoveWindow(Operator):
    bl_idname = GTConfig.gt_move_window_idname
    bl_label = 'Move'
    bl_options = {'UNDO', 'REGISTER', 'INTERNAL'}

    no_updates: BoolProperty(default=False)

    mode: EnumProperty(name='Mode', items=[
        ('CAMERA', 'Camera', 'Move camera', 0),
        ('GEOMETRY', 'Geometry', 'Move geometry', 1),
    ], update=_update_move_mode)

    target_point: EnumProperty(name='Target point', items=[
        ('WORLD', 'World Origin', 'Use world center', 0),
        ('3D_CURSOR', '3D Cursor', 'Use 3D cursor', 1),
        ('CUSTOM', 'Custom', 'Use camera as center', 2)
    ], update=_update_move_target_point)

    location: FloatVectorProperty(name='Target Location',
                                  subtype='TRANSLATION',
                                  update=_update_move_coords)
    euler_rotation: FloatVectorProperty(name='Target rotation',
                                        subtype='EULER',
                                        update=_update_move_coords)
    done: BoolProperty(default=False)

    def draw(self, context) -> None:
        layout = self.layout
        if self.done:
            layout.label(text='Operator has been done')
            return

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
        self.done = True
        act_status = move_scene_tracking_act(self)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}

    def cancel(self, context):
        self.done = True
        revert_object_states()

    def invoke(self, context, event):
        check_status = common_checks(object_mode=True, is_calculating=True,
                                     reload_geotracker=True, geotracker=True,
                                     camera=True, geometry=True,
                                     movie_clip=False)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        geotracker = get_current_geotracker_item()
        store_camobj_state(self, geotracker.camobj)
        store_geomobj_state(self, geotracker.geomobj)

        _update_move_mode(self, context)
        self.done = False
        return context.window_manager.invoke_props_dialog(self, width=350)


_rig_empty = None


def _rig_preview_func(operator, context):
    settings = get_gt_settings()
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
    bl_label = 'Rig'
    bl_options = {'UNDO', 'REGISTER', 'INTERNAL'}

    target_point: EnumProperty(name='Target point', items=[
        ('WORLD', 'World Origin', 'Use world center', 0),
        ('CAMERA', 'Camera', 'Affect camera only', 1),
        ('GEOMETRY', 'Geometry', 'Affect geometry only', 2),
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

    def draw(self, context) -> None:
        layout = self.layout
        if self.done:
            layout.label(text='Operator has been done')
            return

        layout.separator()
        layout.prop(self, 'target_point', text='Empty location')
        layout.prop(self, 'reset_scale')
        layout.prop(self, 'keep_orientation')

        row = layout.row()
        row.enabled = self.parent_geometry_active
        row.prop(self, 'parent_geometry')

        row = layout.row()
        row.enabled = self.parent_camera_active
        row.prop(self, 'parent_camera')

        layout.separator()

    def execute(self, context):
        self.done = True
        global _rig_empty

        if not _rig_empty:
            return {'CANCELLED'}

        if _rig_empty:
            _rig_empty.show_in_front = False
            _rig_empty.show_name = False

        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()

        objects = []
        if self.parent_camera and geotracker.camobj:
            objects.append(geotracker.camobj)
        if self.parent_geometry and geotracker.geomobj:
            objects.append(geotracker.geomobj)

        for obj in objects:
            obj.parent = _rig_empty
            obj.matrix_parent_inverse = _rig_empty.matrix_world.inverted()

        _rig_empty = None
        return {'FINISHED'}

    def cancel(self, context):
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
        check_status = common_checks(object_mode=True, is_calculating=True,
                                     reload_geotracker=True, geotracker=True)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        settings = get_gt_settings()
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
        return context.window_manager.invoke_props_dialog(self, width=350)


BUTTON_CLASSES = (GT_OT_CreateGeoTracker,
                  GT_OT_DeleteGeoTracker,
                  GT_OT_CreatePrecalc,
                  GT_OT_AddKeyframe,
                  GT_OT_RemoveKeyframe,
                  GT_OT_NextKeyframe,
                  GT_OT_PrevKeyframe,
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
                  GT_OT_CreateAnimatedEmpty,
                  GT_OT_CreateEmpty,
                  GT_OT_ExitPinMode,
                  GT_OT_InterruptModal,
                  GT_OT_StopCalculating,
                  GT_OT_ResetToneGain,
                  GT_OT_ResetToneGamma,
                  GT_OT_ResetToneMapping,
                  GT_OT_DefaultWireframeSettings,
                  GT_OT_DefaultPinSettings,
                  GT_OT_CreateNonOverlappingUV,
                  GT_OT_ReprojectFrame,
                  GT_OT_SelectAllFrames,
                  GT_OT_DeselectAllFrames,
                  GT_OT_RelativeToCamera,
                  GT_OT_RelativeToGeometry,
                  GT_OT_GeometryRepositioning,
                  GT_OT_CameraRepositioning,
                  GT_OT_TransferTracking,
                  GT_OT_TransferTrackingToCamera,
                  GT_OT_TransferTrackingToGeometry,
                  GT_OT_BakeAnimationToWorld,
                  GT_OT_BakeLocrotAnimation,
                  GT_OT_RemoveFocalKeyframe,
                  GT_OT_RemoveFocalKeyframes,
                  GT_OT_SelectGeotrackerObjects,
                  GT_OT_RenderWithBackground,
                  GT_OT_RevertDefaultRender,
                  GT_OT_AddonSetupDefaults,
                  GT_OT_AutoNamePrecalc,
                  GT_OT_RescaleWindow,
                  GT_OT_MoveWindow,
                  GT_OT_RigWindow)
