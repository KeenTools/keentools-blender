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
import addon_utils

from ..config import Config, get_main_settings, ErrorType


class WM_OT_FBAddonWarning(Operator):
    bl_idname = Config.fb_warning_operator_idname
    bl_label = ""

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

        op = getattr(bpy.ops.object,
                     Config.fb_main_addon_settings_callname)
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
                "You need to install KeenTools Core",
                "before you can use the addon.",
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
        return context.window_manager.invoke_props_dialog(self, width=300)


class WM_OT_FBTexSelector(Operator):
    bl_idname = Config.fb_tex_selector_operator_idname
    bl_label = "Select Images for Texture Baking"

    headnum: bpy.props.IntProperty(default=0)

    def draw(self, context):
        settings = get_main_settings()
        head = settings.heads[self.headnum]
        layout = self.layout

        if not len(head.cameras) > 0:
            layout.label(text="You need at least one image to get started.")
            return

        row = layout.row()
        # Select All cameras for baking Button
        op = row.operator(Config.fb_main_filter_cameras_idname, text='All')
        op.action = 'select_all_cameras'
        op.headnum = self.headnum
        # Deselect All cameras
        op = row.operator(Config.fb_main_filter_cameras_idname,
                          text='None')
        op.action = 'deselect_all_cameras'
        op.headnum = self.headnum

        for camera in head.cameras:
            row = layout.row()
            # Use in Tex Baking
            row.prop(camera, 'use_in_tex_baking', text='')

            if camera.cam_image:
                row.label(text='', icon='FILE_IMAGE')
                if camera.pins_count > 0:
                    row.label(text='', icon='PINNED')
                row.label(text=camera.cam_image.name)
            else:
                row.label(text='-- empty --')

        layout.label(text="Images without pins will be auto-ignored.")
        layout.label(text="Texture baking can be time consuming, be patient.")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        op = getattr(bpy.ops.object, Config.fb_main_bake_tex_callname)
        op('INVOKE_DEFAULT', headnum=self.headnum)
        return {"FINISHED"}
