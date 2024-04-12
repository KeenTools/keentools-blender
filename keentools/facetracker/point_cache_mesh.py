# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2024  KeenTools

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

from typing import Any
import numpy as np

from bpy.types import Object, Mesh

from ..utils.kt_logging import KTLogger
from ..facetracker_config import FTConfig
from ..utils.attrs import get_safe_custom_attribute, set_custom_attribute
from ..utils.bpy_common import bpy_new_mesh
from ..utils.coords import get_mesh_verts, get_shape_verts, apply_diff_to_shapes
from ..tracker.tracking_blendshapes import get_all_tracking_frame_shapes


_log = KTLogger(__name__)


def create_point_cache_mesh(obj: Object) -> None:
    _log.green('create_point_cache_mesh')
    cache_mesh = mesh_points_copy(
        obj.data, FTConfig.ft_geomobj_cache_mesh_name_pat.format(obj.name))
    set_custom_attribute(
        obj, FTConfig.ft_geomobj_cache_attr_name, cache_mesh)


def check_tracking_shapes_exist(obj) -> bool:
    if not obj or not obj.type == 'MESH' or not obj.data.shape_keys:
        return False
    key_blocks = obj.data.shape_keys.key_blocks
    frame_shapes = get_all_tracking_frame_shapes(key_blocks)
    return len(frame_shapes) > 0


def mesh_points_copy(src_mesh: Mesh, mesh_name: str) -> Mesh:
    vert_count = len(src_mesh.vertices)
    dst_mesh = bpy_new_mesh(mesh_name)
    dst_mesh.vertices.add(vert_count)
    verts = np.empty((vert_count, 3), dtype=np.float32)
    src_mesh.vertices.foreach_get('co', verts.ravel())
    dst_mesh.vertices.foreach_set('co', verts.ravel())
    dst_mesh.update()
    return dst_mesh


def compare_point_np_arrays(verts1: Any, verts2: Any) -> bool:
    if verts1.shape != verts2.shape:
        _log.red(f'compare_all_points different array sizes\n'
                 f'{verts1.shape} != {verts2.shape}')
        return False
    if np.all(verts1 == verts2):
        _log.green('compare_all_points verts1 = verts2')
        return True
    res = np.allclose(verts1, verts2)
    _log.red(f'compare_all_points complex comparing: {res}')
    return res


def compare_mesh_points(first_mesh: Mesh, second_mesh: Mesh) -> bool:
    _log.yellow('compare_mesh_points')
    verts1 = get_mesh_verts(first_mesh)
    verts2 = get_mesh_verts(second_mesh)
    return compare_point_np_arrays(verts1, verts2)


def update_point_cache_mesh(obj: Object) -> bool:
    _log.yellow('update_point_cache_mesh start')
    cache_mesh = get_safe_custom_attribute(obj,
                                           FTConfig.ft_geomobj_cache_attr_name)
    if not cache_mesh:
        create_point_cache_mesh(obj)
        _log.output('update_point_cache_mesh 1 end >>>')
        return True

    if not compare_mesh_points(cache_mesh, obj.data):
        _log.red('update_point_cache_mesh CACHE IS INVALID')
        if not check_tracking_shapes_exist(obj):
            create_point_cache_mesh(obj)
            _log.output('update_point_cache_mesh 2 end >>>')
            return True

        _log.output('update_point_cache_mesh 3 end >>>')
        return False

    _log.green('update_point_cache_mesh cache is valid')
    _log.output('update_point_cache_mesh end >>>')
    return True


def apply_basis_changes(obj: Object, cache_mesh: Mesh) -> bool:
    _log.yellow('apply_basis_changes start')
    if not cache_mesh:
        _log.red('No cached point mesh')
        return False
    if not obj or not obj.type == 'MESH' or not obj.data.shape_keys:
        _log.red('No shape keys')
        return False

    key_blocks = obj.data.shape_keys.key_blocks
    index = key_blocks.find('Basis')
    if index < 0:
        _log.red('No Basis')
        return False

    basis_shape = key_blocks[index]
    basis_verts = get_shape_verts(basis_shape)
    cache_verts = get_mesh_verts(cache_mesh)
    if basis_verts.shape != cache_verts.shape:
        _log.red('Cache size differs from Basis size')
        return False
    diff = basis_verts - cache_verts
    frame_shapes = get_all_tracking_frame_shapes(key_blocks)
    apply_diff_to_shapes(diff, frame_shapes)
    return True
