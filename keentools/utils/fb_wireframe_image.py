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

from typing import Any, Tuple, List, Dict, Optional, Set
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
_shadow_fb: Optional[Any] = None
_cached_edge_indices_dict: Dict = dict()


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


def get_shadow_fb() -> Any:
    global _shadow_fb
    if _shadow_fb is None:
        _shadow_fb = pkt_module().FaceBuilder(_FBCameraInput_class()())
    return _shadow_fb


def masks_to_number(mask_array: List) -> int:
    n = 0
    for m in mask_array:
        n <<= 1
        if m:
            n += 1
    return n


def create_wireframe_image(texture_colors: List) -> bool:
    _log.yellow('create_wireframe_image')
    fb = get_shadow_fb()
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


def get_fb_mesh_for_texturing(fb: Any) -> Any:
    geo = fb.applied_args_replaced_uvs_model()
    return geo.mesh(0)


def change_fb_lod(fb: Any, vertex_count: int) -> bool:
    _log.yellow('change_fb_lod start')
    mesh = get_fb_mesh_for_texturing(fb)
    if vertex_count == mesh.points_count():
        _log.output('change_fb_lod: current is ok >>>')
        return True

    current_model_index = fb.selected_model()
    for i in range(len(fb.models_list())):
        if i == current_model_index:
            continue
        fb.select_model(i)
        mesh = get_fb_mesh_for_texturing(fb)
        if vertex_count == mesh.points_count():
            _log.output(f'change_fb_lod: found new {i} >>>')
            return True

    fb.select_model(current_model_index)
    _log.error('change_fb_lod: cannot find proper LOD >>>')
    return False


def get_mesh_vert_set(me: Any) -> Set:
    return {me.face_point(i, k)
            for i in range(me.faces_count())
            for k in range(me.face_size(i))}


def change_mask_config(fb: Any, geo_mesh: Any) -> bool:
    def _looking_for_mask_with_non_unique_points(
            fb: Any, geo_mesh_faces_count: int) -> bool:
        _log.red('looking for mask having zero unique points (mouth) start')
        masks = fb.masks()
        for i in range(len(masks)):
            if not masks[i]:
                continue
            fb.set_mask(i, not masks[i])
            mesh = get_fb_mesh_for_texturing(fb)
            if geo_mesh_faces_count == mesh.faces_count():
                _log.output(f'zero unique points mask (mouth) [{i}] was found')
                return True
            fb.set_mask(i, masks[i])
        return False

    _log.yellow('change_mask_config start')
    geo_mesh_faces_count = geo_mesh.faces_count()

    all_points_set = {x for x in range(geo_mesh.points_count())}
    rest_points_set = all_points_set.difference(get_mesh_vert_set(geo_mesh))
    masks = fb.masks()
    masks_count = len(masks)

    if not rest_points_set:
        for i in range(masks_count):
            fb.set_mask(i, True)
        _log.output(f'change_mask_config: all parts are visible >>>')

        mesh = get_fb_mesh_for_texturing(fb)
        if geo_mesh_faces_count == mesh.faces_count():
            _log.output(f'change_mask_config: all visible end >>>')
            return True

        _log.red('change_mask_config: polycounts differ')
        return _looking_for_mask_with_non_unique_points(fb,
                                                        geo_mesh_faces_count)
    for i in range(masks_count):
        fb.set_mask(i, False)

    for i in range(masks_count):
        fb.set_mask(i, True)
        mesh = get_fb_mesh_for_texturing(fb)
        masks[i] = not rest_points_set.intersection(get_mesh_vert_set(mesh))
        fb.set_mask(i, False)

    for i in range(masks_count):
        fb.set_mask(i, masks[i])

    mesh = get_fb_mesh_for_texturing(fb)
    _log.output(f'change_mask_config:\n'
                f'geo_mesh.faces_count: {geo_mesh_faces_count}\n'
                f'mesh.faces_count: {mesh.faces_count()}\n'
                f'geo_mesh.points_count: {geo_mesh.points_count()}\n'
                f'mesh.points_count: {mesh.points_count()}\n')

    if geo_mesh_faces_count == mesh.faces_count():
        return True

    return _looking_for_mask_with_non_unique_points(fb, geo_mesh_faces_count)


def empty_edge_indices_and_uvs() -> Tuple[Any, Any]:
    _log.error('empty_edge_indices_and_uvs')
    max_edge_index_count = 200000
    max_vert_count = 200000
    return (np.zeros(shape=(max_edge_index_count, 2), dtype=np.int32),
            np.zeros(shape=(max_vert_count, 2), dtype=np.float32))


