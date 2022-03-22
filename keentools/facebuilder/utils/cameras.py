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
import math

import bpy

from ...addon_config import Config
from ..config import FBConfig
from ..config import get_fb_settings
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


def get_camera_background(camera):
    camobj = camera.camobj
    c = camobj.data
    if len(c.background_images) == 0:
        return None
    else:
        return c.background_images[0]


def reset_background_image_rotation(camera):
    background_image = get_camera_background(camera)
    if background_image is None:
        return
    background_image.rotation = 0
    camera.orientation = 0


def rotate_background_image(camera, delta=1):
    background_image = get_camera_background(camera)
    if background_image is None:
        return

    camera.orientation += delta
    if camera.orientation < 0:
        camera.orientation += 4
    if camera.orientation >= 4:
        camera.orientation += -4
    background_image.rotation = camera.orientation * math.pi / 2


def exit_localview(context):
    if context.space_data and context.space_data.local_view:
        bpy.ops.view3d.localview()
        return True
    return False


def enter_localview(context):
    if not context.space_data.local_view:
        bpy.ops.view3d.localview()


def switch_to_fb_camera(camera, context):
    camera.show_background_image()
    exit_localview(context)
    camera.camobj.hide_set(False)

    bpy.ops.object.select_all(action='DESELECT')
    camera.camobj.select_set(state=True)
    bpy.context.view_layer.objects.active = camera.camobj

    enter_localview(context)
    bpy.ops.view3d.object_as_camera()


def leave_camera_view(context):
    try:
        if context.space_data.region_3d.view_perspective == 'CAMERA':
            bpy.ops.view3d.view_camera()
    except Exception as err:
        pass
