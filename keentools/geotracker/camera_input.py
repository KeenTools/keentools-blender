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
from ..addon_config import gt_settings
from ..tracker.cam_input import (CameraInput,
                                 GeoInput,
                                 ImageInput,
                                 Mask2DInput,
                                 GeoTrackerResultsStorage)


_log = KTLogger(__name__)


class GTCameraInput(CameraInput):
    @classmethod
    def get_settings(cls) -> Any:
        return gt_settings()


class GTGeoInput(GeoInput):
    @classmethod
    def get_settings(cls) -> Any:
        return gt_settings()


class GTImageInput(ImageInput):
    @classmethod
    def get_settings(cls) -> Any:
        return gt_settings()


class GTMask2DInput(Mask2DInput):
    @classmethod
    def get_settings(cls) -> Any:
        return gt_settings()


class GTGeoTrackerResultsStorage(GeoTrackerResultsStorage):
    @classmethod
    def get_settings(cls) -> Any:
        return gt_settings()
