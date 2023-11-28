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
from typing import Any, Tuple, List, Dict, Optional
from math import frexp

from bpy.types import Object

from ..addon_config import Config
from ..utils.kt_logging import KTLogger
from ..geotracker_config import get_gt_settings, get_current_geotracker_item
from ..utils.coords import (focal_mm_to_px,
                            focal_px_to_mm,
                            camera_sensor_width,
                            calc_bpy_camera_mat_relative_to_model,
                            calc_bpy_model_mat_relative_to_camera,
                            camera_projection,
                            xy_to_xz_rotation_matrix_3x3)
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
                                bpy_shape_key_retime,
                                get_traceback)
from ..blender_independent_packages.pykeentools_loader import module as pkt_module
from ..geotracker.gtloader import GTLoader
from ..utils.images import (np_array_from_background_image,
                            np_threshold_image,
                            np_threshold_image_with_channels,
                            np_array_from_bpy_image)
from ..utils.ui_redraw import total_redraw_ui
from ..utils.mesh_builder import build_geo, build_geo_from_basis


_log = KTLogger(__name__)


class GTCameraInput(pkt_module().TrackerCameraInputI):
    def projection(self, frame: int) -> Any:
        geotracker = get_current_geotracker_item()
        if not geotracker or not geotracker.camobj:
            _log.output('projection error: no geotracker or camera')
            return np.eye(4)
        return camera_projection(geotracker.camobj, frame)

    def view(self, keyframe: int) -> Any:
        return np.eye(4)

    def image_size(self) -> Tuple[int, int]:
        return bpy_render_frame()


class GTGeoInput(pkt_module().GeoInputI):
    _previous_val: int = 0
    _hash_counter: int = 0
    _geo_changed: bool = True

    @classmethod
    def set_geo_changed(cls, value: bool = True):
        cls._geo_changed = value

    @classmethod
    def increment_hash(cls) -> None:
        cls._hash_counter += 1
        if cls._hash_counter > 1000:
            cls._hash_counter = 0

    @classmethod
    def get_hash_counter(cls) -> int:
        return cls._hash_counter

    @classmethod
    def _set_previous_val(cls, val) -> None:
        cls._previous_val = val

    def _rounded(self, val: float) -> int:
        p = frexp(val)
        return int(round(p[0] * 10000, 0) + 3 * p[1])

    def geo_hash(self) -> Any:
        _log.output(_log.color('magenta', 'get geo_hash'))

        if not self._geo_changed:
            return pkt_module().Hash(self._previous_val)

        settings = get_gt_settings()

        if self._previous_val != 0 and settings.is_calculating():
            return pkt_module().Hash(self._previous_val)

        _log.output('geo_hash calculating')
        self.set_geo_changed(False)

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
        if val != self._previous_val:
            _log.output(_log.color('magenta', 'geo_hash changed'))
            self._set_previous_val(val)
        return pkt_module().Hash(val)

    def geo(self) -> Any:
        geotracker = get_current_geotracker_item()
        if not geotracker:
            return None
        if Config.test_facetracker:  # build_geo_from_basis
            return build_geo_from_basis(geotracker.geomobj, get_uv=False)
        return build_geo(geotracker.geomobj, get_uv=False)


class GTImageInput(pkt_module().ImageInputI):
    def image_hash(self, frame: int) -> Any:
        return pkt_module().Hash(frame)

    def load_linear_rgb_image_at(self, frame: int) -> Any:
        def _empty_image():
            w, h = bpy_render_frame()
            return np.full((h, w, 3), (0.0, 0.0, 0.0), dtype=np.float32)

        _log.output(_log.color('magenta', f'load_linear_rgb_image_at: {frame}'))
        settings = get_gt_settings()
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


class GTMask2DInput(pkt_module().Mask2DInputI):
    def load_image_2d_mask_at(self, frame: int) -> Any:
        settings = get_gt_settings()
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
        geotracker = get_current_geotracker_item()
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
        geotracker = get_current_geotracker_item()
        mask_source = geotracker.get_2d_mask_source()
        if mask_source == 'COMP_MASK':
            return self.load_compositing_2d_mask_at(frame)
        elif mask_source == 'MASK_2D':
            return self.load_image_2d_mask_at(frame)
        return None


def get_blendshape(obj: Object, name: str = '', *,
                   create_basis: bool = False,
                   create: bool = False) -> Tuple[int, Optional[Any]]:
    if not obj.data.shape_keys:
        if create_basis:
            basis = obj.shape_key_add('Basis')
            if name == 'Basis':
                return 0, basis
        else:
            return -1, None

    index = obj.data.shape_keys.key_blocks.find(name)
    if index < 0:
        if not create:
            return -1, None
        shape = obj.shape_key_add(name)
        index = obj.data.shape_keys.key_blocks.find(name)
    else:
        shape = obj.data.shape_keys.key_blocks[index]

    return index, shape


