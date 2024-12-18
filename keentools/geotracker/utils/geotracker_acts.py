# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2022 KeenTools

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

from typing import List, Dict, Any, Optional
import time
import numpy as np

import bpy
from bpy.types import Object, Operator, Area
from mathutils import Matrix, Euler, Vector

from ...utils.kt_logging import KTLogger
from ...utils.version import BVersion
from ...addon_config import (ActionStatus,
                             get_addon_preferences,
                             ProductType,
                             get_settings,
                             fb_settings,
                             ft_settings,
                             product_name,
                             show_unlicensed_warning)
from ...geotracker_config import GTConfig
from ...utils.animation import (get_object_action,
                                remove_fcurve_point,
                                remove_fcurve_from_object,
                                delete_locrot_keyframe,
                                mark_selected_points_in_locrot,
                                get_object_keyframe_numbers,
                                create_animation_locrot_keyframe_force,
                                bake_locrot_to_world,
                                scene_frame_list)
from .tracking import (get_next_tracking_keyframe,
                       get_previous_tracking_keyframe,
                       unbreak_rotation,
                       check_unbreak_rotaion_is_needed)
from ...utils.bpy_common import (create_empty_object,
                                 bpy_current_frame,
                                 bpy_set_current_frame,
                                 update_depsgraph,
                                 reset_unsaved_animation_changes_in_frame,
                                 bpy_new_action,
                                 bpy_init_action_slot,
                                 bpy_scene,
                                 bpy_render_single_frame,
                                 bpy_scene_selected_objects,
                                 bpy_active_object,
                                 bpy_progress_begin,
                                 bpy_progress_end,
                                 bpy_progress_update)
from ...blender_independent_packages.pykeentools_loader import module as pkt_module
from ...utils.manipulate import (select_object_only,
                                 select_objects_only,
                                 center_viewport,
                                 switch_to_mode)
from .prechecks import (common_checks,
                        track_checks,
                        get_alone_object_in_scene_selection_by_type,
                        get_alone_object_in_scene_by_type,
                        get_alone_ft_object_in_scene_selection,
                        get_alone_ft_object_in_scene,
                        prepare_camera,
                        revert_camera,
                        show_warning_dialog)
from ...utils.compositing import (create_nodes_for_rendering_with_background,
                                  revert_default_compositing)
from ...utils.images import (get_background_image_object,
                             check_background_image_absent_frames)
from ..settings import bpy_poll_is_mesh, bpy_poll_is_camera
from ...utils.coords import (LocRotScale,
                             LocRotWithoutScale,
                             ScaleMatrix,
                             InvScaleMatrix,
                             InvScaleFromMatrix,
                             change_near_and_far_clip_planes,
                             pin_to_xyz_from_geo_mesh,
                             pin_to_normal_from_geo_mesh,
                             xy_to_xz_rotation_matrix_3x3)
from .textures import bake_texture, preview_material_with_texture, get_bad_frame
from ..interface.screen_mesages import clipping_changed_screen_message
from ...utils.ui_redraw import total_redraw_ui
from ...tracker.calc_timer import (TrackTimer,
                                   RefineTimer,
                                   RefineTimerFast,
                                   FTTrackTimer,
                                   FTRefineTimer,
                                   FTRefineTimerFast)
from ...utils.unbreak import (mark_object_keyframes,
                              unbreak_after,
                              unbreak_after_facetracker,
                              unbreak_after_reversed,
                              unbreak_after_reversed_facetracker,
                              unbreak_object_rotation_act,
                              unbreak_rotation_act,
                              unbreak_rotation_with_status)
from ...tracker.tracking_blendshapes import create_relative_shape_keyframe
from ...utils.blendshapes import create_basis_blendshape
from ...utils.fcurve_operations import (get_safe_action_fcurve,
                                        put_anim_data_in_fcurve,
                                        cleanup_keys_in_interval,
                                        snap_keys_in_interval)


_log = KTLogger(__name__)


def create_geotracker_action() -> ActionStatus:
    _log.yellow(f'create_geotracker_action start')
    product = ProductType.GEOTRACKER
    check_status = common_checks(product=product,
                                 object_mode=True, pinmode_out=True,
                                 is_calculating=True)
    if not check_status.success:
        return check_status

    settings = get_settings(product)
    num = settings.add_geotracker_item()
    settings.set_current_tracker_num(num)
    settings.loader().new_kt_geotracker()

    selected_objects = bpy_scene_selected_objects()
    active_object = bpy_active_object()

    geotracker = settings.get_current_geotracker_item()
    obj = get_alone_object_in_scene_selection_by_type('MESH', exclude_list=[])
    if obj is None:
        obj = get_alone_object_in_scene_by_type('MESH', exclude_list=[])
    geotracker.geomobj = obj

    camobj = get_alone_object_in_scene_selection_by_type('CAMERA', exclude_list=[])
    if camobj is None:
        camobj = get_alone_object_in_scene_by_type('CAMERA', exclude_list=[])
    geotracker.camobj = camobj

    settings.reload_current_geotracker()

    select_objects_only(selected_objects)
    bpy_active_object(active_object)
    _log.output('create_geotracker_action end >>>')
    return ActionStatus(True, f'GeoTracker has been added')


def create_facetracker_action() -> ActionStatus:
    _log.yellow(f'create_facetracker_action start')
    product = ProductType.FACETRACKER
    check_status = common_checks(product=product,
                                 object_mode=True, pinmode_out=True,
                                 is_calculating=True)
    if not check_status.success:
        return check_status

    settings = get_settings(product)
    num = settings.add_geotracker_item()
    settings.set_current_tracker_num(num)
    settings.loader().new_kt_geotracker()

    selected_objects = bpy_scene_selected_objects()
    active_object = bpy_active_object()

    geotracker = settings.get_current_geotracker_item()
    obj = get_alone_ft_object_in_scene_selection()
    if obj is None:
        obj = get_alone_ft_object_in_scene()
    geotracker.geomobj = obj

    exclude_camobj = fb_settings().get_all_camobj()
    camobj = get_alone_object_in_scene_selection_by_type(
        'CAMERA', exclude_list=exclude_camobj)
    if camobj is None:
        camobj = get_alone_object_in_scene_by_type(
            'CAMERA', exclude_list=exclude_camobj)
    geotracker.camobj = camobj

    settings.reload_current_geotracker()

    select_objects_only(selected_objects)
    bpy_active_object(active_object)

    _log.output('create_facetracker_action end >>>')
    return ActionStatus(True, f'FaceTracker has been added')


def delete_tracker_action(geotracker_num: int, *, product: int) -> ActionStatus:
    _log.yellow(f'delete_tracker_action start [{product_name(product)}]')
    check_status = common_checks(product=product,
                                 object_mode=True, pinmode_out=True,
                                 is_calculating=True)
    if not check_status.success:
        return check_status

    settings = get_settings(product)
    res = settings.remove_geotracker_item(geotracker_num)
    if not res:
        msg = f'Could not delete a {product_name(product)}'
        _log.error(msg)
        return ActionStatus(False, msg)
    settings.reload_current_geotracker()

    _log.output('delete_tracker_action end >>>')
    return ActionStatus(True, f'{product_name(product)} has been removed')


def select_tracker_objects_action(geotracker_num: int, *,
                                  product: int) -> ActionStatus:
    _log.yellow(f'select_tracker_objects_action start [{product_name(product)}]')
    check_status = common_checks(product=product,
                                 object_mode=True, is_calculating=True,
                                 pinmode_out=True)
    if not check_status.success:
        return check_status

    settings = get_settings(product)
    settings.fix_geotrackers()
    if not settings.change_current_geotracker_safe(geotracker_num):
        return ActionStatus(False, f'Cannot switch to {product_name(product)} '
                                   f'{geotracker_num}')

    geotracker = settings.get_current_geotracker_item()
    if not geotracker.geomobj and not geotracker.camobj:
        return ActionStatus(False, f'{product_name(product)} {geotracker_num} '
                                   f'does not contain any objects')
    if geotracker.camera_mode():
        select_objects_only([geotracker.camobj, geotracker.geomobj])
    else:
        select_objects_only([geotracker.geomobj, geotracker.camobj])

    center_viewport(bpy.context.area)
    _log.output('select_tracker_objects_action end >>>')
    return ActionStatus(True, 'ok')


def add_keyframe_action(*, product: int) -> ActionStatus:
    _log.yellow(f'add_keyframe_action start [{product_name(product)}]')
    check_status = common_checks(product=product,
                                 object_mode=True, pinmode=True,
                                 is_calculating=True, reload_geotracker=True,
                                 geotracker=True, camera=True, geometry=True)
    if not check_status.success:
        return check_status

    settings = get_settings(product)
    loader = settings.loader()
    area = loader.get_work_area()
    if not area:
        return ActionStatus(False, 'Working area does not exist')

    loader.safe_keyframe_add(bpy_current_frame(), update=True)

    if product == ProductType.FACETRACKER:
        create_relative_shape_keyframe(bpy_current_frame())

    loader.save_geotracker()
    _log.output('add_keyframe_action end >>>')
    return ActionStatus(True, 'ok')


