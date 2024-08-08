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

from typing import Any, List, Tuple, Optional, Callable
import numpy as np

from bpy.types import Object, Area, SpaceView3D, SpaceDopeSheetEditor

from ..utils.kt_logging import KTLogger
from ..addon_config import (Config,
                            gt_settings,
                            ActionStatus,
                            ProductType)
from ..geotracker_config import GTConfig
from ..utils.coords import (get_camera_border,
                            image_space_to_region,
                            frame_to_image_space,
                            multiply_verts_on_matrix_4x4,
                            to_homogeneous,
                            pin_to_xyz_from_mesh,
                            get_area_region,
                            get_area_region_3d,
                            calc_camera_zoom_and_offset,
                            bound_box_center,
                            camera_projection)
from ..utils.bpy_common import (bpy_render_frame,
                                evaluated_object,
                                bpy_scene_camera,
                                bpy_background_mode,
                                get_scene_camera_shift)
from ..utils.viewport import KTViewport
from ..utils.screen_text import KTScreenText
from ..utils.points import KTPoints2D, KTPoints3D
from ..utils.edges import (KTEdgeShader2D,
                           KTRectangleShader2D,
                           KTLitEdgeShaderLocal3D,
                           KTEdgeShaderAll2D,
                           KTScreenDashedRectangleShader2D)
from ..utils.polygons import KTRasterMask
from ..preferences.user_preferences import UserPreferences
from ..utils.ui_redraw import force_ui_redraw


_log = KTLogger(__name__)


