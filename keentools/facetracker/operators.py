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
from ..facetracker_config import FTConfig, get_ft_settings
from .ui_strings import buttons
from ..tracker.actions import (create_tracker_action,
                               delete_tracker_action,
                               select_tracker_objects_action)


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
        settings = get_ft_settings()
        act_status = create_tracker_action(settings)
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
        settings = get_ft_settings()
        act_status = delete_tracker_action(settings, self.geotracker_num)
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
        settings = get_ft_settings()
        act_status = select_tracker_objects_action(settings, self.geotracker_num)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        return {'FINISHED'}


BUTTON_CLASSES = (FT_OT_CreateFaceTracker,
                  FT_OT_DeleteFaceTracker,
                  FT_OT_SelectGeotrackerObjects)
