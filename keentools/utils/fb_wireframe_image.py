# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2019-2024  KeenTools

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

from typing import Any, Tuple, List, Dict, Optional
import numpy as np

from .kt_logging import KTLogger
from ..facebuilder_config import FBConfig
from .bpy_common import bpy_new_image
from .images import (check_bpy_image_has_same_size,
                     find_bpy_image_by_name,
                     remove_bpy_image,
                     assign_pixels_data)
from ..blender_independent_packages.pykeentools_loader import module as pkt_module
from ..facebuilder.utils.manipulate import check_facs_available


_log = KTLogger(__name__)
_fb: Optional[Any] = None


def _FBCameraInput_class() -> Any:
    class _FBCameraInput(pkt_module().FaceBuilderCameraInputI):
        def projection(self, frame):
            assert frame == 0
            return pkt_module().math.proj_mat(
                fl_to_haperture=50.0 / 36, w=1920.0, h=1080.0,
                pixel_aspect_ratio=1.0, near=0.1, far=1000.0)

        def view(self, frame):
            assert frame == 0
            return np.eye(4)

        def image_size(self, frame):
            assert frame == 0
            return 1920, 1080

    return _FBCameraInput


def _get_fb() -> Any:
    global _fb
    if _fb is None:
        _fb = pkt_module().FaceBuilder(_FBCameraInput_class()())
    return _fb


def create_wireframe_image(texture_colors: List) -> bool:
    _log.yellow('create_wireframe_image')
    fb = _get_fb()
    if not fb.face_texture_available():
        _log.error('create_wireframe_image: cannot initialize image 1')
        return False

    fb.set_face_texture_colors(texture_colors)
    image_data = fb.face_texture()
    size = image_data.shape[:2]
    if not (size[0] > 0) or not (size[1] > 0):
        _log.error('create_wireframe_image: cannot initialize image 2')
        return False

    image_name = FBConfig.coloring_texture_name
    wireframe_image = find_bpy_image_by_name(image_name)
    if wireframe_image is None or \
            not check_bpy_image_has_same_size(wireframe_image, size):
        remove_bpy_image(wireframe_image)
        wireframe_image = bpy_new_image(image_name,
                                        width=size[1],
                                        height=size[0],
                                        alpha=True,
                                        float_buffer=False)
    if wireframe_image:
        rgba = np.ones((size[1], size[0], 4), dtype=np.float32)
        rgba[:, :, :3] = image_data
        assign_pixels_data(wireframe_image.pixels, rgba.ravel())
        wireframe_image.pack()
        return True

    _log.error('create_wireframe_image: cannot initialize image 3')
    return False


_cached_edge_indices_dict: Dict = dict()


def create_edge_indices(*, fb: Optional[Any] = None,
                        vertex_count: Optional[int] = None) -> Tuple[Any, Any]:
    def _empty_result() -> Tuple[Any, Any]:
        _log.red('create_edge_indices _empty_result')
        return (np.empty(shape=(0, 2), dtype=np.int32),
                np.empty(shape=(0, 3), dtype=np.float32))

    global _cached_edge_indices_dict
    _log.blue('create_edge_indices')
    work_fb = _get_fb() if fb is None else fb

    if not work_fb.face_texture_available():
        _log.error('create_edge_indices: fb.face_texture_available is False')
        return _empty_result()

    working_geo = work_fb.applied_args_replaced_uvs_model()
    me = working_geo.mesh(0)
    vert_count = me.points_count()
    poly_count = me.faces_count()

    _log.green(f'mesh points: {vert_count} polygons: {poly_count}')

    if vertex_count is not None and vertex_count != vert_count:
        # TODO: Change LOD
        _log.error('LOD needs to be changed')
        pass

    cache_key = vert_count * 1000000 + poly_count

    if cache_key in _cached_edge_indices_dict:
        _log.green(f'create_edge_indices: cached data is used [{cache_key}]')
        return _cached_edge_indices_dict[cache_key]

    if not check_facs_available(vert_count):
        _log.error(f'create_edge_indices: '
                   f'check_facs_available({vert_count}) is False')
        return _empty_result()

    _log.output('create_edge_indices: calculate new indices')
    face_counts = [me.face_size(x) for x in range(me.faces_count())]
    sum_face_counts = sum(face_counts)
    indices = np.empty((sum_face_counts, 2), dtype=np.int32)
    tex_uvs = np.empty((sum_face_counts * 2, 2), dtype=np.float32)

    i = 0
    for face, count in enumerate(face_counts):
        for k in range(0, count - 1):
            tex_uvs[i * 2] = me.uv(face, k)
            tex_uvs[i * 2 + 1] = me.uv(face, k + 1)
            indices[i] = (me.face_point(face, k),
                          me.face_point(face, k + 1))
            i += 1

        tex_uvs[i * 2] = me.uv(face, count - 1)
        tex_uvs[i * 2 + 1] = me.uv(face, 0)
        indices[i] = (me.face_point(face, count - 1),
                      me.face_point(face, 0))
        i += 1

    _log.output(f'create_edge_indices: put in cache [{cache_key}]'
                f'\nedge_indices: {indices.shape}'
                f'\nedge_uvs: {tex_uvs.shape}')
    _cached_edge_indices_dict[cache_key] = (indices, tex_uvs)
    return indices, tex_uvs
