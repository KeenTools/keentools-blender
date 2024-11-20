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

import math
from typing import Optional, List, Tuple

from bpy.types import Action, FCurve
from mathutils import Vector, Matrix

from ..utils.version import BVersion


def get_action_fcurve(action: Action, data_path: str, index: int = 0) -> Optional[FCurve]:
    return action.fcurves.find(data_path, index=index)


def get_safe_action_fcurve(action: Action, data_path: str, index: int = 0) -> FCurve:
    fcurve = get_action_fcurve(action, data_path, index=index)
    if not fcurve:
        fcurve = action.fcurves.new(data_path, index=index)
    return fcurve


def get_fcurve_data(fcurve: Optional[FCurve]) -> List[Vector]:
    if not fcurve:
        return []
    return [p.co for p in fcurve.keyframe_points]


def clear_fcurve_new(fcurve: FCurve) -> None:
    fcurve.keyframe_points.clear()


def clear_fcurve_old(fcurve: FCurve) -> None:
    for i in reversed(range(0, len(fcurve.keyframe_points))):
        fcurve.keyframe_points.remove(fcurve.keyframe_points[i], fast=True)
    fcurve.update()


clear_fcurve = clear_fcurve_new if BVersion.fcurve_has_clear else clear_fcurve_old


def put_anim_data_in_fcurve(fcurve: Optional[FCurve],
                            anim_data: List[Vector]) -> None:
    if not fcurve:
        return
    start_index = len(fcurve.keyframe_points)
    fcurve.keyframe_points.add(len(anim_data))
    for i, point in enumerate(anim_data):
        fcurve.keyframe_points[start_index + i].co = point
    fcurve.update()


def cleanup_keys_in_interval(fcurve: FCurve, start_keyframe: float,
                             end_keyframe: float) -> None:
    for p in reversed(fcurve.keyframe_points):
        if start_keyframe <= p.co[0] <= end_keyframe:
            fcurve.keyframe_points.remove(p)
    fcurve.update()


def snap_keys_in_interval(fcurve: FCurve, start_keyframe: float,
                          end_keyframe: float) -> None:
    left = min(start_keyframe, round(start_keyframe))
    right = max(end_keyframe, round(end_keyframe))
    points = list(set([round(p.co[0]) for p in fcurve.keyframe_points
                       if start_keyframe <= p.co[0] <= end_keyframe]))
    points.sort()
    anim_data = [(x, fcurve.evaluate(x)) for x in points]
    cleanup_keys_in_interval(fcurve, left, right)
    put_anim_data_in_fcurve(fcurve, anim_data)


def add_zero_keys_at_start_and_end(fcurve: FCurve, start_keyframe: float,
                                   end_keyframe: float) -> None:
    left = round(start_keyframe)
    right = math.floor(end_keyframe)
    anim_data = [(left, 0), (right, 0)]
    put_anim_data_in_fcurve(fcurve, anim_data)
