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

import numpy as np
import re
from typing import Any, Set, Tuple, List, Optional

from bpy.types import Area, Object

from ..utils.kt_logging import KTLogger
from ..addon_config import ft_settings
from ..facetracker_config import FTConfig
from ..utils.bpy_common import (bpy_new_action,
                                bpy_shape_key_move_top,
                                bpy_shape_key_move_up,
                                bpy_shape_key_move_bottom)
from ..utils.coords import xy_to_xz_rotation_matrix_3x3
from ..utils.blendshapes import get_blendshape
from ..utils.fcurve_operations import (get_safe_action_fcurve,
                                       get_action_fcurve,
                                       clear_fcurve)


_log = KTLogger(__name__)


tracking_frame_name_pattern: Any = re.compile(r'frame_(\d+)$', 0)


def get_prev_frame_shape(key_blocks, shape_index) -> Tuple[int, int]:
    '''
    :return: shape_index, frame_number
    '''
    if shape_index == -1:
        return -1, -1
    for i in range(shape_index - 1, 0, -1):
        res = tracking_frame_name_pattern.match(key_blocks[i].name)
        if res:
            return i, int(res[1])
    return -1, -1


def get_next_frame_shape(key_blocks, shape_index) -> Tuple[int, int]:
    '''
    :return: shape_index, frame_number
    '''
    if shape_index == -1:
        return -1, -1
    for i in range(shape_index + 1, len(key_blocks)):
        res = tracking_frame_name_pattern.match(key_blocks[i].name)
        if res:
            return i, int(res[1])
    return -1, -1


def check_tracking_frames(key_blocks) -> Tuple[bool, Any]:
    count = len(key_blocks)
    check_status = True
    non_tracking_shape_flag = False
    arr = np.empty(shape=(count, 2), dtype=np.int32)
    frame = -1
    for i in range(count - 1, -1, -1):
        res = tracking_frame_name_pattern.match(key_blocks[i].name)
        if not res:
            arr[i] = (i, -1)
            non_tracking_shape_flag = True
        else:
            current_frame = int(res[1])
            if 0 <= frame <= current_frame:
                check_status = False
                if frame == current_frame:
                    _log.error(f'check_tracking_frames: Duplicate frame shape '
                               f'"{key_blocks[i].name}"')
                else:
                    _log.output('check_tracking_frames: wrong frame order')
            arr[i] = (i, current_frame)
            if non_tracking_shape_flag:
                check_status = False
            frame = current_frame
    if frame >= 0 and arr[-1][1] == -1:
        check_status = False
        _log.output('check_tracking_frames: last shape is not tracking')
    return check_status, arr


def reorder_tracking_frames(obj) -> None:
    key_blocks = obj.data.shape_keys.key_blocks
    check_status, arr = check_tracking_frames(key_blocks)
    if check_status:
        _log.output(f'reorder_tracking_frames [no need]')
        return
    pairs = arr[arr[:, 1] >= 0]
    res = pairs[pairs[:, 1].argsort()]
    indices = res[:, 0]
    for i, index in enumerate(indices):
        m = indices[:i]
        offset = (m < index).sum()
        obj.active_shape_key_index = index - offset
        bpy_shape_key_move_bottom(obj)


def check_nearest_frame_sequence(frames: List, key_blocks_count: int) -> bool:
    actual_frames = reversed([x for x in frames if x != -1])
    last_index = key_blocks_count - 1
    for frame in actual_frames:
        if frame != last_index:
            return False
        last_index -= 1
    return True


def make_fcurve_pile_animation(fcurve: Any, frames: List,
                               keyframe_set: Optional[Set] = None) -> None:
    if not fcurve:
        return
    clear_fcurve(fcurve)
    pile = [0.0, 1.0, 0.0]
    anim_data = [x for x in zip(frames, pile) if x[0] != -1]
    fcurve.keyframe_points.add(len(anim_data))
    for i, point in enumerate(anim_data):
        kp = fcurve.keyframe_points[i]
        kp.co = point
        kp.interpolation = 'LINEAR'
        if keyframe_set is None:
            continue
        kp.type = 'KEYFRAME' if point[0] in keyframe_set else 'JITTER'
    fcurve.update()


