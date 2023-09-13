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

from .kt_logging import KTLogger
from ..blender_independent_packages.pykeentools_loader import module as pkt_module
from .coords import (get_scale_matrix_3x3_from_matrix_world,
                     get_mesh_verts,
                     xz_to_xy_rotation_matrix_3x3)
from .bpy_common import evaluated_mesh
from .blendshapes import find_blenshape_index


_log = KTLogger(__name__)


def build_geo(obj: Object, get_uv=False) -> Any:
    _log.output(_log.color('magenta', 'build_geo start'))
    mb = pkt_module().MeshBuilder()
    _geo = pkt_module().Geo()

    if obj:
        mesh = evaluated_mesh(obj)
        scale = get_scale_matrix_3x3_from_matrix_world(obj.matrix_world)
        verts = get_mesh_verts(mesh) @ scale

        mb.add_points(verts @ xz_to_xy_rotation_matrix_3x3())

        for polygon in mesh.polygons:
            mb.add_face(polygon.vertices[:])

        if get_uv and mesh.uv_layers.active:
            uvmap = mesh.uv_layers.active.data
            uvs = [np.array(v.uv) for v in uvmap]
            mb.set_uvs_attribute('VERTEX_BASED', uvs)

    _geo.add_mesh(mb.mesh())
    _log.output(_log.color('magenta', 'build_geo end'))
    return _geo


def build_geo_from_basis(obj: Object, get_uv=False) -> Any:
    _log.output(_log.color('magenta', 'build_geo_from_basis start'))
    mb = pkt_module().MeshBuilder()
    _geo = pkt_module().Geo()

    if obj:
        shape_name = 'Basis'
        shape_index = find_blenshape_index(obj, shape_name)
        if shape_index < 0:
            obj.shape_key_add(name=shape_name)
        basis_shape = obj.data.shape_keys.key_blocks[shape_index]

        shape_name = 'FTAnimated'
        shape_index = find_blenshape_index(obj, shape_name)
        if shape_index < 0:
            obj.shape_key_add(name=shape_name)
            shape_index = find_blenshape_index(obj, shape_name)

        shape = obj.data.shape_keys.key_blocks[shape_index]
        shape.value = 1.0
        obj.active_shape_key_index = shape_index

        mesh = evaluated_mesh(obj)
        scale = get_scale_matrix_3x3_from_matrix_world(obj.matrix_world)
        verts = np.empty((len(mesh.vertices), 3), dtype=np.float32)
        basis_shape.data.foreach_get('co', verts.ravel())

        mb.add_points(verts @ scale @ xz_to_xy_rotation_matrix_3x3())

        for polygon in mesh.polygons:
            mb.add_face(polygon.vertices[:])

        if get_uv and mesh.uv_layers.active:
            uvmap = mesh.uv_layers.active.data
            uvs = [np.array(v.uv) for v in uvmap]
            mb.set_uvs_attribute('VERTEX_BASED', uvs)

    _geo.add_mesh(mb.mesh())
    _log.output(_log.color('magenta', 'build_geo_from_basis end'))
    return _geo
