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

from typing import List
import math
import numpy as np

import bpy
from bpy.types import Object, Operator
from mathutils import Matrix, Euler

from ...utils.kt_logging import KTLogger
from ...addon_config import ActionStatus
from ...geotracker_config import (get_gt_settings,
                                  get_current_geotracker_item)
from ..gtloader import GTLoader
from ...utils.animation import (get_action,
                                remove_fcurve_point,
                                remove_fcurve_from_object,
                                delete_locrot_keyframe,
                                mark_selected_points_in_locrot,
                                get_object_keyframe_numbers,
                                create_animation_locrot_keyframe_force,
                                create_locrot_keyframe)
from .tracking import (get_next_tracking_keyframe,
                       get_previous_tracking_keyframe)
from ...utils.bpy_common import (create_empty_object,
                                 bpy_current_frame,
                                 bpy_set_current_frame,
                                 update_depsgraph,
                                 reset_unsaved_animation_changes_in_frame,
                                 bpy_scene,
                                 bpy_render_single_frame)
from ...blender_independent_packages.pykeentools_loader import module as pkt_module
from ...utils.manipulate import select_objects_only, center_viewport, select_object_only
from .textures import bake_texture, preview_material_with_texture
from .prechecks import (common_checks,
                        track_checks,
                        get_alone_object_in_scene_selection_by_type,
                        get_alone_object_in_scene_by_type,
                        prepare_camera,
                        revert_camera,
                        show_warning_dialog,
                        show_unlicensed_warning)
from ...utils.compositing import (create_nodes_for_rendering_with_background,
                                  revert_default_compositing)
from ...utils.images import get_background_image_object
from .calc_timer import (TrackTimer,
                         RefineTimer,
                         RefineTimerFast)


_log = KTLogger(__name__)


def create_geotracker_act() -> ActionStatus:
    check_status = common_checks(object_mode=True, pinmode_out=True,
                                 is_calculating=True)
    if not check_status.success:
        return check_status

    settings = get_gt_settings()
    num = settings.add_geotracker_item()
    settings.current_geotracker_num = num
    GTLoader.new_kt_geotracker()

    geotracker = settings.get_current_geotracker_item()
    obj = get_alone_object_in_scene_selection_by_type('MESH')
    if obj is None:
        obj = get_alone_object_in_scene_by_type('MESH')
    geotracker.geomobj = obj

    camobj = get_alone_object_in_scene_selection_by_type('CAMERA')
    if camobj is None:
        camobj = get_alone_object_in_scene_by_type('CAMERA')
    geotracker.camobj = camobj

    settings.reload_current_geotracker()
    return ActionStatus(True, 'GeoTracker has been added')


def delete_geotracker_act(geotracker_num: int) -> ActionStatus:
    check_status = common_checks(object_mode=True, pinmode_out=True,
                                 is_calculating=True)
    if not check_status.success:
        return check_status

    settings = get_gt_settings()
    res = settings.remove_geotracker_item(geotracker_num)
    if not res:
        msg = 'Could not delete a GeoTracker'
        _log.error(msg)
        return ActionStatus(False, msg)
    settings.reload_current_geotracker()
    return ActionStatus(True, 'GeoTracker has been removed')


def add_keyframe_act() -> ActionStatus:
    check_status = common_checks(object_mode=True, pinmode=True,
                                 is_calculating=True, reload_geotracker=True,
                                 geotracker=True, camera=True, geometry=True)
    if not check_status.success:
        return check_status

    area = GTLoader.get_work_area()
    if not area:
        return ActionStatus(False, 'Working area does not exist')

    GTLoader.safe_keyframe_add(bpy_current_frame(), update=True)
    GTLoader.save_geotracker()
    return ActionStatus(True, 'ok')


def remove_keyframe_act() -> ActionStatus:
    check_status = common_checks(object_mode=True, pinmode=True,
                                 is_calculating=True, reload_geotracker=True,
                                 geotracker=True, camera=True, geometry=True)
    if not check_status.success:
        return check_status

    gt = GTLoader.kt_geotracker()
    current_frame = bpy_current_frame()
    if gt.is_key_at(current_frame):
        gt.remove_keyframe(current_frame)
        GTLoader.save_geotracker()
        return ActionStatus(True, 'ok')

    geotracker = get_current_geotracker_item()
    obj = geotracker.animatable_object()
    delete_locrot_keyframe(obj)
    return ActionStatus(True, 'No GeoTracker keyframe at this frame')


