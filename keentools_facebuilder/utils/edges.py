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
from . shaders import (simple_fill_vertex_shader,
                       black_fill_fragment_shader, residual_vertex_shader,
                       residual_fragment_shader, raster_image_vertex_shader,
                       raster_image_fragment_shader)
from ..config import Config
from ..utils.images import (check_bpy_image_has_same_size,
                            find_bpy_image_by_name,
                            remove_bpy_image, add_alpha_channel)


class FBEdgeShaderBase:
    """ Wireframe drawing class """
    handler_list = []

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

    def __init__(self):
        self.draw_handler = None  # for handler storage
        self.fill_shader = None
        self.line_shader = None
        self.fill_batch = None
        self.line_batch = None
        # Triangle vertices & indices
        self.vertices = []
        self.indices = []
        # Edge vertices
        self.edges_vertices = []
        self.edges_indices = []
        self.edges_colors = []
        self.vertices_colors = []
        # Check if blender started in background mode
        if not bpy.app.background:
            self.init_shaders()

    def is_working(self):
        return not (self.draw_handler is None)

    def init_color_data(self, color=(0.5, 0.0, 0.7, 0.2)):
        self.edges_colors = np.full(
            (len(self.edges_vertices), 4), color).tolist()

    def init_special_areas(self, mesh, pairs, color=(0.5, 0.0, 0.7, 0.2)):
        for i, edge in enumerate(mesh.edges):
            vv = edge.vertices
            if ((vv[0], vv[1]) in pairs) or ((vv[1], vv[0]) in pairs):
                self.edges_colors[i * 2] = color
                self.edges_colors[i * 2 + 1] = color

    def register_handler(self, args):
        if self.draw_handler is not None:
            self.unregister_handler()
        self.draw_handler = bpy.types.SpaceView3D.draw_handler_add(
            self.draw_callback, args, "WINDOW", "POST_VIEW")
        self.add_handler_list(self.draw_handler)

    def unregister_handler(self):
        if self.draw_handler is not None:
            bpy.types.SpaceView3D.draw_handler_remove(
                self.draw_handler, "WINDOW")
            self.remove_handler_list(self.draw_handler)
        self.draw_handler = None

    def add_color_vertices(self, color, verts):
        for i, v in enumerate(verts):
            self.vertices.append(verts[i])
            self.vertices_colors.append(color)

    def add_vertices_colors(self, verts, colors):
        for i, v in enumerate(verts):
            self.vertices.append(verts[i])
            self.vertices_colors.append(colors[i])

    def set_color_vertices(self, color, verts):
        self.clear_vertices()
        self.add_color_vertices(color, verts)

    def set_vertices_colors(self, verts, colors):
        self.clear_vertices()
        self.add_vertices_colors(verts, colors)

    def clear_vertices(self):
        self.vertices = []
        self.vertices_colors = []

    def init_shaders(self):
        pass

    def draw_callback(self, op, context):
        pass


class FBEdgeShader2D(FBEdgeShaderBase):
    def __init__(self):
        self.edge_lengths = []
        super().__init__()

    def init_shaders(self):
        self.line_shader = gpu.types.GPUShader(
            residual_vertex_shader(), residual_fragment_shader())

    def draw_callback(self, op, context):
        # Force Stop
        if self.is_handler_list_empty():
            self.unregister_handler()
            return

        if self.line_shader is None or self.line_batch is None:
            return

        bgl.glEnable(bgl.GL_BLEND)
        bgl.glEnable(bgl.GL_LINE_SMOOTH)
        bgl.glHint(bgl.GL_LINE_SMOOTH_HINT, bgl.GL_NICEST)
        bgl.glBlendFunc(bgl.GL_SRC_ALPHA, bgl.GL_ONE_MINUS_SRC_ALPHA)

        self.line_shader.bind()
        self.line_batch.draw(self.line_shader)

    def create_batch(self):
        # Our shader batch
        self.line_batch = batch_for_shader(
            self.line_shader, 'LINES',
            {"pos": self.vertices, "color": self.vertices_colors,
             "lineLength": self.edge_lengths}
        )

    def register_handler(self, args):
        if self.draw_handler is not None:
            self.unregister_handler()
        self.draw_handler = bpy.types.SpaceView3D.draw_handler_add(
            self.draw_callback, args, "WINDOW", "POST_PIXEL")
        self.add_handler_list(self.draw_handler)


class FBRasterEdgeShader3D(FBEdgeShaderBase):
    @staticmethod
    def _gamma_color(col, power=2.2):
        return [x ** power for x in col]

    @staticmethod
    def _inverse_gamma_color(col, power=2.2):
        return [x ** (1.0 / power) for x in col]

    def __init__(self):
        self._edges_indices = np.array([], dtype=np.int)
        self._edges_uvs = []
        self._colors = [(1, 0, 0), (0, 1, 0), (0, 0, 1)]
        self._opacity = 0.3
        self._use_simple_shader = False
        super().__init__()

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
        image_data = fb.face_texture()[::2, ::2, :]  # sample down x0.5
        size = image_data.shape[:2]
        assert size[0] > 0 and size[1] > 0
        image_name = Config.coloring_texture_name
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
            rgba = add_alpha_channel(image_data)
            wireframe_image.pixels[:] = rgba.ravel()
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

    def draw_callback(self, op, context):
        # Force Stop
        wireframe_image = find_bpy_image_by_name(Config.coloring_texture_name)
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
            indices=self.indices,
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

    def init_geom_data(self, obj):
        mesh = obj.data
        mesh.calc_loop_triangles()

        verts = np.empty((len(mesh.vertices), 3), 'f')
        indices = np.empty((len(mesh.loop_triangles), 3), 'i')

        mesh.vertices.foreach_get(
            "co", np.reshape(verts, len(mesh.vertices) * 3))
        mesh.loop_triangles.foreach_get(
            "vertices", np.reshape(indices, len(mesh.loop_triangles) * 3))

        # Object matrix usage
        m = np.array(obj.matrix_world, dtype=np.float32).transpose()
        vv = np.ones((len(mesh.vertices), 4), dtype=np.float32)
        vv[:, :-1] = verts
        vv = vv @ m

        self.vertices = vv[:, :3]  # Transformed vertices
        self.indices = indices

    def _clear_edge_indices(self):
        self._edges_indices = np.array([], dtype=np.int)
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
        indices = np.empty((sum(face_counts), 2), 'i')
        tex_coords = np.empty((sum(face_counts) * 2, 2), 'f')

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
