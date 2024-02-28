# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2023 KeenTools

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

from typing import Tuple, List, Any

from ..utils.kt_logging import KTLogger
from ..geotracker_config import GTConfig
from ..utils.bpy_common import bpy_window_manager


_log = KTLogger(__name__)


_geotracker_keymaps: List[Tuple] = []
_facebuilder_keymaps: List[Tuple] = []


def get_keyconfig() -> Any:
    return bpy_window_manager().keyconfigs.addon


def geotracker_keymaps_register() -> None:
    global _geotracker_keymaps
    _log.yellow('geotracker_keymaps_register start')
    keyconfig = get_keyconfig()
    km = keyconfig.keymaps.new(name='Window', space_type='EMPTY')
    kmi1 = km.keymap_items.new(idname=GTConfig.gt_prev_keyframe_idname,
                               type='LEFT_ARROW',
                               value='PRESS', alt=True)
    kmi2 = km.keymap_items.new(idname=GTConfig.gt_next_keyframe_idname,
                               type='RIGHT_ARROW',
                               value='PRESS', alt=True)
    _geotracker_keymaps.append((km, kmi1))
    _geotracker_keymaps.append((km, kmi2))
    km = keyconfig.keymaps.new(name='3D View Generic', space_type='VIEW_3D')
    kmi3 = km.keymap_items.new(idname=GTConfig.gt_toggle_lock_view_idname,
                               type='L',
                               value='PRESS')
    _geotracker_keymaps.append((km, kmi3))
    _log.output('geotracker_keymaps_register end >>>')


def geotracker_keymaps_unregister() -> None:
    _log.yellow('geotracker_keymaps_unregister start')
    global _geotracker_keymaps
    try:
        for km, kmi in _geotracker_keymaps:
            _log.output(f'unregister keymap item: {kmi}')
            km.keymap_items.remove(kmi)

    except Exception as err:
        _log.error(f'geotracker_keymaps_unregister Exception:\n{str(err)}')
    _geotracker_keymaps.clear()
    _log.output('geotracker_keymaps_unregister end >>>')


def facebuilder_keymaps_register(use_trackpad: bool = False) -> None:
    _log.yellow('facebuilder_keymaps_register start')
    global _facebuilder_keymaps
    keyconfig = get_keyconfig()
    category_name = '3D View Generic'
    space_type = 'VIEW_3D'

    km = keyconfig.keymaps.new(name=category_name, space_type=space_type)

    kmi1 = km.keymap_items.new(idname='keentools_fb.move_wrapper',
                               type='MIDDLEMOUSE',
                               value='PRESS', head=True)
    _facebuilder_keymaps.append((km, kmi1))
    kmi1.active = True

    if use_trackpad:
        kmi2 = km.keymap_items.new(idname='keentools_fb.move_wrapper',
                                   type='TRACKPADPAN',
                                   value='ANY', head=True)
        _facebuilder_keymaps.append((km, kmi2))
        kmi2.active = True

    kmi3 = km.keymap_items.new(idname='keentools_fb.move_wrapper',
                               type='MOUSEROTATE',
                               value='ANY', head=True)
    _facebuilder_keymaps.append((km, kmi3))
    kmi3.active = True

    _log.output('facebuilder_keymaps_register end >>>')


def facebuilder_keymaps_unregister() -> None:
    _log.yellow('facebuilder_keymaps_unregister start')
    global _facebuilder_keymaps
    for km, kmi in _facebuilder_keymaps:
        try:
            _log.output(f'unregister keymap item: {kmi}')
            km.keymap_items.remove(kmi)
        except Exception as err:
            _log.error(f'facebuilder_keymaps_unregister Exception:\n{str(err)}')
    _facebuilder_keymaps.clear()
    _log.output('facebuilder_keymaps_unregister end >>>')
