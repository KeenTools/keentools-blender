# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2019-2024  KeenTools

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

from typing import Any, Tuple, List, Optional
import numpy as np

from .kt_logging import KTLogger
from ..facebuilder_config import FBConfig
from .bpy_common import bpy_new_image
from .images import (check_bpy_image_has_same_size,
                     find_bpy_image_by_name,
                     remove_bpy_image,
                     assign_pixels_data)
from ..blender_independent_packages.pykeentools_loader import module as pkt_module


_log = KTLogger(__name__)
_fb: Optional[Any] = None


def _get_fb() -> Any:
    global _fb
    if _fb is None:
        class _FBCameraInput(pkt_module().FaceBuilderCameraInputI):
            def projection(self, frame):
                assert frame == 0
                return pkt_module().math.proj_mat(
                    fl_to_haperture=50.0 / 36, w=1920.0, h=1080.0,
                    pixel_aspect_ratio=1.0, near=0.1, far=1000.0)

            def view(self, frame):
                assert frame == 0
                return np.eye(4)

            def image_size(self, frame):
                assert frame == 0
                return 1920, 1080

        _fb = pkt_module().FaceBuilder(_FBCameraInput())
    return _fb


def create_wireframe_image(texture_colors: List) -> bool:
    _log.yellow('create_wireframe_image')
    fb = _get_fb()
    if not fb.face_texture_available():
        _log.error('create_wireframe_image: cannot initialize image 1')
        return False

    fb.set_face_texture_colors(texture_colors)
    image_data = fb.face_texture()
    size = image_data.shape[:2]
    if not (size[0] > 0) or not (size[1] > 0):
        _log.error('create_wireframe_image: cannot initialize image 2')
        return False

    image_name = FBConfig.coloring_texture_name
    wireframe_image = find_bpy_image_by_name(image_name)
    if wireframe_image is None or \
            not check_bpy_image_has_same_size(wireframe_image, size):
        remove_bpy_image(wireframe_image)
        wireframe_image = bpy_new_image(image_name,
                                        width=size[1],
                                        height=size[0],
                                        alpha=True,
                                        float_buffer=False)
    if wireframe_image:
        rgba = np.ones((size[1], size[0], 4), dtype=np.float32)
        rgba[:, :, :3] = image_data
        assign_pixels_data(wireframe_image.pixels, rgba.ravel())
        wireframe_image.pack()
        return True

    _log.error('create_wireframe_image: cannot initialize image 3')
    return False
