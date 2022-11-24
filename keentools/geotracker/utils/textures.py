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
from typing import Any, List, Optional

import bpy
from bpy.types import Object, Area

from ...utils.kt_logging import KTLogger
from ...utils.bpy_common import (bpy_current_frame,
                                 bpy_set_current_frame,
                                 bpy_timer_register)
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
from ...addon_config import get_operator
from ...geotracker_config import GTConfig, get_gt_settings
from ..gtloader import GTLoader
from .prechecks import prepare_camera
from ...utils.other import unhide_viewport_ui_elements_from_object
from ...utils.localview import exit_area_localview


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
        progress_callBack, tex_height, tex_width, face_angles_affection=3.0)

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


_bake_generator_var = None


def bake_generator(area: Area, geotracker: Any, filepath_pattern: str,
                   *, file_format: str='PNG',
                   from_frame: int=1, to_frame: int=10, digits: int=4,
                   width: int=2048, height: int=2048):
    def _finish():
        settings.stop_calculating()
        GTLoader.viewport().revert_default_screen_message(
            unregister=not settings.pinmode)
        if tex is not None:
            remove_bpy_image(tex)
        if not settings.pinmode:
            unhide_viewport_ui_elements_from_object(area, geotracker.camobj)
            exit_area_localview(area)
        settings.user_interrupts = True

    delta = 0.001
    settings = get_gt_settings()
    settings.calculating_mode = 'REPROJECT'
    op = get_operator(GTConfig.gt_interrupt_modal_idname)
    op('INVOKE_DEFAULT')
    GTLoader.viewport().message_to_screen(
        [{'text': 'Reproject is calculating... Please wait',
          'color': (1.0, 0., 0., 0.7)}])

    tex = None
    total_frames = to_frame - from_frame + 1
    for frame in range(total_frames):
        current_frame = from_frame + frame
        if settings.user_interrupts:
            _finish()
            return None

        GTLoader.viewport().message_to_screen(
            [{'text': 'Reprojection: '
                      f'{frame + 1}/{total_frames}', 'y': 60,
              'color': (1.0, 0.0, 0.0, 0.7)},
             {'text': 'ESC to interrupt', 'y': 30,
              'color': (1.0, 1.0, 1.0, 0.7)}])
        settings.user_percent = 100 * frame / total_frames
        bpy_set_current_frame(current_frame)

        yield delta

        built_texture = bake_texture(geotracker, [current_frame],
                                     tex_width=width, tex_height=height)
        if tex is None:
            tex = create_compatible_bpy_image(built_texture)
        tex.filepath_raw = filepath_pattern.format(str(current_frame).zfill(digits))
        tex.file_format = file_format
        assign_pixels_data(tex.pixels, built_texture.ravel())
        tex.save()
        _log.output(f'TEXTURE SAVED: {tex.filepath}')

        yield delta

    _finish()
    return None


def _bake_caller() -> Optional[float]:
    global _bake_generator_var
    if _bake_generator_var is None:
        return None
    try:
        return next(_bake_generator_var)
    except StopIteration:
        _log.output('Texture sequence baking generator is over')
    _bake_generator_var = None
    return None


def bake_texture_sequence(context: Any, geotracker: Any, filepath_pattern: str,
                          *, file_format: str='PNG',
                          from_frame: int=1, to_frame: int=10, digits: int=4,
                          width: int=2048, height: int=2048) -> None:
    global _bake_generator_var
    _bake_generator_var = bake_generator(context.area, geotracker, filepath_pattern,
                                         file_format=file_format,
                                         from_frame=from_frame,
                                         to_frame=to_frame, digits=digits,
                                         width=width, height=height)
    prepare_camera(context.area)
    settings = get_gt_settings()
    if not settings.pinmode:
        vp = GTLoader.viewport()
        vp.texter().register_handler(context)
    bpy_timer_register(_bake_caller, first_interval=0.0)
