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
from typing import Optional, Any, Callable

import bpy
from bpy.types import Object

from ...addon_config import get_operator
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
from .tracking import (get_next_tracking_keyframe,
                       get_previous_tracking_keyframe)
from ...utils.coords import update_depsgraph
from ...blender_independent_packages.pykeentools_loader import module as pkt_module


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
    delete_locrot_keyframe(geotracker.animatable_object())
    reset_object_action(geotracker.animatable_object())
    update_depsgraph()
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


class TrackTimer:
    _is_working: bool = False

    @classmethod
    def is_working(cls, value: Optional[bool]=None):
        if value is not None:
            cls._is_working = value
        return cls._is_working

    def __init__(self, computation: Any, from_frame: int = -1):
        self._interval: float = 0.01
        self._target_frame: int = from_frame
        self._state: str = 'timeline'
        self._active_state_func: Callable = self.timeline_state
        self._needs_keyframe = False
        self.tracking_computation = computation

    def timeline_state(self) -> Optional[float]:
        logger = logging.getLogger(__name__)
        log_output = logger.info
        settings = get_gt_settings()
        if settings.user_interrupts or not settings.pinmode:
            self._cancel()

        if settings.current_frame() == self._target_frame:
            self._state = 'computation'
            self._active_state_func = self.computation_state
            return self.computation_state()
        settings.set_current_frame(self._target_frame)
        log_output(f'timeline_state: set_current_frame({self._target_frame})')
        return self._interval

    def computation_state(self) -> Optional[float]:
        logger = logging.getLogger(__name__)
        log_error = logger.error
        log_output = logger.info
        settings = get_gt_settings()
        if settings.user_interrupts or not settings.pinmode:
            self._cancel()

        current_frame = settings.current_frame()
        log_output(f'computation_state scene={current_frame} '
                   f'target={self._target_frame}')

        result = self._safe_resume()

        tracking_current_frame = self.tracking_computation.current_frame()
        log_output(f'CURRENT FRAME: scene={current_frame} '
                   f'track={tracking_current_frame} result={result}')
        if self._needs_keyframe or current_frame == tracking_current_frame:
            self._create_keyframe(current_frame)
            GTLoader.update_viewport_wireframe()  # TODO: Look for better performance

        self._needs_keyframe = False
        if result and tracking_current_frame != current_frame:
            self._target_frame = tracking_current_frame
            self._needs_keyframe = True
            self._state = 'timeline'
            self._active_state_func = self.timeline_state
            settings.set_current_frame(self._target_frame)
            return self._interval

        if not result:
            self._output_statistics()
            self._state = 'finish'
            self._active_state_func = self.finish_computation
            return self.finish_computation()
        return self._interval

    def finish_computation(self) -> None:
        logger = logging.getLogger(__name__)
        log_output = logger.info
        log_error = logger.error
        attempts = 0
        max_attempts = 3
        while attempts < max_attempts and not self.tracking_computation.is_finished():
            attempts += 1
            log_output(f'TRY TO STOP COMPUTATION. ATTEMPT {attempts}')
            self.tracking_computation.cancel()
            self._safe_resume()
        if attempts == max_attempts and not self.tracking_computation.is_finished():
            log_error(f'PROBLEM WITH COMPUTATION STOP')
        GTLoader.revert_default_screen_message(unregister=False)
        self._stop_user_interrupt_operator()
        GTLoader.save_geotracker()
        self.is_working(False)
        return None

    def _start_user_interrupt_operator(self) -> None:
        op = get_operator(GTConfig.gt_interrupt_modal_idname)
        op('INVOKE_DEFAULT')

    def _stop_user_interrupt_operator(self) -> None:
        settings = get_gt_settings()
        settings.user_interrupts = True

    def _create_keyframe(self, current_frame: int) -> None:
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()
        create_animation_range(current_frame, current_frame,
                               geotracker.track_focal_length)

    def _safe_resume(self) -> bool:
        logger = logging.getLogger(__name__)
        log_error = logger.error
        try:
            if not self.tracking_computation.is_finished():
                self.tracking_computation.resume()
                total_frames = self.tracking_computation.total_frames()
                finished_frames = self.tracking_computation.finished_frames()
                GTLoader.message_to_screen(
                    [{'text': f'Tracking calculating: '
                              f'{finished_frames}/{total_frames}', 'y': 60,
                      'color': (1.0, 0.0, 0.0, 0.7)},
                     {'text': 'ESC to interrupt', 'y': 30,
                      'color': (1.0, 1.0, 1.0, 0.7)}])
                return True
        except pkt_module().ComputationException as err:
            msg = '_safe_resume ComputationException. ' + str(err)
            log_error(msg)
        except Exception as err:
            msg = '_safe_resume Exception. ' + str(err)
            log_error(msg)
        return False

    def _output_statistics(self) -> None:
        logger = logging.getLogger(__name__)
        log_output = logger.info
        log_output(f'Total calc frames: {self.tracking_computation.total_frames()}')
        gt = GTLoader.kt_geotracker()
        log_output(f'KEYFRAMES: {gt.keyframes()}')
        log_output(f'TRACKED FRAMES: {gt.track_frames()}')

    def _cancel(self) -> None:
        logger = logging.getLogger(__name__)
        log_output = logger.info
        log_output(f'Cancel call. State={self._state}')
        self.tracking_computation.cancel()

    def timer_func(self) -> Optional[float]:
        return self._active_state_func()

    def start(self) -> None:
        self._start_user_interrupt_operator()
        GTLoader.message_to_screen(
            [{'text': 'Tracking calculating... Please wait', 'y': 60,
              'color': (1.0, 0.0, 0.0, 0.7)},
             {'text': 'ESC to cancel', 'y': 30,
              'color': (1.0, 1.0, 1.0, 0.7)}])
        self.is_working(True)
        bpy.app.timers.register(self.timer_func, first_interval=self._interval)


