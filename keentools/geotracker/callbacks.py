# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2022-2023 KeenTools

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

from typing import Optional, Tuple, Any, List

from ..utils.kt_logging import KTLogger
from ..addon_config import (Config,
                            get_operator,
                            ErrorType)
from ..geotracker_config import GTConfig, get_gt_settings
from .gtloader import GTLoader
from ..utils.images import (get_background_image_object,
                            set_background_image_by_movieclip,
                            tone_mapping,
                            remove_background_image_object)
from ..utils.coords import (focal_mm_to_px,
                            camera_focal_length,
                            camera_sensor_width)
from ..utils.video import fit_render_size, fit_time_length
from ..utils.bpy_common import (bpy_render_frame,
                                bpy_start_frame,
                                bpy_end_frame,
                                bpy_current_frame,
                                bpy_set_current_frame)

from ..utils.animation import count_fcurve_points
from ..utils.manipulate import select_object_only, switch_to_camera
from ..utils.ui_redraw import total_redraw_ui


_log = KTLogger(__name__)


_constraint_warning_message = \
    'constraints detected! \n' \
    'Better delete or bake them.\n' \
    ' \n' \
    'If this is the result of Blender tracking, \n' \
    'you need to click on the \'Constraint to F-Curve button\'\n' \
    'of the solver constraint.'


def update_camobj(geotracker, context: Any) -> None:
    _log.output(f'update_camobj: {geotracker.camobj}')
    settings = get_gt_settings()

    if not geotracker.camobj and settings.pinmode:
        GTLoader.out_pinmode()
        return

    set_background_image_by_movieclip(geotracker.camobj,
                                      geotracker.movie_clip,
                                      name=GTConfig.gt_background_name,
                                      index=0)
    switch_to_camera(GTLoader.get_work_area(), geotracker.camobj)

    if settings.pinmode:
        GTLoader.update_viewport_shaders(update_geo_data=True,
                                         geomobj_matrix=True, wireframe=True,
                                         pins_and_residuals=True, timeline=True)

    if geotracker.camobj and len(geotracker.camobj.constraints) > 0:
        msg = f'Camera {_constraint_warning_message}'
        warn = get_operator(Config.kt_warning_idname)
        warn('INVOKE_DEFAULT', msg=ErrorType.CustomMessage,
             msg_content=msg)


def update_geomobj(geotracker, context: Any) -> None:
    _log.output(f'update_geomobj: {geotracker.geomobj}')
    settings = get_gt_settings()

    if not geotracker.geomobj and settings.pinmode:
        GTLoader.out_pinmode()
        return

    GTLoader.load_geotracker()
    gt = GTLoader.kt_geotracker()
    geotracker.check_pins_on_geometry(gt)
    GTLoader.save_geotracker()

    if settings.pinmode:
        GTLoader.update_viewport_shaders(update_geo_data=True,
                                         geomobj_matrix=True, wireframe=True,
                                         pins_and_residuals=True, timeline=True)

    if geotracker.geomobj and len(geotracker.geomobj.constraints) > 0:
        msg = f'Geometry {_constraint_warning_message}'
        warn = get_operator(Config.kt_warning_idname)
        warn('INVOKE_DEFAULT', msg=ErrorType.CustomMessage,
             msg_content=msg)


def update_movieclip(geotracker, context: Any) -> None:
    _log.output('update_movieclip')

    if not geotracker.movie_clip:
        geotracker.precalc_path = ''
        if geotracker.camobj:
            remove_background_image_object(geotracker.camobj, index=0)
        return

    current_frame = bpy_current_frame()
    scene = context.scene
    fit_time_length(geotracker.movie_clip)
    if not (scene.frame_start <= current_frame <= scene.frame_end):
        bpy_set_current_frame(scene.frame_start)

    fit_render_size(geotracker.movie_clip)

    set_background_image_by_movieclip(geotracker.camobj,
                                      geotracker.movie_clip,
                                      name=GTConfig.gt_background_name,
                                      index=0)

    geotracker.precalc_start = bpy_start_frame()
    geotracker.precalc_end = bpy_end_frame()

    geotracker.precalc_path = f'{GTConfig.gt_precalc_folder}' \
                              f'{geotracker.movie_clip.name}'


def update_precalc_path(geotracker, context: Any) -> None:
    _log.output('update_precalc_path')
    settings = get_gt_settings()
    if settings.ui_write_mode:
        return
    ending = '.precalc'
    if geotracker.precalc_path != '' and \
            geotracker.precalc_path[-len(ending):] != ending:
        with settings.ui_write_mode_context():
            geotracker.precalc_path += ending
    geotracker.reload_precalc()


def update_wireframe(settings, context: Any) -> None:
    if not settings.pinmode:
        return
    GTLoader.update_viewport_shaders(adaptive_opacity=True,
                                     geomobj_matrix=True,
                                     wireframe=True)


def update_mask_2d_color(settings, context: Any) -> None:
    vp = GTLoader.viewport()
    mask = vp.mask2d()
    mask.color = (*settings.mask_2d_color, settings.mask_2d_opacity)


def update_mask_3d_color(settings, context: Any) -> None:
    vp = GTLoader.viewport()
    wf = vp.wireframer()
    wf.selection_fill_color = (*settings.mask_3d_color, settings.mask_3d_opacity)
    if settings.pinmode:
        GTLoader.update_viewport_wireframe()


