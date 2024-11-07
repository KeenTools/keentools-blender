# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2019-2023  KeenTools

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

from typing import Any, Tuple

from ..utils.kt_logging import KTLogger
from ..addon_config import ft_settings, ProductType, ActionStatus
from ..utils.bpy_common import bpy_current_frame
from ..tracker.loader import Loader
from ..tracker.class_loader import KTClassLoader
from ..facetracker.viewport import FTViewport
from ..utils.fb_wireframe_image import create_wireframe_image
from ..utils.ui_redraw import force_ui_redraw


_log = KTLogger(__name__)


class FTLoader(Loader):
    _viewport: Any = FTViewport()

    @classmethod
    def product_type(cls):
        return ProductType.FACETRACKER

    @classmethod
    def get_settings(cls) -> Any:
        return ft_settings()

    @classmethod
    def get_geo(cls) -> Any:
        gt = cls.kt_geotracker()
        geo = gt.applied_args_model_at(bpy_current_frame())
        return geo

    @classmethod
    def new_kt_geotracker(cls) -> Any:
        _log.magenta('*** new_kt_facetracker ***')
        cls._geo_input = KTClassLoader.FTGeoInput_class()()
        cls._image_input = KTClassLoader.FTImageInput_class()()
        cls._camera_input = KTClassLoader.FTCameraInput_class()()
        cls._mask2d = KTClassLoader.FTMask2DInput_class()()
        cls._storage = KTClassLoader.FTGeoTrackerResultsStorage_class()()

        cls._kt_geotracker = KTClassLoader.FaceTracker_class()(
            cls._geo_input,
            cls._camera_input,
            cls._image_input,
            cls._mask2d,
            cls._storage
        )
        return cls._kt_geotracker

    @classmethod
    def start_viewport(cls, *, area: Any,
                       texture_colors: Tuple = ((0., 1., 1.),
                                                (1., 0., 1.),
                                                (1., 1., 0.))) -> ActionStatus:
        _log.green(f'{cls.__name__}.start_viewport start')
        vp = cls.viewport()
        if not vp.load_all_shaders():
            msg = 'Problem with loading shaders (see console)'
            _log.error(msg)
            _log.output(f'{cls.__name__}.start_viewport loading shaders error >>>')
            return ActionStatus(False, msg)

        create_wireframe_image(list(texture_colors))
        vp.register_handlers(area=area)
        vp.unhide_all_shaders()
        vp.tag_redraw()
        force_ui_redraw('DOPESHEET_EDITOR')
        _log.output(f'{cls.__name__}.start_viewport end >>>')
        return ActionStatus(True, 'ok')

    @classmethod
    def _deserialize_global_options(cls):
        _log.yellow(f'ft _deserialize_global_options start')
        settings = cls.get_settings()
        geotracker = settings.get_current_geotracker_item()
        gt = cls.kt_geotracker()
        with settings.ui_write_mode_context():
            try:
                _log.output('viewport parameters')
                settings.wireframe_backface_culling = gt.back_face_culling()
                settings.track_focal_length = gt.track_focal_length()
                _log.output('coefficients')
                geotracker.smoothing_depth_coeff = gt.get_smoothing_depth_coeff()
                geotracker.smoothing_focal_length_coeff = gt.get_smoothing_focal_length_coeff()
                geotracker.smoothing_rotations_coeff = gt.get_smoothing_rotations_coeff()
                geotracker.smoothing_xy_translations_coeff = gt.get_smoothing_xy_translations_coeff()
                geotracker.smoothing_face_args_coeff = gt.get_smoothing_face_args_coeff()
                _log.output('locks')
                geotracker.locks = gt.fixed_dofs()

                _log.output('lock_blinking')
                geotracker.lock_blinking = gt.blinking_locked()
                _log.output('lock_neck_movement')
                geotracker.lock_neck_movement = gt.neck_movement_locked()
                _log.output('rigidity')
                geotracker.rigidity = gt.rigidity()
                _log.output('blinking_rigidity')
                geotracker.blinking_rigidity = gt.blinking_rigidity()
                _log.output('neck_movement_rigidity')
                geotracker.neck_movement_rigidity = gt.neck_movement_rigidity()
            except Exception as err:
                _log.error(f'ft _deserialize_global_options:\n{str(err)}')
        _log.output('ft _deserialize_global_options end >>>')

FTLoader.init_handlers()
