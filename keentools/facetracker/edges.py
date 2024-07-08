# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2019-2024  KeenTools

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

from typing import Any, Tuple, List, Optional
import numpy as np

from bpy.types import SpaceView3D, Object
from mathutils import Matrix, Vector
from gpu_extras.batch import batch_for_shader

from ..utils.kt_logging import KTLogger
from ..addon_config import ft_settings
from ..facetracker_config import FTConfig
from ..facebuilder.utils.edges import FBRasterEdgeShader3D
from ..utils.fb_wireframe_image import get_ft_edge_indices_and_uvs
from ..utils.coords import get_triangles_in_vertex_group, get_mesh_verts
from ..utils.bpy_common import evaluated_mesh
from ..utils.gpu_control import (set_depth_test,
                                 set_depth_mask,
                                 set_color_mask,
                                 revert_blender_viewport_state)
from ..utils.gpu_shaders import line_3d_local_shader


_log = KTLogger(__name__)


class FTRasterEdgeShader3D(FBRasterEdgeShader3D):
    def __init__(self, target_class: Any=SpaceView3D):
        super().__init__(target_class)
        self.selection_fill_color: Tuple[float, float, float, float] = (1, 0, 0, 0.5)
        self.selection_fill_shader: Optional[Any] = None
        self.selection_fill_batch: Optional[Any] = None
        self.selection_triangle_indices: Any = np.empty((0,), dtype=np.int32)

        self.lit_color: Tuple[float, float, float, float] = (0., 1., 0., 1.0)
        self.lit_shader: Optional[Any] = None
        self.lit_batch: Optional[Any] = None
        self.lit_shading: bool = True
        self.viewport_size: Tuple[float, float] = (1920, 1080)
        self.lit_light_dist: float = 1000
        self.lit_light1_pos: Vector = Vector((0, 0, 0)) * self.lit_light_dist
        self.lit_light2_pos: Vector = Vector((-2, 0, 1)) * self.lit_light_dist
        self.lit_light3_pos: Vector = Vector((2, 0, 1)) * self.lit_light_dist
        self.lit_camera_pos: Vector = Vector((0, 0, 0)) * self.lit_light_dist
        self.wireframe_offset = FTConfig.ft_wireframe_offset_constant

    def init_edge_indices(self) -> None:
        _log.blue('init_edge_indices')
        geo = ft_settings().loader().get_geo()
        self.edge_indices, self.edge_uvs = get_ft_edge_indices_and_uvs(geo_mesh=geo.mesh(0))

    def init_selection_from_mesh(self, obj: Object, mask_3d: str,
                                 inverted: bool) -> None:
        self.selection_triangle_indices = get_triangles_in_vertex_group(
            obj, mask_3d, inverted)
        if len(self.selection_triangle_indices) > 0:
            mesh = evaluated_mesh(obj)
            self.vertices = get_mesh_verts(mesh)

    def set_lit_wireframe(self, state: bool) -> None:
        self.lit_shading = state

    def init_shaders(self) -> Optional[bool]:
        changes = False
        res = [True] * 2
        super_res = super().init_shaders()

        if super_res is not None:
            res[0] = super_res
            changes = True

        if self.selection_fill_shader is None:
            self.selection_fill_shader = line_3d_local_shader()
            res[1] = self.selection_fill_shader is not None
            _log.output(f'selection_fill_shader: {res[1]}')
            changes = True
        else:
            _log.output(f'{self.__class__.__name__}.selection_fill_shader: skip')

        if changes:
            return res[0] and res[1]
        return None

    def create_batches(self) -> None:
        _log.red(f'{self.__class__.__name__}.create_batches start')
        super().create_batches()

        if self.selection_fill_shader is not None:
            verts = np.empty((0, 3), dtype=np.float32)
            indices = np.empty((0,), dtype=np.int32)
            verts_count = len(self.vertices)
            if verts_count > 0 and len(self.selection_triangle_indices) > 0:
                max_index = np.max(self.selection_triangle_indices)
                if max_index < verts_count:
                    verts = self.vertices
                    indices = self.selection_triangle_indices

            self.selection_fill_batch = batch_for_shader(
                self.selection_fill_shader, 'TRIS',
                {'pos': self.list_for_batch(verts)},
                indices=self.list_for_batch(indices))
        else:
            _log.error(f'{self.__class__.__name__}.selection_fill_shader: is empty')

        _log.output(f'{self.__class__.__name__}.create_batches end >>>')

    def draw_main(self) -> None:
        set_depth_test('LESS_EQUAL')
        set_color_mask(False, False, False, False)
        self.draw_empty_fill()
        set_color_mask(True, True, True, True)

        region = self.work_area.regions[-1]
        assert region.type == 'WINDOW'

        self.set_viewport_size(region)

        set_depth_mask(False)
        if not self.use_simple_shader:
            self._draw_textured_line()
        else:
            self._draw_simple_line()

        self.draw_selection_fill()
        revert_blender_viewport_state()

    def draw_selection_fill(self) -> None:
        shader = self.selection_fill_shader
        shader.bind()
        shader.uniform_float('adaptiveOpacity', 1.0)
        shader.uniform_float('color', self.selection_fill_color)
        shader.uniform_vector_float(
            shader.uniform_from_name('modelMatrix'),
            self.object_world_matrix.ravel(), 16)
        if self.selection_fill_batch:
            self.selection_fill_batch.draw(shader)
