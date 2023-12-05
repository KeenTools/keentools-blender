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

from ..utils.kt_logging import KTLogger
from ..facetracker_config import get_ft_settings
from ..utils.bpy_common import bpy_current_frame
from ..tracker.loader import Loader
from ..tracker.class_loader import KTClassLoader


_log = KTLogger(__name__)


class FTLoader(Loader):
    @classmethod
    def get_settings(cls) -> Any:
        return get_ft_settings()

    @classmethod
    def get_geo(cls) -> Any:
        gt = cls.kt_geotracker()
        geo = gt.applied_args_model_at(bpy_current_frame())
        return geo

    @classmethod
    def new_kt_geotracker(cls) -> Any:
        _log.output(_log.color('magenta', '*** new_kt_facetracker ***'))
        cls._geo_input = KTClassLoader.FTGeoInput_class()()
        cls._image_input = KTClassLoader.FTImageInput_class()()
        cls._camera_input = KTClassLoader.FTCameraInput_class()()
        cls._mask2d = KTClassLoader.FTMask2DInput_class()()
        cls._storage = KTClassLoader.FTGeoTrackerResultsStorage_class()()

        cls._kt_geotracker = KTClassLoader.FaceTracker_class()(
            cls._geo_input,
            cls._camera_input,
            cls._image_input,
            cls._mask2d,
            cls._storage
        )
        return cls._kt_geotracker


FTLoader.init_handlers()
