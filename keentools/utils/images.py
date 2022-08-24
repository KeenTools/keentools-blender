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

from ..addon_config import Config


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


def gamma_np_image(np_img, gamma=1.0):
    res_img = np_img.copy()
    res_img[:, :, :3] = np.power(np_img[:, :, :3], gamma)
    return res_img


def get_background_image_object(camobj):
    cam_data = camobj.data
    if len(cam_data.background_images) == 0:
        bg_img = cam_data.background_images.new()
    else:
        bg_img = cam_data.background_images[0]
    return bg_img


def set_background_image_by_movieclip(camobj, movie_clip, name='geotracker_bg'):
    if not camobj or not movie_clip:
        return
    bg_img = get_background_image_object(camobj)
    bg_img.alpha = 1.0
    cam_data = camobj.data
    cam_data.show_background_images = True

    bg_img.source = 'IMAGE'
    img = bg_img.image
    if not img:
        w, h = movie_clip.size[:]
        img = bpy.data.images.new(name, width=w, height=h, alpha=True,
                                  float_buffer=False)
        bg_img.image = img

    img.source = 'SEQUENCE' if movie_clip.frame_duration > 1 else 'FILE'
    img.filepath = movie_clip.filepath

    bg_img.image_user.frame_duration = movie_clip.frame_duration
    bg_img.image_user.frame_start = 1
    bg_img.image_user.use_auto_refresh = True


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


def np_image_to_grayscale(np_img):
    return (255 * 0.2989 * np_img[:, :, 0] +
            255 * 0.5870 * np_img[:, :, 1] +
            255 * 0.1140 * np_img[:, :, 2]).astype(np.uint8)


def np_array_from_background_image(camobj):
    bg_img = get_background_image_object(camobj)
    np_img = np_array_from_bpy_image(bg_img.image)
    return np_img


def reset_tone_mapping(cam_image):
    if not cam_image:
        return
    if cam_image.is_dirty:
        cam_image.reload()
        logger = logging.getLogger(__name__)
        logger.debug('reset_tone_mapping: IMAGE RELOADED')


def tone_mapping(cam_image, exposure, gamma):
    if not cam_image:
        return
    reset_tone_mapping(cam_image)
    logger = logging.getLogger(__name__)

    if np.all(np.isclose([exposure, gamma], [Config.default_tone_exposure,
                                             Config.default_tone_gamma],
                                             atol=0.001)):
        logger.debug('SKIP tone mapping, only reload()')
        return
    np_img = np_array_from_bpy_image(cam_image)

    gain = pow(2, exposure / 2.2)
    np_img[:, :, :3] = np.power(gain * np_img[:, :, :3], 1.0 / gamma)
    assign_pixels_data(cam_image.pixels, np_img.ravel())
    logger.debug('restore_tone_mapping: exposure: {} '
                 '(gain: {}) gamma: {}'.format(exposure, gain, gamma))