def get_frame_shape_name(frame: int) -> str:
    return f'frame_{str(frame).zfill(4)}'


def bubble_frame_shape(obj: Object, shape_index: int, frame: int) -> int:
    key_blocks = obj.data.shape_keys.key_blocks
    current_index = shape_index
    for i in range(shape_index - 1, 0, -1):
        prev_index, prev_frame = get_prev_frame_shape(key_blocks, current_index)
        if prev_index == -1 or prev_frame < frame:
            break
        for _ in range(prev_index, current_index):
            bpy_shape_key_move_up(obj)
        current_index = prev_index
    return current_index


def create_relative_shape_keyframe(frame: int, *,
                                   action_name: str = FTConfig.ft_action_name) -> None:
    _log.yellow(f'create_shape_keyframe: {frame}')
    settings = ft_settings()
    loader = settings.loader()
    geotracker = settings.get_current_geotracker_item()
    if not geotracker:
        return

    geomobj = geotracker.geomobj
    if not geomobj:
        return

    mesh = geomobj.data
    mesh.shape_keys.use_relative = True

    basis_index, basis_shape, _ = get_blendshape(geomobj, name='Basis',
                                                 create_basis=True)
    if basis_index != 0:
        geomobj.active_shape_key_index = basis_index
        bpy_shape_key_move_top(geomobj)

    shape_name = get_frame_shape_name(frame)
    shape_index, shape, new_shape_created = get_blendshape(geomobj,
                                                           name=shape_name,
                                                           create=True)
    gt = loader.kt_geotracker()
    verts = gt.applied_args_model_vertices_at(frame)
    shape.data.foreach_set('co', (verts @ xy_to_xz_rotation_matrix_3x3()).ravel())

    geomobj.active_shape_key_index = shape_index
    key_blocks = mesh.shape_keys.key_blocks

    if new_shape_created:
        shape_index = bubble_frame_shape(geomobj, shape_index, frame)
        _log.red(f'bubble_shape: {shape_index}')

    prev_index1, prev_frame1 = get_prev_frame_shape(key_blocks, shape_index)
    next_index1, next_frame1 = get_next_frame_shape(key_blocks, shape_index)
    prev_index2, prev_frame2 = get_prev_frame_shape(key_blocks, prev_index1)
    next_index2, next_frame2 = get_next_frame_shape(key_blocks, next_index1)

    if not check_nearest_frame_sequence([prev_frame2, prev_frame1, frame,
                                         next_frame1, next_frame2],
                                        len(key_blocks)):
        _log.red('check_nearest_frame_sequence is not passed!')
        reorder_tracking_frames(geomobj)
        shape_index, _, _ = get_blendshape(geomobj, name=shape_name)
        prev_index1, prev_frame1 = get_prev_frame_shape(key_blocks, shape_index)
        next_index1, next_frame1 = get_next_frame_shape(key_blocks, shape_index)
        prev_index2, prev_frame2 = get_prev_frame_shape(key_blocks, prev_index1)
        next_index2, next_frame2 = get_next_frame_shape(key_blocks, next_index1)

    anim_data = mesh.shape_keys.animation_data
    if not anim_data:
        anim_data = mesh.shape_keys.animation_data_create()

    action = anim_data.action
    if not action:
        action = bpy_new_action(action_name)
        anim_data.action = action

    keyframe_set = set(gt.keyframes())
    main_fcurve = get_safe_action_fcurve(action,
                                         f'key_blocks["{shape_name}"].value')
    make_fcurve_pile_animation(main_fcurve, [prev_frame1, frame, next_frame1],
                               keyframe_set)
    if prev_index1 != -1:
        prev_fcurve = get_safe_action_fcurve(
            action, f'key_blocks["{key_blocks[prev_index1].name}"].value')
        make_fcurve_pile_animation(prev_fcurve,
                                   [prev_frame2, prev_frame1, frame],
                                   keyframe_set)
    if next_frame1 != -1:
        next_fcurve = get_safe_action_fcurve(
            action, f'key_blocks["{key_blocks[next_index1].name}"].value')
        make_fcurve_pile_animation(next_fcurve,
                                   [frame, next_frame1, next_frame2],
                                   keyframe_set)
    _log.output(f'create_shape_keyframe end >>>')


