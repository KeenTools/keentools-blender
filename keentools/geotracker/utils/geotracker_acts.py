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

import logging
from dataclasses import dataclass
from typing import Optional

import bpy
from bpy.types import Object

from ...geotracker_config import GTConfig, get_gt_settings
from ..gtloader import GTLoader
from ..gt_class_loader import GTClassLoader
from ...utils.animation import (create_locrot_keyframe,
                                delete_locrot_keyframe,
                                insert_keyframe_in_fcurve,
                                extend_scene_timeline_start,
                                extend_scene_timeline_end,
                                reset_object_action)
from ...utils.other import bpy_progress_begin, bpy_progress_end
from .tracking import (PreviewTimer,
                       get_next_tracking_keyframe,
                       get_previous_tracking_keyframe)
from ...utils.coords import update_depsgraph


@dataclass(frozen=True)
class ActionStatus:
    success: bool = False
    error_message: str = None


def find_object_in_selection(obj_type: str='MESH',
                             selection: Optional[list]=None) -> Optional[Object]:
    def _get_any_alone_object(obj_type: str) -> Optional[Object]:
        all_objects = [obj for obj in bpy.data.objects if obj.type == obj_type]
        return None if len(all_objects) != 1 else all_objects[0]

    context_obj = bpy.context.object
    if context_obj and context_obj.type == obj_type:
        return context_obj
    objects = bpy.context.selected_objects if selection is None else selection
    selected_objects = [obj for obj in objects if obj.type == obj_type]
    if len(selected_objects) == 1:
        return selected_objects[0]
    return None if selection is not None else _get_any_alone_object(obj_type)


def create_geotracker_act() -> int:
    settings = get_gt_settings()
    num = settings.add_geotracker_item()
    settings.current_geotracker_num = num
    GTLoader.new_kt_geotracker()
    geotracker = settings.get_current_geotracker_item()
    obj = find_object_in_selection('MESH')
    if obj is not None:
        geotracker.geomobj = obj
    camobj = find_object_in_selection('CAMERA')
    if camobj is not None:
        geotracker.camobj = camobj
    else:
        camobj = bpy.context.scene.camera
        if camobj:
            geotracker.camobj = camobj
    return num


def delete_geotracker_act(geotracker_num: int) -> int:
    settings = get_gt_settings()
    num = settings.remove_geotracker_item(geotracker_num)
    settings.change_current_geotracker(num)
    return num


def add_keyframe_act() -> ActionStatus:
    logger = logging.getLogger(__name__)
    settings = get_gt_settings()
    geotracker = settings.get_current_geotracker_item()
    if not geotracker:
        return ActionStatus(False, 'No geotracker')

    area = GTLoader.get_work_area()
    if not area:
        return ActionStatus(False, 'Working area does not exist')

    GTLoader.safe_keyframe_add(settings.current_frame(),
                               GTLoader.calc_model_matrix())
    GTLoader.save_geotracker()
    create_locrot_keyframe(geotracker.animatable_object(), 'KEYFRAME')
    logger.debug('KEYFRAME ADDED')

    GTLoader.update_all_viewport_shaders()
    area.tag_redraw()
    return ActionStatus(True, 'Ok')


def remove_keyframe_act() -> ActionStatus:
    settings = get_gt_settings()
    geotracker = settings.get_current_geotracker_item()
    if not geotracker:
        return ActionStatus(False, 'No geotracker')

    area = GTLoader.get_work_area()
    if not area:
        return ActionStatus(False, 'Working area does not exist')

    gt = GTLoader.kt_geotracker()

    if not gt.is_key_at(settings.current_frame()):
        return ActionStatus(False, 'No GeoTracker keyframe at this frame')

    gt.remove_keyframe(settings.current_frame())
    settings.pin_move_mode = True
    delete_locrot_keyframe(geotracker.animatable_object())
    reset_object_action(geotracker.animatable_object())
    update_depsgraph()
    GTLoader.store_geomobj_world_matrix(-1, geotracker.geomobj.matrix_world)
    settings.pin_move_mode = False
    GTLoader.save_geotracker()
    GTLoader.update_all_viewport_shaders(area)
    return ActionStatus(True, 'ok')


def next_keyframe_act() -> ActionStatus:
    settings = get_gt_settings()
    current_frame = settings.current_frame()
    target_frame = get_next_tracking_keyframe(GTLoader.kt_geotracker(),
                                              current_frame)
    if current_frame != target_frame:
        settings.set_current_frame(target_frame)
        return ActionStatus(True, 'ok')
    return ActionStatus(False, 'No next GeoTracker keyframe')


def prev_keyframe_act() -> ActionStatus:
    settings = get_gt_settings()
    current_frame = settings.current_frame()
    target_frame = get_previous_tracking_keyframe(GTLoader.kt_geotracker(),
                                                  current_frame)
    if current_frame != target_frame:
        settings.set_current_frame(target_frame)
        return ActionStatus(True, 'ok')
    return ActionStatus(False, 'No previous GeoTracker keyframe')


