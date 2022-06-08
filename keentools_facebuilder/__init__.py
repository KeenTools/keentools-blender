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
    "name": "KeenTools FaceBuilder installer 2022.1.1",  # (1/5)
    "version": (2022, 1, 1),  # 2022.1.1 (2/5)
    "author": "KeenTools",
    "description": "KeenTools old FaceBuilder addon uninstaller. "
                   "Use KeenTools addon instead",
    "blender": (2, 80, 0),
    "location": "",
    "wiki_url": "https://keentools.io",
    "tracker_url": "https://link.keentools.io/new-support-request",
    "warning": "",
    "category": "Add Mesh"
}


import logging
from typing import List, Set

import bpy
import addon_utils


class FBPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text='Error message')


def get_window_manager():
    return bpy.data.window_managers['WinMan']


def get_bpy_preferences():
    return bpy.context.preferences


def get_addons_in_use() -> Set[str]:
    prefs = get_bpy_preferences()
    return {addon.module for addon in prefs.addons}


def get_all_addons_info() -> List:
    return [{'module': mod, 'bl_info': addon_utils.module_bl_info(mod)}
            for mod in addon_utils.modules(refresh=False)]


def get_all_modules_info():
    used_addon_names = get_addons_in_use()
    all_addons_info = get_all_addons_info()
    all_module_names = {addon_info['module'].__name__ for addon_info in all_addons_info}
    missing_modules = {name for name in used_addon_names if name not in all_module_names}
    overall_info = {'used_addon_names': used_addon_names,
                    'all_addons_info': all_addons_info,
                    'all_module_names': all_module_names,
                    'missing_modules': missing_modules}
    return overall_info


def register():
    logger = logging.getLogger(__name__)
    log_error = logger.error
    log_output = logger.info

    log_output('register UNINSTALLER')
    overall_info = get_all_modules_info()

    bpy.utils.register_class(FBPreferences)

    if 'keentools' not in overall_info['all_module_names']:
        log_error('NO KEENTOOLS ADDON INSTALLED')
        return

    addon_utils.enable('keentools', default_set=True)
    addon_utils.disable('keentools_facebuilder', default_set=True)


def unregister():
    logger = logging.getLogger(__name__)
    logger.debug('unregister UNINSTALLER')

    bpy.utils.unregister_class(FBPreferences)
