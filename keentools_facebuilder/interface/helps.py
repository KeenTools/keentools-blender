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
        col.scale_y = Config.text_scale_y
        content = [
            "To get a quality model you need to know one important thing about",
            "your photos — the 35mm equivalent focal length the photos "
            "were taken with.",
            "Usually we can automatically get this data from EXIF of the "
            "loaded pictures.",
            " ",
            "Unfortunately it's not a rare case when this data is stripped "
            "out of the photos.",
            "In this case you still can get a quality model manually "
            "setting up the focal",
            "length if you know it. In all other cases we recommend using "
            "focal length estimation.",
            " ",
            "If you don't know the focal length, we recommend you to not "
            "change anything. ",
            "Please rely on automatic settings, that should provide you "
            "the best possible results.",
            " ",
            "If you know the focal length and want to check that "
            "everything's correct,",
            "you can open this panel and see the detected 35mm equiv. "
            "focal length. ",
            "You can change it if you switch into manual mode using "
            "the advanced setting menu",
            "in the header of the camera settings panel.",
            " ",
            "When we detect similar 35mm equiv. focal length across a number "
            "of photographs",
            "we add them into one group, it helps our face morphing algorithm "
            "in cases ",
            "when there are more than one groups with different focal lengths. "
            "You can also ",
            "add different pictures with unknown focal length into one "
            "group manually,",
            "so the FL estimation algorithm will treat them all as if they "
            "were taken with ",
            "the same 35mm equiv. focal length, but we recommend to only do "
            "so if you really ",
            "know what you're doing."]

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
        col.scale_y = Config.text_scale_y
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
        col.scale_y = Config.text_scale_y
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
        col.scale_y = Config.text_scale_y
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
        col.scale_y = Config.text_scale_y
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
        col.scale_y = Config.text_scale_y
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


class HELP_OT_BlendshapesHelp(bpy.types.Operator):
    bl_idname = Config.fb_help_blendshapes_idname
    bl_label = 'Blendshapes'
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = 'Show help information about Blendshapes panel'

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.scale_y = Config.text_scale_y
        content = [
            'On this panel you can create FACS ARKit-compatible blendshapes '
            'for the head ',
            'you\'ve built, load animation from a CSV file and export the head '
            'with all blendshapes ',
            'and animation to a game engine.',
            ' ',
            'Once you press "Create" button, 51 blendshapes will be created. '
            'You can change ',
            'how they affect the shape of the head here: '
            'Object Data Properties > Shape Keys.',
            'If you change the topology, the blendshapes will be recreated. '
            'When you change ',
            'the shape of the head using pins in Pin Mode, and also when you '
            'change the scale ',
            'of the model, you\'ll be asked if you want to update '
            'the blendshapes, note that ',
            'the old blendshapes become useless once you make such changes.',
            ' ',
            'The blendshapes are fully compatible with the ARKit '
            'specifications, which can found ',
            'at Apple Developer portal.',
            ' ',
            'You can animate the blendshapes manually creating keyframes '
            'for each Shape Key.',
            ' ',
            'If you have LiveLinkFace (or similar) application, you can record '
            'the facial animation ',
            'using the iOS device with the True Depth sensor (iPhone X '
            'and newer), ',
            'export a CSV file and then import it here.',
            ' ',
            'To export the head with all its blendshapes and animation, '
            'you need to know ',
            'where you want to import this 3D model to. In most cases '
            'the Export button ',
            'presented here will work for Unreal Engine and Unity, it will '
            'pre-setup the Blender ',
            'export dialog for you. Your free to change the settings before '
            'saving the file if you need.']

        for c in content:
            col.label(text=c)
        layout.separator()

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(
            self, width=_help_window_width)

    def execute(self, context):
        return {'FINISHED'}
