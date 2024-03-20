# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C)2023 KeenTools

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

from ...utils.kt_logging import KTLogger
from .panels import (FT_PT_FacetrackersPanel,
                     FT_PT_InputsPanel,
                     FT_PT_CameraPanel,
                     FT_PT_TrackingPanel,
                     FT_PT_MasksPanel,
                     FT_PT_AppearancePanel,
                     FT_PT_SmoothingPanel,
                     FT_PT_ScenePanel,
                     FT_UL_selected_frame_list,
                     FT_PT_TexturePanel,
                     FT_PT_SupportPanel)
from .helps import (FTHELP_OT_InputsHelp,
                    FTHELP_OT_MasksHelp,
                    FTHELP_OT_AnalyzeHelp,
                    FTHELP_OT_CameraHelp,
                    FTHELP_OT_TrackingHelp,
                    FTHELP_OT_AppearanceHelp,
                    FTHELP_OT_TextureHelp,
                    FTHELP_OT_AnimationHelp,
                    FTHELP_OT_RenderingHelp,
                    FTHELP_OT_SmoothingHelp,)
from .menus import (FT_MT_ClipMenu,
                    FT_MT_ClearAllTrackingMenu)

_log = KTLogger(__name__)


CLASSES_TO_REGISTER = (FTHELP_OT_InputsHelp,
                       FTHELP_OT_MasksHelp,
                       FTHELP_OT_AnalyzeHelp,
                       FTHELP_OT_CameraHelp,
                       FTHELP_OT_TrackingHelp,
                       FTHELP_OT_AppearanceHelp,
                       FTHELP_OT_TextureHelp,
                       FTHELP_OT_AnimationHelp,
                       FTHELP_OT_RenderingHelp,
                       FTHELP_OT_SmoothingHelp,
                       FT_PT_FacetrackersPanel,
                       FT_PT_InputsPanel,
                       FT_PT_CameraPanel,
                       FT_PT_TrackingPanel,
                       FT_PT_MasksPanel,
                       FT_PT_SmoothingPanel,
                       FT_PT_ScenePanel,
                       FT_PT_AppearancePanel,
                       FT_UL_selected_frame_list,
                       FT_PT_TexturePanel,
                       FT_PT_SupportPanel,
                       FT_MT_ClipMenu,
                       FT_MT_ClearAllTrackingMenu)
