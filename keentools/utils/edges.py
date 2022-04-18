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
import bpy
import gpu
import bgl
from gpu_extras.batch import batch_for_shader
from .shaders import (simple_fill_vertex_shader,
                      black_fill_fragment_shader, residual_vertex_shader,
                      residual_fragment_shader, raster_image_vertex_shader,
                      raster_image_fragment_shader,
                      solid_line_vertex_shader, solid_line_fragment_shader,
                      simple_fill_vertex_local_shader,
                      smooth_3d_vertex_local_shader, smooth_3d_fragment_shader)
from ..facebuilder.config import FBConfig
# from ..geotracker.config import GTConfig
from ..utils.images import (check_bpy_image_has_same_size,
                            find_bpy_image_by_name,
                            remove_bpy_image,
                            assign_pixels_data)
from ..utils import coords


class KTEdgeShaderBase:
    handler_list = []

    def is_visible(self):
        return self._is_shader_visible

    def set_visible(self, flag=True):
        self._is_visible = flag

    @classmethod
    def add_handler_list(cls, handler):
        cls.handler_list.append(handler)

    @classmethod
    def remove_handler_list(cls, handler):
        if handler in cls.handler_list:
            cls.handler_list.remove(handler)

    @classmethod
    def is_handler_list_empty(cls):
        return len(cls.handler_list) == 0

    def __init__(self, target_class=bpy.types.SpaceView3D):
        self.draw_handler = None
        self.fill_shader = None
        self.line_shader = None
        self.fill_batch = None
        self.line_batch = None
        # Triangle vertices & indices
        self.vertices = []
        self.triangle_indices = []
        # Edge vertices
        self.edges_vertices = []
        self.edges_indices = []
        self.edges_colors = []
        self.vertices_colors = []

        self._target_class = target_class
        self._work_area = None
        self._is_shader_visible = True

        # Check if blender started in background mode
        if not bpy.app.background:
            self.init_shaders()

    def get_target_class(self):
        return self._target_class

    def set_target_class(self, target_class):
        self._target_class = target_class

    def is_working(self):
        return not (self.draw_handler is None)

    def init_color_data(self, color=(0.5, 0.0, 0.7, 0.2)):
        self.edges_colors = np.full(
            (len(self.edges_vertices), 4), color).tolist()

    def register_handler(self, context):
        self._work_area = context.area

        if self.draw_handler is not None:
            self.unregister_handler()
        self.draw_handler = self.get_target_class().draw_handler_add(
            self.draw_callback, (context,), 'WINDOW', 'POST_VIEW')
        self.add_handler_list(self.draw_handler)

    def unregister_handler(self):
        if self.draw_handler is not None:
            self.get_target_class().draw_handler_remove(
                self.draw_handler, 'WINDOW')
            self.remove_handler_list(self.draw_handler)
        self.draw_handler = None
        self._work_area = None

    def add_vertices_colors(self, verts, colors):
        for i, v in enumerate(verts):
            self.vertices.append(verts[i])
            self.vertices_colors.append(colors[i])

    def set_vertices_colors(self, verts, colors):
        self.vertices = verts
        self.vertices_colors = colors

    def clear_vertices(self):
        self.vertices = []
        self.vertices_colors = []

    def init_shaders(self):
        pass

    def draw_callback(self, context):
        pass

    def hide_shader(self):
        self.set_visible(False)

    def unhide_shader(self):
        self.set_visible(True)

    def get_work_area(self):
        return self._work_area

    @staticmethod
    def _get_triangulation_indices(obj):
        mesh = obj.data
        mesh.calc_loop_triangles()
        indices = np.empty((len(mesh.loop_triangles), 3), dtype=np.int32)
        mesh.loop_triangles.foreach_get(
            'vertices', np.reshape(indices, len(mesh.loop_triangles) * 3))
        return indices


