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
import numpy as np

from .. config import Config, get_main_settings, get_operators, ErrorType
from .. fbloader import FBLoader
from ..utils.coords import projection_matrix
import keentools_facebuilder.blender_independent_packages.pykeentools_loader as pkt


def switch_to_mode(mode='MATERIAL'):
    areas = bpy.context.workspace.screens[0].areas
    for area in areas:
        for space in area.spaces:
            if space.type == 'VIEW_3D':
                space.shading.type = mode


def toggle_mode(modes=('SOLID', 'MATERIAL')):
    areas = bpy.context.workspace.screens[0].areas
    for area in areas:
        for space in area.spaces:
            if space.type == 'VIEW_3D':
                cur_mode = space.shading.type
                ind = 0
                if cur_mode in modes:
                    ind = modes.index(cur_mode)
                    ind += 1
                    if ind >= len(modes):
                        ind = 0
                space.shading.type = modes[ind]


def assign_material_to_object(obj, mat):
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)


def get_mat_by_name(mat_name):
    if bpy.data.materials.find(mat_name) >= 0:
        return bpy.data.materials[mat_name]

    new_mat = bpy.data.materials.new(mat_name)
    new_mat.use_nodes = True
    return new_mat


def get_shader_node(mat, find_type, create_name):
    for node in mat.node_tree.nodes:
        if node.type == find_type:
            return node
    return mat.node_tree.nodes.new(create_name)


def find_tex_by_name(tex_name):
    tex_num = bpy.data.images.find(tex_name)
    if tex_num >= 0:
        return bpy.data.images[tex_num]
    return None


def remove_tex_by_name(name):
    tex = find_tex_by_name(name)
    if tex is not None:
        bpy.data.images.remove(tex)


def remove_mat_by_name(name):
    mat_num = bpy.data.materials.find(name)
    if mat_num >= 0:
        bpy.data.materials.remove(bpy.data.materials[mat_num])


def show_texture_in_mat(tex_name, mat_name):
    tex = find_tex_by_name(tex_name)
    mat = get_mat_by_name(mat_name)
    principled_node = get_shader_node(
        mat, 'BSDF_PRINCIPLED', 'ShaderNodeBsdfPrincipled')
    image_node = get_shader_node(
        mat, 'TEX_IMAGE', 'ShaderNodeTexImage')
    image_node.image = tex
    image_node.location = Config.image_node_layout_coord
    principled_node.inputs['Specular'].default_value = 0.0
    mat.node_tree.links.new(
        image_node.outputs['Color'],
        principled_node.inputs['Base Color'])
    return mat


def _create_texture_builder_from_settings(settings):
    tb = pkt.module().TextureBuilder()
    tb.set_output_texture_size((settings.tex_width, settings.tex_height))
    tb.set_face_angles_affection(settings.tex_face_angles_affection)
    tb.set_uv_expand_percents(settings.tex_uv_expand_percents)
    tb.set_back_face_culling(settings.tex_back_face_culling)
    tb.set_equalize_brightness(settings.tex_equalize_brightness)
    tb.set_equalize_colour(settings.tex_equalize_colour)
    return tb


def _remove_bpy_texture_if_exists(tex_name):
    logger = logging.getLogger(__name__)
    tex_num = bpy.data.images.find(tex_name)
    if tex_num >= 0:
        logger.debug("TEXTURE WITH THAT NAME ALREADY EXISTS. REMOVING")
        existing_tex = bpy.data.images[tex_num]
        bpy.data.images.remove(existing_tex)


def _create_bpy_texture_from_img(img, tex_name):
    logger = logging.getLogger(__name__)
    assert(len(img.shape) == 3 and img.shape[2] == 4)

    _remove_bpy_texture_if_exists(tex_name)

    tex = bpy.data.images.new(
            tex_name, width=img.shape[1], height=img.shape[0],
            alpha=True, float_buffer=False)
    assert(tex.name == tex_name)
    tex.pixels[:] = img.ravel()
    tex.pack()

    logger.debug("TEXTURE BAKED SUCCESSFULLY")


