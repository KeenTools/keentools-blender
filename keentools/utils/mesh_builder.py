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

import numpy as np
from typing import Any

from bpy.types import Object

from ..blender_independent_packages.pykeentools_loader import module as pkt_module
from .coords import (get_scale_matrix_3x3_from_matrix_world,
                     get_mesh_verts,
                     xz_to_xy_rotation_matrix_3x3)
from .bpy_common import evaluated_object


def build_geo(obj: Object, evaluated: bool=True, get_uv=False) -> Any:
    mesh = obj.data if not evaluated else evaluated_object(obj).data
    scale = get_scale_matrix_3x3_from_matrix_world(obj.matrix_world)
    verts = get_mesh_verts(mesh) @ scale

    mb = pkt_module().MeshBuilder()
    mb.add_points(verts @ xz_to_xy_rotation_matrix_3x3())

    for polygon in mesh.polygons:
        mb.add_face(polygon.vertices[:])

    if get_uv and mesh.uv_layers.active:
        uvmap = mesh.uv_layers.active.data
        uvs = [np.array(v.uv) for v in uvmap]
        mb.set_uvs_attribute('VERTEX_BASED', uvs)

    _geo = pkt_module().Geo()
    _geo.add_mesh(mb.mesh())
    return _geo
