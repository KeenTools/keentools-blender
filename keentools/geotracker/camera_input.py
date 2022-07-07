# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2022 KeenTools

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
import logging
from typing import Any, Tuple, List, Dict

import bpy
from bpy.types import Object

from ..geotracker_config import get_gt_settings
from ..utils import coords
from ..utils.animation import (get_safe_evaluated_fcurve,
                               create_locrot_keyframe,
                               get_object_keyframe_numbers,
                               delete_animation_between_frames,
                               insert_keyframe_in_fcurve,
                               remove_fcurve_from_object)
from ..blender_independent_packages.pykeentools_loader import module as pkt_module


_logger: Any = logging.getLogger(__name__)


def _log_output(message: str) -> None:
    global logger
    _logger.debug(message)


class GTCameraInput(pkt_module().TrackerCameraInputI):
    def projection(self, frame: int) -> Any:
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return np.eye(4)
        camera = geotracker.camobj
        assert camera is not None
        cam_data = camera.data
        near = cam_data.clip_start
        far = cam_data.clip_end
        scene = bpy.context.scene
        w = scene.render.resolution_x
        h = scene.render.resolution_y
        lens = get_safe_evaluated_fcurve(cam_data, frame, 'lens')
        proj_mat = coords.projection_matrix(w, h, lens,
                                            cam_data.sensor_width,
                                            near, far, scale=1.0)
        return proj_mat

    def view(self, keyframe: int) -> Any:
        return np.eye(4)

    def image_size(self) -> Tuple[int, int]:
        scene = bpy.context.scene
        w = scene.render.resolution_x
        h = scene.render.resolution_y
        return (w, h)


class GTGeoInput(pkt_module().GeoInputI):
    def geo_hash(self) -> Any:
        return pkt_module().Hash(42)

    def geo(self) -> Any:
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return None
        return self.init_geo(coords.evaluated_mesh(geotracker.geomobj))

    @staticmethod
    def init_geo(obj: Object) -> Any:
        mesh = obj.data
        scale = coords.get_scale_matrix_3x3_from_matrix_world(obj.matrix_world)
        verts = coords.get_mesh_verts(obj) @ scale

        mb = pkt_module().MeshBuilder()
        mb.add_points(verts @ coords.xz_to_xy_rotation_matrix_3x3())

        for polygon in mesh.polygons:
            mb.add_face(polygon.vertices[:])

        _geo = pkt_module().Geo()
        _geo.add_mesh(mb.mesh())
        return _geo


class GTImageInput(pkt_module().ImageInputI):
    def image_hash(self, frame: int) -> Any:
        return pkt_module().Hash(frame)

    def load_linear_rgb_image_at(self, frame: int) -> Any:
        _log_output('load_linear_rgb_image_at: {}'.format(frame))
        settings = get_gt_settings()
        frame_filepath = settings.get_frame_image_path(frame)
        _log_output('frame_filepath: {}'.format(frame_filepath))

        img = bpy.data.images.load(frame_filepath)
        size = img.size
        _log_output('img.size: {} {}'.format(size[0], size[1]))

        np_img0 = np.asarray(img.pixels[:], dtype=np.float32)
        np_img = np_img0.reshape((size[1], size[0], 4))
        bpy.data.images.remove(img, do_unlink=True)
        return np_img[:, :, :3]

    def first_frame(self) -> int:
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return 1
        return geotracker.precalc_start

    def last_frame(self) -> int:
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return 0
        return geotracker.precalc_end


class GTMask2DInput(pkt_module().Mask2DInputI):
    def load_2d_mask_at(self, frame: int) -> Any:
        return None


