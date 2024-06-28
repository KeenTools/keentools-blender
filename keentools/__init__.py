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
    "name": "KeenTools: FaceBuilder, FaceTracker, GeoTracker 2024.1.0",  # (1/6)
    "version": (2024, 1, 0),  # 2024.1.0 (2/6)
    "author": "KeenTools",
    "description": "FaceBuilder: Create Heads. FaceTracker: Track Heads. GeoTracker: Track Objects",
    "blender": (2, 80, 0),
    "location": "View UI (press N to open tab bar)",
    "wiki_url": "https://keentools.io",
    "doc_url": "https://keentools.io",
    "tracker_url": "https://link.keentools.io/new-support-request",
    "warning": "",
    "category": "Interface"
}

bl_info_copy = bl_info


import os
import sys
import logging.config

from bpy import app as _bpy_app
from bpy import types as _bpy_types
from bpy.types import AddonPreferences
from bpy.utils import register_class, unregister_class

# Only minimal imports are performed to check the start
from .addon_config import Config, output_import_statistics
from .facebuilder_config import FBConfig
from .geotracker_config import GTConfig
from .facetracker_config import FTConfig
from .messages import (ERROR_MESSAGES, draw_warning_labels, get_system_info,
                       draw_system_info, draw_long_label, draw_long_labels)


# Init logging system via config file
base_dir = os.path.dirname(os.path.abspath(__file__))
logging.config.fileConfig(os.path.join(base_dir,
    'logging_debug_console.conf' if 'KEENTOOLS_ENABLE_DEBUG_LOGGING'
    in os.environ else 'logging.conf'),
    disable_existing_loggers=False)
_log = logging.getLogger(__name__)
txt = get_system_info()
txt.append('Addon: {}'.format(bl_info_copy['name']))
txt.append('Package: {}'.format(__package__))
_log.info('\n---\nSystem Info:\n' + '\n'.join(txt) + '\n---\n')


def _is_platform_64bit():
    import platform
    return platform.architecture()[0] == '64bit'


def _is_python_64bit():
    return sys.maxsize > 4294967296  # 2**32


def _is_config_latest():
    return Config.addon_version == '2024.1.0'  # (3/6)


def _is_blender_too_old():
    return _bpy_app.version < Config.minimal_blender_api


def _check_libraries():
    try:
        import numpy
        return True
    except Exception:
        return False


def _check_addon_already_registered() -> bool:
    if hasattr(_bpy_types, FBConfig.fb_header_panel_idname):
        _log.error(f'Another version of KeenTools add-on has been detected: '
                   f'class {FBConfig.fb_header_panel_idname}')
        return True
    if hasattr(_bpy_types, GTConfig.gt_geotrackers_panel_idname):
        _log.error(f'Another version of KeenTools add-on has been detected: '
                   f'class {GTConfig.gt_geotrackers_panel_idname}')
        return True
    if hasattr(_bpy_types, FTConfig.ft_facetrackers_panel_idname):
        _log.error(f'Another version of KeenTools add-on has been detected: '
                   f'class {FTConfig.ft_facetrackers_panel_idname}')
        return True
    return False


def _can_load() -> bool:
    if not _is_platform_64bit():
        _log.error('\n'.join(ERROR_MESSAGES['OS_32_BIT']))
        return False
    if not _is_python_64bit():
        _log.error('\n'.join(ERROR_MESSAGES['BLENDER_32_BIT']))
        return False
    if not _is_config_latest():
        _log.error('\n'.join(ERROR_MESSAGES['NEEDS_RESTART']))
        return False
    if _is_blender_too_old():
        _log.error('\n'.join(ERROR_MESSAGES['BLENDER_TOO_OLD']))
        return False
    if not _check_libraries():
        _log.error('\n'.join(ERROR_MESSAGES['NUMPY_PROBLEM']))
        return False
    if _check_addon_already_registered():
        _log.error('\n'.join(ERROR_MESSAGES['ADDON_REGISTERED']))
        return False
    _log.info('Basic checks have been passed')
    return True


