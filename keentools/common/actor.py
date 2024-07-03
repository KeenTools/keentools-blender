# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2022-2024 KeenTools

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
from ..addon_config import Config


_log = KTLogger(__name__)


class KT_OT_Actor(Operator):
    bl_idname = Config.kt_actor_idname
    bl_label = 'Experimental Operator'
    bl_description = 'Experimental Operator description'
    bl_options = {'REGISTER', 'INTERNAL'}

    action: StringProperty(name='Action string', default='none')
    num: IntProperty(name='Numeric parameter', default=0)

    def draw(self, context):
        pass

    def execute(self, context):
        _log.output('ACTION call: {}'.format(self.action))

        if self.action == 'none':
            return {'CANCELLED'}

        self.report({'INFO'}, self.action)
        return {'FINISHED'}
