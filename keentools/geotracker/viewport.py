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

import numpy as np
import bpy

from ..geotracker_config import GTConfig, get_gt_settings
from ..utils import coords
from ..utils.viewport import KTViewport
from ..utils.screen_text import KTScreenText
from ..utils.points import KTPoints2D, KTPoints3D
from ..utils.edges import KTEdgeShader2D, KTEdgeShaderLocal3D, KTEdgeShaderAll2D, KTScreenRectangleShader2D


class GTViewport(KTViewport):
    def __init__(self):
        super().__init__()
        self._points2d = KTPoints2D(bpy.types.SpaceView3D)
        self._points3d = KTPoints3D(bpy.types.SpaceView3D)
        self._residuals = KTEdgeShader2D(bpy.types.SpaceView3D)
        self._texter = KTScreenText(bpy.types.SpaceView3D)
        self._wireframer = KTEdgeShaderLocal3D(bpy.types.SpaceView3D)
        self._timeliner = KTEdgeShaderAll2D(bpy.types.SpaceDopeSheetEditor,
                                            GTConfig.timeline_keyframe_color)
        self._selector = KTScreenRectangleShader2D(bpy.types.SpaceView3D)
        self._draw_update_timer_handler = None

    def register_handlers(self, context):
        self.unregister_handlers()
        self.set_work_area(context.area)
        self.residuals().register_handler(context)
        self.points3d().register_handler(context)
        self.points2d().register_handler(context)
        self.texter().register_handler(context)
        self.wireframer().register_handler(context)
        self.timeliner().register_handler(context)
        self.selector().register_handler(context)
        self.register_draw_update_timer(time_step=GTConfig.viewport_redraw_interval)

    def unregister_handlers(self):
        self.unregister_draw_update_timer()
        self.selector().unregister_handler()
        self.timeliner().unregister_handler()
        self.wireframer().unregister_handler()
        self.texter().unregister_handler()
        self.points2d().unregister_handler()
        self.points3d().unregister_handler()
        self.residuals().unregister_handler()
        self.clear_work_area()

    def update_surface_points(
            self, gt, obj, keyframe, color=GTConfig.surface_point_color):
        verts = self.surface_points_from_mesh(gt, obj, keyframe)
        colors = [color] * len(verts)

        if len(verts) > 0:
            m = np.array(obj.matrix_world, dtype=np.float32).transpose()
            verts = coords.multiply_verts_on_matrix_4x4(verts, m)

        self.points3d().set_vertices_colors(verts, colors)
        self.points3d().create_batch()

    def update_pin_sensitivity(self):
        settings = get_gt_settings()
        self.POINT_SENSITIVITY = settings.pin_sensitivity

    def update_pin_size(self):
        settings = get_gt_settings()
        self.points2d().set_point_size(settings.pin_size)
        self.points3d().set_point_size(
            settings.pin_size * GTConfig.surf_pin_size_scale)

    def surface_points_from_mesh(self, gt, headobj, keyframe):
        verts = []
        pins_count = gt.pins_count()
        obj = coords.evaluated_mesh(headobj)
        if len(obj.data.vertices) == 0:
            return verts
        for i in range(pins_count):
            pin = gt.pin(keyframe, i)
            if pin is not None:
                p = coords.pin_to_xyz_from_mesh(pin, obj)
                verts.append(p)
        return verts

    def img_points(self, gt, keyframe):
        scene = bpy.context.scene
        w = scene.render.resolution_x
        h = scene.render.resolution_y

        pins_count = gt.pins_count()

        verts = []
        for i in range(pins_count):
            pin = gt.pin(keyframe, i)
            if pin is not None:
                x, y = pin.img_pos
                verts.append((coords.frame_to_image_space(x, y, w, h)))
        return verts

    def create_batch_2d(self, area):
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

        scene = bpy.context.scene
        rx = scene.render.resolution_x
        ry = scene.render.resolution_y
        asp = ry / rx

        x1, y1, x2, y2 = coords.get_camera_border(area)

        for i, p in enumerate(points):
            x, y = coords.image_space_to_region(p[0], p[1], x1, y1, x2, y2)
            points[i] = (x, y)

        vertex_colors = [GTConfig.pin_color for _ in range(len(points))]

        pins = self.pins()
        if pins.current_pin() and pins.current_pin_num() < len(vertex_colors):
            vertex_colors[pins.current_pin_num()] = GTConfig.current_pin_color

        if GTConfig.show_markers_at_camera_corners:
            _add_markers_at_camera_corners(points, vertex_colors)

        self.points2d().set_vertices_colors(points, vertex_colors)
        self.points2d().create_batch()

    def update_residuals(self, gt, area, keyframe):
        scene = bpy.context.scene
        rx = scene.render.resolution_x
        ry = scene.render.resolution_y

        x1, y1, x2, y2 = coords.get_camera_border(area)

        p2d = self.img_points(gt, keyframe)
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
        projection = gt.projection_mat(keyframe).T

        camobj = bpy.context.scene.camera
        if not camobj:
            return

        m = camobj.matrix_world.inverted()
        # Object transform, inverse camera, projection apply -> numpy
        transform = np.array(m.transposed()) @ projection

        # Calc projection
        vv = coords.to_homogeneous(p3d) @ transform
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
                                       GTConfig.residual_color).tolist()
        wire.create_batch()

    def update_wireframe_colors(self):
        settings = get_gt_settings()
        self.wireframer().init_color_data((*settings.wireframe_color,
                                          settings.wireframe_opacity))
        self.wireframer().create_batches()