class GTViewport(KTViewport):
    def __init__(self):
        super().__init__()
        self._points2d = KTPoints2D(SpaceView3D)
        self._points3d = KTPoints3D(SpaceView3D)
        self._residuals = KTEdgeShader2D(SpaceView3D)
        self._texter = KTScreenText(SpaceView3D, 'GeoTracker')
        self._wireframer = KTLitEdgeShaderLocal3D(SpaceView3D, mask_color=(
            *UserPreferences.get_value_safe('gt_mask_3d_color',
                                            UserPreferences.type_color),
            UserPreferences.get_value_safe('gt_mask_3d_opacity',
                                           UserPreferences.type_float)))
        self._rectangler: Any = KTRectangleShader2D(SpaceView3D)
        self._timeliner = KTEdgeShaderAll2D(SpaceDopeSheetEditor,
                                            GTConfig.timeline_keyframe_color)
        self._selector = KTScreenDashedRectangleShader2D(SpaceView3D)
        self._mask2d = KTRasterMask(SpaceView3D, mask_color=(
            *UserPreferences.get_value_safe('gt_mask_2d_color',
                                            UserPreferences.type_color),
            UserPreferences.get_value_safe('gt_mask_2d_opacity',
                                           UserPreferences.type_float)))
        self._draw_update_timer_handler: Optional[Callable] = None

        self.stabilization_region_point: Optional[Tuple[float, float]] = None

    def product_type(self) -> int:
        return ProductType.GEOTRACKER

    def get_settings(self) -> Any:
        return gt_settings()

    def clear_stabilization_point(self):
        _log.output(_log.color('yellow', 'clear_stabilization_point'))
        self.stabilization_region_point = None

    def stabilize(self, geomobj: Optional[Object]) -> bool:
        if not geomobj:
            return False

        area = self.get_work_area()
        if not area:
            return False

        shift_x, shift_y = get_scene_camera_shift()
        x1, y1, x2, y2 = get_camera_border(area)

        pins_average_point = self.pins().average_point_of_selected_pins()
        if pins_average_point is None:
            rx, ry = bpy_render_frame()
            camobj = bpy_scene_camera()
            projection = camera_projection(camobj)
            p3d = geomobj.matrix_world @ bound_box_center(geomobj)
            try:
                transform = projection @ camobj.matrix_world.inverted()
                vv = transform @ p3d.to_4d()
                denom = vv[3]
                if denom == 0:
                    return False

                x, y = frame_to_image_space(vv[0] / denom, vv[1] / denom,
                                            rx, ry, shift_x, shift_y)
                point = image_space_to_region(x, y, x1, y1, x2, y2,
                                              shift_x, shift_y)
            except Exception as err:
                _log.error(f'stabilize exception:\n{str(err)}')
                return False
        else:
            point = image_space_to_region(*pins_average_point,
                                          x1, y1, x2, y2, shift_x, shift_y)

        _log.output(_log.color('red', f'point: {point}'))
        if self.stabilization_region_point is None:
            self.stabilization_region_point = point
            _log.output('stabilization_region_point init')
            return True

        sx, sy = self.stabilization_region_point
        _log.output(_log.color('magenta',
                               f'stabilization_region_point: '
                               f'{self.stabilization_region_point}'))
        px, py = point
        _, offset = calc_camera_zoom_and_offset(
            area, x1 + sx - px, y1 + sy - py, width=x2 - x1)

        region_3d = get_area_region_3d(area)
        region_3d.view_camera_offset = offset
        return True

    def get_all_shader_objects(self) -> List:
        return [self._texter,
                self._points3d,
                self._residuals,
                self._points2d,
                self._wireframer,
                self._rectangler,
                self._timeliner,
                self._selector,
                self._mask2d]

    def register_handlers(self, *, area: Any) -> bool:
        _log.cyan(f'{self.__class__.__name__}.register_handlers start')
        status = super().register_handlers(area=area)
        if status:
            self.register_draw_update_timer(time_step=GTConfig.viewport_redraw_interval)
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

    def mask2d(self) -> KTRasterMask:
        return self._mask2d

    def update_surface_points(self, gt: Any, obj: Object, keyframe: int,
                              color: Tuple=GTConfig.surface_point_color) -> None:
        _log.yellow('update_surface_points start')
        if obj:
            verts = self.surface_points_from_mesh(gt, obj, keyframe)
        else:
            verts = np.empty((0, 3), dtype=np.float32)

        verts_count = len(verts)
        colors = np.full((verts_count, 4), color, dtype=np.float32)

        pins = self.pins()
        if pins.move_pin_mode():
            hidden_color = (*color[:3], 0.0)
            for i in [x for x in pins.get_disabled_pins() if x < verts_count]:
                colors[i] = hidden_color

        if len(verts) > 0:
            m = np.array(obj.matrix_world, dtype=np.float32).transpose()
            verts = multiply_verts_on_matrix_4x4(verts, m)

        self.points3d().set_vertices_and_colors(verts, colors)
        self.points3d().create_batch()
        _log.output('update_surface_points end >>>')

    def update_pin_sensitivity(self) -> None:
        settings = self.get_settings()
        self._point_sensitivity = settings.pin_sensitivity

    def update_pin_size(self) -> None:
        settings = self.get_settings()
        self.points2d().set_point_size(settings.pin_size)
        self.points3d().set_point_size(
            settings.pin_size * GTConfig.surf_pin_size_scale)

    def surface_points_from_mesh(self, gt: Any, geomobj: Object,
                                 keyframe: int) -> Any:
        _log.yellow('surface_points_from_mesh start')
        pins_count = gt.pins_count()
        verts = np.zeros((pins_count, 3), dtype=np.float32)
        obj = evaluated_object(geomobj)
        if pins_count ==0 or len(obj.data.vertices) == 0:
            _log.output('surface_points_from_mesh empty end >>>')
            return verts

        for i in range(pins_count):
            pin = gt.pin(keyframe, i)
            if pin is not None:
                p = pin_to_xyz_from_mesh(pin, obj)
                if p is not None:
                    verts[i] = p
        _log.output('surface_points_from_mesh end >>>')
        return verts

    def create_batch_2d(self, area: Area) -> None:
        rx, ry = bpy_render_frame()
        asp = ry / rx
        x1, y1, x2, y2 = get_camera_border(area)

        pins = self.pins()

        shift_x, shift_y = get_scene_camera_shift()
        points = [image_space_to_region(p[0], p[1], x1, y1, x2, y2,
                                        shift_x, shift_y) for p in pins.arr()]
        points_count = len(points)

        vertex_colors = [GTConfig.pin_color] * points_count

        color = (*GTConfig.disabled_pin_color[:3], 0.0) \
            if pins.move_pin_mode() else GTConfig.disabled_pin_color
        for i in [x for x in pins.get_disabled_pins() if x < points_count]:
            vertex_colors[i] = color

        for i in [x for x in pins.get_selected_pins() if x < points_count]:
            vertex_colors[i] = GTConfig.selected_pin_color

        pin_num = pins.current_pin_num()
        if pins.current_pin() and pin_num < points_count:
            vertex_colors[pin_num] = GTConfig.current_pin_color

        self.points2d().set_vertices_and_colors(points, vertex_colors)
        self.points2d().create_batch()

        mask = self.mask2d()
        if mask.image:
            _log.output(f'create_batch_2d mask.image: {mask.image}')
            mask.left = image_space_to_region(-0.5, -asp * 0.5, x1, y1, x2, y2)
            w, h = mask.image.size[:]
            mask.right = image_space_to_region(
                *frame_to_image_space(w, h, rx, ry), x1, y1, x2, y2)
            mask.create_batch()

    def update_residuals(self, gt: Any, area: Area, keyframe: int) -> None:
        rx, ry = bpy_render_frame()
        x1, y1, x2, y2 = get_camera_border(area)

        p2d = self.points2d().get_vertices()
        p3d = self.points3d().get_vertices()

        wire = self.residuals()
        wire.clear_vertices()
        wire.edge_lengths = np.empty((0,), dtype=np.int32)
        wire.vertex_colors = np.empty((0, 4), dtype=np.float32)

        if len(p2d) != len(p3d):
            return

        if len(p3d) == 0:
            wire.create_batch()  # Empty shader
            return

        camobj = bpy_scene_camera()
        if not camobj:
            return

        projection = gt.projection_mat(keyframe).T
        try:
            m = camobj.matrix_world.inverted()
        except Exception as err:
            _log.error(f'update_residuals Exception:\n{str(err)}'
                       f'\n{camobj.matrix_world}')
            return
        # Object transform, inverse camera, projection apply -> numpy
        transform = np.array(m.transposed()) @ projection

        # Calc projection
        vv = to_homogeneous(p3d) @ transform
        vv = (vv.T / vv[:, 3]).T

        residual_count = len(vv)
        verts = np.empty((residual_count * 2, 2), dtype=np.float32)

        shift_x, shift_y = camobj.data.shift_x, camobj.data.shift_y
        for i, v in enumerate(vv):
            x, y = frame_to_image_space(v[0], v[1], rx, ry, shift_x, shift_y)
            verts[i * 2] = image_space_to_region(x, y, x1, y1, x2, y2,
                                                 shift_x, shift_y)
            verts[i * 2 + 1] = p2d[i][:2]
            # length = np.linalg.norm((v[0]-p2d[i][0], v[1]-p2d[i][1]))

        wire.edge_lengths = np.full((residual_count, 2),
                                    (0.0, Config.residual_dashed_line_length),
                                    dtype=np.float32).ravel()

        wire.vertices = verts
        wire.vertex_colors = np.full((residual_count * 2, 4),
                                     GTConfig.residual_color,
                                     dtype=np.float32)
        pins = self.pins()
        if pins.move_pin_mode():
            points_count = len(wire.vertex_colors)
            hidden_color = (*GTConfig.residual_color[:3], 0.0)
            for i in [x for x in pins.get_disabled_pins() if 2 * x < points_count]:
                wire.vertex_colors[i * 2] = hidden_color
                wire.vertex_colors[i * 2 + 1] = hidden_color
        wire.create_batch()

    def hide_pins_and_residuals(self):
        _log.yellow(f'{self.__class__.__name__}.hide_pins_and_residuals start')
        self.points2d().hide_shader()
        self.points3d().hide_shader()
        self.residuals().hide_shader()
        _log.output(f'{self.__class__.__name__}.hide_pins_and_residuals end >>>')

    def unhide_pins_and_residuals(self):
        _log.yellow(f'{self.__class__.__name__}.unhide_pins_and_residuals start')
        self.points2d().unhide_shader()
        self.points3d().unhide_shader()
        self.residuals().unhide_shader()
        _log.output(f'{self.__class__.__name__}.unhide_pins_and_residuals end >>>')

    def hide_all_shaders(self):
        _log.yellow(f'{self.__class__.__name__}.hide_all_shaders start')
        self.mask2d().hide_shader()
        self.residuals().hide_shader()
        self.points3d().hide_shader()
        self.points2d().hide_shader()
        self.texter().hide_shader()
        self.wireframer().hide_shader()
        self.timeliner().hide_shader()
        self.selector().hide_shader()
        _log.output(f'{self.__class__.__name__}.hide_all_shaders end >>>')

    def unhide_all_shaders(self):
        _log.yellow(f'{self.__class__.__name__}.unhide_all_shaders start')
        self.mask2d().unhide_shader()
        self.residuals().unhide_shader()
        self.points3d().unhide_shader()
        self.points2d().unhide_shader()
        self.texter().unhide_shader()
        self.wireframer().unhide_shader()
        self.timeliner().unhide_shader()
        self.selector().unhide_shader()
        _log.output(f'{self.__class__.__name__}.unhide_all_shaders end >>>')

    def needs_to_be_drawn(self):
        return self.points2d().needs_to_be_drawn() or \
               self.residuals().needs_to_be_drawn()

    def start_viewport(self, *, area: Any) -> ActionStatus:
        _log.green(f'{self.__class__.__name__}.start_viewport start')

        if not self.load_all_shaders():
            msg = 'Problem with loading shaders (see console)'
            _log.error(msg)
            _log.output(f'{self.__class__.__name__}.start_viewport loading shaders error >>>')
            return ActionStatus(False, msg)

        self.register_handlers(area=area)
        self.unhide_all_shaders()
        self.tag_redraw()
        force_ui_redraw('DOPESHEET_EDITOR')
        _log.output(f'{self.__class__.__name__}.start_viewport end >>>')
        return ActionStatus(True, 'ok')

    def stop_viewport(self) -> ActionStatus:
        _log.green(f'{self.__class__.__name__}.stop_viewport start')
        area = self.unregister_handlers()
        if area:
            area.tag_redraw()
        _log.output(f'{self.__class__.__name__}.stop_viewport end >>>')
        return ActionStatus(True, 'ok')
