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
import logging

from ...facebuilder_config import FBConfig, get_fb_settings
from ...utils import attrs


def show_all_cameras(headnum):
    settings = get_fb_settings()
    head = settings.get_head(headnum)
    if head is None:
        return
    for i, c in enumerate(head.cameras):
        c.camobj.hide_set(False)


def hide_other_cameras(headnum, camnum):
    settings = get_fb_settings()
    head = settings.get_head(headnum)
    if head is None:
        return
    for i, c in enumerate(head.cameras):
        c.camobj.hide_set(i != camnum)


def default_camera_params():
    return {'focal': FBConfig.default_focal_length,
            'sensor_width': FBConfig.default_sensor_width,
            'sensor_height': FBConfig.default_sensor_height,
            'frame_width': FBConfig.default_frame_width,
            'frame_height': FBConfig.default_frame_height}


def get_camera_params(obj):
    def _get_data_value(data, attr_name):
        return None if attr_name not in data.keys() else data[attr_name]

    logger = logging.getLogger(__name__)
    data = attrs.get_safe_custom_attribute(obj, FBConfig.fb_camera_prop_name)
    if not data:
        logger.error('NO CAMERA PARAMETERS')
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
        logger.info('LOADED CAMERA PARAMS: {}'.format(params))
        if None in params.values():
            return None
    except Exception as err:
        logger.error('get_camera_params: {}'.format(str(err)))
        return None
    return params
