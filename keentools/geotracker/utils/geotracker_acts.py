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
import time
from typing import Optional, Any, Callable, List, Set

import bpy
from bpy.types import Object

from ...addon_config import Config, get_operator, ErrorType, ActionStatus
from ...geotracker_config import GTConfig, get_gt_settings, get_current_geotracker_item
from ..gtloader import GTLoader
from ..gt_class_loader import GTClassLoader
from ...utils.animation import (remove_fcurve_point,
                                remove_fcurve_from_object)
from ...utils.other import bpy_progress_begin, bpy_progress_end
from .tracking import (get_next_tracking_keyframe,
                       get_previous_tracking_keyframe)
from ...utils.bpy_common import (create_empty_object,
                                 bpy_current_frame,
                                 bpy_end_frame,
                                 bpy_set_current_frame)
from ...utils.animation import get_action
from ...blender_independent_packages.pykeentools_loader import module as pkt_module
from ...utils.timer import RepeatTimer
from ...utils.video import (fit_render_size,
                            fit_time_length)
from ...utils.html import split_long_string


_logger: Any = logging.getLogger(__name__)


def _log_output(message: str) -> None:
    global _logger
    _logger.debug(message)


def _log_error(message):
    global _logger
    _logger.error(message)


def find_object_in_selection(obj_type: str='MESH',
                             selection: Optional[List]=None) -> Optional[Object]:
    def _get_any_alone_object(obj_type: str) -> Optional[Object]:
        all_objects = [obj for obj in bpy.data.objects if obj.type == obj_type]
        return None if len(all_objects) != 1 else all_objects[0]

    context_obj = bpy.context.object if hasattr(bpy.context, 'object') else None
    if context_obj and context_obj.type == obj_type:
        return context_obj
    if selection is not None:
        objects = selection
    else:
        if hasattr(bpy.context, 'selected_objects'):
            objects = bpy.context.selected_objects
        else:
            objects = []
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
    geotracker = get_current_geotracker_item()
    if not geotracker:
        return ActionStatus(False, 'No geotracker')

    area = GTLoader.get_work_area()
    if not area:
        return ActionStatus(False, 'Working area does not exist')

    GTLoader.safe_keyframe_add(bpy_current_frame(), update=True)
    GTLoader.save_geotracker()
    return ActionStatus(True, 'Ok')


def remove_keyframe_act() -> ActionStatus:
    geotracker = get_current_geotracker_item()
    if not geotracker:
        return ActionStatus(False, 'No geotracker')

    area = GTLoader.get_work_area()
    if not area:
        return ActionStatus(False, 'Working area does not exist')

    gt = GTLoader.kt_geotracker()

    if not gt.is_key_at(bpy_current_frame()):
        return ActionStatus(False, 'No GeoTracker keyframe at this frame')

    gt.remove_keyframe(bpy_current_frame())
    GTLoader.save_geotracker()
    return ActionStatus(True, 'ok')


def next_keyframe_act() -> ActionStatus:
    current_frame = bpy_current_frame()
    target_frame = get_next_tracking_keyframe(GTLoader.kt_geotracker(),
                                              current_frame)
    if current_frame != target_frame:
        bpy_set_current_frame(target_frame)
        return ActionStatus(True, 'ok')
    return ActionStatus(False, 'No next GeoTracker keyframe')


def prev_keyframe_act() -> ActionStatus:
    current_frame = bpy_current_frame()
    target_frame = get_previous_tracking_keyframe(GTLoader.kt_geotracker(),
                                                  current_frame)
    if current_frame != target_frame:
        bpy_set_current_frame(target_frame)
        return ActionStatus(True, 'ok')
    return ActionStatus(False, 'No previous GeoTracker keyframe')


def fit_render_size_act() -> ActionStatus:
    geotracker = get_current_geotracker_item()
    if not geotracker:
        return ActionStatus(False, 'No geotracker')
    if not geotracker.movie_clip:
        return ActionStatus(False, 'No image sequence in GeoTracker')
    return fit_render_size(geotracker.movie_clip)


def fit_time_length_act() -> ActionStatus:
    geotracker = get_current_geotracker_item()
    if not geotracker:
        return ActionStatus(False, 'No geotracker')
    if not geotracker.movie_clip:
        return ActionStatus(False, 'No image sequence in GeoTracker')
    res = fit_time_length(geotracker.movie_clip)
    if res.success:
        geotracker.precalc_start = 1
        geotracker.precalc_end = bpy_end_frame()
    return res


