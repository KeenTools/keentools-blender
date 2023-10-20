# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2019-2022  KeenTools

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

from typing import Optional, Any

import bpy
from bpy.types import Area, Window, Screen

from .kt_logging import KTLogger
from .bpy_common import operator_with_context


_log = KTLogger(__name__)


def check_context_localview(context: Any) -> bool:
    return context.area and context.area.spaces \
           and context.area.spaces.active \
           and context.area.spaces.active.local_view


def check_area_active_problem(area: Optional[Area]) -> bool:
    return not area or not area.spaces or not area.spaces.active


def enter_area_localview(area: Optional[Area]):
    _log.output(f'enter_area_localview: area={area}')
    if check_area_active_problem(area):
        _log.output('area has problem!')
        return False
    if not area.spaces.active.local_view:
        operator_with_context(bpy.ops.view3d.localview,
                              {'window': bpy.context.window,  # Fix for new temp_context
                               'area': area})
        return True
    return False


def exit_area_localview(area: Optional[Area], window: Optional[Window]=None,
                        screen: Optional[Screen]=None):
    _log.output(f'exit_area_localview: area={area}')
    if check_area_active_problem(area):
        _log.output('exit_area_localview check_area_active_problem')
        return False
    if area.spaces.active.local_view:
        win = bpy.context.window if window is None else window
        scr = bpy.context.screen if screen is None else screen

        if win is None:
            win = bpy.data.window_managers['WinMan'].windows[0]
        if screen is None and win is not None:
            scr = win.screen

        _log.output(f'exit_area_localview context:\n{win}\n{area}\n{scr}\n')

        operator_with_context(bpy.ops.view3d.localview,
                              {'window': win,
                               'area': area,
                               'screen': scr})

        _log.output('exit_area_localview success')
        return True
    return False


def check_localview(area: Optional[Area]) -> bool:
    if check_area_active_problem(area):
        return False
    if not hasattr(area.spaces.active, 'local_view') or \
            not area.spaces.active.local_view:
        return False
    return True
