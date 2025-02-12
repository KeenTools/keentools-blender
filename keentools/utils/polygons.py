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

from typing import Any, List, Tuple, Optional

from bpy.types import Object, Area, Region, Image
from gpu_extras.batch import batch_for_shader

from ..utils.kt_logging import KTLogger
from ..geotracker_config import GTConfig
from .images import check_gl_image
from .base_shaders import KTShaderBase
from .gpu_shaders import raster_image_mask_shader, raster_image_background_shader
from .gpu_control import (set_blend_alpha, set_shader_sampler)
from ..utils.bpy_common import bpy_context


_log = KTLogger(__name__)


class KTRasterMask(KTShaderBase):
    def __init__(self, target_class: Any, mask_color=GTConfig.mask_2d_color):
        super().__init__(target_class)
        self.square: List[Tuple[float, float]] = [(0., 0.), (1., 0.),
                                                  (1., 1), (0., 1)]
        self.vertices: List[Tuple[float, float]] = self.square
        self.uvs: List[Tuple[float, float]] = self.square
        self.color: Tuple[float, float, float, float] = mask_color
        self.mask_shader: Any = None
        self.mask_batch: Any = None
        self.inverted: bool = False
        self.left: Tuple[float, float] = (100., 100.)
        self.right: Tuple[float, float] = (400., 200.)
        self.image: Optional[Image] = None
        self.mask_threshold: float = 0.0
        self.channel: int = 4  # RGB

    def init_shaders(self) -> Optional[bool]:
        if self.mask_shader is not None:
            _log.output(f'{self.__class__.__name__}.mask_shader: skip')
            return None

        self.mask_shader = raster_image_mask_shader()
        res = self.mask_shader is not None
        _log.output(f'{self.__class__.__name__}.mask_shader: {res}')
        return res

    def create_batch(self) -> None:
        if self.mask_shader is None:
            _log.error(f'{self.__class__.__name__}.mask_shader: is empty')
            return
        self.mask_batch = batch_for_shader(
            self.mask_shader, 'TRI_FAN',
            {'pos': self.list_for_batch(self.vertices),
             'texCoord': self.list_for_batch(self.uvs)})

    def draw_checks(self) -> bool:
        if self.is_handler_list_empty():
            self.unregister_handler()
            return False

        if self.mask_shader is None or self.mask_batch is None:
            return False

        if not self.work_area or self.work_area != bpy_context().area:
            return False

        if not self.image:
            return False

        if not check_gl_image(self.image):
            _log.error(f'{self.__class__.__name__}.draw_checks '
                       f'check_gl_image failed: {self.image}')
            return False
        return True

    def draw_main(self) -> None:
        if not self.image:
            return

        set_blend_alpha()
        shader = self.mask_shader
        shader.bind()

        shader.uniform_float('left', self.left)
        shader.uniform_float('right', self.right)
        shader.uniform_float('color', self.color)
        shader.uniform_int('inverted', 1 if self.inverted else 0)
        shader.uniform_float('maskThreshold', self.mask_threshold)
        shader.uniform_int('channel', self.channel)
        set_shader_sampler(shader, self.image)
        if self.mask_batch:
            self.mask_batch.draw(shader)

    def register_handler(self, post_type: str = 'POST_PIXEL', *, area: Any) -> None:
        _log.yellow(f'{self.__class__.__name__}.register_handler')
        _log.output('call super().register_handler')
        super().register_handler(post_type, area=area)


class KTRasterImage(KTShaderBase):
    def __init__(self, target_class: Any):
        super().__init__(target_class)
        self.square: List[Tuple[float, float]] = [(0., 0.), (1., 0.),
                                                  (1., 1), (0., 1)]
        self.vertices: List[Tuple[float, float]] = self.square
        self.uvs: List[Tuple[float, float]] = self.square
        self.image_shader: Any = None
        self.image_batch: Any = None
        self.left: Tuple[float, float] = (-1., -1.)
        self.right: Tuple[float, float] = (1., 1.)
        self.image: Optional[Image] = None

    def init_shaders(self) -> Optional[bool]:
        if self.image_shader is not None:
            _log.output(f'{self.__class__.__name__}.image_shader: skip')
            return None

        self.image_shader = raster_image_background_shader()
        res = self.image_shader is not None
        _log.output(f'{self.__class__.__name__}.image_shader: {res}')
        return res

    def create_batch(self) -> None:
        if self.image_shader is None:
            _log.error(f'{self.__class__.__name__}.image_shader: is empty')
            return
        self.image_batch = batch_for_shader(
            self.image_shader, 'TRI_FAN',
            {'pos': self.list_for_batch(self.vertices),
             'texCoord': self.list_for_batch(self.uvs)})

    def draw_checks(self) -> bool:
        if self.is_handler_list_empty():
            self.unregister_handler()
            return False

        if self.image_shader is None or self.image_batch is None:
            return False

        if not self.work_area or self.work_area != bpy_context().area:
            return False

        if not self.image:
            return False

        if not check_gl_image(self.image):
            _log.error(f'{self.__class__.__name__}.draw_checks '
                       f'check_gl_image failed: {self.image}')
            return False
        return True

    def draw_main(self) -> None:
        if not self.image:
            return

        shader = self.image_shader
        shader.bind()
        shader.uniform_float('left', self.left)
        shader.uniform_float('right', self.right)
        set_shader_sampler(shader, self.image)
        if self.image_batch:
            self.image_batch.draw(shader)

    def register_handler(self, post_type: str = 'POST_PIXEL', *, area: Any) -> None:
        _log.yellow(f'{self.__class__.__name__}.register_handler')
        _log.output('call super().register_handler')
        super().register_handler(post_type, area=area)
