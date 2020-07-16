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

__all__ = [
    'load_rgba',
    'load_unchanged_rgba'
]

import contextlib
import hashlib
import os
import os.path
import shutil
import tempfile

import numpy as np

import bpy

import keentools_facebuilder.blender_independent_packages.pykeentools_loader as pkt


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


@contextlib.contextmanager
def _standard_view_transform():
    # This is done to enforce correct image saving
    view_transform = bpy.context.scene.view_settings.view_transform
    bpy.context.scene.view_settings.view_transform = 'Standard'
    try:
        yield
    finally:
        bpy.context.scene.view_settings.view_transform = view_transform


def load_unchanged_rgba(camera):
    abs_path = camera.get_abspath()
    if abs_path is None:
        return None

    with _tmp_image_path(abs_path) as tmp_path:
        with _standard_view_transform():
            camera.cam_image.save_render(tmp_path)
        img = pkt.module().imread(tmp_path)
        if img is None:
            w, h = camera.cam_image.size[:2]
            img = np.array(camera.cam_image.pixels[:]).reshape((h, w, 4))

    return img.astype(np.float32)


def load_rgba(camera):
    img = load_unchanged_rgba(camera)
    if img is None:
        return None
    return np.rot90(img, camera.orientation)