def next_keyframe_act() -> ActionStatus:
    settings = get_gt_settings()
    check_status = common_checks(object_mode=False, is_calculating=True,
                                 reload_geotracker=not settings.pinmode,
                                 geotracker=True, camera=True, geometry=True)
    if not check_status.success:
        return check_status

    current_frame = bpy_current_frame()
    target_frame = get_next_tracking_keyframe(GTLoader.kt_geotracker(),
                                              current_frame)
    if current_frame != target_frame:
        bpy_set_current_frame(target_frame)
        return ActionStatus(True, 'ok')
    return ActionStatus(False, 'No next GeoTracker keyframe')


def prev_keyframe_act() -> ActionStatus:
    settings = get_gt_settings()
    check_status = common_checks(object_mode=False, is_calculating=True,
                                 reload_geotracker=not settings.pinmode,
                                 geotracker=True, camera=True, geometry=True)
    if not check_status.success:
        return check_status

    current_frame = bpy_current_frame()
    target_frame = get_previous_tracking_keyframe(GTLoader.kt_geotracker(),
                                                  current_frame)
    if current_frame != target_frame:
        bpy_set_current_frame(target_frame)
        return ActionStatus(True, 'ok')
    return ActionStatus(False, 'No previous GeoTracker keyframe')


def track_to(forward: bool) -> ActionStatus:
    _log.output(f'track_to: {forward}')
    check_status = track_checks()
    if not check_status.success:
        return check_status

    geotracker = get_current_geotracker_item()
    gt = GTLoader.kt_geotracker()
    current_frame = bpy_current_frame()
    precalcless = geotracker.precalcless
    if not precalcless and not \
            geotracker.precalc_start <= current_frame <= geotracker.precalc_end:
        return ActionStatus(False, 'Current frame is outside '
                                   'of the precalc-file range')
    try:
        precalc_path = None if precalcless else geotracker.precalc_path
        _log.output(f'gt.track_async({current_frame}, {forward}, {precalc_path})')
        tracking_computation = gt.track_async(current_frame, forward, precalc_path)
        tracking_timer = TrackTimer(tracking_computation, current_frame)
        tracking_timer.start()
    except pkt_module().UnlicensedException as err:
        _log.error(f'UnlicensedException track_to: {str(err)}')
        show_unlicensed_warning()
        # Return True to prevent doubling dialogs
        return ActionStatus(True, 'Unlicensed error')
    except Exception as err:
        _log.error(f'Unknown Exception track_to: {str(err)}')
        show_warning_dialog(err)
        return ActionStatus(False, 'Some problem (see console)')

    return ActionStatus(True, 'Ok')


def track_next_frame_act(forward: bool=True) -> ActionStatus:
    check_status = track_checks()
    if not check_status.success:
        return check_status

    geotracker = get_current_geotracker_item()
    gt = GTLoader.kt_geotracker()
    current_frame = bpy_current_frame()
    try:
        precalc_path = None if geotracker.precalcless else geotracker.precalc_path
        gt.track_frame(current_frame, forward, precalc_path)
    except pkt_module().UnlicensedException as err:
        _log.error(f'UnlicensedException track_next_frame_act: {str(err)}')
        show_unlicensed_warning()
        # Return True to prevent doubling dialogs
        return ActionStatus(True, 'Unlicensed error')
    except Exception as err:
        msg = 'Track next frame problem (see console)'
        _log.error(f'{msg}\n{str(err)}')
        show_warning_dialog(err)
        return ActionStatus(False, msg)

    GTLoader.save_geotracker()
    current_frame += 1 if forward else -1
    bpy_set_current_frame(current_frame)

    return ActionStatus(True, 'Ok')


def refine_async_act() -> ActionStatus:
    _log.output('refine_async_act call')
    check_status = track_checks()
    if not check_status.success:
        return check_status

    geotracker = get_current_geotracker_item()
    gt = GTLoader.kt_geotracker()
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
            refine_timer = RefineTimer(refine_computation, current_frame)
        else:
            refine_timer = RefineTimerFast(refine_computation, current_frame)
        refine_timer.start()
    except pkt_module().UnlicensedException as err:
        _log.error(f'UnlicensedException refine_async_act: {str(err)}')
        show_unlicensed_warning()
        # Return True to prevent doubling dialogs
        return ActionStatus(True, 'Unlicensed error')
    except Exception as err:
        _log.error(f'Unknown Exception refine_async_act: {str(err)}')
        show_warning_dialog(err)
        return ActionStatus(False, 'Some problem (see console)')

    return ActionStatus(True, 'Ok')


