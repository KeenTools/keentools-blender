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

from ..utils.kt_logging import KTLogger
from ..addon_config import Config
from ..facebuilder.utils.edges import FBRasterEdgeShader3D
from ..facebuilder.fbloader import FBLoader


_log = KTLogger(__name__)


class FTRasterEdgeShader3D(FBRasterEdgeShader3D):
    def __init__(self, target_class: Any=SpaceView3D):
        super().__init__(target_class)
        self.selection_fill_color: Tuple[float, float, float, float] = (1, 0, 0, 0.5)
        self.selection_fill_shader: Optional[Any] = None
        self.selection_fill_batch: Optional[Any] = None
        self.selection_triangle_indices: List[Tuple[int, int, int]] = []

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
        self.lit_light_matrix: Matrix = Matrix.Identity(4)
        self.wireframe_offset = Config.wireframe_offset_constant

    def set_lit_light_matrix(self, geomobj_matrix_world: Matrix,
                             camobj_matrix_world: Matrix) -> None:
        _log.output('set_lit_light_matrix')
        mat = geomobj_matrix_world.inverted() @ camobj_matrix_world
        self.lit_light_matrix = mat

    def init_edge_indices(self, builder: Any) -> None:
        _log.output(_log.color('blue', 'init_edge_indices call'))
        fb = FBLoader.get_builder()
        if not fb.face_texture_available():
            self._clear_edge_uvs()
            return

        geo = fb.applied_args_replaced_uvs_model()
        me = geo.mesh(0)
        face_counts = [me.face_size(x) for x in range(me.faces_count())]
        indices = np.empty((sum(face_counts), 2), dtype=np.int32)
        tex_coords = np.empty((sum(face_counts) * 2, 2), dtype=np.float32)

        i = 0
        for face, count in enumerate(face_counts):
            for k in range(0, count - 1):
                tex_coords[i * 2] = me.uv(face, k)
                tex_coords[i * 2 + 1] = me.uv(face, k + 1)
                indices[i] = (me.face_point(face, k),
                              me.face_point(face, k + 1))
                i += 1

            tex_coords[i * 2] = me.uv(face, count - 1)
            tex_coords[i * 2 + 1] = me.uv(face, 0)
            indices[i] = (me.face_point(face, count - 1),
                          me.face_point(face, 0))
            i += 1

        self.edge_indices = indices
        self.edge_uvs = tex_coords
        _log.output(f'init_edge_indices'
                    f'\nedge_indices: {self.edge_indices.shape}'
                    f'\nedge_uvs: {self.edge_uvs.shape}')

    def init_selection_from_mesh(self, obj: Object, mask_3d: str,
                                 inverted: bool) -> None:
        pass

    def set_lit_wireframe(self, state: bool) -> None:
        self.lit_shading = state