def remove_keyframe_action(*, product: int) -> ActionStatus:
    _log.yellow(f'remove_keyframe_action start [{product_name(product)}]')
    check_status = common_checks(product=product,
                                 object_mode=True, pinmode=True,
                                 is_calculating=True, reload_geotracker=True,
                                 geotracker=True, camera=True, geometry=True)
    if not check_status.success:
        return check_status

    settings = get_settings(product)
    loader = settings.loader()
    gt = loader.kt_geotracker()
    current_frame = bpy_current_frame()

    if gt.is_key_at(current_frame):
        gt.remove_keyframe(current_frame)
        loader.save_geotracker()
        return ActionStatus(True, 'ok')

    settings = get_settings(product)
    geotracker = settings.get_current_geotracker_item()
    obj = geotracker.animatable_object()
    delete_locrot_keyframe(obj)

    _log.output('remove_keyframe_action end >>>')
    return ActionStatus(True, f'No {product_name(product)} '
                              f'keyframe at this frame')


def next_keyframe_action(*, product) -> ActionStatus:
    _log.yellow(f'next_keyframe_action start [{product_name(product)}]')
    current_frame = bpy_current_frame()
    settings = get_settings(product)
    gt = settings.loader().kt_geotracker()
    target_frame = get_next_tracking_keyframe(gt, current_frame)

    if current_frame == target_frame:
        track_frames = gt.track_frames()
        if len(track_frames) > 0:
            last_track_frame = track_frames[-1]
            if last_track_frame > current_frame:
                target_frame = last_track_frame

    if current_frame != target_frame:
        bpy_set_current_frame(target_frame)
        total_redraw_ui()  # For proper stabilization
        return ActionStatus(True, 'ok')

    _log.output('next_keyframe_action end >>>')
    return ActionStatus(False, f'No next {product_name(product)} keyframe')


def prev_keyframe_action(*, product) -> ActionStatus:
    _log.yellow(f'prev_keyframe_action start [{product_name(product)}]')
    current_frame = bpy_current_frame()
    settings = get_settings(product)
    gt = settings.loader().kt_geotracker()
    target_frame = get_previous_tracking_keyframe(gt, current_frame)

    if current_frame == target_frame:
        track_frames = gt.track_frames()
        if len(track_frames) > 0:
            first_track_frame = track_frames[0]
            if first_track_frame < current_frame:
                target_frame = first_track_frame

    if current_frame != target_frame:
        bpy_set_current_frame(target_frame)
        total_redraw_ui()  # For proper stabilization
        return ActionStatus(True, 'ok')

    _log.output('prev_keyframe_action end >>>')
    return ActionStatus(False, f'No previous {product_name(product)} keyframe')


def toggle_lock_view_action(*, product: int) -> ActionStatus:
    _log.yellow(f'toggle_lock_view_action start [{product_name(product)}]')
    settings = get_settings(product)
    if not settings.pinmode:
        return ActionStatus(False, f'Lock View works in '
                                   f'{product_name(product)} pinmode only')

    settings.stabilize_viewport_enabled = not settings.stabilize_viewport_enabled
    _log.output('toggle_lock_view_action end >>>')
    return ActionStatus(True, 'Ok')


def track_to(forward: bool, *, product: int) -> ActionStatus:
    _log.yellow(f'track_to: forward={forward} [{product_name(product)}]')
    check_status = track_checks(product=product)
    if not check_status.success:
        return check_status

    settings = get_settings(product)
    loader = settings.loader()
    geotracker = settings.get_current_geotracker_item()
    gt = loader.kt_geotracker()
    current_frame = bpy_current_frame()
    _log.output(loader.get_geotracker_state())
    precalcless = geotracker.precalcless
    if not precalcless and not \
            geotracker.precalc_start <= current_frame <= geotracker.precalc_end:
        return ActionStatus(False, 'Current frame is outside '
                                   'of the precalc-file range')
    try:
        precalc_path = None if precalcless else geotracker.precalc_path
        _log.output(f'gt.track_async({current_frame}, {forward}, {precalc_path})')
        tracking_computation = gt.track_async(current_frame, forward, precalc_path)

        if product == ProductType.GEOTRACKER:
            tracking_timer = TrackTimer(
                tracking_computation, current_frame,
                success_callback=unbreak_after if forward else unbreak_after_reversed,
                error_callback=unbreak_after if forward else unbreak_after_reversed,
                product=product)
        elif product == ProductType.FACETRACKER:
            tracking_timer = FTTrackTimer(
                tracking_computation, current_frame,
                success_callback=unbreak_after_facetracker if forward else unbreak_after_reversed_facetracker,
                error_callback=unbreak_after_facetracker if forward else unbreak_after_reversed_facetracker,
                product=product
            )
        else:
            assert False, f'Wrong product type [{product}]'

        tracking_timer.start()
    except pkt_module().UnlicensedException as err:
        _log.error(f'UnlicensedException track_to:\n{str(err)}')
        show_unlicensed_warning(product)
        # Return True to prevent doubling dialogs
        return ActionStatus(True, 'Unlicensed error')
    except Exception as err:
        _log.error(f'Unknown Exception track_to:\n{str(err)}')
        show_warning_dialog(err)
        return ActionStatus(False, 'Some problem (see console)')

    _log.output('track_to end >>>')
    return ActionStatus(True, 'Ok')


def track_next_frame_action(forward: bool=True, *,
                            product: int) -> ActionStatus:
    _log.yellow(f'track_next_frame_act: forward={forward} [{product_name(product)}]')
    check_status = track_checks(product=product)
    if not check_status.success:
        return check_status

    settings = get_settings(product)
    geotracker = settings.get_current_geotracker_item()

    obj = geotracker.animatable_object()
    if not obj:
        msg = 'No animated object'
        _log.error(msg)
        return ActionStatus(False, msg)

    loader = settings.loader()
    gt = loader.kt_geotracker()
    current_frame = bpy_current_frame()
    next_frame = current_frame + 1 if forward else current_frame - 1
    settings.start_calculating('TRACKING')
    try:
        _log.output(loader.get_geotracker_state())
        precalc_path = None if geotracker.precalcless else geotracker.precalc_path

        if gt.track_frame(current_frame, forward, precalc_path):
            if product == ProductType.FACETRACKER:
                create_relative_shape_keyframe(next_frame)

            prefs = get_addon_preferences()
            if prefs.auto_unbreak_rotation:
                unbreak_status = unbreak_rotation_with_status(
                    obj, [current_frame, next_frame])
                if not unbreak_status.success:
                    _log.error(f'track_next_frame_action '
                               f'{unbreak_status.error_message}')
                else:
                    mark_object_keyframes(obj, product=product)

    except pkt_module().UnlicensedException as err:
        _log.error(f'UnlicensedException track_next_frame_action: {str(err)}')
        show_unlicensed_warning(product)
        # Return True to prevent doubling dialogs
        return ActionStatus(True, 'Unlicensed error')
    except Exception as err:
        msg = 'Track next frame problem (see console)'
        _log.error(f'{msg}\n{str(err)}')
        show_warning_dialog(err)
        return ActionStatus(False, msg)
    finally:
        settings.stop_calculating()

    loader.save_geotracker()
    if bpy_current_frame() != next_frame:
        bpy_set_current_frame(next_frame)

    _log.output('track_next_frame_action end >>>')
    return ActionStatus(True, 'Ok')


def refine_async_action(*, product: int) -> ActionStatus:
    _log.yellow(f'refine_async_action start [{product_name(product)}]')
    check_status = track_checks(product=product)
    if not check_status.success:
        return check_status

    settings = get_settings(product)
    geotracker = settings.get_current_geotracker_item()
    gt = settings.loader().kt_geotracker()
    current_frame = bpy_current_frame()

    if not geotracker.precalcless:
        next_frame = get_next_tracking_keyframe(gt, current_frame)
        prev_frame = get_previous_tracking_keyframe(gt, current_frame)
        if not (geotracker.precalc_start <= prev_frame <= geotracker.precalc_end and
                geotracker.precalc_start <= next_frame <= geotracker.precalc_end):
            return ActionStatus(False, 'Selected frame range is outside '
                                       'of the precalc range')
    try:
        precalc_path = None if geotracker.precalcless else geotracker.precalc_path
        refine_computation = gt.refine_async(current_frame, precalc_path)
        if geotracker.precalcless:
            if product == ProductType.GEOTRACKER:
                refine_timer = RefineTimer(refine_computation, current_frame,
                                           success_callback=unbreak_after,
                                           product=product)
            elif product == ProductType.FACETRACKER:
                refine_timer = FTRefineTimer(refine_computation, current_frame,
                                             success_callback=after_ft_refine,
                                             product=product)
            else:
                assert False, f'Wrong product (1) {product}'
        else:
            if product == ProductType.GEOTRACKER:
                refine_timer = RefineTimerFast(refine_computation, current_frame,
                                               success_callback=unbreak_after,
                                               product=product)
            elif product == ProductType.FACETRACKER:
                refine_timer = FTRefineTimerFast(refine_computation,
                                                 current_frame,
                                                 success_callback=after_ft_refine,
                                                 product=product)
            else:
                assert False, f'Wrong product (2) {product}'

        refine_timer.start()
    except pkt_module().UnlicensedException as err:
        _log.error(f'UnlicensedException refine_async_action:\n{str(err)}')
        show_unlicensed_warning(product)
        # Return True to prevent doubling dialogs
        return ActionStatus(True, 'Unlicensed error')
    except Exception as err:
        _log.error(f'Unknown Exception refine_async_action:\n{str(err)}')
        show_warning_dialog(err)
        return ActionStatus(False, 'Some problem (see console)')

    _log.output('refine_async_action end >>>')
    return ActionStatus(True, 'Ok')


