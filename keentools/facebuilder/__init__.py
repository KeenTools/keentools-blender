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
import logging
import bpy

from ..facebuilder_config import FBConfig, get_fb_settings
from .head import MESH_OT_FBAddHead
from .settings import FBSceneSettings, FBExifItem, FBCameraItem, FBHeadItem
from ..utils.icons import FBIcons
from .pinmode import FB_OT_PinMode
from .pick_operator import FB_OT_PickMode, FB_OT_PickModeStarter
from .movepin import FB_OT_MovePin
from .actor import FB_OT_HistoryActor, FB_OT_CameraActor
from .main_operator import CLASSES_TO_REGISTER as OPERATOR_CLASSES
from .interface import CLASSES_TO_REGISTER as INTERFACE_CLASSES


CLASSES_TO_REGISTER = (MESH_OT_FBAddHead,
                       FBExifItem,
                       FBCameraItem,
                       FBHeadItem,
                       FBSceneSettings,
                       FB_OT_PinMode,
                       FB_OT_PickMode,
                       FB_OT_PickModeStarter,
                       FB_OT_MovePin,
                       FB_OT_HistoryActor,
                       FB_OT_CameraActor,) + OPERATOR_CLASSES + INTERFACE_CLASSES


def _add_addon_settings_var():
    setattr(bpy.types.Scene, FBConfig.fb_global_var_name,
            bpy.props.PointerProperty(type=FBSceneSettings))


def _remove_addon_settings_var():
    delattr(bpy.types.Scene, FBConfig.fb_global_var_name)


def menu_func(self, context):
    settings = get_fb_settings()
    if not settings.pinmode:
        self.layout.operator(MESH_OT_FBAddHead.bl_idname, icon='USER')
    else:
        self.layout.label(text='FaceBuilder Head (disabled in PinMode)',
                          icon='USER')


def facebuilder_register():
    logger = logging.getLogger(__name__)
    logger.debug('START FACEBUILDER REGISTER CLASSES')

    for cls in CLASSES_TO_REGISTER:
        logger.debug('REGISTER FB CLASS: \n{}'.format(str(cls)))
        bpy.utils.register_class(cls)

    bpy.types.VIEW3D_MT_mesh_add.append(menu_func)
    logger.debug('FACEBUILDER ADD MESH MENU REGISTERED')
    _add_addon_settings_var()
    logger.debug('MAIN FACEBUILDER VARIABLE REGISTERED')

    FBIcons.register()
    logger.debug('FACEBUILDER ICONS REGISTERED')


def facebuilder_unregister():
    logger = logging.getLogger(__name__)
    logger.debug('START UNREGISTER CLASSES')

    for cls in reversed(CLASSES_TO_REGISTER):
        logger.debug('UNREGISTER CLASS: \n{}'.format(str(cls)))
        bpy.utils.unregister_class(cls)

    bpy.types.VIEW3D_MT_mesh_add.remove(menu_func)
    logger.debug('FACEBUILDER ADD MESH MENU UNREGISTERED')
    _remove_addon_settings_var()
    logger.debug('MAIN FACEBUILDER VARIABLE UNREGISTERED')

    FBIcons.unregister()
    logger.debug('FACEBUILDER ICONS UNREGISTERED')
