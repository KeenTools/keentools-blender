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
import addon_utils

from ..addon_config import Config
from ..facebuilder_config import FBConfig, get_fb_settings, set_get_fb_settings
from .head import MESH_OT_FBAddHead
from .settings import FBSceneSettings, FBExifItem, FBCameraItem, FBHeadItem
from ..utils.icons import FBIcons
from .pinmode import FB_OT_PinMode
from .pick_operator import FB_OT_PickMode, FB_OT_PickModeStarter
from .movepin import FB_OT_MovePin
from .actor import FB_OT_HistoryActor, FB_OT_CameraActor
from .main_operator import CLASSES_TO_REGISTER as OPERATOR_CLASSES
from .interface import CLASSES_TO_REGISTER as INTERFACE_CLASSES
from ..utils.ui_redraw import (find_modules_by_name,
                               collapse_all_modules,
                               mark_old_modules)


class FB_PT_OldFaceBuilderWarning(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = FBConfig.fb_tab_category
    bl_context = 'objectmode'
    bl_label = 'Old FaceBuilder detected!'

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.alert = True
        col = box.column()
        col.scale_y = Config.text_scale_y
        col.label(icon='ERROR', text='Please uninstall')
        col.label(text='old FaceBuilder addon!')
        col.label(text='and then restart Blender!')

        row = layout.row()
        row.scale_y = 2.0
        op = row.operator(Config.kt_addon_search_idname,
                          icon='PREFERENCES', text='Show in preferences')
        op.search = 'KeenTools'


class OldFBAddonPreferences(bpy.types.AddonPreferences):
    bl_idname = Config.old_facebuilder_addon_name
    bl_description = 'Fake preferences for showing message to the user'

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.alert = True
        col.label(text='This addon is outdated. Please uninstall it to prevent conflicts.')


class OLDMESH_OT_FBAddHead(bpy.types.Operator):
    bl_idname = Config.old_facebuilder_addon_name + '.add_head'
    bl_label = 'Old FaceBuilder Head'
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = 'Operator to prevent old FaceBuilder addon install'

    def execute(self, context):
        logger = logging.getLogger(__name__)
        log_error = logger.error
        log_error('OLDMESH_OT_FBAddHead call')
        return {'FINISHED'}


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
                       FB_OT_CameraActor,) + OPERATOR_CLASSES + INTERFACE_CLASSES  # + (OLDMESH_OT_FBAddHead,)


def _check_addon_settings_var_exists():
    return hasattr(bpy.types.Scene, FBConfig.fb_global_var_name)


def _unregister_old_facebuilder():
    logger = logging.getLogger(__name__)
    log_error = logger.error
    log_output = logger.debug
    if not _check_addon_settings_var_exists():
        log_output('NO OLD FACEBUILDER HAS BEEN FOUND')
        return

    log_error('OLD FACEBUILDER HAS BEEN FOUND! START DEACTIVATION')

    import sys
    mod = sys.modules.get(Config.old_facebuilder_addon_name)
    log_error(f'OLD MODULE:\n{mod}')

    log_output('START UNREGISTER OLD FB CLASSES')
    if hasattr(mod, 'CLASSES_TO_REGISTER'):
        for cls in reversed(mod.CLASSES_TO_REGISTER):
            log_output(f'UNREGISTER OLD FB CLASS: {str(cls)}')
            try:
                bpy.utils.unregister_class(cls)
            except Exception as err:
                log_error(f'CANNOT UNREGISTER OLD FB CLASS: {cls}\n{str(err)}')
    else:
        log_error('MODULE HAS NO CLASSES_TO_REGISTER')

    if hasattr(mod, 'menu_func'):
        try:
            bpy.types.VIEW3D_MT_mesh_add.remove(mod.menu_func)
            log_output('OLD FB MENU UNREGISTERED')
        except Exception as err:
            log_error(f'CANNOT UNREGISTER OLD FB MENU: \n{str(err)}')
    else:
        log_error('MODULE HAS NO menu_func')

    try:
        _remove_addon_settings_var()
        log_output('OLD FB MAIN VAR UNREGISTERED')
    except Exception as err:
        log_error(f'CANNOT UNREGISTER OLD FB MAIN VAR: \n{str(err)}')

    if hasattr(mod, 'FBIcons'):
        try:
            mod.FBIcons.unregister()
            log_output('OLD FB ICONS UNREGISTERED')
        except Exception as err:
            log_error(f'CANNOT UNREGISTER OLD FB ICONS: \n{str(err)}')
    else:
        log_error('MODULE HAS NO FBIcons')

    try:
        mod.unregister = old_facebuilder_unregister_replacement
        mod.register = old_facebuilder_register_replacement
        log_output('OLD FB HANDLERS HAS BEEN REPLACED')
    except Exception as err:
        log_error(f'CANNOT REGISTER HANDLERS: \n{str(err)}')

    try:
        bpy.utils.register_class(OldFBAddonPreferences)
    except Exception as err:
        log_error(f'CANNOT REGISTER PREFERENCES REPLACEMENT CLASS: \n{str(err)}')

    try:
        addon_utils.disable(Config.old_facebuilder_addon_name, default_set=True)
        log_output('OLD FB ADDON HAS BEEN DISABLED')
    except Exception as err:
        log_error(f'CANNOT REGISTER WARNING CLASS: \n{str(err)}')


