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

import bpy
from bpy.types import Object, Area, Region
import gpu
import bgl
from gpu_extras.batch import batch_for_shader

from .shaders import (smooth_3d_fragment_shader,
                      uniform_3d_vertex_local_shader)
from .coords import (get_mesh_verts,
                     get_triangulation_indices)
from .bpy_common import evaluated_mesh
from .base_shaders import KTShaderBase


class KTTrisShaderLocal3D(KTShaderBase):
    def __init__(self, target_class: Any):
        self.vertices: List[Tuple[float, float, float]] = []
        self.triangle_indices: List[List[int]] = []
        self.fill_color: Tuple[float, float, float, float] = (0., 0., 1.0, 0.3)
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
        if bpy.app.background:
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

    def draw_callback(self, context: Any) -> None:
        # Force Stop
        if self.is_handler_list_empty():
            self.unregister_handler()
            return

        if self.fill_shader is None or self.fill_batch is None:
            return

        if self.work_area != context.area:
            return

        bgl.glEnable(bgl.GL_BLEND)
        bgl.glEnable(bgl.GL_LINE_SMOOTH)
        bgl.glHint(bgl.GL_LINE_SMOOTH_HINT, bgl.GL_NICEST)
        bgl.glBlendFunc(bgl.GL_SRC_ALPHA, bgl.GL_ONE_MINUS_SRC_ALPHA)

        self.fill_shader.bind()
        self.fill_shader.uniform_float('color', self.fill_color)
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
