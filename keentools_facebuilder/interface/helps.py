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


_help_window_width = 500


class HELP_OT_CameraHelp(bpy.types.Operator):
    bl_idname = Config.fb_help_camera_idname
    bl_label = "Camera settings"
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = "Show help information about Camera settings panel"

    def draw(self, context):
        layout = self.layout
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
        layout.separator()


    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(
            self, width=_help_window_width)

    def execute(self, context):
        return {'FINISHED'}


class HELP_OT_ExifHelp(bpy.types.Operator):
    bl_idname = Config.fb_help_exif_idname
    bl_label = "EXIF"
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = "Show help information about EXIF panel"

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.scale_y = 0.75
        content = [
            "On this panel you can load and see EXIF information stored "
            "in the image files",
            "that you have loaded into Views. By default EXIF data "
            "of the first file is loaded.",
            "This information can be used for the camera in the panel "
            "above after loading."]

        for c in content:
            col.label(text=c)
        layout.separator()

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(
            self, width=_help_window_width)

    def execute(self, context):
        return {'FINISHED'}


class HELP_OT_ViewsHelp(bpy.types.Operator):
    bl_idname = Config.fb_help_views_idname
    bl_label = "Views"
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = "Show help information about Views panel"

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.scale_y = 0.75
        content = [
            "On this panel you can load and remove images "
            "automatically creating ",
            "and removing views, replace image files, set the Frame size "
            "and go into Pin Mode ",
            "for each of the Views.",
            " ",
            "Please note that all images loaded into stack should have "
            "the same dimensions,",
            "they should be shot with the same camera settings (sensor "
            "size and focal length),",
            "should not be cropped (or the camera settings should be "
            "modified accordingly),",
            "should be shot in the same orientation (vertical or horizontal)."]

        for c in content:
            col.label(text=c)
        layout.separator()

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(
            self, width=_help_window_width)

    def execute(self, context):
        return {'FINISHED'}


class HELP_OT_ModelHelp(bpy.types.Operator):
    bl_idname = Config.fb_help_model_idname
    bl_label = "Model"
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = "Show help information about Model panel"

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.scale_y = 0.75
        content = [
            "On this panel you can modify the 3D model of the "
            "head in different ways: ",
            "switch on and off different parts of the model (pins "
            "created on the disabled parts ",
            "remain intact), reset the model to the default state "
            "(also removing all pins ",
            "on all views), and finally you can modify the rigidity "
            "of the model — ",
            "the less is the number, the softer the model becomes "
            "and the more pins ",
            "affect its shape."]

        for c in content:
            col.label(text=c)
        layout.separator()

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(
            self, width=_help_window_width)

    def execute(self, context):
        return {'FINISHED'}


class HELP_OT_PinSettingsHelp(bpy.types.Operator):
    bl_idname = Config.fb_help_pin_settings_idname
    bl_label = "Pin settings"
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = "Show help information about Pin settings panel"

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.scale_y = 0.75
        content = [
            "Here you can tweak the pin size in terms of visual appearance ",
            "and the size of the active area that responds to mouse "
            "pointer actions."]

        for c in content:
            col.label(text=c)
        layout.separator()

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(
            self, width=_help_window_width)

    def execute(self, context):
        return {'FINISHED'}


class HELP_OT_WireframeSettingsHelp(bpy.types.Operator):
    bl_idname = Config.fb_help_wireframe_settings_idname
    bl_label = "Wireframe settings"
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = "Show help information about Wireframe settings panel"

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.scale_y = 0.75
        content = [
            "On this panel you can change colours and opacity of the "
            "model's wireframe ",
            "visible in Pin mode. Aside of changing colours manually you "
            "can try different ",
            "presets loadable by clicking the one-letter buttons."]

        for c in content:
            col.label(text=c)
        layout.separator()

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(
            self, width=_help_window_width)

    def execute(self, context):
        return {'FINISHED'}


class HELP_OT_TextureHelp(bpy.types.Operator):
    bl_idname = Config.fb_help_texture_idname
    bl_label = "Texture"
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = "Show help information about Texture panel"

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.scale_y = 0.75
        content = [
            "This panel gives you access to an experimental functionality "
            "of automatic texture ",
            "grabbing and stitching. You can change the resolution "
            "of the texture, its layout. ",
            "You can choose which views to use in the grabbing process "
            "after clicking ",
            "the \"Create Texture\" button, also you can apply "
            "the material created ",
            "automatically from the grabbed texture to the head object. ",
            " ",
            "Finally you can tweak the grabbing and stitching algorithm: ",
            "— Brightness equalisation is a highly experimental "
            "feature that will try ",
            "to normalise the brightness of different texture parts "
            "across different views. ",
            "— Colour equalisation is similar to Brightness equalisation "
            "only it affects ",
            "colour instead of brightness.",
            "— Angle strictness determines how much the angle of view "
            "of the polygon affects ",
            "the weight of the colour information grabbed for each pixel. "
            "The value range ",
            "is 0-100. When you have multiple frames containing "
            "the same pixel, 0 would mean ",
            "that in the texture you’ll get an average colour of that pixel "
            "between colours ",
            "from all frames where the pixel was found. The larger "
            "the number — the more ",
            "the algorithm prefers frames where the angle "
            "of view of the pixel ",
            "is closer to 90°, still mixing colours from all frames "
            "but with different strength.",
            "— Expanding edges can help with hiding stitches on texture "
            "edges visible when ",
            "the texture is applied to the object. It basically takes "
            "the colour of the last ",
            "pixel on the edge and duplicates it on the next empty pixel."]

        for c in content:
            col.label(text=c)
        layout.separator()

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(
            self, width=_help_window_width)

    def execute(self, context):
        return {'FINISHED'}