def refine_all_async_action(*, product: int) -> ActionStatus:
    _log.yellow(f'refine_all_async_action start [{product_name(product)}]')
    check_status = track_checks(product=product)
    if not check_status.success:
        return check_status

    settings = get_settings(product)
    geotracker = settings.get_current_geotracker_item()

    gt = settings.loader().kt_geotracker()
    current_frame = bpy_current_frame()
    try:
        precalc_path = None if geotracker.precalcless else geotracker.precalc_path
        refine_computation = gt.refine_all_async(precalc_path)
        if geotracker.precalcless:
            if product == ProductType.GEOTRACKER:
                refine_timer = RefineTimer(refine_computation, current_frame,
                                           success_callback=unbreak_after,
                                           product=product)
            elif product == ProductType.FACETRACKER:
                refine_timer = FTRefineTimer(refine_computation, current_frame,
                                             success_callback=after_ft_refine,
                                             product=product)
            else:
                assert False, f'Wrong product (1) {product}'
        else:
            if product == ProductType.GEOTRACKER:
                refine_timer = RefineTimerFast(refine_computation,
                                               current_frame,
                                               success_callback=unbreak_after,
                                               product=product)
            elif product == ProductType.FACETRACKER:
                refine_timer = FTRefineTimerFast(refine_computation,
                                                 current_frame,
                                                 success_callback=after_ft_refine,
                                                 product=product)
            else:
                assert False, f'Wrong product (2) {product}'

        refine_timer.start()
    except pkt_module().UnlicensedException as err:
        _log.error(f'UnlicensedException refine_all_async_action: {str(err)}')
        show_unlicensed_warning(product)
        # Return True to prevent doubling dialogs
        return ActionStatus(True, 'Unlicensed error')
    except Exception as err:
        _log.error(f'Unknown Exception refine_all_async_action: {str(err)}')
        show_warning_dialog(err)
        return ActionStatus(False, 'Some problem (see console)')

    _log.output('refine_all_async_action end >>>')
    return ActionStatus(True, 'Ok')


def clear_between_keyframes_action(*, product: int) -> ActionStatus:
    _log.yellow(f'clear_between_keyframes_action start [{product_name(product)}]')
    check_status = common_checks(product=product,
                                 object_mode=False, pinmode=True,
                                 is_calculating=True, reload_geotracker=True,
                                 geotracker=True, camera=True, geometry=True)
    if not check_status.success:
        return check_status

    current_frame = bpy_current_frame()
    settings = get_settings(product)
    loader = settings.loader()
    gt = loader.kt_geotracker()
    try:
        gt.remove_track_between_keyframes(current_frame)
    except Exception as err:
        _log.error(f'Unknown Exception clear_between_keyframes_act: {str(err)}')
        show_warning_dialog(err)

    loader.save_geotracker()
    loader.update_viewport_shaders(geomobj_matrix=True, wireframe=True,
                                   pins_and_residuals=True, timeline=True)
    loader.viewport_area_redraw()
    _log.output('clear_between_keyframes_action end >>>')
    return ActionStatus(True, 'ok')


def clear_direction_action(forward: bool, *, product: int) -> ActionStatus:
    _log.yellow(f'clear_direction_action start [{product_name(product)}]')
    check_status = common_checks(product=product,
                                 object_mode=False, pinmode=True,
                                 is_calculating=True, reload_geotracker=True,
                                 geotracker=True, camera=True, geometry=True)
    if not check_status.success:
        return check_status

    current_frame = bpy_current_frame()
    settings = get_settings(product)
    loader = settings.loader()
    gt = loader.kt_geotracker()
    try:
        _log.output(f'clear_direction_act: {current_frame} {forward}')
        gt.remove_track_in_direction(current_frame, forward=forward)
    except Exception as err:
        _log.error(f'Unknown Exception clear_direction_action:\n{str(err)}')
        show_warning_dialog(err)

    loader.save_geotracker()
    loader.update_viewport_shaders(geomobj_matrix=True, wireframe=True,
                                   pins_and_residuals=True, timeline=True)
    loader.viewport_area_redraw()
    _log.output('clear_direction_action end >>>')
    return ActionStatus(True, 'ok')


def clear_all_action(*, product: int) -> ActionStatus:
    _log.yellow(f'clear_all_act start [{product_name(product)}]')
    check_status = common_checks(product=product,
                                 object_mode=False, pinmode=True,
                                 is_calculating=True, reload_geotracker=True,
                                 geotracker=True, camera=True, geometry=True)
    if not check_status.success:
        return check_status

    settings = get_settings(product)
    loader = settings.loader()
    gt = loader.kt_geotracker()
    try:
        gt.remove_all_track_data_and_keyframes()
    except Exception as err:
        _log.error(f'Unknown Exception clear_all_action:\n{str(err)}')
        show_warning_dialog(err)

    loader.save_geotracker()
    loader.update_viewport_shaders(geomobj_matrix=True, wireframe=True,
                                   pins_and_residuals=True, timeline=True)
    loader.viewport_area_redraw()
    _log.output('clear_all_action end >>>')
    return ActionStatus(True, 'ok')


def clear_all_except_keyframes_action(*, product: int) -> ActionStatus:
    _log.yellow(f'clear_all_except_keyframes_action start [{product_name(product)}]')
    check_status = common_checks(product=product,
                                 object_mode=True, pinmode=True,
                                 is_calculating=True, reload_geotracker=True,
                                 geotracker=True, camera=True, geometry=True)
    if not check_status.success:
        return check_status

    settings = get_settings(product)
    loader = settings.loader()
    gt = loader.kt_geotracker()

    keyframes = gt.keyframes()
    if len(keyframes) < 1:
        return clear_all_action(product=product)

    for i in range(len(keyframes) - 1):
        start = keyframes[i]
        end = keyframes[i + 1]
        current = start + 1
        if current in [start, end]:
            continue
        gt.remove_track_between_keyframes(current)

    gt.remove_track_in_direction(keyframes[0], False)
    gt.remove_track_in_direction(keyframes[-1], True)

    loader.save_geotracker()
    loader.update_viewport_shaders(geomobj_matrix=True, wireframe=True,
                                   pins_and_residuals=True, timeline=True)
    _log.output('clear_all_except_keyframes_action end >>>')
    return ActionStatus(True, 'ok')


def remove_focal_keyframe_action(*, product: int) -> ActionStatus:
    _log.yellow(f'remove_focal_keyframe_action start [{product_name(product)}]')
    check_status = common_checks(product=product,
                                 object_mode=False, is_calculating=True,
                                 reload_geotracker=True, geotracker=True,
                                 camera=True)
    if not check_status.success:
        return check_status

    settings = get_settings(product)
    geotracker = settings.get_current_geotracker_item()
    remove_fcurve_point(geotracker.camobj.data, bpy_current_frame(), 'lens')
    _log.output('remove_focal_keyframe_action end >>>')
    return ActionStatus(True, 'ok')


def remove_focal_keyframes_action(*, product: int) -> ActionStatus:
    _log.yellow(f'remove_focal_keyframes_action start [{product_name(product)}]')
    check_status = common_checks(product=product,
                                 object_mode=False, is_calculating=True,
                                 reload_geotracker=True, geotracker=True,
                                 camera=True)
    if not check_status.success:
        return check_status

    settings = get_settings(product)
    geotracker = settings.get_current_geotracker_item()
    remove_fcurve_from_object(geotracker.camobj.data, 'lens')
    _log.output('remove_focal_keyframes_action end >>>')
    return ActionStatus(True, 'ok')


def remove_pins_action(*, product: int) -> ActionStatus:
    _log.yellow(f'remove_pins_action start [{product_name(product)}]')
    check_status = common_checks(product=product,
                                 object_mode=True, pinmode=True,
                                 is_calculating=True, reload_geotracker=True,
                                 geotracker=True, camera=True, geometry=True)
    if not check_status.success:
        return check_status

    settings = get_settings(product)
    loader = settings.loader()
    gt = loader.kt_geotracker()

    vp = loader.viewport()
    pins = vp.pins()
    selected_pins = pins.get_selected_pins()
    if len(selected_pins) == 0:
        gt.remove_pins()
        pins.clear_disabled_pins()
        pins.clear_selected_pins()
    else:
        selected_pins.sort()
        for i in reversed(selected_pins):
            gt.remove_pin(i)
            pins.remove_pin(i)
        pins.clear_selected_pins()
        if gt.is_key_at(bpy_current_frame()) and not loader.solve():
            return ActionStatus(False, 'Could not remove selected pins')
        loader.load_pins_into_viewport()

    pins.reset_current_pin()
    loader.save_geotracker()
    loader.update_viewport_shaders(pins_and_residuals=True)
    loader.viewport_area_redraw()
    _log.output(f'remove_pins_action end >>>')
    return ActionStatus(True, 'ok')


