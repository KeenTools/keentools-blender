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
from gpu_extras.batch import batch_for_shader
from mathutils import Vector, Matrix

from .kt_logging import KTLogger
from ..addon_config import Config
from .gpu_shaders import (line_3d_local_shader,
                          solid_line_2d_shader,
                          dashed_2d_shader,
                          black_offset_fill_local_shader,
                          lit_aa_local_shader,
                          simple_uniform_color_2d_shader)
from .coords import (get_mesh_verts,
                     get_triangulation_indices,
                     get_triangles_in_vertex_group,
                     make_indices_for_wide_edges,
                     frame_to_image_space,
                     get_camera_border,
                     image_space_to_region)
from .bpy_common import evaluated_mesh, bpy_context
from .base_shaders import KTShaderBase
from .gpu_control import (set_blend_alpha,
                          set_smooth_line,
                          set_line_width,
                          set_depth_test,
                          set_depth_mask,
                          set_color_mask,
                          revert_blender_viewport_state)


_log = KTLogger(__name__)


class KTEdgeShaderBase(KTShaderBase):
    def __init__(self, target_class: Any=SpaceView3D):
        super().__init__(target_class)
        self.object_world_matrix: Any = np.eye(4, dtype=np.float32)

        self.fill_shader: Optional[Any] = None
        self.fill_batch: Optional[Any] = None
        self.line_shader: Optional[Any] = None
        self.line_batch: Optional[Any] = None
        # Triangle vertices & indices
        self.vertices: Any = np.empty((0, 3), dtype=np.float32)
        self.triangle_indices: Any = np.empty((0,), dtype=np.int32)
        # Edge vertices
        self.edge_vertices: Any = np.empty((0, 3), dtype=np.float32)
        self.edge_colors: Any = np.empty((0, 4), dtype=np.float32)
        self.vertex_colors: Any = np.empty((0, 4), dtype=np.float32)

        # pykeentools data
        self.triangle_vertices: Any = np.empty((0, 3), dtype=np.float32)
        self.edge_vertex_normals: Any = np.empty((0, 3), dtype=np.float32)

        self.backface_culling: bool = True
        self.adaptive_opacity: float = 1.0
        self.line_color: Tuple[float, float, float, float] = (1., 1., 1., 1.)
        self.line_width: float = 1.0
        self.line_ui_scale: float = 1.0

        self.wireframe_offset: float = 0.0
        self.wide_edge_vertices: Any = np.empty((0, 3), dtype=np.float32)
        self.wide_opposite_edge_vertices: Any = np.empty((0, 3), dtype=np.float32)
        self.wide_vertex_pos_indices: Any = np.empty((0, 3), dtype=np.int32)
        self.wide_vertex_opp_indices: Any = np.empty((0, 3), dtype=np.int32)
        self.wide_edge_vertex_normals: Any = np.empty((0, 3), dtype=np.float32)
        self.camera_pos: Vector = Vector((0, 0, 0))
        self.lit_light_matrix: Matrix = Matrix.Identity(4)

    def set_object_world_matrix(self, bpy_matrix_world: Any) -> None:
        self.object_world_matrix = np.array(bpy_matrix_world,
                                            dtype=np.float32).transpose()

    def set_camera_pos(self, geomobj_matrix_world: Matrix,
                       camobj_matrix_world: Matrix) -> None:
        mat = geomobj_matrix_world.inverted() @ camobj_matrix_world
        self.camera_pos = mat @ Vector((0, 0, 0))
        self.lit_light_matrix = mat

    def init_color_data(self, color: Tuple[float, float, float, float]):
        self.edge_colors = np.full((len(self.edge_vertices), 4), color,
                                   dtype=np.float32)

    def set_vertices_and_colors(self, verts: Any, colors: Any) -> None:
        self.vertices = verts
        self.vertex_colors = colors

    def clear_vertices(self) -> None:
        self.vertices = np.empty((0, 3), dtype=np.float32)
        self.vertex_colors = np.empty((0, 4), dtype=np.float32)

    def set_backface_culling(self, state: bool) -> None:
        self.backface_culling = state

    def set_adaptive_opacity(self, value: float):
        self.adaptive_opacity = value

    def set_line_width(self, width: float) -> None:
        self.line_width = width

    def set_line_ui_scale(self, scale: float) -> None:
        self.line_ui_scale = scale

    def get_line_width(self) -> float:
        return self.line_width * self.line_ui_scale

    def clear_all(self) -> None:
        self.vertices = np.empty((0, 3), dtype=np.float32)
        self.triangle_indices = np.empty((0,), dtype=np.int32)
        self.edge_vertices = np.empty((0, 3), dtype=np.float32)
        self.edge_colors = np.empty((0, 4), dtype=np.float32)
        self.vertex_colors = np.empty((0, 4), dtype=np.float32)

        self.triangle_vertices = np.empty((0, 3), dtype=np.float32)
        self.edge_vertex_normals = np.empty((0, 3), dtype=np.float32)

        self.wide_edge_vertices = np.empty((0, 3), dtype=np.float32)
        self.wide_opposite_edge_vertices = np.empty((0, 3), dtype=np.float32)
        self.wide_vertex_pos_indices = np.empty((0, 3), dtype=np.int32)
        self.wide_vertex_opp_indices = np.empty((0, 3), dtype=np.int32)
        self.wide_edge_vertex_normals = np.empty((0, 3), dtype=np.float32)


