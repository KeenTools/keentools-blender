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
from bpy.types import Menu
from ..config import Config


class OBJECT_MT_FBFixCameraMenu(Menu):
    bl_label = "Fix Frame Size"
    bl_idname = Config.fb_fix_camera_frame_menu_idname
    bl_description = "Fix frame Width and Height parameters for camera"

    def draw(self, context):
        layout = self.layout

        op = layout.operator(
            Config.fb_actor_operator_idname, text="Open New Image",
            icon="FILEBROWSER")
        op.action = 'about_fix_frame_warning'

        layout.separator()

        op = layout.operator(
            Config.fb_actor_operator_idname, text="Info about this warning",
            icon="ERROR")
        op.action = 'about_fix_frame_warning'

        op = layout.operator(
            Config.fb_actor_operator_idname,
            text="Auto-Detect most frequent Size")
        op.action = 'auto_detect_frame_size'

        op = layout.operator(
            Config.fb_actor_operator_idname, text="Use Scene Render Size")
        op.action = 'use_render_frame_size'

        op = layout.operator(
            Config.fb_actor_operator_idname, text="Use This Camera Size")
        op.action = 'use_this_camera_frame_size'


class OBJECT_MT_FBFixMenu(Menu):
    bl_label = "Select Frame Size"
    bl_idname = Config.fb_fix_frame_menu_idname
    bl_description = "Fix frame Width and Height parameters for all cameras"

    def draw(self, context):
        layout = self.layout

        op = layout.operator(
            Config.fb_actor_operator_idname, text="Info about Size warning")
        op.action = 'about_fix_frame_warning'

        op = layout.operator(
            Config.fb_actor_operator_idname,
            text="Auto-Detect most frequent Size")
        op.action = 'auto_detect_frame_size'

        op = layout.operator(
            Config.fb_actor_operator_idname, text="Use Scene Render Size")
        op.action = 'use_render_frame_size'

        op = layout.operator(
            Config.fb_actor_operator_idname, text="Use Current Camera Size")
        op.action = 'use_camera_frame_size'

        # Disabled to avoid problems with users (but usefull for internal use)
        # frame_width & frame_height should be sets before rescale call
        # op = layout.operator(
        #    config.fb_actor_operator_idname,
        #    text="Experimental Rescale to Render Size")
        # op.action = 'use_render_frame_size_scaled'
