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

from bpy.types import Object

from ..utils.kt_logging import KTLogger
from ..addon_config import (Config,
                            ft_settings,
                            get_operator,
                            ErrorType)
from ..facetracker_config import FTConfig
from ..geotracker_config import GTConfig
from ..utils.images import (get_background_image_object,
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
                                bpy_set_current_frame,
                                bpy_msgbus_subscribe_rna,
                                bpy_msgbus_clear_by_owner,
                                bpy_object_name,
                                bpy_object_is_in_scene)

from ..utils.animation import count_fcurve_points
from ..utils.manipulate import select_object_only, switch_to_camera
from ..utils.ui_redraw import total_redraw_ui
from ..geotracker.utils.tracking import check_unbreak_rotaion_is_needed
from ..utils.unbreak import unbreak_object_rotation_act, mark_object_keyframes
from ..facebuilder.utils.manipulate import is_facebuilder_head_topology


_log = KTLogger(__name__)


_constraint_warning_message = \
    'constraints detected! \n' \
    'Better delete or bake them.\n' \
    ' \n' \
    'If this is the result of Blender tracking, \n' \
    'you need to click on the \'Constraint to F-Curve button\'\n' \
    'of the solver constraint.'


class _Owner:
    pass


_old_focal_length_mm: float = 50.0
_camobj_lens_watcher_owner = _Owner()
_movie_clip_color_space_watcher_owner = _Owner()


def _set_old_focal_length_mm(value: float):
    global _old_focal_length_mm
    _old_focal_length_mm = value


def unsubscribe_watcher(owner: object) -> None:
    _log.yellow(f'ft unsubscribe_watcher start: {owner}')
    bpy_msgbus_clear_by_owner(owner)
    _log.output(f'ft unsubscribe_watcher end >>>')


def subscribe_camera_lens_watcher(camobj: Optional[Object]) -> None:
    _log.yellow('ft subscribe_camera_lens_watcher start')
    unsubscribe_watcher(_camobj_lens_watcher_owner)
    if not camobj or not camobj.data:
        _log.red('ft subscribe_camera_lens_watcher: no camera object')
        return
    subscribe_to = camobj.data.path_resolve('lens', False)
    _set_old_focal_length_mm(camobj.data.lens)
    bpy_msgbus_subscribe_rna(key=subscribe_to,
                             owner=_camobj_lens_watcher_owner,
                             args=(),
                             notify=lens_change_callback)
    _log.output('ft subscribe_camera_lens_watcher end >>>')


def subscribe_movie_clip_color_space_watcher(geotracker: Any) -> None:
    _log.yellow('ft subscribe_movie_clip_color_space_watcher start')
    unsubscribe_watcher(_movie_clip_color_space_watcher_owner)
    if not geotracker or not geotracker.movie_clip \
            or not geotracker.movie_clip.colorspace_settings:
        return

    subscribe_to = geotracker.movie_clip.colorspace_settings.path_resolve('name', False)
    bpy_msgbus_subscribe_rna(key=subscribe_to,
                             owner=_movie_clip_color_space_watcher_owner,
                             args=(geotracker.movie_clip.colorspace_settings.name,),
                             notify=color_space_change_callback)
    _log.output('ft subscribe_movie_clip_color_space_watcher end >>>')


def color_space_change_callback(old_name: str) -> None:
    _log.yellow('ft color_space_change_callback call')
    _log.output(f'old color space: {old_name}')
    settings = ft_settings()
    geotracker = settings.get_current_geotracker_item()
    update_movieclip(geotracker, None)
    _log.output('ft color_space_change_callback end >>>')


