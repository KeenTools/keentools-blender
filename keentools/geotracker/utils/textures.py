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
from typing import Any, List, Optional, Tuple

from bpy.types import Object, Area

from ...utils.kt_logging import KTLogger
from ...addon_config import gt_settings, get_settings, ProductType
from ...utils.version import BVersion
from ...utils.bpy_common import (bpy_current_frame,
                                 bpy_set_current_frame,
                                 bpy_render_frame,
                                 bpy_timer_register,
                                 bpy_progress_begin,
                                 bpy_progress_end,
                                 bpy_progress_update)
from ...blender_independent_packages.pykeentools_loader import module as pkt_module
from ...utils.mesh_builder import build_geo
from ...utils.images import (np_array_from_background_image,
                             create_bpy_image_from_np_array,
                             create_compatible_bpy_image,
                             assign_pixels_data,
                             remove_bpy_image)
from ...utils.coords import camera_projection
from ...utils.ui_redraw import (total_redraw_ui,
                                total_redraw_ui_overriding_window)
from ...utils.materials import (remove_bpy_texture_if_exists,
                                show_texture_in_mat,
                                assign_material_to_object,
                                switch_to_mode)
from ..gtloader import GTLoader
from .prechecks import prepare_camera
from ...utils.localview import exit_area_localview
from ..interface.screen_mesages import (revert_default_screen_message,
                                        single_line_screen_message,
                                        texture_projection_screen_message)


_log = KTLogger(__name__)


_bad_frame: int = -1


def _set_bad_frame(frame: int = -1):
    global _bad_frame
    _bad_frame = frame


def get_bad_frame():
    return _bad_frame


def bake_texture(geotracker: Any, selected_frames: List[int],
                 *, product: int) -> Any:
    def _empty_np_image() -> Any:
        w, h = bpy_render_frame()
        np_img = np.zeros((h, w, 4), dtype=np.float32)
        return np_img

    def _create_frame_data_loader(geotracker, frame_numbers):
        def frame_data_loader(index):
            frame = frame_numbers[index]
            _log.output(f'frame_data_loader: {frame}')
            current_frame = bpy_current_frame()

            if frame != current_frame:
                bpy_set_current_frame(frame)

            if not BVersion.open_dialog_overrides_area:
                total_redraw_ui()
            else:
                total_redraw_ui_overriding_window()

            np_img = np_array_from_background_image(geotracker.camobj, index=0)
            if np_img is None:
                _set_bad_frame(frame)
                return None

            geo = build_geo(geotracker.geomobj, get_uv=True)
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
            bpy_progress_update(progress)
            return False

    progress_callBack = ProgressCallBack()

    settings = get_settings(product)
    current_frame = bpy_current_frame()
    bpy_progress_begin(0, 1)
    _set_bad_frame()
    built_texture = pkt_module().texture_builder.build_texture(
        len(selected_frames),
        _create_frame_data_loader(geotracker, selected_frames),
        progress_callBack,
        settings.tex_height, settings.tex_width,
        settings.tex_face_angles_affection,
        settings.tex_uv_expand_percents,
        settings.tex_back_face_culling,
        settings.tex_equalize_brightness,
        settings.tex_equalize_colour,
        settings.tex_fill_gaps
    )

    bpy_progress_end()

    bpy_set_current_frame(current_frame)
    return built_texture


def preview_material_with_texture(
        built_texture: Any, geomobj: Object,
        tex_name: str = 'kt_reprojected_tex',
        mat_name: str = 'kt_reproject_preview_mat') -> Tuple:
    if built_texture is None:
        return None, None
    remove_bpy_texture_if_exists(tex_name)
    img = create_bpy_image_from_np_array(built_texture, tex_name)
    img.pack()

    mat = show_texture_in_mat(img.name, mat_name)
    assign_material_to_object(geomobj, mat)
    switch_to_mode('MATERIAL')
    return mat, img


_bake_generator_var: Optional[Any] = None


def bake_generator(area: Area, geotracker: Any, filepath_pattern: str,
                   *, file_format: str = 'PNG', frames: List[int],
                   digits: int = 4, product: int) -> Any:
    def _finish():
        settings.stop_calculating()
        revert_default_screen_message(unregister=not settings.pinmode,
                                      product=product)
        if tex is not None:
            remove_bpy_image(tex)
        if not settings.pinmode:
            settings.viewport_state.show_ui_elements(area)
            exit_area_localview(area)
        settings.user_interrupts = True

    delta = 0.001
    settings = get_settings(product)
    settings.calculating_mode = 'REPROJECT'

    single_line_screen_message('Projecting and baking… Please wait',
                               product=product)

    tex = None
    total_frames = len(frames)
    for num, frame in enumerate(frames):
        if settings.user_interrupts:
            _finish()
            return None

        texture_projection_screen_message(num + 1, total_frames, product=product)

        settings.user_percent = 100 * num / total_frames
        bpy_set_current_frame(frame)

        yield delta

        built_texture = bake_texture(geotracker, [frame], product=product)
        if tex is None:
            tex = create_compatible_bpy_image(built_texture)
        tex.filepath_raw = filepath_pattern.format(str(frame).zfill(digits))
        tex.file_format = file_format
        assign_pixels_data(tex.pixels, built_texture.ravel())
        tex.save()
        _log.info(f'TEXTURE SAVED: {tex.filepath}')

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
                          *, file_format: str = 'PNG', frames: List[int],
                          digits: int = 4, product: int) -> None:
    global _bake_generator_var
    _bake_generator_var = bake_generator(context.area, geotracker,
                                         filepath_pattern,
                                         file_format=file_format,
                                         frames=frames, digits=digits,
                                         product=product)
    prepare_camera(context.area)
    settings = gt_settings()
    if not settings.pinmode:
        vp = GTLoader.viewport()
        vp.texter().register_handler(context)
    bpy_timer_register(_bake_caller, first_interval=0.0)
