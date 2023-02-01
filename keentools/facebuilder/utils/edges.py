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

from typing import Any, Tuple, List, Optional
import numpy as np

import bpy
from bpy.types import Area, Image, Object, SpaceView3D
import bgl
import gpu
from gpu_extras.batch import batch_for_shader

from ...facebuilder_config import FBConfig
from ...utils.bpy_common import bpy_background_mode
from ...utils.edges import KTEdgeShaderBase, KTEdgeShader2D
from ...utils.coords import (frame_to_image_space,
                             get_camera_border,
                             image_space_to_region,
                             xy_to_xz_rotation_matrix_3x3,
                             multiply_verts_on_matrix_4x4,
                             get_triangulation_indices)
from ...utils.shaders import (solid_line_vertex_shader,
                              solid_line_fragment_shader,
                              simple_fill_vertex_shader,
                              black_fill_fragment_shader,
                              raster_image_vertex_shader,
                              raster_image_fragment_shader)
from ...utils.images import (check_bpy_image_has_same_size,
                             find_bpy_image_by_name,
                             remove_bpy_image,
                             assign_pixels_data,
                             inverse_gamma_color)


class FBRectangleShader2D(KTEdgeShader2D):
    def __init__(self, target_class: Any=SpaceView3D):
        self.rectangles = []
        super().__init__(target_class)
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

    def init_shaders(self) -> None:
        self.line_shader = gpu.types.GPUShader(
            solid_line_vertex_shader(), solid_line_fragment_shader())

    def draw_checks(self, context: Any) -> bool:
        if self.is_handler_list_empty():
            self.unregister_handler()
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

    def create_batch(self) -> None:
        if bpy_background_mode():
            return
        self.line_batch = batch_for_shader(
            self.line_shader, 'LINES',
            {'pos': self.vertices, 'color': self.vertices_colors}
        )