class TrackTimer:
    def __init__(self, computation: Any, from_frame: int = -1):
        self._interval: float = 0.01
        self._target_frame: int = from_frame
        self._state: str = 'timeline'
        self._active_state_func: Callable = self.timeline_state
        self.tracking_computation = computation

    def timeline_state(self) -> Optional[float]:
        settings = get_gt_settings()
        if settings.user_interrupts or not settings.pinmode:
            self._cancel()

        if bpy_current_frame() == self._target_frame:
            self._state = 'computation'
            self._active_state_func = self.computation_state
            return self.computation_state()
        bpy_set_current_frame(self._target_frame)
        _log_output(f'timeline_state: set_current_frame({self._target_frame})')
        return self._interval

    def computation_state(self) -> Optional[float]:
        settings = get_gt_settings()
        if settings.user_interrupts or not settings.pinmode:
            self._cancel()

        current_frame = bpy_current_frame()
        _log_output(f'computation_state scene={current_frame} '
                    f'target={self._target_frame}')

        result = self._safe_resume()

        tracking_current_frame = self.tracking_computation.current_frame()
        _log_output(f'CURRENT FRAME: scene={current_frame} '
                    f'track={tracking_current_frame} result={result}')

        overall = self.tracking_computation.finished_and_total_frames()
        if not result or overall is None:
            self._output_statistics()
            self._state = 'finish'
            self._active_state_func = self.finish_computation
            return self.finish_computation()

        if result and tracking_current_frame != current_frame:
            self._target_frame = tracking_current_frame
            self._state = 'timeline'
            self._active_state_func = self.timeline_state
            bpy_set_current_frame(self._target_frame)
            return self._interval

        return self._interval

    def finish_computation(self) -> None:
        _log_output('finish_computation call')
        attempts = 0
        max_attempts = 3
        while attempts < max_attempts and not self.tracking_computation.is_finished():
            attempts += 1
            _log_output(f'TRY TO STOP COMPUTATION. ATTEMPT {attempts}')
            self.tracking_computation.cancel()
            self._safe_resume()
        if attempts >= max_attempts and not self.tracking_computation.is_finished():
            _log_error(f'PROBLEM WITH COMPUTATION STOP')
        GTLoader.revert_default_screen_message(unregister=False)
        self._stop_user_interrupt_operator()
        GTLoader.save_geotracker()
        settings = get_gt_settings()
        settings.tracking_mode = False
        return None

    def _start_user_interrupt_operator(self) -> None:
        op = get_operator(GTConfig.gt_interrupt_modal_idname)
        op('INVOKE_DEFAULT')

    def _stop_user_interrupt_operator(self) -> None:
        settings = get_gt_settings()
        settings.user_interrupts = True

    def _safe_resume(self) -> bool:
        try:
            if not self.tracking_computation.is_finished():
                self.tracking_computation.resume()
                overall = self.tracking_computation.finished_and_total_frames()
                if overall is None:
                    return False
                finished_frames, total_frames = overall
                GTLoader.message_to_screen(
                    [{'text': f'Tracking calculating: '
                              f'{finished_frames}/{total_frames}', 'y': 60,
                      'color': (1.0, 0.0, 0.0, 0.7)},
                     {'text': 'ESC to interrupt', 'y': 30,
                      'color': (1.0, 1.0, 1.0, 0.7)}])
                return True
        except pkt_module().ComputationException as err:
            msg = '_safe_resume ComputationException. ' + str(err)
            _log_error(msg)
            user_message = '\n'.join(split_long_string(str(err), limit=70))
            warn = get_operator(Config.kt_warning_idname)
            warn('INVOKE_DEFAULT', msg=ErrorType.CustomMessage,
                 msg_content=user_message)
        except Exception as err:
            msg = '_safe_resume Exception. ' + str(err)
            _log_error(msg)
        return False

    def _output_statistics(self) -> None:
        overall = self.tracking_computation.finished_and_total_frames()
        _log_output(f'Total calc frames: {overall}')
        gt = GTLoader.kt_geotracker()
        _log_output(f'KEYFRAMES: {gt.keyframes()}')
        _log_output(f'TRACKED FRAMES: {gt.track_frames()}')

    def _cancel(self) -> None:
        _log_output(f'Cancel call. State={self._state}')
        self.tracking_computation.cancel()

    def timer_func(self) -> Optional[float]:
        return self._active_state_func()

    def start(self) -> None:
        if not bpy.app.background:
            self._start_user_interrupt_operator()
        GTLoader.message_to_screen(
            [{'text': 'Tracking calculating... Please wait', 'y': 60,
              'color': (1.0, 0.0, 0.0, 0.7)},
             {'text': 'ESC to cancel', 'y': 30,
              'color': (1.0, 1.0, 1.0, 0.7)}])
        settings = get_gt_settings()
        settings.tracking_mode = True

        _func = self.timer_func
        if not bpy.app.background:
            bpy.app.timers.register(_func, first_interval=self._interval)
            res = bpy.app.timers.is_registered(_func)
            _log_output(f'tracking timer registered: {res}')
        else:
            # Testing purpose
            timer = RepeatTimer(self._interval, _func)
            timer.start()


