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


CLASSES_TO_REGISTER = (OBJECT_MT_FBFixMenu,  # menus
                       OBJECT_MT_FBFixCameraMenu,
                       OBJECT_MT_FBViewMenu,
                       OBJECT_MT_FBSensorWidthMenu,
                       OBJECT_MT_FBFocalLengthMenu,
                       OBJECT_PT_FBHeaderPanel,  # panels
                       OBJECT_PT_FBCameraPanel,
                       OBJECT_PT_FBExifPanel,
                       OBJECT_PT_FBViewsPanel,
                       OBJECT_PT_FBModel,
                       OBJECT_PT_FBPinSettingsPanel,
                       OBJECT_PT_FBColorsPanel,
                       OBJECT_PT_TexturePanel,
                       HELP_OT_CameraHelp,  # helps
                       HELP_OT_ExifHelp,
                       HELP_OT_ViewsHelp,
                       HELP_OT_ModelHelp,
                       HELP_OT_PinSettingsHelp,
                       HELP_OT_TextureHelp,
                       WM_OT_FBAddonWarning,  # dialogs
                       WM_OT_FBTexSelector,
                       WM_OT_FBSingleFilebrowser,  # filedialog
                       WM_OT_FBSingleFilebrowserExec,
                       WM_OT_FBMultipleFilebrowser)
