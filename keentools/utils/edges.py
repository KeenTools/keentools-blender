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

import numpy as np
from typing import Any, List, Callable, Tuple, Optional

from bpy.types import Object, Area, Region, SpaceView3D
import gpu
import bgl
from gpu_extras.batch import batch_for_shader

from .kt_logging import KTLogger
from .shaders import (simple_fill_vertex_shader,
                      black_fill_fragment_shader, residual_vertex_shader,
                      residual_fragment_shader,
                      dashed_fragment_shader,
                      solid_line_vertex_shader, solid_line_fragment_shader,
                      simple_fill_vertex_local_shader,
                      smooth_3d_vertex_local_shader, smooth_3d_fragment_shader,
                      uniform_3d_vertex_local_shader,
                      lit_vertex_local_shader,
                      lit_fragment_shader)
from .coords import (get_mesh_verts,
                     multiply_verts_on_matrix_4x4,
                     get_scale_vec_4_from_matrix_world,
                     get_triangulation_indices,
                     get_triangles_in_vertex_group)
from .bpy_common import (evaluated_mesh,
                         bpy_background_mode,
                         use_gpu_instead_of_bgl)
from .base_shaders import KTShaderBase


_log = KTLogger(__name__)


class KTEdgeShaderBase(KTShaderBase):
    def __init__(self, target_class: Any=SpaceView3D):
        super().__init__(target_class)
        self.fill_shader: Optional[Any] = None
        self.line_shader: Optional[Any] = None
        self.fill_batch: Optional[Any] = None
        self.line_batch: Optional[Any] = None
        # Triangle vertices & indices
        self.vertices: List = []
        self.triangle_indices: List = []
        # Edge vertices
        self.edges_vertices: List = []
        self.edges_indices: List = []
        self.edges_colors: List = []
        self.vertices_colors: List = []

        self.backface_culling: bool = False
        self.adaptive_opacity: float = 1.0
        self.line_color: Tuple[float, float, float, float] = (1., 1., 1., 1.)
        self.line_width: float = 1.0

        if not bpy_background_mode():
            self.init_shaders()

    def init_color_data(self, color: Tuple[float, float, float, float]):
        self.edges_colors = [color] * len(self.edges_vertices)

    def set_vertices_colors(self, verts: List, colors: List) -> None:
        self.vertices = verts
        self.vertices_colors = colors

    def clear_vertices(self) -> None:
        self.vertices = []
        self.vertices_colors = []

    def set_backface_culling(self, state: bool) -> None:
        self.backface_culling = state

    def set_adaptive_opacity(self, value: float):
        self.adaptive_opacity = value

    def set_line_width(self, width: float) -> None:
        self.line_width = width


class KTEdgeShader2D(KTEdgeShaderBase):
    def __init__(self, target_class: Any):
        self.edge_lengths: List[float] = []
        super().__init__(target_class)

    def init_shaders(self) -> None:
        self.line_shader = gpu.types.GPUShader(
            residual_vertex_shader(), residual_fragment_shader())

    def draw_checks(self, context: Any) -> bool:
        if self.is_handler_list_empty():
            self.unregister_handler()
            return False

        if not self.is_visible():
            return False

        if self.line_shader is None or self.line_batch is None:
            return False

        if self.work_area != context.area:
            return False

        return True

    def draw_main_bgl(self, context: Any) -> None:
        bgl.glEnable(bgl.GL_BLEND)
        bgl.glEnable(bgl.GL_LINE_SMOOTH)
        bgl.glHint(bgl.GL_LINE_SMOOTH_HINT, bgl.GL_NICEST)
        bgl.glBlendFunc(bgl.GL_SRC_ALPHA, bgl.GL_ONE_MINUS_SRC_ALPHA)
        bgl.glLineWidth(self.line_width)

        self.line_shader.bind()
        self.line_batch.draw(self.line_shader)

    def draw_main_gpu(self, context: Any) -> None:
        gpu.state.line_width_set(self.line_width)
        gpu.state.blend_set('ALPHA')
        self.line_shader.bind()
        self.line_batch.draw(self.line_shader)

    def create_batch(self) -> None:
        if bpy_background_mode():
            return

        self.line_batch = batch_for_shader(
            self.line_shader, 'LINES',
            {'pos': self.vertices, 'color': self.vertices_colors,
             'lineLength': self.edge_lengths}
        )

    def register_handler(self, context: Any,
                         post_type: str='POST_PIXEL') -> None:
        super().register_handler(context, post_type)


