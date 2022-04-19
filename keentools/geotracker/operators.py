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


class ButtonOperator:
    bl_options = {'REGISTER', 'UNDO'}

    def draw(self, context):
        pass


class GT_OT_BtnTrackToStart(ButtonOperator, bpy.types.Operator):
    bl_idname = GTConfig.gt_track_to_start_idname
    bl_label = 'Track to start'
    bl_description = 'track to start'

    def execute(self, context):
        op = get_operator(GTConfig.gt_actor_idname)
        op('EXEC_DEFAULT', action='track_to_start')
        return {'FINISHED'}


class GT_OT_BtnTrackToEnd(ButtonOperator, bpy.types.Operator):
    bl_idname = GTConfig.gt_track_to_end_idname
    bl_label = 'Track to end'
    bl_description = 'track to end'

    def execute(self, context):
        op = get_operator(GTConfig.gt_actor_idname)
        op('EXEC_DEFAULT', action='track_to_end')
        return {'FINISHED'}


class GT_OT_BtnTrackNext(ButtonOperator, bpy.types.Operator):
    bl_idname = GTConfig.gt_track_next_idname
    bl_label = 'Track next'
    bl_description = 'track next'

    def execute(self, context):
        op = get_operator(GTConfig.gt_actor_idname)
        try:
            op('EXEC_DEFAULT', action='track_next')
        except Exception as err:
            pass
        return {'FINISHED'}


class GT_OT_BtnTrackPrev(ButtonOperator, bpy.types.Operator):
    bl_idname = GTConfig.gt_track_prev_idname
    bl_label = 'Track prev'
    bl_description = 'track prev'

    def execute(self, context):
        op = get_operator(GTConfig.gt_actor_idname)
        op('EXEC_DEFAULT', action='track_prev')
        return {'FINISHED'}


class GT_OT_BtnPrevKeyframe(ButtonOperator, bpy.types.Operator):
    bl_idname = GTConfig.gt_prev_keyframe_idname
    bl_label = 'Prev keyframe'
    bl_description = 'prev keyframe'

    def execute(self, context):
        op = get_operator(GTConfig.gt_actor_idname)
        op('EXEC_DEFAULT', action='prev_keyframe')
        return {'FINISHED'}


class GT_OT_BtnNextKeyframe(ButtonOperator, bpy.types.Operator):
    bl_idname = GTConfig.gt_next_keyframe_idname
    bl_label = 'Next keyframe'
    bl_description = 'next keyframe'

    def execute(self, context):
        op = get_operator(GTConfig.gt_actor_idname)
        op('EXEC_DEFAULT', action='next_keyframe')
        return {'FINISHED'}


class GT_OT_BtnAddKeyframe(ButtonOperator, bpy.types.Operator):
    bl_idname = GTConfig.gt_add_keyframe_idname
    bl_label = 'Add keyframe'
    bl_description = 'add keyframe'

    def execute(self, context):
        op = get_operator(GTConfig.gt_actor_idname)
        op('EXEC_DEFAULT', action='add_keyframe')
        return {'FINISHED'}


class GT_OT_BtnRemoveKeyframe(ButtonOperator, bpy.types.Operator):
    bl_idname = GTConfig.gt_remove_keyframe_idname
    bl_label = 'Remove keyframe'
    bl_description = 'remove keyframe'

    def execute(self, context):
        op = get_operator(GTConfig.gt_actor_idname)
        op('EXEC_DEFAULT', action='remove_keyframe')
        return {'FINISHED'}


class GT_OT_BtnClearAllTracking(ButtonOperator, bpy.types.Operator):
    bl_idname = GTConfig.gt_clear_all_tracking_idname
    bl_label = 'Clear all'
    bl_description = 'Clear all tracking data'

    def execute(self, context):
        op = get_operator(GTConfig.gt_actor_idname)
        op('EXEC_DEFAULT', action='clear_all')
        return {'FINISHED'}


class GT_OT_BtnClearTrackingForward(ButtonOperator, bpy.types.Operator):
    bl_idname = GTConfig.gt_clear_tracking_forward_idname
    bl_label = 'Clear forward'
    bl_description = 'Clear tracking data forward'

    def execute(self, context):
        op = get_operator(GTConfig.gt_actor_idname)
        op('EXEC_DEFAULT', action='clear_fwd')
        return {'FINISHED'}


