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

from typing import Optional, List, Set, Dict

import bpy
from bpy.types import Object, Action, FCurve, Keyframe
from mathutils import Vector, Matrix
from .bpy_common import (bpy_current_frame,
                         bpy_start_frame,
                         bpy_end_frame,
                         bpy_set_current_frame,
                         create_empty_object,
                         operator_with_context,
                         update_depsgraph,
                         bpy_new_action,
                         bpy_remove_action)

from .fcurve_operations import *
from .kt_logging import KTLogger


_log = KTLogger(__name__)


def count_fcurve_points(obj: Object, data_path: str, index: int = 0) -> int:
    action = get_action(obj)
    if action is None:
        return -1
    fcurve = get_action_fcurve(action, data_path, index=index)
    if not fcurve:
        return -1
    return len(fcurve.keyframe_points)


def remove_fcurve_point(obj: Object, frame: int, data_path: str,
                        index: int = 0, remove_empty_curve: bool = True,
                        remove_empty_action: bool = True) -> None:
    action = get_action(obj)
    if action is None:
        return
    fcurve = get_action_fcurve(action, data_path, index=index)
    if not fcurve:
        return
    points = [p for p in fcurve.keyframe_points if p.co[0] == frame]
    for p in reversed(points):
        fcurve.keyframe_points.remove(p)
    if remove_empty_curve and fcurve.is_empty:
        action.fcurves.remove(fcurve)
    if remove_empty_action and len(action.fcurves) == 0:
        bpy_remove_action(action)


def get_evaluated_fcurve(obj: Object, frame: int, data_path: str,
                         index: int = 0) -> Optional[float]:
    action = get_action(obj)
    if not action:
        return None
    fcurve = get_action_fcurve(action, data_path, index=index)
    if not fcurve:
        return None
    if fcurve.is_empty:
        return None
    return fcurve.evaluate(frame)


def get_safe_evaluated_fcurve(obj: Object, frame: int, data_path: str,
                              index: int = 0) -> float:
    value = get_evaluated_fcurve(obj, frame, data_path, index=index)
    if value is not None:
        return value
    return getattr(obj, data_path)


def _has_action(obj: Object) -> bool:
    return obj.animation_data and obj.animation_data.action


def get_action(obj: Object) -> Optional[Action]:
    if not obj.animation_data:
        return None
    return obj.animation_data.action


def _get_safe_action(obj: Object,
                     action_name: str = 'NewAction') -> Optional[Action]:
    animation_data = obj.animation_data
    if not animation_data:
        animation_data = obj.animation_data_create()
        if not animation_data:
            return None
    if not animation_data.action:
        animation_data.action = bpy_new_action(action_name)
    return animation_data.action


def create_animation_on_object(obj: Object, anim_dict: Dict,
                               action_name: str = 'gtAction') -> None:
    action = _get_safe_action(obj, action_name)
    locrot_dict = get_locrot_dict()

    fcurves = {name: get_safe_action_fcurve(action,
                                            locrot_dict[name]['data_path'],
                                            index=locrot_dict[name]['index'])
               for name in locrot_dict.keys()}

    for name in fcurves.keys():
        clear_fcurve(fcurves[name])
        put_anim_data_in_fcurve(fcurves[name], anim_dict[name])


def create_animated_empty(anim_dict: Dict) -> Object:
    empty_obj = create_empty_object('animatorEmpty')
    create_animation_on_object(empty_obj, anim_dict, 'gtAction')
    return empty_obj


def insert_point_in_fcurve(fcurve: FCurve, frame: int, value: float,
                           keyframe_type: Optional[str] = None) -> Keyframe:
    k = fcurve.keyframe_points.insert(frame, value, options={'NEEDED'})
    if keyframe_type is not None:
        k.type = keyframe_type
    return k


def mark_all_points_in_fcurve(fcurve: FCurve,
                              keyframe_type: str = 'KEYFRAME') -> None:
    for keyframe in fcurve.keyframe_points:
        keyframe.type = keyframe_type


