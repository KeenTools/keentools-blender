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

from typing import List, Optional, Tuple, Any

import numpy as np
from bpy.types import SpaceView3D
from gpu_extras.batch import batch_for_shader

from .kt_logging import KTLogger
from ..addon_config import Config
from .gpu_shaders import (circular_dot_2d_shader,
                          circular_dot_3d_shader)
from ..preferences.user_preferences import UserPreferences
from .base_shaders import KTShaderBase
from .gpu_control import set_blend_alpha, set_point_size
from ..utils.bpy_common import bpy_context


_log = KTLogger(__name__)


class KTScreenPins:
    ''' Pins are stored in image space coordinates '''
    def __init__(self):
        self._pins: Any = np.empty((0, 2), dtype=np.float32)
        self._current_pin_num: int = -1
        self._disabled_pins: Any = np.empty((0,), dtype=np.int32)
        self._selected_pins: Any = np.empty((0,), dtype=np.int32)
        self._add_selection_mode: bool = False
        self._move_pin_mode: bool = False

    def arr(self) -> Any:
        return self._pins

    def set_pins(self, arr: Any) -> None:
        _log.output(f'set_pins: {len(arr)}')
        self._pins = arr
        assert len(self._pins.shape) == 2

    def clear_pins(self) -> None:
        _log.output('clear_pins')
        self.reset_current_pin()
        self.clear_disabled_pins()
        self.clear_selected_pins()
        self.set_pins(np.empty((0, 2), dtype=np.float32))

    def add_pin(self, vec2d: Tuple[float, float]) -> None:
        _log.output(f'add_pin: {vec2d}')
        row = np.array([vec2d], dtype=np.float32)
        self.set_pins(np.append(self._pins, row, axis=0))

    def current_pin_num(self) -> Optional[int]:
        return self._current_pin_num

    def set_current_pin_num(self, value: int) -> None:
        _log.output(f'set_current_pin_num: {value}')
        self._current_pin_num = value

    def set_current_pin_num_to_last(self) -> None:
        self._current_pin_num = len(self.arr()) - 1
        _log.output(f'set_current_pin_num_to_last: {self._current_pin_num}')

    def current_pin(self) -> bool:
        return self._current_pin_num >= 0

    def reset_current_pin(self) -> None:
        _log.output('reset_current_pin')
        self._current_pin_num = -1

    def get_selected_pins(self, pins_count: Optional[int] = None) -> Any:
        if pins_count is not None:
            self._selected_pins = self._selected_pins[self._selected_pins < pins_count]
        return self._selected_pins

    def average_point_of_selected_pins(self) -> Optional[Tuple[float, float]]:
        ''' Return average point in image space '''
        arr = self.arr()
        selected_pins = self.get_selected_pins(len(arr))
        if len(selected_pins) == 0:
            return None
        return np.average(arr[selected_pins], axis=0).tolist()

    def set_selected_pins(self, selected_pins: Any) -> None:
        _log.output('set_selected_pins')
        self._selected_pins = np.array(selected_pins, dtype=np.int32)

    def add_selected_pins(self, selected_pins: Any) -> None:
        _log.output('add_selected_pins')
        self.set_selected_pins(np.unique(
            np.concatenate((self._selected_pins,
                            np.array(selected_pins, dtype=np.int32)))))

    def toggle_selected_pins(self, selected_pins: Any) -> None:
        _log.output('toggle_selected_pins')
        old_selected_set = set(self._selected_pins)
        new_selected_set = set(selected_pins)
        self._selected_pins = np.array(
            list(old_selected_set.symmetric_difference(new_selected_set)),
            dtype=np.int32)

    def exclude_selected_pin(self, pin_number: int) -> None:
        _log.output('exclude_selected_pin')
        self._selected_pins = self._selected_pins[self._selected_pins != pin_number]
        self.reset_current_pin()

    def clear_selected_pins(self) -> None:
        _log.output('clear_selected_pins')
        self._selected_pins = np.empty((0,), dtype=np.int32)

    def get_disabled_pins(self) -> Any:
        return self._disabled_pins

    def set_disabled_pins(self, disabled_pins: List[int]) -> None:
        _log.output('set_disabled_pins')
        self._disabled_pins = np.array(disabled_pins, dtype=np.int32)

    def clear_disabled_pins(self) -> None:
        _log.output('clear_disabled_pins')
        self._disabled_pins = np.empty((0,), dtype=np.int32)

    def pins_inside_rectangle(self, x1: float, y1: float,
                              x2: float, y2: float) -> Any:
        if x1 > x2:
            x1, x2 = x2, x1
        if y1 > y2:
            y1, y2 = y2, y1
        return np.array([i for i, p in enumerate(self._pins)
                         if x1 <= p[0] <= x2 and y1 <= p[1] <= y2],
                        dtype=np.int32)

    def set_add_selection_mode(self, value: bool) -> None:
        self._add_selection_mode = value

    def get_add_selection_mode(self) -> bool:
        return self._add_selection_mode

    def on_start(self) -> None:
        _log.output('on_start')
        self.set_add_selection_mode(False)
        self.set_move_pin_mode(False)
        self.reset_current_pin()
        self.clear_selected_pins()
        self.clear_disabled_pins()

    def clear_all(self) -> None:
        _log.output('clear_all')
        self.set_add_selection_mode(False)
        self.set_move_pin_mode(False)
        self.clear_pins()

    def remove_pin(self, index: int) -> None:
        _log.output(f'remove_pin: {index}')
        pins = self.arr()
        if index >= len(pins):
            return
        self._selected_pins = np.array([x if x < index else x - 1
                                        for x in self._selected_pins
                                        if x != index], dtype=np.int32)
        self._disabled_pins = np.array([x if x < index else x - 1
                                        for x in self._disabled_pins
                                        if x != index], dtype=np.int32)
        self.set_pins(np.delete(pins, index, axis=0))

    def move_pin_mode(self) -> bool:
        return self._move_pin_mode

    def set_move_pin_mode(self, state: bool) -> None:
        self._move_pin_mode = state


