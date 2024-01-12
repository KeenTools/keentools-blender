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

from typing import Dict, Optional

from bpy.types import Object

from ...utils.kt_logging import KTLogger
from ...addon_config import fb_settings
from ...facebuilder_config import FBConfig
from ...utils import attrs


_log = KTLogger(__name__)


def show_all_cameras(headnum: int) -> None:
    settings = fb_settings()
    head = settings.get_head(headnum)
    if head is None:
        return
    for i, c in enumerate(head.cameras):
        c.camobj.hide_set(False)


def hide_other_cameras(headnum: int, camnum: int) -> None:
    settings = fb_settings()
    head = settings.get_head(headnum)
    if head is None:
        return
    for i, c in enumerate(head.cameras):
        c.camobj.hide_set(i != camnum)


def default_camera_params() -> Dict:
    return {'focal': FBConfig.default_focal_length,
            'sensor_width': FBConfig.default_sensor_width,
            'sensor_height': FBConfig.default_sensor_height,
            'frame_width': FBConfig.default_frame_width,
            'frame_height': FBConfig.default_frame_height}


def get_camera_params(obj: Object) -> Optional[Dict]:
    def _get_data_value(data, attr_name: str) -> Optional[float]:
        return None if attr_name not in data.keys() else data[attr_name]

    data = attrs.get_safe_custom_attribute(obj, FBConfig.fb_camera_prop_name)
    if not data:
        _log.error('NO CAMERA PARAMETERS')
        return None
    try:
        params = {
            'focal': _get_data_value(data, FBConfig.reconstruct_focal_param),
            'sensor_width': _get_data_value(
                data, FBConfig.reconstruct_sensor_width_param),
            'sensor_height': _get_data_value(
                data, FBConfig.reconstruct_sensor_height_param),
            'frame_width': _get_data_value(
                data, FBConfig.reconstruct_frame_width_param),
            'frame_height': _get_data_value(
                data, FBConfig.reconstruct_frame_height_param)}
        _log.info(f'LOADED CAMERA PARAMS: {params}')
        if None in params.values():
            return None
    except Exception as err:
        _log.error(f'get_camera_params: {str(err)}')
        return None
    return params