def mark_selected_points_in_fcurve(fcurve: FCurve, selected_frames: List[int],
                                   keyframe_type: str = 'KEYFRAME') -> None:
    selected_set = set(selected_frames)
    selected_points = [x for x in fcurve.keyframe_points
                       if x.co[0] in selected_set]
    for keyframe in selected_points:
        keyframe.type = keyframe_type


def get_loc_dict() -> Dict:
    return {'location_x': {'data_path': 'location', 'index': 0},
            'location_y': {'data_path': 'location', 'index': 1},
            'location_z': {'data_path': 'location', 'index': 2}}


def get_rot_dict() -> Dict:
    return {'rotation_euler_x': {'data_path': 'rotation_euler', 'index': 0},
            'rotation_euler_y': {'data_path': 'rotation_euler', 'index': 1},
            'rotation_euler_z': {'data_path': 'rotation_euler', 'index': 2}}


def get_locrot_dict() -> Dict:
    d = get_loc_dict()
    d.update(get_rot_dict())
    return d


def mark_all_points_in_locrot(obj: Object,
                              keyframe_type: str = 'JITTER') -> None:
    action = get_action(obj)
    if not action:
        return None
    locrot_dict = get_locrot_dict()
    for name in locrot_dict.keys():
        fcurve = get_action_fcurve(action, locrot_dict[name]['data_path'],
                                   index=locrot_dict[name]['index'])
        if fcurve is not None:
            mark_all_points_in_fcurve(fcurve, keyframe_type)


def mark_selected_points_in_locrot(obj: Object, selected_frames: List[int],
                                   keyframe_type: str = 'KEYFRAME') -> None:
    action = get_action(obj)
    if not action:
        return None
    locrot_dict = get_locrot_dict()
    for name in locrot_dict.keys():
        fcurve = get_action_fcurve(action, locrot_dict[name]['data_path'],
                                   index=locrot_dict[name]['index'])
        if fcurve is not None:
            mark_selected_points_in_fcurve(fcurve, selected_frames, keyframe_type)


def get_locrot_keys_in_frame(obj: Object, frame: int) -> Dict:
    res = dict()
    action = get_action(obj)
    if not action:
        return res
    locrot_dict = get_locrot_dict()
    for name in locrot_dict.keys():
        fcurve = get_action_fcurve(action, locrot_dict[name]['data_path'],
                                   index=locrot_dict[name]['index'])
        if fcurve is None:
            continue
        points = [p.co[1] for p in fcurve.keyframe_points if p.co[0] == frame]
        if len(points) != 0:
            res[name] = {'data_path': locrot_dict[name]['data_path'],
                         'index': locrot_dict[name]['index'],
                         'value': points[0]}
    return res


def put_keys_in_frame(obj: Object, frame: int, anim_dict: Dict) -> None:
    if len(anim_dict.keys()) == 0:
        return
    for name in anim_dict.keys():
        row = anim_dict[name]
        insert_keyframe_in_fcurve(obj, frame, row['value'],
                                  keyframe_type='KEYFRAME',
                                  data_path=row['data_path'],
                                  index=row['index'])


def create_animation_locrot_keyframe_force(obj: Object) -> None:
    operator_with_context(bpy.ops.anim.keyframe_insert_menu,
                          {'selected_objects': [obj]},
                          type='BUILTIN_KSI_LocRot')


def insert_keyframe_in_fcurve(obj: Object, frame: int, value: float,
                              keyframe_type: str, data_path: str,
                              index: int = 0, act_name: str = 'GTAct') -> None:
    action = _get_safe_action(obj, act_name)
    if action is None:
        return
    fcurve = get_safe_action_fcurve(action, data_path, index=index)
    insert_point_in_fcurve(fcurve, frame, value, keyframe_type)


def remove_fcurve_from_action(action: Action, data_path: str, index: int = 0,
                              remove_empty_action=True) -> None:
    fcurve = get_action_fcurve(action, data_path, index)
    if fcurve:
        action.fcurves.remove(fcurve)
    if remove_empty_action and len(action.fcurves) == 0:
        bpy_remove_action(action)


