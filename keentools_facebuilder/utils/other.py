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


import bpy
import gpu
from gpu_extras.batch import batch_for_shader
import numpy as np
import math
import blf
import bgl

from keentools_facebuilder.utils import coords
from .. config import get_main_settings, config


def force_stop_shaders():
    FBEdgeShader3D.handler_list = []
    FBText.handler_list = []
    FBPoints2D.handler_list = []
    FBPoints3D.handler_list = []


class FBStopTimer:
    active = False

    @classmethod
    def set_active(cls):
        cls.active = True

    @classmethod
    def set_inactive(cls):
        cls.active = False

    @classmethod
    def is_active(cls):
        return cls.active

    @classmethod
    def check_pinmode(cls):
        settings = get_main_settings()
        if not cls.is_active():
            # Timer works when shouldn't
            print("STOP INACTIVE")
            return None
        # Timer is active
        if not settings.pinmode:
            # But we are not in pinmode
            force_stop_shaders()
            cls.stop()
            print("STOP FORCE")
            return None

        # Interval to next call
        print("NEXT CALL")
        return 1.0

    @classmethod
    def start(cls):
        cls.stop()
        bpy.app.timers.register(cls.check_pinmode, persistent=True)
        print("== REGISTER TIMER")
        cls.set_active()

    @classmethod
    def stop(cls):
        if bpy.app.timers.is_registered(cls.check_pinmode):
            print("== UNREGISTER TIMER")
            bpy.app.timers.unregister(cls.check_pinmode)
        cls.set_inactive()


class FBText:
    """ Text on screen output in Modal view"""
    # Test only
    counter = 0

    # Store all draw handlers registered by class objects
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
        self.text_draw_handler = None
        self.message = [
            "Pin Mode ",
            "Press 'Esc' to Exit "
        ]

    def set_message(self, msg):
        self.message = msg

    @classmethod
    def inc_counter(cls):
        cls.counter += 1

    def text_draw_callback(self, op, context):
        # Force Stop
        if self.is_handler_list_empty():
            self.unregister_handler()
            return

        self.inc_counter()
        # TESTING
        settings = get_main_settings()
        opnum = settings.opnum
        camnum = settings.current_camnum
        # Draw text
        if len(self.message) > 0:
            region = context.region
            text = "Cam [{0}] {1}".format(camnum, self.message[0])
            # TESTING
            subtext = "{} {}".format(self.message[1], opnum)
            # subtext = self.message[1]

            xt = int(region.width / 2.0)

            blf.size(0, 24, 72)
            blf.position(0, xt - blf.dimensions(0, text)[0] / 2, 60, 0)
            blf.draw(0, text)

            blf.size(0, 20, 72)
            blf.position(0, xt - blf.dimensions(0, subtext)[0] / 2, 30, 1)
            blf.draw(0, subtext)  # Text is on screen

    def register_handler(self, args):
        # Draw text on screen registration
        self.text_draw_handler = bpy.types.SpaceView3D.draw_handler_add(
            self.text_draw_callback, args, "WINDOW", "POST_PIXEL")
        self.add_handler_list(self.text_draw_handler)

    def unregister_handler(self):
        if self.text_draw_handler is not None:
            bpy.types.SpaceView3D.draw_handler_remove(
                self.text_draw_handler, "WINDOW")
            self.remove_handler_list(self.text_draw_handler)
        self.text_draw_handler = None