class KTEdgeShader2D(KTEdgeShaderBase):
    def __init__(self, target_class):
        self.edge_lengths = []
        super().__init__(target_class)

    def init_shaders(self):
        self.line_shader = gpu.types.GPUShader(
            residual_vertex_shader(), residual_fragment_shader())

    def draw_callback(self, context):
        # Force Stop
        if self.is_handler_list_empty():
            self.unregister_handler()
            return

        if self.line_shader is None or self.line_batch is None:
            return

        if self._work_area != context.area:
            return

        bgl.glEnable(bgl.GL_BLEND)
        bgl.glEnable(bgl.GL_LINE_SMOOTH)
        bgl.glHint(bgl.GL_LINE_SMOOTH_HINT, bgl.GL_NICEST)
        bgl.glBlendFunc(bgl.GL_SRC_ALPHA, bgl.GL_ONE_MINUS_SRC_ALPHA)

        self.line_shader.bind()
        self.line_batch.draw(self.line_shader)

    def create_batch(self):
        if bpy.app.background:
            return

        self.line_batch = batch_for_shader(
            self.line_shader, 'LINES',
            {'pos': self.vertices, 'color': self.vertices_colors,
             'lineLength': self.edge_lengths}
        )

    def register_handler(self, context):
        self._work_area = context.area

        if self.draw_handler is not None:
            self.unregister_handler()
        self.draw_handler = self.get_target_class().draw_handler_add(
            self.draw_callback, (context,), 'WINDOW', 'POST_PIXEL')
        self.add_handler_list(self.draw_handler)


class KTScreenRectangleShader2D(KTEdgeShader2D):
    def __init__(self, target_class):
        self._edge_vertices = []
        self._edge_vertices_colors = []
        self._line_width = 1.0
        self._line_color = (0., 0., 1.0, 0.9)
        self._fill_color = (0., 0., 1.0, 0.5)
        self._fill_indices = ((0, 1, 3), (4, 5, 0))
        super().__init__(target_class)

    def init_shaders(self):
        self.line_shader = gpu.types.GPUShader(
            solid_line_vertex_shader(), solid_line_fragment_shader())
        self.fill_shader = gpu.shader.from_builtin('2D_UNIFORM_COLOR')

    def draw_callback(self, context):
        # Force Stop
        if self.is_handler_list_empty():
            self.unregister_handler()
            return

        if self.line_shader is None or self.line_batch is None:
            return

        if self._work_area != context.area:
            return

        bgl.glEnable(bgl.GL_BLEND)
        bgl.glEnable(bgl.GL_LINE_SMOOTH)
        bgl.glHint(bgl.GL_LINE_SMOOTH_HINT, bgl.GL_NICEST)
        bgl.glBlendFunc(bgl.GL_SRC_ALPHA, bgl.GL_ONE_MINUS_SRC_ALPHA)
        bgl.glLineWidth(self._line_width)  # Rectangle Width

        self.line_shader.bind()
        self.line_batch.draw(self.line_shader)
        self.fill_shader.bind()
        self.fill_shader.uniform_float('color', self._fill_color)
        self.fill_batch.draw(self.fill_shader)

    def create_batch(self):
        if bpy.app.background:
            return
        self._edge_vertices_colors = [self._line_color] * len(self._edge_vertices)
        # Our shader batch
        self.line_batch = batch_for_shader(
            self.line_shader, 'LINES',
            {'pos': self._edge_vertices, 'color': self._edge_vertices_colors}
        )
        self.fill_batch = batch_for_shader(
            self.fill_shader, 'TRIS',
            {'pos': self._edge_vertices},
            indices=self._fill_indices if len(self._edge_vertices) == 8 else []
        )

    def clear_rectangle(self):
        self._edge_vertices = []
        self._edge_vertices_colors = []

    def add_rectangle(self, x1, y1, x2, y2):
        self._edge_vertices = [(x1, y1), (x1, y2),
                               (x1, y2), (x2, y2),
                               (x2, y2), (x2, y1),
                               (x2, y1), (x1, y1)]


class GTEdgeShaderAll2D (KTEdgeShader2D):
    def __init__(self, target_class):
        self.keyframes = []
        self._state = (-1000.0, -1000.0)
        self._batch_needs_update = True
        super().__init__(target_class)

    def set_keyframes(self, keyframes):
        self.keyframes = keyframes
        self._batch_needs_update = True

    def _update_keyframe_lines(self, area):
        bottom = 0
        top = 1000
        reg = self._get_region(area)
        pos = [reg.view2d.view_to_region(x, 0, clip=False)[0]
               for x in self.keyframes]
        self.vertices = [(x, y) for x in pos for y in (bottom, top)]
        self.vertices_colors = [(0.0, 1.0, 0.0, 0.5)  # GTConfig.timeline_keyframe_color
                                for _ in self.vertices]
        self.edge_lengths = [x for _ in pos for x in (bottom, top * 0.5)]

    def _get_region(self, area):
        return area.regions[3]

    def draw_callback(self, context):
        # Force Stop
        if self.is_handler_list_empty():
            self.unregister_handler()
            return

        if self.line_shader is None or self.line_batch is None:
            return

        if not context.area:
            return

        reg = self._get_region(context.area)
        current_state = (reg.view2d.view_to_region(0, 0, clip=False),
                         reg.view2d.view_to_region(100, 0, clip=False))
        if self._batch_needs_update or current_state != self._state:
            self._state = current_state
            self._update_keyframe_lines(context.area)
            self._batch_needs_update = False
            self.create_batch()

        bgl.glEnable(bgl.GL_BLEND)
        bgl.glEnable(bgl.GL_LINE_SMOOTH)
        bgl.glHint(bgl.GL_LINE_SMOOTH_HINT, bgl.GL_NICEST)
        bgl.glBlendFunc(bgl.GL_SRC_ALPHA, bgl.GL_ONE_MINUS_SRC_ALPHA)

        self.line_shader.bind()
        self.line_batch.draw(self.line_shader)


