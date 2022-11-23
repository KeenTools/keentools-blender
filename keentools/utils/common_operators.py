# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2019-2022  KeenTools

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

from ..addon_config import Config
from .localview import check_context_localview
from .other import force_show_ui_overlays
from .bpy_common import bpy_localview
from ..ui_strings import buttons


class KT_OT_ExitLocalview(Operator):
    bl_idname = Config.kt_exit_localview_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        if not check_context_localview(context):
            self.report({'ERROR', 'Cannot set proper context for operator'})
            return {'CANCELLED'}
        bpy_localview()
        force_show_ui_overlays(context.area)
        return {'FINISHED'}


CLASSES_TO_REGISTER = (KT_OT_ExitLocalview,)
