# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2024 KeenTools

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

from typing import Any

from bpy.types import TIME_MT_editor_menus

from ...utils.kt_logging import KTLogger
from ...addon_config import gt_pinmode, ft_pinmode, gt_settings, ft_settings
from ...geotracker_config import GTConfig
from ...facetracker_config import FTConfig


_log = KTLogger(__name__)


def add_timeline_panel() -> None:
    TIME_MT_editor_menus.append(tracker_timeline_panel)


def remove_timeline_panel() -> None:
    TIME_MT_editor_menus.remove(tracker_timeline_panel)


def tracker_timeline_panel(self, context: Any) -> None:
    if gt_pinmode():
        return geotracker_timeline_panel(self, context)
    elif ft_pinmode():
        return facetracker_timeline_panel(self, context)


def geotracker_timeline_panel(self, context: Any) -> None:
    layout = self.layout
    row = layout.row(align=True)
    row.separator()
    row.operator(GTConfig.gt_prev_keyframe_idname, text='',
                 icon='PREV_KEYFRAME')
    row.operator(GTConfig.gt_next_keyframe_idname, text='',
                 icon='NEXT_KEYFRAME')

    settings = gt_settings()

    row2 = row.row(align=True)
    row2.operator(GTConfig.gt_add_keyframe_idname, text='',
                  icon='KEY_HLT')
    row2.operator(GTConfig.gt_remove_keyframe_idname, text='',
                  icon='KEY_DEHLT')

    row2.separator()
    row2.prop(settings, 'stabilize_viewport_enabled',
              icon='LOCKED' if settings.stabilize_viewport_enabled else 'UNLOCKED')


def facetracker_timeline_panel(self, context: Any) -> None:
    layout = self.layout
    row = layout.row(align=True)
    row.separator()
    row.operator(FTConfig.ft_prev_keyframe_idname, text='',
                 icon='PREV_KEYFRAME')
    row.operator(FTConfig.ft_next_keyframe_idname, text='',
                 icon='NEXT_KEYFRAME')

    settings = ft_settings()

    row2 = row.row(align=True)
    row2.active = settings.pinmode
    row2.operator(FTConfig.ft_add_keyframe_idname, text='',
                  icon='KEY_HLT')
    row2.operator(FTConfig.ft_remove_keyframe_idname, text='',
                  icon='KEY_DEHLT')

    row2.separator()
    row2.prop(settings, 'stabilize_viewport_enabled',
              icon='LOCKED' if settings.stabilize_viewport_enabled else 'UNLOCKED')
