# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2019-2022  KeenTools

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

from typing import Optional

import bpy
from bpy.types import Image, Scene, Mask

from .kt_logging import KTLogger
from .bpy_common import (bpy_new_scene,
                         bpy_new_image,
                         bpy_render_frame,
                         bpy_scene,
                         get_scene_by_name)
from .images import copy_pixels_data, find_bpy_image_by_name, remove_bpy_image


_log = KTLogger(__name__)


def get_viewer_node_image() -> Optional[Image]:
    for img in bpy.data.images:
        if img.type == 'COMPOSITING':
            return img  # Blender uses the first one available
    return None


def get_mask_by_name(mask_name: str) -> Optional[Mask]:
    mask_num = bpy.data.masks.find(mask_name)
    if mask_num >= 0:
        return bpy.data.masks[mask_num]
    return None


def create_compositing_shadow_scene(src_scene: Scene, scene_name: str,
                                    mask_name: str) -> Scene:
    shadow_scene = bpy_new_scene(scene_name)
    shadow_scene.use_nodes = True
    shadow_scene.render.use_compositing = True
    w = src_scene.render.resolution_x
    h = src_scene.render.resolution_y
    shadow_scene.render.resolution_x = w
    shadow_scene.render.resolution_y = h
    shadow_scene.view_settings.view_transform = 'Standard'
    shadow_scene.frame_current = src_scene.frame_current
    create_mask_compositing_node_tree(shadow_scene, mask_name,
                                      clear_nodes=False)
    return shadow_scene


def get_compositing_shadow_scene(scene_name: str) -> Scene:
    shadow_scene = get_scene_by_name(scene_name)
    if shadow_scene is None:
        shadow_scene = create_compositing_shadow_scene(
            bpy_scene(), scene_name, mask_name='')  # Scene with empty mask
    return shadow_scene


def create_mask_compositing_node_tree(scene: Scene, mask_name: str,
                                      clear_nodes: bool=True) -> None:
    mask = get_mask_by_name(mask_name)
    node_tree = scene.node_tree
    if clear_nodes:
        node_tree.nodes.clear()
    comp_node = node_tree.nodes.new(type='CompositorNodeComposite')
    mask_node = node_tree.nodes.new(type='CompositorNodeMask')
    viewer_node = node_tree.nodes.new(type='CompositorNodeViewer')
    mask_node.mask = mask
    node_tree.links.new(mask_node.outputs[0], comp_node.inputs[0])
    comp_node.location.x += 200
    node_tree.links.new(mask_node.outputs[0], viewer_node.inputs[0])
    viewer_node.location.x += 200
    viewer_node.location.y -= 300


def viewer_node_to_image(img: Image) -> bool:
    vn_img = get_viewer_node_image()
    _log.output(f'viewer_node_to_image: {vn_img}')
    if vn_img is None:
        return False
    vw, vh = vn_img.size[:]
    rw, rh = bpy_render_frame()
    if vw != rw or vh != rh:
        _log.output(f'viewer_node_to_image sizes: {vw, vh, rw, rh}')
        return False
    copy_pixels_data(vn_img.pixels, img.pixels)
    return True


def get_rendered_mask_bpy_image(img_name: str) -> Image:
    rw, rh = bpy_render_frame()
    img = find_bpy_image_by_name(img_name)
    if not img or img.size[0] != rw or img.size[1] != rh:
        remove_bpy_image(img)
        img = bpy_new_image(img_name, width=rw, height=rh, alpha=True,
                            float_buffer=False)
    return img