class KTScreenRectangleShader2D(KTEdgeShader2D):
    def __init__(self, target_class: Any):
        self.edge_vertices: List[Tuple[float, float, float]] = []
        self.edge_vertices_colors: List[Tuple[float, float, float, float]] = []
        self.fill_color: Tuple[float, float, float, float] = (1., 1., 1., 0.01)
        self.fill_indices: List[Tuple[int, int, int]] = [(0, 1, 3), (4, 5, 0)]
        super().__init__(target_class)

    def init_shaders(self) -> None:
        self.line_shader = gpu.types.GPUShader(
            solid_line_vertex_shader(), solid_line_fragment_shader())
        self.fill_shader = gpu.shader.from_builtin('2D_UNIFORM_COLOR')

    def draw_main_bgl(self, context: Any) -> None:
        bgl.glEnable(bgl.GL_BLEND)
        bgl.glBlendFunc(bgl.GL_SRC_ALPHA, bgl.GL_ONE_MINUS_SRC_ALPHA)
        bgl.glLineWidth(self.line_width)

        self.line_shader.bind()
        self.line_batch.draw(self.line_shader)
        self.fill_shader.bind()
        self.fill_shader.uniform_float('color', self.fill_color)
        self.fill_batch.draw(self.fill_shader)

    def create_batch(self) -> None:
        if bpy_background_mode():
            return
        self.edge_vertices_colors = [self.line_color] * len(self.edge_vertices)

        self.line_batch = batch_for_shader(
            self.line_shader, 'LINES',
            {'pos': self.edge_vertices, 'color': self.edge_vertices_colors}
        )
        self.fill_batch = batch_for_shader(
            self.fill_shader, 'TRIS',
            {'pos': self.edge_vertices},
            indices=self.fill_indices if len(self.edge_vertices) == 8 else []
        )

    def clear_rectangle(self) -> None:
        self.edge_vertices = []
        self.edge_vertices_colors = []
        self.edge_lengths = []

    def add_rectangle(self, x1: int, y1: int, x2: int, y2: int) -> None:
        self.edge_vertices = [(x1, y1), (x1, y2),
                              (x1, y2), (x2, y2),
                              (x2, y2), (x2, y1),
                              (x2, y1), (x1, y1)]


class KTScreenDashedRectangleShader2D(KTScreenRectangleShader2D):
    def init_shaders(self) -> None:
        self.line_shader = gpu.types.GPUShader(
            residual_vertex_shader(), dashed_fragment_shader())
        self.fill_shader = gpu.shader.from_builtin('2D_UNIFORM_COLOR')

    def create_batch(self) -> None:
        if bpy_background_mode():
            return
        self.edge_vertices_colors = [self.line_color] * len(self.edge_vertices)

        self.line_batch = batch_for_shader(
            self.line_shader, 'LINES',
            {'pos': self.edge_vertices, 'color': self.edge_vertices_colors,
             'lineLength': self.edge_lengths})
        self.fill_batch = batch_for_shader(
            self.fill_shader, 'TRIS',
            {'pos': self.edge_vertices},
            indices=self.fill_indices if len(self.edge_vertices) == 8 else [])

    def add_rectangle(self, x1: int, y1: int, x2: int, y2: int) -> None:
        self.edge_vertices = [(x1, y1), (x1, y2),
                              (x1, y2), (x2, y2),
                              (x2, y2), (x2, y1),
                              (x2, y1), (x1, y1)]
        dy = y2 - y1
        dx = x2 - x1
        self.edge_lengths = [0, dy, dy, dx + dy, -dx - dy, -dx, -dx, 0]