class FBShaderPoints:
    """ Base class for Point Drawing Shaders """
    point_size = config.default_pin_size

    # Store all draw handlers registered by class objects
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
        self.draw_handler = None  # for 3d shader
        self.shader = None
        self.batch = None

        self.vertices = []
        self.vertices_colors = []

    @classmethod
    def set_point_size(cls, ps):
        cls.point_size = ps

    def _create_batch(self, vertices, vertices_colors,
                      shadername='2D_FLAT_COLOR'):
        if shadername == 'CUSTOM_3D':
            # 3D_FLAT_COLOR
            vertex_shader = '''
                uniform mat4 ModelViewProjectionMatrix;
                #ifdef USE_WORLD_CLIP_PLANES
                uniform mat4 ModelMatrix;
                #endif

                in vec3 pos;
                #if defined(USE_COLOR_U32)
                in uint color;
                #else
                in vec4 color;
                #endif

                flat out vec4 finalColor;

                void main()
                {
                    vec4 pos_4d = vec4(pos, 1.0);
                    gl_Position = ModelViewProjectionMatrix * pos_4d;

                #if defined(USE_COLOR_U32)
                    finalColor = vec4(
                        ((color      ) & uint(0xFF)) * (1.0f / 255.0f),
                        ((color >>  8) & uint(0xFF)) * (1.0f / 255.0f),
                        ((color >> 16) & uint(0xFF)) * (1.0f / 255.0f),
                        ((color >> 24)             ) * (1.0f / 255.0f));
                #else
                    finalColor = color;
                #endif

                #ifdef USE_WORLD_CLIP_PLANES
                    world_clip_planes_calc_clip_distance((ModelMatrix * pos_4d).xyz);
                #endif
                }
            '''
            fragment_shader = '''
                flat in vec4 finalColor;
                out vec4 fragColor;
                void main() {
                        vec2 cxy = 2.0 * gl_PointCoord - 1.0;
                        float r = dot(cxy, cxy);
                        float delta = fwidth(r);
                        float alpha = 1.0 - smoothstep(1.0 - delta, 1.0 + delta, r);
                        fragColor = finalColor * alpha;
                }
            '''

            self.shader = gpu.types.GPUShader(vertex_shader, fragment_shader)

            self.batch = batch_for_shader(
                self.shader, 'POINTS',
                {"pos": vertices, "color": vertices_colors},
                indices=None
            )
        elif shadername == 'CUSTOM_2D':
            vertex_shader = '''
                uniform mat4 ModelViewProjectionMatrix;

                in vec2 pos;
                in vec4 color;

                flat out vec4 finalColor;

                void main()
                {
                    gl_Position = ModelViewProjectionMatrix * vec4(pos, 0.0, 1.0);
                    finalColor = color;
                }
            '''
            fragment_shader = '''
                flat in vec4 finalColor;
                out vec4 fragColor;
                void main() {
                        vec2 cxy = 2.0 * gl_PointCoord - 1.0;
                        float r = dot(cxy, cxy);
                        float delta = fwidth(r);
                        float alpha = 1.0 - smoothstep(1.0 - delta, 1.0 + delta, r);
                        fragColor = finalColor * alpha;
                }
            '''
            self.shader = gpu.types.GPUShader(vertex_shader, fragment_shader)

            self.batch = batch_for_shader(
                self.shader, 'POINTS',
                {"pos": vertices, "color": vertices_colors},
                indices=None
            )
        else:
            self.shader = gpu.shader.from_builtin(shadername)
            self.batch = batch_for_shader(
                self.shader, 'POINTS',
                {"pos": vertices, "color": vertices_colors}
            )

    def create_batch(self):
        self._create_batch(self.vertices, self.vertices_colors)

    def register_handler(self, args):
        self.draw_handler = bpy.types.SpaceView3D.draw_handler_add(
            self.draw_callback, args, "WINDOW", "POST_VIEW")
        # Add to handler list
        self.add_handler_list(self.draw_handler)

    def unregister_handler(self):
        if self.draw_handler is not None:
            bpy.types.SpaceView3D.draw_handler_remove(
                self.draw_handler, "WINDOW")
            # Remove from handler list
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

    def draw_callback(self, op, context):
        # Force Stop
        if self.is_handler_list_empty():
            self.unregister_handler()
            return

        if self.shader is not None:
            bgl.glPointSize(self.point_size)
            bgl.glEnable(bgl.GL_BLEND)
            self.shader.bind()
            self.batch.draw(self.shader)
            bgl.glDisable(bgl.GL_BLEND)


class FBPoints2D(FBShaderPoints):
    """ 2D Shader for 2D-points drawing """
    def create_batch(self):
        self._create_batch(
            # 2D_FLAT_COLOR
            self.vertices, self.vertices_colors, 'CUSTOM_2D')

    def register_handler(self, args):
        self.draw_handler = bpy.types.SpaceView3D.draw_handler_add(
            self.draw_callback, args, "WINDOW", "POST_PIXEL")
        # Add to handler list
        self.add_handler_list(self.draw_handler)