def create_shape_keyframe(frame: int, keyframe_type: str = 'JITTER') -> None:
    _log.output(_log.color('yellow', f'create_shape_keyframe: {frame}'))
    geotracker = get_current_geotracker_item()
    gt = GTLoader.kt_geotracker()
    geomobj = geotracker.geomobj
    mesh = geomobj.data
    shape_name = f'frame_{str(frame).zfill(4)}'

    if not mesh.shape_keys:
        geomobj.shape_key_add(name='Basis')

    mesh.shape_keys.use_relative = False

    anim_data = mesh.shape_keys.animation_data
    if not anim_data:
        anim_data = mesh.shape_keys.animation_data_create()

    action = anim_data.action
    if not action:
        import bpy
        action = bpy.data.actions.new('ftAction')
        anim_data.action = action

    fcurve = action.fcurves.find('eval_time')
    if not fcurve:
        fcurve = action.fcurves.new('eval_time', index=0)

    kb_names = [kb.name for kb in mesh.shape_keys.key_blocks]
    if shape_name not in kb_names:
        shape = geomobj.shape_key_add(name=shape_name)
        shape.interpolation = 'KEY_LINEAR'
        bpy_shape_key_retime(geomobj)
    else:
        shape = mesh.shape_keys.key_blocks[shape_name]

    res = [(int(kb.name[6:]) if kb.name[:6] == 'frame_' else -1, kb.frame) for
           kb in mesh.shape_keys.key_blocks[1:]]
    anim_points = np.array(res, dtype=np.float32)
    _log.output(f'anim_points:\n{anim_points}')

    fcurve.keyframe_points.clear()
    fcurve.keyframe_points.add(len(res))
    fcurve.keyframe_points.foreach_set('co', anim_points.ravel())
    for p in fcurve.keyframe_points:
        p.interpolation = 'LINEAR'
        p.type = keyframe_type

    verts = gt.applied_args_model_vertices_at(frame)
    shape.data.foreach_set('co', (verts @ xy_to_xz_rotation_matrix_3x3()).ravel())


class GTGeoTrackerResultsStorage(pkt_module().GeoTrackerResultsStorageI):
    def __init__(self):
        super().__init__()
        fl_mode = pkt_module().TrackerFocalLengthMode
        self._modes: Dict = {
            mode.name: mode for mode in [
            fl_mode.CAMERA_FOCAL_LENGTH,
            fl_mode.STATIC_FOCAL_LENGTH,
            fl_mode.ZOOM_FOCAL_LENGTH
        ]}

    def _mode_by_value(self, value: str) -> Any:
        if value in self._modes.keys():
            return self._modes[value]
        return pkt_module().TrackerFocalLengthMode.CAMERA_FOCAL_LENGTH

    def _set_fl_mode(self, enum_value) -> None:
        geotracker = get_current_geotracker_item()
        if not geotracker:
            return
        geotracker.focal_length_mode = enum_value.name

    def _set_static_fl(self, static_fl: float) -> None:
        _log.output(f'_set_static_fl: {static_fl}')
        geotracker = get_current_geotracker_item()
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
        settings = get_gt_settings()
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
        _log.output(_log.color('yellow', f'set_model_mat_at1: {frame}'))
        settings = get_gt_settings()
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

        gt = GTLoader.kt_geotracker()
        keyframe_type = 'KEYFRAME' if gt.is_key_at(frame) else 'JITTER'
        create_locrot_keyframe(geotracker.animatable_object(), keyframe_type)
        if (current_frame != frame) and not settings.is_calculating():
            bpy_set_current_frame(current_frame)

    def remove_track_data(self, *args, **kwargs) -> None:
        _log.output(f'remove_track_data1: {args}')
        if not (1 <= len(args) <= 2):
            return
        geotracker = get_current_geotracker_item()
        if not geotracker:
            return
        if not geotracker.geomobj or not geotracker.camobj:
            return
        from_frame = args[0]
        to_frame = from_frame if len(args) == 1 else args[1]
        delete_animation_between_frames(geotracker.animatable_object(),
                                        from_frame, to_frame)

    def trackframes(self) -> List[int]:
        _log.output('trackframes call')
        geotracker = get_current_geotracker_item()
        if not geotracker:
            return []
        track_frames = get_object_keyframe_numbers(geotracker.animatable_object())
        _log.output(f'trackframes: {track_frames}')
        return track_frames

    def zoom_focal_length_at(self, frame: int) -> float:
        _log.output(f'zoom_focal_length_at: {frame}')
        geotracker = get_current_geotracker_item()
        if not geotracker or not geotracker.camobj:
            _log.output(f'zoom_focal_length_at default: '
                        f'{geotracker.default_zoom_focal_length}')
            return geotracker.default_zoom_focal_length
        return focal_mm_to_px(
            get_safe_evaluated_fcurve(geotracker.camobj.data, frame, 'lens'),
            *bpy_render_frame(), camera_sensor_width(geotracker.camobj))

    def get_default_zoom_focal_length(self) -> float:
        _log.output('get_default_zoom_focal_length')
        geotracker = get_current_geotracker_item()
        if not geotracker:
            return focal_mm_to_px(50.0, *bpy_render_frame())  # Undefined case
        return focal_mm_to_px(geotracker.default_zoom_focal_length,
                              *bpy_render_frame(),
                              camera_sensor_width(geotracker.camobj))

    def set_default_zoom_focal_length(self, default_fl: float) -> None:
        _log.output(f'set_default_zoom_focal_length: {default_fl}')
        geotracker = get_current_geotracker_item()
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
        geotracker = get_current_geotracker_item()
        if not geotracker:
            return focal_mm_to_px(50.0, *bpy_render_frame())  # Undefined case
        return geotracker.static_focal_length

    def set_camera_focal_length_mode(self) -> None:
        _log.output('set_camera_focal_length_mode')
        self._set_fl_mode(pkt_module().TrackerFocalLengthMode.CAMERA_FOCAL_LENGTH)

    def focal_length_mode(self) -> Any:
        geotracker = get_current_geotracker_item()
        if not geotracker:
            return pkt_module().TrackerFocalLengthMode.CAMERA_FOCAL_LENGTH
        return self._mode_by_value(geotracker.focal_length_mode)

    def set_zoom_focal_length_at(self, frame: int, fl: float) -> None:
        _log.output('set_zoom_focal_length_at')
        geotracker = get_current_geotracker_item()
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