class KTEdgeShaderAll2D(KTEdgeShader2D):
    def __init__(self, target_class: Any,
                 line_color: Tuple[float, float, float, float]):
        self.keyframes: List[int] = []
        self.state: Tuple[float, float] = (-1000.0, -1000.0)
        self.batch_needs_update: bool = True
        super().__init__(target_class)
        self.line_color = line_color

    def set_keyframes(self, keyframes: List[int]) -> None:
        self.keyframes = keyframes
        self.batch_needs_update = True

    def _update_keyframe_lines(self, area: Area) -> None:
        bottom = 0
        top = 1000
        reg = self._get_area_region(area)
        pos = [reg.view2d.view_to_region(x, 0, clip=False)[0]
               for x in self.keyframes]
        self.vertices = [(x, y) for x in pos for y in (bottom, top)]
        self.vertices_colors = [self.line_color for _ in self.vertices]
        self.edge_lengths = [x for _ in pos for x in (bottom, top * 0.5)]

    def _get_area_region(self, area: Area) -> Optional[Region]:
        return area.regions[-1]

    def draw_checks(self, context: Any) -> bool:
        if self.is_handler_list_empty():
            self.unregister_handler()
            return False

        if not self.is_visible():
            return False

        if self.line_shader is None or self.line_batch is None:
            return False

        if not context.area:
            return False

        return True

    def draw_main_bgl(self, context: Any) -> None:
        area = context.area
        reg = self._get_area_region(area)
        current_state = (reg.view2d.view_to_region(0, 0, clip=False),
                         reg.view2d.view_to_region(100, 0, clip=False))
        if self.batch_needs_update or current_state != self.state:
            self.state = current_state
            self._update_keyframe_lines(area)
            self.batch_needs_update = False
            self.create_batch()

        bgl.glEnable(bgl.GL_BLEND)
        bgl.glEnable(bgl.GL_LINE_SMOOTH)
        bgl.glHint(bgl.GL_LINE_SMOOTH_HINT, bgl.GL_NICEST)
        bgl.glBlendFunc(bgl.GL_SRC_ALPHA, bgl.GL_ONE_MINUS_SRC_ALPHA)
        bgl.glLineWidth(self.line_width)

        self.line_shader.bind()
        self.line_batch.draw(self.line_shader)

    def draw_main_gpu(self, context: Any) -> None:
        area = context.area
        reg = self._get_area_region(area)
        current_state = (reg.view2d.view_to_region(0, 0, clip=False),
                         reg.view2d.view_to_region(100, 0, clip=False))
        if self.batch_needs_update or current_state != self.state:
            self.state = current_state
            self._update_keyframe_lines(area)
            self.batch_needs_update = False
            self.create_batch()

        gpu.state.line_width_set(self.line_width * 2)
        gpu.state.blend_set('ALPHA')

        self.line_shader.bind()
        self.line_batch.draw(self.line_shader)


class KTEdgeShader3D(KTEdgeShaderBase):
    def draw_empty_fill(self) -> None:
        self.fill_batch.draw(self.fill_shader)

    def draw_edges(self) -> None:
        self.line_batch.draw(self.line_shader)

    def draw_checks(self, context: Any) -> bool:
        if self.is_handler_list_empty():
            self.unregister_handler()
            return False

        if not self.is_visible():
            return False

        if self.line_shader is None or self.line_batch is None \
                or self.fill_shader is None or self.fill_batch is None:
            return False

        if self.work_area != context.area:
            return False

        return True

    def draw_main_bgl(self, context: Any) -> None:
        bgl.glEnable(bgl.GL_BLEND)
        bgl.glEnable(bgl.GL_LINE_SMOOTH)
        bgl.glHint(bgl.GL_LINE_SMOOTH_HINT, bgl.GL_NICEST)
        bgl.glBlendFunc(bgl.GL_SRC_ALPHA, bgl.GL_ONE_MINUS_SRC_ALPHA)
        bgl.glLineWidth(self.line_width)

        bgl.glEnable(bgl.GL_DEPTH_TEST)
        bgl.glEnable(bgl.GL_POLYGON_OFFSET_FILL)
        bgl.glColorMask(bgl.GL_FALSE, bgl.GL_FALSE, bgl.GL_FALSE, bgl.GL_FALSE)

        if self.backface_culling:
            bgl.glPolygonMode(bgl.GL_BACK, bgl.GL_FILL)
            bgl.glEnable(bgl.GL_CULL_FACE)
            bgl.glCullFace(bgl.GL_FRONT)
            bgl.glPolygonOffset(-1.0, -1.0)
            self.draw_empty_fill()

        bgl.glPolygonMode(bgl.GL_FRONT_AND_BACK, bgl.GL_FILL)
        bgl.glDisable(bgl.GL_CULL_FACE)
        bgl.glPolygonOffset(1.0, 1.0)
        self.draw_empty_fill()

        bgl.glColorMask(bgl.GL_TRUE, bgl.GL_TRUE, bgl.GL_TRUE, bgl.GL_TRUE)
        bgl.glDisable(bgl.GL_POLYGON_OFFSET_FILL)

        bgl.glDepthMask(bgl.GL_FALSE)
        bgl.glPolygonMode(bgl.GL_FRONT_AND_BACK, bgl.GL_LINE)

        self.draw_edges()

        bgl.glPolygonMode(bgl.GL_FRONT_AND_BACK, bgl.GL_FILL)
        self.draw_selection_fill()

        bgl.glDepthMask(bgl.GL_TRUE)
        bgl.glDisable(bgl.GL_DEPTH_TEST)

    def draw_main_gpu(self, context: Any) -> None:
        gpu.state.depth_test_set('LESS_EQUAL')
        gpu.state.color_mask_set(False, False, False, False)
        self.draw_empty_fill()
        gpu.state.color_mask_set(True, True, True, True)

        gpu.state.line_width_set(self.line_width * 2)
        gpu.state.blend_set('ALPHA')
        self.draw_edges()

    def draw_selection_fill(self):
        pass

    def create_batches(self) -> None:
        if bpy_background_mode():
            return
        self.fill_batch = batch_for_shader(
                    self.fill_shader, 'TRIS',
                    {'pos': self.vertices},
                    indices=self.triangle_indices,
                )
        self.line_batch = batch_for_shader(
            self.line_shader, 'LINES',
            {'pos': self.edges_vertices, 'color': self.edges_colors})

    def init_shaders(self) -> None:
        self.fill_shader = gpu.types.GPUShader(
            simple_fill_vertex_shader(), black_fill_fragment_shader())

        self.line_shader = gpu.shader.from_builtin('3D_SMOOTH_COLOR')

    def init_geom_data_from_mesh(self, obj: Any) -> None:
        # self.triangle_indices are for hidden mesh drawing
        # self.edges_vertices are for wireframe drawing
        mesh = obj.data
        verts = get_mesh_verts(mesh)

        mw = np.array(obj.matrix_world, dtype=np.float32).transpose()

        self.vertices = multiply_verts_on_matrix_4x4(verts, mw)
        self.triangle_indices = get_triangulation_indices(mesh)

        edges = np.empty((len(mesh.edges), 2), dtype=np.int32)
        mesh.edges.foreach_get(
            'vertices', np.reshape(edges, len(mesh.edges) * 2))

        self.edges_vertices = self.vertices[edges.ravel()]

    def init_vertex_normals(self, obj: Object) -> None:
        pass


