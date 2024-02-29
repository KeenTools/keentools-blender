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
from ...addon_config import fb_settings
from ...facebuilder_config import FBConfig


class FB_MT_ProperViewMenu(Menu):
    bl_label = "View operations"
    bl_idname = FBConfig.fb_proper_view_menu_idname
    bl_description = "View operations"

    def draw(self, context):
        settings = fb_settings()
        layout = self.layout

        op = layout.operator(
            FBConfig.fb_delete_camera_idname,
            text='Delete this view', icon='CANCEL')
        op.headnum = settings.tmp_headnum
        op.camnum = settings.tmp_camnum

        layout.operator(FBConfig.fb_single_filebrowser_exec_idname,
                        text='Open file', icon='FILEBROWSER')

        layout.separator()

        if settings.pinmode and \
                settings.tmp_headnum == settings.current_headnum and \
                settings.tmp_camnum == settings.current_camnum:
            op = layout.operator(FBConfig.fb_rotate_image_cw_idname,
                                 text='Rotate CW', icon='LOOP_FORWARDS')
            op.headnum = settings.tmp_headnum
            op.camnum = settings.tmp_camnum

            op = layout.operator(FBConfig.fb_rotate_image_ccw_idname,
                                 text='Rotate CCW', icon='LOOP_BACK')
            op.headnum = settings.tmp_headnum
            op.camnum = settings.tmp_camnum

            op = layout.operator(FBConfig.fb_reset_image_rotation_idname,
                                 text='Reset Orientation',
                                 icon='OUTLINER_OB_IMAGE')
            op.headnum = settings.tmp_headnum
            op.camnum = settings.tmp_camnum
        else:
            layout.label(text='Rotate CW', icon='LOOP_FORWARDS')
            layout.label(text='Rotate CCW', icon='LOOP_BACK')
            layout.label(text='Reset Orientation', icon='OUTLINER_OB_IMAGE')


CLASSES_TO_REGISTER = (FB_MT_ProperViewMenu,)