def remove_relative_shape_keyframe(frame: int) -> None:
    _log.yellow(f'remove_relative_shape_keyframe: {frame}')
    settings = ft_settings()
    geotracker = settings.get_current_geotracker_item()
    if not geotracker:
        return

    geomobj = geotracker.geomobj
    if not geomobj:
        return

    mesh = geomobj.data
    mesh.shape_keys.use_relative = True

    basis_index, basis_shape, _ = get_blendshape(geomobj, name='Basis')
    if basis_index < 0:
        _log.red('remove_relative_shape_keyframe: no Basis')
        return

    if basis_index != 0:
        geomobj.active_shape_key_index = basis_index
        bpy_shape_key_move_top(geomobj)

    shape_name = get_frame_shape_name(frame)
    shape_index, shape, new_shape_created = get_blendshape(geomobj,
                                                           name=shape_name)
    if not shape:
        _log.red(f'remove_relative_shape_keyframe: no shape {shape_name}')
        return

    key_blocks = mesh.shape_keys.key_blocks

    prev_index1, prev_frame1 = get_prev_frame_shape(key_blocks, shape_index)
    next_index1, next_frame1 = get_next_frame_shape(key_blocks, shape_index)
    prev_index2, prev_frame2 = get_prev_frame_shape(key_blocks, prev_index1)
    next_index2, next_frame2 = get_next_frame_shape(key_blocks, next_index1)

    if not check_nearest_frame_sequence([prev_frame2, prev_frame1, frame,
                                         next_frame1, next_frame2],
                                        len(key_blocks)):
        _log.red('check_nearest_frame_sequence is not passed!')
        reorder_tracking_frames(geomobj)
        shape_index, _, _ = get_blendshape(geomobj, name=shape_name)
        prev_index1, prev_frame1 = get_prev_frame_shape(key_blocks, shape_index)
        next_index1, next_frame1 = get_next_frame_shape(key_blocks, shape_index)
        prev_index2, prev_frame2 = get_prev_frame_shape(key_blocks, prev_index1)
        next_index2, next_frame2 = get_next_frame_shape(key_blocks, next_index1)

    anim_data = mesh.shape_keys.animation_data
    if not anim_data:
        return
    action = anim_data.action
    if not action:
        return

    main_fcurve = get_action_fcurve(action, f'key_blocks["{shape_name}"].value')
    if not main_fcurve:
        _log.red('no main_fcurve')
        return

    gt = settings.loader().kt_geotracker()
    keyframe_set = set(gt.keyframes())
    if prev_index1 != -1:
        prev_fcurve = get_action_fcurve(
            action, f'key_blocks["{key_blocks[prev_index1].name}"].value')
        if prev_fcurve:
            make_fcurve_pile_animation(prev_fcurve,
                                       [prev_frame2, prev_frame1, next_frame1],
                                       keyframe_set)
    if next_frame1 != -1:
        next_fcurve = get_action_fcurve(
            action, f'key_blocks["{key_blocks[next_index1].name}"].value')
        if next_fcurve:
            make_fcurve_pile_animation(next_fcurve,
                                       [prev_frame1, next_frame1, next_frame2],
                                       keyframe_set)

    action.fcurves.remove(main_fcurve)
    geomobj.shape_key_remove(shape)
    _log.output(f'remove_relative_shape_keyframe end >>>')