class KTEdgeShaderLocal3D(KTEdgeShader3D):
    def __init__(self, target_class: Any, mask_color: Tuple):
        self.object_world_matrix: Any = np.eye(4, dtype=np.float32)
        self.selection_fill_color: Tuple[float, float, float, float] = mask_color
        self.selection_fill_shader: Optional[Any] = None
        self.selection_fill_batch: Optional[Any] = None
        self.selection_triangle_indices: List[Tuple[int, int, int]] = []
        super().__init__(target_class)

    def init_shaders(self) -> None:
        self.fill_shader = gpu.types.GPUShader(
            simple_fill_vertex_local_shader(), black_fill_fragment_shader())

        self.line_shader = gpu.types.GPUShader(
            smooth_3d_vertex_local_shader(), smooth_3d_fragment_shader())

        self.selection_fill_shader = gpu.types.GPUShader(
            uniform_3d_vertex_local_shader(), smooth_3d_fragment_shader())

    def create_batches(self) -> None:
        if bpy_background_mode():
            return
        self.fill_batch = batch_for_shader(
                    self.fill_shader, 'TRIS',
                    {'pos': self.vertices},
                    indices=self.triangle_indices)
        self.line_batch = batch_for_shader(
            self.line_shader, 'LINES',
            {'pos': self.edges_vertices, 'color': self.edges_colors})

        verts = []
        indices = []
        verts_count = len(self.vertices)
        if verts_count > 0 and len(self.selection_triangle_indices) > 0:
            max_index = np.max(self.selection_triangle_indices)
            if max_index < verts_count:
                verts = self.vertices
                indices = self.selection_triangle_indices
        self.selection_fill_batch = batch_for_shader(
            self.selection_fill_shader, 'TRIS', {'pos': verts},
            indices=indices)

    def set_object_world_matrix(self, bpy_matrix_world: Any) -> None:
        self.object_world_matrix = np.array(bpy_matrix_world,
                                            dtype=np.float32).transpose()

    def init_geom_data_from_mesh(self, obj: Any) -> None:
        mw = obj.matrix_world
        scale_vec = get_scale_vec_4_from_matrix_world(mw)
        scale_vec = np.array([1.0, 1.0, 1.0, 1.0], dtype=np.float32)
        scm = np.diag(scale_vec)
        scminv = np.diag(1.0 / scale_vec)

        self.object_world_matrix = scminv @ np.array(mw, dtype=np.float32).transpose()

        mesh = evaluated_mesh(obj)
        verts = get_mesh_verts(mesh)

        self.vertices = multiply_verts_on_matrix_4x4(verts, scm)
        self.triangle_indices = get_triangulation_indices(mesh)

        edges = np.empty((len(mesh.edges), 2), dtype=np.int32)
        mesh.edges.foreach_get(
            'vertices', np.reshape(edges, len(mesh.edges) * 2))

        self.edges_vertices = self.vertices[edges.ravel()]

    def draw_edges(self) -> None:
        shader = self.line_shader
        shader.bind()
        shader.uniform_vector_float(shader.uniform_from_name('modelMatrix'),
                                    self.object_world_matrix.ravel(), 16)
        self.line_batch.draw(shader)

    def draw_empty_fill(self) -> None:
        shader = self.fill_shader
        shader.bind()
        shader.uniform_vector_float(
            shader.uniform_from_name('modelMatrix'),
            self.object_world_matrix.ravel(), 16)
        self.fill_batch.draw(shader)

    def draw_selection_fill(self) -> None:
        shader = self.selection_fill_shader
        shader.bind()
        shader.uniform_float('adaptiveOpacity', self.adaptive_opacity)
        shader.uniform_float('color', self.selection_fill_color)
        shader.uniform_vector_float(
            shader.uniform_from_name('modelMatrix'),
            self.object_world_matrix.ravel(), 16)
        self.selection_fill_batch.draw(shader)

    def init_selection_from_mesh(self, obj: Object, mask_3d: str,
                                 inverted: bool) -> None:
        self.selection_triangle_indices = get_triangles_in_vertex_group(
            obj, mask_3d, inverted)


