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
from typing import Any, Optional
import numpy as np

import bpy
from bpy.types import Area

from ..geotracker_config import GTConfig, get_gt_settings
from .viewport import GTViewport
from ..utils import coords
from .gt_class_loader import GTClassLoader


class GTLoader:
    _viewport: Any = GTViewport()

    _geo: Any = None
    _geomobj_world_matrix_at_frame: tuple[int, Any] = (-1, None)

    _geomobj_edit_mode: str = 'OBJECT'

    _geo_input: Any = None
    _image_input: Any = None
    _camera_input: Any = None
    _kt_geotracker: Any = None
    _mask2d: Any = None

    @classmethod
    def update_geomobj_mesh(cls) -> None:
        logger = logging.getLogger(__name__)
        logger.debug('update_geomobj_mesh UPDATE')
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()
        geotracker.geomobj.update_from_editmode()

    @classmethod
    def get_geomobj_mode(cls) -> str:
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()
        return geotracker.geomobj.mode

    @classmethod
    def store_geomobj_mode(cls, mode: str='OBJECT') -> None:
        cls._geomobj_edit_mode = mode

    @classmethod
    def get_stored_geomobj_mode(cls) -> str:
        return cls._geomobj_edit_mode

    @classmethod
    def geomobj_mode_changed_to_object(cls, update: bool=True) -> bool:
        stored_mode = cls.get_stored_geomobj_mode()
        current_mode = cls.get_geomobj_mode()
        if stored_mode == current_mode:
            return False
        if update:
            cls.store_geomobj_mode(current_mode)
        if current_mode == 'OBJECT':
            return True
        return False

    @classmethod
    def store_geomobj_world_matrix(cls, frame: int, matrix: Any) -> None:
        cls._geomobj_world_matrix_at_frame = (frame, np.array(matrix,
                                                              dtype=np.float32))

    @classmethod
    def get_stored_geomobj_world_matrix(cls) -> Any:
        return cls._geomobj_world_matrix_at_frame

    @classmethod
    def get_geomobj_world_matrix(cls) -> tuple[int, Any]:
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()
        return (settings.current_frame(),
                np.array(geotracker.geomobj.matrix_world, dtype=np.float32))

    @classmethod
    def geomobj_world_matrix_changed(cls, update: bool=False) -> Optional[bool]:
        logger = logging.getLogger(__name__)
        stored = cls.get_stored_geomobj_world_matrix()
        current = cls.get_geomobj_world_matrix()
        if stored[0] != current[0]:
            cls.store_geomobj_world_matrix(*current)
            logger.debug('geomobj_world_matrix_changed FRAMES DIFFER')
            logger.debug('stored: {}'.format(stored[0]))
            logger.debug('\n{}'.format(stored[1]))
            logger.debug('current: {}'.format(current[0]))
            logger.debug('\n{}'.format(current[1]))
            return None
        if np.all(np.isclose(stored[1], current[1],
                             rtol=GTConfig.matrix_rtol, atol=GTConfig.matrix_atol)):
            # logger.debug('geomobj_world_matrix_changed -- NO CHANGES')
            return False
        logger.debug('geomobj_world_matrix_changed -- MATRICES DIFFER')
        logger.debug('stored: {}'.format(stored[0]))
        logger.debug('\n{}'.format(stored[1]))
        logger.debug('current: {}'.format(current[0]))
        logger.debug('\n{}'.format(current[1]))
        logger.debug('\n\n{}\n{}'.format(stored[1][:], current[1][:]))
        logger.debug('\n==\n{}'.format((stored[1] - current[1])[:]))
        if update:
            cls.store_geomobj_world_matrix(*current)
        return True

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
        cls._kt_geotracker = GTClassLoader.GeoTracker_class()(
            cls._geo_input,
            cls._camera_input,
            cls._image_input,
            cls._mask2d)
        return cls._kt_geotracker

    @classmethod
    def kt_geotracker(cls) -> Any:
        if cls._kt_geotracker is None:
            return cls.new_kt_geotracker()
        return cls._kt_geotracker

    @classmethod
    def add_pin(cls, keyframe: int, pos: tuple[float, float]) -> Any:
        logger = logging.getLogger(__name__)
        logger.debug('ADD PIN: {} {}'.format(pos[0], pos[1]))
        gt = cls.kt_geotracker()

        pin_result = gt.add_pin(keyframe, pos)
        logger.debug('PIN RESULT: {}'.format(pin_result))
        if pin_result:
            pin = gt.pin(keyframe, gt.pins_count() - 1)
            logger.debug('ADDED PIN: {} {}'.format(pin.img_pos[0], pin.img_pos[1]))
            return pin
        return False

    @classmethod
    def move_pin(cls, keyframe: int, pin_idx: int,
                 pos: tuple[float, float]) -> None:
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
        vp.pins().reset_current_pin()

    @classmethod
    def tag_redraw(cls, context: Any) -> None:
        if not bpy.app.background:
            logger = logging.getLogger(__name__)
            logger.debug('TAG REDRAW CALL')
            context.area.tag_redraw()

    @classmethod
    def place_camera_relative_to_model(cls, forced: bool=False) -> None:
        logger = logging.getLogger(__name__)
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return

        gt = cls.kt_geotracker()
        keyframe = settings.current_frame()
        model = geotracker.geomobj
        camera = geotracker.camobj
        rot_mat2 = coords.xz_to_xy_rotation_matrix_4x4()

        if gt.is_key_at(keyframe) or forced:
            logger.debug('MATRIX FROM GEOTRACKER')
            scale_vec = coords.get_scale_vec_4_from_matrix_world(model.matrix_world)
            scminv = np.diag(1.0 / scale_vec)
            gt_model_mat = gt.model_mat(keyframe)

            try:
                mat = np.array(model.matrix_world) @ scminv @ rot_mat2 @ np.linalg.inv(gt_model_mat)
                camera.matrix_world = mat.transpose()
            except Exception:
                pass

    @classmethod
    def place_model_relative_to_camera(cls, forced: bool=False) -> None:
        logger = logging.getLogger(__name__)
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return

        gt = cls.kt_geotracker()
        keyframe = settings.current_frame()
        model = geotracker.geomobj
        camera = geotracker.camobj
        rot_mat = coords.xy_to_xz_rotation_matrix_4x4()

        if gt.is_key_at(keyframe) or forced:
            logger.debug('MATRIX FROM GEOTRACKER')
            scale_mat = coords.get_scale_matrix_4x4_from_matrix_world(model.matrix_world)
            gt_model_mat = gt.model_mat(keyframe)
            np_mw = np.array(camera.matrix_world) @ (gt_model_mat @
                                                     rot_mat @ scale_mat)
            model.matrix_world = np_mw.transpose()
            logger.debug('place_model_relative_to_camera MW: \n'
                         '{}'.format(model.matrix_world))
            logger.debug('model_mat:\n{}'.format(gt_model_mat))
        else:
            logger.debug('MATRIX FROM OBJECT')


    @classmethod
    def place_camera(cls, forced: bool=False) -> None:
        logger = logging.getLogger(__name__)
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return

        if geotracker.solve_for_camera_mode():
            logger.debug('place_camera_relative_to_model')
            cls.place_camera_relative_to_model(forced=forced)
        else:
            logger.debug('place_model_relative_to_camera')
            cls.place_model_relative_to_camera(forced=forced)

    @classmethod
    def updated_focal_length(cls, force: bool=False) -> None:
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
        logger = logging.getLogger(__name__)
        logger.debug('FOCAL ESTIMATED: {}'.format(focal))
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

        rot_mat = coords.xz_to_xy_rotation_matrix_4x4()

        cam_mat = geotracker.camobj.matrix_world
        geom_mw = geotracker.geomobj.matrix_world
        scale_vec = coords.get_scale_vec_4_from_matrix_world(geom_mw)
        scminv = np.diag(1.0 / scale_vec)
        geom_mat = np.array(geom_mw, dtype=np.float32) @ scminv

        nm = np.array(cam_mat.inverted_safe(),
                      dtype=np.float32) @ geom_mat @ rot_mat
        return nm

    @classmethod
    def safe_keyframe_add(cls, keyframe: int, mat: Any) -> None:
        logger = logging.getLogger(__name__)
        gt = cls.kt_geotracker()
        if not gt.is_key_at(keyframe):
            logger.debug('safe_keyframe_add: {}\n{}'.format(keyframe, mat))
            gt.set_keyframe(keyframe, mat)
        else:
            gt.update_model_mat(keyframe, mat)

    @classmethod
    def solve(cls, estimate_focal_length: bool=False) -> bool:
        logger = logging.getLogger(__name__)
        logger.debug('GTloader.solve called')
        settings = get_gt_settings()
        gt = cls.kt_geotracker()
        keyframe = settings.current_frame()
        if not estimate_focal_length:
            gt.set_focal_length_mode(GTClassLoader.GeoTracker_class().FocalLengthMode.CAMERA_FOCAL_LENGTH)
        else:
            gt.set_focal_length_mode(GTClassLoader.GeoTracker_class().FocalLengthMode.STATIC_FOCAL_LENGTH)

        gt.solve_for_current_pins(keyframe, estimate_focal_length)
        logger.debug('GTloader.solve finished')
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
            logger = logging.getLogger(__name__)
            logger.warning('EMPTY SERIAL ERROR: {}'.format(settings.current_geotracker_num))
            return False

        gt = cls.kt_geotracker()
        if not gt.deserialize(serial):
            logger = logging.getLogger(__name__)
            logger.warning('DESERIALIZE ERROR: {}'.format(serial))
            return False
        return True

    @classmethod
    def update_viewport_wireframe(cls) -> None:
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return

        vp = GTLoader.viewport()
        wf = vp.wireframer()
        wf.init_geom_data_from_mesh(geotracker.geomobj)
        wf.init_color_data((*settings.wireframe_color,
                            settings.wireframe_opacity))
        wf.create_batches()

    @classmethod
    def update_viewport_pins_and_residuals(cls, context: Any) -> None:
        settings = get_gt_settings()
        vp = GTLoader.viewport()
        GTLoader.load_pins_into_viewport()
        vp.create_batch_2d(context)
        gt = GTLoader.kt_geotracker()
        kid = settings.current_frame()

        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return

        vp.update_surface_points(gt, geotracker.geomobj, kid)
        vp.update_residuals(gt, context, kid)

    @classmethod
    def update_all_viewport_shaders(cls, context: Any) -> None:
        cls.update_viewport_wireframe()
        cls.update_viewport_pins_and_residuals(context)
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
        texter = vp.texter()
        return texter.get_work_area()