def update_wireframe_backface_culling(settings, context: Any) -> None:
    if settings.ui_write_mode:
        return
    gt = GTLoader.kt_geotracker()
    gt.set_back_face_culling(settings.wireframe_backface_culling)
    GTLoader.save_geotracker()
    if settings.pinmode:
        GTLoader.update_viewport_wireframe()


def update_background_tone_mapping(geotracker, context: Any) -> None:
    bg_img = get_background_image_object(geotracker.camobj)
    if not bg_img or not bg_img.image:
        return
    tone_mapping(bg_img.image,
                 exposure=geotracker.tone_exposure, gamma=geotracker.tone_gamma)


def update_pin_sensitivity(settings, context: Any) -> None:
    if settings.pin_size > settings.pin_sensitivity:
        settings.pin_size = settings.pin_sensitivity

    GTLoader.viewport().update_pin_sensitivity()


def update_pin_size(settings, context: Any) -> None:
    if settings.pin_sensitivity < settings.pin_size:
        settings.pin_sensitivity = settings.pin_size
    GTLoader.viewport().update_pin_size()


def update_focal_length_mode(geotracker, context: Any) -> None:
    _log.output(f'update_focal_length_mode: {geotracker.focal_length_mode}')
    if geotracker.focal_length_mode == 'STATIC_FOCAL_LENGTH':
        geotracker.static_focal_length = focal_mm_to_px(
            camera_focal_length(geotracker.camobj),
            *bpy_render_frame(), camera_sensor_width(geotracker.camobj))


def update_lens_mode(geotracker, context: Any=None) -> None:
    _log.output(f'update_lens_mode: {geotracker.lens_mode}')
    settings = get_gt_settings()
    if settings.ui_write_mode:
        return

    if geotracker.lens_mode == 'ZOOM':
        geotracker.focal_length_mode = 'ZOOM_FOCAL_LENGTH'
    else:
        if geotracker.focal_length_mode == 'ZOOM_FOCAL_LENGTH' and geotracker.camobj:
            count = count_fcurve_points(geotracker.camobj.data, 'lens')
            if count > 0:
                warn = get_operator(GTConfig.gt_switch_camera_to_fixed_warning_idname)
                warn('INVOKE_DEFAULT')
                return

        if geotracker.focal_length_estimation:
            geotracker.focal_length_mode = 'STATIC_FOCAL_LENGTH'
        else:
            count = count_fcurve_points(geotracker.camobj.data, 'lens')
            if count > 0:
                geotracker.focal_length_mode = 'STATIC_FOCAL_LENGTH'
            else:
                geotracker.focal_length_mode = 'CAMERA_FOCAL_LENGTH'


def update_track_focal_length(geotracker, context: Any) -> None:
    _log.output('update_track_focal_length')
    settings = get_gt_settings()
    if settings.ui_write_mode:
        return
    gt = GTLoader.kt_geotracker()
    gt.set_track_focal_length(geotracker.track_focal_length)
    GTLoader.save_geotracker()
    if settings.pinmode:
        GTLoader.update_viewport_wireframe()


def update_mask_3d(geotracker, context: Any) -> None:
    GTLoader.update_viewport_wireframe()
    settings = get_gt_settings()
    settings.reload_current_geotracker()
    settings.reload_mask_3d()


def update_mask_2d(geotracker, context: Any) -> None:
    _log.output('update_mask_2d')
    settings = get_gt_settings()
    settings.reload_current_geotracker()
    if not geotracker.mask_2d:
        remove_background_image_object(geotracker.camobj, index=1)
    else:
        set_background_image_by_movieclip(geotracker.camobj,
                                          geotracker.mask_2d,
                                          name=GTConfig.gt_background_mask_name,
                                          index=1)
    total_redraw_ui()
    settings.reload_mask_2d()
    vp = GTLoader.viewport()
    if vp.is_working():
        vp.create_batch_2d(vp.get_work_area())


def update_mask_source(geotracker, context: Any) -> None:
    _log.output('update_mask_source')
    if geotracker.get_2d_mask_source() == 'COMP_MASK':
        _log.output('switch to COMP_MASK')
        geotracker.update_compositing_mask(recreate_nodes=True)
    update_mask_2d(geotracker, context)


def update_spring_pins_back(geotracker, context: Any) -> None:
    if geotracker.spring_pins_back:
        GTLoader.load_geotracker()
        GTLoader.spring_pins_back()
        GTLoader.save_geotracker()
        settings = get_gt_settings()
        if settings.pinmode:
            GTLoader.update_viewport_shaders(pins_and_residuals=True)
            GTLoader.viewport_area_redraw()


def update_solve_for_camera(geotracker, context: Any) -> None:
    settings = get_gt_settings()
    if not settings.pinmode:
        return
    obj = geotracker.animatable_object()
    if not obj:
        return
    select_object_only(obj)
    second_obj = geotracker.non_animatable_object()
    if not second_obj:
        return
    second_obj.select_set(state=False)


def update_smoothing(geotracker, context: Any) -> None:
    settings = get_gt_settings()
    if settings.ui_write_mode:
        return
    gt = GTLoader.kt_geotracker()
    gt.set_smoothing_depth_coeff(geotracker.smoothing_depth_coeff)
    gt.set_smoothing_focal_length_coeff(geotracker.smoothing_focal_length_coeff)
    gt.set_smoothing_rotations_coeff(geotracker.smoothing_rotations_coeff)
    gt.set_smoothing_xy_translations_coeff(geotracker.smoothing_xy_translations_coeff)
    GTLoader.save_geotracker()
