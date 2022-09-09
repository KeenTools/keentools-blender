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
from typing import Any, Tuple, List, Optional

import numpy as np
import math
import bpy
from bpy.types import Area
from . fake_context import get_fake_context


def nearest_point(x: float, y: float, points: List[Tuple[float, float]],
                  dist: float=4000000.0) -> Tuple[int, float]:  # dist squared
    dist2 = dist
    nearest = -1
    for i, p in enumerate(points):
        d2 = (x - p[0]) ** 2 + (y - p[1]) ** 2
        if d2 < dist2:
            dist2 = d2
            nearest = i
    return nearest, dist2


def xy_to_xz_rotation_matrix_3x3() -> Any:
    return np.array([[1., 0., 0.],
                     [0., 0., 1.],
                     [0., -1., 0.]], dtype=np.float32)


def xz_to_xy_rotation_matrix_3x3() -> Any:
    return np.array([[1., 0., 0.],
                     [0., 0., -1.],
                     [0., 1., 0.]], dtype=np.float32)


def xy_to_xz_rotation_matrix_4x4() -> Any:
    return np.array([[1., 0., 0., 0.],
                     [0., 0., 1., 0.],
                     [0., -1., 0., 0.],
                     [0., 0., 0., 1.]], dtype=np.float32)


def xz_to_xy_rotation_matrix_4x4() -> Any:
    return np.array([[1., 0., 0., 0.],
                     [0., 0., -1., 0.],
                     [0., 1., 0., 0.],
                     [0., 0., 0., 1.]], dtype=np.float32)


def update_head_mesh_geom(obj: Any, geom: Any) -> None:
    mesh = obj.data
    assert(len(geom) == len(mesh.vertices))
    npbuffer = geom @ xy_to_xz_rotation_matrix_3x3()
    mesh.vertices.foreach_set('co', npbuffer.ravel())
    if mesh.shape_keys:
        mesh.shape_keys.key_blocks[0].data.foreach_set('co', npbuffer.ravel())
    mesh.update()


def update_head_mesh_neutral(fb: Any, head: Any) -> None:
    geom = fb.applied_args_vertices()
    update_head_mesh_geom(head.headobj, geom)


def update_head_mesh_expressions(fb: Any, head: Any, keyframe: int) -> None:
    geom = fb.applied_args_model_vertices_at(keyframe)
    update_head_mesh_geom(head.headobj, geom)


def update_head_mesh_non_neutral(fb: Any, head: Any) -> None:
    if head.should_use_emotions():
        kid = head.get_expression_view_keyframe()
        if kid == 0:  # Neutral selected
            pass
        elif fb.is_key_at(kid):
            update_head_mesh_expressions(fb, head, kid)
            return
        else:
            logger = logging.getLogger(__name__)
            logger.error(
                'NO KEYFRAME: {} in {}'.format(kid, fb.keyframes()))
    update_head_mesh_neutral(fb, head)


def projection_matrix(w: float, h: float, fl: float, sw: float,
                      near: float, far: float, scale=1.0) -> Any:
    z_diff = near - far
    fl_to_sw = fl / sw
    return np.array(
        [[scale * w * fl_to_sw, 0, 0, 0],
         [0, scale * w * fl_to_sw, 0, 0],
         [-w / 2, -h / 2, (near + far) / z_diff, -1],
         [0, 0, 2 * near * far / z_diff, 0]]
    ).transpose()


def custom_projection_matrix(w: float, h: float, fl: float, sw: float,
                             near: float, far: float) -> Any:
    def _compensate_view_scale(w: float, h: float) -> float:
        if w == 0 or h == 0:
            return 1.0
        if w >= h:
            return 1.0
        else:
            return h / w

    return projection_matrix(w, h, fl, sw, near, far,
                             scale=_compensate_view_scale(w, h))


def focal_by_projection_matrix_mm(pm: Any, sw: float) -> float:
    return - 0.5 * pm[0][0] * sw / pm[0][2]


def focal_by_projection_matrix_px(pm: Any) -> float:
    return pm[0][0]


def focal_mm_to_px(fl_mm: float, image_width: float,
                   sensor_width: float=36.0) -> float:
    return fl_mm * image_width / sensor_width


def focal_px_to_mm(fl_px: float, image_width: float,
                   sensor_width: float=36.0) -> float:
    return fl_px * sensor_width / image_width


def render_frame() -> Tuple[int, int]:
    """ Just get frame size from scene render settings """
    scene = bpy.context.scene
    rx = scene.render.resolution_x
    ry = scene.render.resolution_y
    w = rx if rx != 0 else 1
    h = ry if ry != 0 else 1
    return w, h


def render_width() -> int:
    return bpy.context.scene.render.resolution_x


