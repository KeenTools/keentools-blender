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

from bpy.types import Menu
from ..config import Config, get_main_settings


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

        if settings.pinmode and \
                settings.tmp_headnum == settings.current_headnum and \
                settings.tmp_camnum == settings.current_camnum:
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


class FB_MT_ImageGroupMenu(Menu):
    bl_label = "Camera Group"
    bl_idname = Config.fb_image_group_menu_idname
    bl_description = "Camera Group"

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
                Config.fb_camera_actor_idname,
                text="Group {}".format(group))
            op.action = 'to_image_group'
            op.num = group

        op = layout.operator(
            Config.fb_camera_actor_idname,
            text="New group")
        op.action = 'new_image_group'

        layout.separator()
        op = layout.operator(
            Config.fb_camera_actor_idname,
            text="Reset group")
        op.action = 'reset_image_group'

        op = layout.operator(
            Config.fb_camera_actor_idname,
            text="Exclude from grouping")
        op.action = 'make_unique'

        layout.separator()
        op = layout.operator(
            Config.fb_camera_actor_idname,
            text="Get settings from EXIF")
        op.action = 'settings_by_exif'


class FB_MT_CameraPanelMenu(Menu):
    bl_label = "Advanced Camera settings"
    bl_idname = Config.fb_camera_panel_menu_idname
    bl_description = "Advanced Camera settings"

    def draw(self, context):
        settings = get_main_settings()
        layout = self.layout

        head = settings.get_head(settings.current_headnum)

        if head is None:
            return

        if head.smart_mode():
            op = layout.operator(
                Config.fb_camera_actor_idname,
                text='Exclude all views from grouping')
            op.action = 'make_all_unique'
            op.headnum = settings.tmp_headnum

            op = layout.operator(
                Config.fb_camera_actor_idname,
                text='Reset groups for all views')
            op.action = 'reset_all_image_groups'
            op.headnum = settings.tmp_headnum

        layout.separator()
        op = layout.operator(
            Config.fb_camera_actor_idname,
            text='Reset cameras for all views')
        op.action = 'reset_all_camera_settings'
        op.headnum = settings.tmp_headnum

        layout.separator()
        txt = 'Switch to Manual mode' if head.smart_mode() \
            else 'Switch to Default mode'
        op = layout.operator(
            Config.fb_camera_actor_idname,
            text=txt)
        op.action = 'manual_mode'
        op.headnum = settings.tmp_headnum


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