class FBPoints3D(FBShaderPoints):
    """ 3D Shader wrapper for 3d-points draw """
    def create_batch(self):
        # 3D_FLAT_COLOR
        self._create_batch(self.vertices, self.vertices_colors, 'CUSTOM_3D')

    def __init__(self):
        super().__init__()
        self.set_point_size(
            config.default_pin_size * config.surf_pin_size_scale)


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
        self.init_shaders()

    def is_working(self):
        return not (self.draw_handler is None)

    def init_color_data(self, color=(0.5, 0.0, 0.7, 0.2)):
        col = (color[0], color[1], color[2], color[3])
        self.edges_colors = np.full(
            (len(self.edges_vertices), 4), col).tolist()

    def init_special_areas(self, mesh, pairs, color=(0.5, 0.0, 0.7, 0.2)):
        col = (color[0], color[1], color[2], color[3])
        for i, edge in enumerate(mesh.edges):
            vv = edge.vertices
            if ((vv[0], vv[1]) in pairs) or ((vv[1], vv[0]) in pairs):
                self.edges_colors[i * 2] = col
                self.edges_colors[i * 2 + 1] = col

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
        vertex_shader = '''
            uniform mat4 ModelViewProjectionMatrix;
            in vec2 pos;
            in float lineLength;
            out float v_LineLength;
            
            in vec4 color;
            flat out vec4 finalColor;
            
            void main()
            {
                v_LineLength = lineLength;
                gl_Position = ModelViewProjectionMatrix * vec4(pos, 0.0, 1.0f);
                finalColor = color;
            }
        '''

        fragment_shader = '''
            in float v_LineLength;            
            flat in vec4 finalColor;
            out vec4 fragColor;

            void main()
            {
                if (step(sin(v_LineLength), -0.3f) == 1) discard;
                fragColor = finalColor;
            }
        '''

        self.line_shader = gpu.types.GPUShader(
             vertex_shader, fragment_shader)
        # TEST purpose
        # self.line_shader = gpu.shader.from_builtin('2D_UNIFORM_COLOR')
        print("SHADER 2D INIT")

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

        # bgl.glLineStipple(1, 0x00FF)
        # bgl.glEnable(GL_LINE_STIPPLE)

        # bgl.glLineWidth(2.0)
        self.line_shader.bind()
        # self.line_shader.uniform_float("color", config.residual_color)
        self.line_batch.draw(self.line_shader)
        # print("DRAW RESIDUALS")

    def create_batch(self):
        # Our shader batch
        self.line_batch = batch_for_shader(
            self.line_shader, 'LINES',
            # {"pos": self.vertices}
            {"pos": self.vertices, "color": self.vertices_colors,
             "lineLength": self.edge_lengths}
        )

    def register_handler(self, args):
        if self.draw_handler is not None:
            self.unregister_handler()
        self.draw_handler = bpy.types.SpaceView3D.draw_handler_add(
            self.draw_callback, args, "WINDOW", "POST_PIXEL")
        self.add_handler_list(self.draw_handler)

class FBEdgeShader3D(FBEdgeShaderBase):
    """ Wireframe drawing class """
    def draw_callback(self, op, context):
        # Force Stop
        if self.is_handler_list_empty():
            self.unregister_handler()
            return
        # bgl.glEnable(bgl.GL_BLEND)
        # batch.draw(shader)
        # batch2.draw(shader2)
        # bgl.glDisable(bgl.GL_BLEND)

        # bgl.glPushAttrib(bgl.GL_ALL_ATTRIB_BITS)

        bgl.glEnable(bgl.GL_BLEND)
        bgl.glEnable(bgl.GL_LINE_SMOOTH)
        bgl.glHint(bgl.GL_LINE_SMOOTH_HINT, bgl.GL_NICEST)
        bgl.glBlendFunc(bgl.GL_SRC_ALPHA, bgl.GL_ONE_MINUS_SRC_ALPHA)
        # bgl.glLineWidth(2.0)

        # bgl.glEnable(bgl.GL_MULTISAMPLE)

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

        self.line_batch.draw(self.line_shader)

        bgl.glPolygonMode(bgl.GL_FRONT_AND_BACK, bgl.GL_FILL)
        bgl.glDepthMask(bgl.GL_TRUE)
        bgl.glDisable(bgl.GL_DEPTH_TEST)
        # bgl.glPopAttrib()

    def create_batches(self):
        self.fill_batch = batch_for_shader(
                    self.fill_shader, 'TRIS',
                    {"pos": self.vertices},
                    indices=self.indices,
                )

        # Our shader batch
        self.line_batch = batch_for_shader(
            self.line_shader, 'LINES',
            {"pos": self.edges_vertices, "color": self.edges_colors},
            indices=self.edges_indices)

    def init_shaders(self):
        fill_vertex_shader = '''
            uniform mat4 ModelViewProjectionMatrix;
            #ifdef USE_WORLD_CLIP_PLANES
            uniform mat4 ModelMatrix;
            #endif

            in vec3 pos;

            void main()
            {
                gl_Position = ModelViewProjectionMatrix * vec4(pos, 1.0);

            #ifdef USE_WORLD_CLIP_PLANES
                world_clip_planes_calc_clip_distance((ModelMatrix * vec4(pos, 1.0)).xyz);
            #endif
            }
            '''
        fill_fragment_shader = '''
            out vec4 fragColor;
            void main()
            {
                fragColor = vec4(0.0, 0.0, 0.0, 1.0);
            }
            '''

        self.fill_shader = gpu.types.GPUShader(
            fill_vertex_shader, fill_fragment_shader)  # ORIGINAL
        # TEST purpose
        # self.fill_shader = gpu.shader.from_builtin('3D_SMOOTH_COLOR')
        self.line_shader = gpu.shader.from_builtin('3D_SMOOTH_COLOR')

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
        # Transformed vertices
        verts = vv[:, :3]

        self.vertices = verts
        self.indices = indices

        edges = np.empty((len(mesh.edges), 2), 'i')
        mesh.edges.foreach_get(
            "vertices", np.reshape(edges, len(mesh.edges) * 2))

        self.edges_vertices = self.vertices[edges.ravel()]
        # self.init_edge_indices(obj)

    # Separated to
    def init_edge_indices(self, obj):
        self.edges_indices = np.arange(len(self.edges_vertices) * 2).reshape(
            len(self.edges_vertices), 2).tolist()