def get_cache_key(vert_count: int, poly_count: int, masks: List) -> int:
    mask_value = masks_to_number(masks)
    cache_key = mask_value * 10000000000 + vert_count * 100000 + poly_count
    _log.green(f'get_cache_key: {cache_key}')
    return cache_key


def get_fb_edge_indices_and_uvs(*, fb: Any) -> Tuple[Any, Any]:
    global _cached_edge_indices_dict
    _log.blue('get_fb_edge_indices_and_uvs start >>>')

    if not fb.face_texture_available():
        _log.error('get_fb_edge_indices_and_uvs: '
                   'fb.face_texture_available is False >>>')
        return empty_edge_indices_and_uvs()

    me = get_fb_mesh_for_texturing(fb)
    vert_count = me.points_count()
    poly_count = me.faces_count()

    cache_key = get_cache_key(vert_count, poly_count, fb.masks())

    if cache_key in _cached_edge_indices_dict:
        _log.green(f'get_fb_edge_indices_and_uvs: '
                   f'cached data is used [{cache_key}] >>>')
        return _cached_edge_indices_dict[cache_key]

    if not check_facs_available(vert_count):
        _log.error(f'get_fb_edge_indices_and_uvs: '
                   f'check_facs_available({vert_count}) is False >>>')
        return empty_edge_indices_and_uvs()

    _log.magenta('get_fb_edge_indices_and_uvs: calculate new indices')
    indices, tex_uvs = calc_fb_edge_indices_and_uvs(fb)

    _log.output(f'get_fb_edge_indices_and_uvs: put in cache [{cache_key}] >>>'
                f'\nedge_indices: {indices.shape}'
                f'\nedge_uvs: {tex_uvs.shape}')
    _cached_edge_indices_dict[cache_key] = (indices, tex_uvs)
    return indices, tex_uvs


def get_ft_edge_indices_and_uvs(*, geo_mesh: Any) -> Tuple[Any, Any]:
    global _cached_edge_indices_dict
    _log.blue('get_ft_edge_indices_and_uvs start >>>')
    fb = get_shadow_fb()

    if not fb.face_texture_available():
        _log.error('get_ft_edge_indices_and_uvs: '
                   'fb.face_texture_available is False >>>')
        return empty_edge_indices_and_uvs()

    geo_vertex_count = geo_mesh.points_count()
    geo_poly_count = geo_mesh.faces_count()
    _log.green(f'mesh points: {geo_vertex_count} polygons: {geo_poly_count}')

    me = get_fb_mesh_for_texturing(fb)
    if geo_vertex_count != me.points_count():
        if not change_fb_lod(fb, geo_vertex_count):
            _log.error('get_ft_edge_indices_and_uvs: '
                       'cannot change LOD >>>')
            return empty_edge_indices_and_uvs()
        change_mask_config(fb, geo_mesh)
        me = get_fb_mesh_for_texturing(fb)

    if geo_poly_count != me.faces_count():
        change_mask_config(fb, geo_mesh)
        me = get_fb_mesh_for_texturing(fb)
        if geo_poly_count != me.faces_count():
            _log.error('get_ft_edge_indices_and_uvs: '
                       'cannot find proper mask config >>>')
            return empty_edge_indices_and_uvs()

    cache_key = get_cache_key(geo_vertex_count, geo_poly_count, fb.masks())

    if cache_key in _cached_edge_indices_dict:
        _log.green(f'get_ft_edge_indices_and_uvs: '
                   f'cached data is used [{cache_key}] >>>')
        return _cached_edge_indices_dict[cache_key]

    if not check_facs_available(geo_vertex_count):
        _log.error(f'get_ft_edge_indices_and_uvs: '
                   f'check_facs_available({geo_vertex_count}) is False >>>')
        return empty_edge_indices_and_uvs()

    _log.magenta('get_ft_edge_indices_and_uvs: calculate new indices')
    indices, tex_uvs = calc_fb_edge_indices_and_uvs(fb)

    _log.output(f'get_ft_edge_indices_and_uvs: put in cache [{cache_key}] >>>'
                f'\nedge_indices: {indices.shape}'
                f'\nedge_uvs: {tex_uvs.shape}')
    _cached_edge_indices_dict[cache_key] = (indices, tex_uvs)
    return indices, tex_uvs


def calc_fb_edge_indices_and_uvs(fb: Any) -> Tuple[Any, Any]:
    _log.yellow('calc_fb_edge_indices_and_uvs start')
    geo = fb.applied_args_replaced_uvs_model()
    me = geo.mesh(0)

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

    _log.output('calc_fb_edge_indices_and_uvs end >>>')
    return indices, tex_uvs
