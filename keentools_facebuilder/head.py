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
import numpy as np
from . fbloader import FBLoader
from .config import config, BuilderType, get_main_settings, ErrorType


class MESH_OT_FBAddHead(bpy.types.Operator):
    bl_idname = config.fb_add_head_operator_idname
    bl_label = "Face Builder Head"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            obj = self.new_head()
        except:
            op = getattr(bpy.ops.wm, config.fb_warning_operator_callname)
            op('INVOKE_DEFAULT', msg=ErrorType.CannotCreate)
            return {'CANCELLED'}
        FBLoader.add_to_fb_collection(obj)  # link to FB objects collection
        FBLoader.set_keentools_version(obj)  # Mark Keentools attribute

        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(state=True)
        bpy.context.view_layer.objects.active = obj

        bpy.ops.object.shade_smooth()
        h = get_main_settings().heads.add()
        h.headobj = obj
        return {'FINISHED'}

    @classmethod
    def new_head(cls):
        stored_builder_type = FBLoader.get_builder_type()
        fb = FBLoader.new_builder(stored_builder_type)
        geo = fb.applied_args_model()
        me = geo.mesh(0)

        v_count = me.points_count()
        vertices = []
        for i in range(0, v_count):
            vertices.append(me.point(i))

        rot = np.array([[1., 0., 0.], [0., 0., 1.], [0., -1., 0]])
        vertices2 = vertices @ rot
        # vertices2 = vertices

        f_count = me.faces_count()
        faces = []
        normals = []
        n = 0
        for i in range(0, f_count):
            row = []
            for j in range(0, me.face_size(i)):
                row.append(me.face_point(i, j))
                normal = me.normal(i, j) @ rot
                normals.append(tuple(normal))
                n += 1
            faces.append(tuple(row))

        mesh = bpy.data.meshes.new('Head_mesh')
        mesh.from_pydata(vertices2, [], faces)

        # Init Custom Normals (work on Shading Flat!)
        # mesh.calc_normals_split()
        # mesh.normals_split_custom_set(normals)
        mesh.update()

        # Warning! our autosmooth settings work on Shading Flat!
        # mesh.use_auto_smooth = True
        # mesh.auto_smooth_angle = 3.1415927410125732

        obj = bpy.data.objects.new('FBHead', mesh)
        # Restore builder
        FBLoader.new_builder(stored_builder_type)
        return obj
