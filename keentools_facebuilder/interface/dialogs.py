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

import bpy
from bpy.types import Panel, Operator
import addon_utils

from ..config import Config, get_main_settings, ErrorType


class WM_OT_FBAddonWarning(Operator):
    bl_idname = Config.fb_warning_operator_idname
    bl_label = "FaceBuilder WARNING!"

    msg: bpy.props.IntProperty(default=ErrorType.Unknown)
    msg_content: bpy.props.StringProperty(default="")

    content = []

    def set_content(self, txt_list):
        self.content = txt_list

    def draw(self, context):
        layout = self.layout

        for t in self.content:
            layout.label(text=t)

    def execute(self, context):
        logger = logging.getLogger(__name__)
        if self.msg != 0:
            return {"FINISHED"}

        # Unlicensed message only
        wm = context.window_manager
        # Searching keyword in Addons tab
        wm.addon_search = Config.addon_search

        try:
            addon_utils.modules_refresh()
            mod = addon_utils.addons_fake_modules.get(Config.addon_name)
            info = addon_utils.module_bl_info(mod)
            info["show_expanded"] = True
        except Exception:
            logger.error("SOME ERROR WITH ADDON SETTINGS OPENNING")
            pass

        return {"FINISHED"}

    def invoke(self, context, event):
        if self.msg == ErrorType.CustomMessage:
            self.set_content(re.split("\r\n|\n", self.msg_content))
            return context.window_manager.invoke_props_dialog(self, width=300)
        elif self.msg == ErrorType.NoLicense:
            self.set_content([
                "===============",
                "License is not detected",
                "===============",
                "Go to Addon preferences:",
                "Edit > Preferences --> Addons",
                "Use 'KeenTools' word in search field"
            ])
        elif self.msg == ErrorType.SceneDamaged:
            self.set_content([
                "===============",
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
                "===============",
                "Different sizes",
                "===============",
                "Cameras backgrounds",
                "has different sizes.",
                "Texture Builder can't bake"
            ])
        elif self.msg == ErrorType.IllegalIndex:
            self.set_content([
                "===============",
                "Object index is out of bounds",
                "===============",
                "Object index out of scene count"
            ])
        elif self.msg == ErrorType.CannotReconstruct:
            self.set_content([
                "===============",
                "Can't reconstruct",
                "===============",
                "Object parameters are invalid or missing."
            ])
        elif self.msg == ErrorType.CannotCreate:
            self.set_content([
                "===============",
                "Can't create Object",
                "===============",
                "Error when creating Object",
                "This addon version can't create",
                "objects of this type or ",
                "PyKeenTools library not loaded. ",
                "Refer to Addon Settings"
            ])
        elif self.msg == ErrorType.AboutFrameSize:
            self.set_content([
                "===============",
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