def fit_render_size_act() -> ActionStatus:
    logger = logging.getLogger(__name__)
    log_error = logger.error
    settings = get_gt_settings()
    geotracker = settings.get_current_geotracker_item()
    if not geotracker:
        return ActionStatus(False, 'No geotracker')
    if not geotracker.movie_clip:
        return ActionStatus(False, 'No image sequence in GeoTracker')

    w, h = geotracker.get_movie_clip_size()
    if w <= 0 or h <= 0:
        msg = f'Wrong precalc frame size {w} x {h}'
        log_error(msg)
        return ActionStatus(False, msg)

    scene = bpy.context.scene
    scene.render.resolution_x = w
    scene.render.resolution_y = h
    return ActionStatus(True, f'Render size {w} x {h}')


def fit_time_length_act() -> ActionStatus:
    settings = get_gt_settings()
    geotracker = settings.get_current_geotracker_item()
    if not geotracker:
        return ActionStatus(False, 'No geotracker')
    if not geotracker.movie_clip:
        return ActionStatus(False, 'No image sequence in GeoTracker')

    duration = geotracker.get_movie_clip_duration()
    if duration < 2:
        return ActionStatus(False, f'Image sequence too short: {duration}!')

    extend_scene_timeline_start(1)
    extend_scene_timeline_end(duration, force=True)
    geotracker.precalc_start = 1
    geotracker.precalc_end = duration

    return ActionStatus(True, f'Timeline duration 1 - {duration}')


def track_to(forward: bool=True) -> ActionStatus:
    logger = logging.getLogger(__name__)
    log_output = logger.debug
    log_error = logger.error
    settings = get_gt_settings()
    geotracker = settings.get_current_geotracker_item()
    if not geotracker:
        msg = 'GeoTracker item is not found'
        log_error(msg)
        return ActionStatus(False, msg)

    status, msg, precalc_info = geotracker.reload_precalc()
    if not status or precalc_info is None:
        msg = 'Precalc has problems. Check it'
        log_error(msg)
        return ActionStatus(False, msg)

    gt = GTLoader.kt_geotracker()
    old_focal_mode = gt.focal_length_mode()
    if geotracker.track_focal_length:
        gt.set_focal_length_mode(
            GTClassLoader.GeoTracker_class().FocalLengthMode.ZOOM_FOCAL_LENGTH)
        gt.set_track_focal_length(geotracker.track_focal_length)

    settings.pin_move_mode = True

    left = precalc_info.left_precalculated_frame
    right = precalc_info.right_precalculated_frame
    if forward:
        right -= 1
    else:
        left += 1
    progress_callback = GTClassLoader.TRProgressCallBack_class()(left, right)

    current_frame = settings.current_frame()
    track_error = False
    bpy_progress_begin(0, 100)
    try:
        gt.track(current_frame, forward=forward,
                 precalc_path=geotracker.precalc_path,
                 progress_callback=progress_callback)
    except RuntimeError as err:
        track_error = True
        track_error_message = str(err)
        log_error(f'gt.track error: {track_error_message}')
    bpy_progress_end()

    end_frame = progress_callback.last_progress
    if end_frame != -1:
        create_animation_range(current_frame, end_frame,
                               geotracker.track_focal_length)

    if track_error:
        gt.set_focal_length_mode(old_focal_mode)
        GTLoader.save_geotracker()
        return ActionStatus(False, track_error_message)

    if end_frame == -1:
        msg = 'No progress in tracking'
        log_error(msg)
        gt.set_focal_length_mode(old_focal_mode)
        GTLoader.save_geotracker()
        return ActionStatus(False, msg)

    settings.pin_move_mode = False
    gt.set_focal_length_mode(old_focal_mode)
    GTLoader.save_geotracker()

    pt = PreviewTimer(current_frame, end_frame)
    pt.start()
    return ActionStatus(True, 'Ok')


def create_animation_range(from_frame: int, to_frame: int,
                           animate_focal: bool=False) -> None:
    logger = logging.getLogger(__name__)
    settings = get_gt_settings()
    geotracker = settings.get_current_geotracker_item()
    if not geotracker:
        return

    gt = GTLoader.kt_geotracker()
    track_frames = gt.track_frames()
    keyframes = gt.keyframes()

    scope = range(from_frame, to_frame + 1) if from_frame < to_frame else \
        range(from_frame, to_frame - 1, -1)
    for frame in scope:
        settings.set_current_frame(frame)
        if frame in track_frames:
            GTLoader.place_camera(forced=True)
            keyframe_type = 'JITTER' if frame not in keyframes else 'KEYFRAME'
            create_locrot_keyframe(geotracker.animatable_object(), keyframe_type)

            if animate_focal:
                focal = GTLoader.updated_focal_length(force=True)
                logger.debug('ANIMATED FOCAL: {}'.format(focal))
                if focal is not None:
                    camobj = geotracker.camobj
                    insert_keyframe_in_fcurve(camobj.data, frame, focal,
                                              keyframe_type=keyframe_type,
                                              data_path='lens', index=0)
