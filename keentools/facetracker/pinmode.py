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

from typing import Any, Optional

from bpy.types import Object
from bpy.props import IntProperty, StringProperty, FloatProperty

from ..utils.kt_logging import KTLogger
from ..addon_config import ft_settings, get_addon_preferences, common_loader
from ..facetracker_config import FTConfig
from ..tracker.pinmode import PinMode
from .ui_strings import buttons
from ..tracker.tracking_blendshapes import reorder_tracking_frames
from ..preferences.hotkeys import (facetracker_keymaps_register,
                                   all_keymaps_unregister)
from ..facetracker.callbacks import (
    recalculate_focal as ft_recalculate_focal,
    subscribe_camera_lens_watcher as ft_subscribe_camera_lens_watcher,
    subscribe_movie_clip_color_space_watcher as ft_subscribe_movie_clip_color_space_watcher)

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

    def subscribe_camera_lens_watcher(self, camobj: Optional[Object]) -> None:
        return ft_subscribe_camera_lens_watcher(camobj)

    def subscribe_movie_clip_color_space_watcher(self, geotracker: Any) -> None:
        return ft_subscribe_movie_clip_color_space_watcher(geotracker)

    def recalculate_focal(self, use_current_frame: bool) -> bool:
        return ft_recalculate_focal(use_current_frame)

    def init_bus(self) -> None:
        message_bus = common_loader().message_bus()
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
        if prefs.use_hotkeys:
            _log.yellow(f'{self.__class__.__name__} register_hotkeys')
            facetracker_keymaps_register()
        else:
            _log.red(f'{self.__class__.__name__} register_hotkeys disabled')

    def unregister_hotkeys(self) -> None:
        _log.yellow(f'{self.__class__.__name__} unregister_hotkeys')
        all_keymaps_unregister()
