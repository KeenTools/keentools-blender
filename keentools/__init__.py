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
    "name": "KeenTools FaceBuilder & GeoTracker 2024.1.0",  # (1/5)
    "version": (2024, 1, 0),  # 2024.1.0 (2/5)
    "author": "KeenTools",
    "description": "FaceBuilder: Create Heads. GeoTracker: Track Objects in videos using 3D models",
    "blender": (2, 80, 0),
    "location": "View UI (press N to open tab bar)",
    "wiki_url": "https://keentools.io",
    "doc_url": "https://keentools.io",
    "tracker_url": "https://link.keentools.io/new-support-request",
    "warning": "",
    "category": "Interface"
}


import os
import sys
import logging.config

from bpy import app as _bpy_app
from bpy.types import AddonPreferences
from bpy.utils import register_class, unregister_class

# Only minimal imports are performed to check the start
from .addon_config import Config, output_import_statistics
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
txt.append('Addon: {}'.format(bl_info['name']))
_log.info('\n---\nSystem Info:\n' + '\n'.join(txt) + '\n---\n')


def _is_platform_64bit():
    import platform
    return platform.architecture()[0] == '64bit'


def _is_python_64bit():
    return sys.maxsize > 4294967296  # 2**32


def _is_config_latest():
    return Config.addon_version == '2024.1.0'  # (3/5)


def _is_blender_too_old():
    return _bpy_app.version < Config.minimal_blender_api


def _check_libraries():
    try:
        import numpy
        return True
    except Exception:
        return False


def _can_load():
    return _is_platform_64bit() and _is_python_64bit() and \
           _is_config_latest() and not _is_blender_too_old() and \
           _check_libraries()


if not _can_load():
    class KTCannotLoadPreferences(AddonPreferences):
        bl_idname = Config.addon_name

        def draw(self, context):
            layout = self.layout
            box = layout.box()

            if not _is_platform_64bit():
                draw_warning_labels(box, ERROR_MESSAGES['OS_32_BIT'],
                                    alert=True, icon='ERROR')
                draw_system_info(layout)
                return

            if not _is_python_64bit():
                draw_warning_labels(box, ERROR_MESSAGES['BLENDER_32_BIT'],
                                    alert=True, icon='ERROR')
                draw_system_info(layout)
                return

            if not _is_config_latest():
                msg = ['Before installing a new add-on version you need '
                       'to relaunch Blender.']
                draw_warning_labels(box, msg, alert=True, icon='ERROR')
                draw_system_info(layout)
                return

            if _is_blender_too_old():
                draw_warning_labels(box, ERROR_MESSAGES['BLENDER_TOO_OLD'],
                                    alert=True, icon='ERROR')
                draw_system_info(layout)
                return

            if not _check_libraries():
                draw_warning_labels(box, ERROR_MESSAGES['NUMPY_PROBLEM'],
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

            draw_warning_labels(box, ERROR_MESSAGES['UNKNOWN'],
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
        _log.debug(f'--- START KEENTOOLS ADDON {bl_info["version"]} '
                   f'REGISTER ---')
        stop_timers(False)
        _log.debug('START REGISTER CLASSES')
        for cls in CLASSES_TO_REGISTER:
            _log.debug('REGISTER CLASS: \n{}'.format(str(cls)))
            register_class(cls)
        _log.info('KeenTools addon classes have been registered')
        facebuilder_register()
        _log.info('FaceBuilder classes have been registered')
        geotracker_register()
        _log.info('GeoTracker classes have been registered')
        facetracker_register()
        _log.info('FaceTracker classes have been registered')
        _log.debug(f'=== KEENTOOLS ADDON {bl_info["version"]} REGISTERED ===')
        output_import_statistics()


    def unregister():
        _log.debug(f'--- START KEENTOOLS ADDON {bl_info["version"]} '
                   f'UNREGISTER ---')
        stop_timers(True)
        _log.debug('START UNREGISTER CLASSES')
        facetracker_unregister()
        _log.info('FaceTracker classes have been unregistered')
        geotracker_unregister()
        _log.info('GeoTracker classes have been unregistered')
        facebuilder_unregister()
        _log.info('FaceBuilder classes have been unregistered')
        for cls in reversed(CLASSES_TO_REGISTER):
            _log.debug('UNREGISTER CLASS: \n{}'.format(str(cls)))
            unregister_class(cls)
        _log.info('KeenTools addon classes have been unregistered')
        _log.debug(f'=== KEENTOOLS ADDON {bl_info["version"]} '
                   f'UNREGISTERED ===')


if __name__ == '__main__':
    _log.info('KeenTools addon direct initialization')
    register()