class KTEdgeShader2D(KTEdgeShaderBase):
    def __init__(self, target_class: Any):
        super().__init__(target_class)
        self.edge_lengths: Any = np.empty((0,), dtype=np.float32)

    def init_shaders(self) -> Optional[bool]:
        if self.line_shader is not None:
            _log.output(f'{self.__class__.__name__}.line_shader: skip')
            return None

        self.line_shader = dashed_2d_shader(**Config.residual_dashed_line)
        res = self.line_shader is not None
        _log.output(f'{self.__class__.__name__}.line_shader: {res}')
        return res

    def draw_checks(self) -> bool:
        if self.is_handler_list_empty():
            self.unregister_handler()
            return False

        if not self.is_visible():
            return False

        if self.line_shader is None or self.line_batch is None:
            return False

        if not self.work_area or self.work_area != bpy_context().area:
            return False

        return True

    def draw_main(self) -> None:
        set_blend_alpha()
        set_smooth_line()
        set_line_width(self.get_line_width())
        self.line_shader.bind()
        if self.line_batch:
            self.line_batch.draw(self.line_shader)

    def create_batch(self) -> None:
        if self.line_shader is None:
            _log.error(f'{self.__class__.__name__}.line_shader: is empty')
            return

        self.line_batch = batch_for_shader(
            self.line_shader, 'LINES',
            {'pos': self.list_for_batch(self.vertices),
             'color': self.list_for_batch(self.vertex_colors),
             'lineLength': self.list_for_batch(self.edge_lengths)}
        )
        self.increment_batch_counter()

    def register_handler(self, post_type: str = 'POST_PIXEL', *, area: Any) -> None:
        _log.yellow(f'{self.__class__.__name__}.register_handler')
        _log.output('call super().register_handler')
        super().register_handler(post_type, area=area)

    def clear_all(self) -> None:
        super().clear_all()
        self.edge_lengths = np.empty((0,), dtype=np.float32)


