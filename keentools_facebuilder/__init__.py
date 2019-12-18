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
    "name": "KeenTools FaceBuilder 1.5.7 (Beta)",
    "author": "KeenTools",
    "description": "Creates Head and Face geometry with a few "
                   "reference photos",
    "blender": (2, 80, 0),
    "location": "Add > Mesh menu and View UI (press N to open panel)",
    "wiki_url": "https://link.keentools.io/fbb-guide",
    "tracker_url": "https://link.keentools.io/new-support-request",
    "warning": "",
    "category": "Add Mesh"
}


import os
import logging.config

import bpy

from .config import Config
from .preferences import CLASSES_TO_REGISTER as PREFERENCES_CLASSES
from .interface import CLASSES_TO_REGISTER as INTERFACE_CLASSES
from .main_operator import CLASSES_TO_REGISTER as OPERATOR_CLASSES
from .head import MESH_OT_FBAddHead
from .body import MESH_OT_FBAddBody
from .settings import FBExifItem, FBCameraItem, FBHeadItem, FBSceneSettings
from .pinmode import FB_OT_PinMode
from .movepin import FB_OT_MovePin
from .actor import FB_OT_Actor, FB_OT_CameraActor

from .utils.icons import FBIcons

CLASSES_TO_REGISTER = (MESH_OT_FBAddHead,
                       MESH_OT_FBAddBody,
                       FBExifItem,
                       FBCameraItem,
                       FBHeadItem,
                       FBSceneSettings,
                       FB_OT_PinMode,
                       FB_OT_MovePin,
                       FB_OT_Actor,
                       FB_OT_CameraActor) + OPERATOR_CLASSES + \
                       INTERFACE_CLASSES + PREFERENCES_CLASSES

# Init logging system via config file
base_dir = os.path.dirname(os.path.abspath(__file__))
logging.config.fileConfig(os.path.join(base_dir, 'logging.conf'))


def _add_addon_settings_var():
    setattr(bpy.types.Scene, Config.addon_global_var_name,
            bpy.props.PointerProperty(type=FBSceneSettings))


def _remove_addon_settings_var():
    delattr(bpy.types.Scene, Config.addon_global_var_name)


def menu_func(self, context):
    self.layout.operator(MESH_OT_FBAddHead.bl_idname, icon='USER')
    # self.layout.operator(MESH_OT_FBAddBody.bl_idname, icon='ARMATURE_DATA')


# Blender predefined methods
def register():
    for cls in CLASSES_TO_REGISTER:
        bpy.utils.register_class(cls)
    bpy.types.VIEW3D_MT_mesh_add.append(menu_func)
    _add_addon_settings_var()

    FBIcons.register()

def unregister():
    for cls in reversed(CLASSES_TO_REGISTER):
        bpy.utils.unregister_class(cls)
    bpy.types.VIEW3D_MT_mesh_add.remove(menu_func)
    _remove_addon_settings_var()

    FBIcons.unregister()

if __name__ == "__main__":
    register()
