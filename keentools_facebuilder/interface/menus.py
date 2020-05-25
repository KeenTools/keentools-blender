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


class FB_MT_ProperViewMenu(Menu):
    bl_label = "View operations"
    bl_idname = Config.fb_proper_view_menu_idname
    bl_description = "View operations"

    def draw(self, context):
        settings = get_main_settings()
        layout = self.layout

        op = layout.operator(
            Config.fb_delete_camera_idname,
            text='Delete this view', icon='CANCEL')
        op.headnum = settings.tmp_headnum
        op.camnum = settings.tmp_camnum

        layout.operator(Config.fb_single_filebrowser_exec_idname,
                        text="Open file", icon='FILEBROWSER')

        layout.separator()

        if settings.pinmode:
            op = layout.operator(Config.fb_rotate_image_cw_idname,
                                 text='Rotate CW', icon='LOOP_FORWARDS')
            op.headnum = settings.tmp_headnum
            op.camnum = settings.tmp_camnum

            op = layout.operator(Config.fb_rotate_image_ccw_idname,
                                 text='Rotate CCW', icon='LOOP_BACK')
            op.headnum = settings.tmp_headnum
            op.camnum = settings.tmp_camnum

            op = layout.operator(Config.fb_reset_image_rotation_idname,
                                 text='Reset Orientation',
                                 icon='OUTLINER_OB_IMAGE')
            op.headnum = settings.tmp_headnum
            op.camnum = settings.tmp_camnum
        else:
            layout.label(text='Rotate CW', icon='LOOP_FORWARDS')
            layout.label(text='Rotate CCW', icon='LOOP_BACK')
            layout.label(text='Reset Orientation', icon='OUTLINER_OB_IMAGE')


class FB_MT_ImproperViewMenu(Menu):
    bl_label = "View operations"
    bl_idname = Config.fb_improper_view_menu_idname
    bl_description = "Improper View operations"

    def draw(self, context):
        settings = get_main_settings()
        layout = self.layout

        col = layout.column()
        col.alert = True
        col.active = True
        col.scale_y = 0.7
        col.label(icon='ERROR', text='Possible Frame size issue detected.')
        col.label(icon='BLANK1',
                  text='Size of this image is different from the Frame size.')

        layout.separator()

        op = layout.operator(
            Config.fb_view_to_frame_size_idname,
            text="Set the Frame size using this view", icon='SHADING_BBOX')
        op.headnum = settings.tmp_headnum
        op.camnum = settings.tmp_camnum

        op = layout.operator(
            Config.fb_delete_camera_idname,
            text='Delete this view', icon='CANCEL')
        op.headnum = settings.tmp_headnum
        op.camnum = settings.tmp_camnum

        layout.operator(Config.fb_single_filebrowser_exec_idname,
                        text="Open file", icon='FILEBROWSER')

        op = layout.operator(Config.fb_rotate_image_cw_idname,
                        text='Rotate CW', icon='LOOP_FORWARDS')
        op.headnum = settings.tmp_headnum
        op.camnum = settings.tmp_camnum

        op = layout.operator(Config.fb_rotate_image_ccw_idname,
                        text='Rotate CCW', icon='LOOP_BACK')
        op.headnum = settings.tmp_headnum
        op.camnum = settings.tmp_camnum

        op = layout.operator(Config.fb_reset_image_rotation_idname,
                             text='Reset Orientation',
                             icon='OUTLINER_OB_IMAGE')
        op.headnum = settings.tmp_headnum
        op.camnum = settings.tmp_camnum



class FB_MT_FrameSizeMenu(Menu):
    bl_label = "Change Frame size"
    bl_idname = Config.fb_fix_frame_size_menu_idname
    bl_description = "Change Frame size description"

    def draw(self, context):
        layout = self.layout

        layout.operator(
            Config.fb_most_frequent_frame_size_idname,
            text="Use most frequent image size", icon="FULLSCREEN_ENTER")

        layout.operator(
            Config.fb_render_size_to_frame_size_idname,
            text="Use Scene render size", icon="OUTPUT")