class KTRectangleShader2D(KTEdgeShader2D):
    def __init__(self, target_class: Any=SpaceView3D):
        super().__init__(target_class)
        self.rectangles: List[List] = []
        self.line_width: float = Config.face_selection_frame_width

    def clear_rectangles(self) -> None:
        self.rectangles = []

    def add_rectangle(self, x1: float, y1: float, x2: float, y2: float,
                      frame_w: float, frame_h: float, color: Tuple) -> None:
        self.rectangles.append([
            *frame_to_image_space(x1, y1, frame_w, frame_h),
            *frame_to_image_space(x2, y2, frame_w, frame_h),
            frame_w, frame_h, (*color,), (*color,)])

    def active_rectangle_index(self, mouse_x: float, mouse_y: float) -> int:
        current_index = -1
        dist_squared = 10000000.0
        for i, rect in enumerate(self.rectangles):
            x1, y1, x2, y2 = rect[:4]
            if x1 <= mouse_x <= x2 and y1 <= mouse_y <= y2:
                d2 = (mouse_x - (x1 + x2) * 0.5) ** 2 + \
                     (mouse_y - (y1 + y2) * 0.5) ** 2
                if d2 < dist_squared:
                    dist_squared = d2
                    current_index = i
        return current_index

    def highlight_rectangle(self, index: int=-1,
                            color: Tuple=(1.0, 0.0, 0.0, 1.0)) -> None:
        for i, rect in enumerate(self.rectangles):
            rect[6] = (*color,) if i == index else (*rect[7],)

    def prepare_shader_data(self, area: Area) -> None:
        rect_points: List[Tuple] = []
        rect_colors: List[Tuple] = []

        rx1, ry1, rx2, ry2 = get_camera_border(area)

        for x1, y1, x2, y2, w, h, col1, col2 in self.rectangles:
            points = [(x1, y1), (x1, y2), (x2, y2), (x2, y1)]
            previous_p = points[-1]
            for p in points:
                rect_points.append(image_space_to_region(*previous_p,
                                                         rx1, ry1, rx2, ry2))
                rect_colors.append(col1)
                rect_points.append(image_space_to_region(*p,
                                                         rx1, ry1, rx2, ry2))
                rect_colors.append(col1)
                previous_p = p

        self.set_vertices_and_colors(rect_points, rect_colors)

    def init_shaders(self) -> Optional[bool]:
        if self.line_shader is not None:
            _log.output(f'{self.__class__.__name__}.line_shader: skip')
            return None

        self.line_shader = solid_line_2d_shader()
        res = self.line_shader is not None
        _log.output(f'{self.__class__.__name__}.line_shader: {res}')
        return res

    def draw_checks(self) -> bool:
        if self.is_handler_list_empty():
            self.unregister_handler()
            return False

        if self.line_shader is None or self.line_batch is None:
            return False

        if not self.work_area or self.work_area != bpy_context().area:
            return False

        return True

    def draw_main(self) -> None:
        set_blend_alpha()
        set_smooth_line()
        set_line_width(self.get_line_width())
        self.line_shader.bind()
        if self.line_batch:
            self.line_batch.draw(self.line_shader)

    def create_batch(self) -> None:
        if self.line_shader is None:
            _log.error(f'{self.__class__.__name__}.line_shader: is empty')
            return
        self.line_batch = batch_for_shader(
            self.line_shader, 'LINES',
            {'pos': self.list_for_batch(self.vertices),
             'color': self.list_for_batch(self.vertex_colors)}
        )


