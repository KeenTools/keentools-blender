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
import numpy as np
import bpy


def find_bpy_image_by_name(image_name):
    image_num = bpy.data.images.find(image_name)
    if image_num >= 0:
        return bpy.data.images[image_num]
    return None


def remove_bpy_image(image):
    if image and image in bpy.data.images:
        bpy.data.images.remove(image)


def remove_bpy_image_by_name(image_name):
    image = find_bpy_image_by_name(image_name)
    if image is not None:
        bpy.data.images.remove(image)


def store_bpy_image_in_scene(image):
    image.pack()
    image.use_fake_user = True


def add_alpha_channel(np_image_array):
    return np.dstack((np_image_array, np.ones(np_image_array.shape[:2])))


def check_bpy_image_size(image):
    if not image or not image.size:
        return False
    w, h = image.size[:2]
    return w > 0 and h > 0


def check_bpy_image_has_same_size(image, size):
    if not image or not image.size:
        return False
    w, h = image.size[:2]
    return w == size[0] and h == size[1]


def safe_bpy_image_loading(blender_name, path):
    tex = find_bpy_image_by_name(blender_name)
    if tex is not None:
        if check_bpy_image_size(tex):
            return tex
        else:
            remove_bpy_image_by_name(blender_name)
    try:
        image = bpy.data.images.load(path)
        image.name = blender_name
    except Exception:
        logger = logging.getLogger(__name__)
        logger.error('Source texture for "{}" '
                     'is not found on path: {}'.format(blender_name, path))
        return None
    if not check_bpy_image_size(image):
        return None
    return image


def safe_bpy_image_in_scene_loading(blender_name, path):
    logger = logging.getLogger(__name__)
    tex = find_bpy_image_by_name(blender_name)
    if tex is not None:
        if check_bpy_image_size(tex):
            return tex
        else:
            remove_bpy_image_by_name(blender_name)
    try:
        image = bpy.data.images.load(path)
    except Exception:
        logger.error('Source texture for "{}" '
                     'is not found on path: {}'.format(blender_name, path))
        return None
    if not check_bpy_image_size(image):
        bpy.data.images.remove(image)
        logger.error('Source texture "{}" '
                     'has wrong format on path: {}'.format(blender_name, path))
        return None

    tex = bpy.data.images.new(blender_name,
                              width=image.size[0], height=image.size[1],
                              alpha=True, float_buffer=False)
    tex.pixels[:] = image.pixels[:]
    store_bpy_image_in_scene(tex)
    bpy.data.images.remove(image)
    return tex