def remove_fcurve_from_object(obj: Object, data_path: str, index: int = 0,
                              remove_empty_action=True) -> None:
    action = get_action(obj)
    if action is None:
        return
    remove_fcurve_from_action(action, data_path, index, remove_empty_action)


def create_locrot_keyframe(obj: Object, keyframe_type: str = 'KEYFRAME') -> None:
    action = _get_safe_action(obj, 'GTAct')
    if action is None:
        return
    locrot_dict = get_locrot_dict()
    current_frame = bpy_current_frame()

    mat = obj.matrix_basis
    loc = mat.to_translation()
    rot = mat.to_euler()

    _log.output(f'{keyframe_type} at {current_frame}')
    for name, value in zip(locrot_dict.keys(), [*loc, *rot]):
        fcurve = get_safe_action_fcurve(action, locrot_dict[name]['data_path'],
                                        index=locrot_dict[name]['index'])
        insert_point_in_fcurve(fcurve, current_frame, value, keyframe_type)


def delete_locrot_keyframe(obj: Object) -> None:
    operator_with_context(bpy.ops.anim.keyframe_delete_by_name,
                          {'selected_objects': [obj]},
                          type='BUILTIN_KSI_LocRot')


def reset_object_action(obj: Object) -> None:
    animation_data = obj.animation_data
    if not animation_data:
        return
    act = animation_data.action
    animation_data.action = None
    animation_data.action = act


def delete_animation_between_frames(obj: Object, from_frame: int, to_frame: int) -> None:
    action = get_action(obj)
    if action is None:
        return

    locrot_dict = get_locrot_dict()
    for name in locrot_dict.keys():
        fcurve = get_action_fcurve(action, locrot_dict[name]['data_path'],
                                    index=locrot_dict[name]['index'])
        if fcurve is None:
            continue
        points = [p for p in fcurve.keyframe_points
                  if from_frame <= p.co[0] <= to_frame]
        for p in reversed(points):
            fcurve.keyframe_points.remove(p)


def get_object_keyframe_numbers(obj: Object, *, loc: bool = True,
                                rot: bool = True) -> List[int]:
    if not obj:
        return []
    action: Action = get_action(obj)
    if action is None:
        return []

    if loc and rot:
        fcurve_dict = get_locrot_dict()
    elif loc:
        fcurve_dict = get_loc_dict()
    elif rot:
        fcurve_dict = get_rot_dict()
    else:
        assert False, 'Improper flag usage'

    fcurves: Dict = {name: get_safe_action_fcurve(action,
                                                  fcurve_dict[name]['data_path'],
                                                  index=fcurve_dict[name]['index'])
                     for name in fcurve_dict.keys()}

    keys_set: Set = set()
    for name in fcurves.keys():
        points: Set = {int(p.co[0]) for p in fcurves[name].keyframe_points}
        keys_set = keys_set.union(points)

    return sorted(keys_set)


def get_world_matrices_in_frames(obj: Object,
                                 frame_list: List[int]) -> Dict[int, Matrix]:
    all_matrices = {}
    current_frame = bpy_current_frame()
    for frame in frame_list:
        bpy_set_current_frame(frame)
        all_matrices[frame] = obj.matrix_world.copy()
    bpy_set_current_frame(current_frame)
    return all_matrices


def apply_world_matrices_in_frames(obj: Object,
                                   matrices: Dict[int, Matrix]) -> None:
    current_frame = bpy_current_frame()
    for frame in matrices:
        bpy_set_current_frame(frame)
        obj.matrix_world = matrices[frame]
        update_depsgraph()
        create_animation_locrot_keyframe_force(obj)
    bpy_set_current_frame(current_frame)


def bake_locrot_to_world(obj: Object, bake_frames: List[int]) -> None:
    obj_matrix_world = obj.matrix_world.copy()
    all_matrices = get_world_matrices_in_frames(obj, bake_frames)
    obj.parent = None
    apply_world_matrices_in_frames(obj, all_matrices)
    obj.matrix_world = obj_matrix_world


def scene_frame_list() -> List[int]:
    return [x for x in range(bpy_start_frame(), bpy_end_frame() + 1)]