class KTShaderPoints(KTShaderBase):
    def __init__(self, target_class: Any=SpaceView3D):
        super().__init__(target_class)
        self.shader: Any = None
        self.batch: Any = None

        self.vertices: Any = np.empty((0, 3), dtype=np.float32)
        self.vertex_colors: Any = np.empty((0, 4), dtype=np.float32)

        self._point_size: float = UserPreferences.get_value_safe(
            'pin_size', UserPreferences.type_float)
        self._point_scale: float = 1.0

    def get_vertices(self) -> Any:
        return self.vertices

    def set_point_size(self, ps: float) -> None:
        self._point_size = ps

    def get_point_size(self) -> float:
        return self._point_size

    def set_point_scale(self, ps: float) -> None:
        self._point_scale = ps

    def set_vertices_and_colors(self, verts: Any, colors: Any) -> None:
        self.vertices = verts
        self.vertex_colors = colors

    def clear_vertices(self) -> None:
        self.vertices = np.empty((0, 3), dtype=np.float32)
        self.vertex_colors = np.empty((0, 4), dtype=np.float32)

    def clear_all(self) -> None:
        self.clear_vertices()

    def draw_checks(self) -> bool:
        if self.is_handler_list_empty():
            self.unregister_handler()
            return False

        if not self.is_visible():
            return False

        if not self.work_area or self.work_area != bpy_context().area:
            return False

        if not self.shader or not self.batch:
            return False
        return True

    def draw_main(self) -> None:
        set_point_size(self.get_point_size() * self._point_scale)
        set_blend_alpha()
        self.shader.bind()
        self.batch.draw(self.shader)


class KTPoints2D(KTShaderPoints):
    def init_shaders(self) -> Optional[bool]:
        if self.shader is not None:
            _log.output(f'{self.__class__.__name__}.shader: skip')
            return None

        self.shader = circular_dot_2d_shader()
        res = self.shader is not None
        _log.output(f'{self.__class__.__name__}.shader: {res}')
        return res

    def create_batch(self) -> None:
        if self.shader is None:
            _log.error(f'{self.__class__.__name__}.shader: is empty')
            return

        self.batch = batch_for_shader(
            self.shader, 'POINTS',
            {'pos': self.list_for_batch(self.vertices),
             'color': self.list_for_batch(self.vertex_colors)},
            indices=None)
        self.increment_batch_counter()

    def register_handler(self, post_type: str = 'POST_PIXEL', *, area: Any) -> None:
        _log.yellow(f'{self.__class__.__name__}.register_handler')
        _log.output('call super().register_handler')
        super().register_handler(post_type, area=area)


class KTPoints3D(KTShaderPoints):
    def init_shaders(self) -> Optional[bool]:
        if self.shader is not None:
            _log.output(f'{self.__class__.__name__}.shader: skip')
            return None

        self.shader = circular_dot_3d_shader()
        res = self.shader is not None
        _log.output(f'{self.__class__.__name__}.shader: {res}')
        return res

    def create_batch(self) -> None:
        if self.shader is None:
            _log.error(f'{self.__class__.__name__}.shader: is empty')
            return
        self.batch = batch_for_shader(
            self.shader, 'POINTS',
            {'pos': self.list_for_batch(self.vertices),
             'color': self.list_for_batch(self.vertex_colors)},
            indices=None)
        self.increment_batch_counter()

    def __init__(self, target_class: Any):
        super().__init__(target_class)
        self.set_point_size(
            UserPreferences.get_value_safe(
                'pin_size',
                UserPreferences.type_float) * Config.surf_pin_size_scale)
