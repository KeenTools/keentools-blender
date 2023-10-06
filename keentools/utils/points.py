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


_log = KTLogger(__name__)


class KTScreenPins:
    ''' Pins are stored in image space coordinates '''
    def __init__(self):
        self._pins: List[Tuple[float, float]] = []
        self._current_pin: Optional[Tuple[float, float]] = None
        self._current_pin_num: int = -1
        self._disabled_pins: List[int] = []
        self._selected_pins: List[int] = []
        self._add_selection_mode: bool = False
        self._move_pin_mode: bool = False

    def arr(self) -> List:
        return self._pins

    def set_pins(self, arr: List[Tuple[float, float]]) -> None:
        self._pins = arr

    def add_pin(self, vec2d: Tuple[float, float]) -> None:
        self._pins.append(vec2d)

    def current_pin_num(self) -> Optional[int]:
        return self._current_pin_num

    def set_current_pin_num(self, value: int) -> None:
        self._current_pin_num = value

    def set_current_pin_num_to_last(self) -> None:
        self._current_pin_num = len(self.arr()) - 1

    def current_pin(self) -> Optional[Tuple[float, float]]:
        return self._current_pin

    def set_current_pin(self, value: Tuple[float, float]) -> None:
        self._current_pin = value

    def reset_current_pin(self) -> None:
        self._current_pin = None
        self._current_pin_num = -1

    def get_selected_pins(self, pins_count: Optional[int]=None) -> List[int]:
        if pins_count is not None:
            self._selected_pins = [x for x in self._selected_pins
                                   if x < pins_count]
        return self._selected_pins

    def average_point_of_selected_pins(self) -> Optional[Tuple[float, float]]:
        ''' Return average point in image space '''
        arr = self.arr()
        selected_pins = self.get_selected_pins(len(arr))
        pins = [arr[x] for x in selected_pins]
        if len(pins) > 0:
            return np.average(pins, axis=0).tolist()
        return None

    def set_selected_pins(self, selected_pins: List[int]) -> None:
        self._selected_pins = selected_pins

    def add_selected_pins(self, selected_pins: List[int]) -> None:
        self._selected_pins = list(set(self._selected_pins + selected_pins))

    def toggle_selected_pins(self, selected_pins: List[int]) -> None:
        old_selected_set = set(self._selected_pins)
        new_selected_set = set(selected_pins)
        self._selected_pins = list(old_selected_set.symmetric_difference(new_selected_set))

    def exclude_selected_pin(self, pin_number: int) -> None:
        self.set_selected_pins([x for x in self.get_selected_pins()
                                if x != pin_number])

    def clear_selected_pins(self) -> None:
        self._selected_pins = []

    def get_disabled_pins(self) -> List[int]:
        return self._disabled_pins

    def set_disabled_pins(self, disabled_pins: List[int]) -> None:
        self._disabled_pins = disabled_pins

    def clear_disabled_pins(self) -> None:
        self._disabled_pins = []

    def pins_inside_rectangle(self, x1: float, y1: float,
                              x2: float, y2: float) -> List[int]:
        if x1 > x2:
            x1, x2 = x2, x1
        if y1 > y2:
            y1, y2 = y2, y1
        return [i for i, p in enumerate(self._pins)
                if x1 <= p[0] <= x2 and y1 <= p[1] <= y2]

    def set_add_selection_mode(self, value: bool) -> None:
        self._add_selection_mode = value

    def get_add_selection_mode(self) -> bool:
        return self._add_selection_mode

    def on_start(self) -> None:
        self.set_add_selection_mode(False)
        self.clear_selected_pins()
        self.clear_disabled_pins()

    def remove_pin(self, index: int) -> None:
        if index in self._selected_pins:
            self._selected_pins.remove(index)
        self._selected_pins = [x if x < index else x - 1
                               for x in self._selected_pins]
        if index in self._disabled_pins:
            self._disabled_pins.remove(index)
        self._disabled_pins = [x if x < index else x - 1
                               for x in self._disabled_pins]
        del self.arr()[index]

    def move_pin_mode(self) -> bool:
        return self._move_pin_mode

    def set_move_pin_mode(self, state: bool) -> None:
        self._move_pin_mode = state


class KTShaderPoints(KTShaderBase):
    def __init__(self, target_class: Any=SpaceView3D):
        super().__init__(target_class)
        self.shader: Any = None
        self.batch: Any = None

        self.vertices: List[Tuple[float, float, float]] = []
        self.vertices_colors: List[Tuple[float, float, float, float]] = []

        self._point_size: float = UserPreferences.get_value_safe(
            'pin_size', UserPreferences.type_float)

    def get_vertices(self) -> List[Tuple[float, float, float]]:
        return self.vertices

    def set_point_size(self, ps: float) -> None:
        self._point_size = ps

    def get_point_size(self) -> float:
        return self._point_size

    def set_vertices_colors(self, verts: List, colors: List) -> None:
        self.vertices = verts
        self.vertices_colors = colors

    def clear_vertices(self) -> None:
        self.vertices = []
        self.vertices_colors = []

    def draw_checks(self, context: Any) -> bool:
        if self.is_handler_list_empty():
            self.unregister_handler()
            return False

        if not self.is_visible():
            return False

        if self.work_area != context.area:
            return False

        if not self.shader or not self.batch:
            return False
        return True

    def draw_main(self, context: Any) -> None:
        set_point_size(self.get_point_size())
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
            {'pos': self.vertices, 'color': self.vertices_colors},
            indices=None)
        self.increment_batch_counter()

    def register_handler(self, context: Any,
                         post_type: str = 'POST_PIXEL') -> None:
        _log.output(f'{self.__class__.__name__}.register_handler')
        super().register_handler(context, post_type)


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
            {'pos': self.vertices, 'color': self.vertices_colors},
            indices=None)
        self.increment_batch_counter()

    def __init__(self, target_class: Any):
        super().__init__(target_class)
        self.set_point_size(
            UserPreferences.get_value_safe(
                'pin_size',
                UserPreferences.type_float) * Config.surf_pin_size_scale)
