# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2019-2022 KeenTools

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
from typing import Any, List

import bpy
from bpy.types import Object

from ...utils.kt_logging import KTLogger
from ...utils.bpy_common import bpy_current_frame, bpy_set_current_frame
from ...blender_independent_packages.pykeentools_loader import module as pkt_module
from ...utils.mesh_builder import build_geo
from ...utils.images import np_array_from_background_image
from ...utils.coords import camera_projection
from ...utils.ui_redraw import total_redraw_ui
from ...utils.images import create_bpy_image_from_np_array
from ...utils.materials import (remove_bpy_texture_if_exists,
                                show_texture_in_mat,
                                assign_material_to_object,
                                switch_to_mode)
from ...utils.images import (create_compatible_bpy_image,
                             assign_pixels_data,
                             remove_bpy_image)


_log = KTLogger(__name__)


def bake_texture(geotracker: Any, selected_frames: List[int],
                 tex_width: int=2048, tex_height: int=2048) -> Any:
    def _create_frame_data_loader(geotracker, frame_numbers):
        def frame_data_loader(index):
            frame = frame_numbers[index]
            _log.output(f'frame_data_loader: {frame}')
            current_frame = bpy_current_frame()

            if frame != current_frame:
                bpy_set_current_frame(frame)
            total_redraw_ui()

            np_img = np_array_from_background_image(geotracker.camobj)
            geo = build_geo(geotracker.geomobj, evaluated=True, get_uv=True)
            frame_data = pkt_module().texture_builder.FrameData()
            frame_data.geo = geo
            frame_data.image = np_img
            frame_data.model = geotracker.calc_model_matrix()
            frame_data.view = np.eye(4)
            frame_data.projection = camera_projection(geotracker.camobj)
            return frame_data
        return frame_data_loader

    class ProgressCallBack(pkt_module().ProgressCallback):
        def set_progress_and_check_abort(self, progress):
            bpy.context.window_manager.progress_update(progress)
            return False

    progress_callBack = ProgressCallBack()

    current_frame = bpy_current_frame()
    bpy.context.window_manager.progress_begin(0, 1)
    built_texture = pkt_module().texture_builder.build_texture(
        len(selected_frames),
        _create_frame_data_loader(geotracker, selected_frames),
        progress_callBack, tex_height, tex_width)

    bpy.context.window_manager.progress_end()

    bpy_set_current_frame(current_frame)
    return built_texture


def preview_material_with_texture(
        built_texture: Any, geomobj: Object,
        tex_name: str='kt_reprojected_tex',
        mat_name: str='kt_reproject_preview_mat') -> None:
    if built_texture is None:
        return
    remove_bpy_texture_if_exists(tex_name)
    img = create_bpy_image_from_np_array(built_texture, tex_name)
    img.pack()

    mat = show_texture_in_mat(img.name, mat_name)
    assign_material_to_object(geomobj, mat)
    switch_to_mode('MATERIAL')


def bake_texture_sequence(geotracker, filepath_pattern, *, file_format='PNG',
                          from_frame=1, to_frame=10, digits=4,
                          width=2048, height=2048) -> None:
    current_frame = bpy_current_frame()
    tex = None
    for frame in range(from_frame, to_frame + 1):
        built_texture = bake_texture(geotracker, [frame],
                                     tex_width=width, tex_height=height)
        if tex is None:
            tex = create_compatible_bpy_image(built_texture)
        tex.filepath_raw = filepath_pattern.format(str(frame).zfill(digits))
        tex.file_format = file_format
        assign_pixels_data(tex.pixels, built_texture.ravel())
        tex.save()
        _log.output(f'TEXTURE SAVED: {tex.filepath}')
    bpy_set_current_frame(current_frame)
    remove_bpy_image(tex)
