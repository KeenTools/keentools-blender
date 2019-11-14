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
import bpy

from .. config import get_main_settings, Config
from . import attrs
from . fake_context import get_override_context


def show_all_cameras(headnum):
    settings = get_main_settings()
    head = settings.get_head(headnum)
    for i, c in enumerate(head.cameras):
        # Unhide camera
        c.camobj.hide_set(False)


def hide_other_cameras(headnum, camnum):
    settings = get_main_settings()
    head = settings.get_head(headnum)
    for i, c in enumerate(head.cameras):
        if i != camnum:
            # Hide camera
            c.camobj.hide_set(True)


def switch_to_camera(camobj):
    """ Switch to camera context independently"""
    scene = bpy.context.scene
    settings = get_main_settings()

    camobj.select_set(state=True)
    bpy.context.view_layer.objects.active = camobj

    # Switch to camera
    if (scene.camera == camobj) and settings.pinmode:
        if not bpy.app.background:
            bpy.ops.view3d.view_camera()
        else:
            override = get_override_context()
            bpy.ops.view3d.view_camera(override)
    else:
        camobj.hide_set(False)  # To allow switch
        if not bpy.app.background:
            bpy.ops.view3d.object_as_camera()
        else:
            override = get_override_context()
            bpy.ops.view3d.object_as_camera(override)


def get_camera_params(obj):
    logger = logging.getLogger(__name__)
    # Init camera parameters
    data = attrs.get_safe_custom_attribute(
        obj, Config.fb_camera_prop_name[0])
    if not data:
        return None
    try:
        params = {'focal': attrs.get_attr_variant_named(
            data, Config.reconstruct_focal_param),
            'sensor_width': attrs.get_attr_variant_named(
                data, Config.reconstruct_sensor_width_param),
            'sensor_height': attrs.get_attr_variant_named(
                data, Config.reconstruct_sensor_width_param),
            'frame_width': attrs.get_attr_variant_named(
                data, Config.reconstruct_frame_width_param),
            'frame_height': attrs.get_attr_variant_named(
                data, Config.reconstruct_frame_height_param)}
        logger.debug("LOADED PARAMS {}".format(params))
        if None in params.values():
            return None
    except Exception:
        return None
    return params
