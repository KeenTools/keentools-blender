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
from mathutils import Vector, Matrix

from .kt_logging import KTLogger
from .gpu_shaders import (line_3d_local_shader,
                          solid_line_2d_shader,
                          residual_2d_shader,
                          dashed_2d_shader,
                          black_fill_local_shader,
                          lit_local_shader)
from .coords import (get_mesh_verts,
                     multiply_verts_on_matrix_4x4,
                     get_scale_vec_4_from_matrix_world,
                     get_triangulation_indices,
                     get_triangles_in_vertex_group,
                     LocRotWithoutScale, InvScaleMatrix)
from .bpy_common import (evaluated_mesh,
                         use_gpu_instead_of_bgl)
from .base_shaders import KTShaderBase


_log = KTLogger(__name__)


class KTEdgeShaderBase(KTShaderBase):
    def __init__(self, target_class: Any=SpaceView3D):
        super().__init__(target_class)
        self.fill_shader: Optional[Any] = None
        self.fill_batch: Optional[Any] = None
        self.line_shader: Optional[Any] = None
        self.line_batch: Optional[Any] = None
        # Triangle vertices & indices
        self.vertices: List = []
        self.triangle_indices: List = []
        # Edge vertices
        self.edge_vertices: List = []
        self.edge_colors: List = []
        self.vertices_colors: List = []

        # pykeentools data
        self.triangle_vertices: List = []
        self.edge_vertex_normals: List = []

        self.backface_culling: bool = False
        self.backface_culling_in_shader: bool = False
        self.adaptive_opacity: float = 1.0
        self.line_color: Tuple[float, float, float, float] = (1., 1., 1., 1.)
        self.line_width: float = 1.0

    def init_color_data(self, color: Tuple[float, float, float, float]):
        self.edge_colors = [color] * len(self.edge_vertices)

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

    def clear_all(self) -> None:
        self.vertices = []
        self.triangle_indices = []
        self.edge_vertices = []
        self.edge_colors = []
        self.vertices_colors = []


class KTEdgeShader2D(KTEdgeShaderBase):
    def __init__(self, target_class: Any):
        self.edge_lengths: List[float] = []
        super().__init__(target_class)

    def init_shaders(self) -> Optional[bool]:
        if self.line_shader is not None:
            _log.output(f'{self.__class__.__name__}.line_shader: skip')
            return None

        self.line_shader = residual_2d_shader()
        res = self.line_shader is not None
        _log.output(f'{self.__class__.__name__}.line_shader: {res}')
        return res

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
        if self.line_shader is None:
            _log.error(f'{self.__class__.__name__}.line_shader: is empty')
            return

        self.line_batch = batch_for_shader(
            self.line_shader, 'LINES',
            {'pos': self.vertices, 'color': self.vertices_colors,
             'lineLength': self.edge_lengths}
        )
        self.increment_batch_counter()

    def register_handler(self, context: Any,
                         post_type: str='POST_PIXEL') -> None:
        _log.output(f'{self.__class__.__name__}.register_handler')
        super().register_handler(context, post_type)


