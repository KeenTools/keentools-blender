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

import logging
import bpy

from ..addon_config import get_operator
from ..geotracker_config import GTConfig, get_gt_settings
from .utils.geotracker_acts import (create_geotracker_act,
                                    delete_geotracker_act,
                                    add_keyframe_act,
                                    remove_keyframe_act,
                                    prev_keyframe_act,
                                    next_keyframe_act,
                                    track_to,
                                    track_next_frame_act,
                                    refine_act,
                                    refine_all_act,
                                    clear_between_keyframes_act,
                                    clear_direction_act,
                                    clear_all_act)


class ButtonOperator:
    bl_options = {'REGISTER', 'UNDO'}

    def draw(self, context):
        pass


class GT_OT_CreateGeoTracker(ButtonOperator, bpy.types.Operator):
    bl_idname = GTConfig.gt_create_geotracker_idname
    bl_label = 'Create GeoTracker'
    bl_description = 'create GeoTracker object in scene'

    def execute(self, context):
        create_geotracker_act()
        return {'FINISHED'}


class GT_OT_DeleteGeoTracker(ButtonOperator, bpy.types.Operator):
    bl_idname = GTConfig.gt_delete_geotracker_idname
    bl_label = 'Delete GeoTracker'
    bl_description = 'delete GeoTracker object from scene'

    geotracker_num: bpy.props.IntProperty(default=-1)

    def execute(self, context):
        delete_geotracker_act(self.geotracker_num)
        return {'FINISHED'}


class GT_OT_PrevKeyframe(ButtonOperator, bpy.types.Operator):
    bl_idname = GTConfig.gt_prev_keyframe_idname
    bl_label = 'Prev keyframe'
    bl_description = 'prev keyframe'

    def execute(self, context):
        act_status = prev_keyframe_act()
        if not act_status.success:
            self.report({'INFO'}, act_status.error_message)
        return {'FINISHED'}


class GT_OT_NextKeyframe(ButtonOperator, bpy.types.Operator):
    bl_idname = GTConfig.gt_next_keyframe_idname
    bl_label = 'Next keyframe'
    bl_description = 'next keyframe'

    def execute(self, context):
        act_status = next_keyframe_act()
        if not act_status.success:
            self.report({'INFO'}, act_status.error_message)
        return {'FINISHED'}


class GT_OT_TrackToStart(ButtonOperator, bpy.types.Operator):
    bl_idname = GTConfig.gt_track_to_start_idname
    bl_label = 'Track to start'
    bl_description = 'track to start'

    def execute(self, context):
        act_status = track_to(forward=False)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class GT_OT_TrackToEnd(ButtonOperator, bpy.types.Operator):
    bl_idname = GTConfig.gt_track_to_end_idname
    bl_label = 'Track to end'
    bl_description = 'track to end'

    def execute(self, context):
        act_status = track_to(forward=True)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class GT_OT_TrackNext(ButtonOperator, bpy.types.Operator):
    bl_idname = GTConfig.gt_track_next_idname
    bl_label = 'Track next'
    bl_description = 'track next'

    def execute(self, context):
        act_status = track_next_frame_act(forward=True)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class GT_OT_TrackPrev(ButtonOperator, bpy.types.Operator):
    bl_idname = GTConfig.gt_track_prev_idname
    bl_label = 'Track prev'
    bl_description = 'track prev'

    def execute(self, context):
        act_status = track_next_frame_act(forward=False)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class GT_OT_AddKeyframe(ButtonOperator, bpy.types.Operator):
    bl_idname = GTConfig.gt_add_keyframe_idname
    bl_label = 'Add GT keyframe'
    bl_description = 'add keyframe'

    def execute(self, context):
        act_status = add_keyframe_act()
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class GT_OT_RemoveKeyframe(ButtonOperator, bpy.types.Operator):
    bl_idname = GTConfig.gt_remove_keyframe_idname
    bl_label = 'Remove keyframe'
    bl_description = 'remove keyframe'

    def execute(self, context):
        act_status = remove_keyframe_act()
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class GT_OT_ClearAllTracking(ButtonOperator, bpy.types.Operator):
    bl_idname = GTConfig.gt_clear_all_tracking_idname
    bl_label = 'Clear all'
    bl_description = 'Clear all tracking data'

    def execute(self, context):
        act_status = clear_all_act()
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class GT_OT_ClearTrackingForward(ButtonOperator, bpy.types.Operator):
    bl_idname = GTConfig.gt_clear_tracking_forward_idname
    bl_label = 'Clear forward'
    bl_description = 'Clear tracking data forward'

    def execute(self, context):
        act_status = clear_direction_act(forward=True)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class GT_OT_ClearTrackingBackward(ButtonOperator, bpy.types.Operator):
    bl_idname = GTConfig.gt_clear_tracking_backward_idname
    bl_label = 'Clear backward'
    bl_description = 'Clear tracking data backward'

    def execute(self, context):
        act_status = clear_direction_act(forward=False)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class GT_OT_ClearTrackingBetween(ButtonOperator, bpy.types.Operator):
    bl_idname = GTConfig.gt_clear_tracking_between_idname
    bl_label = 'Clear between'
    bl_description = 'Clear tracking data between keyframes'

    def execute(self, context):
        act_status = clear_between_keyframes_act()
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class GT_OT_Refine(ButtonOperator, bpy.types.Operator):
    bl_idname = GTConfig.gt_refine_idname
    bl_label = 'refine'
    bl_description = 'Refine tracking between nearest keyframes'

    def execute(self, context):
        act_status = refine_act()
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class GT_OT_RefineAll(ButtonOperator, bpy.types.Operator):
    bl_idname = GTConfig.gt_refine_all_idname
    bl_label = 'refine all'
    bl_description = 'Refine all tracking data'

    def execute(self, context):
        act_status = refine_all_act()
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


