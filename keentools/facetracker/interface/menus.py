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

from ...addon_config import ft_settings, ProductType
from ...facetracker_config import FTConfig
from ..ui_strings import buttons


class FT_MT_ClipMenu(Menu):
    bl_idname = FTConfig.ft_clip_menu_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def draw(self, context):
        layout = self.layout
        settings = ft_settings()
        geotracker = settings.get_current_geotracker_item()

        layout.separator()
        col = layout.column()
        op = col.operator(FTConfig.ft_sequence_filebrowser_idname,
                          icon='FILEBROWSER')
        op.product = ProductType.FACETRACKER

        if not geotracker or not geotracker.movie_clip:
            return
        col.separator()
        op = col.operator(FTConfig.ft_video_snapshot_idname, icon='IMAGE')
        op.product = ProductType.FACETRACKER

        col.separator()
        col.operator(FTConfig.ft_split_video_to_frames_exec_idname,
                     icon='RENDER_RESULT')


class FT_MT_ClearAllTrackingMenu(Menu):
    bl_idname = FTConfig.ft_clear_tracking_menu_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def draw(self, context):
        layout = self.layout

        col = layout.column()
        col.operator(FTConfig.ft_clear_tracking_except_keyframes_idname,
                     icon='PANEL_CLOSE')
        col.separator()
        col.operator(FTConfig.ft_clear_all_tracking_idname,
                     icon='CANCEL')
