# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2024 KeenTools

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

from typing import List, Tuple, Dict, Any
from collections import namedtuple
import numpy as np

from bpy.types import Object
from mathutils import Vector, Matrix

from ..utils.kt_logging import KTLogger
from ..addon_config import ActionStatus
from ..utils.manipulate import select_object_only, switch_to_mode
from ..utils.bpy_common import (update_depsgraph,
                                bpy_set_current_frame,
                                bpy_current_frame,
                                bpy_start_frame,
                                bpy_end_frame,
                                bpy_progress_begin,
                                bpy_progress_update,
                                bpy_progress_end)
from ..utils.coords import get_obj_verts, xy_to_xz_rotation_matrix_3x3


_log = KTLogger(__name__)


CPoint = namedtuple('CPoint', ['name', 'vertex', 'scale'])


def get_control_point_array() -> List:
    return [
CPoint('lips.L', 9649, (1.0, 1.0, 1.0)),
CPoint('lips.R', 6606, (1.0, 1.0, 1.0)),
CPoint('lip.B', 8307, (1.0, 1.0, 1.0)),
CPoint('lip.B.L.001', 9044, (1.0, 1.0, 1.0)),
CPoint('lip.B.R.001', 6801, (1.0, 1.0, 1.0)),
CPoint('lip.T', 8884, (1.0, 1.0, 1.0)),
CPoint('lip.T.L.001', 9114, (1.0, 1.0, 1.0)),
CPoint('lip.T.R.001', 6704, (1.0, 1.0, 1.0)),
CPoint('chin', 9317, (1.0, 1.0, 1.0)),
CPoint('chin.L', 9134, (1.0, 1.0, 1.0)),
CPoint('chin.R', 7539, (1.0, 1.0, 1.0)),
CPoint('cheek.B.L.001', 4253, (1.0, 1.0, 1.0)),
CPoint('cheek.B.R.001', 4246, (1.0, 1.0, 1.0)),
CPoint('nose.002', 5723, (1.0, 1.0, 1.0)),
CPoint('nose.L.001', 975, (1.0, 1.0, 1.0)),
CPoint('nose.R.001', 1178, (1.0, 1.0, 1.0)),
CPoint('nose.003', 5381, (1.0, 1.0, 1.0)),
CPoint('nose.004', 5721, (1.0, 1.0, 1.0)),
CPoint('nose.005', 8770, (1.0, 1.0, 1.0)),
CPoint('nose.001', 5378, (1.0, 1.0, 1.0)),
CPoint('nose.L', 3695, (1.0, 1.0, 1.0)),
CPoint('nose.R', 1478, (1.0, 1.0, 1.0)),
CPoint('nose', 5384, (1.0, 1.0, 1.0)),
CPoint('lid.B.L', 1069, (1.0, 1.0, 1.0)),
CPoint('lid.T.L', 891, (1.0, 1.0, 1.0)),
CPoint('lid.B.R', 1698, (1.0, 1.0, 1.0)),
CPoint('lid.T.R', 1283, (1.0, 1.0, 1.0)),
CPoint('lid.B.L.002', 584, (1.0, 1.0, 1.0)),
CPoint('lid.B.L.001', 651, (1.0, 1.0, 1.0)),
CPoint('lid.B.L.003', 2426, (1.0, 1.0, 1.0)),
CPoint('lid.B.R.002', 1492, (1.0, 1.0, 1.0)),
CPoint('lid.B.R.001', 1647, (1.0, 1.0, 1.0)),
CPoint('lid.B.R.003', 212, (1.0, 1.0, 1.0)),
CPoint('lid.T.L.002', 4332, (1.0, 1.0, 1.0)),  # 3755
CPoint('lid.T.L.001', 4398, (1.0, 1.0, 1.0)),  # 720
CPoint('lid.T.L.003', 4372, (1.0, 1.0, 1.0)),  # 2939
CPoint('lid.T.R.002', 4333, (1.0, 1.0, 1.0)),  # 1549
CPoint('lid.T.R.001', 4390, (1.0, 1.0, 1.0)),  # 1528
CPoint('lid.T.R.003', 4343, (1.0, 1.0, 1.0)),  # 2927
CPoint('brow.T.L.003', 1010, (1.0, 1.0, 1.0)),
CPoint('brow.T.L.002', 2720, (1.0, 1.0, 1.0)),
CPoint('brow.T.L.001', 2386, (1.0, 1.0, 1.0)),
CPoint('brow.T.L', 2068, (1.0, 1.0, 1.0)),
CPoint('brow.B.L.004', 3628, (1.0, 1.0, 1.0)),
CPoint('brow.B.L.003', 2913, (1.0, 1.0, 1.0)),
CPoint('brow.B.L.002', 3441, (1.0, 1.0, 1.0)),
CPoint('brow.B.L.001', 2099, (1.0, 1.0, 1.0)),
CPoint('brow.B.L', 2388, (1.0, 1.0, 1.0)),
CPoint('jaw.L.001', 9207, (1.0, 1.0, 1.0)),
CPoint('jaw.L', 821, (1.0, 1.0, 1.0)),
CPoint('brow.T.R.003', 1644, (1.0, 1.0, 1.0)),
CPoint('brow.T.R.002', 463, (1.0, 1.0, 1.0)),
CPoint('brow.T.R.001', 138, (1.0, 1.0, 1.0)),
CPoint('brow.T.R', 434, (1.0, 1.0, 1.0)),
CPoint('brow.B.R.004', 3404, (1.0, 1.0, 1.0)),
CPoint('brow.B.R.003', 56, (1.0, 1.0, 1.0)),
CPoint('brow.B.R.002', 4135, (1.0, 1.0, 1.0)),
CPoint('brow.B.R.001', 3733, (1.0, 1.0, 1.0)),
CPoint('brow.B.R', 125, (1.0, 1.0, 1.0)),
CPoint('jaw.R.001', 5803, (1.0, 1.0, 1.0)),
CPoint('jaw.R', 4015, (1.0, 1.0, 1.0)),
CPoint('jaw', 9861, (1.0, 1.0, 1.0)),
CPoint('chin.002', 8769, (1.0, 1.0, 1.0)),
]


