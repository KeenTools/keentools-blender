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

from ..config import Config, get_main_settings
from ..utils.exif_reader import get_sensor_size_35mm_equivalent


class OBJECT_MT_FBFixCameraMenu(Menu):
    bl_label = "Fix Frame Size"
    bl_idname = Config.fb_fix_camera_frame_menu_idname
    bl_description = "Fix frame Width and Height parameters for camera"

    def draw(self, context):
        settings = get_main_settings()
        layout = self.layout

        op = layout.operator(
            Config.fb_actor_operator_idname,
            text="Auto-Detect most frequent Frame Size",
            icon="FULLSCREEN_ENTER")
        op.action = 'auto_detect_frame_size'

        op = layout.operator(
            Config.fb_actor_operator_idname, text="Use This Camera Frame Size",
            icon='VIEW_CAMERA')
        op.action = 'use_this_camera_frame_size'

        op = layout.operator(
            Config.fb_actor_operator_idname, text="Use Scene Render Size",
            icon='OUTPUT')
        op.action = 'use_render_frame_size'

        # ----------------
        layout.separator()

        op = layout.operator(
            Config.fb_actor_operator_idname, text="Read EXIF for this file",
            icon='TEXT')
        op.action = 'read_file_exif'
        op.headnum = settings.tmp_headnum
        op.camnum = settings.tmp_camnum

        # ----------------
        layout.separator()

        op = layout.operator(
            Config.fb_actor_operator_idname,
            text="Info about Frame Size warning",
            icon='ERROR')
        op.action = 'about_fix_frame_warning'


class OBJECT_MT_FBFixMenu(Menu):
    bl_label = "Frame Size Setup"
    bl_idname = Config.fb_fix_frame_menu_idname
    bl_description = "Setup Frame Width and Height parameters for all cameras"

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

        # Disabled to avoid problems with users (but useful for internal use)
        # ---
        # frame_width & frame_height should be sets before rescale call
        # op = layout.operator(
        #    config.fb_actor_operator_idname,
        #    text="Experimental Rescale to Render Size")
        # op.action = 'use_render_frame_size_scaled'

        layout.separator()

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
    bl_label = "Focal Length setup"
    bl_idname = Config.fb_focal_length_menu_idname
    bl_description = "Setup Camera Focal Length"

    def draw(self, context):
        settings = get_main_settings()
        layout = self.layout
        head = settings.heads[settings.tmp_headnum]

        # Focal Length (only) via EXIF
        if head.exif.focal > 0.0:
            txt = "[{:.2f} mm]   ".format(head.exif.focal)
            op = layout.operator(Config.fb_camera_actor_operator_idname,
                                 text=txt + "EXIF Focal Length",
                                 icon='RESTRICT_RENDER_OFF')
            op.headnum = settings.tmp_headnum
            op.action = 'exif_focal'

        # Focal Length (only) via EXIF 35mm equivalent
        if head.exif.focal35mm > 0.0:
            txt = "[{:.2f} mm]   ".format(head.exif.focal35mm)
            op = layout.operator(Config.fb_camera_actor_operator_idname,
                                 text=txt + "EXIF Focal Length "
                                      "35mm equivalent",
                                 icon='RESTRICT_RENDER_ON')
            op.headnum = settings.tmp_headnum
            op.action = 'exif_focal35mm'

        # ----------------
        layout.separator()

        # Set Automatic Focal Length Estimation OFF
        if settings.heads[settings.tmp_headnum].auto_focal_estimation:
            op = layout.operator(Config.fb_camera_actor_operator_idname,
                                 text="Set Automatic Focal Length "
                                      "Estimation OFF")
            op.action = 'auto_focal_off'
        else:
            op = layout.operator(Config.fb_camera_actor_operator_idname,
                                 text="Set Automatic Focal Length "
                                      "Estimation ON")
            op.action = 'auto_focal_on'
        op.headnum = settings.tmp_headnum

        # ----------------
        layout.separator()

        # Default Focal Length: 50 mm
        op = layout.operator(Config.fb_camera_actor_operator_idname,
                             text="[50 mm]   Default Focal Length",
                             icon='DRIVER_DISTANCE')
        op.headnum = settings.tmp_headnum
        op.action = 'focal_50mm'


