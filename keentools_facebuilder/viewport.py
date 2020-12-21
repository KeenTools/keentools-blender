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
import cProfile
import logging
import bpy

import numpy as np

from . config import Config, get_main_settings
from . utils import coords
from . utils.edges import FBEdgeShader2D, FBRasterEdgeShader3D
from . utils.other import FBText
from . utils.points import FBPoints2D, FBPoints3D


class FBScreenPins:
    _pins = []
    _current_pin = None
    _current_pin_num = -1

    @classmethod
    def arr(cls):
        return cls._pins

    @classmethod
    def set_pins(cls, arr):
        cls._pins = arr

    @classmethod
    def add_pin(cls, vec2d):
        cls._pins.append(vec2d)

    @classmethod
    def current_pin_num(cls):
        return cls._current_pin_num

    @classmethod
    def set_current_pin_num(cls, value):
        cls._current_pin_num = value

    @classmethod
    def set_current_pin_num_to_last(cls):
        cls._current_pin_num = len(cls.arr()) - 1

    @classmethod
    def current_pin(cls):
        return cls._current_pin

    @classmethod
    def set_current_pin(cls, value):
        cls._current_pin = value

    @classmethod
    def reset_current_pin(cls):
        cls._current_pin = None
        cls._current_pin_num = -1


