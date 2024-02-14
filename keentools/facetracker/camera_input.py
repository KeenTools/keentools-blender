# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2022-2023 KeenTools

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
from ..addon_config import ft_settings
from ..tracker.cam_input import (CameraInput,
                                 GeoInput,
                                 ImageInput,
                                 Mask2DInput,
                                 GeoTrackerResultsStorage)
from ..utils.mesh_builder import build_geo_from_basis


_log = KTLogger(__name__)


class FTCameraInput(CameraInput):
    @classmethod
    def get_settings(cls) -> Any:
        return ft_settings()


class FTGeoInput(GeoInput):
    @classmethod
    def get_settings(cls) -> Any:
        return ft_settings()

    def geo(self) -> Any:
        settings = self.get_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return None
        return build_geo_from_basis(geotracker.geomobj, get_uv=False)


class FTImageInput(ImageInput):
    @classmethod
    def get_settings(cls) -> Any:
        return ft_settings()


class FTMask2DInput(Mask2DInput):
    @classmethod
    def get_settings(cls) -> Any:
        return ft_settings()


class FTGeoTrackerResultsStorage(GeoTrackerResultsStorage):
    @classmethod
    def get_settings(cls) -> Any:
        return ft_settings()