def toggle_pins_action(*, product: int) -> ActionStatus:
    _log.yellow(f'toggle_pins_action start [{product_name(product)}]')
    check_status = common_checks(product=product,
                                 object_mode=True, pinmode=True,
                                 is_calculating=True, reload_geotracker=True,
                                 geotracker=True, camera=True, geometry=True)
    if not check_status.success:
        return check_status

    settings = get_settings(product)
    loader = settings.loader()
    gt = loader.kt_geotracker()
    keyframe = bpy_current_frame()
    pins_count = gt.pins_count()
    if pins_count > 0:
        loader.safe_keyframe_add(keyframe, update=True)
        pins = loader.viewport().pins()
        selected_pins = pins.get_selected_pins(pins_count)
        if len(selected_pins) == 0:
            gt.toggle_pins(keyframe)
        else:
            gt.toggle_pins(keyframe, selected_pins)
        pins.clear_selected_pins()
        loader.save_geotracker()

    loader.update_viewport_shaders(pins_and_residuals=True)
    loader.viewport_area_redraw()
    _log.output(f'toggle_pins_action end >>>')
    return ActionStatus(True, 'ok')


def center_geo_action(*, product: int) -> ActionStatus:
    _log.yellow(f'center_geo_act start [{product_name(product)}]')
    check_status = common_checks(product=product,
                                 object_mode=True, pinmode=True,
                                 is_calculating=True, reload_geotracker=True,
                                 geotracker=True, camera=True, geometry=True)
    if not check_status.success:
        return check_status

    settings = get_settings(product)
    loader = settings.loader()
    loader.center_geo()

    settings = get_settings(product)
    geotracker = settings.get_current_geotracker_item()
    camobj = geotracker.camobj
    camera_clip_start = camobj.data.clip_start
    camera_clip_end = camobj.data.clip_end

    if GTConfig.auto_increase_far_clip_distance and camobj and \
            change_near_and_far_clip_planes(geotracker.camobj,
                                            geotracker.geomobj,
                                            prev_clip_start=camera_clip_start,
                                            prev_clip_end=camera_clip_end):
        near = camobj.data.clip_start
        far = camobj.data.clip_end
        if near != camera_clip_start or far != camera_clip_end:
            clipping_changed_screen_message(near, far, product=product)

    loader.update_viewport_shaders(wireframe=True, geomobj_matrix=True,
                                   pins_and_residuals=True)
    loader.viewport_area_redraw()
    _log.output('center_geo_act end >>>')
    return ActionStatus(True, 'ok')


def create_animated_empty_action(
        obj: Object, linked: bool=False,
        force_bake_all_frames: bool=False) -> ActionStatus:
    _log.yellow(f'create_animated_empty_action start')
    if not bpy_poll_is_mesh(None, obj) and not bpy_poll_is_camera(None, obj):
        msg = 'Selected object is not Geometry or Camera'
        return ActionStatus(False, msg)

    action = get_object_action(obj)
    if action is None:
        msg = 'Selected object has no animation'
        _log.error(msg)
        return ActionStatus(False, msg)

    obj_matrix_world = obj.matrix_world.copy()
    current_frame = reset_unsaved_animation_changes_in_frame()
    if linked:
        if obj.parent:
            msg = 'Cannot create linked animation for a parented object'
            _log.error(msg)
            return ActionStatus(False, msg)

        empty = create_empty_object(GTConfig.gt_empty_name)
        anim_data = empty.animation_data_create()
        anim_data.action = action
        bpy_init_action_slot(anim_data)
        select_object_only(empty)
    else:
        obj_animated_frames = get_object_keyframe_numbers(obj)
        if force_bake_all_frames:
            obj_animated_frames = scene_frame_list()
        if len(obj_animated_frames) == 0:
            if len(obj.constraints) != 0:
                obj_animated_frames = scene_frame_list()
            else:
                msg = 'Selected object has no Location & Rotation animation'
                _log.error(msg)
                return ActionStatus(False, msg)

        empty = create_empty_object(GTConfig.gt_empty_name)

        for frame in obj_animated_frames:
            bpy_set_current_frame(frame)
            empty.matrix_world = obj.matrix_world.copy()
            update_depsgraph()
            create_animation_locrot_keyframe_force(empty)
        bpy_set_current_frame(current_frame)

        obj.matrix_world = obj_matrix_world
        empty.matrix_world = obj_matrix_world
        select_object_only(empty)

        prefs = get_addon_preferences()
        if prefs.auto_unbreak_rotation:
            unbreak_status = unbreak_object_rotation_act(empty)
            if not unbreak_status.success:
                return unbreak_status

    _log.output(f'create_animated_empty_action end >>>')
    return ActionStatus(True, 'ok')


def create_hard_empties_from_selected_pins_action(
        from_frame: int, to_frame: int, linked: bool = False,
        orientation: str = 'NORMAL', size: float = 1.0,
        *, product: int) -> ActionStatus:
    _log.yellow(f'create_hard_empties_from_selected_pins_action start [{product_name(product)}]')
    check_status = common_checks(product=product,
                                 object_mode=True, pinmode=True,
                                 is_calculating=True, reload_geotracker=True,
                                 geotracker=True, camera=True, geometry=True)
    if not check_status.success:
        return check_status

    if from_frame < 0 or to_frame < from_frame:
        return ActionStatus(False, 'Wrong frame range')

    settings = get_settings(product)
    geotracker = settings.get_current_geotracker_item()
    geomobj = geotracker.geomobj
    loader = settings.loader()

    gt = loader.kt_geotracker()

    pins = loader.viewport().pins()
    pins_count = gt.pins_count()
    selected_pins = pins.get_selected_pins(pins_count)
    selected_pins_count = len(selected_pins)
    if selected_pins_count == 0:
        return ActionStatus(False, 'No pins selected')

    current_frame = bpy_current_frame()
    geo = loader.get_geo()
    geo_mesh = geo.mesh(0)

    points = np.empty((selected_pins_count, 3), dtype=np.float32)
    normals = np.empty((selected_pins_count, 3), dtype=np.float32)
    for i, pin_index in enumerate(selected_pins):
        pin = gt.pin(current_frame, pin_index)
        points[i] = pin_to_xyz_from_geo_mesh(pin, geo_mesh)
        normals[i] = pin_to_normal_from_geo_mesh(pin, geo_mesh)

    pin_positions = points @ xy_to_xz_rotation_matrix_3x3()
    scale_inv = InvScaleFromMatrix(geomobj.matrix_world)
    inv_mat = geomobj.matrix_world.inverted_safe()

    empties: List[Object] = []
    zv = Vector((0, 0, 1))

    for i, pos in enumerate(pin_positions):
        empty = create_empty_object('gtPin')
        empty.empty_display_type = 'ARROWS'
        empty.empty_display_size = size

        if orientation == 'NORMAL':
            quaternion_matrix = zv.rotation_difference(
                np.array(normals[i], dtype=np.float32) @
                xy_to_xz_rotation_matrix_3x3()).to_matrix().to_4x4()
            empty.matrix_world = quaternion_matrix
        elif orientation == 'WORLD':
            empty.matrix_world = inv_mat

        empty.location = pos @ scale_inv
        empty.parent = geotracker.geomobj
        empties.append(empty)

    if linked:
        return ActionStatus(True, 'ok')

    settings.start_calculating('NO_SHADER_UPDATE')

    source_matrices = {}
    for frame in range(from_frame, to_frame + 1):
        bpy_set_current_frame(frame)
        matrices: List[Matrix] = []
        for empty in empties:
            matrices.append(empty.matrix_world.copy())
        source_matrices[frame] = matrices

    bpy_set_current_frame(current_frame)

    for empty in empties:
        empty.parent = None

    for frame in range(from_frame, to_frame + 1):
        bpy_set_current_frame(frame)
        for i, empty in enumerate(empties):
            empty.matrix_world = source_matrices[frame][i]
            update_depsgraph()
            create_animation_locrot_keyframe_force(empty)

    prefs = get_addon_preferences()
    if prefs.auto_unbreak_rotation:
        for empty in empties:
            unbreak_status = unbreak_object_rotation_act(empty)
            if not unbreak_status.success:
                _log.error(unbreak_status.error_message)

    bpy_set_current_frame(current_frame)

    settings.stop_calculating()

    _log.output(f'create_hard_empties_from_selected_pins_action end >>>')
    return ActionStatus(True, 'ok')