class KTLitEdgeShaderLocal3D(KTEdgeShaderLocal3D):
    def __init__(self, target_class: Any, mask_color: Tuple):
        self.lit_color: Tuple[float, float, float, float] = (0., 1., 0., 1.0)
        self.lit_shader: Optional[Any] = None
        self.lit_batch: Optional[Any] = None
        self.lit_flag: bool = False
        self.lit_edge_vertices: List = []
        self.lit_edge_vertex_normals: List = []
        super().__init__(target_class, mask_color)

    def set_lit_wireframe(self, state: bool) -> None:
        self.lit_flag = state

    def lit_is_working(self) -> bool:
        return self.lit_flag

    def init_shaders(self) -> None:
        super().init_shaders()
        self.lit_shader = gpu.types.GPUShader(
            lit_vertex_local_shader(), lit_fragment_shader())

    def init_vertex_normals(self, obj: Object) -> None:
        mesh = evaluated_mesh(obj)

        loop_count = len(mesh.loops)
        loops = np.empty((loop_count,), dtype=np.int32)
        mesh.loops.foreach_get('vertex_index', np.reshape(loops, loop_count))

        loop_normals = np.empty((loop_count, 3), dtype=np.float32)
        mesh.calc_normals_split()
        mesh.loops.foreach_get('normal', np.reshape(loop_normals,
                                                    loop_count * 3))
        poly_count = len(mesh.polygons)
        polys = np.empty((poly_count,), dtype=np.int32)
        mesh.polygons.foreach_get('loop_total', np.reshape(polys, poly_count))

        edge_indices = np.empty((loop_count * 2,), dtype=np.int32)
        edge_normals = np.empty((loop_count * 2, 3), dtype=np.float32)
        i = 0
        k = 0
        for p_count in polys:
            indices = loops[i: i + p_count]
            normals = loop_normals[i: i + p_count]
            delta = p_count * 2
            edge_indices[k: k + delta] = \
                np.roll(np.repeat(indices, 2), -1, axis=0)
            edge_normals[k: k + delta] = \
                np.roll(np.repeat(normals, 2, axis=0), -1, axis=0)
            i += p_count
            k += delta

        self.lit_edge_vertices = self.vertices[edge_indices.ravel()]
        self.lit_edge_vertex_normals = edge_normals

    def init_color_data(self, color: Tuple[float, float, float, float]) -> None:
        self.edges_colors = [color] * len(self.edges_vertices)
        self.lit_color = color
        self.line_color = color

    def create_batches(self) -> None:
        if bpy_background_mode():
            return
        super().create_batches()
        self.lit_batch = batch_for_shader(
            self.lit_shader, 'LINES',
            {'pos': self.lit_edge_vertices,
             'vertNormal': self.lit_edge_vertex_normals})

    def draw_edges(self) -> None:
        if not self.lit_is_working():
            return super().draw_edges()

        shader = self.lit_shader
        shader.bind()
        shader.uniform_float('color', self.lit_color)
        shader.uniform_vector_float(
            shader.uniform_from_name('modelMatrix'),
            self.object_world_matrix.ravel(), 16)
        self.lit_batch.draw(shader)