class GTGeoTrackerResultsStorage(pkt_module().GeoTrackerResultsStorageI):
    def __init__(self):
        super().__init__()
        flm =pkt_module().GeoTracker.FocalLengthMode
        self._modes: Dict = {
            mode.value: mode for mode in [
            flm.CAMERA_FOCAL_LENGTH,
            flm.STATIC_FOCAL_LENGTH,
            flm.ZOOM_FOCAL_LENGTH
        ]}

    def _mode_by_value(self, value: int) -> Any:
        if value in self._modes.keys():
            return self._modes[value]
        return pkt_module().GeoTracker.FocalLengthMode.CAMERA_FOCAL_LENGTH

    def _set_fl_mode(self, enum_value) -> None:
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return
        geotracker.focal_length_mode = enum_value.value

    def _set_static_fl(self, static_fl: float) -> None:
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker or not geotracker.camobj:
            return
        geotracker.static_focal_length = static_fl
        cam_data = geotracker.camobj.data
        remove_fcurve_from_object(cam_data, 'lens')
        cam_data.lens = static_fl

    def serialize(self) -> str:
        return ''

    def deserialize(self, serial_txt: str) -> bool:
        return True

    def model_mat_at(self, frame: int) -> Any:
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return np.eye(4)

        current_frame = settings.current_frame()
        if current_frame != frame:
            settings.set_current_frame(frame)
            mat = geotracker.calc_model_matrix()
            settings.set_current_frame(current_frame)
            return mat
        else:
            return geotracker.calc_model_matrix()

    def set_model_mat_at(self, frame: int, model_mat: Any) -> None:
        _log_output(f'set_model_mat_at1: {frame}\n{model_mat}')
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return
        if not geotracker.geomobj or not geotracker.camobj:
            return

        current_frame = settings.current_frame()
        if current_frame != frame:
            settings.set_current_frame(frame)

        if geotracker.camera_mode():
            mat = coords.calc_bpy_camera_mat_relative_to_model(
                geotracker.geomobj, model_mat)
            _log_output(f'set_model_mat2:\n{mat}')
            geotracker.camobj.matrix_world = mat
        else:
            mat = coords.calc_bpy_model_mat_relative_to_camera(
                geotracker.camobj, geotracker.geomobj, model_mat)
            _log_output(f'set_model_mat3:\n{mat}')
            geotracker.geomobj.matrix_world = mat

        create_locrot_keyframe(geotracker.animatable_object(),
            'KEYFRAME' if not settings.tracking_mode else 'JITTER')
        if current_frame != frame:
            settings.set_current_frame(current_frame)

    def remove_track_data(self, *args, **kwargs) -> None:
        _log_output(f'remove_track_data1: {args}')
        if not (1 <= len(args) <= 2):
            return
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return
        if not geotracker.geomobj or not geotracker.camobj:
            return
        from_frame = args[0]
        to_frame = from_frame if len(args) == 1 else args[1]
        delete_animation_between_frames(geotracker.animatable_object(),
                                        from_frame, to_frame)

    def trackframes(self) -> List[int]:
        _log_output('trackframes call')
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return []
        track_frames = get_object_keyframe_numbers(geotracker.animatable_object())
        _log_output(f'trackframes: {track_frames}')
        return track_frames

    def zoom_focal_length_at(self, frame: int) -> float:
        _log_output(f'zoom_focal_length_at: {frame}')
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker or not geotracker.camobj:
            return geotracker.default_zoom_focal_length
        return get_safe_evaluated_fcurve(geotracker.camobj.data, frame, 'lens')

    def get_default_zoom_focal_length(self) -> float:
        _log_output('get_default_zoom_focal_length')
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return 50.0  # Undefined case
        return geotracker.default_zoom_focal_length

    def set_default_zoom_focal_length(self, default_fl: float) -> None:
        _log_output(f'set_default_zoom_focal_length: {default_fl}')
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return
        geotracker.default_zoom_focal_length = default_fl

    def set_zoom_focal_length_mode(self, default_fl: float) -> None:
        _log_output('set_zoom_focal_length_mode call')
        self.set_default_zoom_focal_length(default_fl)
        self._set_fl_mode(pkt_module().GeoTracker.FocalLengthMode.ZOOM_FOCAL_LENGTH)

    def set_static_focal_length(self, static_fl: float) -> None:
        _log_output(f'set_static_focal_length: {static_fl}')
        self._set_static_fl(static_fl)

    def set_static_focal_length_mode(self, static_fl: float) -> None:
        _log_output(f'set_static_focal_length_mode: {static_fl}')
        self._set_fl_mode(pkt_module().GeoTracker.FocalLengthMode.STATIC_FOCAL_LENGTH)
        self._set_static_fl(static_fl)

    def static_focal_length(self) -> float:
        _log_output('static_focal_length call')
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return 50.0  # Undefined case
        return geotracker.static_focal_length

    def set_camera_focal_length_mode(self) -> None:
        _log_output('set_camera_focal_length_mode')
        self._set_fl_mode(pkt_module().GeoTracker.FocalLengthMode.CAMERA_FOCAL_LENGTH)

    def focal_length_mode(self) -> Any:
        _log_output('focal_length_mode call')
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return pkt_module().GeoTracker.FocalLengthMode.CAMERA_FOCAL_LENGTH
        _log_output(f'focal_length_mode: {geotracker.focal_length_mode}')
        return self._mode_by_value(geotracker.focal_length_mode)

    def set_zoom_focal_length_at(self, frame: int, fl: float) -> None:
        _log_output('set_zoom_focal_length_at')
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return
        insert_keyframe_in_fcurve(geotracker.camobj.data, frame, fl,
                                  'KEYFRAME', 'lens')