class FBRasterEdgeShader3D(KTEdgeShaderBase):
    def __init__(self, target_class: Any=SpaceView3D):
        self.edge_indices: Any = np.array([], dtype=np.int32)
        self.edge_uvs: List = []
        self.texture_colors: List = [(1., 0., 0.), (0., 1., 0.), (0., 0., 1.)]
        self.opacity: float = 0.5
        self.use_simple_shader = False
        super().__init__(target_class)

    def init_colors(self, colors: List, opacity: float) -> None:
        self.texture_colors = [inverse_gamma_color(color[:3]) for color in colors]
        self.opacity = opacity

    def switch_to_simple_shader(self) -> None:
        self.use_simple_shader = True

    def switch_to_complex_shader(self) -> None:
        self.use_simple_shader = False

    def init_wireframe_image(self, fb: Any, show_specials: bool) -> bool:
        if not show_specials or not fb.face_texture_available():
            self.switch_to_simple_shader()
            return False

        fb.set_face_texture_colors(self.texture_colors)
        image_data = fb.face_texture()
        size = image_data.shape[:2]
        assert size[0] > 0 and size[1] > 0
        image_name = FBConfig.coloring_texture_name
        wireframe_image = find_bpy_image_by_name(image_name)
        if wireframe_image is None or \
                not check_bpy_image_has_same_size(wireframe_image, size):
            remove_bpy_image(wireframe_image)
            wireframe_image = bpy.data.images.new(image_name,
                                                  width=size[1],
                                                  height=size[0],
                                                  alpha=True,
                                                  float_buffer=False)
        if wireframe_image:
            rgba = np.ones((size[1], size[0], 4), dtype=np.float32)
            rgba[:, :, :3] = image_data
            assign_pixels_data(wireframe_image.pixels, rgba.ravel())
            wireframe_image.pack()
            self.switch_to_complex_shader()
            return True
        self.switch_to_simple_shader()
        return False

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
        self.fill_batch.draw(self.fill_shader)

    def draw_checks(self, context: Any) -> bool:
        if self.is_handler_list_empty():
            self.unregister_handler()
            return False

        if not self.is_visible():
            return False

        if self.work_area != context.area:
            return False

        return True

    def draw_main_bgl(self, context: Any) -> None:
        wireframe_image = find_bpy_image_by_name(FBConfig.coloring_texture_name)
        if not self._check_coloring_image(wireframe_image):
            self.unregister_handler()
            return

        bgl.glEnable(bgl.GL_BLEND)
        bgl.glEnable(bgl.GL_LINE_SMOOTH)
        bgl.glHint(bgl.GL_LINE_SMOOTH_HINT, bgl.GL_NICEST)
        bgl.glBlendFunc(bgl.GL_SRC_ALPHA, bgl.GL_ONE_MINUS_SRC_ALPHA)

        bgl.glEnable(bgl.GL_DEPTH_TEST)
        bgl.glEnable(bgl.GL_POLYGON_OFFSET_FILL)
        bgl.glPolygonOffset(1.0, 1.0)

        bgl.glColorMask(bgl.GL_FALSE, bgl.GL_FALSE, bgl.GL_FALSE, bgl.GL_FALSE)
        bgl.glPolygonMode(bgl.GL_FRONT_AND_BACK, bgl.GL_FILL)

        self.draw_empty_fill()

        bgl.glColorMask(bgl.GL_TRUE, bgl.GL_TRUE, bgl.GL_TRUE, bgl.GL_TRUE)
        bgl.glDisable(bgl.GL_POLYGON_OFFSET_FILL)

        bgl.glDepthMask(bgl.GL_FALSE)
        bgl.glPolygonMode(bgl.GL_FRONT_AND_BACK, bgl.GL_LINE)
        bgl.glEnable(bgl.GL_DEPTH_TEST)
        bgl.glLineWidth(self.line_width)

        if not self.use_simple_shader:
            # coloring_image.bindcode should not be zero
            # if we don't want to destroy video driver in Blender
            if not wireframe_image or wireframe_image.bindcode == 0:
                self.switch_to_simple_shader()
            else:
                bgl.glActiveTexture(bgl.GL_TEXTURE0)
                bgl.glBindTexture(bgl.GL_TEXTURE_2D,
                                  wireframe_image.bindcode)
                self.line_shader.bind()
                self.line_shader.uniform_int('image', 0)
                self.line_shader.uniform_float('opacity', self.opacity)
                self.line_batch.draw(self.line_shader)

        if self.use_simple_shader:
            self.simple_line_shader.bind()
            self.simple_line_shader.uniform_float(
                'color', ((*self.texture_colors[0][:3], self.opacity)))
            self.simple_line_batch.draw(self.simple_line_shader)

        bgl.glPolygonMode(bgl.GL_FRONT_AND_BACK, bgl.GL_FILL)
        bgl.glDepthMask(bgl.GL_TRUE)
        bgl.glDisable(bgl.GL_DEPTH_TEST)

    def draw_simple_line_gpu(self):
        gpu.state.line_width_set(self.line_width * 2)
        gpu.state.blend_set('ALPHA')
        self.simple_line_shader.bind()
        self.simple_line_shader.uniform_float(
            'color', ((*self.texture_colors[0][:3], self.opacity)))
        self.simple_line_batch.draw(self.simple_line_shader)

    def draw_textured_line_gpu(self):
        wireframe_image = find_bpy_image_by_name(FBConfig.coloring_texture_name)
        if not self._check_coloring_image(wireframe_image):
            self.unregister_handler()
            return
        if not wireframe_image or wireframe_image.bindcode == 0:
            self.switch_to_simple_shader()
            self.draw_simple_line_gpu()
        else:
            gpu.state.line_width_set(self.line_width * 2)
            gpu.state.blend_set('ALPHA')
            self.line_shader.bind()
            self.line_shader.uniform_sampler(
                'image', gpu.texture.from_image(wireframe_image))
            self.line_shader.uniform_float('opacity', self.opacity)
            self.line_batch.draw(self.line_shader)

    def draw_main_gpu(self, context: Any) -> None:
        gpu.state.depth_test_set('LESS_EQUAL')
        gpu.state.color_mask_set(False, False, False, False)
        self.draw_empty_fill()
        gpu.state.color_mask_set(True, True, True, True)
        if not self.use_simple_shader:
            self.draw_textured_line_gpu()
        else:
            self.draw_simple_line_gpu()

    def create_batches(self) -> None:
        if bpy_background_mode():
            return
        self.fill_batch = batch_for_shader(
            self.fill_shader, 'TRIS',
            {'pos': self.vertices},
            indices=self.triangle_indices,
        )

        self.simple_line_batch = batch_for_shader(
            self.simple_line_shader, 'LINES',
            {'pos': self.edges_vertices},
        )

        self.line_batch = batch_for_shader(
            self.line_shader, 'LINES',
            {'pos': self.edges_vertices, 'texCoord': self.edge_uvs}
        )

    def init_shaders(self) -> None:
        self.fill_shader = gpu.types.GPUShader(
            simple_fill_vertex_shader(), black_fill_fragment_shader())

        self.line_shader = gpu.types.GPUShader(
            raster_image_vertex_shader(), raster_image_fragment_shader())

        self.simple_line_shader = gpu.shader.from_builtin('3D_UNIFORM_COLOR')

    def init_geom_data_from_fb(self, fb: Any, obj: Object,
                               keyframe: Optional[int]=None) -> None:
        if keyframe is not None:
            geom_verts = fb.applied_args_model_vertices_at(keyframe) @ \
                         xy_to_xz_rotation_matrix_3x3()
        else:
            geom_verts = fb.applied_args_vertices() @ \
                         xy_to_xz_rotation_matrix_3x3()

        m = np.array(obj.matrix_world, dtype=np.float32).transpose()
        self.vertices = multiply_verts_on_matrix_4x4(geom_verts, m)
        self.triangle_indices = get_triangulation_indices(obj.data)

    def init_geom_data_from_mesh(self, obj: Object) -> None:
        mesh = obj.data
        verts = np.empty((len(mesh.vertices), 3), dtype=np.float32)
        mesh.vertices.foreach_get(
            'co', np.reshape(verts, len(mesh.vertices) * 3))

        m = np.array(obj.matrix_world, dtype=np.float32).transpose()
        self.vertices = multiply_verts_on_matrix_4x4(verts, m)
        self.triangle_indices = get_triangulation_indices(mesh)

    def _clear_edge_indices(self) -> None:
        self.edge_indices = np.array([], dtype=np.int32)
        self.edge_uvs = []

    def init_edge_indices(self, builder: Any) -> None:
        if not builder.face_texture_available():
            self._clear_edge_indices()
            return
        keyframes = builder.keyframes()
        if len(keyframes) == 0:
            return
        geo = builder.applied_args_replaced_uvs_model_at(keyframes[0])
        me = geo.mesh(0)
        face_counts = [me.face_size(x) for x in range(me.faces_count())]
        indices = np.empty((sum(face_counts), 2), dtype=np.int32)
        tex_coords = np.empty((sum(face_counts) * 2, 2), dtype=np.float32)

        i = 0
        for face, count in enumerate(face_counts):
            tex_coords[i * 2] = me.uv(face, count - 1)
            tex_coords[i * 2 + 1] = me.uv(face, 0)
            indices[i] = (me.face_point(face, count - 1),
                          me.face_point(face, 0))
            i += 1
            for k in range(1, count):
                tex_coords[i * 2] = me.uv(face, k - 1)
                tex_coords[i * 2 +1] = me.uv(face, k)
                indices[i] = (me.face_point(face, k - 1),
                              me.face_point(face, k))
                i += 1

        self.edge_indices = indices
        self.edge_uvs = tex_coords
        self.update_edge_vertices()

    def update_edge_vertices(self) -> None:
        self.edges_vertices = self.vertices[self.edge_indices.ravel()]