def _minimal_checks() -> ActionStatus:
    settings = get_gt_settings()
    geotracker = settings.get_current_geotracker_item()

    if not geotracker:
        msg = 'GeoTracker item is not found'
        _log_error(msg)
        return ActionStatus(False, msg)

    if settings.calculation_mode():
        settings.user_interrupts = True
        msg = 'Calculation has been stopped by user'
        _log_error(msg)
        return ActionStatus(False, msg)

    return ActionStatus(True, 'ok')


def _track_checks() -> ActionStatus:
    settings = get_gt_settings()
    geotracker = settings.get_current_geotracker_item()
    if not settings.pinmode:
        msg = 'Tracking works only in Pin mode'
        _log_error(msg)
        return ActionStatus(False, msg)

    if not geotracker:
        msg = 'GeoTracker item is not found'
        _log_error(msg)
        return ActionStatus(False, msg)

    status, msg, precalc_info = geotracker.reload_precalc()
    if not status or precalc_info is None:
        msg = 'Precalc has problems. Check it'
        _log_error(msg)
        return ActionStatus(False, msg)

    if settings.calculation_mode():
        settings.user_interrupts = True
        msg = 'Calculation has been stopped by user'
        _log_error(msg)
        return ActionStatus(False, msg)
    return ActionStatus(True, 'ok')


def track_to(forward: bool) -> ActionStatus:
    check_status = _track_checks()
    if not check_status.success:
        return check_status

    geotracker = get_current_geotracker_item()

    gt = GTLoader.kt_geotracker()
    current_frame = bpy_current_frame()
    try:
        tracking_computation = gt.track_async(current_frame, forward,
                                              geotracker.precalc_path)
        tracking_timer = TrackTimer(tracking_computation, current_frame)
        tracking_timer.start()
    except pkt_module().UnlicensedException as err:
        _log_error(f'UnlicensedException refine_act: {str(err)}')
        warn = get_operator(Config.kt_warning_idname)
        warn('INVOKE_DEFAULT', msg=ErrorType.NoLicense)
        # Return True to prevent doubling dialogs
        return ActionStatus(True, 'Unlicensed error')
    except Exception as err:
        _log_error(f'Unknown Exception refine_act: {str(err)}')
        return ActionStatus(False, 'Some problem (see console)')

    return ActionStatus(True, 'Ok')


def track_next_frame_act(forward: bool=True) -> ActionStatus:
    check_status = _track_checks()
    if not check_status.success:
        return check_status

    geotracker = get_current_geotracker_item()
    gt = GTLoader.kt_geotracker()
    current_frame = bpy_current_frame()
    try:
        gt.track_frame(current_frame, forward=forward,
                       precalc_path=geotracker.precalc_path)
    except pkt_module().UnlicensedException as err:
        _log_error(f'UnlicensedException track_next_frame_act: {str(err)}')
        warn = get_operator(Config.kt_warning_idname)
        warn('INVOKE_DEFAULT', msg=ErrorType.NoLicense)
        # Return True to prevent doubling dialogs
        return ActionStatus(True, 'Unlicensed error')
    except Exception as err:
        msg = 'Track next frame problem (see console)'
        _log_error(msg)
        _log_error(str(err))
        return ActionStatus(False, msg)

    GTLoader.save_geotracker()
    current_frame += 1 if forward else -1
    bpy_set_current_frame(current_frame)

    return ActionStatus(True, 'Ok')


