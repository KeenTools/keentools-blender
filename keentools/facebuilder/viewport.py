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

from ..utils.kt_logging import KTLogger
from ..addon_config import (Config,
                            fb_settings,
                            get_operator,
                            ErrorType,
                            ProductType)
from ..facebuilder_config import FBConfig
from ..utils.bpy_common import bpy_render_frame, bpy_background_mode
from ..utils.coords import (multiply_verts_on_matrix_4x4,
                            pin_to_xyz_from_mesh,
                            pin_to_xyz_from_geo_mesh,
                            xy_to_xz_rotation_matrix_3x3,
                            frame_to_image_space,
                            image_space_to_region,
                            get_camera_border,
                            get_area_region_3d,
                            to_homogeneous)
from ..utils.viewport import KTViewport
from ..utils.edges import KTEdgeShader2D, KTRectangleShader2D
from ..utils.screen_text import KTScreenText
from ..utils.points import KTPoints2D, KTPoints3D
from .utils.edges import FBRasterEdgeShader3D


_log = KTLogger(__name__)


class FBViewport(KTViewport):
    def __init__(self):
        super().__init__()
        self._points2d: Any = KTPoints2D(SpaceView3D)
        self._points3d: Any = KTPoints3D(SpaceView3D)
        self._residuals: Any = KTEdgeShader2D(SpaceView3D)
        self._texter: Any = KTScreenText(SpaceView3D, 'FaceBuilder')
        self._wireframer: Any = FBRasterEdgeShader3D(SpaceView3D)
        self._rectangler: Any = KTRectangleShader2D(SpaceView3D)
        self._draw_update_timer_handler: Optional[Callable] = None

    def product_type(self) -> int:
        return ProductType.FACEBUILDER

    def get_all_shader_objects(self) -> List:
        return [self._texter,
                self._points3d,
                self._residuals,
                self._points2d,
                self._wireframer,
                self._rectangler]

    def viewport_is_working(self) -> bool:
        if not super().viewport_is_working():
            return False
        wireframer = self.wireframer()
        if not wireframer:
            return False
        return wireframer.shader_is_working()

    def register_handlers(self, *, area: Any) -> bool:
        _log.cyan(f'{self.__class__.__name__}.register_handlers start')
        _log.output('call super().register_handler')
        status = super().register_handlers(area=area)
        if status:
            self.register_draw_update_timer(time_step=FBConfig.viewport_redraw_interval)
        else:
            _log.error(f'{self.__class__.__name__}: '
                       f'Could not register viewport handlers')
        _log.cyan(f'{self.__class__.__name__}.register_handlers end >>>')
        return status

    def unregister_handlers(self) -> Area:
        _log.cyan(f'{self.__class__.__name__}.unregister_handlers start')
        self.unregister_draw_update_timer()
        area = super().unregister_handlers()
        _log.cyan(f'{self.__class__.__name__}.unregister_handlers end >>>')
        return area

    def update_surface_points(
            self, fb: Any, headobj: Object, keyframe: int = -1,
            color: Tuple[float, float, float, float] = FBConfig.surface_point_color) -> None:
        verts = self.surface_points_from_fb(fb, keyframe)
        colors = [color] * len(verts)

        if len(verts) > 0:
            m = np.array(headobj.matrix_world, dtype=np.float32).transpose()
            verts = multiply_verts_on_matrix_4x4(verts, m)

        self.points3d().set_vertices_and_colors(verts, colors)
        self.points3d().create_batch()

    def update_wireframe_colors(self) -> None:
        settings = fb_settings()
        wf = self.wireframer()
        wf.init_colors((settings.wireframe_color,
                        settings.wireframe_special_color,
                        settings.wireframe_midline_color),
                       settings.wireframe_opacity)
        wf.set_adaptive_opacity(settings.get_adaptive_opacity())
        wf.set_backface_culling(settings.wireframe_backface_culling)

    def update_pin_sensitivity(self) -> None:
        settings = fb_settings()
        self._point_sensitivity = settings.pin_sensitivity

    def update_pin_size(self) -> None:
        settings = fb_settings()
        self.points2d().set_point_size(settings.pin_size)
        self.points3d().set_point_size(
            settings.pin_size * FBConfig.surf_pin_size_scale)

    def surface_points_from_mesh(self, fb: Any, headobj: Object,
                                 keyframe: int = -1) -> Any:
        pins_count = fb.pins_count(keyframe)
        verts = np.empty((pins_count, 3), dtype=np.float32)
        for i in range(pins_count):
            pin = fb.pin(keyframe, i)
            verts[i] = pin_to_xyz_from_mesh(pin, headobj)
        return verts

    def surface_points_from_fb(self, fb: Any, keyframe: int = -1) -> Any:
        geo = fb.applied_args_model_at(keyframe)
        geo_mesh = geo.mesh(0)
        pins_count = fb.pins_count(keyframe)
        verts = np.empty((pins_count, 3), dtype=np.float32)
        for i in range(fb.pins_count(keyframe)):
            pin = fb.pin(keyframe, i)
            verts[i] = pin_to_xyz_from_geo_mesh(pin, geo_mesh)
        return verts @ xy_to_xz_rotation_matrix_3x3()

    def img_points(self, fb: Any, keyframe: int) -> Any:
        w, h = bpy_render_frame()
        pins_count = fb.pins_count(keyframe)
        verts = np.empty((pins_count, 2), dtype=np.float32)
        for i in range(pins_count):
            pin = fb.pin(keyframe, i)
            x, y = pin.img_pos
            verts[i] = frame_to_image_space(x, y, w, h)
        return verts

    def create_batch_2d(self, area: Area) -> None:
        x1, y1, x2, y2 = get_camera_border(area)

        points = self.pins().arr().copy()
        for i, p in enumerate(points):
            points[i] = image_space_to_region(p[0], p[1], x1, y1, x2, y2)

        vertex_colors = np.full((len(points), 4), FBConfig.pin_color,
                                dtype=np.float32)

        pins = self.pins()
        if pins.current_pin() and pins.current_pin_num() < len(vertex_colors):
            vertex_colors[pins.current_pin_num()] = FBConfig.current_pin_color

        self.points2d().set_vertices_and_colors(points, vertex_colors)
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

        verts_count = len(kt_pins)
        verts = np.empty((verts_count * 2, 2), dtype=np.float32)
        for i, pin in enumerate(kt_pins):
            x, y = frame_to_image_space(*pin.img_pos, rx, ry)
            verts[i * 2] = image_space_to_region(x, y, x1, y1, x2, y2)
            x, y = frame_to_image_space(*pin.surface_point, rx, ry)
            verts[i * 2 + 1] = image_space_to_region(x, y, x1, y1, x2, y2)

        wire = self.residuals()
        wire.vertices = verts
        wire.vertex_colors = np.full((verts_count * 2, 4),
                                     FBConfig.residual_color,
                                     dtype=np.float32)

        # For pin dashes drawing template like this: O- - - -o
        wire.edge_lengths = np.full((verts_count, 2), (0.0, 22.0),
                                    dtype=np.float32).ravel()
        wire.create_batch()

    def unhide_all_shaders(self):
        _log.yellow(f'{self.__class__.__name__}.unhide_all_shaders start')
        self.residuals().unhide_shader()
        self.points3d().unhide_shader()
        self.points2d().unhide_shader()
        self.texter().unhide_shader()
        self.wireframer().unhide_shader()
        self.rectangler().unhide_shader()
        _log.output(f'{self.__class__.__name__}.unhide_all_shaders end >>>')