def _find_bones_with_constraints(arm_obj: Object, points: List) -> List:
    return [point.name for point in points
            if len(arm_obj.pose.bones[point.name].constraints) > 0]


def _get_constraint_states_on_bones(arm_obj: Object, bones_list: List) -> Dict:
    return {name: [cs.enabled for cs in arm_obj.pose.bones[name].constraints]
                   for name in bones_list}


def _revert_constraint_states_on_bones(arm_obj: Object, bone_dict: Dict) -> None:
    for name in bone_dict:
        pbone = arm_obj.pose.bones[name]
        for i, cs in enumerate(pbone.constraints):
            cs.enabled = bone_dict[name][i]


def _set_constraints_on_bones(arm_obj, bones_list, state=False):
    for name in bones_list:
        pbone = arm_obj.pose.bones[name]
        for cs in pbone.constraints:
            cs.enabled = state


def transfer_animation_to_rig(*,
                              obj: Object,
                              arm_obj: Object,
                              facetracker: Any,
                              use_tracked_only: bool = True,
                              detect_scale: bool = True,
                              from_frame: int = 1,
                              to_frame: int = 1,
                              scale: Tuple = (1.0, 1.0, 1.0)) -> ActionStatus:
    _log.yellow('transfer_animation_to_rig start')
    neutral_verts = get_obj_verts(obj)
    all_points = get_control_point_array()

    select_object_only(arm_obj)
    switch_to_mode('EDIT')

    points = [cpoint for cpoint in all_points
              if cpoint.name in arm_obj.data.edit_bones]
    if len(points) == 0:
        msg = f'No target bones in rig'
        _log.error(msg)
        return ActionStatus(False, msg)

    if len(points) < len(all_points):
        lost_bones = [cpoint.name for cpoint in all_points
                      if cpoint.name not in arm_obj.data.edit_bones]
        msg = f'Not all target bones are in rig: {lost_bones}'
        _log.warning(msg)

    point_indices = {point.name: x for x, point in enumerate(points)}

    if detect_scale:
        left_bone = 'lid.T.L'
        right_bone = 'lid.T.R'
        if left_bone not in point_indices or right_bone not in point_indices:
            msg = 'No necessary eye bones in target rig'
            _log.error(msg)
            return ActionStatus(False, msg)

        left_eye_arm_corner = arm_obj.data.edit_bones[left_bone].head.copy()
        right_eye_arm_corner = arm_obj.data.edit_bones[right_bone].head.copy()
        base_arm = left_eye_arm_corner - right_eye_arm_corner

        left_eye_corner = neutral_verts[points[point_indices[left_bone]].vertex]
        right_eye_corner = neutral_verts[points[point_indices[right_bone]].vertex]
        base_eye_corner = left_eye_corner - right_eye_corner

        sc_factor = base_arm.length / np.linalg.norm(base_eye_corner)
        sc = (sc_factor, sc_factor, sc_factor)
    else:
        sc = scale
    _log.output(f'scale: {sc}')

    switch_to_mode('POSE')

    constrained_bones = _find_bones_with_constraints(arm_obj, points)
    bone_dict = _get_constraint_states_on_bones(arm_obj, constrained_bones)

    current_frame = bpy_current_frame()

    if not use_tracked_only:
        frames = [x for x in range(from_frame, to_frame + 1)]
    else:
        frames = [x for x in facetracker.track_frames()
                  if from_frame <= x <= to_frame]

    bpy_progress_begin(0, len(frames))
    for i, frame in enumerate(frames):
        bpy_set_current_frame(frame)

        verts = (facetracker.applied_args_model_vertices_at(frame) @
                 xy_to_xz_rotation_matrix_3x3())
        delta = verts - neutral_verts
        m0_dict = dict()
        for point in points:
            name = point.name
            delta_mat = Matrix.Translation(
                (delta[point.vertex] * point.scale) * sc)
            pbone = arm_obj.pose.bones[name]
            m0 = delta_mat @ pbone.bone.matrix_local
            pbone.matrix = m0
            m0_dict[name] = m0.copy()
            _ = pbone.keyframe_insert(data_path='location', frame=frame)
        update_depsgraph()
        m1_dict = {name: arm_obj.pose.bones[name].matrix.copy()
                   for name in constrained_bones}
        _set_constraints_on_bones(arm_obj, constrained_bones, state=False)
        update_depsgraph()
        m2_dict = {name: arm_obj.pose.bones[name].matrix.copy()
                   for name in constrained_bones}
        _revert_constraint_states_on_bones(arm_obj, bone_dict)
        for name in constrained_bones:
            pbone = arm_obj.pose.bones[name]
            tr_mat = Matrix.Translation(
                m2_dict[name].translation - m1_dict[name].translation)
            pbone.matrix = tr_mat @ m0_dict[name]
            _ = pbone.keyframe_insert(data_path='location', frame=frame)
        bpy_progress_update(i)

    bpy_progress_end()
    switch_to_mode('OBJECT')
    bpy_set_current_frame(current_frame)
    return ActionStatus(True, 'ok')