def recalculate_focal(use_current_frame: bool = True) -> bool:
    _log.yellow('ft recalculate_focal start')
    settings = ft_settings()
    geotracker = settings.get_current_geotracker_item()
    if not geotracker or not geotracker.camobj:
        return False

    if geotracker.focal_length_mode != 'STATIC_FOCAL_LENGTH':
        _log.red(f'recalculate_focal wrong mode: {geotracker.focal_length_mode}')
        return False

    _log.output(_log.color('magenta', f'start lens calculation'))
    rw, rh = bpy_render_frame()
    old_focal_length_px = focal_mm_to_px(
        _old_focal_length_mm,
        rw, rh, camera_sensor_width(geotracker.camobj))
    new_focal_length_px = focal_mm_to_px(
        camera_focal_length(geotracker.camobj),
        rw, rh, camera_sensor_width(geotracker.camobj))

    _log.red(f'\nold: {old_focal_length_px} new: {new_focal_length_px}')
    if abs(old_focal_length_px - new_focal_length_px) <= Config.focal_length_tolerance:
        _log.red('recalculate_focal: old and new are too close')
        return False

    current_frame = bpy_current_frame()
    settings.start_calculating('ESTIMATE_FL')
    loader = settings.loader()
    gt = loader.kt_geotracker()
    _log.magenta('ft recalculate_model_for_new_focal_length')
    gt.recalculate_model_for_new_focal_length(old_focal_length_px,
                                              new_focal_length_px,
                                              use_current_frame,
                                              current_frame)
    bpy_set_current_frame(current_frame)
    settings.stop_calculating()
    _set_old_focal_length_mm(geotracker.camobj.data.lens)
    _log.output('ft recalculate_focal end >>>')
    return True


def lens_change_callback() -> None:
    _log.magenta('ft lens_change_callback start')
    settings = ft_settings()
    if settings.ui_write_mode:
        _log.green('ft lens_change_callback ui_write_mode >>>')
        return

    loader = settings.loader()
    geotracker = settings.get_current_geotracker_item()
    if not settings.pinmode and not settings.is_calculating():
        _log.output('ft lens_change_callback stop 1')
        _set_old_focal_length_mm(geotracker.camobj.data.lens)
        return

    if loader.viewport().pins().move_pin_mode():
        _log.output('ft lens_change_callback stop 2')
        _set_old_focal_length_mm(geotracker.camobj.data.lens)
        return

    if not recalculate_focal(True):
        _log.output('ft lens_change_callback end 1 >>>')
        return

    if settings.pinmode:
        loader.update_viewport_shaders(wireframe_data=True,
                                       geomobj_matrix=True,
                                       wireframe=True,
                                       pins_and_residuals=True,
                                       timeline=True)
    _log.output('ft lens_change_callback end >>>')


def update_camobj(geotracker, context: Any) -> None:
    _log.yellow(f'ft update_camobj: {geotracker.camobj}')
    settings = ft_settings()
    loader = settings.loader()

    subscribe_camera_lens_watcher(geotracker.camobj)

    if not geotracker.camobj and settings.pinmode:
        loader.out_pinmode()
        return

    geotracker.setup_background_image()
    switch_to_camera(loader.get_work_area(), geotracker.camobj)

    if settings.pinmode:
        loader.update_viewport_shaders(wireframe_data=True,
                                       geomobj_matrix=True, wireframe=True,
                                       pins_and_residuals=True, timeline=True)

    if geotracker.camobj and len(geotracker.camobj.constraints) > 0:
        msg = f'Camera {_constraint_warning_message}'
        warn = get_operator(Config.kt_warning_idname)
        warn('INVOKE_DEFAULT', msg=ErrorType.CustomMessage,
             msg_content=msg)

    product = settings.product_type()
    prefs = settings.preferences()
    if prefs.auto_unbreak_rotation and \
            check_unbreak_rotaion_is_needed(geotracker.camobj):
        _log.info(f'Applying Unbreak Rotation to object: '
                  f'{bpy_object_name(geotracker.camobj)}')
        unbreak_status = unbreak_object_rotation_act(geotracker.camobj)
        if not unbreak_status.success:
            _log.error(unbreak_status.error_message)
        else:
            mark_object_keyframes(geotracker.camobj, product=product)

    _log.output('ft update_camobj end >>>')


