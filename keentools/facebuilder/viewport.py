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
import bpy

import numpy as np

from ..facebuilder.config import FBConfig, get_fb_settings
from ..preferences.user_preferences import UserPreferences
from ..utils import coords
from ..utils.edges import FBEdgeShader2D, FBRasterEdgeShader3D, FBRectangleShader2D
from ..utils.screen_text import KTScreenText
from ..utils.points import KTScreenPins, KTPoints2D, KTPoints3D


class FBViewport:
    def __init__(self):
        self.profiling = False
        # --- PROFILING ---
        if self.profiling:
            pr = cProfile.Profile()
            pr.disable()
        # --- PROFILING ---
        # Current View Pins draw
        self._points2d = KTPoints2D(bpy.types.SpaceView3D)
        # Rectangles for Face picking
        self._rectangler = FBRectangleShader2D(bpy.types.SpaceView3D)
        # Surface points draw
        self._points3d = KTPoints3D(bpy.types.SpaceView3D)
        # Text output in Modal mode
        self._texter = KTScreenText(bpy.types.SpaceView3D)
        # Wireframe shader object
        self._wireframer = FBRasterEdgeShader3D(bpy.types.SpaceView3D)
        # Update timer
        self._draw_timer_handler = None

        self._residuals = FBEdgeShader2D(bpy.types.SpaceView3D)

        # Pins
        self._pins = KTScreenPins()
        self._point_sensitivity = UserPreferences.get_value_safe(
            'pin_sensitivity', UserPreferences.type_float)
        self._pixel_size = 0.1  # Auto Calculated

    def pins(self):
        return self._pins

    def points2d(self):
        return self._points2d

    def points3d(self):
        return self._points3d

    def texter(self):
        return self._texter

    def wireframer(self):
        return self._wireframer

    def residuals(self):
        return self._residuals

    def rectangler(self):
        return self._rectangler

    def update_view_relative_pixel_size(self, context):
        ps = coords.get_pixel_relative_size(context)
        self._pixel_size = ps

    def tolerance_dist(self):  # distance * sensitivity
        return self._point_sensitivity * self._pixel_size

    def tolerance_dist2(self):  # squared distance
        return (self._point_sensitivity * self._pixel_size)**2

    def in_pin_drag(self):
        pins = self.pins()
        return pins.current_pin_num() >= 0

    # --------
    # Handlers
    def register_handlers(self, context):
        self.unregister_handlers()

        self.residuals().register_handler(context)
        self.rectangler().register_handler(context)

        self.points3d().register_handler(context)
        self.points2d().register_handler(context)
        # Draw text on screen registration
        self.texter().register_handler(context)
        self.wireframer().register_handler(context)
        # Timer for continuous update modal view
        self._draw_timer_handler = context.window_manager.event_timer_add(
            time_step=FBConfig.viewport_redraw_interval, window=context.window
        )

    def unregister_handlers(self):
        if self._draw_timer_handler is not None:
            bpy.context.window_manager.event_timer_remove(
                self._draw_timer_handler
            )
        self._draw_timer_handler = None
        self.wireframer().unregister_handler()
        self.texter().unregister_handler()
        self.points2d().unregister_handler()
        self.points3d().unregister_handler()

        self.rectangler().unregister_handler()
        self.residuals().unregister_handler()
    # --------

    # --------------------
    # Update functions
    # --------------------
    def update_surface_points(
            self, fb, headobj, keyframe=-1, color=FBConfig.surface_point_color):
        verts = self.surface_points_from_fb(fb, keyframe)
        colors = [color] * len(verts)

        if len(verts) > 0:
            m = np.array(headobj.matrix_world, dtype=np.float32).transpose()
            verts = coords.multiply_verts_on_matrix_4x4(verts, m)

        self.points3d().set_vertices_colors(verts, colors)
        self.points3d().create_batch()

    def update_wireframe_colors(self):
        settings = get_fb_settings()
        self.wireframer().init_colors((settings.wireframe_color,
                                      settings.wireframe_special_color,
                                      settings.wireframe_midline_color),
                                      settings.wireframe_opacity)
        self.wireframer().create_batches()

    def update_pin_sensitivity(self):
        settings = get_fb_settings()
        self._point_sensitivity = settings.pin_sensitivity

    def update_pin_size(self):
        settings = get_fb_settings()
        self.points2d().set_point_size(settings.pin_size)
        self.points3d().set_point_size(
            settings.pin_size * FBConfig.surf_pin_size_scale)

    def surface_points_from_mesh(self, fb, headobj, keyframe=-1):
        verts = []
        for i in range(fb.pins_count(keyframe)):
            pin = fb.pin(keyframe, i)
            p = coords.pin_to_xyz_from_mesh(pin, headobj)
            verts.append(p)
        return verts

    def surface_points_from_fb(self, fb, keyframe=-1):
        geo = fb.applied_args_model_at(keyframe)
        geo_mesh = geo.mesh(0)
        pins_count = fb.pins_count(keyframe)
        verts = np.empty((pins_count, 3), dtype=np.float32)
        for i in range(fb.pins_count(keyframe)):
            pin = fb.pin(keyframe, i)
            p = coords.pin_to_xyz_from_fb_geo_mesh(pin, geo_mesh)
            verts[i] = p
        # tolist() is needed by shader batch on Mac
        return (verts @ coords.xy_to_xz_rotation_matrix_3x3()).tolist()

    def img_points(self, fb, keyframe):
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

    def create_batch_2d(self, context):
        def _add_markers_at_camera_corners(points, vertex_colors):
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

        points = self.pins().arr().copy()

        scene = context.scene
        rx = scene.render.resolution_x
        ry = scene.render.resolution_y
        asp = ry / rx

        x1, y1, x2, y2 = coords.get_camera_border(context)

        for i, p in enumerate(points):
            x, y = coords.image_space_to_region(p[0], p[1], x1, y1, x2, y2)
            points[i] = (x, y)

        vertex_colors = [FBConfig.pin_color for _ in range(len(points))]

        pins = self.pins()
        if pins.current_pin() and pins.current_pin_num() < len(vertex_colors):
            vertex_colors[pins.current_pin_num()] = FBConfig.current_pin_color

        if FBConfig.show_markers_at_camera_corners:
            _add_markers_at_camera_corners(points, vertex_colors)

        self.points2d().set_vertices_colors(points, vertex_colors)
        self.points2d().create_batch()

        # Rectangles drawing
        rectangler = self.rectangler()
        rectangler.prepare_shader_data(context)
        rectangler.create_batch()

    def update_residuals(self, fb, headobj, keyframe, context):
        scene = bpy.context.scene
        rx = scene.render.resolution_x
        ry = scene.render.resolution_y

        x1, y1, x2, y2 = coords.get_camera_border(context)

        p2d = self.img_points(fb, keyframe)
        p3d = self.points3d().get_vertices()

        wire = self.residuals()
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
        if not camobj:  # Fix for tests
            return

        vv = coords.to_homogeneous(p3d)
        # No object transform, just inverse camera, then projection apply
        vv = vv @ np.array(camobj.matrix_world.inverted().transposed()) @ projection
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
                                       FBConfig.residual_color).tolist()
        wire.create_batch()