def refine_act() -> ActionStatus:
    check_status = _track_checks()
    if not check_status.success:
        return check_status

    settings = get_gt_settings()
    geotracker = settings.get_current_geotracker_item()
    gt = GTLoader.kt_geotracker()
    current_frame = bpy_current_frame()
    _log_output(f'REFINE AT: {current_frame}')

    progress_callback = GTClassLoader.RFProgressCallBack_class()()

    start_time = time.time()
    bpy_progress_begin(0, 100)
    settings.tracking_mode = True
    result = False
    try:
        result = gt.refine(current_frame, geotracker.precalc_path,
                           progress_callback)
    except pkt_module().UnlicensedException as err:
        _log_error(f'UnlicensedException refine_act: {str(err)}')
        warn = get_operator(Config.kt_warning_idname)
        warn('INVOKE_DEFAULT', msg=ErrorType.NoLicense)
        # Return True to prevent doubling dialogs
        return ActionStatus(True, 'Unlicensed error')
    except Exception as err:
        _log_error(f'Unknown Exception refine_act: {str(err)}')
    finally:
        settings.tracking_mode = False
        bpy_progress_end()
        overall_time = time.time() - start_time
        _log_output('Refine calculation time: {:.2f} sec'.format(overall_time))

    _log_output(f'Refined frames: {progress_callback.refined_frames}')
    GTLoader.save_geotracker()
    GTLoader.update_all_viewport_shaders()
    GTLoader.viewport_area_redraw()
    if not result:
        return ActionStatus(False, 'Some problem. See console for details')
    return ActionStatus(True, 'ok')


def refine_all_act() -> ActionStatus:
    check_status = _track_checks()
    if not check_status.success:
        return check_status

    settings = get_gt_settings()
    geotracker = settings.get_current_geotracker_item()
    gt = GTLoader.kt_geotracker()
    current_frame = bpy_current_frame()
    _log_output('REFINE AT: {}'.format(current_frame))

    progress_callback = GTClassLoader.RFProgressCallBack_class()()

    start_time = time.time()
    bpy_progress_begin(0, 100)
    settings.tracking_mode = True
    result = False
    try:
        result = gt.refine_all(geotracker.precalc_path, progress_callback)
    except pkt_module().UnlicensedException as err:
        _log_error(f'UnlicensedException refine_all_act: {str(err)}')
        warn = get_operator(Config.kt_warning_idname)
        warn('INVOKE_DEFAULT', msg=ErrorType.NoLicense)
        # Return True to prevent doubling dialogs
        return ActionStatus(True, 'Unlicensed error')
    except Exception as err:
        _log_error(f'Unknown Exception refine_all_act: {str(err)}')
    finally:
        settings.tracking_mode = False
        bpy_progress_end()
        overall_time = time.time() - start_time
        _log_output('Refine calculation time: {:.2f} sec'.format(overall_time))

    GTLoader.save_geotracker()
    GTLoader.update_all_viewport_shaders()
    GTLoader.viewport_area_redraw()
    if not result:
        return ActionStatus(False, 'Some problem. See console for details')
    return ActionStatus(True, 'ok')


def _active_frames(kt_geotracker: Any) -> Set:
    return set(kt_geotracker.track_frames() + kt_geotracker.keyframes())


def clear_between_keyframes_act() -> ActionStatus:
    check_status = _minimal_checks()
    if not check_status.success:
        return check_status

    current_frame = bpy_current_frame()
    gt = GTLoader.kt_geotracker()
    try:
        gt.remove_track_between_keyframes(current_frame)
    except Exception as err:
        _log_error(f'Unknown Exception clear_between_keyframes_act: {str(err)}')

    GTLoader.save_geotracker()
    GTLoader.update_all_viewport_shaders()
    GTLoader.viewport_area_redraw()
    return ActionStatus(True, 'ok')


def clear_direction_act(forward: bool) -> ActionStatus:
    check_status = _minimal_checks()
    if not check_status.success:
        return check_status

    current_frame = bpy_current_frame()
    gt = GTLoader.kt_geotracker()
    try:
        _log_output(f'clear_direction_act: {current_frame} {forward}')
        gt.remove_track_in_direction(current_frame, forward=forward)
    except Exception as err:
        _log_error(f'Unknown Exception clear_direction_act: {str(err)}')

    GTLoader.save_geotracker()
    GTLoader.update_all_viewport_shaders()
    GTLoader.viewport_area_redraw()
    return ActionStatus(True, 'ok')


