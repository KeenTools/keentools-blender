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
from bpy.props import IntProperty
from ..config import Config, get_main_settings


class OBJECT_MT_FBFixCameraMenu(Menu):
    bl_label = "Fix Frame Size"
    bl_idname = Config.fb_fix_camera_frame_menu_idname
    bl_description = "Fix frame Width and Height parameters for camera"

    def draw(self, context):
        settings = get_main_settings()
        layout = self.layout

        # Disabled because it does not work in popup window
        op = layout.operator(Config.fb_multiple_filebrowser_operator_idname,
                          text="Add Camera Image(s)", icon='OUTLINER_OB_IMAGE')
        op.headnum = settings.tmp_headnum

        layout.separator()

        op = layout.operator(
            Config.fb_actor_operator_idname, text="Info about Frame Size warning",
            icon='ERROR')
        op.action = 'about_fix_frame_warning'

        op = layout.operator(
            Config.fb_actor_operator_idname,
            text="Auto-Detect most frequent Size", icon="FULLSCREEN_ENTER")
        op.action = 'auto_detect_frame_size'

        op = layout.operator(
            Config.fb_actor_operator_idname, text="Use Scene Render Size",
            icon='OUTPUT')
        op.action = 'use_render_frame_size'

        op = layout.operator(
            Config.fb_actor_operator_idname, text="Use This Camera Size",
            icon='VIEW_CAMERA')
        op.action = 'use_this_camera_frame_size'

        op = layout.operator(
            Config.fb_actor_operator_idname, text="Read EXIF for this file",
            icon='TEXT')
        op.action = 'read_file_exif'
        op.headnum = settings.tmp_headnum
        op.camnum = settings.tmp_camnum

        layout.separator()


class OBJECT_MT_FBFixMenu(Menu):
    bl_label = "Select Frame Size"
    bl_idname = Config.fb_fix_frame_menu_idname
    bl_description = "Fix frame Width and Height parameters for all cameras"

    def draw(self, context):
        settings = get_main_settings()
        layout = self.layout

        op = layout.operator(
            Config.fb_actor_operator_idname,
            text="Auto-Detect most frequent Size", icon="FULLSCREEN_ENTER")
        op.action = 'auto_detect_frame_size'

        op = layout.operator(
            Config.fb_actor_operator_idname, text="Use Scene Render Size",
            icon="OUTPUT")
        op.action = 'use_render_frame_size'

        # Disabled because it is not obvious
        # ---
        # op = layout.operator(
        #     Config.fb_actor_operator_idname, text="Use Current Camera Size",
        #     icon="VIEW_CAMERA")
        # op.action = 'use_camera_frame_size'

        # Disabled to avoid problems with users (but useful for internal use)
        # ---
        # frame_width & frame_height should be sets before rescale call
        # op = layout.operator(
        #    config.fb_actor_operator_idname,
        #    text="Experimental Rescale to Render Size")
        # op.action = 'use_render_frame_size_scaled'

        layout.separator()

        # Disabled becaouse it does not work in popup window
        # op = layout.operator(Config.fb_filedialog_operator_idname,
        #                   text="Add Camera Image(s)", icon='OUTLINER_OB_IMAGE')
        # op.headnum = settings.tmp_headnum

        # Add New Camera button
        op = layout.operator(Config.fb_main_add_camera_idname,
                             text="Create Empty Camera",
                             icon='LIBRARY_DATA_BROKEN')  # 'PLUS'
        op.headnum = settings.tmp_headnum

        layout.separator()
        op = layout.operator(
            Config.fb_actor_operator_idname,
            text="Info about Frame Size warning",
            icon="ERROR")
        op.action = 'about_fix_frame_warning'


class OBJECT_MT_FBFocalLengthMenu(Menu):
    bl_label = "Select Frame Size"
    bl_idname = Config.fb_focal_length_menu_idname
    bl_description = "Camera parameters"

    def draw(self, context):
        settings = get_main_settings()
        layout = self.layout

        op = layout.operator(Config.fb_camera_actor_operator_idname,
                             text="Set default Focal Length: 50 mm")
        op.headnum = settings.tmp_headnum
        op.action = 'focal_50mm'

        op = layout.operator(Config.fb_camera_actor_operator_idname,
                             text="Get Focal via EXIF")
        op.headnum = settings.tmp_headnum
        op.action = 'exif_focal'

        op = layout.operator(Config.fb_camera_actor_operator_idname,
                             text="Get Focal via EXIF 35mm equivalent "
                                  "(adjust Sensor too)")
        op.headnum = settings.tmp_headnum
        op.action = 'exif_focal35mm'

        if settings.heads[settings.tmp_headnum].auto_focal_estimation:
            op = layout.operator(Config.fb_camera_actor_operator_idname,
                                 text="Set Automatic Focal Length Estimation OFF")
            op.action = 'auto_focal_off'
        else:
            op = layout.operator(Config.fb_camera_actor_operator_idname,
                                 text="Set Automatic Focal Length Estimation ON")
            op.action = 'auto_focal_on'
        op.headnum = settings.tmp_headnum


class OBJECT_MT_FBSensorWidthMenu(Menu):
    bl_label = "Select Frame Size"
    bl_idname = Config.fb_sensor_width_menu_idname
    bl_description = "Fix frame Width and Height parameters for all cameras"

    def draw(self, context):
        settings = get_main_settings()
        layout = self.layout

        op = layout.operator(Config.fb_camera_actor_operator_idname,
                             text="Set default Sensor Size: 36 x 24 mm")
        op.headnum = settings.tmp_headnum
        op.action = 'sensor_36x24mm'

        op = layout.operator(Config.fb_camera_actor_operator_idname,
                             text="Get Sensor via EXIF")
        op.headnum = settings.tmp_headnum
        op.action = 'exif_sensor'

        op = layout.operator(Config.fb_camera_actor_operator_idname,
                             text="Get Sensor via EXIF 35mm equivalent")
        op.headnum = settings.tmp_headnum
        op.action = 'exif_sensor35mm'
