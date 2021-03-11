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
