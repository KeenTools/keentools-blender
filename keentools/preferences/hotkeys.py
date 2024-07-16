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

from typing import Tuple, List, Any, Callable, Optional

from ..utils.kt_logging import KTLogger
from ..addon_config import Config
from ..geotracker_config import GTConfig
from ..facetracker_config import FTConfig
from ..utils.bpy_common import bpy_window_manager


_log = KTLogger(__name__)


_tracker_keymaps: List[Tuple] = []
_facebuilder_keymaps: List[Tuple] = []
_native_pan_operator_kmi: Optional[Any] = None


def set_native_pan_operator_kmi(kmi: Any) -> None:
    global _native_pan_operator_kmi
    _native_pan_operator_kmi = kmi


def viewport_native_pan_operator_activate(status: bool) -> bool:
    global _native_pan_operator_kmi
    if not _native_pan_operator_kmi:
        return False
    prev_status = _native_pan_operator_kmi.active
    _native_pan_operator_kmi.active = status
    return prev_status != status


def get_keyconfig() -> Any:
    return bpy_window_manager().keyconfigs.addon


def common_keymaps_register(keymap_list: List[Tuple],
                            keymap: Optional[Any] = None) -> None:
    _log.yellow('common_keymaps_register start')

    keyconfig = get_keyconfig()
    km = keymap if keymap is not None \
        else keyconfig.keymaps.new(name='3D View Generic', space_type='VIEW_3D')

    kmi_pan1 = km.keymap_items.new(idname=Config.kt_move_wrapper_idname,
                                   type='MIDDLEMOUSE',
                                   value='PRESS', head=True)
    keymap_list.append((km, kmi_pan1))
    kmi_pan1.active = True
    _log.output(f'register common keymap item: {kmi_pan1}')

    kmi_pan2 = km.keymap_items.new(idname=Config.kt_move_wrapper_idname,
                                   type='MOUSEROTATE',
                                   value='ANY', head=True)
    keymap_list.append((km, kmi_pan2))
    kmi_pan2.active = True
    _log.output(f'register common keymap item: {kmi_pan2}')

    kmi_pan_detector = km.keymap_items.new(idname=Config.kt_pan_detector_idname,
                                           type='TRACKPADPAN',
                                           value='ANY', head=True)
    keymap_list.append((km, kmi_pan_detector))
    kmi_pan_detector.active = True
    _log.output(f'register common keymap item: {kmi_pan_detector}')

    kmi_pan3 = km.keymap_items.new(idname='view3d.move',
                                   type='TRACKPADPAN',
                                   value='ANY', head=True)
    keymap_list.append((km, kmi_pan3))
    kmi_pan3.active = True
    _log.output(f'register common keymap item: {kmi_pan3}')

    set_native_pan_operator_kmi(kmi_pan3)

    _log.output('common_keymaps_register end >>>')


def geotracker_keymaps_register() -> None:
    _log.yellow('geotracker_keymaps_register start')
    all_keymaps_unregister()

    global _tracker_keymaps
    keyconfig = get_keyconfig()
    km = keyconfig.keymaps.new(name='Window', space_type='EMPTY')
    kmi1 = km.keymap_items.new(idname=GTConfig.gt_prev_keyframe_idname,
                               type='LEFT_ARROW',
                               value='PRESS', alt=True)
    _tracker_keymaps.append((km, kmi1))
    _log.output(f'register gt keymap item: {kmi1}')

    kmi2 = km.keymap_items.new(idname=GTConfig.gt_next_keyframe_idname,
                               type='RIGHT_ARROW',
                               value='PRESS', alt=True)
    _tracker_keymaps.append((km, kmi2))
    _log.output(f'register gt keymap item: {kmi2}')

    km = keyconfig.keymaps.new(name='3D View Generic', space_type='VIEW_3D')
    kmi3 = km.keymap_items.new(idname=GTConfig.gt_toggle_lock_view_idname,
                               type='L',
                               value='PRESS')
    _tracker_keymaps.append((km, kmi3))
    _log.output(f'register gt keymap item: {kmi3}')

    common_keymaps_register(_tracker_keymaps, km)

    _log.output('geotracker_keymaps_register end >>>')


def facetracker_keymaps_register() -> None:
    _log.yellow('facetracker_keymaps_register start')
    all_keymaps_unregister()

    global _tracker_keymaps
    keyconfig = get_keyconfig()
    km = keyconfig.keymaps.new(name='Window', space_type='EMPTY')
    kmi1 = km.keymap_items.new(idname=FTConfig.ft_prev_keyframe_idname,
                               type='LEFT_ARROW',
                               value='PRESS', alt=True)
    _tracker_keymaps.append((km, kmi1))
    _log.output(f'register ft keymap item: {kmi1}')

    kmi2 = km.keymap_items.new(idname=FTConfig.ft_next_keyframe_idname,
                               type='RIGHT_ARROW',
                               value='PRESS', alt=True)
    _tracker_keymaps.append((km, kmi2))
    _log.output(f'register ft keymap item: {kmi2}')

    km = keyconfig.keymaps.new(name='3D View Generic', space_type='VIEW_3D')
    kmi3 = km.keymap_items.new(idname=FTConfig.ft_toggle_lock_view_idname,
                               type='L',
                               value='PRESS')
    _tracker_keymaps.append((km, kmi3))
    _log.output(f'register ft keymap item: {kmi3}')

    common_keymaps_register(_tracker_keymaps, km)

    _log.output('facetracker_keymaps_register end >>>')


def tracker_keymaps_unregister() -> None:
    _log.yellow('tracker_keymaps_unregister start')
    global _tracker_keymaps
    for km, kmi in _tracker_keymaps:
        try:
            _log.output(f'unregister keymap item: {kmi}')
            km.keymap_items.remove(kmi)
        except Exception as err:
            _log.error(f'tracker_keymaps_unregister Exception:\n{str(err)}')
    _tracker_keymaps.clear()
    set_native_pan_operator_kmi(None)
    _log.output('tracker_keymaps_unregister end >>>')


geotracker_keymaps_unregister: Callable = tracker_keymaps_unregister
facetracker_keymaps_unregister: Callable = tracker_keymaps_unregister


def facebuilder_keymaps_register() -> None:
    _log.yellow('facebuilder_keymaps_register start')
    all_keymaps_unregister()

    global _facebuilder_keymaps
    keyconfig = get_keyconfig()

    km = keyconfig.keymaps.new(name='3D View Generic', space_type='VIEW_3D')

    common_keymaps_register(_facebuilder_keymaps, km)

    _log.output('facebuilder_keymaps_register end >>>')


def facebuilder_keymaps_unregister() -> None:
    _log.yellow('facebuilder_keymaps_unregister start')
    global _facebuilder_keymaps
    for km, kmi in _facebuilder_keymaps:
        try:
            _log.output(f'unregister fb keymap item: {kmi}')
            km.keymap_items.remove(kmi)
        except Exception as err:
            _log.error(f'facebuilder_keymaps_unregister Exception:\n{str(err)}')
    _facebuilder_keymaps.clear()
    set_native_pan_operator_kmi(None)
    _log.output('facebuilder_keymaps_unregister end >>>')


def all_keymaps_unregister() -> None:
    _log.yellow('all_keymaps_unregister start')
    facebuilder_keymaps_unregister()
    tracker_keymaps_unregister()
    set_native_pan_operator_kmi(None)
    _log.output('facebuilder_keymaps_unregister end >>>')