if not _can_load():
    class KTCannotLoadPreferences(AddonPreferences):
        bl_idname = Config.package

        def draw(self, context):
            layout = self.layout

            if not _is_platform_64bit():
                draw_warning_labels(layout, ERROR_MESSAGES['OS_32_BIT'],
                                    alert=True, icon='ERROR')
                draw_system_info(layout)
                return

            if not _is_python_64bit():
                draw_warning_labels(layout, ERROR_MESSAGES['BLENDER_32_BIT'],
                                    alert=True, icon='ERROR')
                draw_system_info(layout)
                return

            if not _is_config_latest():
                draw_warning_labels(layout, ERROR_MESSAGES['NEEDS_RESTART'],
                                    alert=True, icon='ERROR')
                draw_system_info(layout)
                return

            if _is_blender_too_old():
                draw_warning_labels(layout, ERROR_MESSAGES['BLENDER_TOO_OLD'],
                                    alert=True, icon='ERROR')
                draw_system_info(layout)
                return

            if not _check_libraries():
                draw_warning_labels(layout, ERROR_MESSAGES['NUMPY_PROBLEM'],
                                    alert=True, icon='ERROR')

                box = layout.box()
                col = box.column()
                col.scale_y = Config.text_scale_y
                col.label(text='NumPy paths:')
                try:
                    import importlib
                    sp = importlib.util.find_spec('numpy')
                    if sp is not None:
                        if sp.origin:
                            draw_long_label(col, sp.origin, 120)
                        draw_long_labels(col, sp.submodule_search_locations,
                                         120)
                    else:
                        col.label(icon='ERROR',
                                  text='Cannot detect numpy paths.')
                except Exception:
                    col.label(icon='ERROR', text='importlib problems.')
                draw_system_info(layout)
                return

            if _check_addon_already_registered():
                draw_warning_labels(layout, ERROR_MESSAGES['ADDON_REGISTERED'],
                                    alert=True, icon='ERROR')
                draw_system_info(layout)
                return

            draw_warning_labels(layout, ERROR_MESSAGES['UNKNOWN'],
                                alert=True, icon='ERROR')


    def register():
        register_class(KTCannotLoadPreferences)
        _log.error('CANNOT LOAD PREFERENCES REGISTERED')


    def unregister():
        unregister_class(KTCannotLoadPreferences)
        _log.error('CANNOT LOAD PREFERENCES UNREGISTERED')

else:
    from .preferences import CLASSES_TO_REGISTER as PREFERENCES_CLASSES
    from .facebuilder import facebuilder_register, facebuilder_unregister
    from .geotracker import geotracker_register, geotracker_unregister
    from .facetracker import facetracker_register, facetracker_unregister
    from .common.interface.panels import add_timeline_panel, remove_timeline_panel
    from .utils.viewport_state import ViewportStateItem
    from .utils.warning import KT_OT_AddonWarning
    from .utils.common_operators import CLASSES_TO_REGISTER as COMMON_OPERATOR_CLASSES
    from .updater import CLASSES_TO_REGISTER as UPDATER_CLASSES


    CLASSES_TO_REGISTER = PREFERENCES_CLASSES + UPDATER_CLASSES + \
                          COMMON_OPERATOR_CLASSES + (ViewportStateItem,
                                                     KT_OT_AddonWarning,)


    def stop_timers(value: bool = True):
        _log.debug('STOP TIMERS')
        try:
            from .utils.timer import stop_all_working_timers
            stop_all_working_timers(value)
        except Exception as err:
            _log.error(f'stop_timers Exception:\n{str(err)}')
        _log.debug('STOPPED TIMERS')


    def register():
        _log.debug(f'--- START KEENTOOLS ADDON {bl_info_copy["version"]} '
                   f'REGISTER ---')
        stop_timers(False)
        _log.debug('START REGISTER CLASSES')
        for cls in CLASSES_TO_REGISTER:
            _log.debug(f'REGISTER CLASS: \n{str(cls)}')
            register_class(cls)
        _log.info('KeenTools addon classes have been registered')
        facebuilder_register()
        _log.info('FaceBuilder classes have been registered')
        geotracker_register()
        _log.info('GeoTracker classes have been registered')
        facetracker_register()
        _log.info('FaceTracker classes have been registered')
        add_timeline_panel()
        _log.info('Common timeline panel has been registered')
        _log.debug(f'=== KEENTOOLS ADDON {bl_info_copy["version"]} '
                   f'REGISTERED ===\n\n')
        output_import_statistics()


    def unregister():
        _log.debug(f'--- START KEENTOOLS ADDON {bl_info_copy["version"]} '
                   f'UNREGISTER ---')
        stop_timers(True)
        _log.debug('START UNREGISTER CLASSES')
        remove_timeline_panel()
        _log.info('Common timeline panel has been unregistered')
        facetracker_unregister()
        _log.info('FaceTracker classes have been unregistered')
        geotracker_unregister()
        _log.info('GeoTracker classes have been unregistered')
        facebuilder_unregister()
        _log.info('FaceBuilder classes have been unregistered')
        for cls in reversed(CLASSES_TO_REGISTER):
            _log.debug(f'UNREGISTER CLASS: \n{str(cls)}')
            unregister_class(cls)
        _log.info('KeenTools addon classes have been unregistered')
        _log.debug(f'=== KEENTOOLS ADDON {bl_info_copy["version"]} '
                   f'UNREGISTERED ===\n\n')


if __name__ == '__main__':
    _log.info('KeenTools addon direct initialization')
    register()