def refine_all_async_act() -> ActionStatus:
    _log.output('refine_all_async_act call')
    check_status = track_checks()
    if not check_status.success:
        return check_status

    geotracker = get_current_geotracker_item()

    gt = GTLoader.kt_geotracker()
    current_frame = bpy_current_frame()
    try:
        precalc_path = None if geotracker.precalcless else geotracker.precalc_path
        refine_computation = gt.refine_all_async(precalc_path)
        if geotracker.precalcless:
            refine_timer = RefineTimer(refine_computation, current_frame)
        else:
            refine_timer = RefineTimerFast(refine_computation, current_frame)
        refine_timer.start()
    except pkt_module().UnlicensedException as err:
        _log.error(f'UnlicensedException refine_all_async_act: {str(err)}')
        show_unlicensed_warning()
        # Return True to prevent doubling dialogs
        return ActionStatus(True, 'Unlicensed error')
    except Exception as err:
        _log.error(f'Unknown Exception refine_all_async_act: {str(err)}')
        show_warning_dialog(err)
        return ActionStatus(False, 'Some problem (see console)')

    return ActionStatus(True, 'Ok')


def clear_between_keyframes_act() -> ActionStatus:
    check_status = common_checks(object_mode=False, pinmode=True,
                                 is_calculating=True, reload_geotracker=True,
                                 geotracker=True, camera=True, geometry=True)
    if not check_status.success:
        return check_status

    current_frame = bpy_current_frame()
    gt = GTLoader.kt_geotracker()
    try:
        gt.remove_track_between_keyframes(current_frame)
    except Exception as err:
        _log.error(f'Unknown Exception clear_between_keyframes_act: {str(err)}')
        show_warning_dialog(err)

    GTLoader.save_geotracker()
    GTLoader.update_viewport_shaders()
    GTLoader.viewport_area_redraw()
    return ActionStatus(True, 'ok')


def clear_direction_act(forward: bool) -> ActionStatus:
    check_status = common_checks(object_mode=False, pinmode=True,
                                 is_calculating=True, reload_geotracker=True,
                                 geotracker=True, camera=True, geometry=True)
    if not check_status.success:
        return check_status

    current_frame = bpy_current_frame()
    gt = GTLoader.kt_geotracker()
    try:
        _log.output(f'clear_direction_act: {current_frame} {forward}')
        gt.remove_track_in_direction(current_frame, forward=forward)
    except Exception as err:
        _log.error(f'Unknown Exception clear_direction_act: {str(err)}')
        show_warning_dialog(err)

    GTLoader.save_geotracker()
    GTLoader.update_viewport_shaders()
    GTLoader.viewport_area_redraw()
    return ActionStatus(True, 'ok')


def clear_all_act() -> ActionStatus:
    check_status = common_checks(object_mode=False, pinmode=True,
                                 is_calculating=True, reload_geotracker=True,
                                 geotracker=True, camera=True, geometry=True)
    if not check_status.success:
        return check_status

    gt = GTLoader.kt_geotracker()
    try:
        gt.remove_all_track_data_and_keyframes()
    except Exception as err:
        _log.error(f'Unknown Exception clear_all_act: {str(err)}')
        show_warning_dialog(err)

    GTLoader.save_geotracker()
    GTLoader.update_viewport_shaders()
    GTLoader.viewport_area_redraw()
    return ActionStatus(True, 'ok')


def clear_all_except_keyframes_act() -> ActionStatus:
    check_status = common_checks(object_mode=True, pinmode=True,
                                 is_calculating=True, reload_geotracker=True,
                                 geotracker=True, camera=True, geometry=True)
    if not check_status.success:
        return check_status

    gt = GTLoader.kt_geotracker()

    keyframes = gt.keyframes()
    if len(keyframes) < 1:
        return clear_all_act()

    for i in range(len(keyframes) - 1):
        start = keyframes[i]
        end = keyframes[i + 1]
        current = start + 1
        if current in [start, end]:
            continue
        gt.remove_track_between_keyframes(current)

    gt.remove_track_in_direction(keyframes[0], False)
    gt.remove_track_in_direction(keyframes[-1], True)

    GTLoader.save_geotracker()
    return ActionStatus(True, 'ok')


def remove_focal_keyframe_act() -> ActionStatus:
    check_status = common_checks(object_mode=False, is_calculating=True,
                                 reload_geotracker=True, geotracker=True,
                                 camera=True)
    if not check_status.success:
        return check_status

    geotracker = get_current_geotracker_item()
    remove_fcurve_point(geotracker.camobj.data, bpy_current_frame(), 'lens')
    return ActionStatus(True, 'ok')


