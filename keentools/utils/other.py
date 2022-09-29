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

import time
import bpy

from .kt_logging import KTLogger
from ..addon_config import Config
from ..utils.attrs import set_custom_attribute, get_safe_custom_attribute
from ..utils.coords import get_area_overlay


_log = KTLogger(__name__)


def _viewport_ui_attribute_names():
    return ['show_floor', 'show_axis_x', 'show_axis_y', 'show_cursor']


def _get_ui_space_data(area):
    return get_area_overlay(area)


def _setup_viewport_ui_state(area, state_dict):
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


def _get_viewport_ui_state(area):
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


def force_show_ui_overlays(area):
    _setup_viewport_ui_state(area, {'show_floor': 1, 'show_axis_x': 1,
                                    'show_axis_y': 1, 'show_cursor': 1})


def force_hide_ui_overlays(area):
    _setup_viewport_ui_state(area, {'show_floor': 0, 'show_axis_x': 0,
                                    'show_axis_y': 0, 'show_cursor': 0})


def hide_viewport_ui_elements_and_store_on_object(area, obj):
    state = _get_viewport_ui_state(area)
    set_custom_attribute(obj, Config.viewport_state_prop_name, state)
    force_hide_ui_overlays(area)


def unhide_viewport_ui_elements_from_object(area, obj):
    def _unpack_state(states):
        attr_names = _viewport_ui_attribute_names()
        values = {}
        for name in attr_names:
            if name in states.keys():
                values[name] = states[name]
        return values

    attr_value = get_safe_custom_attribute(obj, Config.viewport_state_prop_name)
    if attr_value is None:
        force_show_ui_overlays(area)  # For old version compatibility
        return

    try:
        attr_dict = attr_value.to_dict()
    except Exception as err:
        force_show_ui_overlays(area)
        return

    res = _unpack_state(attr_dict)
    _setup_viewport_ui_state(area, res)


# --------------
# FPSMeter usage:
# fps = FPSMeter()
# fps.tick()
# print(fps.update_indicator())
class FPSMeter:
    def __init__(self, buf_length=5):
        self.start_time = time.time()
        self.indicator = "None"
        self.counter = 0
        self.buffer = [self.start_time for _ in range(buf_length)]
        self.head = 0
        self.buf_length = len(self.buffer)

    def prev_index(self, ind):
        prev_ind = ind - 1
        if prev_ind < 0:
            prev_ind = self.buf_length
        return prev_ind

    def next_index(self, ind):
        next_ind = ind + 1
        if next_ind >= self.buf_length:
            next_ind = 0
        return next_ind

    def update_indicator(self):
        new_time = self.buffer[self.head]
        old_time = self.buffer[self.next_index(self.head)]
        delta = new_time - old_time
        d = 0.0
        if delta > 0.00001:
            d = (self.buf_length - 1) / delta
        self.indicator = "{0:.2f}".format(d)
        return self.indicator

    def tick(self):
        self.head = self.next_index(self.head)
        self.buffer[self.head] = time.time()
        self.counter += 1


def bpy_progress_begin(start_val=0, end_val=1):
    bpy.context.window_manager.progress_begin(start_val, end_val)


def bpy_progress_end():
    bpy.context.window_manager.progress_end()