def poll_is_facebuilder_mesh(self: Any, obj: Optional[Object]) -> bool:
    if not obj or not obj.type == 'MESH' or not bpy_object_is_in_scene(obj):
        return False
    return is_facebuilder_head_topology(obj)


def update_geomobj(geotracker, context: Any) -> None:
    _log.magenta(f'ft update_geomobj: {geotracker.geomobj} start')
    settings = ft_settings()
    loader = settings.loader()
    product = settings.product_type()
    loader.increment_geo_hash()

    if not geotracker.geomobj:
        if settings.pinmode:
            loader.out_pinmode()
        _log.output('ft update_geomobj 1 end >>>')
        return

    if not is_facebuilder_head_topology(geotracker.geomobj):
        msg = 'Geometry for FaceTracker should have KeenTools Head Topology'
        warn = get_operator(Config.kt_warning_idname)
        warn('INVOKE_DEFAULT', msg=ErrorType.CustomMessage, msg_content=msg)
        geotracker.geomobj = None
        _log.output('ft update_geomobj 2 end >>>')
        return

    loader.load_geotracker()
    gt = loader.kt_geotracker()
    geotracker.check_pins_on_geometry(gt)
    loader.save_geotracker()

    if settings.pinmode:
        loader.update_viewport_shaders(wireframe_data=True,
                                       geomobj_matrix=True, wireframe=True,
                                       pins_and_residuals=True, timeline=True)

    if geotracker.geomobj and len(geotracker.geomobj.constraints) > 0:
        msg = f'Geometry {_constraint_warning_message}'
        warn = get_operator(Config.kt_warning_idname)
        warn('INVOKE_DEFAULT', msg=ErrorType.CustomMessage,
             msg_content=msg)

    prefs = settings.preferences()
    if prefs.auto_unbreak_rotation and \
            check_unbreak_rotaion_is_needed(geotracker.geomobj):
        _log.info(f'Applying Unbreak Rotation to object: '
                  f'{bpy_object_name(geotracker.geomobj)}')
        unbreak_status = unbreak_object_rotation_act(geotracker.geomobj)
        if not unbreak_status.success:
            _log.error(unbreak_status.error_message)
        else:
            mark_object_keyframes(geotracker.geomobj, product=product)

    _log.output('ft update_geomobj end >>>')


def update_movieclip(geotracker, context: Any) -> None:
    _log.yellow('ft update_movieclip')
    if not geotracker:
        return

    if not geotracker.movie_clip:
        geotracker.precalc_path = ''
        if geotracker.camobj:
            remove_background_image_object(geotracker.camobj, index=0)
        return

    current_frame = bpy_current_frame()
    fit_time_length(geotracker.movie_clip)
    if not (bpy_start_frame() <= current_frame <= bpy_end_frame()):
        bpy_set_current_frame(bpy_start_frame())

    fit_render_size(geotracker.movie_clip)

    geotracker.setup_background_image()

    geotracker.precalc_start = bpy_start_frame()
    geotracker.precalc_end = bpy_end_frame()

    geotracker.precalc_path = f'{GTConfig.gt_precalc_folder}' \
                              f'{geotracker.movie_clip.name}'

    if context is not None:
        subscribe_movie_clip_color_space_watcher(geotracker)

    _log.output('ft update_movieclip end >>>')


def update_precalc_path(geotracker, context: Any) -> None:
    _log.yellow('ft update_precalc_path')
    settings = ft_settings()
    if settings.ui_write_mode:
        return
    ending = '.precalc'
    if geotracker.precalc_path != '' and \
            geotracker.precalc_path[-len(ending):] != ending:
        with settings.ui_write_mode_context():
            geotracker.precalc_path += ending
    geotracker.reload_precalc()
    _log.output('ft update_precalc_path end >>>')