def camera_sensor_width(camobj: Any) -> float:
    if not camobj or not camobj.data:
        return 36.0
    return camobj.data.sensor_width


def camera_focal_length(camobj: Any) -> float:
    if not camobj or not camobj.data:
        return 50.0
    return camobj.data.lens


def image_space_to_frame(x: float, y: float) -> Tuple[float, float]:
    """ Image centered Relative coords to Frame pixels """
    w, h = render_frame()
    return (x + 0.5) * w, y * w + 0.5 * h


def frame_to_image_space(x: float, y: float, w: float, h: float) -> Tuple[float, float]:
    return x / w - 0.5, (y - 0.5 * h) / w


def get_mouse_coords(event: Any) -> Tuple[float, float]:
    return event.mouse_region_x, event.mouse_region_y


def image_space_to_region(x: float, y: float, x1: float, y1: float,
                          x2: float, y2: float) -> Tuple[float, float]:
    """ Relative coords to Region (screen) space """
    w = (x2 - x1)
    h = (y2 - y1)
    sc = w
    return x1 + (x + 0.5) * sc, (y1 + y2) * 0.5 + y * sc


def get_image_space_coord(px: float, py: float, area: Area) -> Tuple[float, float]:
    x1, y1, x2, y2 = get_camera_border(area)
    x, y = region_to_image_space(px, py, x1, y1, x2, y2)
    return x, y


def region_to_image_space(x: float, y: float, x1: float, y1: float,
                          x2: float, y2: float) -> Tuple[float, float]:
    w = (x2 - x1) if x2 != x1 else 1.0
    sc = w
    return (x - (x1 + x2) * 0.5) / sc, (y - (y1 + y2) * 0.5) / sc


def pin_to_xyz_from_mesh(pin: Any, headobj: Any) -> Tuple[float, float, float]:
    """ Surface point from barycentric to XYZ using passed mesh"""
    sp = pin.surface_point
    gp = sp.geo_point_idxs
    bar = sp.barycentric_coordinates
    vv = headobj.data.vertices
    p = vv[gp[0]].co * bar[0] + vv[gp[1]].co * bar[1] + vv[gp[2]].co * bar[2]
    return p


def pin_to_xyz_from_fb_geo_mesh(pin: Any, geo_mesh: Any) -> Tuple[float, float, float]:
    """ Surface point from barycentric to XYZ using fb geo_mesh"""
    sp = pin.surface_point
    gp = sp.geo_point_idxs
    bar = sp.barycentric_coordinates
    v1 = geo_mesh.point(gp[0])
    v2 = geo_mesh.point(gp[1])
    v3 = geo_mesh.point(gp[2])
    p = v1 * bar[0] + v2 * bar[1] + v3 * bar[2]
    return p


def calc_model_mat(model_mat: Any, head_mat: Any) -> Optional[Any]:
    """ Convert model matrix to camera matrix """
    rot_mat = xy_to_xz_rotation_matrix_4x4()

    try:
        nm = np.array(model_mat @ rot_mat) @ np.linalg.inv(head_mat)
        im = np.linalg.inv(nm)
        return im.transpose()
    except Exception:
        return None


def get_area_region_3d(area: Area) -> Optional[Any]:
    return area.spaces.active.region_3d


def get_area_region(area: Area) -> Optional[Any]:
    return area.regions[-1]


def get_area_overlay(area: Area) -> Optional[Any]:
    if not area:
        return None
    return area.spaces.active.overlay


def get_camera_border(area: Area) -> Tuple[float, float, float, float]:
    if bpy.app.background:
        context = get_fake_context()
        area = context.area

    region = get_area_region(area)
    assert region.type == 'WINDOW'
    w = region.width
    h = region.height

    rv3d = get_area_region_3d(area)
    z = rv3d.view_camera_zoom
    # Blender Zoom formula
    f = (z * 0.01 + math.sqrt(0.5)) ** 2  # f - scale factor

    scene = bpy.context.scene
    rx = scene.render.resolution_x
    ry = scene.render.resolution_y

    a1 = w / h
    a2 = rx / ry

    offset = (rv3d.view_camera_offset[0] * w * 2 * f,
              rv3d.view_camera_offset[1] * h * 2 * f)

    # This works when Camera Sensor Mode is Auto
    if a1 >= 1.0:
        if a2 >= 1.0:
            # Horizontal image in horizontal View
            kx = f
            ky = f * a1 * a2  # (ry / rx) * (w / h)
        else:
            kx = f * a2  # (rx / ry)
            ky = f * a1  # (w / h)

    else:
        if a2 < 1.0:
            # Vertical image in vertical View
            kx = f * a2 / a1  # (rx / ry) * (h / w)
            ky = f
        else:
            kx = f / a1  # (h / w)
            ky = f / a2  # (ry / rx)

    x1 = w * 0.5 - kx * w * 0.5 - offset[0]
    x2 = w * 0.5 + kx * w * 0.5 - offset[0]
    y1 = h * 0.5 - ky * h * 0.5 - offset[1]
    y2 = h * 0.5 + ky * h * 0.5 - offset[1]
    return x1, y1, x2, y2


