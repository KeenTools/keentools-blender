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
from ..facetracker_config import (FTConfig,
                                  get_ft_settings)
from .ftloader import FTLoader
from ..tracker.pinmode import PinMode
from .ui_strings import buttons


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

    @classmethod
    def get_loader(cls) -> Any:
        return FTLoader

    @classmethod
    def get_settings(cls) -> Any:
        return get_ft_settings()