def _cam_image_data_exists(cam):
    if not cam.cam_image:
        return False
    w, h = cam.cam_image.size[:2]
    return w > 0 and h > 0


def _get_fb_for_bake_tex(headnum, head):
    logger = logging.getLogger(__name__)
    FBLoader.load_model(headnum)
    fb = FBLoader.get_builder()
    for i, m in enumerate(head.get_masks()):
        fb.set_mask(i, m)

    uv_shape = head.tex_uv_shape
    logger.debug("UV_TYPE: {}".format(uv_shape))
    if uv_shape == 'uv1':
        fb.select_uv_set(1)
    elif uv_shape == 'uv2':
        fb.select_uv_set(2)
    elif uv_shape == 'uv3':
        fb.select_uv_set(3)
    else:
        fb.select_uv_set(0)

    return fb


def _create_frame_data_loader(settings, head, camnums, fb):
    def frame_data_loader(kf_idx):
        cam = head.cameras[camnums[kf_idx]]

        w, h = cam.cam_image.size[:2]
        img = np.rot90(
            np.asarray(cam.cam_image.pixels[:]).reshape((h, w, 4)),
            cam.orientation)

        if w < h:  # Fix for Blender Camera Auto-mode
            sw = head.sensor_width * \
                 settings.frame_width / settings.frame_height
        else:
            sw = head.sensor_width
        pm = projection_matrix(w, h, head.focal, sw,
                               near=0.1, far=1000.)
        if cam.orientation % 2 > 0:
            offset = np.array([[1., 0., 0., (h - w) * 0.5],
                               [0., 1., 0., (w - h) * 0.5],
                               [0., 0., 1., 0.],
                               [0., 0., 0., 1.]])
            projection = offset @ pm
        else:
            projection = pm

        frame_data = pkt.module().TextureBuilder.FrameData()
        frame_data.geo = fb.applied_args_model_at(cam.get_keyframe())
        frame_data.image = img
        frame_data.model = cam.get_model_mat()
        frame_data.view = np.eye(4)
        frame_data.projection = projection

        return frame_data

    return frame_data_loader


def bake_tex(headnum, tex_name):
    logger = logging.getLogger(__name__)
    settings = get_main_settings()
    head = settings.get_head(headnum)

    if not head.has_cameras():
        logger.debug("NO CAMERAS ON HEAD")
        return False

    camnums = [cam_idx for cam_idx, cam in enumerate(head.cameras)
               if cam.use_in_tex_baking and \
                  _cam_image_data_exists(cam) and \
                  cam.has_pins()]

    frames_count = len(camnums)
    if frames_count == 0:
        logger.debug("NO FRAMES FOR TEXTURE BUILDING")
        return False

    tb = _create_texture_builder_from_settings(settings)

    fb = _get_fb_for_bake_tex(headnum, head)
    frame_data_loader = _create_frame_data_loader(
        settings, head, camnums, fb)

    def progress_callback(progress):
        bpy.context.window_manager.progress_update(progress)
        return False

    #-------------- New baking
    # bpy.context.window_manager.progress_begin(0, 1)
    # built_texture = tb.build_texture(
    #     frames_count, frame_data_loader, progress_callback)
    # bpy.context.window_manager.progress_end()

    #-------------- Old baking
    imgs = []
    geos = []
    projections = []
    keyframes = []
    model_views = [head.cameras[x].get_model_mat() for x in camnums]

    for i, cam in enumerate(head.cameras):
        if cam.use_in_tex_baking and cam.cam_image and cam.has_pins():
            w, h = cam.cam_image.size[:3]
            if w > 0 and h > 0:
                img = np.rot90(
                    np.asarray(cam.cam_image.pixels[:]).reshape((h, w, 4)),
                    cam.orientation)

                pm = cam.get_projection_matrix()
                projections.append(pm)

                imgs.append(img)
                keyframes.append(cam.get_keyframe())
                camnums.append(i)
                geos.append(fb.applied_args_model_at(cam.get_keyframe()))

    if len(keyframes) == 0:
        return
    built_texture = tb.build_texture(geos, imgs, model_views, projections)
    #-------------- Old baking

    _create_bpy_texture_from_img(built_texture, tex_name)
    return True
