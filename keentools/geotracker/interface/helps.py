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

import bpy

from ...addon_config import Config
from ...geotracker_config import GTConfig


_help_window_width = 500


class GTHELP_Common:
    bl_options = {'REGISTER', 'INTERNAL'}
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(
            self, width=_help_window_width)

    def execute(self, context):
        return {'FINISHED'}


class GTHELP_OT_InputsHelp(GTHELP_Common, bpy.types.Operator):
    bl_idname = GTConfig.gt_help_inputs_idname
    bl_label = 'Inputs help'
    bl_description = 'Show help information about Inputs panel'

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.scale_y = Config.text_scale_y
        content = [
            'Inputs panel description will be here...',
            ' '
        ]

        for txt in content:
            col.label(text=txt)
        layout.separator()


class GTHELP_OT_AnalyzeHelp(GTHELP_Common, bpy.types.Operator):
    bl_idname = GTConfig.gt_help_analyze_idname
    bl_label = 'Analyze help'
    bl_description = 'Show help information about Analyze panel'

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.scale_y = Config.text_scale_y
        content = [
            'Analyze panel description will be here...',
            ' '
        ]

        for txt in content:
            col.label(text=txt)
        layout.separator()


class GTHELP_OT_CameraHelp(GTHELP_Common, bpy.types.Operator):
    bl_idname = GTConfig.gt_help_camera_idname
    bl_label = 'Camera help'
    bl_description = 'Show help information about Camera settings panel'

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.scale_y = Config.text_scale_y
        content = [
            'Camera panel description will be here...',
            ' '
        ]

        for txt in content:
            col.label(text=txt)
        layout.separator()


class GTHELP_OT_TrackingHelp(GTHELP_Common, bpy.types.Operator):
    bl_idname = GTConfig.gt_help_tracking_idname
    bl_label = 'Tracking help'
    bl_description = 'Show help information about Tracking panel'

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.scale_y = Config.text_scale_y
        content = [
            'Tracking panel description will be here...',
            ' '
        ]

        for txt in content:
            col.label(text=txt)
        layout.separator()


class GTHELP_OT_AppearanceHelp(GTHELP_Common, bpy.types.Operator):
    bl_idname = GTConfig.gt_help_appearance_idname
    bl_label = 'Appearance help'
    bl_description = 'Show help information about Appearance panel'

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.scale_y = Config.text_scale_y
        content = [
            'Appearance panel description will be here...',
            ' '
        ]

        for txt in content:
            col.label(text=txt)
        layout.separator()


class GTHELP_OT_TextureHelp(GTHELP_Common, bpy.types.Operator):
    bl_idname = GTConfig.gt_help_texture_idname
    bl_label = 'Texture help'
    bl_description = 'Show help information about Texture panel'

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.scale_y = Config.text_scale_y
        content = [
            'Texture panel description will be here...',
            ' '
        ]

        for txt in content:
            col.label(text=txt)
        layout.separator()


class GTHELP_OT_AnimationHelp(GTHELP_Common, bpy.types.Operator):
    bl_idname = GTConfig.gt_help_animation_idname
    bl_label = 'Animation help'
    bl_description = 'Show help information about Animation panel'

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.scale_y = Config.text_scale_y
        content = [
            'Animation panel description will be here...',
            ' '
        ]

        for txt in content:
            col.label(text=txt)
        layout.separator()