class KTScreenRectangleShader2D(KTEdgeShader2D):
    def __init__(self, target_class: Any):
        super().__init__(target_class)
        self.edge_vertices: List[Tuple[float, float, float]] = []
        self.edge_vertex_colors: List[Tuple[float, float, float, float]] = []
        self.fill_color: Tuple[float, float, float, float] = (1., 1., 1., 0.01)
        self.fill_indices: List[Tuple[int, int, int]] = [(0, 1, 3), (4, 5, 0)]

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
            self.fill_shader = simple_uniform_color_2d_shader()
            res[1] = self.fill_shader is not None
            _log.output(f'fill_shader: {res[1]}')
            changes = True
        else:
            _log.output(f'{self.__class__.__name__}.fill_shader: skip')

        if changes:
            return res[0] and res[1]
        return None

    def draw_main(self) -> None:
        set_blend_alpha()
        set_line_width(self.get_line_width())
        self.line_shader.bind()
        if self.line_batch:
            self.line_batch.draw(self.line_shader)
        self.fill_shader.bind()
        self.fill_shader.uniform_float('color', self.fill_color)
        if self.fill_batch:
            self.fill_batch.draw(self.fill_shader)

    def create_batch(self) -> None:
        self.edge_vertex_colors = [self.line_color] * len(self.edge_vertices)

        if self.line_shader is not None:
            self.line_batch = batch_for_shader(
                self.line_shader, 'LINES',
                {'pos': self.list_for_batch(self.edge_vertices),
                 'color': self.list_for_batch(self.edge_vertex_colors)}
            )
        else:
            _log.error(f'{self.__class__.__name__}.line_shader: is empty')

        if self.fill_shader is not None:
            self.fill_batch = batch_for_shader(
                self.fill_shader, 'TRIS',
                {'pos': self.list_for_batch(self.edge_vertices)},
                indices=self.fill_indices if len(self.edge_vertices) == 8 else []
            )
        else:
            _log.error(f'{self.__class__.__name__}.fill_shader: is empty')

    def clear_rectangle(self) -> None:
        self.edge_vertices = []
        self.edge_vertex_colors = []
        self.edge_lengths = []

    def clear_all(self) -> None:
        super().clear_all()
        self.clear_rectangle()

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
            self.line_shader = dashed_2d_shader(**Config.selection_dashed_line)
            res[0] = self.line_shader is not None
            _log.output(f'line_shader: {res[0]}')
            changes = True
        else:
            _log.output(f'{self.__class__.__name__}.line_shader: skip')

        if self.fill_shader is None:
            self.fill_shader = simple_uniform_color_2d_shader()
            res[1] = self.fill_shader is not None
            _log.output(f'fill_shader: {res[1]}')
            changes = True
        else:
            _log.output(f'{self.__class__.__name__}.fill_shader: skip')

        if changes:
            return res[0] and res[1]
        return None

    def create_batch(self) -> None:
        self.edge_vertex_colors = [self.line_color] * len(self.edge_vertices)

        if self.line_shader is not None:
            self.line_batch = batch_for_shader(
                self.line_shader, 'LINES',
                {'pos': self.list_for_batch(self.edge_vertices),
                 'color': self.list_for_batch(self.edge_vertex_colors),
                 'lineLength': self.list_for_batch(self.edge_lengths)})
        else:
            _log.error(f'{self.__class__.__name__}.line_shader: is empty')

        if self.fill_shader is not None:
            self.fill_batch = batch_for_shader(
                self.fill_shader, 'TRIS',
                {'pos': self.list_for_batch(self.edge_vertices)},
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
                 line_color: Tuple[float, float, float, float],
                 *, area: Optional[Area] = None):
        super().__init__(target_class)
        self.keyframes: List[int] = []
        self.state: Tuple[float, float] = (-1000.0, -1000.0)
        self.batch_needs_update: bool = True
        self.line_color = line_color
        self.line_width = Config.keyframe_line_width

    def set_keyframes(self, keyframes: List[int]) -> None:
        self.keyframes = keyframes
        self.batch_needs_update = True

    def _update_keyframe_lines(self, region: Area) -> None:
        bottom = 0
        top = Config.keyframe_line_length
        pos = [region.view2d.view_to_region(x, 0, clip=False)[0]
               for x in self.keyframes]
        self.vertices = [(x, y) for x in pos for y in (bottom, top)]
        self.vertex_colors = [self.line_color for _ in self.vertices]
        self.edge_lengths = [x for _ in pos for x in (bottom, top * 0.5)]

    def draw_checks(self) -> bool:
        if self.is_handler_list_empty():
            self.unregister_handler()
            return False

        if not self.is_visible():
            return False

        if self.line_shader is None or self.line_batch is None:
            return False

        return True

    def draw_main(self) -> None:
        area = bpy_context().area
        if not area:
            return
        region = area.regions[-1]
        assert region.type == 'WINDOW'

        current_state = (region.view2d.view_to_region(0, 0, clip=False),
                         region.view2d.view_to_region(100, 0, clip=False))
        if self.batch_needs_update or current_state != self.state:
            self.state = current_state
            self._update_keyframe_lines(region)
            self.batch_needs_update = False
            self.create_batch()

        set_blend_alpha()
        set_smooth_line()
        set_line_width(self.get_line_width())

        self.line_shader.bind()
        if self.line_batch:
            self.line_batch.draw(self.line_shader)

    def register_handler(self, post_type: str = 'POST_PIXEL',
                         *, area: Any = None) -> None:
        _log.yellow(f'{self.__class__.__name__}.register_handler')
        _log.output('call super().register_handler')
        super().register_handler(post_type, area=area)


