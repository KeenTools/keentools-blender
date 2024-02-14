# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2022-2023 KeenTools

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
from typing import Any, Tuple, List, Dict, Optional
from math import frexp

from ..utils.kt_logging import KTLogger
from ..addon_config import ProductType
from ..utils.coords import (focal_mm_to_px,
                            focal_px_to_mm,
                            camera_sensor_width,
                            calc_bpy_camera_mat_relative_to_model,
                            calc_bpy_model_mat_relative_to_camera,
                            camera_projection)
from ..utils.animation import (get_safe_evaluated_fcurve,
                               create_locrot_keyframe,
                               get_object_keyframe_numbers,
                               delete_animation_between_frames,
                               insert_keyframe_in_fcurve,
                               remove_fcurve_from_object)
from ..utils.bpy_common import (bpy_current_frame,
                                bpy_set_current_frame,
                                bpy_render_frame,
                                bpy_start_frame,
                                bpy_end_frame,
                                get_traceback)
from ..blender_independent_packages.pykeentools_loader import module as pkt_module
from ..geotracker.gtloader import GTLoader
from ..utils.images import (np_array_from_background_image,
                            np_threshold_image,
                            np_threshold_image_with_channels,
                            np_array_from_bpy_image)
from ..utils.ui_redraw import total_redraw_ui
from ..utils.mesh_builder import build_geo
from ..tracker.tracking_blendshapes import remove_relative_shape_keyframe


_log = KTLogger(__name__)


class CameraInput(pkt_module().TrackerCameraInputI):
    @classmethod
    def get_settings(cls) -> Any:
        assert False, 'CameraInput: get_settings'

    def projection(self, frame: int) -> Any:
        settings = self.get_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker or not geotracker.camobj:
            _log.output('projection error: no geotracker or camera')
            return np.eye(4)
        return camera_projection(geotracker.camobj, frame)

    def view(self, keyframe: int) -> Any:
        return np.eye(4)

    def image_size(self) -> Tuple[int, int]:
        return bpy_render_frame()


class GeoInput(pkt_module().GeoInputI):
    _previous_val: int = 0
    _previous_hash: Any = pkt_module().Hash(_previous_val)
    _hash_counter: int = 0

    hash_is_cached: bool = False

    @classmethod
    def get_settings(cls) -> Any:
        assert False, 'GeoInput: get_settings'

    @classmethod
    def clear_cache(cls) -> None:
        cls.hash_is_cached = False

    @classmethod
    def increment_hash(cls) -> None:
        cls._hash_counter += 1
        if cls._hash_counter > 1000:
            cls._hash_counter = 0
        cls.clear_cache()

    @classmethod
    def get_hash_counter(cls) -> int:
        return cls._hash_counter

    @classmethod
    def _set_previous_val(cls, val: int) -> Any:
        if cls._previous_val != val:
            cls._previous_val = val
            cls._previous_hash = pkt_module().Hash(cls._previous_val)
        cls.hash_is_cached = True
        return cls._previous_hash


    def _rounded(self, val: float) -> int:
        p = frexp(val)
        return int(round(p[0] * 10000, 0) + 3 * p[1])

    def geo_hash(self) -> Any:
        settings = self.get_settings()

        if self.hash_is_cached or settings.is_calculating():
            return self._previous_hash

        _log.output(_log.color('magenta', 'new geo_hash'))
        geotracker = settings.get_current_geotracker_item()
        if geotracker and geotracker.geomobj:
            vert_count = len(geotracker.geomobj.data.vertices)
            empirical_const = 3
            poly_count = len(geotracker.geomobj.data.polygons) * empirical_const
            scale = geotracker.geomobj.matrix_world.to_scale()
            scale_val = self._rounded(29 * scale[0]) + \
                        self._rounded(31 * scale[1]) + \
                        self._rounded(37 * scale[2])
        else:
            vert_count = 0
            poly_count = 0
            scale_val = 0

        val = abs(hash(settings.pinmode_id) + vert_count + poly_count +
                  scale_val + self.get_hash_counter())
        return self._set_previous_val(val)

    def geo(self) -> Any:
        settings = self.get_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return None
        return build_geo(geotracker.geomobj, get_uv=False)


