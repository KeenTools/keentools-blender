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

from typing import Any, List, Tuple
import numpy as np

from bpy.types import Object, Area, SpaceView3D, SpaceDopeSheetEditor

from ..geotracker_config import GTConfig, get_gt_settings
from ..utils.coords import (get_camera_border,
                            image_space_to_region,
                            frame_to_image_space,
                            multiply_verts_on_matrix_4x4,
                            to_homogeneous,
                            pin_to_xyz_from_mesh)
from ..utils.bpy_common import (bpy_render_frame,
                                evaluated_object,
                                bpy_scene_camera)
from ..utils.viewport import KTViewport
from ..utils.screen_text import KTScreenText
from ..utils.points import KTPoints2D, KTPoints3D
from ..utils.edges import (KTEdgeShader2D,
                           KTLitEdgeShaderLocal3D,
                           KTEdgeShaderAll2D,
                           KTScreenDashedRectangleShader2D)
from ..utils.polygons import KTRasterMask
from ..preferences.user_preferences import UserPreferences


class GTViewport(KTViewport):
    def __init__(self):
        super().__init__()
        self._points2d = KTPoints2D(SpaceView3D)
        self._points3d = KTPoints3D(SpaceView3D)
        self._residuals = KTEdgeShader2D(SpaceView3D)
        self._texter = KTScreenText(SpaceView3D)
        self._wireframer = KTLitEdgeShaderLocal3D(SpaceView3D, mask_color=(
            *UserPreferences.get_value_safe('gt_mask_3d_color',
                                            UserPreferences.type_color),
            UserPreferences.get_value_safe('gt_mask_3d_opacity',
                                           UserPreferences.type_float)))
        self._timeliner = KTEdgeShaderAll2D(SpaceDopeSheetEditor,
                                            GTConfig.timeline_keyframe_color)
        self._selector = KTScreenDashedRectangleShader2D(SpaceView3D)
        self._mask2d = KTRasterMask(SpaceView3D, mask_color=(
            *UserPreferences.get_value_safe('gt_mask_2d_color',
                                            UserPreferences.type_color),
            UserPreferences.get_value_safe('gt_mask_2d_opacity',
                                           UserPreferences.type_float)))
        self._draw_update_timer_handler = None

    def register_handlers(self, context):
        self.unregister_handlers()
        self.set_work_area(context.area)
        self.mask2d().register_handler(context)
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
        self.mask2d().unregister_handler()
        self.clear_work_area()

    def mask2d(self) -> KTRasterMask:
        return self._mask2d

    def update_surface_points(self, gt: Any, obj: Object, keyframe: int,
                              color: Tuple=GTConfig.surface_point_color) -> None:
        verts = self.surface_points_from_mesh(gt, obj, keyframe)
        colors = [color] * len(verts)

        pins = self.pins()
        if pins.move_pin_mode():
            points_count = len(verts)
            hidden_color = (*color[:3], 0.0)
            for i in [x for x in pins.get_disabled_pins() if x < points_count]:
                colors[i] = hidden_color

        if len(verts) > 0:
            m = np.array(obj.matrix_world, dtype=np.float32).transpose()
            verts = multiply_verts_on_matrix_4x4(verts, m)

        self.points3d().set_vertices_colors(verts, colors)
        self.points3d().create_batch()

    def update_pin_sensitivity(self) -> None:
        settings = get_gt_settings()
        self._point_sensitivity = settings.pin_sensitivity

    def update_pin_size(self) -> None:
        settings = get_gt_settings()
        self.points2d().set_point_size(settings.pin_size)
        self.points3d().set_point_size(
            settings.pin_size * GTConfig.surf_pin_size_scale)

    def surface_points_from_mesh(self, gt: Any, geomobj: Object,
                                 keyframe: int) -> List:
        verts = []
        pins_count = gt.pins_count()
        obj = evaluated_object(geomobj)
        if len(obj.data.vertices) == 0:
            return verts
        for i in range(pins_count):
            pin = gt.pin(keyframe, i)
            if pin is not None:
                p = pin_to_xyz_from_mesh(pin, obj)
                if p is not None:
                    verts.append(p)
        return verts

    def create_batch_2d(self, area: Area) -> None:
        def _add_markers_at_camera_corners(points: List,
                                           vertex_colors: List) -> None:
            points.append(
                (image_space_to_region(-0.5, -asp * 0.5, x1, y1, x2, y2))
            )
            points.append(
                (image_space_to_region(0.5, asp * 0.5, x1, y1, x2, y2))
            )
            vertex_colors.append((1.0, 0.0, 1.0, 0.2))  # left camera corner
            vertex_colors.append((1.0, 0.0, 1.0, 0.2))  # right camera corner

        rx, ry = bpy_render_frame()
        asp = ry / rx
        x1, y1, x2, y2 = get_camera_border(area)

        pins = self.pins()
        points = pins.arr().copy()
        for i, p in enumerate(points):
            points[i] = image_space_to_region(p[0], p[1], x1, y1, x2, y2)

        points_count = len(points)

        vertex_colors = [GTConfig.pin_color] * points_count

        color = (*GTConfig.disabled_pin_color[:3], 0.0) \
            if pins.move_pin_mode() else GTConfig.disabled_pin_color
        for i in [x for x in pins.get_disabled_pins() if x < points_count]:
            vertex_colors[i] = color

        for i in [x for x in pins.get_selected_pins() if x < points_count]:
            vertex_colors[i] = GTConfig.selected_pin_color

        pin_num = pins.current_pin_num()
        if pins.current_pin() and pin_num >= 0 and pin_num < points_count:
            vertex_colors[pin_num] = GTConfig.current_pin_color

        if GTConfig.show_markers_at_camera_corners:
            _add_markers_at_camera_corners(points, vertex_colors)

        self.points2d().set_vertices_colors(points, vertex_colors)
        self.points2d().create_batch()

        mask = self.mask2d()
        if mask.image:
            mask.left = image_space_to_region(-0.5, -asp * 0.5, x1, y1, x2, y2)
            w, h = mask.image.size[:]
            mask.right = image_space_to_region(
                *frame_to_image_space(w, h, rx, ry), x1, y1, x2, y2)

    def update_residuals(self, gt: Any, area: Area, keyframe: int) -> None:
        rx, ry = bpy_render_frame()
        x1, y1, x2, y2 = get_camera_border(area)

        p2d = self.points2d().get_vertices()
        if GTConfig.show_markers_at_camera_corners:
            p2d = p2d[:-2]
        p3d = self.points3d().get_vertices()

        wire = self.residuals()
        wire.clear_vertices()
        wire.edge_lengths = []
        wire.vertices_colors = []

        if len(p2d) != len(p3d):
            return

        if len(p3d) == 0:
            wire.create_batch()  # Empty shader
            return

        camobj = bpy_scene_camera()
        if not camobj:
            return

        projection = gt.projection_mat(keyframe).T
        m = camobj.matrix_world.inverted()
        # Object transform, inverse camera, projection apply -> numpy
        transform = np.array(m.transposed()) @ projection

        # Calc projection
        vv = to_homogeneous(p3d) @ transform
        vv = (vv.T / vv[:, 3]).T

        verts = []
        shift_x, shift_y = camobj.data.shift_x, camobj.data.shift_y
        for i, v in enumerate(vv):
            x, y = frame_to_image_space(v[0], v[1], rx, ry, shift_x, shift_y)
            verts.append(image_space_to_region(x, y, x1, y1, x2, y2))
            wire.edge_lengths.append(0)
            verts.append((p2d[i][0], p2d[i][1]))
            # length = np.linalg.norm((v[0]-p2d[i][0], v[1]-p2d[i][1]))
            length = 22.0
            wire.edge_lengths.append(length)

        wire.vertices = verts
        wire.vertices_colors = [GTConfig.residual_color] * len(verts)
        pins = self.pins()
        if pins.move_pin_mode():
            points_count = len(wire.vertices_colors)
            color = (*GTConfig.residual_color[:3], 0.0)
            for i in [x for x in pins.get_disabled_pins() if 2 * x < points_count]:
                wire.vertices_colors[i * 2] = color
                wire.vertices_colors[i * 2 + 1] = color
        wire.create_batch()

    def update_wireframe_colors(self) -> None:
        settings = get_gt_settings()
        wf = self.wireframer()
        wf.init_color_data((*settings.wireframe_color,
                            settings.wireframe_opacity * settings.get_adaptive_opacity()))
        wf.set_lit_wireframe(settings.lit_wireframe)
        wf.create_batches()

    def hide_pins_and_residuals(self):
        self.points2d().hide_shader()
        self.points3d().hide_shader()
        self.residuals().hide_shader()

    def unhide_pins_and_residuals(self):
        self.points2d().unhide_shader()
        self.points3d().unhide_shader()
        self.residuals().unhide_shader()

    def unhide_all_shaders(self):
        self.mask2d().unhide_shader()
        self.residuals().unhide_shader()
        self.points3d().unhide_shader()
        self.points2d().unhide_shader()
        self.texter().unhide_shader()
        self.wireframer().unhide_shader()
        self.timeliner().unhide_shader()
        self.selector().unhide_shader()
