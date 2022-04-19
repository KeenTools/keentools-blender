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

from typing import Optional
import bpy
from bpy.types import Object, Action, FCurve, Keyframe
from mathutils import Vector

from ...geotracker_config import get_gt_settings


def extend_scene_timeline_end(keyframe_num: int) -> None:
    scene = bpy.context.scene
    if scene.frame_end < keyframe_num:
        scene.frame_end = keyframe_num


def extend_scene_timeline_start(keyframe_num: int) -> None:
    scene = bpy.context.scene
    if 0 <= keyframe_num < scene.frame_start:
        scene.frame_start = keyframe_num

def _get_action_fcurve(action: Action, data_path: str, index: int=0) -> FCurve:
    return action.fcurves.find(data_path, index=index)


def _get_safe_action_fcurve(action: Action,
                            data_path: str, index: int=0) -> FCurve:
    fcurve = _get_action_fcurve(action, data_path, index=index)
    if fcurve:
        return fcurve
    return action.fcurves.new(data_path, index=index)


def _get_fcurve_data(fcurve: Optional[FCurve]) -> list[Vector]:
    if not fcurve:
        return []
    return [p.co for p in fcurve.keyframe_points]


def _clear_fcurve(fcurve: FCurve) -> None:
    for p in reversed(fcurve.keyframe_points):
        fcurve.keyframe_points.remove(p)


def clear_whole_fcurve(obj: Object, data_path: str, index: int=0,
                       frame:Optional[int]=None) -> Optional[float]:
    action = get_action(obj)
    if action is None:
        return None
    fcurve = _get_action_fcurve(action, data_path, index=index)
    if not fcurve:
        return None
    if frame is not None:
        value = fcurve.evaluate(frame)
    else:
        value = None
    _clear_fcurve(fcurve)
    # setattr(obj, data_path, value)
    return value


def remove_fcurve_point(obj: Object, data_path: str, index: int,
                        frame: int) -> None:
    action = get_action(obj)
    if action is None:
        return None
    fcurve = _get_action_fcurve(action, data_path, index=index)
    if not fcurve:
        return None
    points = [p for p in fcurve.keyframe_points if p.co[0] == frame]
    for p in reversed(points):
        fcurve.keyframe_points.remove(p)
    if fcurve.is_empty:
        action.fcurves.remove(fcurve)


def _put_anim_data_in_fcurve(fcurve: Optional[FCurve],
                             anim_data: list[Vector]) -> None:
    if not fcurve:
        return
    start_index = len(fcurve.keyframe_points)
    fcurve.keyframe_points.add(len(anim_data))
    for i, point in enumerate(anim_data):
        fcurve.keyframe_points[start_index + i].co = point
    fcurve.update()


def get_evaluated_fcurve(obj: Object, frame: int, data_path: str,
                         index: int=0) -> Optional[float]:
    action = get_action(obj)
    if not action:
        return None
    fcurve = _get_action_fcurve(action, data_path, index=index)
    if not fcurve:
        return None
    if fcurve.is_empty:
        return None
    return fcurve.evaluate(frame)


def get_safe_evaluated_fcurve(obj: Object, frame: int, data_path: str,
                              index: int=0) -> float:
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
                     action_name: str='NewAction') -> Optional[Action]:
    animation_data = obj.animation_data
    if not animation_data:
        animation_data = obj.animation_data_create()
        if not animation_data:
            return None
    if not animation_data.action:
        animation_data.action = bpy.data.actions.new(action_name)
    return animation_data.action


def _link_object_to_current_scene_collection(obj: Object) -> None:
    act_col = bpy.context.view_layer.active_layer_collection
    index = bpy.data.collections.find(act_col.name)
    if index >= 0:
        col = bpy.data.collections[index]
    else:
        col = bpy.context.scene.collection
    col.objects.link(obj)


def _create_empty_object(name: str) -> Object:
    control = bpy.data.objects.new(name + 'Empty', None)  # Empty-object
    _link_object_to_current_scene_collection(control)
    control.empty_display_type = 'PLAIN_AXES'
    control.empty_display_size = 2.5
    control.rotation_euler = (0, 0, 0)
    control.location = (0, 0, 0)
    return control