class ImageInput(pkt_module().ImageInputI):
    @classmethod
    def get_settings(cls) -> Any:
        assert False, 'ImageInput: get_settings'

    def image_hash(self, frame: int) -> Any:
        return pkt_module().Hash(frame)

    def load_linear_rgb_image_at(self, frame: int) -> Any:
        def _empty_image():
            w, h = bpy_render_frame()
            return np.full((h, w, 3), (0.0, 0.0, 0.0), dtype=np.float32)

        _log.output(_log.color('magenta', f'load_linear_rgb_image_at: {frame}'))
        settings = self.get_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            _log.error('load_linear_rgb_image_at NO GEOTRACKER')
            return _empty_image()

        current_frame = bpy_current_frame()
        if current_frame != frame:
            _log.output('load_linear_rgb_image_at1')
            bpy_set_current_frame(frame)
            _log.output('load_linear_rgb_image_at2')

        total_redraw_ui()
        np_img = np_array_from_background_image(geotracker.camobj, index=0)

        if (current_frame != frame) and not settings.is_calculating():
            _log.output('load_linear_rgb_image_at3')
            bpy_set_current_frame(current_frame)

        if np_img is not None:
            return np_img[:, :, :3]
        else:
            _log.output(f'load_linear_rgb_image_at EMPTY IMAGE: {frame}')
            return _empty_image()

    def first_frame(self) -> int:
        return bpy_start_frame()

    def last_frame(self) -> int:
        return bpy_end_frame()


class Mask2DInput(pkt_module().Mask2DInputI):
    @classmethod
    def get_settings(cls) -> Any:
        assert False, 'Mask2DInput: get_settings'

    def load_image_2d_mask_at(self, frame: int) -> Any:
        settings = self.get_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker or not geotracker.mask_2d:
            return None

        current_frame = bpy_current_frame()
        _log.output(f'load_image_2d_mask_at: {frame} [{current_frame}]')
        if current_frame != frame:
            _log.output(f'FORCE CHANGE FRAME TO: {frame}')
            bpy_set_current_frame(frame)

        total_redraw_ui()
        np_img = np_array_from_background_image(geotracker.camobj, index=1)

        if (current_frame != frame) and not settings.is_calculating():
            _log.output(f'REVERT FRAME TO: {frame}')
            bpy_set_current_frame(current_frame)

        if np_img is None:
            _log.output('NO MASK IMAGE')
            return None

        rw, rh = bpy_render_frame()
        if np_img.shape[0] != rh and np_img.shape[1] != rw:
            _log.error(f'MASK HAS DIFFERENT SIZE: {np_img.shape} RW: {rw} RH: {rh}')

        _log.output(f'MASK INPUT HAS BEEN CALCULATED AT FRAME: {frame}')

        result = np_threshold_image_with_channels(
            np_img, geotracker.get_mask_2d_channels(),
            geotracker.mask_2d_threshold)

        if result is not None:
            _log.output(f'mask shape: {result.shape}')
            return pkt_module().LoadedMask(result, geotracker.mask_2d_inverted)
        return None

    def load_compositing_2d_mask_at(self, frame: int) -> Any:
        settings = self.get_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker or geotracker.compositing_mask == '':
            return None
        mask_image = geotracker.update_compositing_mask(frame=frame)
        np_img = np_array_from_bpy_image(mask_image)
        if np_img is None:
            _log.output('NO COMP MASK IMAGE')
            return None
        grayscale = np_threshold_image(np_img,
                                       geotracker.compositing_mask_threshold)
        _log.output(f'COMP MASK INPUT HAS BEEN CALCULATED AT FRAME: {frame}')
        return pkt_module().LoadedMask(grayscale,
                                       geotracker.compositing_mask_inverted)

    def load_2d_mask_at(self, frame: int) -> Any:
        settings = self.get_settings()
        geotracker = settings.get_current_geotracker_item()
        mask_source = geotracker.get_2d_mask_source()
        if mask_source == 'COMP_MASK':
            return self.load_compositing_2d_mask_at(frame)
        elif mask_source == 'MASK_2D':
            return self.load_image_2d_mask_at(frame)
        return None