def remove_focal_keyframes_act() -> ActionStatus:
    check_status = common_checks(object_mode=False, is_calculating=True,
                                 reload_geotracker=True, geotracker=True,
                                 camera=True)
    if not check_status.success:
        return check_status

    geotracker = get_current_geotracker_item()
    remove_fcurve_from_object(geotracker.camobj.data, 'lens')
    return ActionStatus(True, 'ok')


def remove_pins_act() -> ActionStatus:
    check_status = common_checks(object_mode=True, pinmode=True,
                                 is_calculating=True, reload_geotracker=True,
                                 geotracker=True, camera=True, geometry=True)
    if not check_status.success:
        return check_status

    gt = GTLoader.kt_geotracker()

    vp = GTLoader.viewport()
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
            selected_pins.remove(i)
        if not GTLoader.solve():
            return ActionStatus(False, 'Could not remove selected pins')
        GTLoader.load_pins_into_viewport()

    pins.reset_current_pin()
    GTLoader.save_geotracker()
    GTLoader.update_viewport_shaders()
    GTLoader.viewport_area_redraw()
    return ActionStatus(True, 'ok')


def toggle_pins_act() -> ActionStatus:
    check_status = common_checks(object_mode=True, pinmode=True,
                                 is_calculating=True, reload_geotracker=True,
                                 geotracker=True, camera=True, geometry=True)
    if not check_status.success:
        return check_status

    gt = GTLoader.kt_geotracker()
    keyframe = bpy_current_frame()
    if gt.pins_count() > 0:
        GTLoader.safe_keyframe_add(keyframe, update=True)
        pins = GTLoader.viewport().pins()
        selected_pins = pins.get_selected_pins()
        if len(selected_pins) == 0:
            gt.toggle_pins(keyframe)
        else:
            gt.toggle_pins(keyframe, selected_pins)
        pins.clear_selected_pins()
        GTLoader.save_geotracker()

    GTLoader.update_viewport_shaders()
    GTLoader.viewport_area_redraw()
    return ActionStatus(True, 'ok')


def center_geo_act() -> ActionStatus:
    check_status = common_checks(object_mode=True, pinmode=True,
                                 is_calculating=True, reload_geotracker=True,
                                 geotracker=True, camera=True, geometry=True)
    if not check_status.success:
        return check_status

    GTLoader.center_geo()
    GTLoader.update_viewport_shaders()
    GTLoader.viewport_area_redraw()
    return ActionStatus(True, 'ok')


def create_animated_empty_act() -> ActionStatus:
    check_status = common_checks(object_mode=True, is_calculating=True,
                                 reload_geotracker=True, geotracker=True,
                                 camera=True, geometry=True)
    if not check_status.success:
        return check_status

    geotracker = get_current_geotracker_item()
    action = get_action(geotracker.animatable_object())
    if not action:
        msg = 'Tracked object has no animation'
        _log.error(msg)
        return ActionStatus(False, msg)

    obj = create_empty_object('GTEmpty')
    anim_data = obj.animation_data_create()
    anim_data.action = action
    return ActionStatus(True, 'ok')


def switch_to_mode_unsafe(mode='OBJECT') -> None:
    bpy.ops.object.mode_set(mode=mode, toggle=False)


def check_uv_overlapping() -> ActionStatus:
    geotracker = get_current_geotracker_item()
    geomobj = geotracker.geomobj
    old_mode = geomobj.mode
    if not geomobj or not geomobj.data.uv_layers.active:
        return ActionStatus(False, 'No UV map on object')

    select_object_only(geomobj)
    if old_mode != 'OBJECT':
        switch_to_mode_unsafe('OBJECT')

    mesh = geomobj.data
    mesh.polygons.foreach_set('select', [True] * len(mesh.polygons))

    switch_to_mode_unsafe('EDIT')
    bpy.ops.uv.select_overlap()
    switch_to_mode_unsafe('OBJECT')

    uvmap = geomobj.data.uv_layers.active.data
    selected = np.empty((len(uvmap),), dtype=np.bool)
    uvmap.foreach_get('select', selected.ravel())

    switch_to_mode_unsafe(old_mode)
    if np.any(selected):
        return ActionStatus(False, 'UV map has overlapping')
    return ActionStatus(True, 'ok')


def create_non_overlapping_uv_act() -> ActionStatus:
    check_status = common_checks(object_mode=True, is_calculating=True,
                                 reload_geotracker=True, geotracker=True,
                                 camera=True, geometry=True)
    if not check_status.success:
        return check_status

    geotracker = get_current_geotracker_item()
    geomobj = geotracker.geomobj
    old_mode = geomobj.mode
    if not geomobj.data.uv_layers.active:
        uv_layer = geomobj.data.uv_layers.new()

    select_object_only(geomobj)
    if old_mode != 'OBJECT':
        switch_to_mode_unsafe('OBJECT')

    mesh = geomobj.data
    mesh.polygons.foreach_set('select', [True] * len(mesh.polygons))

    switch_to_mode_unsafe('EDIT')
    bpy.ops.uv.smart_project()
    switch_to_mode_unsafe(old_mode)
    return ActionStatus(True, 'ok')