class KTEdgeShader3D(KTEdgeShaderBase):
    def draw_empty_fill(self):
        self.fill_batch.draw(self.fill_shader)

    def draw_edges(self):
        self.line_batch.draw(self.line_shader)

    def draw_callback(self, context):
        # Force Stop
        if self.is_handler_list_empty():
            self.unregister_handler()
            return

        if self.line_shader is None or self.line_batch is None \
                or self.fill_shader is None or self.fill_batch is None:
            return

        if self._work_area != context.area:
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

        self.draw_edges()

        bgl.glPolygonMode(bgl.GL_FRONT_AND_BACK, bgl.GL_FILL)
        bgl.glDepthMask(bgl.GL_TRUE)
        bgl.glDisable(bgl.GL_DEPTH_TEST)

    def create_batches(self):
        if bpy.app.background:
            return
        self.fill_batch = batch_for_shader(
                    self.fill_shader, 'TRIS',
                    {'pos': self.vertices},
                    indices=self.triangle_indices,
                )
        self.line_batch = batch_for_shader(
            self.line_shader, 'LINES',
            {'pos': self.edges_vertices, 'color': self.edges_colors})

    def init_shaders(self):
        self.fill_shader = gpu.types.GPUShader(
            simple_fill_vertex_shader(), black_fill_fragment_shader())

        self.line_shader = gpu.shader.from_builtin('3D_SMOOTH_COLOR')

    def init_geom_data_from_mesh(self, obj):
        # self.vertices for mesh coords
        # self.triangle_indices for hidden mesh drawing
        # self.edges_vertices for wireframe drawing
        mesh = obj.data
        verts = coords.get_mesh_verts(obj)

        mw = np.array(obj.matrix_world, dtype=np.float32).transpose()

        self.vertices = coords.multiply_verts_on_matrix_4x4(verts, mw)
        self.triangle_indices = self._get_triangulation_indices(obj)

        edges = np.empty((len(mesh.edges), 2), dtype=np.int32)
        mesh.edges.foreach_get(
            'vertices', np.reshape(edges, len(mesh.edges) * 2))

        self.edges_vertices = self.vertices[edges.ravel()]