def update_wireframe(settings, context: Any) -> None:
    _log.yellow('ft update_wireframe')
    if not settings.pinmode:
        return
    settings.loader().update_viewport_shaders(adaptive_opacity=True,
                                              geomobj_matrix=True,
                                              wireframe_colors=True,
                                              wireframe=True)
    _log.output('ft update_wireframe end >>>')


def update_wireframe_image(settings: Any, context: Any) -> None:
    _log.yellow('ft update_wireframe_image')
    settings.loader().update_viewport_shaders(wireframe_colors=True)
    _log.output('ft update_wireframe_image end >>>')


def update_mask_2d_color(settings, context: Any) -> None:
    _log.yellow('ft update_mask_2d_color')
    vp = settings.loader().viewport()
    mask = vp.mask2d()
    mask.color = (*settings.mask_2d_color, settings.mask_2d_opacity)
    _log.output('ft update_mask_2d_color end >>>')


def update_mask_3d_color(settings, context: Any) -> None:
    _log.yellow('ft update_mask_3d_color')
    loader = settings.loader()
    vp = loader.viewport()
    wf = vp.wireframer()
    wf.set_selection_fill_color((*settings.mask_3d_color,
                                 settings.mask_3d_opacity))
    if settings.pinmode:
        loader.update_viewport_shaders(wireframe=True, wireframe_colors=True)
    _log.output('ft update_mask_3d_color end >>>')


def update_wireframe_backface_culling(settings, context: Any) -> None:
    _log.yellow('ft update_wireframe_backface_culling')
    if settings.ui_write_mode:
        return
    loader = settings.loader()
    gt = loader.kt_geotracker()
    gt.set_back_face_culling(settings.wireframe_backface_culling)
    loader.save_geotracker()
    if settings.pinmode:
        loader.update_viewport_shaders(wireframe=True)
    _log.output('ft update_wireframe_backface_culling end >>>')


def update_background_tone_mapping(geotracker, context: Any) -> None:
    _log.yellow('ft update_background_tone_mapping')
    bg_img = get_background_image_object(geotracker.camobj)
    if not bg_img or not bg_img.image:
        return
    tone_mapping(bg_img.image,
                 exposure=geotracker.tone_exposure, gamma=geotracker.tone_gamma)
    _log.output('ft update_background_tone_mapping end >>>')


def update_pin_sensitivity(settings, context: Any) -> None:
    _log.yellow('ft update_pin_sensitivity')
    if settings.pin_size > settings.pin_sensitivity:
        settings.pin_size = settings.pin_sensitivity

    settings.loader().viewport().update_pin_sensitivity()
    _log.output('ft update_pin_sensitivity end >>>')


def update_pin_size(settings, context: Any) -> None:
    _log.yellow('ft update_pin_size')
    if settings.pin_sensitivity < settings.pin_size:
        settings.pin_sensitivity = settings.pin_size
    settings.loader().viewport().update_pin_size()
    _log.output('ft update_pin_size end >>>')


def update_focal_length_mode(geotracker, context: Any) -> None:
    _log.yellow(f'ft update_focal_length_mode: {geotracker.focal_length_mode}')
    if geotracker.focal_length_mode == 'STATIC_FOCAL_LENGTH':
        geotracker.static_focal_length = focal_mm_to_px(
            camera_focal_length(geotracker.camobj),
            *bpy_render_frame(), camera_sensor_width(geotracker.camobj))
    _log.output('ft update_focal_length_mode end >>>')


