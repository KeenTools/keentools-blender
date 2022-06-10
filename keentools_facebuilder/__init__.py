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
    "name": "KeenTools FaceBuilder uninstaller 2022.1.1",  # [1/2]
    "version": (2022, 1, 1),  # 2022.1.1 [2/2]
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
import logging.config
import os
import shutil
import sys

import bpy
import addon_utils


# Init logging system
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(stream=sys.stdout)
handler.setFormatter(logging.Formatter(fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)


_PYKEENTOOLS_RELATIVE_PATH = 'blender_independent_packages/pykeentools_loader/pykeentools'


class FBPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text='This is uninstaller for old FaceBuilder add-on.')
        box.label(text='Please remove it!')


def get_window_manager():
    return bpy.data.window_managers['WinMan']


def get_bpy_preferences():
    return bpy.context.preferences


def get_addons_in_use():
    prefs = get_bpy_preferences()
    return {addon.module for addon in prefs.addons}


def get_all_addons_info():
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


def find_addon_modules_by_name(name, info):
    found = []
    for row in info:
        if row['module'].__name__ == name:
            found.append(row)
    return found


def scan_tree(root_path):
    res = {}
    for dirpath, dirs, files in os.walk(root_path):
        relpath = os.path.relpath(os.path.abspath(dirpath), root_path).replace('\\','/')
        res[relpath] = [name for name in files]
    return res


def find_extra_paths(tree_info, exclude_dirs):
    def _path_is_in_dirs(path, dirs):
        for dir in dirs:
            if path == dir:
                return True
            len_dir = len(dir)
            if len(path) > len_dir and dir == path[:len_dir] and path[len_dir] == '/':
                return True
        return False
    res = {}
    for path in tree_info.keys():
        if not _path_is_in_dirs(path, exclude_dirs):
            res[path] = tree_info[path]
    return res


def copy_dir(from_path, to_path):
    logger = logging.getLogger(__name__)
    log_error = logger.error
    log_output = logger.info
    try:
        log_output(f'TRY COPY TREE:\nSRC: {from_path}\nDST: {to_path}')
        shutil.rmtree(to_path, ignore_errors=True)
        log_output('TARGET PATH IS CLEAR')
        shutil.copytree(from_path, to_path)
        log_output(f'COPYING WAS SUCCESSFUL ')
    except Exception as err:
        log_error(f'CANNOT COPY:\n{str(err)}')
        return False
    return True


def copy_pykeentools(from_dir, to_dir):
    global _PYKEENTOOLS_RELATIVE_PATH
    fb_path = os.path.abspath(os.path.join(from_dir, _PYKEENTOOLS_RELATIVE_PATH))
    kt_path = os.path.abspath(os.path.join(to_dir, _PYKEENTOOLS_RELATIVE_PATH))
    return copy_dir(fb_path, kt_path)


def disable_addon(name):
    logger = logging.getLogger(__name__)
    log_error = logger.error
    log_output = logger.info
    try:
        addon_utils.disable(name, default_set=True)
        log_output(f'ADDON {name} HAS BEEN DEACTIVATED')
    except Exception as err:
        log_error(f'CANNOT DEACTIVATE ADDON {name}:\n{str(err)}')
        return False
    return True


def enable_addon(name):
    logger = logging.getLogger(__name__)
    log_error = logger.error
    log_output = logger.info
    try:
        addon_utils.enable(name, default_set=True)
        log_output(f'ADDON {name} HAS BEEN ACTIVATED')
    except Exception as err:
        log_error(f'CANNOT ACTIVATE ADDON {name}:\n{str(err)}')
        return False
    return True


def remove_keentools_facebuilder_addon(fb_dir):
    logger = logging.getLogger(__name__)
    log_error = logger.error
    log_output = logger.info
    try:
        shutil.rmtree(fb_dir, ignore_errors=True)
        log_output('KEENTOOLS FACEBUILDER ADDON HAS BEEN REMOVED')
    except Exception as err:
        log_error(f'CANNOT REMOVE KEENTOOLS FACEBUILDER ADDON:\n{str(err)}')
        return False
    return True


def anyway_enable_keentools_addon():
    logger = logging.getLogger(__name__)
    log_error = logger.error
    log_error('EXTREME KEENTOOLS ADDON INITIALIZATION')
    enable_addon('keentools')


def register():
    logger = logging.getLogger(__name__)
    log_error = logger.error
    log_output = logger.info

    log_output('register UNINSTALLER')
    overall_info = get_all_modules_info()

    try:
        bpy.utils.register_class(FBPreferences)
    except Exception as err:
        logger.error(f'CANNOT REGISTER PREFERENCES CLASS:\n{str(err)}')

    if 'keentools' not in overall_info['all_module_names']:
        log_error('NO KEENTOOLS ADDON INSTALLED')
        return

    fb_mod_info = find_addon_modules_by_name('keentools_facebuilder',
                                        overall_info['all_addons_info'])
    if len(fb_mod_info) == 0:
        log_error('NO keentools_facebuilder')
        anyway_enable_keentools_addon()
        return

    if len(fb_mod_info) != 1:
        log_error(f'WRONG keentools_facebuilder COUNTER: {fb_mod_info}')

    kt_modules_info = find_addon_modules_by_name(
        'keentools', overall_info['all_addons_info'])

    if len(kt_modules_info) == 0:
        log_error('NO keentools')
        return

    if len(kt_modules_info) != 1:
        log_error(f'WRONG keentools COUNTER: {kt_modules_info}')

    kt_mod_info = kt_modules_info[0]

    fb_dir = os.path.dirname(__file__)
    try:
        kt_dir = os.path.dirname(kt_mod_info['module'].__file__)
    except Exception as err:
        log_error(f'CANNOT GET KEENTOOLS MODULE FILE:\n{str(err)}')
        return

    tree_info = scan_tree(fb_dir)
    if '.' not in tree_info.keys():
        log_error('WRONG STRUCTURE OF FOLDER TREE')
        anyway_enable_keentools_addon()
        return
    else:
        log_output('IT IS PROPER UPDATING STAGE')

    if len(tree_info['.']) > 3:
        log_error('EXTRA FILES EXIST IN KEENTOOLS FACEBUILDER ADDON FOLDER')
        anyway_enable_keentools_addon()
        return

    extra = find_extra_paths(tree_info, ['.', 'blender_independent_packages'])
    if len(extra) > 1:
        log_error('EXTRA FOLDERS EXIST IN KEENTOOLS FACEBUILDER ADDON FOLDER')
        anyway_enable_keentools_addon()
        return

    if _PYKEENTOOLS_RELATIVE_PATH in tree_info.keys():
        copy_pykeentools(fb_dir, kt_dir)
    else:
        log_error('NO PYKEENTOOLS IN FACEBUILDER ADDON')

    if disable_addon('keentools_facebuilder'):
        remove_keentools_facebuilder_addon(fb_dir)

    if enable_addon('keentools'):
        log_output('KEENTOOLS ADDON UPDATE COMPLETE')
    else:
        log_error('THERE WAS PROBLEM WITH KEENTOOLS ADDON UPDATE')


def unregister():
    logger = logging.getLogger(__name__)
    logger.debug('unregister UNINSTALLER')
    try:
        bpy.utils.unregister_class(FBPreferences)
    except Exception as err:
        logger.error(f'CANNOT UNREGISTER PREFERENCES CLASS:\n{str(err)}')


if __name__ == '__main__':
    register()
