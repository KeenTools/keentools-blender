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
from .ui import (reset_updater_preferences_to_default,
                 KTPREF_OT_UserPreferencesChanger,
                 GTPREF_OT_UserPreferencesGetColors,
                 FBPREF_OT_UserPreferencesGetColors,
                 FBPREF_OT_UserPreferencesResetAll,
                 GTPREF_OT_UserPreferencesResetAll,
                 KTPREF_OT_UserPreferencesResetAllWarning,
                 KTAddonPreferences)

CLASSES_TO_REGISTER = (
    KTPREF_OT_InstallLicenseOnline,
    KTPREF_OT_FloatingConnect,
    KTPREF_OT_InstallLicenseOffline,
    KTPREF_OT_CopyHardwareId,
    KTPREF_OT_InstallPkt,
    KTPREF_OT_OpenPktLicensePage,
    KTPREF_OT_InstalFromFilePktWithWarning,
    KTPREF_OT_InstallFromFilePkt,
    KTPREF_OT_OpenManualInstallPage,
    KTPREF_OT_OpenURL,
    KTPREF_OT_DownloadsURL,
    KTPREF_OT_ComputerInfo,
    KTPREFS_OT_UninstallCore,
    KTPREF_OT_UserPreferencesChanger,
    FBPREF_OT_UserPreferencesGetColors,
    GTPREF_OT_UserPreferencesGetColors,
    FBPREF_OT_UserPreferencesResetAll,
    GTPREF_OT_UserPreferencesResetAll,
    KTPREF_OT_UserPreferencesResetAllWarning,
    KTAddonPreferences
)
