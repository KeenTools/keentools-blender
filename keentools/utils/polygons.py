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

import numpy as np
from typing import Any, List, Callable, Tuple, Optional

from bpy.types import Object, Area, Region, Image
import gpu
import bgl
from gpu_extras.batch import batch_for_shader

from ..utils.kt_logging import KTLogger
from ..geotracker_config import GTConfig
from .shaders import (smooth_3d_fragment_shader,
                      uniform_3d_vertex_local_shader,
                      raster_image_mask_vertex_shader,
                      raster_image_mask_fragment_shader)
from .coords import (get_mesh_verts,
                     get_triangulation_indices)
from .bpy_common import evaluated_mesh, bpy_background_mode
from .images import check_gl_image
from .base_shaders import KTShaderBase


_log = KTLogger(__name__)


class KTTrisShaderLocal3D(KTShaderBase):
    def __init__(self, target_class: Any, mask_color=GTConfig.mask_3d_color):
        self.vertices: List[Tuple[float, float, float]] = []
        self.triangle_indices: List[List[int]] = []
        self.color: Tuple[float, float, float, float] = mask_color
        self.fill_shader: Any = None
        self.fill_batch: Any = None
        self.object_world_matrix: Any = np.eye(4, dtype=np.float32)
        super().__init__(target_class)

    def set_object_world_matrix(self, bpy_matrix_world: Any) -> None:
        self.object_world_matrix = np.array(bpy_matrix_world,
                                            dtype=np.float32).transpose()

    def init_shaders(self) -> None:
        self.fill_shader = gpu.types.GPUShader(
            uniform_3d_vertex_local_shader(), smooth_3d_fragment_shader())

    def create_batch(self) -> None:
        if bpy_background_mode():
            return
        verts = []
        indices = []

        verts_count = len(self.vertices)
        if verts_count > 0:
            if len(self.triangle_indices) > 0:
                max_index = np.max(self.triangle_indices)
                if max_index < verts_count:
                    verts = self.vertices
                    indices = self.triangle_indices

        self.fill_batch = batch_for_shader(
            self.fill_shader, 'TRIS', {'pos': verts},
            indices=indices)

    def draw_checks(self, context: Any) -> bool:
        if self.is_handler_list_empty():
            self.unregister_handler()
            return False

        if self.fill_shader is None or self.fill_batch is None:
            return False

        if self.work_area != context.area:
            return False

        return True

    def draw_main_bgl(self, context: Any) -> None:
        bgl.glEnable(bgl.GL_BLEND)
        bgl.glEnable(bgl.GL_LINE_SMOOTH)
        bgl.glHint(bgl.GL_LINE_SMOOTH_HINT, bgl.GL_NICEST)
        bgl.glBlendFunc(bgl.GL_SRC_ALPHA, bgl.GL_ONE_MINUS_SRC_ALPHA)

        self.fill_shader.bind()
        self.fill_shader.uniform_float('color', self.color)
        self.fill_shader.uniform_vector_float(
            self.fill_shader.uniform_from_name('modelMatrix'),
            self.object_world_matrix.ravel(), 16)
        self.fill_batch.draw(self.fill_shader)

    def draw_main_gpu(self, context: Any) -> None:
        gpu.state.blend_set('ALPHA')
        self.fill_shader.bind()
        self.fill_shader.uniform_float('color', self.color)
        self.fill_shader.uniform_vector_float(
            self.fill_shader.uniform_from_name('modelMatrix'),
            self.object_world_matrix.ravel(), 16)
        self.fill_batch.draw(self.fill_shader)

    def init_geom_data_from_mesh(self, obj: Object) -> None:
        mesh = evaluated_mesh(obj)
        verts = get_mesh_verts(mesh)
        mw = np.array(obj.matrix_world, dtype=np.float32).transpose()

        self.object_world_matrix = mw
        self.vertices = verts
        self.triangle_indices = get_triangulation_indices(mesh)


class KTRasterMask(KTShaderBase):
    def __init__(self, target_class: Any, mask_color=GTConfig.mask_2d_color):
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
        super().__init__(target_class)
        if not bpy_background_mode():
            self.init_shaders()
            self.create_batch()

    def init_shaders(self) -> None:
        self.mask_shader = gpu.types.GPUShader(
            raster_image_mask_vertex_shader(),
            raster_image_mask_fragment_shader())

    def create_batch(self) -> None:
        if bpy_background_mode():
            return
        self.mask_batch = batch_for_shader(
            self.mask_shader, 'TRI_FAN', {'pos': self.vertices,
                                          'texCoord': self.uvs})

    def draw_checks(self, context: Any) -> bool:
        if self.is_handler_list_empty():
            self.unregister_handler()
            return False

        if self.mask_shader is None or self.mask_batch is None:
            return False

        if self.work_area != context.area:
            return False

        if not check_gl_image(self.image):
            return False
        return True

    def draw_main_bgl(self, context: Any) -> None:
        bgl.glEnable(bgl.GL_BLEND)
        bgl.glBlendFunc(bgl.GL_SRC_ALPHA, bgl.GL_ONE_MINUS_SRC_ALPHA)

        bgl.glActiveTexture(bgl.GL_TEXTURE0)
        bgl.glBindTexture(bgl.GL_TEXTURE_2D, self.image.bindcode)

        shader = self.mask_shader
        shader.bind()
        shader.uniform_float('left', self.left)
        shader.uniform_float('right', self.right)
        shader.uniform_float('color', self.color)
        shader.uniform_int('inverted', 1 if self.inverted else 0)
        shader.uniform_float('maskThreshold', self.mask_threshold)
        shader.uniform_int('image', 0)
        self.mask_batch.draw(shader)

    def register_handler(self, context: Any,
                         post_type: str='POST_PIXEL') -> None:
        super().register_handler(context, post_type)