def is_safe_region(area: Area, x: float, y: float) -> bool:
    """ Safe region for pin operation """
    if bpy.app.background:
        context = get_fake_context()
        area = context.area

    x0 = area.x
    y0 = area.y
    for i, r in enumerate(area.regions):
        if r.type != 'WINDOW':
            if (r.x <= x + x0 <= r.x + r.width) and (
                    r.y <= y + y0 <= r.y + r.height):
                return False
    return True


def is_in_area(area: Area, x: float, y: float) -> bool:
    """ Is point in area """
    if bpy.app.background:
        context = get_fake_context()
        area = context.area

    return (0 <= x <= area.width) and (0 <= y <= area.height)


def get_pixel_relative_size(area: Area) -> float:
    """ One Pixel size in relative coords via current zoom """
    if bpy.app.background:
        context = get_fake_context()
        area = context.area

    w = area.width if area.width > 0 else 1.0
    space = area.spaces.active
    rv3d = space.region_3d
    z = rv3d.view_camera_zoom
    # Blender Zoom formula
    f = (z * 0.01 + math.sqrt(0.5)) ** 2  # f - scale factor
    ps = 1.0 / (w * f)
    return ps


def get_depsgraph() -> Any:
    return bpy.context.evaluated_depsgraph_get()


def evaluated_mesh(obj: Any) -> Any:
    depsgraph = get_depsgraph()
    return obj.evaluated_get(depsgraph)


def update_depsgraph() -> Any:
    depsgraph = get_depsgraph()
    depsgraph.update()
    return depsgraph


def get_mesh_verts(obj: Any) -> Any:
    mesh = obj.data
    verts = np.empty((len(mesh.vertices), 3), dtype=np.float32)
    mesh.vertices.foreach_get(
        'co', np.reshape(verts, len(mesh.vertices) * 3))
    return verts


def to_homogeneous(verts: Any) -> Any:
    vv = np.ones((len(verts), 4), dtype=np.float32)
    vv[:, :-1] = verts
    return vv


def multiply_verts_on_matrix_4x4(verts: Any, mat: Any) -> Any:
    vv = to_homogeneous(verts) @ mat
    return vv[:, :3]


def get_scale_vec_3_from_matrix_world(obj_matrix_world: Any) -> Any:
    return np.array(obj_matrix_world.to_scale(), dtype=np.float32)


def get_scale_vec_4_from_matrix_world(obj_matrix_world: Any) -> Any:
    return np.array(obj_matrix_world.to_scale().to_4d(), dtype=np.float32)


def get_scale_matrix_4x4_from_matrix_world(obj_matrix_world: Any) -> Any:
    scale_vec = get_scale_vec_4_from_matrix_world(obj_matrix_world)
    return np.diag(scale_vec)


def get_world_matrix_without_scale(obj_matrix_world: Any) -> Any:
    scale_vec = get_scale_vec_4_from_matrix_world(obj_matrix_world)
    scminv = np.diag(1.0 / scale_vec)
    return scminv @ np.array(obj_matrix_world, dtype=np.float32).transpose()


def get_scale_matrix_3x3_from_matrix_world(obj_matrix_world: Any) -> Any:
    scale_vec = get_scale_vec_3_from_matrix_world(obj_matrix_world)
    return np.diag(scale_vec)


def compensate_view_scale() -> float:
    image_width, image_height = render_frame()
    if image_width >= image_height:
        return 1.0
    return image_width / image_height


def calc_bpy_camera_mat_relative_to_model(model: Any, gt_model_mat: Any) -> Any:
    rot_mat2 = xz_to_xy_rotation_matrix_4x4()
    scale_vec = get_scale_vec_4_from_matrix_world(model.matrix_world)
    scminv = np.diag(1.0 / scale_vec)

    try:
        mat = np.array(
            model.matrix_world) @ scminv @ rot_mat2 @ np.linalg.inv(
            gt_model_mat)
        return mat.transpose()
    except Exception:
        return np.eye(4)


def calc_bpy_model_mat_relative_to_camera(camera: Any, model: Any,
                                          gt_model_mat: Any) -> Any:
    rot_mat = xy_to_xz_rotation_matrix_4x4()
    scale_mat = get_scale_matrix_4x4_from_matrix_world(model.matrix_world)
    np_mw = np.array(camera.matrix_world) @ (gt_model_mat @
                                             rot_mat @ scale_mat)
    return np_mw.transpose()