def create_soft_empties_from_selected_pins_action(
        from_frame: int, to_frame: int, linked: bool = False,
        orientation: str = 'NORMAL', size: float = 1.0,
        *, product: int) -> ActionStatus:
    _log.yellow(f'create_soft_empties_from_selected_pins_action start [{product_name(product)}]')
    check_status = common_checks(product=product,
                                 object_mode=True, pinmode=True,
                                 is_calculating=True, reload_geotracker=True,
                                 geotracker=True, camera=True, geometry=True)
    if not check_status.success:
        return check_status

    if from_frame < 0 or to_frame < from_frame:
        return ActionStatus(False, 'Wrong frame range')

    settings = get_settings(product)
    geotracker = settings.get_current_geotracker_item()
    geomobj = geotracker.geomobj
    loader = settings.loader()

    gt = loader.kt_geotracker()

    pins = loader.viewport().pins()
    pins_count = gt.pins_count()
    selected_pins = pins.get_selected_pins(pins_count)
    selected_pins_count = len(selected_pins)
    if selected_pins_count == 0:
        return ActionStatus(False, 'No pins selected')

    zv = Vector((0, 0, 1))
    empties: List[Object] = []
    for i in range(selected_pins_count):
        empty = create_empty_object('ftPin')
        empty.empty_display_type = 'ARROWS'
        empty.empty_display_size = size
        empty.parent = geotracker.geomobj
        empties.append(empty)

    current_frame = bpy_current_frame()

    settings.start_calculating('NO_SHADER_UPDATE')

    for frame in range(from_frame, to_frame + 1):
        bpy_set_current_frame(frame)
        geo = gt.applied_args_model_at(frame)
        geo_mesh = geo.mesh(0)

        geomobj_matrix_world = geomobj.matrix_world
        scale_inv = InvScaleFromMatrix(geomobj_matrix_world)
        inv_mat = geomobj_matrix_world.inverted_safe()

        for i, pin_index in enumerate(selected_pins):
            empty = empties[i]
            pin = gt.pin(frame, pin_index)
            point = pin_to_xyz_from_geo_mesh(pin, geo_mesh)
            normal = pin_to_normal_from_geo_mesh(pin, geo_mesh)
            pos = np.array(point, dtype=np.float32) @ xy_to_xz_rotation_matrix_3x3()

            if orientation == 'NORMAL':
                quaternion_matrix = zv.rotation_difference(
                    np.array(normal, dtype=np.float32) @
                    xy_to_xz_rotation_matrix_3x3()).to_matrix().to_4x4()
                empty.matrix_world = quaternion_matrix
            elif orientation == 'WORLD':
                empty.matrix_world = inv_mat

            empty.location = pos @ scale_inv
            update_depsgraph()
            create_animation_locrot_keyframe_force(empty)

    prefs = get_addon_preferences()
    if prefs.auto_unbreak_rotation:
        for empty in empties:
            unbreak_status = unbreak_object_rotation_act(empty)
            if not unbreak_status.success:
                _log.error(unbreak_status.error_message)

    if linked:
        bpy_set_current_frame(current_frame)
        settings.stop_calculating()
        return ActionStatus(True, 'ok')

    source_matrices = {}
    for frame in range(from_frame, to_frame + 1):
        bpy_set_current_frame(frame)
        matrices: List[Matrix] = []
        for empty in empties:
            matrices.append(empty.matrix_world.copy())
        source_matrices[frame] = matrices

    for empty in empties:
        empty.parent = None

    for frame in range(from_frame, to_frame + 1):
        bpy_set_current_frame(frame)
        for i, empty in enumerate(empties):
            empty.matrix_world = source_matrices[frame][i]
            update_depsgraph()
            create_animation_locrot_keyframe_force(empty)

    bpy_set_current_frame(current_frame)
    settings.stop_calculating()
    _log.output(f'create_soft_empties_from_selected_pins_action end >>>')
    return ActionStatus(True, 'ok')


def check_uv_exists(obj: Optional[Object]) -> ActionStatus:
    if not obj or not obj.data.uv_layers.active:
        return ActionStatus(False, 'No UV map on object')
    return ActionStatus(True, 'ok')


def check_uv_overlapping(obj: Optional[Object]) -> ActionStatus:
    if not BVersion.uv_select_overlap_exists:
        return ActionStatus(False, 'Too old Blender version for overlapping check')

    old_mode = obj.mode
    select_object_only(obj)

    mesh = obj.data
    mesh.polygons.foreach_set('select', [True] * len(mesh.polygons))

    switch_to_mode('EDIT')
    bpy.ops.uv.select_overlap()
    switch_to_mode('OBJECT')

    uvmap = obj.data.uv_layers.active.data
    selected = np.empty((len(uvmap),), dtype=np.bool_)
    uvmap.foreach_get('select', selected.ravel())

    switch_to_mode(old_mode)
    if np.any(selected):
        return ActionStatus(False, 'Overlapping UVs detected')
    return ActionStatus(True, 'ok')


def check_uv_overlapping_with_status(geotracker: Any) -> ActionStatus:
    status = check_uv_overlapping(geotracker.geomobj)
    geotracker.overlapping_detected = not status.success
    return status


def create_non_overlapping_uv_action(*, product: int) -> ActionStatus:
    _log.yellow(f'create_non_overlapping_uv_action start [{product_name(product)}]')
    settings = get_settings(product)
    geotracker = settings.get_current_geotracker_item()
    geomobj = geotracker.geomobj
    old_mode = geomobj.mode
    if not geomobj.data.uv_layers.active:
        uv_layer = geomobj.data.uv_layers.new()

    select_object_only(geomobj)

    mesh = geomobj.data
    mesh.polygons.foreach_set('select', [True] * len(mesh.polygons))

    switch_to_mode('EDIT')
    bpy.ops.uv.smart_project(island_margin=0.01)
    switch_to_mode(old_mode)

    if geotracker.overlapping_detected:
        return check_uv_overlapping_with_status(geotracker)

    _log.output(f'create_non_overlapping_uv_action end >>>')
    return ActionStatus(True, 'ok')


def repack_uv_action(*, product: int) -> ActionStatus:
    _log.yellow(f'repack_uv_action start [{product_name(product)}]')
    settings = get_settings(product)
    geotracker = settings.get_current_geotracker_item()
    geomobj = geotracker.geomobj
    old_mode = geomobj.mode

    select_object_only(geomobj)

    mesh = geomobj.data
    uv_layer = mesh.uv_layers.active
    if not uv_layer :
        uv_layer = mesh.uv_layers.new()
    uvmap = uv_layer.data

    mesh.polygons.foreach_set('select', [True] * len(mesh.polygons))
    uvmap.foreach_set('select', [True] * len(uvmap))
    _log.output('repack_uv_action all polygons are selected')

    _log.output(f'repack_uv_action mode: {old_mode}')
    switch_to_mode('EDIT')
    _log.output('repack_uv_action average_islands_scale')
    bpy.ops.uv.average_islands_scale()
    _log.output('repack_uv_action pack_islands')
    bpy.ops.uv.pack_islands(margin=0.01)
    _log.output(f'repack_uv_action mode: {old_mode}')
    switch_to_mode(old_mode)
    _log.output('repack_uv_action end >>>')
    return ActionStatus(True, 'ok')


def bake_texture_from_frames_action(area: Area, selected_frames: List,
                                    *, product: int) -> ActionStatus:
    _log.yellow(f'bake_texture_from_frames_action [{product_name(product)}]:'
                f'\n{selected_frames}')
    if not area:
        return ActionStatus(False, 'Improper context area')

    settings = get_settings(product)
    geotracker = settings.get_current_geotracker_item()

    check_status = check_uv_exists(geotracker.geomobj)
    if not check_status.success:
        return check_status

    absent_frames = check_background_image_absent_frames(
        geotracker.camobj, index=0, frames=selected_frames)
    if len(absent_frames) > 0:
        return ActionStatus(False, f'Frames {absent_frames} are outside of Clip range')

    check_status = check_uv_overlapping_with_status(geotracker)

    prepare_camera(area, product=product)
    built_texture = bake_texture(geotracker, selected_frames, product=product)
    revert_camera(area, product=product)

    if settings.pinmode:
        settings.reload_current_geotracker()
        settings.loader().update_viewport_shaders(geomobj_matrix=True,
                                                  pins_and_residuals=True)
    if built_texture is None:
        bad_frame = get_bad_frame()
        if bad_frame < 0:
            msg = 'Operation failed'
        else:
            msg = f'Frame {bad_frame} read error'
        _log.error(msg)
        return ActionStatus(False, msg)

    mat, tex = preview_material_with_texture(built_texture, geotracker.geomobj,
                                             geotracker.preview_texture_name(),
                                             geotracker.preview_material_name())
    if tex is not None:
        try:
            tex.colorspace_settings.name = \
                geotracker.movie_clip.colorspace_settings.name
        except Exception as err:
            _log.error(f'bake_texture_from_frames_act Exception:\n{str(err)}')

    if not check_status.success:
        return ActionStatus(False, f'Done but {check_status.error_message}')

    _log.output('bake_texture_from_frames_action end >>>')
    return ActionStatus(True, 'ok')


