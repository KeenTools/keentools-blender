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

from bpy.types import Operator
from bpy.props import StringProperty, IntProperty

from ..utils.kt_logging import KTLogger
from ..addon_config import ActionStatus
from ..geotracker_config import GTConfig, get_current_geotracker_item
from .utils.geotracker_acts import center_geo_act
from .ui_strings import buttons


_log = KTLogger(__name__)


def convert_to_relative_blendshapes() -> ActionStatus:
    _log.output(
        _log.color('yellow', f'convert_to_relative_blendshapes'))
    geotracker = get_current_geotracker_item()
    geomobj = geotracker.geomobj
    mesh = geomobj.data

    if not mesh.shape_keys:
        return ActionStatus(False, 'No mesh shape keys')

    anim_data = mesh.shape_keys.animation_data
    if not anim_data:
        return ActionStatus(False, 'No mesh animation')

    old_action = anim_data.action
    if not old_action:
        return ActionStatus(False, 'No mesh action')

    keyframes = [(int(kb.name[6:]) if kb.name[:6] == 'frame_' else -1, kb.name)
                 for kb in geomobj.data.shape_keys.key_blocks[1:]]
    keyframe_count = len(keyframes)

    if keyframe_count <= 1:
        return ActionStatus(False, 'Not enough animated keyframes')

    import bpy
    action = bpy.data.actions.new('ftRelativeAction')
    anim_data.action = action

    mesh.shape_keys.use_relative = True

    prev_frame = 0

    for i, pair in enumerate(keyframes):
        frame, name = pair
        fcurve = action.fcurves.new(f'key_blocks["{name}"].value', index=0)

        if i == 0:
            fcurve.keyframe_points.add(2)
            fcurve.keyframe_points[0].co = (frame, 1.0)
            fcurve.keyframe_points[1].co = (keyframes[i + 1][0], 0.0)
        elif i == keyframe_count - 1:
            fcurve.keyframe_points.add(2)
            fcurve.keyframe_points[0].co = (prev_frame, 0.0)
            fcurve.keyframe_points[1].co = (frame, 1.0)
        else:
            fcurve.keyframe_points.add(3)
            fcurve.keyframe_points[0].co = (prev_frame, 0.0)
            fcurve.keyframe_points[1].co = (frame, 1.0)
            fcurve.keyframe_points[2].co = (keyframes[i + 1][0], 0.0)

        fcurve.update()
        prev_frame = frame

    return ActionStatus(True, 'ok')


class GT_OT_Actor(Operator):
    bl_idname = GTConfig.gt_actor_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER'}

    action: StringProperty(name='Action string', default='none')
    num: IntProperty(name='Numeric parameter', default=0)

    def draw(self, context):
        pass

    def execute(self, context):
        _log.output('ACTION call: {}'.format(self.action))

        if self.action == 'none':
            act_status = center_geo_act()
            if not act_status.success:
                self.report({'ERROR'}, act_status.error_message)
            else:
                self.report({'INFO'}, act_status.error_message)
            return {'FINISHED'}
        elif self.action == 'convert_to_relative_blendshapes':
            act_status = convert_to_relative_blendshapes()
            if not act_status.success:
                self.report({'ERROR'}, act_status.error_message)
            else:
                self.report({'INFO'}, act_status.error_message)
            return {'FINISHED'}

        self.report({'INFO'}, self.action)
        return {'FINISHED'}
