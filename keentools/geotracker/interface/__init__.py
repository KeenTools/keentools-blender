# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C)2022 KeenTools

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

from .menus import *
from .panels import *
from .filedialogs import *
from .dialogs import *
from .helps import *


CLASSES_TO_REGISTER = (GT_PT_GeotrackersPanel,  # UI panels
                       GT_PT_UpdatePanel,
                       GT_PT_DownloadNotification,
                       GT_PT_DownloadingProblemPanel,
                       GT_PT_UpdatesInstallationPanel,
                       GT_PT_InputsPanel,
                       GT_PT_CameraPanel,
                       GT_PT_TrackingPanel,
                       GT_PT_MasksPanel,
                       GT_PT_SmoothingPanel,
                       GT_PT_ScenePanel,
                       GT_PT_AppearanceSettingsPanel,
                       GT_UL_selected_frame_list,
                       GT_PT_TexturePanel,
                       GT_PT_SupportPanel,
                       GT_OT_SequenceFilebrowser,  # file dialogs
                       GT_OT_MaskSequenceFilebrowser,
                       GT_OT_ChoosePrecalcFile,
                       GT_OT_SplitVideo,
                       GT_OT_SplitVideoExec,
                       GT_OT_VideoSnapshot,
                       GT_OT_ReprojectTextureSequence,
                       GT_OT_AnalyzeCall,
                       GT_OT_PrecalcInfo,
                       GT_OT_TextureBakeOptions,
                       GT_OT_TextureFileExport,
                       GT_OT_ConfirmRecreatePrecalc,
                       GTHELP_OT_InputsHelp,  # helps
                       GTHELP_OT_MasksHelp,
                       GTHELP_OT_AnalyzeHelp,
                       GTHELP_OT_CameraHelp,
                       GTHELP_OT_TrackingHelp,
                       GTHELP_OT_AppearanceHelp,
                       GTHELP_OT_TextureHelp,
                       GTHELP_OT_AnimationHelp,
                       GTHELP_OT_RenderingHelp,
                       GTHELP_OT_SmoothingHelp,
                       GT_MT_ClipMenu,  # menus
                       GT_MT_ClearAllTrackingMenu,
                       GT_OT_ClearAllTrackingMenuExec)