def transfer_tracking_to_camera_action(*, product: int) -> ActionStatus:
    _log.yellow(f'transfer_tracking_to_camera_action start [{product_name(product)}]')
    check_status = common_checks(product=product,
                                 object_mode=True, is_calculating=True,
                                 reload_geotracker=True, geotracker=True,
                                 camera=True, geometry=True)
    if not check_status.success:
        return check_status

    settings = get_settings(product)
    geotracker = settings.get_current_geotracker_item()

    geomobj = geotracker.geomobj
    camobj = geotracker.camobj
    geom_matrix = geomobj.matrix_world.copy()

    geom_animated_frames = get_object_keyframe_numbers(geomobj)
    cam_animated_frames = get_object_keyframe_numbers(camobj)
    if len(geom_animated_frames) == 0:
        msg = 'Geometry does not have any keyframes'
        _log.error(msg)
        return ActionStatus(False, msg)

    current_frame = reset_unsaved_animation_changes_in_frame()

    loader = settings.loader()
    gt = loader.kt_geotracker()

    all_animated_frames = list(set(geom_animated_frames).union(set(cam_animated_frames)))
    all_animated_frames.sort()
    _log.output(f'ALL FRAMES: {all_animated_frames}')
    all_matrices = {x:gt.model_mat(x) for x in all_animated_frames}
    _log.output(f'ALL: {all_matrices.keys()}')

    bpy_progress_begin(0, len(all_matrices))
    for i, frame in enumerate(all_matrices):
        bpy_set_current_frame(frame)
        delete_locrot_keyframe(geomobj)
        geomobj.matrix_world = geom_matrix
        loader.place_camera_relative_to_object(all_matrices[frame])
        update_depsgraph()
        create_animation_locrot_keyframe_force(camobj)
        bpy_progress_update(i)

    bpy_progress_end()

    bpy_set_current_frame(current_frame)
    geotracker.solve_for_camera = True
    mark_object_keyframes(camobj, product=product)

    prefs = get_addon_preferences()
    if prefs.auto_unbreak_rotation:
        unbreak_status = unbreak_rotation_act(product=product)
        if not unbreak_status.success:
            return unbreak_status

    _log.output('transfer_tracking_to_camera_action end >>>')
    return ActionStatus(True, 'ok')


def transfer_tracking_to_geometry_action(*, product: int) -> ActionStatus:
    _log.yellow(f'transfer_tracking_to_geometry_action start [{product_name(product)}]')
    check_status = common_checks(product=product,
                                 object_mode=True, is_calculating=True,
                                 reload_geotracker=True, geotracker=True,
                                 camera=True, geometry=True)
    if not check_status.success:
        return check_status

    settings = get_settings(product)
    geotracker = settings.get_current_geotracker_item()

    geomobj = geotracker.geomobj
    camobj = geotracker.camobj
    cam_matrix = camobj.matrix_world.copy()

    geom_animated_frames = get_object_keyframe_numbers(geomobj)
    cam_animated_frames = get_object_keyframe_numbers(camobj)
    if len(cam_animated_frames) == 0:
        msg = 'Camera does not have any keyframes'
        _log.error(msg)
        return ActionStatus(False, msg)

    current_frame = reset_unsaved_animation_changes_in_frame()

    loader = settings.loader()
    gt = loader.kt_geotracker()

    all_animated_frames = list(set(geom_animated_frames).union(set(cam_animated_frames)))
    all_animated_frames.sort()
    _log.output(f'ALL FRAMES: {all_animated_frames}')
    all_matrices = {x:gt.model_mat(x) for x in all_animated_frames}
    _log.output(f'ALL: {all_matrices.keys()}')

    bpy_progress_begin(0, len(all_matrices))
    for i, frame in enumerate(all_matrices):
        bpy_set_current_frame(frame)
        delete_locrot_keyframe(camobj)
        camobj.matrix_world = cam_matrix
        loader.place_object_relative_to_camera(all_matrices[frame])
        update_depsgraph()
        create_animation_locrot_keyframe_force(geomobj)
        bpy_progress_update(i)

    bpy_progress_end()

    bpy_set_current_frame(current_frame)
    geotracker.solve_for_camera = False
    mark_object_keyframes(geomobj, product=product)

    prefs = get_addon_preferences()
    if prefs.auto_unbreak_rotation:
        unbreak_status = unbreak_rotation_act(product=product)
        if not unbreak_status.success:
            return unbreak_status

    _log.output('transfer_tracking_to_geometry_action end >>>')
    return ActionStatus(True, 'ok')


def render_with_background_action(*, product: int) -> ActionStatus:
    _log.yellow(f'render_with_background_action start [{product_name(product)}]')
    check_status = common_checks(product=product,
                                 object_mode=True, is_calculating=True,
                                 reload_geotracker=True, geotracker=True,
                                 camera=True, geometry=True)
    if not check_status.success:
        return check_status

    settings = get_settings(product)
    geotracker = settings.get_current_geotracker_item()
    scene = bpy_scene()
    scene.use_nodes = True
    scene.render.film_transparent = True

    bg_img = get_background_image_object(geotracker.camobj)
    if not bg_img:
        return ActionStatus(False, 'Camera background is not initialized')
    img = bg_img.image
    if not img:
        return ActionStatus(False, 'Camera background is not initialized2')
    node_bg_image = create_nodes_for_rendering_with_background(scene)
    node_bg_image.image = img
    node_bg_image.frame_duration = scene.frame_end

    bpy.ops.render.view_show('INVOKE_DEFAULT')
    bpy_render_single_frame(scene)
    _log.output('render_with_background_action end >>>')
    return ActionStatus(True, 'ok')


def revert_default_render_action(*, product: int) -> ActionStatus:
    _log.yellow(f'revert_default_render_action start [{product_name(product)}]')
    check_status = common_checks(product=product,
                                 object_mode=True, is_calculating=True,
                                 reload_geotracker=True, geotracker=True,
                                 camera=True, geometry=True)
    if not check_status.success:
        return check_status

    settings = get_settings(product)
    geotracker = settings.get_current_geotracker_item()
    scene = bpy_scene()
    scene.render.film_transparent = False

    bg_img = get_background_image_object(geotracker.camobj)
    if not bg_img:
        return ActionStatus(False, 'Camera background is not initialized')
    img = bg_img.image
    if not img:
        return ActionStatus(False, 'Camera background is not initialized2')
    if not revert_default_compositing(scene):
        scene.use_nodes = False
    bpy.ops.render.view_show('INVOKE_DEFAULT')
    bpy_render_single_frame(scene)
    _log.output('revert_default_render_action end >>>')
    return ActionStatus(True, 'ok')


def save_facs_as_csv_action(*, filepath: Optional[str] = None,
                            from_frame: int = 1,
                            to_frame: int = 1,
                            use_tracked_only: bool = False,
                            facs_animation_object: Optional[Any] = None) -> ActionStatus:
    _log.yellow(f'save_facs_as_csv_action start')
    check_status = common_checks(product=ProductType.FACETRACKER,
                                 object_mode=True, is_calculating=True,
                                 reload_geotracker=True, geotracker=True,
                                 camera=True, geometry=True)
    if not check_status.success:
        return check_status

    start_time = time.time()

    fps = bpy_scene().render.fps

    settings = ft_settings()
    geotracker = settings.get_current_geotracker_item()
    if not geotracker:
        return ActionStatus(False, 'FaceTracker is not found')

    ft = settings.loader().kt_geotracker()

    try:
        neutral_geo = ft.scaled_input_geo()
        face_model_scale = ft.get_face_model_scale()
        facs_executor = pkt_module().FacsExecutor(neutral_geo, face_model_scale)
        facs_animation = facs_animation_object \
            if facs_animation_object is not None \
            else pkt_module().FacsAnimation()

        if not use_tracked_only:
            frames = [x for x in range(from_frame, to_frame + 1)]
        else:
            frames = [x for x in ft.track_frames()
                      if from_frame <= x <= to_frame]

        bpy_progress_begin(0, len(frames))
        frame_count = 0
        for frame in frames:
            current_frame_vertices = ft.applied_args_model_vertices_at(frame)
            facs_coeffs = facs_executor.approximate_vertices(current_frame_vertices)
            facs_animation.set_at_frame(frame, facs_coeffs)
            frame_count += 1
            bpy_progress_update(frame_count)

        if filepath is not None:
            res = facs_animation.save_as_csv_to_file(filepath, fps)
            if not res:
                return ActionStatus(False, 'Cannot save FACS animation as CSV')
            res_str = 'ok'
        else:
            res_str = facs_animation.save_as_csv_to_string(fps)
    except Exception as err:
        _log.error(f'save_facs_as_csv_action Exception:\n{str(err)}')
        return ActionStatus(False, 'Exception while save FACS animation')
    finally:
        bpy_progress_end()
        _log.output(f'save_facs_as_csv_action '
                    f'time: {time.time() - start_time:.2f} sec. end >>>')
    return ActionStatus(True, res_str)