class GT_OT_BtnCenterGeo(ButtonOperator, bpy.types.Operator):
    bl_idname = GTConfig.gt_center_geo_idname
    bl_label = 'center geo'
    bl_description = 'Center geometry in the view'

    def execute(self, context):
        op = get_operator(GTConfig.gt_actor_idname)
        op('EXEC_DEFAULT', action='center_geo')
        return {'FINISHED'}


class GT_OT_BtnMagicKeyframe(ButtonOperator, bpy.types.Operator):
    bl_idname = GTConfig.gt_magic_keyframe_idname
    bl_label = 'magic'
    bl_description = 'Magic keyframe detection'

    def execute(self, context):
        op = get_operator(GTConfig.gt_actor_idname)
        op('EXEC_DEFAULT', action='magic_keyframe')
        return {'FINISHED'}


class GT_OT_BtnRemovePins(ButtonOperator, bpy.types.Operator):
    bl_idname = GTConfig.gt_remove_pins_idname
    bl_label = 'remove pins'
    bl_description = 'Remove all pins from view'

    def execute(self, context):
        op = get_operator(GTConfig.gt_actor_idname)
        op('EXEC_DEFAULT', action='remove_pins')
        return {'FINISHED'}


class GT_OT_BtnCreateAnimation(ButtonOperator, bpy.types.Operator):
    bl_idname = GTConfig.gt_create_animation_idname
    bl_label = 'Create animation'
    bl_description = 'Create animation to geometry'

    def execute(self, context):
        op = get_operator(GTConfig.gt_actor_idname)
        op('EXEC_DEFAULT', action='create_animation')
        return {'FINISHED'}


class GT_OT_BtnExitPinMode(ButtonOperator, bpy.types.Operator):
    bl_idname = GTConfig.gt_exit_pinmode_idname
    bl_label = 'Out Pinmode'
    bl_description = 'Out from PinMode'

    def execute(self, context):
        op = get_operator(GTConfig.gt_actor_idname)
        op('EXEC_DEFAULT', action='exit_pinmode')
        return {'FINISHED'}


class GT_OT_StopPrecalc(bpy.types.Operator):
    bl_idname = GTConfig.gt_stop_precalc_idname
    bl_label = 'Stop Precalc'
    bl_description = 'Stop Precalc calculation'

    def execute(self, context):
        settings = get_gt_settings()
        settings.precalc_mode = False
        return {'FINISHED'}


class GT_OT_InterruptModal(bpy.types.Operator):
    bl_idname = GTConfig.gt_interrupt_modal_idname
    bl_label = 'GeoTracker Interruptor'
    bl_description = 'Operator for in-Viewport drawing'
    bl_options = {'REGISTER', 'INTERNAL'}

    def invoke(self, context, event):
        logger = logging.getLogger(__name__)
        settings = get_gt_settings()
        settings.user_interrupts = False

        context.window_manager.modal_handler_add(self)
        logger.debug('INTERRUPTOR START')
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        logger = logging.getLogger(__name__)
        settings = get_gt_settings()

        if (event.type == 'ESC' and event.value == 'RELEASE') or settings.user_interrupts:
            logger.debug('Exit Interruptor by ESC')
            settings.user_interrupts = True
            return {'FINISHED'}
        logger.debug('INTERRUPTOR IN ACTION')
        return {'PASS_THROUGH'}


BUTTON_CLASSES = (GT_OT_CreateGeoTracker,
                  GT_OT_DeleteGeoTracker,
                  GT_OT_AddKeyframe,
                  GT_OT_RemoveKeyframe,
                  GT_OT_NextKeyframe,
                  GT_OT_PrevKeyframe,
                  GT_OT_TrackToStart,
                  GT_OT_TrackPrev,
                  GT_OT_TrackNext,
                  GT_OT_TrackToEnd,
                  GT_OT_ClearAllTracking,
                  GT_OT_ClearTrackingForward,
                  GT_OT_ClearTrackingBackward,
                  GT_OT_ClearTrackingBetween,
                  GT_OT_Refine,
                  GT_OT_RefineAll,
                  GT_OT_BtnCenterGeo,
                  GT_OT_BtnMagicKeyframe,
                  GT_OT_BtnRemovePins,
                  GT_OT_BtnCreateAnimation,
                  GT_OT_BtnExitPinMode,
                  GT_OT_InterruptModal,
                  GT_OT_StopPrecalc)
