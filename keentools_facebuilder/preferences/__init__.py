# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2019  KeenTools

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

"""
This module contains everything connected with the addon preferences
"""

from .operators import *
from .ui import FBAddonPreferences

CLASSES_TO_REGISTER = (
    PREF_OT_InstallLicenseOnline,
    PREF_OT_FloatingConnect,
    PREF_OT_InstallLicenseOffline,
    PREF_OT_CopyHardwareId,
    PREF_OT_InstallPkt,
    PREF_OT_OpenPktLicensePage,
    PREF_OT_InstalFromFilePktWithWarning,
    PREF_OT_InstallFromFilePkt,
    PREF_OT_OpenManualInstallPage,
    PREF_OT_ShowURL,
    PREF_OT_OpenURL,
    PREF_OT_DownloadsURL,
    PREF_OT_ShowWhy,
    FBAddonPreferences
)