def update_lens_mode(geotracker, context: Any=None) -> None:
    _log.yellow(f'ft update_lens_mode: {geotracker.lens_mode}')
    settings = ft_settings()
    if settings.ui_write_mode:
        return

    if geotracker.lens_mode == 'ZOOM':
        geotracker.focal_length_mode = 'ZOOM_FOCAL_LENGTH'
    else:
        if geotracker.focal_length_mode == 'ZOOM_FOCAL_LENGTH' and geotracker.camobj:
            count = count_fcurve_points(geotracker.camobj.data, 'lens')
            if count > 0:
                warn = get_operator(FTConfig.ft_switch_camera_to_fixed_warning_idname)
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

    _log.output('ft update_lens_mode end >>>')


def update_track_focal_length(geotracker, context: Any) -> None:
    _log.yellow('ft update_track_focal_length')
    settings = ft_settings()
    if settings.ui_write_mode:
        return
    loader = settings.loader()
    gt = loader.kt_geotracker()
    gt.set_track_focal_length(geotracker.track_focal_length)
    loader.save_geotracker()
    if settings.pinmode:
        loader.update_viewport_shaders(wireframe=True)
    _log.output('ft update_track_focal_length end >>>')


def update_mask_3d(geotracker, context: Any) -> None:
    _log.yellow('ft update_mask_3d')
    settings = ft_settings()
    settings.reload_current_geotracker()
    settings.reload_mask_3d()
    settings.loader().update_viewport_shaders(wireframe=True, wireframe_colors=True)
    _log.output('ft update_mask_3d end >>>')


def update_mask_2d(geotracker, context: Any) -> None:
    _log.yellow('ft update_mask_2d')
    settings = ft_settings()
    settings.reload_current_geotracker()
    if not geotracker.mask_2d:
        remove_background_image_object(geotracker.camobj, index=1)
    else:
        geotracker.setup_background_mask()

    total_redraw_ui()
    settings.reload_mask_2d()
    vp = settings.loader().viewport()
    if vp.viewport_is_working():
        vp.create_batch_2d(vp.get_work_area())
    _log.output('ft update_mask_2d end >>>')


def update_mask_source(geotracker, context: Any) -> None:
    _log.yellow('ft update_mask_source')
    if geotracker.get_2d_mask_source() == 'COMP_MASK':
        _log.output('switch to COMP_MASK')
        geotracker.update_compositing_mask(recreate_nodes=True)
    update_mask_2d(geotracker, context)
    _log.output('ft update_mask_source end >>>')


def update_spring_pins_back(geotracker, context: Any) -> None:
    _log.yellow('ft update_spring_pins_back')
    if geotracker.spring_pins_back:
        settings = ft_settings()
        loader = settings.loader()
        loader.load_geotracker()
        loader.spring_pins_back()
        loader.save_geotracker()
        if settings.pinmode:
            loader.update_viewport_shaders(pins_and_residuals=True)
            loader.viewport_area_redraw()
    _log.output('ft update_spring_pins_back end >>>')


def update_solve_for_camera(geotracker, context: Any) -> None:
    _log.green('ft update_solve_for_camera start')
    settings = ft_settings()
    if not settings.pinmode:
        _log.output('ft update_solve_for_camera no pinmode >>>')
        return
    obj = geotracker.animatable_object()
    if not obj:
        return
    select_object_only(obj)
    second_obj = geotracker.non_animatable_object()
    if not second_obj:
        return
    second_obj.select_set(state=False)
    _log.output('ft update_solve_for_camera end >>>')


def update_smoothing(geotracker, context: Any) -> None:
    _log.green('ft update_smoothing start')
    settings = ft_settings()
    if settings.ui_write_mode:
        _log.green('ft update_smoothing ui_write_mode >>>')
        return
    loader = settings.loader()
    gt = loader.kt_geotracker()
    gt.set_smoothing_depth_coeff(geotracker.smoothing_depth_coeff)
    gt.set_smoothing_focal_length_coeff(geotracker.smoothing_focal_length_coeff)
    gt.set_smoothing_rotations_coeff(geotracker.smoothing_rotations_coeff)
    gt.set_smoothing_xy_translations_coeff(geotracker.smoothing_xy_translations_coeff)
    gt.set_smoothing_face_args_coeff(geotracker.smoothing_face_args_coeff)
    loader.save_geotracker()
    _log.output('ft update_smoothing end >>>')


