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
import bgl
from gpu_extras.batch import batch_for_shader
from .shaders import (flat_color_3d_vertex_shader,
                      circular_dot_fragment_shader,
                      flat_color_2d_vertex_shader)
from ..config import Config
from ..preferences.user_preferences import UserPreferences


class FBShaderPoints:
    """ Base class for Point Drawing Shaders """
    _is_visible = True
    _point_size = UserPreferences.get_value_safe('pin_size', UserPreferences.type_float)

    # Store all draw handlers registered by class objects
    handler_list = []

    @classmethod
    def is_visible(cls):
        return cls._is_visible

    @classmethod
    def set_visible(cls, flag=True):
        cls._is_visible = flag

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
        self.draw_handler = None  # for 3d shader
        self.shader = None
        self.batch = None

        self.vertices = []
        self.vertices_colors = []

        self._target_class = target_class
        self._work_area = None

    def get_target_class(self):
        return self._target_class

    def set_target_class(self, target_class):
        self._target_class = target_class

    def get_vertices(self):
        return self.vertices

    @classmethod
    def set_point_size(cls, ps):
        cls._point_size = ps

    def _create_batch(self, vertices, vertices_colors,
                      shadername='2D_FLAT_COLOR'):
        if bpy.app.background:
            return
        if shadername == 'CUSTOM_3D':
            # 3D_FLAT_COLOR
            vertex_shader = flat_color_3d_vertex_shader()
            fragment_shader = circular_dot_fragment_shader()

            self.shader = gpu.types.GPUShader(vertex_shader, fragment_shader)

            self.batch = batch_for_shader(
                self.shader, 'POINTS',
                {"pos": vertices, "color": vertices_colors},
                indices=None
            )
        elif shadername == 'CUSTOM_2D':
            vertex_shader = flat_color_2d_vertex_shader()
            fragment_shader = circular_dot_fragment_shader()

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
        self._work_area = args[1].area

        self.draw_handler = self.get_target_class().draw_handler_add(
            self.draw_callback, args, 'WINDOW', 'POST_VIEW')
        # Add to handler list
        self.add_handler_list(self.draw_handler)

    def unregister_handler(self):
        if self.draw_handler is not None:
            self.get_target_class().draw_handler_remove(
                self.draw_handler, "WINDOW")
            # Remove from handler list
            self.remove_handler_list(self.draw_handler)

        self.draw_handler = None

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

    def draw_callback(self, op, context):
        if not self.is_visible():
            return
        # Force Stop
        if self.is_handler_list_empty():
            self.unregister_handler()
            return

        if self._work_area != context.area:
            return

        if self.shader is not None:
            bgl.glPointSize(self._point_size)
            bgl.glEnable(bgl.GL_BLEND)
            self.shader.bind()
            self.batch.draw(self.shader)
            bgl.glDisable(bgl.GL_BLEND)

    def hide_shader(self):
        self.set_visible(False)

    def unhide_shader(self):
        self.set_visible(True)


class FBPoints2D(FBShaderPoints):
    """ 2D Shader for 2D-points drawing """
    def create_batch(self):
        self._create_batch(
            # 2D_FLAT_COLOR
            self.vertices, self.vertices_colors, 'CUSTOM_2D')

    def register_handler(self, args):
        self._work_area = args[1].area

        self.draw_handler = self.get_target_class().draw_handler_add(
            self.draw_callback, args, 'WINDOW', 'POST_PIXEL')
        # Add to handler list
        self.add_handler_list(self.draw_handler)


class FBPoints3D(FBShaderPoints):
    """ 3D Shader wrapper for 3d-points draw """
    def create_batch(self):
        # 3D_FLAT_COLOR
        self._create_batch(self.vertices, self.vertices_colors, 'CUSTOM_3D')

    def __init__(self, target_class):
        super().__init__(target_class)
        self.set_point_size(
            UserPreferences.get_value_safe('pin_size', UserPreferences.type_float) *
            Config.surf_pin_size_scale)
