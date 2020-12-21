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

from .menus import *
from .panels import *
from .dialogs import *
from .filedialog import *
from .helps import *
from .updater import *


CLASSES_TO_REGISTER = (FB_MT_ProperViewMenu, # menus
                       FB_MT_ReadExifMenu,
                       FB_MT_ImageGroupMenu,
                       FB_MT_CameraPanelMenu,
                       FB_PT_HeaderPanel,  # panels
                       FB_PT_UpdatePanel,
                       FB_PT_CameraPanel,
                       FB_PT_ViewsPanel,
                       FB_PT_Model,
                       FB_PT_PinSettingsPanel,
                       FB_PT_WireframeSettingsPanel,
                       FB_PT_TexturePanel,
                       FB_PT_BlendShapesPanel,
                       FB_OT_RemindLater, FB_OT_SkipVersion,
                       HELP_OT_CameraHelp,  # helps
                       HELP_OT_ViewsHelp,
                       HELP_OT_ModelHelp,
                       HELP_OT_PinSettingsHelp,
                       HELP_OT_WireframeSettingsHelp,
                       HELP_OT_TextureHelp,
                       HELP_OT_BlendshapesHelp,
                       FB_OT_AddonWarning,  # dialogs
                       FB_OT_BlendshapesWarning,
                       FB_OT_TexSelector,
                       FB_OT_SingleFilebrowser,  # filedialog
                       FB_OT_SingleFilebrowserExec,
                       FB_OT_TextureFileExport,
                       FB_OT_AnimationFilebrowser,
                       FB_OT_MultipleFilebrowser,
                       FB_OT_MultipleFilebrowserExec)
