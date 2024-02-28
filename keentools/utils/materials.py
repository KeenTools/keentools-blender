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

from typing import Any, Tuple, List
import numpy as np

import bpy
from bpy.types import Object, Material

from .kt_logging import KTLogger
from .version import BVersion
from ..addon_config import fb_settings, ActionStatus
from ..facebuilder_config import FBConfig
from ..facebuilder.fbloader import FBLoader
from ..utils.images import load_rgba, find_bpy_image_by_name, assign_pixels_data
from ..blender_independent_packages.pykeentools_loader import module as pkt_module
from .bpy_common import bpy_progress_begin, bpy_progress_end, bpy_progress_update


_log = KTLogger(__name__)


def switch_to_mode(mode: str = 'MATERIAL') -> None:
    areas = bpy.context.workspace.screens[0].areas
    for area in areas:
        for space in area.spaces:
            if space.type == 'VIEW_3D':
                space.shading.type = mode


def toggle_mode(modes: Tuple[str]=('SOLID', 'MATERIAL')) -> None:
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


def assign_material_to_object(obj: Object, mat: Material) -> None:
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)


def copy_materials_from_object(from_obj: Object, to_obj: Object) -> bool:
    if not from_obj.data.materials:
        return False
    to_obj.data.materials.clear()
    for mat in from_obj.data.materials:
        to_obj.data.materials.append(mat)
    return True


def new_material(mat_name: str) -> Material:
    new_mat = bpy.data.materials.new(mat_name)
    new_mat.use_nodes = True
    return new_mat


def get_mat_by_name(mat_name: str) -> Material:
    if bpy.data.materials.find(mat_name) >= 0:
        return bpy.data.materials[mat_name]

    new_mat = new_material(mat_name)
    return new_mat


def new_shader_node(mat: Material, create_name: str) -> Any:
    return mat.node_tree.nodes.new(create_name)


def get_shader_node(mat: Material, find_type: str,
                    create_name: str) -> Material:
    for node in mat.node_tree.nodes:
        if node.type == find_type:
            return node
    return new_shader_node(mat, create_name)


def remove_mat_by_name(name: str) -> None:
    mat_num = bpy.data.materials.find(name)
    if mat_num >= 0:
        bpy.data.materials.remove(bpy.data.materials[mat_num])


def make_node_shader_matte(node: Any) -> None:
    if BVersion.principled_shader_has_specular:
        node.inputs['Specular'].default_value = 0.0
    else:
        node.inputs['IOR'].default_value = 1.0

def show_texture_in_mat(tex_name: str, mat_name: str) -> Material:
    tex = find_bpy_image_by_name(tex_name)
    mat = get_mat_by_name(mat_name)
    principled_node = get_shader_node(
        mat, 'BSDF_PRINCIPLED', 'ShaderNodeBsdfPrincipled')
    image_node = get_shader_node(
        mat, 'TEX_IMAGE', 'ShaderNodeTexImage')
    image_node.image = tex
    image_node.location = FBConfig.image_node_layout_coord
    make_node_shader_matte(principled_node)
    mat.node_tree.links.new(
        image_node.outputs['Color'],
        principled_node.inputs['Base Color'])
    return mat


def remove_bpy_texture_if_exists(tex_name: str) -> None:
    tex_num = bpy.data.images.find(tex_name)
    if tex_num >= 0:
        _log.output('TEXTURE WITH THAT NAME ALREADY EXISTS. REMOVING')
        existing_tex = bpy.data.images[tex_num]
        bpy.data.images.remove(existing_tex)


def _create_bpy_texture_from_img(img: Any, tex_name: str) -> None:
    assert(len(img.shape) == 3 and img.shape[2] == 4)

    remove_bpy_texture_if_exists(tex_name)

    tex = bpy.data.images.new(
            tex_name, width=img.shape[1], height=img.shape[0],
            alpha=True, float_buffer=False)
    assert(tex.name == tex_name)
    try:
        tex.colorspace_settings.name = 'sRGB'
    except TypeError as err:
        _log.error(f'_create_bpy_texture_from_img '
                   f'color space sRGB is not found:\n{str(err)}')
    assign_pixels_data(tex.pixels, img.ravel())
    tex.pack()

    _log.output('TEXTURE BAKED SUCCESSFULLY')


def _cam_image_data_exists(cam: Any) -> bool:
    if not cam.cam_image:
        return False
    w, h = cam.cam_image.size[:2]
    return w > 0 and h > 0


def _get_fb_for_bake_tex(headnum: int, head: Any) -> Any:
    FBLoader.load_model(headnum)
    fb = FBLoader.get_builder()
    for i, m in enumerate(head.get_masks()):
        fb.set_mask(i, m)

    FBLoader.select_uv_set(fb, head.tex_uv_shape)
    return fb


def _sRGB_to_linear(img: Any) -> Any:
    img_rgb = img[:, :, :3]
    img_rgb[img_rgb < 0.04045] = 25 * img_rgb[img_rgb < 0.04045] / 323
    img_rgb[img_rgb >= 0.04045] = ((200 * img_rgb[img_rgb >= 0.04045] + 11) / 211) ** (12 / 5)
    return img


def _create_frame_data_loader(head: Any, camnums: List, fb: Any) -> Any:
    def frame_data_loader(kf_idx):
        cam = head.cameras[camnums[kf_idx]]
        cam.reset_tone_mapping()

        img = load_rgba(cam)

        frame_data = pkt_module().texture_builder.FrameData()
        frame_data.geo = fb.applied_args_model_at(cam.get_keyframe())
        frame_data.image = img
        frame_data.model = fb.model_mat(cam.get_keyframe())
        frame_data.view = np.eye(4)
        frame_data.projection = cam.get_projection_matrix()

        return frame_data

    return frame_data_loader


def bake_tex(headnum: int, tex_name: str) -> ActionStatus:
    settings = fb_settings()
    head = settings.get_head(headnum)

    if not head.has_cameras():
        msg = 'No cameras on Head'
        _log.error(msg)
        return ActionStatus(False, msg)

    camnums = [cam_idx for cam_idx, cam in enumerate(head.cameras)
               if cam.use_in_tex_baking and \
                  _cam_image_data_exists(cam) and \
                  cam.has_pins()]

    frames_count = len(camnums)
    if frames_count == 0:
        msg = 'No frames for texture building'
        _log.error(msg)
        return ActionStatus(False, msg)
    
    fb = _get_fb_for_bake_tex(headnum, head)
    frame_data_loader = _create_frame_data_loader(head, camnums, fb)

    bpy_progress_begin(0, 1)

    class ProgressCallBack(pkt_module().ProgressCallback):
        def set_progress_and_check_abort(self, progress):
            bpy_progress_update(progress)
            return False

    progress_callBack = ProgressCallBack()
    built_texture = pkt_module().texture_builder.build_texture(
        frames_count, frame_data_loader, progress_callBack,
        settings.tex_height, settings.tex_width, settings.tex_face_angles_affection,
        settings.tex_uv_expand_percents, settings.tex_back_face_culling,
        settings.tex_equalize_brightness, settings.tex_equalize_colour, settings.tex_fill_gaps)
    bpy_progress_end()

    _create_bpy_texture_from_img(built_texture, tex_name)
    return ActionStatus(True, 'ok')


def get_nodes_by_type(nodes: List, find_type: str) -> List:
    return [node for node in nodes if node.type == find_type]


def get_node_from_input(node: Any, num: int = 0) -> Any:
    if len(node.inputs) < num + 1:
        return None
    input = node.inputs[num]
    if len(input.links) < 1:
        return None
    return input.links[0].from_node
