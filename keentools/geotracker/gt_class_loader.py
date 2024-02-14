# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2022 KeenTools

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

from ..blender_independent_packages.pykeentools_loader import module as pkt_module


class GTClassLoader:
    @staticmethod
    def GTCameraInput_class():
        from .camera_input import GTCameraInput
        return GTCameraInput

    @staticmethod
    def GTGeoInput_class():
        from .camera_input import GTGeoInput
        return GTGeoInput

    @staticmethod
    def GTImageInput_class():
        from .camera_input import GTImageInput
        return GTImageInput

    @staticmethod
    def GTMask2DInput_class():
        from .camera_input import GTMask2DInput
        return GTMask2DInput

    @staticmethod
    def GTGeoTrackerResultsStorage_class():
        from .camera_input import GTGeoTrackerResultsStorage
        return GTGeoTrackerResultsStorage

    @staticmethod
    def GeoTracker_class():
        return pkt_module().GeoTracker

    @staticmethod
    def FaceTracker_class():
        return pkt_module().FaceTracker

    @staticmethod
    def TrackerFocalLengthMode_class():
        return pkt_module().TrackerFocalLengthMode

    @staticmethod
    def PrecalcRunner_class():
        from .utils.precalc_runner import PrecalcRunner
        return PrecalcRunner

    @staticmethod
    def precalc():
        return pkt_module().precalc

    @staticmethod
    def TRProgressCallBack_class():
        from .utils.progress_callbacks import TRProgressCallBack
        return TRProgressCallBack

    @staticmethod
    def RFProgressCallBack_class():
        from .utils.progress_callbacks import RFProgressCallBack
        return RFProgressCallBack
