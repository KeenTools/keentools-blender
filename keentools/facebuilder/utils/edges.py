# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2019-2023  KeenTools

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

import bpy
from bpy.types import Area, Image, Object, SpaceView3D
from mathutils import Vector

from gpu_extras.batch import batch_for_shader

from ...utils.kt_logging import KTLogger
from ...addon_config import fb_settings
from ...facebuilder_config import FBConfig
from ...utils.edges import KTEdgeShaderBase, KTEdgeShader2D
from ...utils.coords import (frame_to_image_space,
                             get_camera_border,
                             image_space_to_region,
                             xy_to_xz_rotation_matrix_3x3,
                             multiply_verts_on_matrix_4x4,
                             get_triangulation_indices,
                             make_indices_for_wide_edges)
from ...utils.gpu_shaders import (solid_line_2d_shader,
                                  black_offset_fill_local_shader,
                                  raster_image_shader,
                                  uniform_color_3d_shader)

from ...utils.images import (check_bpy_image_has_same_size,
                             find_bpy_image_by_name,
                             remove_bpy_image,
                             assign_pixels_data,
                             inverse_gamma_color)
from ...utils.gpu_control import (set_blend_alpha,
                                  set_smooth_line,
                                  set_line_width,
                                  set_shader_sampler,
                                  set_depth_test,
                                  set_depth_mask,
                                  set_color_mask,
                                  revert_blender_viewport_state)
from ...utils.fb_wireframe_image import (create_wireframe_image,
                                         create_edge_indices)


_log = KTLogger(__name__)


class FBRectangleShader2D(KTEdgeShader2D):
    def __init__(self, target_class: Any=SpaceView3D):
        super().__init__(target_class)
        self.rectangles = []
        self.line_width = FBConfig.face_selection_frame_width

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
        rect_points = []
        rect_colors = []

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

        self.set_vertices_colors(rect_points, rect_colors)

    def init_shaders(self) -> Optional[bool]:
        if self.line_shader is not None:
            _log.output(f'{self.__class__.__name__}.line_shader: skip')
            return None

        self.line_shader = solid_line_2d_shader()
        res = self.line_shader is not None
        _log.output(f'{self.__class__.__name__}.line_shader: {res}')
        return res

    def draw_checks(self, context: Any) -> bool:
        if self.is_handler_list_empty():
            self.unregister_handler()
            return False

        if self.line_shader is None or self.line_batch is None:
            return False

        if self.work_area != context.area:
            return False

        return True

    def draw_main(self, context: Any) -> None:
        set_blend_alpha()
        set_smooth_line()
        set_line_width(self.line_width)
        self.line_shader.bind()
        self.line_batch.draw(self.line_shader)

    def create_batch(self) -> None:
        if self.line_shader is None:
            _log.error(f'{self.__class__.__name__}.line_shader: is empty')
            return
        self.line_batch = batch_for_shader(
            self.line_shader, 'LINES',
            {'pos': self.vertices, 'color': self.vertices_colors}
        )


