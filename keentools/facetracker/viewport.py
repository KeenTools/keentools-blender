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

from typing import Tuple, Optional, Callable, Any, List
import numpy as np

from bpy.types import Object, Area, SpaceView3D, SpaceDopeSheetEditor

from ..utils.kt_logging import KTLogger
from ..addon_config import Config, ProductType, ft_settings
from ..geotracker_config import GTConfig
from ..geotracker.viewport import GTViewport
from ..utils.screen_text import KTScreenText
from ..utils.points import KTPoints2D, KTPoints3D
from ..utils.edges import (KTEdgeShader2D,
                           KTRectangleShader2D,
                           KTEdgeShaderAll2D,
                           KTScreenDashedRectangleShader2D)
from ..utils.polygons import KTRasterMask
from .edges import FTRasterEdgeShader3D
from ..utils.coords import (pin_to_xyz_from_geo_mesh,
                            xy_to_xz_rotation_matrix_3x3,
                            InvScaleFromMatrix)


_log = KTLogger(__name__)


class FTViewport(GTViewport):
    def __init__(self):
        super().__init__()
        self._points2d = KTPoints2D(SpaceView3D)
        self._points3d = KTPoints3D(SpaceView3D)
        self._residuals = KTEdgeShader2D(SpaceView3D)
        self._texter = KTScreenText(SpaceView3D, 'FaceTracker')
        self._wireframer = FTRasterEdgeShader3D(SpaceView3D)
        self._rectangler = KTRectangleShader2D(SpaceView3D)
        self._timeliner = KTEdgeShaderAll2D(SpaceDopeSheetEditor,
                                            GTConfig.timeline_keyframe_color)
        self._selector = KTScreenDashedRectangleShader2D(SpaceView3D)
        self._mask2d = KTRasterMask(SpaceView3D,
                                    mask_color=(*Config.gt_mask_2d_color,
                                                Config.gt_mask_2d_opacity))
        self._draw_update_timer_handler: Optional[Callable] = None

        self.stabilization_region_point: Optional[Tuple[float, float]] = None

    def product_type(self) -> int:
        return ProductType.FACETRACKER

    def get_settings(self) -> Any:
        return ft_settings()

    def surface_points_from_mesh(self, gt: Any, obj: Object,
                                 keyframe: int) -> Any:
        geo = gt.applied_args_model_at(keyframe)
        geo_mesh = geo.mesh(0)
        pins_count = gt.pins_count()
        verts = np.empty((pins_count, 3), dtype=np.float32)
        for i in range(pins_count):
            pin = gt.pin(keyframe, i)
            p = pin_to_xyz_from_geo_mesh(pin, geo_mesh)
            verts[i] = p

        scale_inv = np.array(InvScaleFromMatrix(obj.matrix_world),
                             dtype=np.float32)
        return verts @ xy_to_xz_rotation_matrix_3x3() @ scale_inv
