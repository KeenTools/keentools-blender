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
import numpy as np
import math
import bpy
from . fake_context import get_fake_context


def nearest_point(x, y, points, dist=4000000):  # dist squared
    dist2 = dist
    nearest = -1
    for i, p in enumerate(points):
        d2 = (x - p[0]) ** 2 + (y - p[1]) ** 2
        if d2 < dist2:
            dist2 = d2
            nearest = i
    return nearest, dist2


def xy_to_xz_rotation_matrix_3x3():
    return np.array([[1., 0., 0.],
                     [0., 0., 1.],
                     [0., -1., 0.]], dtype=np.float32)


def xz_to_xy_rotation_matrix_3x3():
    return np.array([[1., 0., 0.],
                     [0., 0., -1.],
                     [0., 1., 0.]], dtype=np.float32)


def xy_to_xz_rotation_matrix_4x4():
    return np.array([[1., 0., 0., 0.],
                     [0., 0., 1., 0.],
                     [0., -1., 0., 0.],
                     [0., 0., 0., 1.]], dtype=np.float32)


def xz_to_xy_rotation_matrix_4x4():
    return np.array([[1., 0., 0., 0.],
                     [0., 0., -1., 0.],
                     [0., 1., 0., 0.],
                     [0., 0., 0., 1.]], dtype=np.float32)


def update_head_mesh_geom(obj, geom):
    mesh = obj.data
    assert(len(geom) == len(mesh.vertices))
    npbuffer = geom @ xy_to_xz_rotation_matrix_3x3()
    mesh.vertices.foreach_set('co', npbuffer.ravel())
    if mesh.shape_keys:
        mesh.shape_keys.key_blocks[0].data.foreach_set('co', npbuffer.ravel())
    mesh.update()


def update_head_mesh_neutral(fb, headobj):
    geom = fb.applied_args_vertices()
    update_head_mesh_geom(headobj, geom)


def update_head_mesh_emotions(fb, headobj, keyframe):
    geom = fb.applied_args_model_vertices_at(keyframe)
    update_head_mesh_geom(headobj, geom)


def update_head_mesh(settings, fb, head):
    if head.should_use_emotions():
        if settings.current_camnum >= 0:
            update_head_mesh_emotions(
                fb, head.headobj, head.get_keyframe(settings.current_camnum))
    else:
        update_head_mesh_neutral(fb, head.headobj)


def projection_matrix(w, h, fl, sw, near, far, scale=1.0):
    z_diff = near - far
    fl_to_sw = fl / sw
    return np.array(
        [[scale * w * fl_to_sw, 0, 0, 0],
         [0, scale * w * fl_to_sw, 0, 0],
         [-w / 2, -h / 2, (near + far) / z_diff, -1],
         [0, 0, 2 * near * far / z_diff, 0]]
    ).transpose()


def focal_by_projection_matrix(pm, sw):
    return - 0.5 * pm[0][0] * sw / pm[0][2]


def render_frame():
    """ Just get frame size from scene render settings """
    scene = bpy.context.scene
    rx = scene.render.resolution_x
    ry = scene.render.resolution_y
    w = rx if rx != 0.0 else 1.0
    h = ry if ry != 0.0 else 1.0
    return w, h


def image_space_to_frame(x, y):
    """ Image centered Relative coords to Frame pixels """
    w, h = render_frame()
    return (x + 0.5) * w, y * w + 0.5 * h


def frame_to_image_space(x, y, w, h):
    return x / w - 0.5, (y - 0.5 * h) / w


def get_mouse_coords(event):
    return event.mouse_region_x, event.mouse_region_y


def image_space_to_region(x, y, x1, y1, x2, y2):
    """ Relative coords to Region (screen) space """
    w = (x2 - x1)
    h = (y2 - y1)
    sc = w
    return x1 + (x + 0.5) * sc, (y1 + y2) * 0.5 + y * sc


def get_image_space_coord(px, py, context):
    x1, y1, x2, y2 = get_camera_border(context)
    x, y = region_to_image_space(px, py, x1, y1, x2, y2)
    return x, y


def region_to_image_space(x, y, x1, y1, x2, y2):
    w = (x2 - x1) if x2 != x1 else 1.0
    sc = w
    return (x - (x1 + x2) * 0.5) / sc, (y - (y1 + y2) * 0.5) / sc


def pin_to_xyz(pin, headobj):
    """ Surface point from barycentric to XYZ """
    sp = pin.surface_point
    bar = sp.barycentric_coordinates
    v = headobj.data.vertices
    gp = sp.geo_point_idxs
    p = v[gp[0]].co * bar[0] + v[gp[1]].co * bar[1] + v[gp[2]].co * bar[2]
    return p


def calc_model_mat(model_mat, head_mat):
    """ Convert model matrix to camera matrix """
    rot_mat = xy_to_xz_rotation_matrix_4x4()

    try:
        nm = np.array(model_mat @ rot_mat) @ np.linalg.inv(head_mat)
        im = np.linalg.inv(nm)
        return im.transpose()
    except Exception:
        return None


def get_raw_camera_2d_data(context):
    """ Area coordinates and view parameters for debug logging """
    if bpy.app.background:
        context = get_fake_context()

    a = context.area
    rv3d = context.space_data.region_3d
    z = rv3d.view_camera_zoom
    off = rv3d.view_camera_offset
    x1, y1, x2, y2 = get_camera_border(context)
    # res = (a.x, a.y, a.width, a.height, z, off[0], off[1])
    res = (x1, y1, x2, y2, z, off[0], off[1])
    return res


def get_camera_border(context):
    """ Camera corners detection via context and parameters """
    if bpy.app.background:
        context = get_fake_context()

    reg = context.region
    w = reg.width
    h = reg.height
    rv3d = context.space_data.region_3d
    z = rv3d.view_camera_zoom
    # Blender Zoom formula
    f = (z * 0.01 + math.sqrt(0.5)) ** 2  # f - scale factor

    scene = context.scene
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


def is_safe_region(context, x, y):
    """ Safe region for pin operation """
    if bpy.app.background:
        context = get_fake_context()

    a = context.area
    rr = a.regions
    x0 = a.x
    y0 = a.y
    w = a.width
    h = a.height
    for i, r in enumerate(rr):
        if r.type != 'WINDOW':
            if (r.x <= x + x0 <= r.x + r.width) and (
                    r.y <= y + y0 <= r.y + r.height):
                return False
    return True


def is_in_area(context, x, y):
    """ Is point in context.area """
    if bpy.app.background:
        context = get_fake_context()

    a = context.area
    return (0 <= x <= a.width) and (0 <= y <= a.height)


def get_pixel_relative_size(context):
    """ One Pixel size in relative coords via current zoom """
    if bpy.app.background:
        context = get_fake_context()

    a = context.area
    w = a.width if a.width > 0 else 1.0
    rv3d = context.space_data.region_3d
    z = rv3d.view_camera_zoom
    # Blender Zoom formula
    f = (z * 0.01 + math.sqrt(0.5)) ** 2  # f - scale factor
    ps = 1.0 / (w * f)
    return ps
