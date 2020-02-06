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
    # Switch to Mode
    areas = bpy.context.workspace.screens[0].areas
    for area in areas:
        for space in area.spaces:
            if space.type == 'VIEW_3D':
                space.shading.type = mode


def toggle_mode(modes=('SOLID', 'MATERIAL')):
    # Switch to Mode
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


def get_mesh_uvmap(mesh):
    # if no UVtex - create it
    if not len(mesh.uv_layers) > 0:
        uvtex = mesh.uv_layers.new()
    else:
        uvtex = mesh.uv_layers.active
    return uvtex.data


def assign_mat(obj, mat):
    # Assign Material to Object
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)


def get_mat_by_name(mat_name):
    if bpy.data.materials.find(mat_name) >= 0:
        # Material exists
        mat = bpy.data.materials[mat_name]
    else:
        # Create new material
        mat = bpy.data.materials.new(mat_name)
        mat.use_nodes = True
    return mat


def get_shader_node(mat, find_name, create_name):
    # Looking for node
    nodnum = mat.node_tree.nodes.find(find_name)
    if nodnum >= 0:
        shader_node = mat.node_tree.nodes[nodnum]
    else:
        shader_node = mat.node_tree.nodes.new(create_name)
    return shader_node


def find_tex_by_name(tex_name):
    tex_num = bpy.data.images.find(tex_name)
    if tex_num >= 0:
        tex = bpy.data.images[tex_num]
    else:
        tex = None
    return tex


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
        mat, 'Principled BSDF', 'ShaderNodeBsdfPrincipled')
    image_node = get_shader_node(
        mat, 'Image Texture', 'ShaderNodeTexImage')
    image_node.image = tex
    image_node.location = Config.image_node_layout_coord
    principled_node.inputs['Specular'].default_value = 0.0
    mat.node_tree.links.new(
        image_node.outputs['Color'],
        principled_node.inputs['Base Color'])
    return mat


def bake_tex(headnum, tex_name):
    logger = logging.getLogger(__name__)
    settings = get_main_settings()
    head = settings.get_head(headnum)

    if not head.has_cameras():
        logger.debug("NO CAMERAS ON HEAD")
        return None

    FBLoader.load_only(headnum)
    fb = FBLoader.get_builder()

    mesh = head.headobj.data
    uvmap = get_mesh_uvmap(mesh)

    uv_shape = head.tex_uv_shape
    if uv_shape == 'uv1':
        fb.select_uv_set(1)
    elif uv_shape == 'uv2':
        fb.select_uv_set(2)
    elif uv_shape == 'uv3':
        fb.select_uv_set(3)
    else:
        fb.select_uv_set(0)  # default UV

    logger.debug("UV_TYPE: {}".format(uv_shape))

    geo = fb.applied_args_model()
    me = geo.mesh(0)

    uvs_count = me.uvs_count()
    for i in range(uvs_count):
        uvmap[i].uv = me.uv(i)

    wm = bpy.context.window_manager
    wm.progress_begin(0, len(head.cameras) + 1.0)

    imgs = []
    keyframes = []
    camnums = []
    geos = []
    projections = []

    for i, cam in enumerate(head.cameras):
        wm.progress_update(i + 1.0)
        # Bake only if 1) Marked 2) Image is exists 3) Some pins added
        if cam.use_in_tex_baking and cam.cam_image and cam.has_pins():
            w, h = cam.cam_image.size[:3]
            if w > 0 and h > 0:  # 4) Image data exists
                img = np.rot90(
                    np.asarray(cam.cam_image.pixels[:]).reshape((h, w, 4)),
                    cam.orientation)  # Slow operation .pixels[:]

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
                    projections.append(offset @ pm)
                else:
                    projections.append(pm)

                imgs.append(img)
                keyframes.append(cam.get_keyframe())
                camnums.append(i)
                geos.append(fb.applied_args_model_at(cam.get_keyframe()))

    wm.progress_end()

    # Texture baking
    if len(keyframes) > 0:
        tb = pkt.module().TextureBuilder()
        tb.set_output_texture_size((settings.tex_width, settings.tex_height))
        tb.set_face_angles_affection(settings.tex_face_angles_affection)
        tb.set_uv_expand_percents(settings.tex_uv_expand_percents)
        tb.set_back_face_culling(settings.tex_back_face_culling)
        tb.set_equalize_brightness(settings.tex_equalize_brightness)
        tb.set_equalize_colour(settings.tex_equalize_colour)

        # geos = [geo for _ in keyframes]
        model_views = [head.cameras[x].get_model_mat() for x in camnums]

        texture = tb.build_texture(geos, imgs, model_views, projections)

        tex_num = bpy.data.images.find(tex_name)

        if tex_num >= 0:
            logger.debug("TEXTURE ALREADY EXISTS")
            tex = bpy.data.images[tex_num]
            bpy.data.images.remove(tex)

        tex = bpy.data.images.new(
                tex_name, width=settings.tex_width, height=settings.tex_height,
                alpha=True, float_buffer=False)
        tex.pixels[:] = texture.ravel()  # Slow operation
        tex.pack()  # Pack in blend-file
        logger.debug("TEXTURE BAKED SUCCESSFULLY: {}".format(tex.name))
        return tex.name
    else:
        logger.debug("NO KEYFRAMES")
    return None