class OBJECT_MT_FBSensorWidthMenu(Menu):
    bl_label = "Sensor Size setup"
    bl_idname = Config.fb_sensor_width_menu_idname
    bl_description = "Setup Sensor Width and Height parameters for camera"

    def draw(self, context):
        settings = get_main_settings()
        layout = self.layout
        head = settings.heads[settings.tmp_headnum]

        # Auto Sensor & Focal via EXIF
        if head.exif.sensor_width > 0.0 and head.exif.sensor_length > 0.0 \
                and head.exif.focal > 0.0:
            w = head.exif.sensor_width
            h = head.exif.sensor_length
            f = head.exif.focal
            txt = "{:.2f} x {:.2f} mm [{:.2f}]   ".format(w, h, f)
            op = layout.operator(Config.fb_camera_actor_operator_idname,
                                 text=txt + "EXIF Sensor & [EXIF Focal]",
                                 icon='OBJECT_DATAMODE')
            op.headnum = settings.tmp_headnum
            op.action = 'exif_sensor_and_focal'

        # EXIF Focal and Sensor via 35mm equiv.
        if head.exif.focal > 0.0 and head.exif.focal35mm > 0.0:
            f = head.exif.focal
            w, h = get_sensor_size_35mm_equivalent(head)
            txt = "{:.2f} x {:.2f} mm [{:.2f}]   ".format(w, h, f)
            op = layout.operator(Config.fb_camera_actor_operator_idname,
                text=txt + "Sensor via 35mm equiv. & [EXIF Focal]",
                icon='OBJECT_HIDDEN')
            op.headnum = settings.tmp_headnum
            op.action = 'exif_focal_and_sensor_via_35mm'

        # Auto Sensor & Focal via EXIF 35mm equiv.
        if head.exif.focal > 0.0 and head.exif.focal35mm > 0.0:
            w = 35.0
            h = 24.0 * 35.0 / 36.0
            f = head.exif.focal35mm
            txt = "{:.2f} x {:.2f} mm [{:.2f}]   ".format(w, h, f)
            op = layout.operator(Config.fb_camera_actor_operator_idname,
                text=txt + "Standard Sensor & [Focal 35mm equiv.] ",
                icon='FULLSCREEN_ENTER')
            op.headnum = settings.tmp_headnum
            op.action = 'standard_sensor_and_exif_focal35mm'

        layout.separator()

        # Sensor Size (only) via EXIF
        if head.exif.sensor_width > 0.0 and head.exif.sensor_length > 0.0:
            w = head.exif.sensor_width
            h = head.exif.sensor_length
            txt = "{:.2f} x {:.2f} mm   ".format(w, h)
            op = layout.operator(Config.fb_camera_actor_operator_idname,
                                 text=txt + "EXIF Sensor Size",
                                 icon='OBJECT_DATAMODE')
            op.headnum = settings.tmp_headnum
            op.action = 'exif_sensor'

        # Sensor Size (only) via EXIF 35mm equivalent
        if head.exif.focal > 0.0 and head.exif.focal35mm > 0.0:
            w, h = get_sensor_size_35mm_equivalent(head)
            txt = "{:.2f} x {:.2f} mm   ".format(w, h)
            op = layout.operator(Config.fb_camera_actor_operator_idname,
                                 text=txt + "Sensor Size 35mm equivalent",
                                 icon='OBJECT_HIDDEN')
            op.headnum = settings.tmp_headnum
            op.action = 'exif_sensor_via_35mm'

        # ----------------
        layout.separator()

        op = layout.operator(Config.fb_camera_actor_operator_idname,
                             text="36 x 24 mm   Default Sensor Size",
                             icon='FULLSCREEN_ENTER')
        op.headnum = settings.tmp_headnum
        op.action = 'sensor_36x24mm'

