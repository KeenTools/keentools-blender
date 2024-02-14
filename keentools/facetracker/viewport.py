# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2019-2024  KeenTools

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

from typing import Tuple, Optional, Callable

from bpy.types import Object, Area, SpaceView3D, SpaceDopeSheetEditor

from ..utils.kt_logging import KTLogger
from ..addon_config import gt_settings
from ..geotracker_config import GTConfig
from ..geotracker.viewport import GTViewport
from ..utils.screen_text import KTScreenText
from ..utils.points import KTPoints2D, KTPoints3D
from ..utils.edges import (KTEdgeShader2D,
                           KTLitEdgeShaderLocal3D,
                           KTEdgeShaderAll2D,
                           KTScreenDashedRectangleShader2D)
from ..utils.polygons import KTRasterMask
from ..preferences.user_preferences import UserPreferences
from .edges import FTRasterEdgeShader3D


_log = KTLogger(__name__)


class FTViewport(GTViewport):
    def __init__(self):
        super().__init__()
        self._points2d = KTPoints2D(SpaceView3D)
        self._points3d = KTPoints3D(SpaceView3D)
        self._residuals = KTEdgeShader2D(SpaceView3D)
        self._texter = KTScreenText(SpaceView3D)
        self._wireframer = FTRasterEdgeShader3D(SpaceView3D)
        self._timeliner = KTEdgeShaderAll2D(SpaceDopeSheetEditor,
                                            GTConfig.timeline_keyframe_color)
        self._selector = KTScreenDashedRectangleShader2D(SpaceView3D)
        self._mask2d = KTRasterMask(SpaceView3D, mask_color=(
            *UserPreferences.get_value_safe('gt_mask_2d_color',
                                            UserPreferences.type_color),
            UserPreferences.get_value_safe('gt_mask_2d_opacity',
                                           UserPreferences.type_float)))
        self._draw_update_timer_handler: Optional[Callable] = None

        self.stabilization_region_point: Optional[Tuple[float, float]] = None
