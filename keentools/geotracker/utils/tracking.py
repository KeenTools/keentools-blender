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

import os
from typing import Tuple, Optional, Any, List
from math import pi

from bpy.types import Object

from ...utils.kt_logging import KTLogger
from ...utils.bpy_common import bpy_render_frame, update_depsgraph
from ...blender_independent_packages.pykeentools_loader import module as pkt_module
from ..ui_strings import PrecalcStatusMessage
from ...utils.animation import (get_action,
                                get_safe_evaluated_fcurve,
                                get_safe_action_fcurve,
                                insert_point_in_fcurve,
                                get_object_keyframe_numbers,
                                get_rot_dict,
                                get_action_fcurve,
                                get_fcurve_data)


_log = KTLogger(__name__)


def get_precalc_info(precalc_path: str) -> Tuple[Optional[Any], str]:
    try:
        loader = pkt_module().precalc.Loader(precalc_path)
        precalc_info = loader.load_info()
        if precalc_info.image_w <= 0 or precalc_info.image_h <= 0:
            msg = 'Wrong precalc image size'
            _log.error(msg)
            return None, msg
        left = precalc_info.left_precalculated_frame
        right = precalc_info.right_precalculated_frame
        if not isinstance(left, int) or not isinstance(right, int):
            msg = 'Problem with frame indices'
            _log.error(msg)
            return None, msg
        if left < 0 or right < 0 or right < left:
            msg = 'Wrong frame indices'
            _log.error(msg)
            return None, msg
    except pkt_module().precalc.PrecalcLoadingException as err:
        msg = f'get_precalc_info. Precalc is damaged:\n{str(err)}'
        _log.error(msg)
        return None, msg
    except Exception as err:
        msg = f'get_precalc_info: {str(err)}'
        _log.error(msg)
        return None, msg
    return precalc_info, 'ok'


def get_precalc_message(precalc_info: Any) -> str:
    return f'Frame size: {precalc_info.image_w}x{precalc_info.image_h}\n' \
           f'Frames from: {precalc_info.left_precalculated_frame} ' \
           f'to {precalc_info.right_precalculated_frame}'


def check_precalc(precalc_info: Any,
                  frame_from: Optional[int]=None,
                  frame_to: Optional[int]=None) -> Tuple[bool, str]:
    left = precalc_info.left_precalculated_frame
    right = precalc_info.right_precalculated_frame
    if frame_from is not None and frame_to is not None:
        if (not left <= frame_from <= right) or \
                (not left <= frame_to <= right):
            msg = 'Frames are not in precalculated range'
            _log.error(msg)
            return False, msg

    rw, rh = bpy_render_frame()
    if rw != precalc_info.image_w or rh != precalc_info.image_h:
        msg = 'Render size differs from precalculated'
        _log.error(msg)
        return False, msg

    return True, 'ok'


def reload_precalc(geotracker: Any) -> Tuple[bool, str, Any]:
    precalc_path = geotracker.precalc_path
    if os.path.exists(precalc_path):
        precalc_info, msg = get_precalc_info(precalc_path)
        if precalc_info is None:
            geotracker.precalc_message = PrecalcStatusMessage.broken_file
            return False, 'Warning! Precalc file seems corrupted', None
        try:
            geotracker.precalc_message = get_precalc_message(precalc_info)
            geotracker.precalc_start = precalc_info.left_precalculated_frame
            geotracker.precalc_end = precalc_info.right_precalculated_frame
            _log.debug(f'precalc: {geotracker.precalc_start} '
                       f'{geotracker.precalc_end}')
        except Exception as err:
            _log.error(f'reload_precalc Exception:\n{str(err)}')
            return False, 'Precalc file exception', None
        return True, 'ok', precalc_info

    geotracker.precalc_message = PrecalcStatusMessage.missing_file
    return False, 'Precalc file has not been created yet', None


def get_next_tracking_keyframe(kt_geotracker: Any, current_frame: int) -> int:
    keyframes = kt_geotracker.keyframes()
    next_keyframes = [x for x in filter(lambda i: i > current_frame, keyframes)]
    if len(next_keyframes) > 0:
        return next_keyframes[0]
    else:
        return current_frame


def get_previous_tracking_keyframe(kt_geotracker: Any, current_frame: int) -> int:
    keyframes = kt_geotracker.keyframes()
    prev_keyframes = [x for x in filter(lambda i: i < current_frame, keyframes)]
    if len(prev_keyframes) > 0:
        return prev_keyframes[-1]
    else:
        return current_frame


def unbreak_rotation(obj: Object, frame_list: List[int]) -> bool:
    if len(frame_list) < 2:
        return False

    action = get_action(obj)
    if action is None:
        return False

    euler_list = list()
    for frame in frame_list:
        x_rot = get_safe_evaluated_fcurve(obj, frame, 'rotation_euler', 0)
        y_rot = get_safe_evaluated_fcurve(obj, frame, 'rotation_euler', 1)
        z_rot = get_safe_evaluated_fcurve(obj, frame, 'rotation_euler', 2)
        euler_list.append((x_rot, y_rot, z_rot))

    x_rot_fcurve = get_safe_action_fcurve(action, 'rotation_euler', 0)
    y_rot_fcurve = get_safe_action_fcurve(action, 'rotation_euler', 1)
    z_rot_fcurve = get_safe_action_fcurve(action, 'rotation_euler', 2)

    euler_prev = euler_list[0]
    for frame, euler_current in zip(frame_list[1:], euler_list[1:]):
        rot = pkt_module().math.unbreak_rotation(euler_prev,
                                                 euler_current)
        insert_point_in_fcurve(x_rot_fcurve, frame, rot[0])
        insert_point_in_fcurve(y_rot_fcurve, frame, rot[1])
        insert_point_in_fcurve(z_rot_fcurve, frame, rot[2])
        euler_prev = rot

    update_depsgraph()
    return True


def check_unbreak_rotaion_is_needed(obj: Object) -> bool:
    if not obj:
        return False

    frame_list = get_object_keyframe_numbers(obj, loc=False, rot=True)
    if len(frame_list) < 2:
        return False

    action = get_action(obj)
    if action is None:
        return False

    rot_dict = get_rot_dict()

    for name in rot_dict:
        fcurve = get_action_fcurve(action, rot_dict[name]['data_path'],
                                   index=rot_dict[name]['index'])
        if not fcurve:
            continue

        points = get_fcurve_data(fcurve)
        if len(points) < 2:
            continue

        points.sort(key = lambda x: x[0])
        prev = points[0][1]
        for point in points[1:]:
            if abs(prev - point[1]) > pi:
                return True
            prev = point[1]

    return False