class FBRectangleShader2D(KTEdgeShader2D):
    def __init__(self, target_class):
        self._rectangles = []
        super().__init__(target_class)

    def clear_rectangles(self):
        self._rectangles = []

    def add_rectangle(self, x1, y1, x2, y2, frame_w, frame_h, color):
        self._rectangles.append([
            *coords.frame_to_image_space(x1, y1, frame_w, frame_h),
            *coords.frame_to_image_space(x2, y2, frame_w, frame_h),
            frame_w, frame_h, (*color,), (*color,)])

    def active_rectangle_index(self, mouse_x, mouse_y):
        current_index = -1
        dist_squared = 10000000.0
        for i, rect in enumerate(self._rectangles):
            x1, y1, x2, y2 = rect[:4]
            if x1 <= mouse_x <= x2 and y1 <= mouse_y <= y2:
                d2 = (mouse_x - (x1 + x2) * 0.5) ** 2 + \
                     (mouse_y - (y1 + y2) * 0.5) ** 2
                if d2 < dist_squared:
                    dist_squared = d2
                    current_index = i
        return current_index

    def highlight_rectangle(self, index=-1, color=(1.0, 0.0, 0.0, 1.0)):
        for i, rect in enumerate(self._rectangles):
            rect[6] = (*color,) if i == index else (*rect[7],)

    def prepare_shader_data(self, context):
        rect_points = []
        rect_colors = []

        rx1, ry1, rx2, ry2 = coords.get_camera_border(context)

        for x1, y1, x2, y2, w, h, col1, col2 in self._rectangles:
            points = [(x1, y1), (x1, y2), (x2, y2), (x2, y1)]
            previous_p = points[-1]
            for p in points:
                rect_points.append(coords.image_space_to_region(*previous_p,
                                                                rx1, ry1,
                                                                rx2, ry2))
                rect_colors.append(col1)
                rect_points.append(coords.image_space_to_region(*p,
                                                                rx1, ry1,
                                                                rx2, ry2))
                rect_colors.append(col1)
                previous_p = p

        self.set_vertices_colors(rect_points, rect_colors)

    def init_shaders(self):
        self.line_shader = gpu.types.GPUShader(
            solid_line_vertex_shader(), solid_line_fragment_shader())

    def draw_callback(self, context):
        # Force Stop
        if self.is_handler_list_empty():
            self.unregister_handler()
            return

        if self.line_shader is None or self.line_batch is None:
            return

        if self._work_area != context.area:
            return

        bgl.glEnable(bgl.GL_BLEND)
        bgl.glEnable(bgl.GL_LINE_SMOOTH)
        bgl.glHint(bgl.GL_LINE_SMOOTH_HINT, bgl.GL_NICEST)
        bgl.glBlendFunc(bgl.GL_SRC_ALPHA, bgl.GL_ONE_MINUS_SRC_ALPHA)
        bgl.glLineWidth(3.0)  # Rectangle Width

        self.line_shader.bind()
        self.line_batch.draw(self.line_shader)

    def create_batch(self):
        if bpy.app.background:
            return
        self.line_batch = batch_for_shader(
            self.line_shader, 'LINES',
            {'pos': self.vertices, 'color': self.vertices_colors}
        )


class FBRasterEdgeShader3D(KTEdgeShaderBase):
    @staticmethod
    def _gamma_color(col, power=2.2):
        return [x ** power for x in col]

    @staticmethod
    def _inverse_gamma_color(col, power=2.2):
        return [x ** (1.0 / power) for x in col]

    def __init__(self, target_class):
        self._edges_indices = np.array([], dtype=np.int32)
        self._edges_uvs = []
        self._colors = [(1, 0, 0), (0, 1, 0), (0, 0, 1)]
        self._opacity = 0.3
        self._use_simple_shader = False
        super().__init__(target_class)

    def init_colors(self, colors, opacity):
        self._colors = [self._inverse_gamma_color(color[:3]) for color in colors]
        self._opacity = opacity

    def switch_to_simple_shader(self):
        self._use_simple_shader = True

    def switch_to_complex_shader(self):
        self._use_simple_shader = False

    def init_wireframe_image(self, fb, show_specials):
        if not show_specials or not fb.face_texture_available():
            self.switch_to_simple_shader()
            return False

        fb.set_face_texture_colors(self._colors)
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

    def _activate_coloring_image(self, image):
        if image.gl_load():
            raise Exception()
        image.gl_touch()

    def _deactivate_coloring_image(self, image):
        if image is not None:
            image.gl_free()

    def _check_coloring_image(self, image):
        if self._use_simple_shader:
            return True
        if image is None:
            return False

        if image.bindcode == 0:
            self._activate_coloring_image(image)
        return True

    def draw_callback(self, context):
        if not self.is_visible():
            return

        if self._work_area != context.area:
            return

        # Force Stop
        wireframe_image = find_bpy_image_by_name(FBConfig.coloring_texture_name)
        if self.is_handler_list_empty() or \
                not self._check_coloring_image(wireframe_image):
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

        self.fill_batch.draw(self.fill_shader)

        bgl.glColorMask(bgl.GL_TRUE, bgl.GL_TRUE, bgl.GL_TRUE, bgl.GL_TRUE)
        bgl.glDisable(bgl.GL_POLYGON_OFFSET_FILL)

        bgl.glDepthMask(bgl.GL_FALSE)
        bgl.glPolygonMode(bgl.GL_FRONT_AND_BACK, bgl.GL_LINE)
        bgl.glEnable(bgl.GL_DEPTH_TEST)

        if not self._use_simple_shader:
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
                self.line_shader.uniform_float('opacity', self._opacity)
                self.line_batch.draw(self.line_shader)

        if self._use_simple_shader:
            self.simple_line_shader.bind()
            self.simple_line_shader.uniform_float(
                'color', ((*self._colors[0][:3], self._opacity)))
            self.simple_line_batch.draw(self.simple_line_shader)

        bgl.glPolygonMode(bgl.GL_FRONT_AND_BACK, bgl.GL_FILL)
        bgl.glDepthMask(bgl.GL_TRUE)
        bgl.glDisable(bgl.GL_DEPTH_TEST)

    def create_batches(self):
        if bpy.app.background:
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
            {'pos': self.edges_vertices, 'texCoord': self._edges_uvs}
        )

    def init_shaders(self):
        self.fill_shader = gpu.types.GPUShader(
            simple_fill_vertex_shader(), black_fill_fragment_shader())

        self.line_shader = gpu.types.GPUShader(
            raster_image_vertex_shader(), raster_image_fragment_shader())

        self.simple_line_shader = gpu.shader.from_builtin('3D_UNIFORM_COLOR')

    def init_geom_data_from_fb(self, fb, obj, keyframe=None):
        if keyframe is not None:
            geom_verts = fb.applied_args_model_vertices_at(keyframe) @ \
                         coords.xy_to_xz_rotation_matrix_3x3()
        else:
            geom_verts = fb.applied_args_vertices() @ \
                         coords.xy_to_xz_rotation_matrix_3x3()

        m = np.array(obj.matrix_world, dtype=np.float32).transpose()
        self.vertices = coords.multiply_verts_on_matrix_4x4(geom_verts, m)
        self.triangle_indices = self._get_triangulation_indices(obj)

    def init_geom_data_from_mesh(self, obj):
        mesh = obj.data
        verts = np.empty((len(mesh.vertices), 3), dtype=np.float32)
        mesh.vertices.foreach_get(
            'co', np.reshape(verts, len(mesh.vertices) * 3))

        m = np.array(obj.matrix_world, dtype=np.float32).transpose()
        self.vertices = coords.multiply_verts_on_matrix_4x4(verts, m)
        self.triangle_indices = self._get_triangulation_indices(obj)

    def _clear_edge_indices(self):
        self._edges_indices = np.array([], dtype=np.int32)
        self._edges_uvs = []

    def init_edge_indices(self, builder):
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

        self._edges_indices = indices
        self._edges_uvs = tex_coords
        self.update_edges_vertices()

    def update_edges_vertices(self):
        self.edges_vertices = self.vertices[self._edges_indices.ravel()]