def old_facebuilder_register_replacement():
    logger = logging.getLogger(__name__)
    logger.error('OLD FACEBUILDER REGISTER CALL')


def old_facebuilder_unregister_replacement():
    logger = logging.getLogger(__name__)
    logger.error('OLD FACEBUILDER UNREGISTER CALL')


def _add_addon_settings_var():
    setattr(bpy.types.Scene, FBConfig.fb_global_var_name,
            bpy.props.PointerProperty(type=FBSceneSettings))


def _check_addon_settings_var_type():
    if not hasattr(bpy.context.scene, FBConfig.fb_global_var_name):
        return None
    return type(getattr(bpy.context.scene, FBConfig.fb_global_var_name))


def _remove_addon_settings_var():
    delattr(bpy.types.Scene, FBConfig.fb_global_var_name)


def menu_func(self, context):
    settings = get_fb_settings()
    if settings is None:
        return
    if not settings.pinmode:
        self.layout.operator(MESH_OT_FBAddHead.bl_idname, icon='USER')
    else:
        self.layout.label(text='FaceBuilder Head (disabled in PinMode)',
                          icon='USER')


def get_fb_settings_safe():
    name = FBConfig.fb_global_var_name
    if not hasattr(bpy.context.scene, name):
        bpy.app.timers.register(_add_addon_settings_var, first_interval=0.1)
        return None
    return getattr(bpy.context.scene, name)


def facebuilder_register():
    global CLASSES_TO_REGISTER
    logger = logging.getLogger(__name__)

    _unregister_old_facebuilder()

    keentools_mods = find_modules_by_name('KeenTools')
    if len(keentools_mods) > 1:
        collapse_all_modules(keentools_mods)
        mark_old_modules(keentools_mods, name='KeenTools FaceBuilder',
                         category='Add Mesh')

        if FB_PT_OldFaceBuilderWarning not in CLASSES_TO_REGISTER:
            CLASSES_TO_REGISTER = (FB_PT_OldFaceBuilderWarning,) + CLASSES_TO_REGISTER

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

    set_get_fb_settings(get_fb_settings_safe)


def facebuilder_unregister():
    logger = logging.getLogger(__name__)
    logger.debug('START UNREGISTER CLASSES')

    for cls in reversed(CLASSES_TO_REGISTER):
        logger.debug('UNREGISTER FB CLASS: \n{}'.format(str(cls)))
        bpy.utils.unregister_class(cls)

    bpy.types.VIEW3D_MT_mesh_add.remove(menu_func)
    logger.debug('FACEBUILDER ADD MESH MENU UNREGISTERED')
    if _check_addon_settings_var_type() == FBSceneSettings:
        _remove_addon_settings_var()
        logger.debug('MAIN FACEBUILDER VARIABLE UNREGISTERED')
    else:
        logger.error('CANNOT UNREGISTER MAIN FB VAR')

    FBIcons.unregister()
    logger.debug('FACEBUILDER ICONS UNREGISTERED')
