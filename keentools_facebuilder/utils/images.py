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

import contextlib
import hashlib
import logging
import os
import os.path
import shutil
import tempfile

import numpy as np

import bpy
import bgl

from ..blender_independent_packages.pykeentools_loader import module as pkt_module
from ..config import Config


_TMP_IMAGES_DIR = os.path.join(tempfile.gettempdir(), 'pykeentools_tmp_images')


def _make_tmp_path(abs_path):
    sha1 = hashlib.sha1()
    sha1.update(abs_path.encode())
    return os.path.join(_TMP_IMAGES_DIR, sha1.hexdigest() + '.png')


@contextlib.contextmanager
def _tmp_image_path(curr_abs_path):
    shutil.rmtree(_TMP_IMAGES_DIR, ignore_errors=True)
    try:
        os.makedirs(_TMP_IMAGES_DIR, exist_ok=True)
        yield _make_tmp_path(curr_abs_path)
    finally:
        shutil.rmtree(_TMP_IMAGES_DIR, ignore_errors=True)


def _get_color_transform_state():
    vs = bpy.context.scene.view_settings
    ds = bpy.context.scene.display_settings
    return {
        'display_device': ds.display_device,
        'view_transform': vs.view_transform,
        'look': vs.look,
        'exposure': vs.exposure,
        'gamma': vs.gamma,
        'use_curve_mapping': vs.use_curve_mapping
    }


def _set_color_transform_state(state):
    success_flag = True

    ds = bpy.context.scene.display_settings
    try:
        ds.display_device = state['display_device']
    except TypeError as err:
        success_flag = False
        logger = logging.getLogger(__name__)
        logger.error('_set_color_transform_state Exception: {}'.format(str(err)))

    vs = bpy.context.scene.view_settings
    vs.view_transform = state['view_transform']
    vs.look = state['look']
    vs.exposure = state['exposure']
    vs.gamma = state['gamma']
    vs.use_curve_mapping = state['use_curve_mapping']
    return success_flag


def _default_color_transform_state():
    return {
        'display_device': 'sRGB',
        'view_transform': 'Standard',
        'look': 'None',
        'exposure': 0.0,
        'gamma': 1.0,
        'use_curve_mapping': False
    }


@contextlib.contextmanager
def _standard_view_transform():
    # This is done to enforce correct image saving
    state = _get_color_transform_state()
    _set_color_transform_state(_default_color_transform_state())

    try:
        yield
    finally:
        _set_color_transform_state(state)


def load_unchanged_rgba(camera):
    abs_path = camera.get_abspath()
    if abs_path is None:
        return None

    with _tmp_image_path(abs_path) as tmp_path:
        with _standard_view_transform():
            camera.cam_image.save_render(tmp_path)
        img = pkt_module().read_png(tmp_path)

    if img is None:
        if camera.cam_image is None:
            return None
        w, h = camera.cam_image.size[:2]
        img = np.array(camera.cam_image.pixels[:]).reshape((h, w, 4))

    return img.astype(np.float32)


def np_array_from_bpy_image_using_gpu(bpy_image):
    if not check_bpy_image_size(bpy_image):
        return None
    np_array = np.empty((bpy_image.size[1], bpy_image.size[0], bpy_image.channels), dtype=np.float32)
    if bpy_image.gl_load():
        return None
    bgl.glActiveTexture(bgl.GL_TEXTURE0)
    bgl.glBindTexture(bgl.GL_TEXTURE_2D, bpy_image.bindcode)
    buffer = bgl.Buffer(bgl.GL_FLOAT, np_array.shape, np_array)
    bgl.glGetTexImage(bgl.GL_TEXTURE_2D, 0, bgl.GL_RGBA, bgl.GL_FLOAT, buffer)
    bgl.glBindTexture(bgl.GL_TEXTURE_2D, 0)
    return np_array


def load_rgba(camera):
    if camera.cam_image is None:
        return None

    if Config.use_gpu_texture_loading:
        img = np_array_from_bpy_image_using_gpu(camera.cam_image)
    else:
        img = None
    if img is None:
        logger = logging.getLogger(__name__)
        logger.error('GPU texture acceleration '
                     'does not work: {}'.format(camera.cam_image))
        img = load_unchanged_rgba(camera)
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