def save_facs_as_animation_action(*, from_frame: int = 1, to_frame: int = 1,
                                  use_tracked_only: bool = False,
                                  obj: Object,
                                  action_name: str = 'ktARKit_anim') -> ActionStatus:
    _log.yellow(f'save_facs_as_csv_action start')
    facs_animation = pkt_module().FacsAnimation()
    save_status = save_facs_as_csv_action(filepath=None,
                                          from_frame=from_frame,
                                          to_frame=to_frame,
                                          use_tracked_only=use_tracked_only,
                                          facs_animation_object=facs_animation)
    if not save_status.success:
        return save_status

    facs_names = pkt_module().FacsExecutor.facs_names

    blendshape_action = bpy_new_action(action_name)

    for name in facs_names:
        blendshape_fcurve = get_safe_action_fcurve(
            blendshape_action, 'key_blocks["{}"].value'.format(name), index=0)

        keyframes = [x for x in facs_animation.keyframes()]
        if len(keyframes) > 0:
            start_keyframe = keyframes[0]
            end_keyframe = keyframes[-1]
        else:
            start_keyframe = 0
            end_keyframe = -1
        cleanup_keys_in_interval(blendshape_fcurve,
                                 start_keyframe, end_keyframe)

        anim_data_list = [x for x in zip(keyframes, facs_animation.at_name(name))]
        put_anim_data_in_fcurve(blendshape_fcurve, anim_data_list)
        snap_keys_in_interval(blendshape_fcurve, start_keyframe, end_keyframe)

    if not obj.data.shape_keys:
        create_basis_blendshape(obj)
    anim_data = obj.data.shape_keys.animation_data
    if not anim_data:
        anim_data = obj.data.shape_keys.animation_data_create()
    anim_data.action = blendshape_action
    bpy_init_action_slot(anim_data)
    obj.data.update()

    return ActionStatus(True, 'ok')


_stored_data: Dict = {}


def store_data(name: str, mat: Any) -> None:
    global _stored_data
    _log.output(f'store_data {name}')
    _stored_data[name] = mat


def get_stored_data(name: str) -> Any:
    global _stored_data
    if name in _stored_data.keys():
        return _stored_data[name]
    _log.error(f'get_stored_data("{name}") is not found')
    return None


def store_camobj_state(operator: Operator, camobj: Object) -> None:
    store_data('camobj_matrix_basis', camobj.matrix_basis.copy())
    store_data('camobj_matrix_world', camobj.matrix_world.copy())
    store_data('camobj_scale', camobj.scale.copy())
    operator.cam_scale = camobj.scale


def store_geomobj_state(operator: Operator, geomobj: Object) -> None:
    store_data('geomobj_matrix_basis', geomobj.matrix_basis.copy())
    store_data('geomobj_matrix_world', geomobj.matrix_world.copy())
    store_data('geomobj_scale', geomobj.scale.copy())
    operator.geom_scale = geomobj.scale


def revert_object_states(*, product: int) -> bool:
    _log.output('revert_object_states')
    settings = get_settings(product)
    geotracker = settings.get_current_geotracker_item()
    if not geotracker or not geotracker.geomobj or not geotracker.camobj:
        return False

    geotracker.geomobj.matrix_basis = get_stored_data('geomobj_matrix_basis').copy()
    geotracker.camobj.matrix_basis = get_stored_data('camobj_matrix_basis').copy()
    update_depsgraph()
    return True


def _scale_relative_to_point_matrix(origin_matrix: Matrix,
                                    scale: float) -> Matrix:
    scale_mat = Matrix.Scale(scale, 4)
    return origin_matrix @ scale_mat @ origin_matrix.inverted()


def _apply_geomobj_scale(geomobj: Object, operator: Operator) -> None:
    if operator.keep_geom_scale:
        geomobj.scale = operator.geom_scale
    else:
        geomobj.scale = (operator.geom_scale[0] * operator.value,
                         operator.geom_scale[1] * operator.value,
                         operator.geom_scale[2] * operator.value)


def _apply_camobj_scale(camobj: Object, operator: Operator) -> None:
    if operator.keep_cam_scale:
        camobj.scale = operator.cam_scale
    else:
        camobj.scale = (operator.cam_scale[0] * operator.value,
                        operator.cam_scale[1] * operator.value,
                        operator.cam_scale[2] * operator.value)


def _get_operator_origin_matrix(origin_point: str, *, product: int) -> Matrix:
    settings = get_settings(product)
    geotracker = settings.get_current_geotracker_item()
    origin_matrix = Matrix.Identity(4)
    if origin_point == 'GEOMETRY':
        origin_matrix = LocRotWithoutScale(geotracker.geomobj.matrix_world)
    elif origin_point == 'CAMERA':
        origin_matrix = LocRotWithoutScale(geotracker.camobj.matrix_world)
    elif origin_point == '3D_CURSOR':
        origin_matrix = bpy_scene().cursor.matrix.copy()
    return origin_matrix


def scale_scene_tracking_preview_func(operator: Operator, context: Any) -> None:
    product = operator.product

    if not revert_object_states(product=product):
        return

    settings = get_settings(product)
    geotracker = settings.get_current_geotracker_item()
    geomobj = geotracker.geomobj
    camobj = geotracker.camobj
    origin_matrix = _get_operator_origin_matrix(operator.origin_point,
                                                product=product)
    rescale_matrix = _scale_relative_to_point_matrix(origin_matrix,
                                                     operator.value)
    camobj.matrix_world = rescale_matrix @ camobj.matrix_world
    _apply_camobj_scale(camobj, operator)
    geomobj.matrix_world = rescale_matrix @ geomobj.matrix_world
    _apply_geomobj_scale(geomobj, operator)


def scale_scene_tracking_action(operator: Operator,
                                *, product: int) -> ActionStatus:
    _log.yellow(f'scale_scene_tracking_action start [{product_name(product)}]')
    settings = get_settings(product)
    geotracker = settings.get_current_geotracker_item()
    geomobj = geotracker.geomobj
    camobj = geotracker.camobj
    current_frame = bpy_current_frame()
    revert_object_states(product=product)

    geom_animated_frame_set = set(get_object_keyframe_numbers(geomobj))
    cam_animated_frame_set = set(get_object_keyframe_numbers(camobj))
    all_animated_frame_set = geom_animated_frame_set.union(
        cam_animated_frame_set)

    static_origin_matrix = _get_operator_origin_matrix(operator.origin_point,
                                                       product=product)
    static_rescale_matrix = _scale_relative_to_point_matrix(
        static_origin_matrix, operator.value)
    rescale_matrix = static_rescale_matrix

    source_geom_matrices = {}
    source_cam_matrices = {}
    bpy_progress_begin(0, len(all_animated_frame_set))
    for i, frame in enumerate(all_animated_frame_set):
        bpy_set_current_frame(frame)
        source_geom_matrices[frame] = geomobj.matrix_world.copy()
        source_cam_matrices[frame] = camobj.matrix_world.copy()
        bpy_progress_update(i)

    bpy_progress_end()

    if operator.mode == 'GEOMETRY':
        bpy_progress_begin(0, len(geom_animated_frame_set))
        for i, frame in enumerate(geom_animated_frame_set):
            bpy_set_current_frame(frame)
            rescale_matrix = _scale_relative_to_point_matrix(
                LocRotWithoutScale(source_cam_matrices[frame]), operator.value)

            geomobj.matrix_world = rescale_matrix @ source_geom_matrices[frame]
            _apply_geomobj_scale(geomobj, operator)
            update_depsgraph()
            create_animation_locrot_keyframe_force(geomobj)
            bpy_progress_update(i)

        bpy_progress_end()

        bpy_set_current_frame(current_frame)
        if len(geom_animated_frame_set) == 0:
            geomobj.matrix_world = \
                rescale_matrix @ get_stored_data('geomobj_matrix_world')

    elif operator.mode == 'CAMERA':
        bpy_progress_begin(0, len(cam_animated_frame_set))
        for i, frame in enumerate(cam_animated_frame_set):
            bpy_set_current_frame(frame)
            rescale_matrix = _scale_relative_to_point_matrix(
                LocRotWithoutScale(source_geom_matrices[frame]), operator.value)

            camobj.matrix_world = rescale_matrix @ source_cam_matrices[frame]
            _apply_camobj_scale(camobj, operator)
            update_depsgraph()
            create_animation_locrot_keyframe_force(camobj)
            bpy_progress_update(i)

        bpy_progress_end()

        bpy_set_current_frame(current_frame)
        if len(cam_animated_frame_set) == 0:
            camobj.matrix_world = \
                rescale_matrix @ get_stored_data('camobj_matrix_world')
    else:
        bpy_progress_begin(0, len(all_animated_frame_set))
        for i, frame in enumerate(all_animated_frame_set):
            bpy_set_current_frame(frame)
            camobj.matrix_world = rescale_matrix @ source_cam_matrices[frame]
            geomobj.matrix_world = rescale_matrix @ source_geom_matrices[frame]
            _apply_camobj_scale(camobj, operator)
            _apply_geomobj_scale(geomobj, operator)
            update_depsgraph()
            if frame in cam_animated_frame_set:
                create_animation_locrot_keyframe_force(camobj)
            if frame in geom_animated_frame_set:
                create_animation_locrot_keyframe_force(geomobj)
            bpy_progress_update(i)

        bpy_progress_end()

        bpy_set_current_frame(current_frame)
        if len(cam_animated_frame_set) == 0:
            camobj.matrix_world = \
                rescale_matrix @ get_stored_data('camobj_matrix_world')

        if len(geom_animated_frame_set) == 0:
            geomobj.matrix_world = \
                rescale_matrix @ get_stored_data('geomobj_matrix_world')

    _apply_camobj_scale(camobj, operator)
    _apply_geomobj_scale(geomobj, operator)

    loader = settings.loader()
    loader.save_geotracker()

    prefs = get_addon_preferences()
    if prefs.auto_unbreak_rotation:
        unbreak_status = unbreak_rotation_act(product=product)
        if not unbreak_status.success:
            return unbreak_status

    if not settings.reload_current_geotracker():
        msg = 'Cannot reload GeoTracker data'
        _log.error(msg)
        return ActionStatus(False, msg)

    if settings.pinmode:
        loader.update_viewport_shaders(geomobj_matrix=True,
                                       pins_and_residuals=True)
    _log.output('scale_scene_tracking_action end >>>')
    return ActionStatus(True, 'ok')