class FB_MT_ImageGroupMenu(Menu):
    bl_label = "Image Group"
    bl_idname = Config.fb_image_group_menu_idname
    bl_description = "Image Group"

    def draw(self, context):
        settings = get_main_settings()
        layout = self.layout

        layout.separator()
        head = settings.get_head(settings.current_headnum)
        groups = set([x.image_group for x in head.cameras])
        for group in groups:
            if group == 0 or group == -1:
                continue
            op = layout.operator(
                Config.fb_actor_idname,
                text="Group {}".format(group))
            op.action = 'to_image_group'
            op.num = group

        op = layout.operator(
            Config.fb_actor_idname,
            text="New group")
        op.action = 'new_image_group'

        layout.separator()
        op = layout.operator(
            Config.fb_actor_idname,
            text="Reset group")
        op.action = 'reset_image_group'

        op = layout.operator(
            Config.fb_actor_idname,
            text="Exclude from grouping")
        op.action = 'make_unique'

        layout.separator()
        op = layout.operator(
            Config.fb_actor_idname,
            text="Get settings from EXIF")
        op.action = 'settings_by_exif'


class FB_MT_CameraPanelMenu(Menu):
    bl_label = "Advanced Camera settings"
    bl_idname = Config.fb_camera_panel_menu_idname
    bl_description = "Camera Panel Menu description"

    def draw(self, context):
        settings = get_main_settings()
        layout = self.layout

        head = settings.get_head(settings.current_headnum)
        if head is not None:
            txt = 'Switch to Manual mode' if head.smart_mode() \
                else 'Switch to Default mode'
            op = layout.operator(
                Config.fb_actor_idname,
                text=txt)
            op.action = 'manual_mode'
            op.headnum = settings.tmp_headnum
            op.camnum = settings.tmp_camnum

        layout.separator()

        op = layout.operator(
            Config.fb_actor_idname,
            text='Exclude all images from grouping')
        op.action = 'make_all_unique'

        op = layout.operator(
            Config.fb_actor_idname,
            text="Reset groups for all images")
        op.action = 'reset_all_image_groups'

        layout.separator()
        op = layout.operator(
            Config.fb_actor_idname,
            text="Reset all camera settings")
        op.action = 'reset_all_camera_settings'


class FB_MT_ReadExifMenu(Menu):
    bl_label = "Select image to read EXIF"
    bl_idname = Config.fb_read_exif_menu_idname
    bl_description = "Select image to read EXIF"

    def draw(self, context):
        settings = get_main_settings()
        headnum = settings.tmp_headnum
        head = settings.get_head(headnum)
        layout = self.layout

        if not head.has_cameras():
            layout.label(text='No images found', icon='ERROR')
            layout.label(text='You need at least one image to read EXIF.')
            return

        for i, camera in enumerate(head.cameras):
            image_icon = 'PINNED' if camera.has_pins() else 'FILE_IMAGE'
            if camera.cam_image:
                op = layout.operator(Config.fb_read_exif_idname,
                                     text=camera.get_image_name(),
                                     icon=image_icon)
                op.headnum = headnum
                op.camnum = i

            else:
                layout.label(text='-- empty --', icon='LIBRARY_DATA_BROKEN')


