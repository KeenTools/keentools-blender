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

from typing import Any, Callable, Optional, Tuple, List
import numpy as np

from bpy.types import Object, Area, SpaceView3D

from ..facebuilder_config import FBConfig, get_fb_settings
from ..utils.bpy_common import bpy_render_frame
from ..utils.coords import (multiply_verts_on_matrix_4x4,
                            pin_to_xyz_from_mesh,
                            pin_to_xyz_from_fb_geo_mesh,
                            xy_to_xz_rotation_matrix_3x3,
                            frame_to_image_space,
                            image_space_to_region,
                            get_camera_border,
                            get_area_region_3d,
                            to_homogeneous)
from ..utils.viewport import KTViewport
from ..utils.edges import KTEdgeShader2D
from ..utils.screen_text import KTScreenText
from ..utils.points import KTPoints2D, KTPoints3D
from .utils.edges import FBRasterEdgeShader3D, FBRectangleShader2D


class FBViewport(KTViewport):
    def __init__(self):
        super().__init__()
        self._points2d: Any = KTPoints2D(SpaceView3D)
        self._points3d: Any = KTPoints3D(SpaceView3D)
        self._residuals: Any = KTEdgeShader2D(SpaceView3D)
        self._texter: Any = KTScreenText(SpaceView3D)
        self._wireframer: Any = FBRasterEdgeShader3D(SpaceView3D)
        self._rectangler: Any = FBRectangleShader2D(SpaceView3D)
        self._draw_update_timer_handler: Optional[Callable] = None

    def register_handlers(self, context: Any) -> None:
        self.unregister_handlers()
        self.set_work_area(context.area)
        self.residuals().register_handler(context)
        self.rectangler().register_handler(context)
        self.points3d().register_handler(context)
        self.points2d().register_handler(context)
        self.texter().register_handler(context)
        self.wireframer().register_handler(context)
        self.register_draw_update_timer(time_step=FBConfig.viewport_redraw_interval)

    def unregister_handlers(self) -> None:
        self.unregister_draw_update_timer()
        self.wireframer().unregister_handler()
        self.texter().unregister_handler()
        self.points2d().unregister_handler()
        self.points3d().unregister_handler()
        self.rectangler().unregister_handler()
        self.residuals().unregister_handler()
        self.clear_work_area()

    def update_surface_points(
            self, fb: Any, headobj: Object, keyframe: int=-1,
            color: Tuple[float, float, float, float]=FBConfig.surface_point_color):
        verts = self.surface_points_from_fb(fb, keyframe)
        colors = [color] * len(verts)

        if len(verts) > 0:
            m = np.array(headobj.matrix_world, dtype=np.float32).transpose()
            verts = multiply_verts_on_matrix_4x4(verts, m)

        self.points3d().set_vertices_colors(verts, colors)
        self.points3d().create_batch()

    def update_wireframe_colors(self) -> None:
        settings = get_fb_settings()
        self.wireframer().init_colors((settings.wireframe_color,
                                      settings.wireframe_special_color,
                                      settings.wireframe_midline_color),
                                      settings.wireframe_opacity * settings.get_adaptive_opacity())
        self.wireframer().create_batches()

    def update_pin_sensitivity(self) -> None:
        settings = get_fb_settings()
        self._point_sensitivity = settings.pin_sensitivity

    def update_pin_size(self) -> None:
        settings = get_fb_settings()
        self.points2d().set_point_size(settings.pin_size)
        self.points3d().set_point_size(
            settings.pin_size * FBConfig.surf_pin_size_scale)

    def surface_points_from_mesh(self, fb: Any, headobj: Object,
                                 keyframe: int=-1) -> List[Any]:
        verts = []
        for i in range(fb.pins_count(keyframe)):
            pin = fb.pin(keyframe, i)
            p = pin_to_xyz_from_mesh(pin, headobj)
            verts.append(p)
        return verts

    def surface_points_from_fb(self, fb: Any, keyframe: int=-1) -> List[Tuple]:
        geo = fb.applied_args_model_at(keyframe)
        geo_mesh = geo.mesh(0)
        pins_count = fb.pins_count(keyframe)
        verts = np.empty((pins_count, 3), dtype=np.float32)
        for i in range(fb.pins_count(keyframe)):
            pin = fb.pin(keyframe, i)
            p = pin_to_xyz_from_fb_geo_mesh(pin, geo_mesh)
            verts[i] = p
        # tolist() is needed by shader batch on Mac
        return (verts @ xy_to_xz_rotation_matrix_3x3()).tolist()

    def img_points(self, fb: Any, keyframe: int) -> List[Tuple]:
        w, h = bpy_render_frame()
        pins_count = fb.pins_count(keyframe)
        verts = []
        for i in range(pins_count):
            pin = fb.pin(keyframe, i)
            x, y = pin.img_pos
            verts.append(frame_to_image_space(x, y, w, h))
        return verts

    def create_batch_2d(self, area: Area) -> None:
        def _add_markers_at_camera_corners(points: List[Tuple],
                                           vertex_colors: List[Tuple]) -> None:
            asp = ry / rx
            points.append(
                image_space_to_region(-0.5, -asp * 0.5, x1, y1, x2, y2))
            points.append(
                image_space_to_region(0.5, asp * 0.5, x1, y1, x2, y2))
            vertex_colors.append((1.0, 0.0, 1.0, 0.2))  # left camera corner
            vertex_colors.append((1.0, 0.0, 1.0, 0.2))  # right camera corner

        points = self.pins().arr().copy()

        rx, ry = bpy_render_frame()
        x1, y1, x2, y2 = get_camera_border(area)

        for i, p in enumerate(points):
            points[i] = image_space_to_region(p[0], p[1], x1, y1, x2, y2)

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
        rectangler.prepare_shader_data(area)
        rectangler.create_batch()

    def update_residuals(self, fb: Any, keyframe: int, area: Area) -> None:
        if not area:
            return
        r3d = get_area_region_3d(area)
        if not r3d:
            return

        rx, ry = bpy_render_frame()
        x1, y1, x2, y2 = get_camera_border(area)
        kt_pins = fb.projected_pins(keyframe)

        verts = []
        for pin in kt_pins:
            x, y = frame_to_image_space(*pin.img_pos, rx, ry)
            verts.append(image_space_to_region(x, y, x1, y1, x2, y2))
            x, y = frame_to_image_space(*pin.surface_point, rx, ry)
            verts.append(image_space_to_region(x, y, x1, y1, x2, y2))

        wire = self.residuals()
        wire.vertices = verts
        wire.vertices_colors = [FBConfig.residual_color] * len(wire.vertices)

        # For pin dashes drawing template like this: O- - - -o
        wire.edge_lengths = [0.0, 22.0] * len(kt_pins)
        wire.create_batch()