def scale_scene_trajectory_act(
        operator: Operator, *,
        product: int = ProductType.GEOTRACKER) -> ActionStatus:
    check_status = common_checks(product=product,
                                 object_mode=True, is_calculating=True,
                                 reload_geotracker=True, geotracker=True,
                                 camera=True, geometry=True)
    if not check_status.success:
        return check_status

    settings = get_settings(product)
    geotracker = settings.get_current_geotracker_item()
    geomobj = geotracker.geomobj
    camobj = geotracker.camobj
    current_frame = bpy_current_frame()

    geom_animated_frames = get_object_keyframe_numbers(geomobj)
    cam_animated_frames = get_object_keyframe_numbers(camobj)

    origin_matrix = _get_operator_origin_matrix(operator.origin_point,
                                                product=product)
    rescale_matrix = _scale_relative_to_point_matrix(origin_matrix,
                                                     operator.value)

    cam_scale_matrix = ScaleMatrix(4, operator.cam_scale)
    cam_scale_matrix_inv = InvScaleMatrix(4, operator.cam_scale)
    _log.output(f'cam_scale_matrix_inv: {cam_scale_matrix_inv}')

    operator_scale_matrix = Matrix.Scale(operator.value, 4)
    operator_scale_matrix_inv = Matrix.Scale(1.0 / operator.value, 4)
    rescale_matrix = origin_matrix @ operator_scale_matrix @ origin_matrix.inverted()

    scene_frame_set = set(scene_frame_list())
    geom_animated_frame_set = set(get_object_keyframe_numbers(geomobj))
    cam_animated_frame_set = set(get_object_keyframe_numbers(camobj))
    all_animated_frame_set = scene_frame_set \
        .union(geom_animated_frame_set) \
        .union(cam_animated_frame_set)

    geom_matrices = {}
    cam_matrices = {}
    for frame in all_animated_frame_set:
        bpy_set_current_frame(frame)
        geom_matrices[frame] = geomobj.matrix_world.copy()
        cam_matrices[frame] = camobj.matrix_world.copy()

    model_matrices = [LocRotWithoutScale(cam_matrices[x].inverted() @ geom_matrices[x])
                      for x in all_animated_frame_set]

    revert_object_states(product=product)

    for frame in all_animated_frame_set:
        bpy_set_current_frame(frame)
        mat = rescale_matrix @ LocRotWithoutScale(cam_matrices[frame])
        # camobj.matrix_world = mat.copy()
        camobj.matrix_world = rescale_matrix @ camobj.matrix_world
        camobj.scale = operator.cam_scale
        _log.output(f'camera scale: {camobj.scale}')

        geomobj.matrix_world = LocRotWithoutScale(mat) @ model_matrices[frame]
        geomobj.scale = operator.geom_scale

        update_depsgraph()
        if frame in cam_animated_frames:
            create_animation_locrot_keyframe_force(camobj)
        if frame in geom_animated_frames:
            create_animation_locrot_keyframe_force(geomobj)
        # camobj.scale = operator.cam_scale

    bpy_set_current_frame(current_frame)

    loader = settings.loader()
    loader.save_geotracker()
    if not settings.reload_current_geotracker():
        msg = 'Cannot reload GeoTracker data'
        _log.error(msg)
        return ActionStatus(False, msg)

    if settings.pinmode:
        loader.update_viewport_shaders(geomobj_matrix=True,
                                       pins_and_residuals=True)
    return ActionStatus(True, 'ok')


def get_operator_reposition_matrix(operator: Operator,
                                   *, product: int) -> Matrix:
    settings = get_settings(product)
    geotracker = settings.get_current_geotracker_item()
    from_matrix = geotracker.geomobj.matrix_world \
        if operator.mode == 'GEOMETRY' else geotracker.camobj.matrix_world

    t, r, s = from_matrix.decompose()
    source_matrix = LocRotScale(t, r, (1, 1, 1))
    quat = Euler(operator.euler_rotation, 'XYZ').to_quaternion()
    target_matrix = LocRotScale(operator.location, quat, (1, 1, 1))
    return target_matrix @ source_matrix.inverted()


def move_scene_tracking_action(operator: Operator,
                               *, product: int) -> ActionStatus:
    _log.yellow(f'move_scene_tracking_action start [{product_name(product)}]')
    settings = get_settings(product)
    geotracker = settings.get_current_geotracker_item()
    geomobj = geotracker.geomobj
    camobj = geotracker.camobj
    current_frame = bpy_current_frame()
    revert_object_states(product=product)

    geom_animated_frame_set = set(get_object_keyframe_numbers(geomobj))
    cam_animated_frame_set = set(get_object_keyframe_numbers(camobj))

    transform_matrix = get_operator_reposition_matrix(operator, product=product)
    _log.output(f'transform_matrix:\n{transform_matrix}')

    bpy_progress_begin(0, len(geom_animated_frame_set))
    for i, frame in enumerate(geom_animated_frame_set):
        bpy_set_current_frame(frame)
        geomobj.matrix_world = transform_matrix @ geomobj.matrix_world
        update_depsgraph()
        create_animation_locrot_keyframe_force(geomobj)
        bpy_progress_update(i)

    bpy_progress_end()

    if len(geom_animated_frame_set) == 0:
        geomobj.matrix_world = transform_matrix @ geomobj.matrix_world

    bpy_progress_begin(0, len(cam_animated_frame_set))
    for i, frame in enumerate(cam_animated_frame_set):
        bpy_set_current_frame(frame)
        camobj.matrix_world = transform_matrix @ camobj.matrix_world
        update_depsgraph()
        create_animation_locrot_keyframe_force(camobj)
        bpy_progress_update(i)

    bpy_progress_end()

    if len(cam_animated_frame_set) == 0:
        camobj.matrix_world = transform_matrix @ camobj.matrix_world

    bpy_set_current_frame(current_frame)

    loader = settings.loader()
    loader.save_geotracker()

    prefs = get_addon_preferences()
    if prefs.auto_unbreak_rotation:
        unbreak_status = unbreak_rotation_act(product=product)
        if not unbreak_status.success:
            return unbreak_status

    if not settings.reload_current_geotracker():
        msg = f'Cannot reload {product_name(product)} data'
        _log.error(msg)
        return ActionStatus(False, msg)

    if settings.pinmode:
        loader.update_viewport_shaders(geomobj_matrix=True,
                                       pins_and_residuals=True)
    _log.output('move_scene_tracking_action end >>>')
    return ActionStatus(True, 'ok')


def bake_locrot_action(obj: Object, *, product: int) -> ActionStatus:
    def _remove_all_constraints(obj: Object):
        if len(obj.constraints) != 0:
            all_constraints = [x for x in obj.constraints]
            for x in all_constraints:
                obj.constraints.remove(x)

    _log.yellow(f'bake_locrot_action start [{product_name(product)}]')
    check_status = common_checks(product=product,
                                 object_mode=True, is_calculating=True)
    if not check_status.success:
        return check_status

    if not obj:
        return ActionStatus(False, 'Wrong object')

    if not bpy_poll_is_mesh(None, obj) and not bpy_poll_is_camera(None, obj):
        msg = 'Selected object is not Geometry or Camera'
        return ActionStatus(False, msg)

    if not obj.parent and len(obj.constraints) == 0:
        msg = 'Selected object has no parent'
        return ActionStatus(False, msg)

    obj_animated_frames = get_object_keyframe_numbers(obj)

    if len(obj_animated_frames) == 0:
        obj_animated_frames = [bpy_current_frame()]

    bake_locrot_to_world(obj, obj_animated_frames)
    _remove_all_constraints(obj)

    prefs = get_addon_preferences()
    if prefs.auto_unbreak_rotation:
        unbreak_status = unbreak_rotation_act(product=product)
        if not unbreak_status.success:
            return unbreak_status

    _log.output('bake_locrot_action end >>>')
    return ActionStatus(True, 'ok')


def after_ft_refine(frame_list: List) -> None:
    _log.yellow('after_ft_refine start')
    unbreak_after(frame_list, product=ProductType.FACETRACKER)
    for frame in frame_list:
        create_relative_shape_keyframe(frame)
    _log.output('after_ft_refine end >>>')