class FBRasterEdgeShader3D(KTEdgeShaderBase):
    def __init__(self, target_class: Any=SpaceView3D):
        super().__init__(target_class)
        self.edge_indices: Any = np.array([], dtype=np.int32)
        self.edge_uvs: Any = np.empty(shape=(0, 3), dtype=np.float32)
        self.wide_edge_uvs: Any = np.empty(shape=(0, 2), dtype=np.float32)

        self.viewport_size: Tuple[float, float] = (1920, 1080)
        self.camera_pos: Vector = Vector((0, 0, 0))

        self.texture_colors: List = [(1., 0., 0.), (0., 1., 0.), (0., 0., 1.)]
        self.opacity: float = 0.5
        self.use_simple_shader: bool = False
        self.simple_line_shader: Optional[Any] = None

        self.wireframe_offset = FBConfig.wireframe_offset_constant

    def get_statistics(self):
        return f'\nvertices: {len(self.vertices)}' \
               f'\ntriangle_indices: {len(self.triangle_indices)}' \
               f'\ntriangle_vertices: {len(self.triangle_vertices)}' \
               f'\nedge_vertices: {len(self.edge_vertices)}' \
               f'\nedge_colors: {len(self.edge_colors)}' \
               f'\nedge_indices: {len(self.edge_indices)}' \
               f'\nedge_uvs: {len(self.edge_uvs)}' \
               f'\nwide_edge_vertices: {len(self.wide_edge_vertices)}' \
               f'\nwide_opposite_edge_vertices: {len(self.wide_opposite_edge_vertices)}' \
               f'\ntexture_colors: {self.texture_colors}'

    def set_viewport_size(self, region: Any) -> None:
        if not region or not region.width or not region.height:
            return
        w, h = region.width, region.height
        if w <= 0 or h <=0:
            return
        self.viewport_size = (w, h)

    def set_camera_pos(self, camobj: Optional[Object],
                       geomobj: Optional[Object]) -> None:
        if not geomobj or not camobj:
            return
        mat = geomobj.matrix_world.inverted() @ camobj.matrix_world
        self.camera_pos = mat @ Vector((0, 0, 0))

    def init_colors(self, colors: List, opacity: float) -> None:
        self.texture_colors = [inverse_gamma_color(color[:3]) for color in colors]
        self.opacity = opacity

    def switch_to_simple_shader(self) -> None:
        self.use_simple_shader = True

    def switch_to_complex_shader(self) -> None:
        self.use_simple_shader = False

    def init_wireframe_image(self, show_specials: bool) -> bool:
        _log.output('init_wireframe_image call')
        if not show_specials:
            self.switch_to_simple_shader()
            return False

        if not create_wireframe_image(self.texture_colors):
            self.switch_to_simple_shader()
            return False

        self.switch_to_complex_shader()
        return True

    def _activate_coloring_image(self, image: Image) -> None:
        if image.gl_load():
            raise Exception()
        image.gl_touch()

    def _deactivate_coloring_image(self, image: Optional[Image]) -> None:
        if image is not None:
            image.gl_free()

    def _check_coloring_image(self, image: Optional[Image]) -> bool:
        if self.use_simple_shader:
            return True
        if image is None:
            return False

        if image.bindcode == 0:
            self._activate_coloring_image(image)
        return True

    def draw_empty_fill(self) -> None:
        shader = self.fill_shader
        shader.bind()
        shader.uniform_vector_float(
            shader.uniform_from_name('modelMatrix'),
            self.object_world_matrix.ravel(), 16)
        shader.uniform_float('offset', self.wireframe_offset)
        self.fill_batch.draw(shader)

    def draw_checks(self, context: Any) -> bool:
        if self.is_handler_list_empty():
            self.unregister_handler()
            return False

        if not self.is_visible():
            return False

        if self.work_area != context.area:
            return False

        return True

    def _draw_simple_line(self):
        set_line_width(self.line_width)
        set_blend_alpha()
        shader = self.simple_line_shader
        shader.bind()
        shader.uniform_float('color',
                             ((*self.texture_colors[0][:3], self.opacity)))
        shader.uniform_float('adaptiveOpacity', self.adaptive_opacity)
        shader.uniform_vector_float(
            shader.uniform_from_name('modelMatrix'),
            self.object_world_matrix.ravel(), 16)
        shader.uniform_float('viewportSize', self.viewport_size)
        shader.uniform_float('lineWidth', self.line_width)
        self.simple_line_batch.draw(shader)

    def _draw_textured_line(self):
        wireframe_image = find_bpy_image_by_name(FBConfig.coloring_texture_name)
        if not self._check_coloring_image(wireframe_image):
            _log.error(f'draw_textured_line_gpu _check_coloring_image failed: {wireframe_image}')
            self.unregister_handler()
            return
        if not wireframe_image:
            self.switch_to_simple_shader()
            self._draw_simple_line()
            _log.error('draw_textured_line_gpu switched to simple')
        else:
            set_blend_alpha()
            shader = self.line_shader
            shader.bind()
            set_shader_sampler(shader, wireframe_image)
            shader.uniform_float('opacity', self.opacity)
            shader.uniform_float('adaptiveOpacity', self.adaptive_opacity)
            shader.uniform_vector_float(
                shader.uniform_from_name('modelMatrix'),
                self.object_world_matrix.ravel(), 16)
            shader.uniform_float('viewportSize', self.viewport_size)
            shader.uniform_float('lineWidth', self.line_width)
            shader.uniform_int('ignoreBackface', 1 if self.backface_culling else 0)
            shader.uniform_float('cameraPos', self.camera_pos)
            self.line_batch.draw(shader)

    def draw_main(self, context: Any) -> None:
        set_depth_test('LESS_EQUAL')
        set_color_mask(False, False, False, False)
        self.draw_empty_fill()
        set_color_mask(True, True, True, True)
        self.set_viewport_size(context.region)
        set_depth_mask(False)
        if not self.use_simple_shader:
            self._draw_textured_line()
        else:
            self._draw_simple_line()
        revert_blender_viewport_state()

    def create_batches(self) -> None:
        if self.fill_shader is not None:
            self.fill_batch = batch_for_shader(
                self.fill_shader, 'TRIS',
                {'pos': self.triangle_vertices}
            )
        else:
            _log.error(f'{self.__class__.__name__}.fill_shader: is empty')

        if self.simple_line_shader is not None:
            self.simple_line_batch = batch_for_shader(
                self.simple_line_shader, 'TRIS',
                {'pos': self.list_for_batch(self.wide_edge_vertices),
                 'opp': self.list_for_batch(self.wide_opposite_edge_vertices),
                 }
            )
        else:
            _log.error(f'{self.__class__.__name__}.simple_line_shader: is empty')

        if self.line_shader is not None:
            self.line_batch = batch_for_shader(
                self.line_shader, 'TRIS',
                {'pos': self.list_for_batch(self.wide_edge_vertices),
                 'opp': self.list_for_batch(self.wide_opposite_edge_vertices),
                 'vertNormal': self.list_for_batch(self.wide_edge_vertex_normals),
                 'texCoord': self.list_for_batch(self.wide_edge_uvs),
                 }
            )
        else:
            _log.error(f'{self.__class__.__name__}.line_shader: is empty')

    def init_shaders(self) -> Optional[bool]:
        changes = False
        res = [True] * 3

        if self.fill_shader is None:
            self.fill_shader = black_offset_fill_local_shader()
            res[0] = self.fill_shader is not None
            _log.output(f'{self.__class__.__name__}.fill_shader: {res[0]}')
            changes = True
        else:
            _log.output(f'{self.__class__.__name__}.fill_shader: skip')

        if self.simple_line_shader is None:
            self.simple_line_shader = uniform_color_3d_shader()
            res[2] = self.simple_line_shader is not None
            _log.output(f'{self.__class__.__name__}.simple_line_shader: {res[2]}')
            changes = True
        else:
            _log.output(f'{self.__class__.__name__}.simple_line_shader: skip')

        if self.line_shader is None:
            self.line_shader = raster_image_shader()
            res[1] = self.line_shader is not None
            _log.output(f'{self.__class__.__name__}.line_shader: {res[1]}')
            changes = True
        else:
            _log.output(f'{self.__class__.__name__}.line_shader: skip')

        if changes:
            return res[0] and res[1] and res[2]
        return None

    def init_geom_data_from_fb(self, fb: Any, obj: Object,
                               keyframe: Optional[int]=None) -> None:
        if keyframe is not None:
            geom_verts = fb.applied_args_model_vertices_at(keyframe) @ \
                         xy_to_xz_rotation_matrix_3x3()
        else:
            geom_verts = fb.applied_args_vertices() @ \
                         xy_to_xz_rotation_matrix_3x3()

        mat = np.array(obj.matrix_world, dtype=np.float32).transpose()
        self.vertices = multiply_verts_on_matrix_4x4(geom_verts, mat)
        self.triangle_indices = get_triangulation_indices(obj.data)

    def init_geom_data_from_mesh(self, obj: Object) -> None:
        mesh = obj.data
        verts = np.empty((len(mesh.vertices), 3), dtype=np.float32)
        mesh.vertices.foreach_get(
            'co', np.reshape(verts, len(mesh.vertices) * 3))

        m = np.array(obj.matrix_world, dtype=np.float32).transpose()
        self.vertices = multiply_verts_on_matrix_4x4(verts, m)
        self.triangle_indices = get_triangulation_indices(mesh)

    def _clear_edge_uvs(self) -> None:
        self.edge_indices = np.empty(shape=(0, 2), dtype=np.int32)
        self.edge_uvs = np.empty(shape=(0, 3), dtype=np.float32)
        self.wide_edge_uvs = np.empty(shape=(0, 3), dtype=np.float32)

    def init_edge_indices(self) -> None:
        _log.blue('fb init_edge_indices')
        fb = fb_settings().loader().get_builder()
        self.edge_indices, self.edge_uvs = create_edge_indices(fb=fb)

    def init_geom_data_from_core(self, edge_vertices: Any,
                                 edge_vertex_normals: Any,
                                 triangle_vertices: Any) -> None:
        _log.output(_log.color('yellow', 'init_geom_data_from_core'))
        len_edge_vertices = len(edge_vertices)
        if len_edge_vertices * 3 != len(self.wide_vertex_pos_indices):
            _log.output('init_geom_data_from_core recalc index arrays')
            self.wide_vertex_pos_indices, self.wide_vertex_opp_indices = \
                make_indices_for_wide_edges(len_edge_vertices)

        self.wide_edge_vertices = edge_vertices[self.wide_vertex_pos_indices]
        self.wide_opposite_edge_vertices = edge_vertices[self.wide_vertex_opp_indices]
        self.wide_edge_vertex_normals = edge_vertex_normals[self.wide_vertex_pos_indices]

        self.wide_edge_uvs = self.edge_uvs[self.wide_vertex_pos_indices]
        self.triangle_vertices = triangle_vertices