def track_to(forward: bool=True) -> ActionStatus:
    logger = logging.getLogger(__name__)
    log_output = logger.info
    log_error = logger.error
    settings = get_gt_settings()
    geotracker = settings.get_current_geotracker_item()
    if not settings.pinmode:
        msg = 'Tracking works only in Pin mode'
        log_error(msg)
        return ActionStatus(False, msg)

    if not geotracker:
        msg = 'GeoTracker item is not found'
        log_error(msg)
        return ActionStatus(False, msg)

    status, msg, precalc_info = geotracker.reload_precalc()
    if not status or precalc_info is None:
        msg = 'Precalc has problems. Check it'
        log_error(msg)
        return ActionStatus(False, msg)

    if TrackTimer.is_working():
        settings.user_interrupts = True
        msg = 'Tracking has been stopped by user'
        log_error(msg)
        return ActionStatus(False, msg)

    gt = GTLoader.kt_geotracker()
    old_focal_mode = gt.focal_length_mode()
    if geotracker.track_focal_length:
        gt.set_focal_length_mode(
            GTClassLoader.GeoTracker_class().FocalLengthMode.ZOOM_FOCAL_LENGTH)
        gt.set_track_focal_length(geotracker.track_focal_length)

    current_frame = settings.current_frame()
    tracking_computation = gt.track_async(current_frame, forward,
                                          geotracker.precalc_path)
    tracking_timer = TrackTimer(tracking_computation, current_frame)
    tracking_timer.start()

    gt.set_focal_length_mode(old_focal_mode)  # TODO: Check it for TrackTimer
    return ActionStatus(True, 'Ok')


def create_animation_range(from_frame: int, to_frame: int,
                           animate_focal: bool=False) -> None:
    logger = logging.getLogger(__name__)
    log_output = logger.debug
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
                log_output('ANIMATED FOCAL: {}'.format(focal))
                if focal is not None:
                    camobj = geotracker.camobj
                    insert_keyframe_in_fcurve(camobj.data, frame, focal,
                                              keyframe_type=keyframe_type,
                                              data_path='lens', index=0)
