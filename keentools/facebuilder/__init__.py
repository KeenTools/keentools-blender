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

from bpy.types import Panel, AddonPreferences, Scene, VIEW3D_MT_mesh_add
from bpy.utils import register_class, unregister_class
import addon_utils

from ..utils.kt_logging import KTLogger
from ..addon_config import (Config,
                            fb_settings,
                            add_addon_settings_var,
                            remove_addon_settings_var,
                            check_addon_settings_var_exists,
                            check_addon_settings_var_type)
from .head import MESH_OT_FBAddHead
from .settings import FBSceneSettings, FBExifItem, FBCameraItem, FBHeadItem
from .pinmode import FB_OT_PinMode
from .pick_operator import FB_OT_PickMode, FB_OT_PickModeStarter
from .movepin import FB_OT_MovePin
from .actor import FB_OT_HistoryActor, FB_OT_CameraActor
from .main_operator import CLASSES_TO_REGISTER as OPERATOR_CLASSES
from .interface import CLASSES_TO_REGISTER as INTERFACE_CLASSES
from ..utils.ui_redraw import (find_modules_by_name_starting_with,
                               collapse_all_modules,
                               mark_old_modules)


_log = KTLogger(__name__)


class FB_PT_OldFaceBuilderWarning(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = Config.fb_tab_category
    bl_context = 'objectmode'
    bl_label = 'Remove old FaceBuilder'

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.alert = True
        col = box.column()
        col.scale_y = Config.text_scale_y
        col.label(icon='ERROR', text='To continue using FaceBuilder ')
        col.label(text='you need to remove the old')
        col.label(text='version of the add-on manually')

        row = layout.row()
        row.scale_y = 2.0
        op = row.operator(Config.kt_addon_search_idname,
                          icon='PREFERENCES', text='Open preferences')
        op.search = 'KeenTools'


class OldFBAddonPreferences(AddonPreferences):
    bl_idname = Config.old_facebuilder_addon_name
    bl_description = 'Preferences replacement for showing message to the user'

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.scale_y = Config.text_scale_y
        col.alert = True
        col.label(text='This add-on is outdated. '
                       'Please remove it before using the new version.')


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


def _unregister_old_facebuilder() -> None:
    if not check_addon_settings_var_exists(Config.fb_global_var_name):
        _log.output('NO OLD FACEBUILDER HAS BEEN FOUND')
        return

    _log.error('OLD FACEBUILDER HAS BEEN FOUND! START DEACTIVATION')

    import sys
    mod = sys.modules.get(Config.old_facebuilder_addon_name)
    _log.error(f'OLD MODULE:\n{mod}')

    try:
        addon_utils.disable(Config.old_facebuilder_addon_name, default_set=True)
        _log.output('OLD FB ADDON HAS BEEN DISABLED')
    except Exception as err:
        _log.error(f'CANNOT DISABLE OLD FB: \n{str(err)}')

    try:
        mod.unregister = old_facebuilder_unregister_replacement
        mod.register = old_facebuilder_register_replacement
        _log.output('OLD FB HANDLERS HAS BEEN REPLACED')
    except Exception as err:
        _log.error(f'CANNOT REGISTER HANDLERS: \n{str(err)}')

    try:
        register_class(OldFBAddonPreferences)
    except Exception as err:
        _log.error(f'CANNOT REGISTER PREFERENCES REPLACEMENT CLASS: \n{str(err)}')


def old_facebuilder_register_replacement() -> None:
    _log.error('OLD FACEBUILDER REGISTER CALL')


def old_facebuilder_unregister_replacement() -> None:
    _log.error('OLD FACEBUILDER UNREGISTER CALL')


def menu_fb_func(self, context):
    settings = fb_settings()
    if settings is None:
        return
    if not settings.pinmode:
        self.layout.operator(MESH_OT_FBAddHead.bl_idname, icon='USER')
    else:
        self.layout.label(text='FaceBuilder Head (disabled in PinMode)',
                          icon='USER')


def facebuilder_register():
    _log.output('--- START FACEBUILDER REGISTER ---')
    global CLASSES_TO_REGISTER

    _unregister_old_facebuilder()

    old_addon_title = 'KeenTools FaceBuilder'
    old_addon_category = 'Add Mesh'
    keentools_fb_mods = find_modules_by_name_starting_with(old_addon_title)
    if len(keentools_fb_mods) > 1:
        collapse_all_modules(keentools_fb_mods)
        mark_old_modules(keentools_fb_mods, {'category': old_addon_category})

        if FB_PT_OldFaceBuilderWarning not in CLASSES_TO_REGISTER:
            CLASSES_TO_REGISTER = (FB_PT_OldFaceBuilderWarning,) + CLASSES_TO_REGISTER

    _log.output('FACEBUILDER REGISTER CLASSES')
    for cls in CLASSES_TO_REGISTER:
        _log.output(f'REGISTER FB CLASS:\n{str(cls)}')
        register_class(cls)

    _log.output('FACEBUILDER ADD MESH MENU REGISTER')
    VIEW3D_MT_mesh_add.append(menu_fb_func)
    _log.output('MAIN FACEBUILDER VARIABLE REGISTER')
    add_addon_settings_var(Config.fb_global_var_name, FBSceneSettings)
    _log.output('MAIN FACEBUILDER VARIABLE REGISTERED')
    _log.output('=== FACEBUILDER REGISTERED ===')


def facebuilder_unregister() -> None:
    _log.output('--- START FACEBUILDER UNREGISTER ---')

    _log.output('FACEBUILDER UNREGISTER CLASSES')
    for cls in reversed(CLASSES_TO_REGISTER):
        _log.output(f'UNREGISTER FB CLASS:\n{str(cls)}')
        unregister_class(cls)

    _log.output('FACEBUILDER ADD MESH MENU UNREGISTER')
    VIEW3D_MT_mesh_add.remove(menu_fb_func)

    try:
        if check_addon_settings_var_type(Config.fb_global_var_name) == FBSceneSettings:
            remove_addon_settings_var(Config.fb_global_var_name)
            _log.output('MAIN FACEBUILDER VARIABLE UNREGISTERED')
        else:
            _log.error('CANNOT UNREGISTER MAIN FB VAR')
    except Exception as err:
        _log.error(f'FACEBUILDER UNREGISTER VARIABLE ERROR:\n{str(err)}')

    _log.output('=== FACEBUILDER UNREGISTERED ===')