class KTScreenRectangleShader2D(KTEdgeShader2D):
    def __init__(self, target_class: Any):
        self.edge_vertices: List[Tuple[float, float, float]] = []
        self.edge_vertices_colors: List[Tuple[float, float, float, float]] = []
        self.fill_color: Tuple[float, float, float, float] = (1., 1., 1., 0.01)
        self.fill_indices: List[Tuple[int, int, int]] = [(0, 1, 3), (4, 5, 0)]
        super().__init__(target_class)

    def init_shaders(self) -> Optional[bool]:
        changes = False
        res = [True] * 2

        if self.line_shader is None:
            self.line_shader = solid_line_2d_shader()
            res[0] = self.line_shader is not None
            _log.output(f'line_shader: {res[0]}')
            changes = True
        else:
            _log.output(f'{self.__class__.__name__}.line_shader: skip')

        if self.fill_shader is None:
            self.fill_shader = gpu.shader.from_builtin('2D_UNIFORM_COLOR')
            res[1] = self.fill_shader is not None
            _log.output(f'fill_shader: {res[1]}')
            changes = True
        else:
            _log.output(f'{self.__class__.__name__}.fill_shader: skip')

        if changes:
            return res[0] and res[1]
        return None

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
        self.edge_vertices_colors = [self.line_color] * len(self.edge_vertices)

        if self.line_shader is not None:
            self.line_batch = batch_for_shader(
                self.line_shader, 'LINES',
                {'pos': self.edge_vertices, 'color': self.edge_vertices_colors}
            )
        else:
            _log.error(f'{self.__class__.__name__}.line_shader: is empty')

        if self.fill_shader is not None:
            self.fill_batch = batch_for_shader(
                self.fill_shader, 'TRIS',
                {'pos': self.edge_vertices},
                indices=self.fill_indices if len(self.edge_vertices) == 8 else []
            )
        else:
            _log.error(f'{self.__class__.__name__}.fill_shader: is empty')

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
    def init_shaders(self) -> Optional[bool]:
        changes = False
        res = [True] * 2

        if self.line_shader is None:
            self.line_shader = dashed_2d_shader()
            res[0] = self.line_shader is not None
            _log.output(f'line_shader: {res[0]}')
            changes = True
        else:
            _log.output(f'{self.__class__.__name__}.line_shader: skip')

        if self.fill_shader is None:
            self.fill_shader = gpu.shader.from_builtin('2D_UNIFORM_COLOR')
            res[1] = self.fill_shader is not None
            _log.output(f'fill_shader: {res[1]}')
            changes = True
        else:
            _log.output(f'{self.__class__.__name__}.fill_shader: skip')

        if changes:
            return res[0] and res[1]
        return None

    def create_batch(self) -> None:
        self.edge_vertices_colors = [self.line_color] * len(self.edge_vertices)

        if self.line_shader is not None:
            self.line_batch = batch_for_shader(
                self.line_shader, 'LINES',
                {'pos': self.edge_vertices, 'color': self.edge_vertices_colors,
                 'lineLength': self.edge_lengths})
        else:
            _log.error(f'{self.__class__.__name__}.line_shader: is empty')

        if self.fill_shader is not None:
            self.fill_batch = batch_for_shader(
                self.fill_shader, 'TRIS',
                {'pos': self.edge_vertices},
                indices=self.fill_indices if len(self.edge_vertices) == 8 else [])
        else:
            _log.error(f'{self.__class__.__name__}.fill_shader: is empty')

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

        if self.backface_culling and not self.backface_culling_in_shader:
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
        if self.fill_shader is not None:
            self.fill_batch = batch_for_shader(self.fill_shader, 'TRIS',
                                               {'pos': self.vertices},
                                               indices=self.triangle_indices)
        else:
            _log.error(f'{self.__class__.__name__}.fill_shader: is empty')

        if self.line_shader is not None:
            self.line_batch = batch_for_shader(
                self.line_shader, 'LINES',
                {'pos': self.edge_vertices, 'color': self.edge_colors})
        else:
            _log.error(f'{self.__class__.__name__}.line_shader: is empty')

    def init_shaders(self) -> Optional[bool]:
        changes = False
        res = [True] * 2

        if self.fill_shader is None:
            self.fill_shader = black_fill_local_shader()
            res[0] = self.fill_shader is not None
            _log.output(f'fill_shader: {res[0]}')
            changes = True
        else:
            _log.output(f'{self.__class__.__name__}.fill_shader: skip')

        if self.line_shader is None:
            self.line_shader = gpu.shader.from_builtin('3D_SMOOTH_COLOR')
            res[1] = self.line_shader is not None
            _log.output(f'line_shader: {res[1]}')
            changes = True
        else:
            _log.output(f'{self.__class__.__name__}.line_shader: skip')

        if changes:
            return res[0] and res[1]
        return None

    def init_geom_data_from_mesh(self, obj: Any) -> None:
        mesh = obj.data
        verts = get_mesh_verts(mesh)

        mw = np.array(obj.matrix_world, dtype=np.float32).transpose()

        self.vertices = multiply_verts_on_matrix_4x4(verts, mw)
        self.triangle_indices = get_triangulation_indices(mesh)

        edges = np.empty((len(mesh.edges), 2), dtype=np.int32)
        mesh.edges.foreach_get(
            'vertices', np.reshape(edges, len(mesh.edges) * 2))

        self.edge_vertices = self.vertices[edges.ravel()]

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

    def init_shaders(self) -> Optional[bool]:
        changes = False
        res = [True] * 3

        if self.fill_shader is None:
            self.fill_shader = black_fill_local_shader()
            res[0] = self.fill_shader is not None
            _log.output(f'fill_shader: {res[0]}')
            changes = True
        else:
            _log.output(f'{self.__class__.__name__}.fill_shader: skip')

        if self.line_shader is None:
            self.line_shader = line_3d_local_shader()
            res[1] = self.line_shader is not None
            _log.output(f'line_shader: {res[1]}')
            changes = True
        else:
            _log.output(f'{self.__class__.__name__}.line_shader: skip')

        if self.selection_fill_shader is None:
            self.selection_fill_shader = line_3d_local_shader()
            res[2] = self.selection_fill_shader is not None
            _log.output(f'selection_fill_shader: {res[2]}')
            changes = True
        else:
            _log.output(f'{self.__class__.__name__}.selection_fill_shader: skip')

        if changes:
            return res[0] and res[1] and res[2]
        return None

    def create_batches(self) -> None:
        if self.fill_shader is not None:
            self.fill_batch = batch_for_shader(
                        self.fill_shader, 'TRIS',
                        {'pos': self.vertices},
                        indices=self.triangle_indices)
        else:
            _log.error(f'{self.__class__.__name__}.fill_shader: is empty')

        if self.line_shader is not None:
            self.line_batch = batch_for_shader(
                self.line_shader, 'LINES',
                {'pos': self.edge_vertices})
        else:
            _log.error(f'{self.__class__.__name__}.line_shader: is empty')

        verts = []
        indices = []
        verts_count = len(self.vertices)
        if verts_count > 0 and len(self.selection_triangle_indices) > 0:
            max_index = np.max(self.selection_triangle_indices)
            if max_index < verts_count:
                verts = self.vertices
                indices = self.selection_triangle_indices

        if self.selection_fill_shader is not None:
            self.selection_fill_batch = batch_for_shader(
                self.selection_fill_shader, 'TRIS', {'pos': verts},
                indices=indices)
        else:
            _log.error(f'{self.__class__.__name__}.selection_fill_shader: is empty')

    def set_object_world_matrix(self, bpy_matrix_world: Any) -> None:
        self.object_world_matrix = np.array(bpy_matrix_world,
                                            dtype=np.float32).transpose()

    def init_geom_data_from_mesh(self, obj: Any) -> None:
        self.set_object_world_matrix(obj.matrix_world)
        mesh = evaluated_mesh(obj)
        self.vertices = get_mesh_verts(mesh)
        self.triangle_indices = get_triangulation_indices(mesh)

        edges = np.empty((len(mesh.edges), 2), dtype=np.int32)
        mesh.edges.foreach_get(
            'vertices', np.reshape(edges, len(mesh.edges) * 2))

        self.edge_vertices = self.vertices[edges.ravel()]

    def draw_edges(self) -> None:
        shader = self.line_shader
        shader.bind()
        shader.uniform_float('adaptiveOpacity', self.adaptive_opacity)
        shader.uniform_float('color', self.line_color)
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
        shader.uniform_float('adaptiveOpacity', 1.0)
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
        self.lit_light_dist: float = 1000
        self.lit_light1_pos: Vector = Vector((0, 0, 0)) * self.lit_light_dist
        self.lit_light2_pos: Vector = Vector((-2, 0, 1)) * self.lit_light_dist
        self.lit_light3_pos: Vector = Vector((2, 0, 1)) * self.lit_light_dist
        self.lit_camera_pos: Vector = Vector((0, 0, 0)) * self.lit_light_dist
        self.lit_light_matrix: Matrix = Matrix.Identity(4)
        self.fill_batch2: Optional[Any] = None
        super().__init__(target_class, mask_color)
        self.backface_culling_in_shader = True

    def set_lit_wireframe(self, state: bool) -> None:
        self.lit_flag = state

    def lit_is_working(self) -> bool:
        return self.lit_flag

    def set_lit_light_matrix(self, geomobj_matrix_world: Matrix,
                             camobj_matrix_world: Matrix) -> None:
        _log.output('set_lit_light_matrix')
        mat = geomobj_matrix_world.inverted() @ camobj_matrix_world
        self.lit_light_matrix = mat

    def init_shaders(self) -> Optional[bool]:
        res = [True] * 2

        res[0] = super().init_shaders()

        if self.lit_shader is not None:
            _log.output(f'{self.__class__.__name__}.lit_shader: skip')
            return res[0]

        self.lit_shader = lit_local_shader()
        res[1] = self.lit_shader is not None
        _log.output(f'{self.__class__.__name__}.lit_shader: {res[1]}')

        if res[0] is None:
            return res[1]
        return res[0] and res[1]

    def init_vertex_normals(self, obj: Object) -> None:
        _log.output(_log.color('green', 'init_vertex_normals start'))
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
        _log.output(_log.color('green', 'init_vertex_normals end'))

    def init_color_data(self, color: Tuple[float, float, float, float]) -> None:
        self.lit_color = color
        self.line_color = color

    def create_batches(self) -> None:
        super().create_batches()
        if not self.lit_shader is None:
            self.lit_batch = batch_for_shader(
                self.lit_shader, 'LINES',
                {'pos': self.lit_edge_vertices,
                 'vertNormal': self.lit_edge_vertex_normals})
        else:
            _log.error(f'{self.__class__.__name__}.lit_shader: is empty')

        if self.fill_shader is not None:
            if self.lit_is_working():
                _log.output(_log.color('red', 'Extra self.fill_shader'))
                self.fill_batch = batch_for_shader(
                    self.fill_shader, 'TRIS',
                    {'pos': self.triangle_vertices})
        else:
            _log.error(f'{self.__class__.__name__}.fill_shader2: is empty')

    def draw_edges(self) -> None:
        shader = self.lit_shader
        shader.bind()
        shader.uniform_float('color', self.lit_color)
        shader.uniform_float('adaptiveOpacity', self.adaptive_opacity)
        # uniform_int is used instead of uniform_bool for backward compatibility
        shader.uniform_int('ignoreBackface', 1 if self.backface_culling else 0)
        shader.uniform_int('litShading', 1 if self.lit_is_working() else 0)
        shader.uniform_vector_float(
            shader.uniform_from_name('modelMatrix'),
            self.object_world_matrix.ravel(), 16)
        shader.uniform_float('pos1', self.lit_light_matrix @
                             self.lit_light1_pos)
        shader.uniform_float('pos2', self.lit_light_matrix @
                             self.lit_light2_pos)
        shader.uniform_float('pos3', self.lit_light_matrix @
                             self.lit_light3_pos)
        shader.uniform_float('cameraPos', self.lit_light_matrix @
                             self.lit_camera_pos)
        self.lit_batch.draw(shader)

    def clear_all(self) -> None:
        super().clear_all()
        self.lit_edge_vertices = []
        self.lit_edge_vertex_normals = []
