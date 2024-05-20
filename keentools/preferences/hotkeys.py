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
from ..facebuilder_config import FBConfig
from ..geotracker_config import GTConfig
from ..facetracker_config import FTConfig
from ..utils.bpy_common import bpy_window_manager


_log = KTLogger(__name__)


_tracker_keymaps: List[Tuple] = []
_facebuilder_keymaps: List[Tuple] = []
_pan_detector_kmi: Optional[Any] = None


def viewport_pan_detector_activate(status: bool) -> None:
    global _pan_detector_kmi
    if not _pan_detector_kmi:
        return
    _pan_detector_kmi.active = status


def get_keyconfig() -> Any:
    return bpy_window_manager().keyconfigs.addon


def geotracker_keymaps_register(use_trackpad: bool = True) -> None:
    _log.yellow('geotracker_keymaps_register start')
    geotracker_keymaps_unregister()

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

    kmi_pan1 = km.keymap_items.new(idname=GTConfig.gt_move_wrapper,
                                   type='MIDDLEMOUSE',
                                   value='PRESS', head=True)
    _tracker_keymaps.append((km, kmi_pan1))
    kmi_pan1.active = True
    _log.output(f'register fb keymap item: {kmi_pan1}')

    kmi_pan2 = km.keymap_items.new(idname=GTConfig.gt_move_wrapper,
                                   type='MOUSEROTATE',
                                   value='ANY', head=True)
    _tracker_keymaps.append((km, kmi_pan2))
    kmi_pan2.active = True
    _log.output(f'register fb keymap item: {kmi_pan2}')

    if use_trackpad:
        kmi_pan3 = km.keymap_items.new(idname='view3d.move',
                                       type='TRACKPADPAN',
                                       value='ANY', head=True)
        _tracker_keymaps.append((km, kmi_pan3))
        kmi_pan3.active = True
        _log.output(f'register fb keymap item: {kmi_pan3}')

        global _pan_detector_kmi
        _pan_detector_kmi = km.keymap_items.new(idname=GTConfig.gt_pan_detector,
                                                type='TRACKPADPAN',
                                                value='ANY', head=True)
        _tracker_keymaps.append((km, _pan_detector_kmi))
        _pan_detector_kmi.active = True
        _log.output(f'register fb keymap item: {_pan_detector_kmi}')

    _log.output('geotracker_keymaps_register end >>>')


def facetracker_keymaps_register(use_trackpad: bool = True) -> None:
    _log.yellow('facetracker_keymaps_register start')
    facetracker_keymaps_unregister()

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

    kmi_pan1 = km.keymap_items.new(idname=FTConfig.ft_move_wrapper,
                                   type='MIDDLEMOUSE',
                                   value='PRESS', head=True)
    _tracker_keymaps.append((km, kmi_pan1))
    kmi_pan1.active = True
    _log.output(f'register fb keymap item: {kmi_pan1}')

    kmi_pan2 = km.keymap_items.new(idname=FTConfig.ft_move_wrapper,
                                   type='MOUSEROTATE',
                                   value='ANY', head=True)
    _tracker_keymaps.append((km, kmi_pan2))
    kmi_pan2.active = True
    _log.output(f'register fb keymap item: {kmi_pan2}')

    if use_trackpad:
        kmi_pan3 = km.keymap_items.new(idname='view3d.move',
                                       type='TRACKPADPAN',
                                       value='ANY', head=True)
        _tracker_keymaps.append((km, kmi_pan3))
        kmi_pan3.active = True
        _log.output(f'register fb keymap item: {kmi_pan3}')

        global _pan_detector_kmi
        _pan_detector_kmi = km.keymap_items.new(idname=FTConfig.ft_pan_detector,
                                                type='TRACKPADPAN',
                                                value='ANY', head=True)
        _tracker_keymaps.append((km, _pan_detector_kmi))
        _pan_detector_kmi.active = True
        _log.output(f'register fb keymap item: {_pan_detector_kmi}')

    _log.output('facetracker_keymaps_register end >>>')


def tracker_keymaps_unregister() -> None:
    _log.yellow('tracker_keymaps_unregister start')
    global _tracker_keymaps
    try:
        for km, kmi in _tracker_keymaps:
            _log.output(f'unregister keymap item: {kmi}')
            km.keymap_items.remove(kmi)

    except Exception as err:
        _log.error(f'tracker_keymaps_unregister Exception:\n{str(err)}')
    _tracker_keymaps.clear()
    global _pan_detector_kmi
    _pan_detector_kmi = None
    _log.output('tracker_keymaps_unregister end >>>')


geotracker_keymaps_unregister: Callable = tracker_keymaps_unregister
facetracker_keymaps_unregister: Callable = tracker_keymaps_unregister


def facebuilder_keymaps_register(use_trackpad: bool = True) -> None:
    _log.yellow('facebuilder_keymaps_register start')
    facebuilder_keymaps_unregister()

    global _facebuilder_keymaps
    keyconfig = get_keyconfig()
    category_name = '3D View Generic'
    space_type = 'VIEW_3D'

    km = keyconfig.keymaps.new(name=category_name, space_type=space_type)

    kmi_pan1 = km.keymap_items.new(idname=FBConfig.fb_move_wrapper,
                                   type='MIDDLEMOUSE',
                                   value='PRESS', head=True)
    _facebuilder_keymaps.append((km, kmi_pan1))
    kmi_pan1.active = True
    _log.output(f'register fb keymap item: {kmi_pan1}')

    kmi_pan2 = km.keymap_items.new(idname=FBConfig.fb_move_wrapper,
                                   type='MOUSEROTATE',
                                   value='ANY', head=True)
    _facebuilder_keymaps.append((km, kmi_pan2))
    kmi_pan2.active = True
    _log.output(f'register fb keymap item: {kmi_pan2}')

    if use_trackpad:
        kmi_pan3 = km.keymap_items.new(idname='view3d.move',
                                       type='TRACKPADPAN',
                                       value='ANY', head=True)
        _facebuilder_keymaps.append((km, kmi_pan3))
        kmi_pan3.active = True
        _log.output(f'register fb keymap item: {kmi_pan3}')

        global _pan_detector_kmi
        _pan_detector_kmi = km.keymap_items.new(idname=FBConfig.fb_pan_detector,
                                                type='TRACKPADPAN',
                                                value='ANY', head=True)
        _facebuilder_keymaps.append((km, _pan_detector_kmi))
        _pan_detector_kmi.active = True
        _log.output(f'register fb keymap item: {_pan_detector_kmi}')

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
    global _pan_detector_kmi
    _pan_detector_kmi = None
    _log.output('facebuilder_keymaps_unregister end >>>')