def bake_texture_from_frames_act(selected_frames: List) -> ActionStatus:
    _log.output(f'bake_texture_from_frames_act: {selected_frames}')
    check_status = common_checks(object_mode=True, is_calculating=True,
                                 reload_geotracker=True, geotracker=True,
                                 camera=True, geometry=True, movie_clip=True)
    if not check_status.success:
        return check_status

    check_status = check_uv_overlapping()
    if not check_status.success:
        return check_status

    area = bpy.context.area
    prepare_camera(area)
    geotracker = get_current_geotracker_item()
    built_texture = bake_texture(geotracker, selected_frames)
    revert_camera(area)
    preview_material_with_texture(built_texture, geotracker.geomobj)
    if not check_status.success:
        return check_status
    return ActionStatus(True, 'ok')


def relative_to_camera_act() -> ActionStatus:
    _log.output('relative_to_camera_act call')
    check_status = common_checks(object_mode=True, is_calculating=True,
                                 reload_geotracker=True, geotracker=True,
                                 camera=True, geometry=True)
    if not check_status.success:
        return check_status

    geotracker = get_current_geotracker_item()
    geomobj = geotracker.geomobj
    camobj = geotracker.camobj

    gt = GTLoader.kt_geotracker()
    geom_animated_frames = get_object_keyframe_numbers(geomobj)
    cam_animated_frames = get_object_keyframe_numbers(camobj)
    all_animated_frames = list(set(geom_animated_frames).union(set(cam_animated_frames)))
    all_animated_frames.sort()
    if len(all_animated_frames) == 0:
        msg = 'No animation keys on both objects'
        _log.error(msg)
        return ActionStatus(False, msg)

    matrices = {x:gt.model_mat(x) for x in all_animated_frames}

    current_frame = bpy_current_frame()

    # Default camera position at (0, 0, 0) and +90 deg rotated on X
    scale = camobj.matrix_world.to_scale()
    cam_matrix = Matrix.LocRotScale(
        (0, 0, 0), Euler((math.radians(90), 0, 0), 'XYZ'), scale)

    bpy.context.window_manager.progress_begin(0, len(matrices))
    for i, frame in enumerate(matrices):
        bpy.context.window_manager.progress_update(i)
        _log.output(f'relative_to_camera_act frame:{frame}')
        bpy_set_current_frame(frame)
        _log.output(f'relative_to_camera_act before delete')
        delete_locrot_keyframe(camobj)
        _log.output(f'relative_to_camera_act after delete_locrot_keyframe')
        camobj.matrix_world = cam_matrix
        GTLoader.place_object_relative_to_camera(matrices[frame])
        _log.output(f'relative_to_camera_act place_object_relative_to_camera')
        update_depsgraph()
        _log.output(f'relative_to_camera_act update_depsgraph')
        create_locrot_keyframe(geomobj)

    bpy.context.window_manager.progress_end()

    bpy_set_current_frame(current_frame)
    geotracker.solve_for_camera = False
    _mark_object_keyframes(geomobj)
    return ActionStatus(True, 'ok')


def relative_to_geometry_act() -> ActionStatus:
    check_status = common_checks(object_mode=True, is_calculating=True,
                                 reload_geotracker=True, geotracker=True,
                                 camera=True, geometry=True)
    if not check_status.success:
        return check_status

    geotracker = get_current_geotracker_item()
    geomobj = geotracker.geomobj
    camobj = geotracker.camobj

    gt = GTLoader.kt_geotracker()
    geom_animated_frames = get_object_keyframe_numbers(geomobj)
    cam_animated_frames = get_object_keyframe_numbers(camobj)
    all_animated_frames = list(set(geom_animated_frames).union(set(cam_animated_frames)))
    all_animated_frames.sort()
    if len(all_animated_frames) == 0:
        msg = 'No animation keys on both objects'
        _log.error(msg)
        return ActionStatus(False, msg)

    matrices = {x:gt.model_mat(x) for x in all_animated_frames}

    current_frame = bpy_current_frame()

    # Object at (0, 0, 0) keeping its scale
    scale = geomobj.matrix_world.to_scale()
    geom_matrix = Matrix.LocRotScale((0, 0, 0), Euler((0, 0, 0), 'XYZ'), scale)

    bpy.context.window_manager.progress_begin(0, len(matrices))
    for i, frame in enumerate(matrices):
        bpy.context.window_manager.progress_update(i)
        _log.output(f'relative_to_geometry_act frame:{frame}')
        bpy_set_current_frame(frame)
        delete_locrot_keyframe(geomobj)
        geomobj.matrix_world = geom_matrix
        GTLoader.place_camera_relative_to_object(matrices[frame])
        update_depsgraph()
        create_animation_locrot_keyframe_force(camobj)

    bpy.context.window_manager.progress_end()

    bpy_set_current_frame(current_frame)
    geotracker.solve_for_camera = True
    _mark_object_keyframes(camobj)
    return ActionStatus(True, 'ok')


