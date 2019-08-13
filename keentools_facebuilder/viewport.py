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
import time
import logging
import bpy

import numpy as np

from . import const
from . config import Config, get_main_settings, BuilderType
from . utils import coords
from . utils.edges import FBEdgeShader3D, FBEdgeShader2D
from . utils.other import FBText
from . utils.points import FBPoints2D, FBPoints3D


class FPSMeter:
    def __init__(self, buf_length=5):
        self.start_time = time.time()
        self.indicator = "None"
        self.counter = 0
        self.buffer = [self.start_time for _ in range(buf_length)]
        self.head = 0
        self.buf_length = len(self.buffer)

    def prev_index(self, ind):
        prev_ind = ind - 1
        if prev_ind < 0:
            prev_ind = self.buf_length
        return prev_ind

    def next_index(self, ind):
        next_ind = ind + 1
        if next_ind >= self.buf_length:
            next_ind = 0
        return next_ind

    def update_indicator(self):
        new_time = self.buffer[self.head]
        old_time = self.buffer[self.next_index(self.head)]
        delta = new_time - old_time
        d = 0.0
        if delta > 0.00001:
            d = (self.buf_length - 1) / delta
        self.indicator = "{0:.2f}".format(d)

    def tick(self):
        self.head = self.next_index(self.head)
        self.buffer[self.head] = time.time()
        self.counter += 1


class FBViewport:
    profiling = False
    # --- PROFILING ---
    if profiling:
        pr = cProfile.Profile()
        pr.disable()

    fps = FPSMeter()
    # --- PROFILING ---

    # Current View Pins draw
    points2d = FBPoints2D()
    # Surface points draw
    points3d = FBPoints3D()
    # Text output in Modal mode
    texter = FBText()
    # Wireframe shader object
    wireframer = FBEdgeShader3D()
    # Update timer
    draw_timer_handler = None

    residuals = FBEdgeShader2D()

    # Pins
    spins = []  # current screen pins
    current_pin = None
    current_pin_num = -1

    last_context = None

    POINT_SENSITIVITY = Config.default_POINT_SENSITIVITY
    PIXEL_SIZE = 0.1  # Auto Calculated

    @classmethod
    def update_pixel_size(cls, context):
        ps = coords.get_pixel_relative_size(context)
        cls.PIXEL_SIZE = ps

    @classmethod
    def tolerance_dist(cls):  # distance * sensitivity
        return cls.POINT_SENSITIVITY * cls.PIXEL_SIZE

    @classmethod
    def tolerance_dist2(cls):  # squared distance
        return (cls.POINT_SENSITIVITY * cls.PIXEL_SIZE)**2

    # --------
    # Handlers
    @classmethod
    def register_handlers(cls, args, context):
        cls.unregister_handlers()  # Experimental

        cls.residuals.register_handler(args)

        cls.points3d.register_handler(args)
        cls.points2d.register_handler(args)
        # Draw text on screen registration
        cls.texter.register_handler(args)
        cls.wireframer.register_handler(args)
        # Timer for continuous update modal view
        cls.draw_timer_handler = context.window_manager.event_timer_add(
            time_step=0.2, window=context.window
        )

    @classmethod
    def unregister_handlers(cls):
        if cls.draw_timer_handler is not None:
            bpy.context.window_manager.event_timer_remove(
                cls.draw_timer_handler
            )
        cls.draw_timer_handler = None
        cls.wireframer.unregister_handler()
        cls.texter.unregister_handler()
        cls.points2d.unregister_handler()
        cls.points3d.unregister_handler()

        cls.residuals.unregister_handler()
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

        cls.points3d.set_vertices_colors(verts, colors)
        cls.points3d.create_batch()

    @classmethod
    def update_wireframe(cls, builder_type, obj):
        logger = logging.getLogger(__name__)
        settings = get_main_settings()
        main_color = settings.wireframe_color
        comp_color = settings.wireframe_special_color

        cls.wireframer.init_color_data((*main_color,
                                        settings.wireframe_opacity))
        if settings.show_specials:
            mesh = obj.data
            # Check to prevent shader problem
            if len(mesh.edges) * 2 == len(cls.wireframer.edges_colors):
                logger.info("COLORING")
                special_indices = cls.get_special_indices(builder_type)
                cls.wireframer.init_special_areas(
                    obj.data, special_indices, (*comp_color,
                                                settings.wireframe_opacity))
            else:
                logging.warning("LISTS HAVE DIFFERENT SIZES")
        cls.wireframer.create_batches()

    @classmethod
    def get_special_indices(cls, builder_type):
        if builder_type == BuilderType.FaceBuilder:
            pairs = const.get_eyes_indices()
            pairs = pairs.union(const.get_eyebrows_indices())
            pairs = pairs.union(const.get_nose_indices())
            pairs = pairs.union(const.get_mouth_indices())
            pairs = pairs.union(const.get_ears_indices())
            pairs = pairs.union(const.get_half_indices())
            pairs = pairs.union(const.get_jaw_indices2())
            return pairs
        elif builder_type == BuilderType.BodyBuilder:
            return const.get_bodybuilder_highlight_indices()
        return {}

    @classmethod
    def update_pin_sensitivity(cls):
        settings = get_main_settings()
        cls.POINT_SENSITIVITY = settings.pin_sensitivity

    @classmethod
    def update_pin_size(cls):
        settings = get_main_settings()
        cls.points2d.set_point_size(settings.pin_size)
        cls.points3d.set_point_size(
            settings.pin_size * Config.surf_pin_size_scale)

    @classmethod
    def get_spins(cls):
        return cls.spins

    @classmethod
    def set_spins(cls, arr):
        cls.spins = arr

    @classmethod
    def surface_points(
            cls, fb, headobj, keyframe=-1,
            allcolor=(0, 0, 1, 0.15), selcolor=(0, 1, 0, 1)):
        """ Load 3D pin points """
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
    def surface_points_only(
            cls, fb, headobj, keyframe=-1):
        """ Load 3D pin points """
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
        points = cls.spins.copy()

        scene = context.scene
        rx = scene.render.resolution_x
        ry = scene.render.resolution_y
        asp = ry / rx

        x1, y1, x2, y2 = coords.get_camera_border(context)

        for i, p in enumerate(points):
            x, y = coords.image_space_to_region(p[0], p[1], x1, y1, x2, y2)
            points[i] = (x, y)

        vertex_colors = [Config.pin_color for _ in range(len(points))]

        if cls.current_pin and cls.current_pin_num < len(vertex_colors):
            vertex_colors[cls.current_pin_num] = Config.current_pin_color

        # Sensitivity indicator
        points.append(
            (coords.image_space_to_region(
                -0.5 - cls.PIXEL_SIZE * cls.POINT_SENSITIVITY, -asp * 0.5,
                x1, y1, x2, y2))
        )
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
        vertex_colors.append((0, 1, 0, 0.2))  # sensitivity indicator
        vertex_colors.append(Config.current_pin_color)  # camera corner
        vertex_colors.append(Config.current_pin_color)  # camera corner

        cls.points2d.set_vertices_colors(points, vertex_colors)
        cls.points2d.create_batch()

    @classmethod
    def update_residuals(cls, fb, context, headobj, keyframe):
        scene = bpy.context.scene
        rx = scene.render.resolution_x
        ry = scene.render.resolution_y

        x1, y1, x2, y2 = coords.get_camera_border(context)

        p2d = cls.img_points(fb, keyframe)
        p3d = cls.surface_points_only(fb, headobj, keyframe)

        wire = cls.residuals
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
        projection = fb.projection_mat().T

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
