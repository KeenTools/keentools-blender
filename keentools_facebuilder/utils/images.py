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
import bpy


_pixels_foreach_exists = None


def _get_pixels_foreach_exists():
    global _pixels_foreach_exists
    if _pixels_foreach_exists is None:
        ver = bpy.app.version
        _pixels_foreach_exists = ver >= (2, 83, 0)
    return _pixels_foreach_exists


def assign_pixels_data(pixels, data):
    if _get_pixels_foreach_exists():
        pixels.foreach_set(data)
    else:
        pixels[:] = data


def get_pixels_data(pixels, data):
    if _get_pixels_foreach_exists():
        pixels.foreach_get(data)
    else:
        data[:] = pixels[:]


def np_array_from_bpy_image(bpy_image):
    if not bpy_image or not bpy_image.size or not bpy_image.channels:
        return None
    w, h = bpy_image.size[:2]
    if w > 0 and h > 0:
        np_img = np.empty((h, w, bpy_image.channels), dtype=np.float32)
        get_pixels_data(bpy_image.pixels, np_img.ravel())
    else:
        return None
    return np_img


def load_rgba(camera):
    if not camera or camera.cam_image is None:
        return None

    img = np_array_from_bpy_image(camera.cam_image)
    if img is None:
        return None
    return np.rot90(img, camera.orientation)


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