class KTEdgeShaderLocal3D(KTEdgeShader3D):
    def __init__(self, target_class):
        self.object_world_matrix = np.eye(4, dtype=np.float32)
        super().__init__(target_class)

    def init_shaders(self):
        self.fill_shader = gpu.types.GPUShader(
            simple_fill_vertex_local_shader(), black_fill_fragment_shader())

        self.line_shader = gpu.types.GPUShader(
            smooth_3d_vertex_local_shader(), smooth_3d_fragment_shader())

    def init_geom_data_from_mesh(self, obj):
        # self.vertices for evaluated mesh coords
        # self.triangle_indices for hidden mesh drawing
        # self.edges_vertices for wireframe drawing
        mw = obj.matrix_world
        scale_vec = coords.get_scale_vec_4_from_matrix_world(mw)
        scale_vec = np.array([1.0, 1.0, 1.0, 1.0], dtype=np.float32)
        scm = np.diag(scale_vec)
        scminv = np.diag(1.0 / scale_vec)

        self.object_world_matrix = scminv @ np.array(mw, dtype=np.float32).transpose()

        object_eval = coords.evaluated_mesh(obj) if obj.mode == 'OBJECT' else obj
        mesh = object_eval.data
        verts = coords.get_mesh_verts(object_eval)

        self.vertices = coords.multiply_verts_on_matrix_4x4(verts, scm)
        self.triangle_indices = self._get_triangulation_indices(object_eval)

        edges = np.empty((len(mesh.edges), 2), dtype=np.int32)
        mesh.edges.foreach_get(
            'vertices', np.reshape(edges, len(mesh.edges) * 2))

        self.edges_vertices = self.vertices[edges.ravel()]

    def draw_edges(self):
        self.line_shader.bind()
        self.line_shader.uniform_vector_float(
            self.line_shader.uniform_from_name('modelMatrix'),
            self.object_world_matrix.ravel(), 16)
        self.line_batch.draw(self.line_shader)

    def draw_empty_fill(self):
        self.fill_shader.bind()
        self.fill_shader.uniform_vector_float(
            self.fill_shader.uniform_from_name('modelMatrix'),
            self.object_world_matrix.ravel(), 16)
        self.fill_batch.draw(self.fill_shader)