class FBViewport:
    profiling = False
    # --- PROFILING ---
    if profiling:
        pr = cProfile.Profile()
        pr.disable()
    # --- PROFILING ---

    # Current View Pins draw
    _points2d = FBPoints2D()
    # Surface points draw
    _points3d = FBPoints3D()
    # Text output in Modal mode
    _texter = FBText()
    # Wireframe shader object
    _wireframer = FBRasterEdgeShader3D()
    # Update timer
    _draw_timer_handler = None

    _residuals = FBEdgeShader2D()

    # Pins
    _pins = FBScreenPins()

    @classmethod
    def pins(cls):
        return cls._pins

    POINT_SENSITIVITY = Config.default_point_sensitivity
    PIXEL_SIZE = 0.1  # Auto Calculated

    @classmethod
    def points2d(cls):
        return cls._points2d

    @classmethod
    def points3d(cls):
        return cls._points3d

    @classmethod
    def texter(cls):
        return cls._texter

    @classmethod
    def wireframer(cls):
        return cls._wireframer

    @classmethod
    def residuals(cls):
        return cls._residuals

    @classmethod
    def update_view_relative_pixel_size(cls, context):
        ps = coords.get_pixel_relative_size(context)
        cls.PIXEL_SIZE = ps

    @classmethod
    def tolerance_dist(cls):  # distance * sensitivity
        return cls.POINT_SENSITIVITY * cls.PIXEL_SIZE

    @classmethod
    def tolerance_dist2(cls):  # squared distance
        return (cls.POINT_SENSITIVITY * cls.PIXEL_SIZE)**2

    @classmethod
    def in_pin_drag(cls):
        pins = cls.pins()
        return pins.current_pin_num() >= 0

    # --------
    # Handlers
    @classmethod
    def register_handlers(cls, args, context):
        cls.unregister_handlers()  # Experimental

        cls.residuals().register_handler(args)

        cls.points3d().register_handler(args)
        cls.points2d().register_handler(args)
        # Draw text on screen registration
        cls.texter().register_handler(args)
        cls.wireframer().register_handler(args)
        # Timer for continuous update modal view
        cls._draw_timer_handler = context.window_manager.event_timer_add(
            time_step=Config.viewport_redraw_interval, window=context.window
        )

    @classmethod
    def unregister_handlers(cls):
        if cls._draw_timer_handler is not None:
            bpy.context.window_manager.event_timer_remove(
                cls._draw_timer_handler
            )
        cls._draw_timer_handler = None
        cls.wireframer().unregister_handler()
        cls.texter().unregister_handler()
        cls.points2d().unregister_handler()
        cls.points3d().unregister_handler()

        cls.residuals().unregister_handler()
    # --------

    # --------------------
    # Update functions
    # --------------------
    @classmethod
    def update_surface_points(
            cls, fb, headobj, keyframe=-1,
            allcolor=(0, 0, 1, 0.15), selcolor=Config.surface_point_color):
        # Load 3D pins
        verts, colors = cls.surface_points(
            fb, headobj, keyframe, allcolor, selcolor)

        if len(verts) > 0:
            # Object matrix usage
            m = np.array(headobj.matrix_world, dtype=np.float32).transpose()
            vv = np.ones((len(verts), 4), dtype=np.float32)
            vv[:, :-1] = verts
            vv = vv @ m
            # Transformed vertices
            verts = vv[:, :3]

        cls.points3d().set_vertices_colors(verts, colors)
        cls.points3d().create_batch()

    @classmethod
    def update_wireframe(cls):
        settings = get_main_settings()
        cls.wireframer().init_colors((settings.wireframe_color,
                                      settings.wireframe_special_color,
                                      settings.wireframe_midline_color),
                                     settings.wireframe_opacity)
        cls.wireframer().create_batches()

    @classmethod
    def update_pin_sensitivity(cls):
        settings = get_main_settings()
        cls.POINT_SENSITIVITY = settings.pin_sensitivity

    @classmethod
    def update_pin_size(cls):
        settings = get_main_settings()
        cls.points2d().set_point_size(settings.pin_size)
        cls.points3d().set_point_size(
            settings.pin_size * Config.surf_pin_size_scale)

    @classmethod
    def surface_points(cls, fb, headobj, keyframe=-1,
                       allcolor=(0, 0, 1, 0.15), selcolor=(0, 1, 0, 1)):
        verts = []
        colors = []

        for k in fb.keyframes():
            for i in range(fb.pins_count(k)):
                pin = fb.pin(k, i)
                p = coords.pin_to_xyz(pin, headobj)
                verts.append(p)
                if k == keyframe:
                    colors.append(selcolor)
                else:
                    colors.append(allcolor)
        return verts, colors

    @classmethod
    def surface_points_only(cls, fb, headobj, keyframe=-1):
        verts = []

        for i in range(fb.pins_count(keyframe)):
            pin = fb.pin(keyframe, i)
            p = coords.pin_to_xyz(pin, headobj)
            verts.append(p)
        return verts

    @classmethod
    def img_points(cls, fb, keyframe):
        scene = bpy.context.scene
        w = scene.render.resolution_x
        h = scene.render.resolution_y

        pins_count = fb.pins_count(keyframe)

        verts = []
        for i in range(pins_count):
            pin = fb.pin(keyframe, i)
            x, y = pin.img_pos
            verts.append((coords.frame_to_image_space(x, y, w, h)))
        return verts

    @classmethod
    def create_batch_2d(cls, context):
        """ Main Pin Draw Batch"""
        points = cls.pins().arr().copy()

        scene = context.scene
        rx = scene.render.resolution_x
        ry = scene.render.resolution_y
        asp = ry / rx

        x1, y1, x2, y2 = coords.get_camera_border(context)

        for i, p in enumerate(points):
            x, y = coords.image_space_to_region(p[0], p[1], x1, y1, x2, y2)
            points[i] = (x, y)

        vertex_colors = [Config.pin_color for _ in range(len(points))]

        pins = cls.pins()
        if pins.current_pin() and pins.current_pin_num() < len(vertex_colors):
            vertex_colors[pins.current_pin_num()] = Config.current_pin_color

        # Camera corners
        points.append(
            (coords.image_space_to_region(
                -0.5, -asp * 0.5, x1, y1, x2, y2))
        )
        points.append(
            (coords.image_space_to_region(
                0.5, asp * 0.5,
                x1, y1, x2, y2))
        )
        vertex_colors.append((1.0, 0.0, 1.0, 0.2))  # left camera corner
        vertex_colors.append((1.0, 0, 1.0, 0.2))  # right camera corner

        cls.points2d().set_vertices_colors(points, vertex_colors)
        cls.points2d().create_batch()

    @classmethod
    def update_residuals(cls, fb, context, headobj, keyframe):
        scene = bpy.context.scene
        rx = scene.render.resolution_x
        ry = scene.render.resolution_y

        x1, y1, x2, y2 = coords.get_camera_border(context)

        p2d = cls.img_points(fb, keyframe)
        p3d = cls.surface_points_only(fb, headobj, keyframe)

        wire = cls.residuals()
        wire.clear_vertices()
        wire.edge_lengths = []
        wire.vertices_colors = []

        # Pins count != Surf points count
        if len(p2d) != len(p3d):
            return

        if len(p3d) == 0:
            # Empty shader
            wire.create_batch()
            return

        # ----------
        # Projection
        projection = fb.projection_mat(keyframe).T

        camobj = bpy.context.scene.camera
        m = camobj.matrix_world.inverted()

        # Fill matrix in homogeneous coords
        vv = np.ones((len(p3d), 4), dtype=np.float32)
        vv[:, :-1] = p3d

        # Object transform, inverse camera, projection apply -> numpy
        transform = np.array(
            headobj.matrix_world.transposed() @ m.transposed()) @ projection
        # Calc projection
        vv = vv @ transform
        vv = (vv.T / vv[:, 3]).T

        verts2 = []
        for i, v in enumerate(vv):
            x, y = coords.frame_to_image_space(v[0], v[1], rx, ry)
            verts2.append(coords.image_space_to_region(x, y,
                                                       x1, y1, x2, y2))
            wire.edge_lengths.append(0)
            verts2.append(coords.image_space_to_region(p2d[i][0], p2d[i][1],
                                                       x1, y1, x2, y2))
            # length = np.linalg.norm((v[0]-p2d[i][0], v[1]-p2d[i][1]))
            length = 22.0
            wire.edge_lengths.append(length)

        wire.vertices = verts2
        wire.vertices_colors = np.full((len(verts2), 4),
                                       Config.residual_color).tolist()
        wire.create_batch()