def create_animation_on_object(obj: Object, anim_dict: dict,
                               action_name: str='gtAction') -> None:
    action = _get_safe_action(obj, action_name)
    locrot_dict = get_locrot_dict()

    fcurves = {name: _get_safe_action_fcurve(action,
                                             locrot_dict[name]['data_path'],
                                             index=locrot_dict[name]['index'])
               for name in locrot_dict.keys()}

    for name in fcurves.keys():
        _clear_fcurve(fcurves[name])
        _put_anim_data_in_fcurve(fcurves[name], anim_dict[name])


def create_animated_empty(anim_dict: dict) -> Object:
    empty_obj = _create_empty_object('animator')
    create_animation_on_object(empty_obj, anim_dict, 'gtAction')
    return empty_obj


def insert_point_in_fcurve(fcurve: FCurve, frame: int, value: float,
                           keyframe_type: str='KEYFRAME') -> Keyframe:
    k = fcurve.keyframe_points.insert(frame, value, options={'NEEDED'})
    k.type = keyframe_type
    return k


def get_locrot_dict() -> dict:
    return {'location_x': {'data_path': 'location', 'index': 0},
            'location_y': {'data_path': 'location', 'index': 1},
            'location_z': {'data_path': 'location', 'index': 2},
            'rotation_euler_x': {'data_path': 'rotation_euler', 'index': 0},
            'rotation_euler_y': {'data_path': 'rotation_euler', 'index': 1},
            'rotation_euler_z': {'data_path': 'rotation_euler', 'index': 2}}


def create_animation_locrot_keyframe_force(obj: Object) -> None:
    bpy.ops.anim.keyframe_insert_menu({'selected_objects': [obj]},
                                      type='BUILTIN_KSI_LocRot')


def insert_keyframe_in_fcurve(obj: Object, frame: int, value: float,
                              keyframe_type: str, data_path: str,
                              index: int=0) -> None:
    action = _get_safe_action(obj, 'GTAct')
    if action is None:
        return
    fcurve = _get_safe_action_fcurve(action, data_path, index=index)
    insert_point_in_fcurve(fcurve, frame, value, keyframe_type)


def create_locrot_keyframe(obj: Object, keyframe_type: str='KEYFRAME'):
    action = _get_safe_action(obj, 'GTAct')
    if action is None:
        return
    locrot_dict = get_locrot_dict()
    settings = get_gt_settings()
    current_frame = settings.current_frame()
    loc = obj.matrix_world.to_translation()
    rot = obj.matrix_world.to_euler()

    for name, value in zip(locrot_dict.keys(), [*loc, *rot]):
        fcurve = _get_safe_action_fcurve(action, locrot_dict[name]['data_path'],
                                         index=locrot_dict[name]['index'])
        insert_point_in_fcurve(fcurve, current_frame, value, keyframe_type)


def delete_locrot_keyframe(obj: Object) -> None:
    bpy.ops.anim.keyframe_delete_by_name({'selected_objects': [obj]},
                                         type='BUILTIN_KSI_LocRot')


def reset_object_action(obj: Object) -> None:
    animation_data = obj.animation_data
    if not animation_data:
        return
    act = animation_data.action
    animation_data.action = None
    animation_data.action = act


def delete_animation_interval(obj: Object, from_frame: int, to_frame: int,
                              exclude_frames: Optional[list]=None) -> None:
    action = get_action(obj)
    if action is None:
        return

    locrot_dict = get_locrot_dict()
    excluded_frames = exclude_frames if exclude_frames is not None else []

    for name in locrot_dict.keys():
        fcurve = _get_action_fcurve(action, locrot_dict[name]['data_path'],
                                    index=locrot_dict[name]['index'])
        if fcurve is None:
            continue

        points = [p for p in fcurve.keyframe_points
                  if (from_frame <= p.co[0] <= to_frame)
                  and p.co[0] not in excluded_frames]

        for p in reversed(points):
            fcurve.keyframe_points.remove(p)
