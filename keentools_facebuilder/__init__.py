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


bl_info = {
    "name": "KeenTools FaceBuilder (Beta)",
    "author": "KeenTools",
    "description": "Creates Head and Face geometry with a few "
                   "reference photos",
    "blender": (2, 80, 0),
    "location": "View3D > Add > Mesh and View UI (press N to open panel)",
    "wiki_url": "https://www.keentools.io/facebuilder",
    "tracker_url": "https://www.keentools.io/contact",
    "warning": "",
    "category": "Add Mesh"
}


import os
import logging.config
import bpy
import keentools_facebuilder.preferences
from . config import Config
from . panels import (OBJECT_PT_FBHeaderPanel, OBJECT_PT_FBCameraPanel,
                      OBJECT_PT_FBPanel, OBJECT_PT_FBFaceParts,
                      WM_OT_FBAddonWarning, OBJECT_PT_FBSettingsPanel,
                      OBJECT_PT_FBColorsPanel, OBJECT_PT_TBPanel,
                      OBJECT_MT_FBFixMenu, OBJECT_MT_FBFixCameraMenu)
from . head import MESH_OT_FBAddHead
from . body import MESH_OT_FBAddBody
from . settings import FBCameraItem
from . settings import FBHeadItem
from . settings import FBSceneSettings
from . main_operator import (OBJECT_OT_FBSelectCamera, OBJECT_OT_FBCenterGeo,
                             OBJECT_OT_FBUnmorph, OBJECT_OT_FBRemovePins,
                             OBJECT_OT_FBWireframeColor,
                             OBJECT_OT_FBFilterCameras, OBJECT_OT_FBFixSize,
                             OBJECT_OT_FBCameraFixSize,
                             OBJECT_OT_FBDeleteCamera, OBJECT_OT_FBAddCamera,
                             OBJECT_OT_FBAddonSettings,
                             OBJECT_OT_FBBakeTexture, OBJECT_OT_FBShowTexture,
                             OBJECT_OT_FBDefaultSensor, OBJECT_OT_FBAllUnknown)
from . pinmode import OBJECT_OT_FBPinMode
from . movepin import OBJECT_OT_FBMovePin
from . actor import OBJECT_OT_FBActor
from . filedialog import WM_OT_FBOpenFilebrowser
from . config import Config


# Init logging system via config file
base_dir = os.path.dirname(os.path.abspath(__file__))
logging.config.fileConfig(os.path.join(base_dir, 'logging.conf'))


_CLASSES_TO_REGISTER = (
    OBJECT_PT_FBHeaderPanel,
    OBJECT_PT_FBCameraPanel,
    OBJECT_PT_FBPanel,
    OBJECT_PT_FBFaceParts,
    OBJECT_PT_FBColorsPanel,
    OBJECT_PT_TBPanel,
    OBJECT_MT_FBFixMenu,
    OBJECT_MT_FBFixCameraMenu,
    WM_OT_FBAddonWarning,
    MESH_OT_FBAddHead,
    MESH_OT_FBAddBody,
    OBJECT_OT_FBSelectCamera,
    OBJECT_OT_FBCenterGeo,
    OBJECT_OT_FBUnmorph,
    OBJECT_OT_FBRemovePins,
    OBJECT_OT_FBWireframeColor,
    OBJECT_OT_FBFilterCameras,
    OBJECT_OT_FBDeleteCamera,
    OBJECT_OT_FBAddCamera,
    OBJECT_OT_FBFixSize,
    OBJECT_OT_FBCameraFixSize,
    OBJECT_OT_FBAddonSettings,
    OBJECT_OT_FBBakeTexture,
    OBJECT_OT_FBShowTexture,
    OBJECT_OT_FBDefaultSensor,
    OBJECT_OT_FBAllUnknown,
    FBCameraItem,
    FBHeadItem,
    FBSceneSettings,
    OBJECT_PT_FBSettingsPanel,
    OBJECT_OT_FBPinMode,
    OBJECT_OT_FBMovePin,
    OBJECT_OT_FBActor,
    WM_OT_FBOpenFilebrowser) + preferences.CLASSES_TO_REGISTER


def menu_func(self, context):
    self.layout.operator(MESH_OT_FBAddHead.bl_idname, icon='USER')
    # self.layout.operator(MESH_OT_FBAddBody.bl_idname, icon='ARMATURE_DATA')


def register():
    for cls in _CLASSES_TO_REGISTER:
        bpy.utils.register_class(cls)
    bpy.types.VIEW3D_MT_mesh_add.append(menu_func)
    # Main addon settings variable creation
    setattr(bpy.types.Scene, Config.addon_global_var_name,
            bpy.props.PointerProperty(type=FBSceneSettings))


def unregister():
    for cls in reversed(_CLASSES_TO_REGISTER):
        bpy.utils.unregister_class(cls)
    bpy.types.VIEW3D_MT_mesh_add.remove(menu_func)
    # Delete addon settings
    delattr(bpy.types.Scene, Config.addon_global_var_name)


if __name__ == "__main__":
    register()