class KTLitEdgeShaderLocal3D(KTEdgeShaderBase):
    def __init__(self, target_class: Any, mask_color: Tuple):
        super().__init__(target_class)
        self.selection_fill_color: Tuple[float, float, float, float] = mask_color
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
        self.wireframe_offset = Config.wireframe_offset_constant

    def set_lit_wireframe(self, state: bool) -> None:
        self.lit_shading = state

    def set_selection_fill_color(self, color: Tuple) -> None:
        self.selection_fill_color = color

    def set_viewport_size(self, region: Any):
        if not region or not region.width or not region.height:
            return
        w, h = region.width, region.height
        if w <= 0 or h <=0:
            return
        self.viewport_size = (w, h)

    def init_shaders(self) -> Optional[bool]:
        changes = False
        res = [True] * 4

        if self.fill_shader is None:
            self.fill_shader = black_offset_fill_local_shader()
            res[0] = self.fill_shader is not None
            _log.output(f'fill_shader (offset): {res[0]}')
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

        if self.lit_shader is None:
            self.lit_shader = lit_aa_local_shader()
            res[3] = self.lit_shader is not None
            _log.output(f'{self.__class__.__name__}.lit_shader: {res[3]}')
            changes = True
        else:
            _log.output(f'{self.__class__.__name__}.lit_shader: skip')

        if changes:
            return res[0] and res[1] and res[2] and res[3]
        return None

    def init_color_data(self, color: Tuple[float, float, float, float]) -> None:
        self.lit_color = color
        self.line_color = color

    def init_geom_data_from_core(self, edge_vertices: Any,
                                 edge_vertex_normals: Any,
                                 triangle_vertices: Any):
        len_edge_vertices = len(edge_vertices)
        if len_edge_vertices * 3 != len(self.wide_vertex_pos_indices):
            _log.output('init_geom_data_from_core recalc index arrays')
            self.wide_vertex_pos_indices, self.wide_vertex_opp_indices = \
                make_indices_for_wide_edges(len_edge_vertices)

        self.wide_edge_vertices = edge_vertices[self.wide_vertex_pos_indices]
        self.wide_opposite_edge_vertices = edge_vertices[self.wide_vertex_opp_indices]
        self.wide_edge_vertex_normals = edge_vertex_normals[self.wide_vertex_pos_indices]
        self.triangle_vertices = triangle_vertices

    def init_geom_data_from_mesh(self, obj: Any) -> None:
        _log.output(_log.color('red', 'init_geom_data_from_mesh'))
        self.set_object_world_matrix(obj.matrix_world)
        mesh = evaluated_mesh(obj)
        self.vertices = get_mesh_verts(mesh)
        self.triangle_indices = get_triangulation_indices(mesh)

        edges = np.empty((len(mesh.edges), 2), dtype=np.int32)
        mesh.edges.foreach_get(
            'vertices', np.reshape(edges, len(mesh.edges) * 2))

        self.edge_vertices = self.vertices[edges.ravel()]

    def create_batches(self) -> None:
        _log.yellow(f'{self.__class__.__name__}.create_batches start')
        if self.lit_shader is not None:
            _log.magenta('LIT WIREFRAME BATCH:')
            self.lit_batch = batch_for_shader(
                self.lit_shader, 'TRIS',
                {'pos': self.list_for_batch(self.wide_edge_vertices),
                 'opp': self.list_for_batch(self.wide_opposite_edge_vertices),
                 'vertNormal': self.list_for_batch(self.wide_edge_vertex_normals)})
            _log.output(f'\nbatch: {self.lit_batch}'
                        f'pos: {self.wide_edge_vertices.shape}'
                        f'opp: {self.wide_opposite_edge_vertices.shape}'
                        f'vertNormal: {self.wide_edge_vertex_normals.shape}')
        else:
            _log.error(f'{self.__class__.__name__}.lit_shader: is empty')

        if self.fill_shader is not None:
            _log.output('lit self.fill_shader')
            self.fill_batch = batch_for_shader(
                self.fill_shader, 'TRIS',
                {'pos': self.list_for_batch(self.triangle_vertices)})
        else:
            _log.error(f'{self.__class__.__name__}.fill_shader: is empty')

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

    def draw_checks(self) -> bool:
        if self.is_handler_list_empty():
            self.unregister_handler()
            return False

        if not self.is_visible():
            return False

        if self.lit_shader is None or self.lit_batch is None \
                or self.fill_shader is None or self.fill_batch is None:
            return False

        if not self.work_area or self.work_area != bpy_context().area:
            return False

        return True

    def draw_edges(self) -> None:
        shader = self.lit_shader
        shader.bind()
        shader.uniform_float('color', self.lit_color)
        shader.uniform_float('adaptiveOpacity', self.adaptive_opacity)
        # uniform_int is used instead of uniform_bool for backward compatibility
        shader.uniform_int('ignoreBackface', 1 if self.backface_culling else 0)
        shader.uniform_int('litShading', 1 if self.lit_shading else 0)
        shader.uniform_vector_float(
            shader.uniform_from_name('modelMatrix'),
            self.object_world_matrix.ravel(), 16)

        shader.uniform_float('pos1', self.lit_light_matrix @
                             (self.lit_light1_pos * self.lit_light_dist))
        shader.uniform_float('pos2', self.lit_light_matrix @
                             (self.lit_light2_pos * self.lit_light_dist))
        shader.uniform_float('pos3', self.lit_light_matrix @
                             (self.lit_light3_pos * self.lit_light_dist))
        shader.uniform_float('cameraPos',
                             self.lit_light_matrix @ self.lit_camera_pos)

        shader.uniform_float('viewportSize', self.viewport_size)
        shader.uniform_float('lineWidth', self.get_line_width())
        if self.lit_batch:
            self.lit_batch.draw(shader)

    def draw_main(self) -> None:
        set_depth_test('LESS_EQUAL')
        set_color_mask(False, False, False, False)
        self.draw_empty_fill()
        set_color_mask(True, True, True, True)
        set_depth_mask(False)
        set_blend_alpha()

        region = self.work_area.regions[-1]
        assert region.type == 'WINDOW'

        self.set_viewport_size(region)

        self.draw_edges()
        set_depth_test('LESS')
        self.draw_selection_fill()
        revert_blender_viewport_state()

    def clear_all(self) -> None:
        super().clear_all()
        self.wide_edge_vertices = np.empty((0, 3), dtype=np.float32)
        self.wide_opposite_edge_vertices = np.empty((0, 3), dtype=np.float32)
        self.wide_edge_vertex_normals = np.empty((0, 3), dtype=np.float32)

    def draw_empty_fill(self) -> None:
        shader = self.fill_shader
        shader.bind()
        shader.uniform_vector_float(
            shader.uniform_from_name('modelMatrix'),
            self.object_world_matrix.ravel(), 16)
        shader.uniform_float('offset', self.wireframe_offset)
        if self.fill_batch:
            self.fill_batch.draw(shader)

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

    def init_selection_from_mesh(self, obj: Object, mask_3d: str,
                                 inverted: bool) -> None:
        _log.yellow(f'{self.__class__.__name__}.init_selection_from_mesh')
        self.selection_triangle_indices = get_triangles_in_vertex_group(
            obj, mask_3d, inverted)
        if len(self.selection_triangle_indices) > 0:
            mesh = evaluated_mesh(obj)
            self.vertices = get_mesh_verts(mesh)
