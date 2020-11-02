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
from ..callbacks import update_mesh_geometry


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
        layout = self.layout.column()
        layout.scale_y = Config.text_scale_y

        for t in self.content:
            layout.label(text=t)

        if self.msg == ErrorType.NoLicense:
            op = self.layout.operator(Config.fb_open_url_idname,
                                      text='Purchase a license')
            op.url = Config.license_purchase_url

    def execute(self, context):
        if self.msg not in (ErrorType.PktProblem, ErrorType.NoLicense):
            return {"FINISHED"}

        op = getattr(get_operators(), Config.fb_addon_settings_callname)
        op('EXEC_DEFAULT')
        return {"FINISHED"}

    def invoke(self, context, event):
        if self.msg == ErrorType.CustomMessage:
            self.set_content(re.split("\r\n|\n", self.msg_content))
            return context.window_manager.invoke_props_dialog(self, width=400)
        elif self.msg == ErrorType.NoLicense:
            self.set_content([
                "License is not found",
                " ",
                "You have 0 days of trial left and there is no license "
                "installed",
                "or something wrong has happened with the installed license.",
                "Please check the license settings."
            ])

        elif self.msg == ErrorType.SceneDamaged:
            self.set_content([
                "Scene was damaged",
                " ",
                "Some objects created by FaceBuilder were missing "
                "from the scene.",
                "The scene was restored automatically."
            ])
        elif self.msg == ErrorType.CannotReconstruct:
            self.set_content([
                "Reconstruction is impossible",
                " ",
                "Object parameters are invalid or missing."
            ])
        elif self.msg == ErrorType.CannotCreateObject:
            self.set_content([
                "Cannot create object",
                " ",
                "An error occurred while creating an object."
            ])
        elif self.msg == ErrorType.MeshCorrupted:
            self.set_content([
                "Wrong topology",
                " ",
                "The FaceBuilder mesh is damaged and cannot be used."
            ])
        elif self.msg == ErrorType.PktProblem:
            self.set_content([
                "You need to install KeenTools Core library "
                "before using FaceBuilder."
            ])
        elif self.msg == ErrorType.PktModelProblem:
            self.set_content([
                "KeenTools Core corrupted",
                " ",
                "Model data cannot be loaded. You need to reinstall "
                "FaceBuilder."
            ])
        return context.window_manager.invoke_props_dialog(self, width=400)


class FB_OT_BlendshapesWarning(Operator):
    bl_idname = Config.fb_blendshapes_warning_idname
    bl_label = ""
    bl_options = {'REGISTER', 'INTERNAL'}

    msg: bpy.props.IntProperty(default=ErrorType.Unknown)
    msg_content: bpy.props.StringProperty(default="Some mesh warning")
    accept: bpy.props.BoolProperty(name='Yes, delete blendshapes', default=False)

    content = []

    def set_content(self, txt_list):
        self.content = txt_list
        self.content.append(" ")  # Additional line at end

    def draw(self, context):
        layout = self.layout.column()
        layout.scale_y = Config.text_scale_y

        layout.prop(self, 'accept')
        box = layout.box()

        for t in self.content:
            row = box.row()
            row.alert = True
            row.label(text=t)

        if self.msg == ErrorType.NoLicense:
            op = self.layout.operator(Config.fb_open_url_idname,
                                      text='Purchase a license')
            op.url = Config.license_purchase_url

    def execute(self, context):
        update_mesh_geometry(self.accept)
        return {'FINISHED'}

    def invoke(self, context, event):
        self.msg_content = 'Warning! Your mesh contains blendshapes so if you change topology you will lost it'
        self.set_content(re.split("\r\n|\n", self.msg_content))
        return context.window_manager.invoke_props_dialog(self, width=400)


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
        checked_views = False
        for camera in head.cameras:
            row = box.row()
            if camera.has_pins():
                row.prop(camera, 'use_in_tex_baking', text='')
                if camera.use_in_tex_baking:
                    checked_views = True
            else:
                row.active = False
                row.label(text='', icon='CHECKBOX_DEHLT')

            image_icon = 'PINNED' if camera.has_pins() else 'FILE_IMAGE'
            if camera.cam_image:
                row.label(text=camera.get_image_name(), icon=image_icon)
            else:
                row.label(text='-- empty --', icon='LIBRARY_DATA_BROKEN')

        row = box.row()

        op = row.operator(Config.fb_filter_cameras_idname, text='All')
        op.action = 'select_all_cameras'
        op.headnum = self.headnum

        op = row.operator(Config.fb_filter_cameras_idname, text='None')
        op.action = 'deselect_all_cameras'
        op.headnum = self.headnum

        col = layout.column()
        col.scale_y = Config.text_scale_y

        if checked_views:
            col.label(text="Please note: texture creation is very "
                           "time consuming.")
        else:
            col.alert = True
            col.label(text="You need to select at least one image "
                           "to create texture.")

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
