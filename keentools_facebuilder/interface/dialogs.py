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

import logging
import re

import bpy
from bpy.types import Panel, Operator

from ..config import Config, get_main_settings, get_operators, ErrorType


class FB_OT_AddonWarning(Operator):
    bl_idname = Config.fb_warning_idname
    bl_label = ""
    bl_options = {'REGISTER', 'INTERNAL'}

    msg: bpy.props.IntProperty(default=ErrorType.Unknown)
    msg_content: bpy.props.StringProperty(default="")

    content = []

    def set_content(self, txt_list):
        self.content = txt_list
        self.content.append(" ")  # Additional line at end

    def draw(self, context):
        layout = self.layout
        layout.scale_y = 0.75

        for t in self.content:
            layout.label(text=t)

    def execute(self, context):
        logger = logging.getLogger(__name__)
        if self.msg != ErrorType.PktProblem:
            return {"FINISHED"}

        op = getattr(get_operators(), Config.fb_addon_settings_callname)
        op('EXEC_DEFAULT')
        return {"FINISHED"}

    def invoke(self, context, event):
        if self.msg == ErrorType.CustomMessage:
            self.set_content(re.split("\r\n|\n", self.msg_content))
            return context.window_manager.invoke_props_dialog(self, width=300)
        elif self.msg == ErrorType.NoLicense:
            self.set_content([
                "License is not detected",
                "===============",
                "Go to Addon preferences:",
                "Edit > Preferences --> Addons",
                "Use 'KeenTools' word in search field"
            ])
        elif self.msg == ErrorType.SceneDamaged:
            self.set_content([
                "Scene was damaged",
                "===============",
                "It looks like you manualy deleted",
                "some FaceBuilder cameras.",
                "It's not safe way.",
                "Please use [X] button on tab.",
                "===============",
                "The scene was fixed.",
                "Now everything is ok!"
            ])
        elif self.msg == ErrorType.BackgroundsDiffer:
            self.set_content([
                "Different sizes",
                "===============",
                "Cameras backgrounds",
                "has different sizes.",
                "Texture Builder can't bake"
            ])
        elif self.msg == ErrorType.IllegalIndex:
            self.set_content([
                "Object index is out of bounds",
                "===============",
                "Object index out of scene count"
            ])
        elif self.msg == ErrorType.CannotReconstruct:
            self.set_content([
                "Can't reconstruct",
                "===============",
                "Object parameters are invalid or missing."
            ])
        elif self.msg == ErrorType.CannotCreateObject:
            self.set_content([
                "Can't create Object",
                "===============",
                "An error occurred while creating object.",
                "This addon version can't create",
                "objects of this type."
            ])
        elif self.msg == ErrorType.PktProblem:
            self.set_content([
                "You need to install KeenTools Core library",
                "before using FaceBuilder.",
            ])
        elif self.msg == ErrorType.AboutFrameSize:
            self.set_content([
                "About Frame Sizes",
                "===============",
                "All frames used as a background image ",
                "must be the same size. This size should ",
                "be specified as the Render Size ",
                "in the scene.",
                "You will receive a warning if these ",
                "sizes are different. You can fix them ",
                "by choosing commands from this menu."
            ])
        elif self.msg == ErrorType.MeshCorrupted:
            self.set_content([
                "Mesh is corrupted",
                "===============",
                "It looks like the mesh is damaged. ",
                "Addon cannot work with the wrong topology"
            ])
        return context.window_manager.invoke_props_dialog(self, width=300)


class FB_OT_TexSelector(Operator):
    bl_idname = Config.fb_tex_selector_idname
    bl_label = "Select images:"
    bl_description = "Create texture using pinned views"
    bl_options = {'REGISTER', 'INTERNAL'}

    headnum: bpy.props.IntProperty(default=0)

    def draw(self, context):
        settings = get_main_settings()
        head = settings.get_head(self.headnum)
        layout = self.layout

        if not head.has_cameras():
            layout.label(text="You need at least one image to create texture.",
                         icon='ERROR')
            return

        box = layout.box()
        for camera in head.cameras:
            row = box.row()
            # Use in Tex Baking
            row.prop(camera, 'use_in_tex_baking', text='')

            image_icon = 'PINNED' if camera.has_pins() else 'FILE_IMAGE'
            if camera.cam_image:
                row.label(text=camera.get_image_name(), icon=image_icon)
            else:
                row.label(text='-- empty --', icon='LIBRARY_DATA_BROKEN')

        row = box.row()
        # Select All cameras for baking Button
        op = row.operator(Config.fb_filter_cameras_idname, text='All')
        op.action = 'select_all_cameras'
        op.headnum = self.headnum
        # Deselect All cameras
        op = row.operator(Config.fb_filter_cameras_idname, text='None')
        op.action = 'deselect_all_cameras'
        op.headnum = self.headnum

        col = layout.column()
        col.scale_y = 0.75
        col.label(text="Images without pins will be ignored.")
        col.label(text="Please note: texture creation is very time consuming.")
        layout.prop(settings, 'tex_auto_preview')


    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        logger = logging.getLogger(__name__)
        logger.debug('START TEXTURE CREATION')

        head = get_main_settings().get_head(self.headnum)
        if head is None:
            logger.error('WRONG HEADNUM')
            return {'CANCELLED'}

        if head.has_cameras():
            op = getattr(get_operators(), Config.fb_bake_tex_callname)
            res = op('INVOKE_DEFAULT', headnum=self.headnum)

            if res == {'CANCELLED'}:
                logger.debug('CANNOT CREATE TEXTURE')
                self.report({'ERROR'}, "Can't create texture")
            elif res == {'FINISHED'}:
                logger.debug('TEXTURE CREATED')
                self.report({'INFO'}, "Texture has been created successfully")

        return {'FINISHED'}


class FB_OT_ExifSelector(Operator):
    bl_idname = Config.fb_exif_selector_idname
    bl_label = "Select image to read EXIF:"
    bl_description = "Choose image to load EXIF from"
    bl_options = {'REGISTER', 'UNDO'}

    headnum: bpy.props.IntProperty(default=0)

    def draw(self, context):
        settings = get_main_settings()
        head = settings.get_head(self.headnum)
        layout = self.layout

        if not head.has_cameras():
            layout.label(text='No images found')
            layout.label(text='You need at least one image to read EXIF.',
                         icon='ERROR')
            return

        layout.label(text='Select image to read EXIF:')
        box = layout.box()
        for i, camera in enumerate(head.cameras):
            row = box.row()
            image_icon = 'PINNED' if camera.has_pins() else 'FILE_IMAGE'
            if camera.cam_image:
                op = row.operator(Config.fb_read_exif_idname,
                                  text=camera.get_image_name(), icon=image_icon)
                op.headnum = self.headnum
                op.camnum = i

            else:
                row.label(text='-- empty --', icon='LIBRARY_DATA_BROKEN')


    def invoke(self, context, event):
        return context.window_manager.invoke_props_popup(self, event)

    def execute(self, context):
        return {"FINISHED"}
