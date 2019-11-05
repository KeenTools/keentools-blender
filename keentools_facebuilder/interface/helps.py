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
    bl_label = "Camera Info"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Show Camera About"

    def draw(self, context):
        layout = self.layout
        layout.label(text='Camera Help')

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        return {'FINISHED'}


class HELP_OT_ViewsHelp(bpy.types.Operator):
    bl_idname = Config.fb_help_views_idname
    bl_label = "Views Info"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Show Views About"

    def draw(self, context):
        layout = self.layout
        layout.label(text='Views Help')

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        return {'FINISHED'}


class HELP_OT_ExifHelp(bpy.types.Operator):
    bl_idname = Config.fb_help_exif_idname
    bl_label = "EXIF Info"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Show EXIF About"

    def draw(self, context):
        layout = self.layout
        layout.label(text='EXIF Help')

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        return {'FINISHED'}


class HELP_OT_ModelHelp(bpy.types.Operator):
    bl_idname = Config.fb_help_model_idname
    bl_label = "Model Info"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Show Model About"

    def draw(self, context):
        layout = self.layout
        layout.label(text='Model Help')

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        return {'FINISHED'}


class HELP_OT_PinSettingsHelp(bpy.types.Operator):
    bl_idname = Config.fb_help_pin_settings_idname
    bl_label = "Pin Settings Info"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Show Pin Settings About"

    def draw(self, context):
        layout = self.layout
        layout.label(text='Pin Settings Help')

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        return {'FINISHED'}


class HELP_OT_TextureHelp(bpy.types.Operator):
    bl_idname = Config.fb_help_texture_idname
    bl_label = "Texture Info"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Show Texture About"

    def draw(self, context):
        layout = self.layout
        layout.label(text='Texture Help')

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        return {'FINISHED'}
