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

from typing import Any, List, Callable, Tuple, Optional

from bpy.types import Object, Area, Region, SpaceView3D

from .kt_logging import KTLogger
from .bpy_common import use_gpu_instead_of_bgl


_log = KTLogger(__name__)


class KTShaderBase:
    handler_list: List[Callable] = []

    @classmethod
    def add_handler_list(cls, handler: Callable) -> None:
        cls.handler_list.append(handler)

    @classmethod
    def remove_handler_list(cls, handler: Callable) -> None:
        if handler in cls.handler_list:
            cls.handler_list.remove(handler)

    @classmethod
    def is_handler_list_empty(cls) -> bool:
        return len(cls.handler_list) == 0

    @staticmethod
    def list_for_batch(arr: Any) -> Any:
        return arr if len(arr) > 0 else []

    def __init__(self, target_class: Any=SpaceView3D):
        self.draw_handler: Optional[Any] = None
        self.target_class: Any = target_class
        self.work_area: Optional[Area] = None
        self.is_shader_visible: bool = True
        self.batch_counter: int = 0
        self.draw_counter: int = -1

    def needs_to_be_drawn(self) -> bool:
        return self.batch_counter != self.draw_counter

    def increment_batch_counter(self) -> None:
        self.batch_counter += 1

    def count_draw_call(self) -> None:
        self.draw_counter = self.batch_counter

    def is_visible(self) -> bool:
        return self.is_shader_visible

    def set_visible(self, flag: bool=True) -> None:
        self.is_shader_visible = flag

    def get_target_class(self) -> Any:
        return self.target_class

    def set_target_class(self, target_class: Any) -> None:
        self.target_class = target_class

    def is_working(self) -> bool:
        return not (self.draw_handler is None)

    def init_shaders(self) -> Optional[bool]:
        _log.output(f'{self.__class__.__name__}.init_shaders: pass')
        return None

    def create_batch(self) -> None:
        self.increment_batch_counter()

    def draw_callback(self, context: Any) -> None:
        if self.draw_checks(context):
            self.draw_main(context)
            self.count_draw_call()

    def draw_checks(self, context: Any) -> bool:
        return True

    def draw_main(self, context: Any) -> None:
        pass

    def register_handler(self, context: Any,
                         post_type: str = 'POST_VIEW') -> None:
        _log.output(f'{self.__class__.__name__}.register_handler')
        if self.draw_handler is not None:
            _log.output('draw_handler is not empty, call unregister')
            self.unregister_handler()
            _log.output('continue register')
        self.work_area = context.area
        self.draw_handler = self.get_target_class().draw_handler_add(
            self.draw_callback, (context,), 'WINDOW', post_type)
        self.add_handler_list(self.draw_handler)

    def unregister_handler(self) -> None:
        _log.output(f'{self.__class__.__name__}.unregister_handler')
        if self.draw_handler is not None:
            self.get_target_class().draw_handler_remove(
                self.draw_handler, 'WINDOW')
            self.remove_handler_list(self.draw_handler)
        self.draw_handler = None
        self.work_area = None

    def hide_shader(self) -> None:
        _log.output(f'{self.__class__.__name__}.hide_shader')
        self.set_visible(False)

    def unhide_shader(self) -> None:
        _log.output(f'{self.__class__.__name__}.unhide_shader')
        self.set_visible(True)

    def get_statistics(self):
        return 'No statistics defined'
