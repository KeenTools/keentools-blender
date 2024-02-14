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
from typing import List, Any, Dict, Tuple

import bpy
from bpy.types import Area, Window
import addon_utils

from .kt_logging import KTLogger
from .bpy_common import bpy_background_mode, operator_with_context
from ..utils.coords import get_area_region


_log = KTLogger(__name__)


def get_areas_by_type(area_type: str = 'VIEW_3D') -> List[Tuple[Area, Window]]:
    pairs = []
    for window in bpy.data.window_managers['WinMan'].windows:
        for area in window.screen.areas:
            if area.type == area_type:
                pairs.append((area, window))
    return pairs


def get_all_areas() -> List[Area]:
    return [area for window in bpy.data.window_managers['WinMan'].windows
                 for area in window.screen.areas]


def force_ui_redraw(area_type: str = 'PREFERENCES') -> None:
    pairs = get_areas_by_type(area_type)
    for area, _ in pairs:
        area.tag_redraw()


def show_ui_panel(context: Any) -> None:
    try:
        area = context.area
        area.spaces[0].show_region_ui = True
    except Exception:
        pass


def filter_module_list_by_name_starting_with(module_list: List[Any],
                                             name_start: str) -> List[Any]:
    mods = []
    for mod in module_list:
        if hasattr(mod, 'bl_info') and mod.bl_info \
                and 'name' in mod.bl_info.keys() \
                and type(mod.bl_info['name']) == str:
            if mod.bl_info['name'][:len(name_start)].lower() == name_start.lower():
                mods.append(mod)
        else:
            try:
                _log.error(f'Problem with addon description:\n{mod.bl_info}')
            except Exception as err:
                _log.error(f'Exception:\n{str(err)}')
                _log.error(f'Critical error with addon:\n{mod}')
    return mods


def find_modules_by_name_starting_with(name_start: str = 'KeenTools') -> List[Any]:
    try:
        mods = filter_module_list_by_name_starting_with(addon_utils.modules(),
                                                        name_start)
        return mods
    except Exception as err:
        _log.error(f'Module analysis error: {str(err)}')
    return []


def collapse_all_modules(mods: List[Any]) -> None:
    for mod in mods:
        mod.bl_info['show_expanded'] = False


def mark_old_modules(mods: List[Any], filter_dict: Dict) -> None:
    def _mark_outdated(mod):
        mark_text = ' OUTDATED \u2014 REMOVE THIS'  # \u2014 - em dash
        if mod.bl_info['name'][-len(mark_text):] != mark_text:
            mod.bl_info['name'] = mod.bl_info['name'] + mark_text
        mod.bl_info[
            'description'] = 'This add-on is outdated. Please remove it.'
        mod.bl_info['location'] = ''
        mod.bl_info['show_expanded'] = True

    for mod in mods:
        if all([mod.bl_info[key] == filter_dict[key]
                for key in filter_dict.keys()]):
            _mark_outdated(mod)


def total_redraw_ui() -> None:
    ''' This call also updates all texture nodes in scene depsgraph '''
    if not bpy_background_mode():
        bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
        _log.output(_log.color('red', 'total_redraw_ui'))


def total_redraw_ui_overriding_window() -> None:
    ''' This function is actual for Blender 2.80 only '''
    if not bpy_background_mode():
        wm = bpy.context.window_manager
        override = {
            'window': wm.windows[0],
            'screen': wm.windows[0].screen,
        }
        bpy.ops.wm.redraw_timer(override, type='DRAW_WIN_SWAP', iterations=1)
        _log.output(_log.color('red', 'total_redraw_ui_overriding_window'))



def timeline_view_all() -> None:
    _log.output('timeline_view_all')
    pairs = get_areas_by_type('DOPESHEET_EDITOR')
    for area, _ in pairs:
        region = get_area_region(area)
        if not region:
            continue
        _log.output(f'area: {area}')
        operator_with_context(bpy.ops.action.view_all,
                              {'area': area, 'region': region})