class FB_MT_FocalLengthMenu(Menu):
    bl_label = "Focal Length setup"
    bl_idname = Config.fb_focal_length_menu_idname
    bl_description = "Setup Camera Focal Length"

    def draw(self, context):
        settings = get_main_settings()
        layout = self.layout
        head = settings.get_head(settings.tmp_headnum)

        # Focal Length (only) via EXIF
        if head.exif.focal > 0.0:
            txt = "[{:.2f} mm]   ".format(head.exif.focal)
            op = layout.operator(Config.fb_camera_actor_idname,
                                 text=txt + "EXIF Focal Length",
                                 icon='RESTRICT_RENDER_OFF')
            op.headnum = settings.tmp_headnum
            op.action = 'exif_focal'

        # Focal Length (only) via EXIF 35mm equivalent
        if head.exif.focal35mm > 0.0:
            txt = "[{:.2f} mm]   ".format(head.exif.focal35mm)
            op = layout.operator(Config.fb_camera_actor_idname,
                                 text=txt + "EXIF Focal Length "
                                            "35mm equivalent",
                                 icon='RESTRICT_RENDER_ON')
            op.headnum = settings.tmp_headnum
            op.action = 'exif_focal35mm'

        # ----------------
        layout.separator()

        # Default Focal Length: 50 mm
        op = layout.operator(Config.fb_camera_actor_idname,
                             text="[50 mm]   Default Focal Length",
                             icon='DRIVER_DISTANCE')
        op.headnum = settings.tmp_headnum
        op.action = 'focal_50mm'


class FB_MT_SensorWidthMenu(Menu):
    bl_label = "Sensor Size setup"
    bl_idname = Config.fb_sensor_width_menu_idname
    bl_description = "Setup Sensor Width and Height parameters for camera"

    def draw(self, context):
        settings = get_main_settings()
        layout = self.layout
        head = settings.get_head(settings.tmp_headnum)

        # Auto Sensor & Focal via EXIF
        if head.exif.sensor_width > 0.0 and head.exif.sensor_length > 0.0 \
                and head.exif.focal > 0.0:
            w = head.exif.sensor_width
            h = head.exif.sensor_length
            f = head.exif.focal
            txt = "{:.2f} x {:.2f} mm [{:.2f}]   ".format(w, h, f)
            op = layout.operator(Config.fb_camera_actor_idname,
                                 text=txt + "EXIF Sensor & [EXIF Focal]",
                                 icon='OBJECT_DATAMODE')
            op.headnum = settings.tmp_headnum
            op.action = 'exif_sensor_and_focal'

        # EXIF Focal and Sensor via 35mm equiv.
        if head.exif.focal > 0.0 and head.exif.focal35mm > 0.0:
            f = head.exif.focal
            w, h = get_sensor_size_35mm_equivalent(head)
            txt = "{:.2f} x {:.2f} mm [{:.2f}]   ".format(w, h, f)
            op = layout.operator(Config.fb_camera_actor_idname,
                                 text=txt + "Sensor via 35mm equiv. & [EXIF Focal]",
                                 icon='OBJECT_HIDDEN')
            op.headnum = settings.tmp_headnum
            op.action = 'exif_focal_and_sensor_via_35mm'

        # Auto Sensor & Focal via EXIF 35mm equiv.
        if head.exif.focal > 0.0 and head.exif.focal35mm > 0.0:
            w = 36.0
            h = 24.0
            f = head.exif.focal35mm
            txt = "{:.2f} x {:.2f} mm [{:.2f}]   ".format(w, h, f)
            op = layout.operator(Config.fb_camera_actor_idname,
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
            op = layout.operator(Config.fb_camera_actor_idname,
                                 text=txt + "EXIF Sensor Size",
                                 icon='OBJECT_DATAMODE')
            op.headnum = settings.tmp_headnum
            op.action = 'exif_sensor'

        # Sensor Size (only) via EXIF 35mm equivalent
        if head.exif.focal > 0.0 and head.exif.focal35mm > 0.0:
            w, h = get_sensor_size_35mm_equivalent(head)
            txt = "{:.2f} x {:.2f} mm   ".format(w, h)
            op = layout.operator(Config.fb_camera_actor_idname,
                                 text=txt + "Sensor Size 35mm equivalent",
                                 icon='OBJECT_HIDDEN')
            op.headnum = settings.tmp_headnum
            op.action = 'exif_sensor_via_35mm'

        # ----------------
        layout.separator()

        op = layout.operator(Config.fb_camera_actor_idname,
                             text="36 x 24 mm   35mm Full-frame (default)",
                             icon='FULLSCREEN_ENTER')
        op.headnum = settings.tmp_headnum
        op.action = 'sensor_36x24mm'
