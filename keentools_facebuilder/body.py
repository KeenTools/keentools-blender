# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2019  KeenTools

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


import bpy

from . utils import attrs
from . config import Config, get_main_settings, get_operators, \
    BuilderType, ErrorType
from . fbloader import FBLoader


class MESH_OT_FBAddBody(bpy.types.Operator):
    bl_idname = Config.fb_add_body_operator_idname
    bl_label = "BodyBuilder Body"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            obj = self.new_body()
        except Exception:
            warn = getattr(get_operators(), Config.fb_warning_callname)
            warn('INVOKE_DEFAULT', msg=ErrorType.CannotCreateObject)
            return {'CANCELLED'}
        attrs.add_to_fb_collection(obj)  # link to FB objects collection
        FBLoader.set_keentools_version(obj)  # Mark Keentools attribute

        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(state=True)
        bpy.context.view_layer.objects.active = obj

        bpy.ops.object.shade_smooth()
        h = get_main_settings().heads.add()
        h.headobj = obj
        h.mod_ver = FBLoader.get_builder_version()

        try:
            a = context.area
            # Try to show UI Panel
            a.spaces[0].show_region_ui = True
        except Exception:
            pass
        return {'FINISHED'}

    @classmethod
    def new_body(cls):
        mesh = FBLoader.universal_mesh_loader(
            BuilderType.BodyBuilder, 'Body_mesh')
        obj = bpy.data.objects.new('BBBody', mesh)
        return obj
