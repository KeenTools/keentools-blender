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
import logging
from typing import List, Optional, Tuple

import bpy
import gpu
import bgl
from gpu_extras.batch import batch_for_shader
from .shaders import (flat_color_3d_vertex_shader,
                      circular_dot_fragment_shader,
                      flat_color_2d_vertex_shader)
from ..addon_config import Config
from ..preferences.user_preferences import UserPreferences


class KTScreenPins:
    def __init__(self):
        self._pins: List[Tuple[float, float]] = []
        self._current_pin: Optional[Tuple[float, float]] = None
        self._current_pin_num: int = -1
        self._disabled_pins: List[int] = []
        self._selected_pins: List[int] = []
        self._add_selection_mode: bool = False

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
        logger = logging.getLogger(__name__)
        log_output = logger.debug
        log_output(f'set_current_pin: {value}')
        self._current_pin = value

    def reset_current_pin(self) -> None:
        logger = logging.getLogger(__name__)
        log_output = logger.debug
        self._current_pin = None
        self._current_pin_num = -1
        log_output(f'reset_current_pin: {self._current_pin}')

    def get_selected_pins(self) -> List:
        return self._selected_pins

    def set_selected_pins(self, selected_pins: List[int]) -> None:
        self._selected_pins = selected_pins

    def add_selected_pins(self, selected_pins: List[int]) -> None:
        self._selected_pins = list(set(self._selected_pins + selected_pins))

    def exclude_selected_pin(self, pin_number: int) -> None:
        self.set_selected_pins([x for x in self.get_selected_pins()
                                if x != pin_number])

    def get_disabled_pins(self) -> List:
        return self._disabled_pins

    def set_disabled_pins(self, disabled_pins: List[int]) -> None:
        self._disabled_pins = disabled_pins

    def clear_selected_pins(self):
        self._selected_pins = []

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


class KTShaderPoints:
    """ Base class for Point Drawing Shaders """
    _is_visible = True
    _point_size = UserPreferences.get_value_safe('pin_size', UserPreferences.type_float)

    # Store all draw handlers registered by class objects
    handler_list = []

    @classmethod
    def is_visible(cls):
        return cls._is_visible

    @classmethod
    def set_visible(cls, flag=True):
        cls._is_visible = flag

    @classmethod
    def add_handler_list(cls, handler):
        cls.handler_list.append(handler)

    @classmethod
    def remove_handler_list(cls, handler):
        if handler in cls.handler_list:
            cls.handler_list.remove(handler)

    @classmethod
    def is_handler_list_empty(cls):
        return len(cls.handler_list) == 0

    def __init__(self, target_class=bpy.types.SpaceView3D):
        self.draw_handler = None  # for 3d shader
        self.shader = None
        self.batch = None

        self.vertices = []
        self.vertices_colors = []

        self._target_class = target_class
        self._work_area = None

    def get_target_class(self):
        return self._target_class

    def set_target_class(self, target_class):
        self._target_class = target_class

    def get_vertices(self):
        return self.vertices

    @classmethod
    def set_point_size(cls, ps):
        cls._point_size = ps

    def _create_batch(self, vertices, vertices_colors,
                      shadername='2D_FLAT_COLOR'):
        if bpy.app.background:
            return
        if shadername == 'CUSTOM_3D':
            # 3D_FLAT_COLOR
            vertex_shader = flat_color_3d_vertex_shader()
            fragment_shader = circular_dot_fragment_shader()

            self.shader = gpu.types.GPUShader(vertex_shader, fragment_shader)

            self.batch = batch_for_shader(
                self.shader, 'POINTS',
                {'pos': vertices, 'color': vertices_colors},
                indices=None
            )
        elif shadername == 'CUSTOM_2D':
            vertex_shader = flat_color_2d_vertex_shader()
            fragment_shader = circular_dot_fragment_shader()

            self.shader = gpu.types.GPUShader(vertex_shader, fragment_shader)

            self.batch = batch_for_shader(
                self.shader, 'POINTS',
                {'pos': vertices, 'color': vertices_colors},
                indices=None
            )
        else:
            self.shader = gpu.shader.from_builtin(shadername)
            self.batch = batch_for_shader(
                self.shader, 'POINTS',
                {'pos': vertices, 'color': vertices_colors}
            )

    def create_batch(self):
        self._create_batch(self.vertices, self.vertices_colors)

    def register_handler(self, context):
        pass

    def unregister_handler(self):
        if self.draw_handler is not None:
            self.get_target_class().draw_handler_remove(
                self.draw_handler, 'WINDOW')
            self.remove_handler_list(self.draw_handler)
        self.draw_handler = None

    def add_vertices_colors(self, verts, colors):
        for i, v in enumerate(verts):
            self.vertices.append(verts[i])
            self.vertices_colors.append(colors[i])

    def set_vertices_colors(self, verts, colors):
        self.vertices = verts
        self.vertices_colors = colors

    def clear_vertices(self):
        self.vertices = []
        self.vertices_colors = []

    def draw_callback(self, context):
        if not self.is_visible():
            return
        # Force Stop
        if self.is_handler_list_empty():
            self.unregister_handler()
            return

        if self._work_area != context.area:
            return

        if self.shader is not None:
            bgl.glPointSize(self._point_size)
            bgl.glEnable(bgl.GL_BLEND)
            self.shader.bind()
            self.batch.draw(self.shader)
            bgl.glDisable(bgl.GL_BLEND)

    def hide_shader(self):
        self.set_visible(False)

    def unhide_shader(self):
        self.set_visible(True)


class KTPoints2D(KTShaderPoints):
    def create_batch(self):
        if bpy.app.background:
            return
        self._create_batch(
            # 2D_FLAT_COLOR
            self.vertices, self.vertices_colors, 'CUSTOM_2D')

    def register_handler(self, context):
        self._work_area = context.area
        self.draw_handler = self.get_target_class().draw_handler_add(
            self.draw_callback, (context,), 'WINDOW', 'POST_PIXEL')
        self.add_handler_list(self.draw_handler)


class KTPoints3D(KTShaderPoints):
    def create_batch(self):
        if bpy.app.background:
            return
        # 3D_FLAT_COLOR
        self._create_batch(self.vertices, self.vertices_colors, 'CUSTOM_3D')

    def __init__(self, target_class):
        super().__init__(target_class)
        self.set_point_size(
            UserPreferences.get_value_safe('pin_size', UserPreferences.type_float) *
            Config.surf_pin_size_scale)

    def register_handler(self, context):
        self._work_area = context.area
        self.draw_handler = self.get_target_class().draw_handler_add(
            self.draw_callback, (context,), 'WINDOW', 'POST_VIEW')
        self.add_handler_list(self.draw_handler)
