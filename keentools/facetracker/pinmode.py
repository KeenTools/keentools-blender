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

from typing import Any

from bpy.props import IntProperty, StringProperty, FloatProperty

from ..utils.kt_logging import KTLogger
from ..addon_config import ft_settings, get_addon_preferences
from ..facetracker_config import FTConfig
from ..tracker.pinmode import PinMode
from .ui_strings import buttons
from ..tracker.tracking_blendshapes import reorder_tracking_frames
from ..preferences.hotkeys import (facetracker_keymaps_register,
                                   facetracker_keymaps_unregister)
from ..common.loader import CommonLoader


_log = KTLogger(__name__)


class FT_OT_PinMode(PinMode):
    bl_idname = FTConfig.ft_pinmode_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'INTERNAL'}

    geotracker_num: IntProperty(default=-1)
    pinmode_id: StringProperty(default='')

    camera_clip_start: FloatProperty(default=0.1)
    camera_clip_end: FloatProperty(default=1000.0)

    movepin_operator_idname: str = FTConfig.ft_movepin_idname

    bus_id: IntProperty(default=-1)

    def init_bus(self) -> None:
        message_bus = CommonLoader.message_bus()
        self.bus_id = message_bus.register_item(FTConfig.ft_pinmode_idname)
        _log.output(f'{self.__class__.__name__} bus_id={self.bus_id}')

    @classmethod
    def get_settings(cls) -> Any:
        return ft_settings()

    def perform_checks_before_pinmode(self) -> None:
        settings = self.get_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return
        geomobj = geotracker.geomobj
        if not geomobj or not geomobj.data.shape_keys:
            return
        reorder_tracking_frames(geomobj)

    def register_hotkeys(self) -> None:
        prefs = get_addon_preferences()
        if prefs.ft_use_hotkeys:
            _log.yellow(f'{self.__class__.__name__} register_hotkeys')
            facetracker_keymaps_register()
        else:
            _log.red(f'{self.__class__.__name__} register_hotkeys disabled')

    def unregister_hotkeys(self) -> None:
        _log.yellow(f'{self.__class__.__name__} unregister_hotkeys')
        facetracker_keymaps_unregister()
