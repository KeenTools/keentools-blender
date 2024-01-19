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
    _log.output('geotracker_keymaps_register start')
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
    _log.output('geotracker_keymaps_register end')


def geotracker_keymaps_unregister() -> None:
    _log.output('geotracker_keymaps_unregister start')
    global _geotracker_keymaps
    try:
        for km, kmi in _geotracker_keymaps:
            _log.output(f'unregister keymap item: {kmi}')
            km.keymap_items.remove(kmi)

    except Exception as err:
        _log.error(f'geotracker_keymaps_unregister Exception:\n{str(err)}')
    _geotracker_keymaps.clear()
    _log.output('geotracker_keymaps_unregister end')


def _find_pan_in_keymap(km) -> Any:
    kmi = km.keymap_items.find_from_operator('keentools_fb.move_wrapper')  # view3d.move
    if (kmi and kmi.type == 'MIDDLEMOUSE' and kmi.value == 'PRESS' and
            not kmi.ctrl and not kmi.shift and not kmi.alt):
        return kmi
    return None


def facebuilder_keymaps_register() -> None:
    _log.output('facebuilder_keymaps_register start')
    global _facebuilder_keymaps
    keyconfig = get_keyconfig()
    category_name = '3D View Generic'
    space_type = 'VIEW_3D'
    # keymap = keyconfig.keymaps.find(category_name, space_type=space_type)
    km = keyconfig.keymaps.new(name=category_name, space_type=space_type)
    kmi = _find_pan_in_keymap(km)
    if not kmi:
        kmi = km.keymap_items.new(idname='keentools_fb.move_wrapper', # 'view3d.move',
                                  type='MIDDLEMOUSE',
                                  value='PRESS', head=True)
        _facebuilder_keymaps.append((km, kmi))
    kmi.active = True
    _log.output('facebuilder_keymaps_register end')


def facebuilder_keymaps_unregister() -> None:
    _log.output('facebuilder_keymaps_unregister start')
    global _facebuilder_keymaps
    try:
        for km, kmi in _facebuilder_keymaps:
            _log.output(f'unregister keymap item: {kmi}')
            km.keymap_items.remove(kmi)

    except Exception as err:
        _log.error(f'facebuilder_keymaps_unregister Exception:\n{str(err)}')
    _facebuilder_keymaps.clear()
    _log.output('facebuilder_keymaps_unregister end')
