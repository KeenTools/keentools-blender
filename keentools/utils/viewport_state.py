# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2019-2023 KeenTools

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

from typing import Optional, Any, Dict, List

from bpy.types import Area, PropertyGroup
from bpy.props import BoolProperty

from .kt_logging import KTLogger


_log = KTLogger(__name__)


def get_area_overlay(area: Area) -> Optional[Any]:
    if not area or not area.spaces.active:
        return None
    return area.spaces.active.overlay


def _viewport_ui_attribute_names() -> List:
    return ['show_floor', 'show_axis_x', 'show_axis_y', 'show_axis_z',
            'show_cursor']


def _get_ui_space_data(area: Area) -> Any:
    return get_area_overlay(area)


def _setup_viewport_ui_state(area: Area, state_dict: Dict) -> None:
    python_obj = _get_ui_space_data(area)
    if python_obj is None:
        _log.error(f'_setup_viewport_ui_state: overlay does not exist. area={area}')
        return
    attr_names = _viewport_ui_attribute_names()
    for name in attr_names:
        if name in state_dict.keys() and hasattr(python_obj, name):
            try:
                setattr(python_obj, name, state_dict[name])
            except Exception as err:
                _log.error(f'EXCEPTION _setup_viewport_ui_state: {str(err)}')


def _get_viewport_ui_state(area: Area) -> Dict:
    python_obj = _get_ui_space_data(area)
    attr_names = _viewport_ui_attribute_names()
    res = {}
    for name in attr_names:
        if hasattr(python_obj, name):
            try:
                res[name] = getattr(python_obj, name)
            except Exception as err:
                _log.error(f'EXCEPTION _get_viewport_ui_state: {str(err)}')
    return res


def force_show_ui_overlays(area: Area) -> None:
    _log.output('force_show_ui_overlays')
    _setup_viewport_ui_state(area, {'show_floor': 1, 'show_axis_x': 1,
                                    'show_axis_y': 1, 'show_axis_z': 0,
                                    'show_cursor': 1})


def force_hide_ui_overlays(area: Area) -> None:
    _log.output('force_hide_ui_overlays')
    _setup_viewport_ui_state(area, {'show_floor': 0, 'show_axis_x': 0,
                                    'show_axis_y': 0, 'show_axis_z': 0,
                                    'show_cursor': 0})


class ViewportStateItem(PropertyGroup):
    show_floor: BoolProperty(default=True)
    show_axis_x: BoolProperty(default=True)
    show_axis_y: BoolProperty(default=True)
    show_axis_z: BoolProperty(default=False)
    show_cursor: BoolProperty(default=True)
    loaded: BoolProperty(default=False)

    def get_from_area(self, area: Area) -> bool:
        _log.output('get_from_area')
        overlay = get_area_overlay(area)
        if not overlay:
            return False
        try:
            self.show_floor = overlay.show_floor
            self.show_axis_x = overlay.show_axis_x
            self.show_axis_y = overlay.show_axis_y
            self.show_axis_z = overlay.show_axis_z
            self.show_cursor = overlay.show_cursor
            self.loaded = True
        except Exception as err:
            _log.error(f'ViewportStateItem get_from_area Exception:\n{str(err)}')
            return False
        return True

    def put_to_area(self, area: Area) -> bool:
        _log.output('put_to_area')
        overlay = get_area_overlay(area)
        if not overlay:
            return False
        try:
            overlay.show_floor = self.show_floor
            overlay.show_axis_x = self.show_axis_x
            overlay.show_axis_y = self.show_axis_y
            overlay.show_axis_z = self.show_axis_z
            overlay.show_cursor = self.show_cursor
            self.loaded = False
        except Exception as err:
            _log.error(f'ViewportStateItem put_to_area Exception:\n{str(err)}')
            return False
        return True

    def hide_ui_elements(self, area: Area, forced: bool=False) -> None:
        _log.output('hide_ui_elements')
        if forced or not self.loaded:
            self.get_from_area(area)
        force_hide_ui_overlays(area)

    def show_ui_elements(self, area: Area, forced: bool=False) -> None:
        _log.output('show_ui_elements')
        if self.loaded and not forced:
            self.put_to_area(area)
        else:
            force_show_ui_overlays(area)
            self.loaded = False