class GeoTrackerResultsStorage(pkt_module().GeoTrackerResultsStorageI):
    def __init__(self):
        super().__init__()
        fl_mode = pkt_module().TrackerFocalLengthMode
        self._modes: Dict = {
            mode.name: mode for mode in [
            fl_mode.CAMERA_FOCAL_LENGTH,
            fl_mode.STATIC_FOCAL_LENGTH,
            fl_mode.ZOOM_FOCAL_LENGTH
        ]}

    @classmethod
    def get_settings(cls) -> Any:
        assert False, 'GeoTrackerResultsStorage: get_settings'

    def _mode_by_value(self, value: str) -> Any:
        if value in self._modes.keys():
            return self._modes[value]
        return pkt_module().TrackerFocalLengthMode.CAMERA_FOCAL_LENGTH

    def _set_fl_mode(self, enum_value) -> None:
        settings = self.get_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return
        geotracker.focal_length_mode = enum_value.name

    def _set_static_fl(self, static_fl: float) -> None:
        _log.output(f'_set_static_fl: {static_fl}')
        settings = self.get_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return
        geotracker.static_focal_length = static_fl
        if not geotracker.camobj:
            return
        cam_data = geotracker.camobj.data
        _log.output('remove_fcurve_from_object: lens')
        remove_fcurve_from_object(cam_data, 'lens')
        cam_data.lens = focal_px_to_mm(static_fl, *bpy_render_frame(),
                                       cam_data.sensor_width)

    def serialize(self) -> str:
        _log.output('serialize call')
        return ''

    def deserialize(self, serial_txt: str) -> bool:
        _log.output(f'deserialize: {serial_txt}')
        return True

    def model_mat_at(self, frame: int) -> Any:
        settings = self.get_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return np.eye(4)

        current_frame = bpy_current_frame()
        if current_frame != frame:
            bpy_set_current_frame(frame)
            mat = geotracker.calc_model_matrix()
            if not settings.is_calculating():
                bpy_set_current_frame(current_frame)
            return mat
        else:
            return geotracker.calc_model_matrix()

    def set_model_mat_at(self, frame: int, model_mat: Any) -> None:
        _log.output(f'set_model_mat_at1: {frame}')
        settings = self.get_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return
        if not geotracker.geomobj or not geotracker.camobj:
            return

        current_frame = bpy_current_frame()
        if current_frame != frame:
            bpy_set_current_frame(frame)

        if geotracker.camera_mode():
            mat = calc_bpy_camera_mat_relative_to_model(
                geotracker.geomobj.matrix_world,
                geotracker.camobj.matrix_world, model_mat)
            _log.output(f'set_model_mat_at2')
            geotracker.camobj.matrix_world = mat
        else:
            mat = calc_bpy_model_mat_relative_to_camera(
                geotracker.geomobj.matrix_world,
                geotracker.camobj.matrix_world, model_mat)
            _log.output(f'set_model_mat_at3')
            geotracker.geomobj.matrix_world = mat

        gt = settings.loader().kt_geotracker()
        keyframe_type = 'KEYFRAME' if gt.is_key_at(frame) else 'JITTER'
        create_locrot_keyframe(geotracker.animatable_object(), keyframe_type)
        if (current_frame != frame) and not settings.is_calculating():
            bpy_set_current_frame(current_frame)

    def remove_track_data(self, *args, **kwargs) -> None:
        _log.output(f'remove_track_data1: {args}')
        if not (1 <= len(args) <= 2):
            return
        settings = self.get_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return
        if not geotracker.geomobj or not geotracker.camobj:
            return
        from_frame = args[0]
        to_frame = from_frame if len(args) == 1 else args[1]
        delete_animation_between_frames(geotracker.animatable_object(),
                                        from_frame, to_frame)
        if settings.product_type() == ProductType.FACETRACKER:
            from_frame = max(1, from_frame)
            to_frame = min(bpy_end_frame(), to_frame)
            _log.output(f'remove_track_data: from: {from_frame} to: {to_frame} ')
            for frame in range(from_frame, to_frame + 1):
                remove_relative_shape_keyframe(frame)

    def trackframes(self) -> List[int]:
        _log.output('trackframes call')
        settings = self.get_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return []
        track_frames = get_object_keyframe_numbers(geotracker.animatable_object())
        _log.output(f'trackframes: {track_frames}')
        return track_frames

    def zoom_focal_length_at(self, frame: int) -> float:
        _log.output(f'zoom_focal_length_at: {frame}')
        settings = self.get_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker or not geotracker.camobj:
            _log.output(f'zoom_focal_length_at default: '
                        f'{geotracker.default_zoom_focal_length}')
            return geotracker.default_zoom_focal_length
        return focal_mm_to_px(
            get_safe_evaluated_fcurve(geotracker.camobj.data, frame, 'lens'),
            *bpy_render_frame(), camera_sensor_width(geotracker.camobj))

    def get_default_zoom_focal_length(self) -> float:
        _log.output('get_default_zoom_focal_length')
        settings = self.get_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return focal_mm_to_px(50.0, *bpy_render_frame())  # Undefined case
        return focal_mm_to_px(geotracker.default_zoom_focal_length,
                              *bpy_render_frame(),
                              camera_sensor_width(geotracker.camobj))

    def set_default_zoom_focal_length(self, default_fl: float) -> None:
        _log.output(f'set_default_zoom_focal_length: {default_fl}')
        settings = self.get_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return
        geotracker.default_zoom_focal_length = default_fl

    def set_zoom_focal_length_mode(self, default_fl: float) -> None:
        _log.output('set_zoom_focal_length_mode call')
        self.set_default_zoom_focal_length(default_fl)
        self._set_fl_mode(pkt_module().TrackerFocalLengthMode.ZOOM_FOCAL_LENGTH)

    def set_static_focal_length(self, static_fl: float) -> None:
        _log.output(f'set_static_focal_length: {static_fl}')
        self._set_static_fl(static_fl)

    def set_static_focal_length_mode(self, static_fl: float) -> None:
        _log.output(f'set_static_focal_length_mode: {static_fl}')
        self._set_fl_mode(pkt_module().TrackerFocalLengthMode.STATIC_FOCAL_LENGTH)
        self._set_static_fl(static_fl)

    def static_focal_length(self) -> float:
        settings = self.get_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return focal_mm_to_px(50.0, *bpy_render_frame())  # Undefined case
        return geotracker.static_focal_length

    def set_camera_focal_length_mode(self) -> None:
        _log.output('set_camera_focal_length_mode')
        self._set_fl_mode(pkt_module().TrackerFocalLengthMode.CAMERA_FOCAL_LENGTH)

    def focal_length_mode(self) -> Any:
        settings = self.get_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return pkt_module().TrackerFocalLengthMode.CAMERA_FOCAL_LENGTH
        return self._mode_by_value(geotracker.focal_length_mode)

    def set_zoom_focal_length_at(self, frame: int, fl: float) -> None:
        _log.output('set_zoom_focal_length_at')
        settings = self.get_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker or not geotracker.camobj:
            return
        cam_data = geotracker.camobj.data
        if geotracker.focal_length_mode == 'ZOOM_FOCAL_LENGTH':
            insert_keyframe_in_fcurve(cam_data, frame,
                                      focal_px_to_mm(fl, *bpy_render_frame(),
                                                     cam_data.sensor_width),
                                      'KEYFRAME', 'lens')
        else:
            cam_data.lens = focal_px_to_mm(fl, *bpy_render_frame(),
                                           cam_data.sensor_width)

    def reset(self) -> None:
        _log.output('gt reset call')
