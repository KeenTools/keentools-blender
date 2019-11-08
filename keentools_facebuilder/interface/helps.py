# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2019  KeenTools

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
from ..config import Config, get_main_settings


class HELP_OT_CameraHelp(bpy.types.Operator):
    bl_idname = Config.fb_help_camera_idname
    bl_label = "Camera settings"
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = "Show help information about Camera settings panel"

    def draw(self, context):
        layout = self.layout
        # layout.label(text='Camera Help')

        # box = layout.box()
        # box.scale_y = 0.75
        col = layout.column()
        col.scale_y = 0.75
        content = [
            "In order to get a quality model you need to know two things:",
            "sensor size and focal length. Both in millimetres.",
            "Of the sensor size you need to know the length "
            "of the longest side.",
            "Of the focal length — you need to know the real focal length,",
            "not the 35mm equivalent.",
            " ",
            "If you don't know either the sensor width or the focal length,",
            "it's better to switch on the automatic focal length estimation —",
            "it usually gives pretty good results. ",
            "The sensor size in such case can be anything, "
            "but it still is going to be used",
            "in estimation. The estimation happens every "
            "time you change pins.",
            " ",
            "You can also try getting camera settings from EXIF "
            "when it's available.",
            "It can be found on corresponding panel below.",
            " ",
            "Different ways of using EXIF information "
            "for Sensor width and Focal length",
            "can be found in corresponding menus (buttons with gear icons) "
            "on this tab, ",
            "on the right side of fields."]

        for c in content:
            col.label(text=c)


    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=500)

    def execute(self, context):
        return {'FINISHED'}


class HELP_OT_ExifHelp(bpy.types.Operator):
    bl_idname = Config.fb_help_exif_idname
    bl_label = "EXIF"
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = "Show help information about EXIF panel"

    def draw(self, context):
        layout = self.layout
        layout.label(text='EXIF Help')

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        return {'FINISHED'}


class HELP_OT_ViewsHelp(bpy.types.Operator):
    bl_idname = Config.fb_help_views_idname
    bl_label = "Views"
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = "Show help information about Views panel"

    def draw(self, context):
        layout = self.layout
        layout.label(text='Views Help')

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        return {'FINISHED'}


class HELP_OT_ModelHelp(bpy.types.Operator):
    bl_idname = Config.fb_help_model_idname
    bl_label = "Model"
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = "Show help information about Model panel"

    def draw(self, context):
        layout = self.layout
        layout.label(text='Model Help')

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        return {'FINISHED'}


class HELP_OT_PinSettingsHelp(bpy.types.Operator):
    bl_idname = Config.fb_help_pin_settings_idname
    bl_label = "Pin settings"
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = "Show help information about Pin settings panel"

    def draw(self, context):
        layout = self.layout
        layout.label(text='Pin Settings Help')

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        return {'FINISHED'}


class HELP_OT_TextureHelp(bpy.types.Operator):
    bl_idname = Config.fb_help_texture_idname
    bl_label = "Texture"
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = "Show help information about Texture panel"

    def draw(self, context):
        layout = self.layout
        layout.label(text='Texture Help')

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        return {'FINISHED'}