class GT_OT_BtnClearTrackingBackward(ButtonOperator, bpy.types.Operator):
    bl_idname = GTConfig.gt_clear_tracking_backward_idname
    bl_label = 'Clear backward'
    bl_description = 'Clear tracking data backward'

    def execute(self, context):
        op = get_operator(GTConfig.gt_actor_idname)
        op('EXEC_DEFAULT', action='clear_bkwd')
        return {'FINISHED'}


class GT_OT_BtnClearTrackingBetween(ButtonOperator, bpy.types.Operator):
    bl_idname = GTConfig.gt_clear_tracking_between_idname
    bl_label = 'Clear between'
    bl_description = 'Clear tracking data between keyframes'

    def execute(self, context):
        op = get_operator(GTConfig.gt_actor_idname)
        op('EXEC_DEFAULT', action='clear_between_keyframes')
        return {'FINISHED'}


class GT_OT_BtnRefine(ButtonOperator, bpy.types.Operator):
    bl_idname = GTConfig.gt_refine_idname
    bl_label = 'refine'
    bl_description = 'Refine tracking between nearest keyframes'

    def execute(self, context):
        op = get_operator(GTConfig.gt_actor_idname)
        op('EXEC_DEFAULT', action='refine')
        return {'FINISHED'}


class GT_OT_BtnRefineAll(ButtonOperator, bpy.types.Operator):
    bl_idname = GTConfig.gt_refine_all_idname
    bl_label = 'refine all'
    bl_description = 'Refine all tracking data'

    def execute(self, context):
        op = get_operator(GTConfig.gt_actor_idname)
        op('EXEC_DEFAULT', action='refine_all')
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


class GT_OT_BtnEnterPinMode(ButtonOperator, bpy.types.Operator):
    bl_idname = GTConfig.gt_enter_pinmode_idname
    bl_label = 'View'
    bl_description = 'Switch to pinmode'

    def execute(self, context):
        try:
            op = get_operator(GTConfig.gt_actor_idname)
            op('EXEC_DEFAULT', action='enter_pinmode')
        except Exception as err:
            self.report({'ERROR'}, 'Problem with PinMode start: {}'.format(str(err)))
        return {'FINISHED'}


class GT_OT_BtnExitPinMode(ButtonOperator, bpy.types.Operator):
    bl_idname = GTConfig.gt_exit_pinmode_idname
    bl_label = 'Out Pinmode'
    bl_description = 'Out from PinMode'

    def execute(self, context):
        op = get_operator(GTConfig.gt_actor_idname)
        op('EXEC_DEFAULT', action='exit_pinmode')
        return {'FINISHED'}


class GT_OT_BtnPrecalcFile(bpy.types.Operator):
    bl_idname = GTConfig.gt_precalc_file_export_idname
    bl_label = 'Set precalc file'
    bl_description = 'Choose an existing .precalc file ' \
                     'or just enter a name for a new one'

    def execute(self, context):
        settings = get_gt_settings()
        settings.precalc_mode = False
        return {'FINISHED'}


class GT_OT_BtnStopPrecalc(bpy.types.Operator):
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

        if event.type == 'ESC' or settings.user_interrupts:
            logger.debug('Exit Interruptor by ESC')
            settings.user_interrupts = True
            return {'FINISHED'}
        logger.debug('INTERRUPTOR IN ACTION')
        return {'PASS_THROUGH'}


BUTTON_CLASSES = (GT_OT_BtnTrackToStart,
                  GT_OT_BtnTrackPrev,
                  GT_OT_BtnTrackNext,
                  GT_OT_BtnTrackToEnd,
                  GT_OT_BtnAddKeyframe,
                  GT_OT_BtnRemoveKeyframe,
                  GT_OT_BtnNextKeyframe,
                  GT_OT_BtnPrevKeyframe,
                  GT_OT_BtnClearAllTracking,
                  GT_OT_BtnClearTrackingForward,
                  GT_OT_BtnClearTrackingBackward,
                  GT_OT_BtnClearTrackingBetween,
                  GT_OT_BtnRefine,
                  GT_OT_BtnRefineAll,
                  GT_OT_BtnCenterGeo,
                  GT_OT_BtnMagicKeyframe,
                  GT_OT_BtnRemovePins,
                  GT_OT_BtnCreateAnimation,
                  GT_OT_BtnEnterPinMode,
                  GT_OT_BtnExitPinMode,
                  GT_OT_InterruptModal,
                  GT_OT_BtnPrecalcFile,
                  GT_OT_BtnStopPrecalc)