# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2019-2022 KeenTools

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
from typing import Any, Dict, Callable, Tuple

import bpy
from bpy.types import Object, Operator


def bpy_scene() -> Any:
    return bpy.context.scene


def bpy_current_frame() -> int:
    return bpy.context.scene.frame_current


def bpy_start_frame() -> int:
    return bpy.context.scene.frame_start

def bpy_end_frame() -> int:
    return bpy.context.scene.frame_end


def bpy_set_current_frame(frame: int) -> None:
    bpy.context.scene.frame_set(frame)


def link_object_to_current_scene_collection(obj: Object) -> None:
    act_col = bpy.context.view_layer.active_layer_collection
    index = bpy.data.collections.find(act_col.name)
    if index >= 0:
        col = bpy.data.collections[index]
    else:
        col = bpy.context.scene.collection
    col.objects.link(obj)


def create_empty_object(name: str) -> Object:
    control = bpy.data.objects.new(name, None)  # Empty-object
    link_object_to_current_scene_collection(control)
    control.empty_display_type = 'PLAIN_AXES'
    control.empty_display_size = 2.5
    control.rotation_euler = (0, 0, 0)
    control.location = (0, 0, 0)
    return control


def _operator_with_context_old(operator: Operator,
                               context_override_dict: Dict, **kwargs) -> None:
    return operator(context_override_dict, **kwargs)


def _operator_with_context_new(operator: Operator,
                               context_override_dict: Dict, **kwargs) -> None:
    with bpy.context.temp_override(**context_override_dict):
        return operator(**kwargs)


operator_with_context: Callable = _operator_with_context_new \
    if bpy.app.version >= (3, 2, 0) else _operator_with_context_old


def extend_scene_timeline_end(keyframe_num: int, force=False) -> None:
    scene = bpy.context.scene
    if force or scene.frame_end < keyframe_num:
        scene.frame_end = keyframe_num


def extend_scene_timeline_start(keyframe_num: int) -> None:
    scene = bpy.context.scene
    if 0 <= keyframe_num < scene.frame_start:
        scene.frame_start = keyframe_num


def get_scene_camera_shift() -> Tuple[float, float]:
    cam = bpy.context.scene.camera
    if not cam:
        return 0.0, 0.0
    return cam.data.shift_x, cam.data.shift_y
