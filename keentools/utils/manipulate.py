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

import logging

import bpy

from .localview import enter_area_localview, exit_area_localview


def has_no_blendshape(obj):
    return not obj or obj.type != 'MESH' or not obj.data or \
           not obj.data.shape_keys


def has_blendshapes_action(obj):
    if obj and obj.type == 'MESH' \
           and obj.data.shape_keys \
           and obj.data.shape_keys.animation_data \
           and obj.data.shape_keys.animation_data.action:
        return True
    return False


def force_undo_push(msg='KeenTools operation'):
    logger = logging.getLogger(__name__)
    logger.debug('UNDO PUSH: {}'.format(msg))
    bpy.ops.ed.undo_push(message=msg)


def select_object_only(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(state=True)
    bpy.context.view_layer.objects.active = obj


def get_vertex_groups(obj):
    vertices = obj.data.vertices
    vertex_groups = [x for x in obj.vertex_groups]
    vg_dict = {}
    for vg in vertex_groups:
        vg_dict[vg.name] = [[v.index, vg.weight(v.index)]
                            for v in vertices
                            if vg.index in [g.group for g in v.groups]]
    return vg_dict


def create_vertex_groups(obj, vg_dict):
    for vg_name in vg_dict.keys():
        if vg_name in obj.vertex_groups.keys():
            vg = obj.vertex_groups[vg_name]
        else:
            vg = obj.vertex_groups.new(name=vg_name)
        for i, w in vg_dict[vg_name]:
            vg.add([i], w, 'REPLACE')


def switch_to_camera(area, camobj, select_obj=None):
    exit_area_localview(area)
    camobj.hide_set(False)
    select_object_only(camobj)
    enter_area_localview(area)

    # Low-level code instead bpy.ops.view3d.object_as_camera()
    area.spaces.active.camera = camobj
    area.spaces.active.region_3d.view_perspective = 'CAMERA'

    if select_obj is not None:
        select_object_only(select_obj)