def update_stabilize_viewport_enabled(settings, context: Any) -> None:
    _log.green('ft update_stabilize_viewport_enabled start')
    settings.stabilize_viewport(reset=True)
    _log.output('ft update_stabilize_viewport_enabled end >>>')


def update_locks(geotracker, context: Any) -> None:
    _log.green('ft update_locks start')
    settings = ft_settings()
    if settings.ui_write_mode:
        _log.green('ft update_locks ui_write_mode >>>')
        return
    loader = settings.loader()
    gt = loader.kt_geotracker()
    gt.set_fixed_dofs(list(geotracker.locks))
    _log.output(f'locks={geotracker.locks}')
    loader.save_geotracker()
    _log.magenta(f'{gt.fixed_dofs()}')
    _log.output('ft update_locks end >>>')


def update_lock_blinking(geotracker: Any, context: Any) -> None:
    _log.green('ft update_lock_blinking start')
    settings = ft_settings()
    if settings.ui_write_mode:
        _log.green('ft update_lock_blinking ui_write_mode >>>')
        return
    loader = settings.loader()
    gt = loader.kt_geotracker()
    gt.set_blinking_locked(geotracker.lock_blinking)
    _log.output(f'lock_blinking={geotracker.lock_blinking}')
    loader.save_geotracker()
    _log.output('ft update_lock_blinking end >>>')


def update_lock_neck_movement(geotracker: Any, context: Any) -> None:
    _log.green('ft update_lock_neck_movement start')
    settings = ft_settings()
    if settings.ui_write_mode:
        _log.green('ft update_lock_neck_movement ui_write_mode >>>')
        return
    loader = settings.loader()
    gt = loader.kt_geotracker()
    gt.set_neck_movement_locked(geotracker.lock_neck_movement)
    _log.output(f'lock_neck_movement={geotracker.lock_neck_movement}')
    loader.save_geotracker()
    _log.output('ft update_lock_neck_movement end >>>')


def update_rigidity(geotracker: Any, context: Any) -> None:
    _log.green('ft update_rigidity start')
    settings = ft_settings()
    if settings.ui_write_mode:
        _log.green('ft update_rigidity ui_write_mode >>>')
        return
    loader = settings.loader()
    gt = loader.kt_geotracker()
    gt.set_rigidity(geotracker.rigidity)
    _log.output(f'rigidity={geotracker.rigidity}')
    loader.save_geotracker()
    _log.output('ft update_rigidity end >>>')


def update_blinking_rigidity(geotracker: Any, context: Any) -> None:
    _log.green('ft update_blinking_rigidity start')
    settings = ft_settings()
    if settings.ui_write_mode:
        _log.green('ft update_blinking_rigidity ui_write_mode >>>')
        return
    loader = settings.loader()
    gt = loader.kt_geotracker()
    gt.set_blinking_rigidity(geotracker.blinking_rigidity)
    _log.output(f'blinking_rigidity={geotracker.blinking_rigidity}')
    loader.save_geotracker()
    _log.output('ft update_blinking_rigidity end >>>')


def update_neck_movement_rigidity(geotracker: Any, context: Any) -> None:
    _log.green('ft update_neck_movement_rigidity start')
    settings = ft_settings()
    if settings.ui_write_mode:
        _log.green('ft update_neck_movement_rigidity ui_write_mode >>>')
        return
    loader = settings.loader()
    gt = loader.kt_geotracker()
    gt.set_neck_movement_rigidity(geotracker.neck_movement_rigidity)
    _log.output(f'neck_movement_rigidity={geotracker.neck_movement_rigidity}')
    loader.save_geotracker()
    _log.output('ft update_neck_movement_rigidity end >>>')
