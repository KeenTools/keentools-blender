# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2019-2023  KeenTools

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

from bpy.types import Menu, Operator

from ...addon_config import gt_settings, ProductType
from ...geotracker_config import GTConfig
from ...utils.bpy_common import bpy_call_menu
from ..ui_strings import buttons


class GT_MT_ClipMenu(Menu):
    bl_idname = GTConfig.gt_clip_menu_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def draw(self, context):
        layout = self.layout
        settings = gt_settings()
        geotracker = settings.get_current_geotracker_item()

        layout.separator()
        col = layout.column()
        op = col.operator(GTConfig.gt_sequence_filebrowser_idname,
                          icon='FILEBROWSER')
        op.product = ProductType.GEOTRACKER

        if not geotracker or not geotracker.movie_clip:
            return
        col.separator()
        op = col.operator(GTConfig.gt_video_snapshot_idname, icon='IMAGE')
        op.product = ProductType.GEOTRACKER

        col.separator()
        op = col.operator(GTConfig.gt_split_video_to_frames_exec_idname,
                          icon='RENDER_RESULT')
        op.product = ProductType.GEOTRACKER


class GT_MT_ClearAllTrackingMenu(Menu):
    bl_idname = GTConfig.gt_clear_tracking_menu_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def draw(self, context):
        layout = self.layout

        col = layout.column()
        col.operator(GTConfig.gt_clear_tracking_except_keyframes_idname,
                     icon='PANEL_CLOSE')
        col.separator()
        col.operator(GTConfig.gt_clear_all_tracking_idname,
                     icon='CANCEL')


class GT_OT_ClearAllTrackingMenuExec(Operator):
    bl_idname = GTConfig.gt_clear_tracking_menu_exec_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'UNDO'}

    def draw(self, context):
        pass

    def execute(self, context):
        bpy_call_menu('INVOKE_DEFAULT',
                      name=GTConfig.gt_clear_tracking_menu_idname)
        return {'FINISHED'}