def geometry_repositioning_act() -> ActionStatus:
    check_status = common_checks(object_mode=True, is_calculating=True,
                                 reload_geotracker=True, geotracker=True,
                                 camera=True, geometry=True)
    if not check_status.success:
        return check_status

    geotracker = get_current_geotracker_item()

    geomobj = geotracker.geomobj
    camobj = geotracker.camobj
    new_geom_matrix = geomobj.matrix_world.copy()

    geom_animated_frames = get_object_keyframe_numbers(geomobj)
    if len(geom_animated_frames) == 0:
        msg = 'Geometry does not have any keyframes'
        _log.error(msg)
        return ActionStatus(False, msg)

    current_frame = reset_unsaved_animation_changes_in_frame()

    gt = GTLoader.kt_geotracker()

    cam_animated_frames = get_object_keyframe_numbers(camobj)
    cam_matrices = {x:gt.model_mat(x) for x in cam_animated_frames}

    transform_matrix = new_geom_matrix @ geomobj.matrix_world.inverted()

    old_gt_model_mat = geotracker.calc_model_matrix()
    geomobj.matrix_world = new_geom_matrix
    GTLoader.place_camera_relative_to_object(old_gt_model_mat)

    for frame in geom_animated_frames:
        bpy_set_current_frame(frame)
        geomobj.matrix_world = transform_matrix @ geomobj.matrix_world
        update_depsgraph()
        create_animation_locrot_keyframe_force(geomobj)

    for frame in cam_matrices:
        bpy_set_current_frame(frame)
        GTLoader.place_camera_relative_to_object(cam_matrices[frame])
        update_depsgraph()
        create_animation_locrot_keyframe_force(camobj)

    bpy_set_current_frame(current_frame)
    return ActionStatus(True, 'ok')


def camera_repositioning_act() -> ActionStatus:
    check_status = common_checks(object_mode=True, is_calculating=True,
                                 reload_geotracker=True, geotracker=True,
                                 camera=True, geometry=True)
    if not check_status.success:
        return check_status

    geotracker = get_current_geotracker_item()

    geomobj = geotracker.geomobj
    camobj = geotracker.camobj
    new_cam_matrix = camobj.matrix_world.copy()

    cam_animated_frames = get_object_keyframe_numbers(camobj)
    if len(cam_animated_frames) == 0:
        msg = 'Camera does not have any keyframes'
        _log.error(msg)
        return ActionStatus(False, msg)

    current_frame = reset_unsaved_animation_changes_in_frame()

    gt = GTLoader.kt_geotracker()

    geom_animated_frames = get_object_keyframe_numbers(camobj)
    geom_matrices = {x:gt.model_mat(x) for x in geom_animated_frames}

    transform_matrix = new_cam_matrix @ camobj.matrix_world.inverted()

    old_gt_model_mat = geotracker.calc_model_matrix()
    camobj.matrix_world = new_cam_matrix
    GTLoader.place_object_relative_to_camera(old_gt_model_mat)

    for frame in cam_animated_frames:
        bpy_set_current_frame(frame)
        camobj.matrix_world = transform_matrix @ camobj.matrix_world
        update_depsgraph()
        create_animation_locrot_keyframe_force(camobj)

    for frame in geom_matrices:
        bpy_set_current_frame(frame)
        GTLoader.place_object_relative_to_camera(geom_matrices[frame])
        update_depsgraph()
        create_animation_locrot_keyframe_force(geomobj)

    bpy_set_current_frame(current_frame)
    return ActionStatus(True, 'ok')


