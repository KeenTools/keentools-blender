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

import logging
from typing import Any, Optional, Tuple, List
import numpy as np

import bpy
from bpy.types import Area

from ..addon_config import Config, get_operator, ErrorType
from ..geotracker_config import GTConfig, get_gt_settings
from .viewport import GTViewport
from ..utils import coords
from .gt_class_loader import GTClassLoader
from ..utils.timer import KTStopShaderTimer
from ..utils.ui_redraw import force_ui_redraw
from ..blender_independent_packages.pykeentools_loader import module as pkt_module


_logger: Any = logging.getLogger(__name__)


def _log_output(message: str) -> None:
    global logger
    _logger.debug(message)


def _log_warning(message):
    global logger
    _logger.warning(message)


def _log_error(message):
    global logger
    _logger.error(message)


def force_stop_gt_shaders() -> None:
    GTLoader.stop_viewport_shaders()
    force_ui_redraw('VIEW_3D')


class GTLoader:
    _viewport: Any = GTViewport()
    _geo: Any = None
    _geomobj_edit_mode: str = 'OBJECT'

    _geo_input: Any = None
    _image_input: Any = None
    _camera_input: Any = None
    _kt_geotracker: Any = None
    _mask2d: Any = None

    _check_shader_timer: Any = KTStopShaderTimer(get_gt_settings,
                                                 force_stop_gt_shaders)

    @classmethod
    def start_shader_timer(cls, uuid: str):
        cls._check_shader_timer.start(uuid)

    @classmethod
    def update_geomobj_mesh(cls) -> None:
        _log_output('update_geomobj_mesh UPDATE')
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()
        geotracker.geomobj.update_from_editmode()

    @classmethod
    def get_geomobj_mode(cls) -> str:
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker or not geotracker.geomobj:
            return 'OBJECT'
        return geotracker.geomobj.mode

    @classmethod
    def store_geomobj_mode(cls, mode: str='OBJECT') -> None:
        cls._geomobj_edit_mode = mode

    @classmethod
    def get_stored_geomobj_mode(cls) -> str:
        return cls._geomobj_edit_mode

    @classmethod
    def geomobj_mode_changed_to_object(cls, update: bool=True) -> bool:
        stored_mode: str = cls.get_stored_geomobj_mode()
        current_mode: str = cls.get_geomobj_mode()
        if stored_mode == current_mode:
            return False
        if update:
            cls.store_geomobj_mode(current_mode)
        if current_mode == 'OBJECT':
            return True
        return False

    @classmethod
    def viewport(cls) -> Any:
        return cls._viewport

    @classmethod
    def geo(cls) -> Any:
        return cls._geo

    @classmethod
    def new_kt_geotracker(cls) -> Any:
        cls._geo_input = GTClassLoader.GTGeoInput_class()()
        cls._image_input = GTClassLoader.GTImageInput_class()()
        cls._camera_input = GTClassLoader.GTCameraInput_class()()
        cls._mask2d = GTClassLoader.GTMask2DInput_class()()
        cls._storage = GTClassLoader.GTGeoTrackerResultsStorage_class()()

        if GTConfig.use_storage:
            cls._kt_geotracker = GTClassLoader.GeoTracker_class()(
                cls._geo_input,
                cls._camera_input,
                cls._image_input,
                cls._mask2d,
                cls._storage
            )
        else:
            cls._kt_geotracker = GTClassLoader.GeoTracker_class()(
                cls._geo_input,
                cls._camera_input,
                cls._image_input,
                cls._mask2d
            )
        return cls._kt_geotracker

    @classmethod
    def kt_geotracker(cls) -> Any:
        if cls._kt_geotracker is None:
            return cls.new_kt_geotracker()
        return cls._kt_geotracker

    @classmethod
    def add_pin(cls, keyframe: int, pos: Tuple[float, float]) -> Any:
        _log_output(f'add_pin ADD PIN: {pos}')
        gt = cls.kt_geotracker()
        pin_result = gt.add_pin(keyframe, pos)
        _log_output('add_pin PIN RESULT: {}'.format(pin_result))
        if pin_result:
            pin = gt.pin(keyframe, gt.pins_count() - 1)
            _log_output(f'add_pin ADDED PIN: {pin.img_pos}')
            return pin
        return False

    @classmethod
    def move_pin(cls, keyframe: int, pin_idx: int,
                 pos: Tuple[float, float]) -> None:
        gt = cls.kt_geotracker()
        if pin_idx < gt.pins_count():
            gt.move_pin(keyframe, pin_idx, coords.image_space_to_frame(*pos))

    @classmethod
    def load_pins_into_viewport(cls) -> None:
        settings = get_gt_settings()
        keyframe = settings.current_frame()

        vp = cls.viewport()
        gt = cls.kt_geotracker()
        vp.pins().set_pins(vp.img_points(gt, keyframe))

    @classmethod
    def tag_redraw(cls, context: Any) -> None:
        if not bpy.app.background:
            _log_output('TAG REDRAW CALL')
            context.area.tag_redraw()

    @classmethod
    def viewport_area_redraw(cls):
        vp = cls.viewport()
        vp.tag_redraw()

    @classmethod
    def place_camera(cls, forced: bool=False) -> None:
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return
        gt = cls.kt_geotracker()
        keyframe = settings.current_frame()
        if not gt.is_key_at(keyframe) and not forced:
            return
        gt_model_mat = gt.model_mat(keyframe)
        if geotracker.camera_mode():
            mat = coords.calc_bpy_camera_mat_relative_to_model(
                geotracker.geomobj, gt_model_mat)
            geotracker.camobj.matrix_world = mat
        else:
            mat = coords.calc_bpy_model_mat_relative_to_camera(
                geotracker.camobj, geotracker.geomobj, gt_model_mat)
            geotracker.geomobj.matrix_world = mat

    @classmethod
    def updated_focal_length(cls, force: bool=False) -> Optional[float]:
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return None
        gt = GTLoader.kt_geotracker()
        frame = settings.current_frame()
        if not force and not gt.is_key_at(frame):
            return None
        proj_mat = gt.projection_mat(frame)
        focal = coords.focal_by_projection_matrix_mm(
            proj_mat, 36.0)  # Config.default_sensor_width
        _log_output('FOCAL ESTIMATED: {}'.format(focal))
        return focal * coords.compensate_view_scale()

    @classmethod
    def center_geo(cls) -> None:
        settings = get_gt_settings()
        keyframe = settings.current_frame()
        gt = cls.kt_geotracker()
        cls.safe_keyframe_add(keyframe, cls.calc_model_matrix())
        gt.center_geo(keyframe)

    @classmethod
    def calc_model_matrix(cls) -> Any:
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return np.eye(4)
        return geotracker.calc_model_matrix()

    @classmethod
    def safe_keyframe_add(cls, keyframe: int, mat: Any) -> None:
        gt = cls.kt_geotracker()
        if not gt.is_key_at(keyframe):
            _log_output('safe_keyframe_add: {}\n{}'.format(keyframe, mat))
            gt.set_keyframe(keyframe, mat)
        else:
            gt.update_model_mat(keyframe, mat)

    @classmethod
    def solve(cls) -> bool:
        _log_output('GTloader.solve called')
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()
        gt = cls.kt_geotracker()
        keyframe = settings.current_frame()
        try:
            if geotracker.focal_length_mode == 'STATIC_FOCAL_LENGTH':
                gt.set_focal_length_mode(GTClassLoader.GeoTracker_class().FocalLengthMode.STATIC_FOCAL_LENGTH)
            elif geotracker.focal_length_mode == 'ZOOM_FOCAL_LENGTH':
                gt.set_focal_length_mode(GTClassLoader.GeoTracker_class().FocalLengthMode.ZOOM_FOCAL_LENGTH)
            else:
                gt.set_focal_length_mode(GTClassLoader.GeoTracker_class().FocalLengthMode.CAMERA_FOCAL_LENGTH)
                geotracker.focal_length_estimation = False

            gt.solve_for_current_pins(keyframe, geotracker.focal_length_estimation)

        except pkt_module().UnlicensedException as err:
            _log_error(f'solve UnlicensedException: \n{str(err)}')
            warn = get_operator(Config.kt_warning_idname)
            warn('INVOKE_DEFAULT', msg=ErrorType.NoLicense)
            settings.force_out_pinmode = True
            return False
        except Exception as err:
            _log_error(f'solve UNKNOWN EXCEPTION: \n{str(err)}')
            return False
        _log_output('GTloader.solve finished')
        return True

    @classmethod
    def save_geotracker(cls) -> None:
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return

        gt = cls.kt_geotracker()
        geotracker.save_serial_str(gt.serialize())
        geotracker.store_serial_str_on_geomobj()

    @classmethod
    def load_geotracker(cls) -> bool:
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return False

        serial = geotracker.get_serial_str()

        if serial == '':
            _log_warning('EMPTY SERIAL ERROR: {}'.format(settings.current_geotracker_num))
            return False

        gt = cls.kt_geotracker()
        if not gt.deserialize(serial):
            _log_warning('DESERIALIZE ERROR: {}'.format(serial))
            return False
        return True

    @classmethod
    def update_viewport_wireframe(cls) -> None:
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker or not geotracker.geomobj:
            return

        vp = GTLoader.viewport()
        wf = vp.wireframer()
        wf.init_geom_data_from_mesh(geotracker.geomobj)
        wf.init_color_data((*settings.wireframe_color,
                            settings.wireframe_opacity))
        wf.create_batches()

    @classmethod
    def update_viewport_pins_and_residuals(cls, area: Area) -> None:
        settings = get_gt_settings()
        vp = GTLoader.viewport()
        GTLoader.load_pins_into_viewport()
        vp.create_batch_2d(area)
        gt = GTLoader.kt_geotracker()
        kid = settings.current_frame()

        geotracker = settings.get_current_geotracker_item()
        if not geotracker or not geotracker.geomobj:
            return

        vp.update_surface_points(gt, geotracker.geomobj, kid)
        vp.update_residuals(gt, area, kid)

    @classmethod
    def update_all_viewport_shaders(cls, area: Optional[Area]=None) -> None:
        if area is None:
            vp = cls.viewport()
            area = vp.get_work_area()
            if not area:
                return
        cls.update_viewport_wireframe()
        cls.update_viewport_pins_and_residuals(area)
        cls.update_timeline()

    @classmethod
    def _update_all_timelines(cls) -> None:
        areas = bpy.context.workspace.screens[0].areas
        for area in areas:
            if area.type == 'DOPESHEET_EDITOR':
                area.tag_redraw()

    @classmethod
    def update_timeline(cls) -> None:
        vp = GTLoader.viewport()
        timeliner = vp.timeliner()
        gt = cls.kt_geotracker()
        timeliner.set_keyframes(gt.keyframes())
        timeliner.create_batch()
        cls._update_all_timelines()

    @classmethod
    def spring_pins_back(cls) -> None:
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return

        if geotracker.spring_pins_back:
            gt = cls.kt_geotracker()
            gt.spring_pins_back(settings.current_frame())

    @classmethod
    def get_work_area(cls) -> Optional[Area]:
        vp = cls.viewport()
        return vp.get_work_area()

    @classmethod
    def message_to_screen(cls, msg: List) -> None:
        vp = cls.viewport()
        texter = vp.texter()
        texter.set_message(msg)

    @classmethod
    def revert_default_screen_message(cls, unregister=True) -> None:
        vp = cls.viewport()
        texter = vp.texter()
        texter.set_message(texter.get_default_text())
        if unregister:
            texter.unregister_handler()

    @classmethod
    def stop_viewport_shaders(cls) -> None:
        cls._check_shader_timer.stop()
        vp = cls.viewport()
        vp.unregister_handlers()
        _log_output('GT VIEWPORT SHADERS HAVE BEEN STOPPED')