def clear_all_act() -> ActionStatus:
    check_status = _minimal_checks()
    if not check_status.success:
        return check_status

    gt = GTLoader.kt_geotracker()
    try:
        gt.remove_all_track_data_and_keyframes()
    except Exception as err:
        _log_error(f'Unknown Exception clear_all_act: {str(err)}')

    GTLoader.save_geotracker()
    GTLoader.update_all_viewport_shaders()
    GTLoader.viewport_area_redraw()
    return ActionStatus(True, 'ok')


def remove_focal_keyframe_act() -> ActionStatus:
    geotracker = get_current_geotracker_item()
    if not geotracker:
        msg = 'GeoTracker item is not found'
        _log_error(msg)
        return ActionStatus(False, msg)

    if not geotracker.camobj:
        msg = 'GeoTracker camera is not found'
        _log_error(msg)
        return ActionStatus(False, msg)

    remove_fcurve_point(geotracker.camobj.data, bpy_current_frame(), 'lens')
    return ActionStatus(True, 'ok')


def remove_focal_keyframes_act() -> ActionStatus:
    geotracker = get_current_geotracker_item()
    if not geotracker:
        msg = 'GeoTracker item is not found'
        _log_error(msg)
        return ActionStatus(False, msg)

    if not geotracker.camobj:
        msg = 'GeoTracker camera is not found'
        _log_error(msg)
        return ActionStatus(False, msg)

    remove_fcurve_from_object(geotracker.camobj.data, 'lens')
    return ActionStatus(True, 'ok')


def remove_pins_act() -> ActionStatus:
    settings = get_gt_settings()
    if not settings.pinmode:
        msg = 'Remove pins can be called in PinMode only'
        _log_error(msg)
        return ActionStatus(False, msg)
    geotracker = settings.get_current_geotracker_item()
    if not geotracker:
        msg = 'GeoTracker item is not found'
        _log_error(msg)
        return ActionStatus(False, msg)

    gt = GTLoader.kt_geotracker()
    gt.remove_pins()

    pins = GTLoader.viewport().pins()
    pins.clear_disabled_pins()
    pins.clear_selected_pins()
    pins.reset_current_pin()

    GTLoader.update_all_viewport_shaders()
    GTLoader.viewport_area_redraw()
    return ActionStatus(True, 'ok')


def toggle_pins_act() -> ActionStatus:
    settings = get_gt_settings()
    if not settings.pinmode:
        msg = 'Remove pins can be called in PinMode only'
        _log_error(msg)
        return ActionStatus(False, msg)
    geotracker = settings.get_current_geotracker_item()
    if not geotracker:
        msg = 'GeoTracker item is not found'
        _log_error(msg)
        return ActionStatus(False, msg)

    gt = GTLoader.kt_geotracker()
    keyframe = bpy_current_frame()
    if gt.pins_count() > 0:
        GTLoader.safe_keyframe_add(keyframe, update=True)
        gt.toggle_pins(keyframe)

    GTLoader.update_all_viewport_shaders()
    GTLoader.viewport_area_redraw()
    return ActionStatus(True, 'ok')


def center_geo_act() -> ActionStatus:
    settings = get_gt_settings()
    if not settings.pinmode:
        msg = 'Center geo can be called in PinMode only'
        _log_error(msg)
        return ActionStatus(False, msg)
    geotracker = settings.get_current_geotracker_item()
    if not geotracker:
        msg = 'GeoTracker item is not found'
        _log_error(msg)
        return ActionStatus(False, msg)

    GTLoader.center_geo()
    GTLoader.update_all_viewport_shaders()
    GTLoader.viewport_area_redraw()
    return ActionStatus(True, 'ok')


def create_animated_empty_act() -> ActionStatus:
    geotracker = get_current_geotracker_item()
    if not geotracker:
        msg = 'GeoTracker item is not found'
        _log_error(msg)
        return ActionStatus(False, msg)

    action = get_action(geotracker.animatable_object())
    if not action:
        msg = 'Animation is not created on source object'
        _log_error(msg)
        return ActionStatus(False, msg)

    obj = create_empty_object('GTEmpty')
    anim_data = obj.animation_data_create()
    anim_data.action = action
    return ActionStatus(True, 'ok')