def move_tracking_to_camera_act() -> ActionStatus:
    check_status = common_checks(object_mode=True, is_calculating=True,
                                 reload_geotracker=True, geotracker=True,
                                 camera=True, geometry=True)
    if not check_status.success:
        return check_status

    geotracker = get_current_geotracker_item()

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

    gt = GTLoader.kt_geotracker()

    all_animated_frames = list(set(geom_animated_frames).union(set(cam_animated_frames)))
    all_animated_frames.sort()
    _log.output(f'ALL FRAMES: {all_animated_frames}')
    all_matrices = {x:gt.model_mat(x) for x in all_animated_frames}
    _log.output(f'ALL: {all_matrices.keys()}')

    for frame in all_matrices:
        bpy_set_current_frame(frame)
        delete_locrot_keyframe(geomobj)
        geomobj.matrix_world = geom_matrix
        GTLoader.place_camera_relative_to_object(all_matrices[frame])
        update_depsgraph()
        create_animation_locrot_keyframe_force(camobj)

    bpy_set_current_frame(current_frame)
    geotracker.solve_for_camera = True

    _mark_object_keyframes(camobj)
    return ActionStatus(True, 'ok')


def move_tracking_to_geometry_act() -> ActionStatus:
    check_status = common_checks(object_mode=True, is_calculating=True,
                                 reload_geotracker=True, geotracker=True,
                                 camera=True, geometry=True)
    if not check_status.success:
        return check_status

    geotracker = get_current_geotracker_item()

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

    gt = GTLoader.kt_geotracker()

    all_animated_frames = list(set(geom_animated_frames).union(set(cam_animated_frames)))
    all_animated_frames.sort()
    _log.output(f'ALL FRAMES: {all_animated_frames}')
    all_matrices = {x:gt.model_mat(x) for x in all_animated_frames}
    _log.output(f'ALL: {all_matrices.keys()}')

    for frame in all_matrices:
        bpy_set_current_frame(frame)
        delete_locrot_keyframe(camobj)
        camobj.matrix_world = cam_matrix
        GTLoader.place_object_relative_to_camera(all_matrices[frame])
        update_depsgraph()
        create_animation_locrot_keyframe_force(geomobj)

    bpy_set_current_frame(current_frame)
    geotracker.solve_for_camera = False

    _mark_object_keyframes(geomobj)
    return ActionStatus(True, 'ok')


def _mark_object_keyframes(obj: Object) -> None:
    gt = GTLoader.kt_geotracker()
    tracked_keyframes = [x for x in gt.track_frames()]
    _log.output(f'KEYFRAMES TO MARK AS TRACKED: {tracked_keyframes}')
    mark_selected_points_in_locrot(obj, tracked_keyframes, 'JITTER')
    keyframes = [x for x in gt.keyframes()]
    _log.output(f'KEYFRAMES TO MARK AS KEYFRAMES: {keyframes}')
    mark_selected_points_in_locrot(obj, keyframes, 'KEYFRAME')


def select_geotracker_objects_act(geotracker_num: int) -> ActionStatus:
    check_status = common_checks(object_mode=True, is_calculating=True,
                                 pinmode_out=True)
    if not check_status.success:
        return check_status

    settings = get_gt_settings()
    settings.fix_geotrackers()
    if not settings.change_current_geotracker_safe(geotracker_num):
        return ActionStatus(False, f'Cannot switch to Geotracker '
                                   f'{geotracker_num}')

    geotracker = get_current_geotracker_item()
    if not geotracker.geomobj and not geotracker.camobj:
        return ActionStatus(False, f'Geotracker {geotracker_num} '
                                   f'does not contain any objects')
    if geotracker.camera_mode():
        select_objects_only([geotracker.camobj, geotracker.geomobj])
    else:
        select_objects_only([geotracker.geomobj, geotracker.camobj])

    center_viewport(bpy.context.area)

    return ActionStatus(True, 'ok')


def render_with_background_act() -> ActionStatus:
    check_status = common_checks(object_mode=True, is_calculating=True,
                                 reload_geotracker=True, geotracker=True,
                                 camera=True, geometry=True)
    if not check_status.success:
        return check_status

    geotracker = get_current_geotracker_item()
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
    return ActionStatus(True, 'ok')


def revert_default_render_act() -> ActionStatus:
    check_status = common_checks(object_mode=True, is_calculating=True,
                                 reload_geotracker=True, geotracker=True,
                                 camera=True, geometry=True)
    if not check_status.success:
        return check_status

    geotracker = get_current_geotracker_item()
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
    return ActionStatus(True, 'ok')


_geom_mw: Matrix = Matrix.Identity(4)
_cam_mw: Matrix = Matrix.Identity(4)


def _get_geom_mw() -> Matrix:
    global _geom_mw
    return _geom_mw


def _get_cam_mw() -> Matrix:
    global _cam_mw
    return _cam_mw


def _set_geom_mw(value: Matrix) -> None:
    global _geom_mw
    _geom_mw = value


def _set_cam_mw(value: Matrix) -> None:
    global _cam_mw
    _cam_mw = value


def get_camobj_state(operator: Operator, camobj: Object) -> None:
    _set_cam_mw(camobj.matrix_world.copy())
    operator.cam_scale = camobj.scale


def get_geomobj_state(operator: Operator, geomobj: Object) -> None:
    _set_geom_mw(geomobj.matrix_world.copy())
    operator.geom_scale = geomobj.scale


def revert_object_states() -> bool:
    settings = get_gt_settings()
    geotracker = settings.get_current_geotracker_item()
    geomobj = geotracker.geomobj
    camobj = geotracker.camobj
    if not geomobj or not camobj:
        return False

    geomobj.matrix_world = _get_geom_mw().copy()
    camobj.matrix_world = _get_cam_mw().copy()
    return True


def _calc_resize_matrix(origin_matrix: Matrix, scale: float) -> Matrix:
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


def _get_operator_origin_matrix(operator: Operator) -> Matrix:
    geotracker = get_current_geotracker_item()
    origin_matrix = Matrix.Identity(4)
    if operator.origin_point == 'GEOMETRY':
        origin_matrix = geotracker.geomobj.matrix_world.copy()
    elif operator.origin_point == 'CAMERA':
        origin_matrix = geotracker.camobj.matrix_world.copy()
    elif operator.origin_point == '3D_CURSOR':
        origin_matrix = bpy_scene().cursor.matrix.copy()
    return origin_matrix


def resize_object(operator: Operator) -> None:
    geotracker = get_current_geotracker_item()

    origin_matrix = _get_operator_origin_matrix(operator)
    rescale_matrix = _calc_resize_matrix(origin_matrix, operator.value)
    geotracker.camobj.matrix_world = rescale_matrix @ \
                                     geotracker.camobj.matrix_world
    _apply_camobj_scale(geotracker.camobj, operator)
    geotracker.geomobj.matrix_world = rescale_matrix @ \
                                      geotracker.geomobj.matrix_world
    _apply_geomobj_scale(geotracker.geomobj, operator)


def scale_scene_tracking_act(operator: Operator) -> ActionStatus:
    check_status = common_checks(object_mode=True, is_calculating=True,
                                 reload_geotracker=True, geotracker=True,
                                 camera=True, geometry=True)
    if not check_status.success:
        return check_status

    settings = get_gt_settings()
    geotracker = settings.get_current_geotracker_item()
    geomobj = geotracker.geomobj
    camobj = geotracker.camobj
    current_frame = bpy_current_frame()

    geom_animated_frames = get_object_keyframe_numbers(geomobj)
    cam_animated_frames = get_object_keyframe_numbers(camobj)

    origin_matrix = _get_operator_origin_matrix(operator)
    rescale_matrix = _calc_resize_matrix(origin_matrix, operator.value)

    revert_object_states()

    for frame in cam_animated_frames:
        bpy_set_current_frame(frame)
        geotracker.camobj.matrix_world = rescale_matrix @ \
                                         geotracker.camobj.matrix_world
        _apply_camobj_scale(geotracker.camobj, operator)
        update_depsgraph()
        create_animation_locrot_keyframe_force(camobj)
        geotracker.camobj.scale = operator.cam_scale

    if len(cam_animated_frames) == 0:
        geotracker.camobj.matrix_world = rescale_matrix @ \
                                         geotracker.camobj.matrix_world

    for frame in geom_animated_frames:
        bpy_set_current_frame(frame)
        geotracker.geomobj.matrix_world = rescale_matrix @ \
                                          geotracker.geomobj.matrix_world
        _apply_geomobj_scale(geotracker.geomobj, operator)
        update_depsgraph()
        create_animation_locrot_keyframe_force(geomobj)
        geotracker.geomobj.scale = operator.geom_scale

    if len(geom_animated_frames) == 0:
        geotracker.geomobj.matrix_world = rescale_matrix @ \
                                          geotracker.geomobj.matrix_world

    _apply_camobj_scale(geotracker.camobj, operator)
    _apply_geomobj_scale(geotracker.geomobj, operator)
    bpy_set_current_frame(current_frame)

    GTLoader.save_geotracker()
    if not settings.reload_current_geotracker():
        msg = 'Cannot reload GeoTracker data'
        _log.error(msg)
        return ActionStatus(False, msg)

    if settings.pinmode:
        GTLoader.update_viewport_shaders(wireframe=False, geomobj_matrix=True,
                                         pins_and_residuals=True)
    return ActionStatus(True, 'ok')
