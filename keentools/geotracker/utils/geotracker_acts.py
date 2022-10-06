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

import time
from typing import Optional, Any, Callable, List, Set

import bpy
from bpy.types import Object

from ...utils.kt_logging import KTLogger
from ...addon_config import Config, get_operator, ErrorType, ActionStatus
from ...geotracker_config import GTConfig, get_gt_settings, get_current_geotracker_item
from ..gtloader import GTLoader
from ..gt_class_loader import GTClassLoader
from ...utils.animation import (remove_fcurve_point,
                                remove_fcurve_from_object,
                                delete_locrot_keyframe,
                                mark_all_points_in_locrot,
                                mark_selected_points_in_locrot)
from ...utils.other import bpy_progress_begin, bpy_progress_end
from .tracking import (get_next_tracking_keyframe,
                       get_previous_tracking_keyframe)
from ...utils.bpy_common import (create_empty_object,
                                 bpy_current_frame,
                                 bpy_end_frame,
                                 bpy_set_current_frame)
from ...utils.animation import (get_action,
                                get_object_keyframe_numbers,
                                create_animation_locrot_keyframe_force)
from ...blender_independent_packages.pykeentools_loader import module as pkt_module
from ...utils.timer import RepeatTimer
from ...utils.video import (fit_render_size,
                            fit_time_length)
from ...utils.html import split_long_string
from ...utils.coords import (calc_bpy_model_mat_relative_to_camera,
                             update_depsgraph,
                             xy_to_xz_rotation_matrix_4x4)
from .textures import bake_texture, preview_material_with_texture


_log = KTLogger(__name__)


def show_warning_dialog(err: Any, limit=70) -> None:
    _log.output('show_warning_dialog call')
    user_message = '\n'.join(split_long_string(str(err), limit=limit))
    warn = get_operator(Config.kt_warning_idname)
    warn('INVOKE_DEFAULT', msg=ErrorType.CustomMessage,
         msg_content=user_message)


def show_unlicensed_warning():
    _log.output('show_unlicensed_warning call')
    warn = get_operator(Config.kt_warning_idname)
    warn('INVOKE_DEFAULT', msg=ErrorType.NoLicense)


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


def common_checks(*, pinmode: bool=False,
                  pinmode_out: bool=False,
                  is_calculating: bool=False,
                  reload_geotracker: bool = False,
                  geotracker: bool=False,
                  camera: bool=False,
                  geometry: bool=False,
                  movie_clip: bool=False) -> ActionStatus:
    settings = get_gt_settings()
    if is_calculating and settings.is_calculating():
        msg = 'Calculation is performing'
        _log.error(msg)
        return ActionStatus(False, msg)
    if pinmode and not settings.pinmode:
        msg = 'This operation works only in Pin mode'
        _log.error(msg)
        return ActionStatus(False, msg)
    if pinmode_out and settings.pinmode:
        msg = 'This operation does not work in Pin mode'
        _log.error(msg)
        return ActionStatus(False, msg)

    if reload_geotracker:
        if not settings.reload_current_geotracker():
            msg = 'Cannot load GeoTracker data'
            _log.error(msg)
            return ActionStatus(False, msg)
    geotracker_item = get_current_geotracker_item()
    if geotracker and not geotracker_item:
        msg = 'GeoTracker item is not found'
        _log.error(msg)
        return ActionStatus(False, msg)
    if camera and not geotracker_item.camobj:
        msg = 'GeoTracker camera is not found'
        _log.error(msg)
        return ActionStatus(False, msg)
    if geometry and not geotracker_item.geomobj:
        msg = 'GeoTracker geometry is not found'
        _log.error(msg)
        return ActionStatus(False, msg)
    if movie_clip and not geotracker_item.movie_clip:
        msg = 'GeoTracker movie clip is not found'
        _log.error(msg)
        return ActionStatus(False, msg)
    return ActionStatus(True, 'Checks have been passed')


def create_geotracker_act() -> ActionStatus:
    check_status = common_checks(pinmode_out=True, is_calculating=True)
    if not check_status.success:
        return check_status

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
    settings.reload_current_geotracker()
    return ActionStatus(True, 'GeoTracker has been added')


def delete_geotracker_act(geotracker_num: int) -> ActionStatus:
    check_status = common_checks(pinmode_out=True, is_calculating=True)
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
    check_status = common_checks(pinmode=True, is_calculating=True,
                                 reload_geotracker=True,
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
    check_status = common_checks(pinmode=True, is_calculating=True,
                                 reload_geotracker=True,
                                 geotracker=True, camera=True, geometry=True)
    if not check_status.success:
        return check_status

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
    check_status = common_checks(is_calculating=True, reload_geotracker=True,
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
    check_status = common_checks(is_calculating=True, reload_geotracker=True,
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


class _CommonTimer:
    def __init__(self, computation: Any, from_frame: int = -1,
                 revert_current_frame: bool=False):
        self._interval: float = 0.001
        self._target_frame: int = from_frame
        self._state: str = 'timeline'
        self._active_state_func: Callable = self.timeline_state
        self.tracking_computation: Any = computation
        self._operation_name: str = 'common operation'
        self._calc_mode: str = 'NONE'
        self._overall_func: Callable = lambda: None
        self._start_frame: int = from_frame
        self._revert_current_frame: bool = revert_current_frame

    def timeline_state(self) -> Optional[float]:
        settings = get_gt_settings()
        if settings.user_interrupts or not settings.pinmode:
            self._cancel()

        if bpy_current_frame() == self._target_frame:
            self._state = 'computation'
            self._active_state_func = self.computation_state
            return self.computation_state()
        bpy_set_current_frame(self._target_frame)
        _log.output(f'{self._operation_name} timeline_state: '
                    f'set_current_frame({self._target_frame})')
        return self._interval

    def computation_state(self) -> Optional[float]:
        settings = get_gt_settings()
        if settings.user_interrupts or not settings.pinmode:
            self._cancel()

        current_frame = bpy_current_frame()
        _log.output(f'{self._operation_name} computation_state '
                    f'scene={current_frame} target={self._target_frame}')

        result = self._safe_resume()

        tracking_current_frame = self.tracking_computation.current_frame()
        _log.output(f'{self._operation_name} '
                    f'CURRENT FRAME: scene={current_frame} '
                    f'track={tracking_current_frame} result={result}')

        overall = self._overall_func()
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
        _log.output(f'{self._operation_name} finish_computation call')
        attempts = 0
        max_attempts = 3
        while attempts < max_attempts and not self.tracking_computation.is_finished():
            attempts += 1
            _log.output(f'TRY TO STOP COMPUTATION. ATTEMPT {attempts}')
            self.tracking_computation.cancel()
            self._safe_resume()
        if attempts >= max_attempts and not self.tracking_computation.is_finished():
            _log.error(f'PROBLEM WITH COMPUTATION STOP')
        GTLoader.revert_default_screen_message(unregister=False)
        self._stop_user_interrupt_operator()
        GTLoader.save_geotracker()
        settings = get_gt_settings()
        settings.stop_calculating()
        if self._revert_current_frame:
            bpy_set_current_frame(self._start_frame)
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
                overall = self._overall_func()
                if overall is None:
                    return False
                finished_frames, total_frames = overall
                GTLoader.message_to_screen(
                    [{'text': f'{self._operation_name} calculating: '
                              f'{finished_frames}/{total_frames}', 'y': 60,
                      'color': (1.0, 0.0, 0.0, 0.7)},
                     {'text': 'ESC to interrupt', 'y': 30,
                      'color': (1.0, 1.0, 1.0, 0.7)}])
                settings = get_gt_settings()
                total = total_frames if total_frames != 0 else 1
                settings.user_percent = 100 * finished_frames / total
                return True
        except pkt_module().ComputationException as err:
            msg = f'{self._operation_name} _safe_resume ' \
                  f'ComputationException.\n{str(err)}'
            _log.error(msg)
            show_warning_dialog(err)
        except Exception as err:
            msg = f'{self._operation_name} _safe_resume Exception. {str(err)}'
            _log.error(msg)
            show_warning_dialog(err)
        return False

    def _output_statistics(self) -> None:
        overall = self._overall_func()
        _log.output(f'--- {self._operation_name} statistics ---')
        _log.output(f'Total calc frames: {overall}')
        gt = GTLoader.kt_geotracker()
        _log.output(f'KEYFRAMES: {gt.keyframes()}')
        _log.output(f'TRACKED FRAMES: {gt.track_frames()}\n')

    def _cancel(self) -> None:
        _log.output(f'{self._operation_name} Cancel call. State={self._state}')
        self.tracking_computation.cancel()

    def timer_func(self) -> Optional[float]:
        return self._active_state_func()

    def start(self) -> None:
        if not bpy.app.background:
            self._start_user_interrupt_operator()
        GTLoader.message_to_screen(
            [{'text': f'{self._operation_name} calculating... Please wait', 'y': 60,
              'color': (1.0, 0.0, 0.0, 0.7)},
             {'text': 'ESC to cancel', 'y': 30,
              'color': (1.0, 1.0, 1.0, 0.7)}])
        settings = get_gt_settings()
        settings.calculating_mode = self._calc_mode

        _func = self.timer_func
        if not bpy.app.background:
            bpy.app.timers.register(_func, first_interval=self._interval)
            res = bpy.app.timers.is_registered(_func)
            _log.output(f'{self._operation_name} timer registered: {res}')
        else:
            # Testing purpose
            timer = RepeatTimer(self._interval, _func)
            timer.start()


class TrackTimer(_CommonTimer):
    def __init__(self, computation: Any, from_frame: int = -1):
        super().__init__(computation, from_frame)
        self._operation_name = 'Tracking'
        self._calc_mode = 'TRACKING'
        self._overall_func = computation.finished_and_total_frames


class RefineTimer(_CommonTimer):
    def __init__(self, computation: Any, from_frame: int = -1):
        super().__init__(computation, from_frame, revert_current_frame=True)
        self._operation_name = 'Refine'
        self._calc_mode = 'REFINE'
        self._overall_func = computation.finished_and_total_stage_frames


def _track_checks() -> ActionStatus:
    check_status = common_checks(pinmode=True, is_calculating=True,
                                 reload_geotracker=True, geotracker=True,
                                 camera=True, geometry=True)
    if not check_status.success:
        return check_status

    settings = get_gt_settings()
    geotracker = settings.get_current_geotracker_item()

    if not geotracker.precalcless:
        status, msg, precalc_info = geotracker.reload_precalc()
        if not status or precalc_info is None:
            msg = 'Precalc has problems. Check it'
            _log.error(msg)
            return ActionStatus(False, msg)
    else:
        check_status = common_checks(movie_clip=True)
        if not check_status.success:
            return check_status

    return ActionStatus(True, 'ok')


def track_to(forward: bool) -> ActionStatus:
    check_status = _track_checks()
    if not check_status.success:
        return check_status

    geotracker = get_current_geotracker_item()

    gt = GTLoader.kt_geotracker()
    current_frame = bpy_current_frame()
    try:
        precalc_path = None if geotracker.precalcless else geotracker.precalc_path
        tracking_computation = gt.track_async(current_frame, forward, precalc_path)
        tracking_timer = TrackTimer(tracking_computation, current_frame)
        tracking_timer.start()
    except pkt_module().UnlicensedException as err:
        _log.error(f'UnlicensedException refine_act: {str(err)}')
        show_unlicensed_warning()
        # Return True to prevent doubling dialogs
        return ActionStatus(True, 'Unlicensed error')
    except Exception as err:
        _log.error(f'Unknown Exception refine_act: {str(err)}')
        show_warning_dialog(err)
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
    check_status = _track_checks()
    if not check_status.success:
        return check_status

    geotracker = get_current_geotracker_item()

    gt = GTLoader.kt_geotracker()
    current_frame = bpy_current_frame()
    try:
        precalc_path = None if geotracker.precalcless else geotracker.precalc_path
        tracking_computation = gt.refine_async(current_frame, precalc_path)
        tracking_timer = RefineTimer(tracking_computation, current_frame)
        tracking_timer.start()
    except pkt_module().UnlicensedException as err:
        _log.error(f'UnlicensedException refine_act: {str(err)}')
        show_unlicensed_warning()
        # Return True to prevent doubling dialogs
        return ActionStatus(True, 'Unlicensed error')
    except Exception as err:
        _log.error(f'Unknown Exception refine_act: {str(err)}')
        show_warning_dialog(err)
        return ActionStatus(False, 'Some problem (see console)')

    return ActionStatus(True, 'Ok')


def refine_act() -> ActionStatus:
    check_status = _track_checks()
    if not check_status.success:
        return check_status

    settings = get_gt_settings()
    geotracker = settings.get_current_geotracker_item()
    gt = GTLoader.kt_geotracker()
    current_frame = bpy_current_frame()
    _log.output(f'REFINE AT: {current_frame}')

    progress_callback = GTClassLoader.RFProgressCallBack_class()()

    start_time = time.time()
    bpy_progress_begin(0, 100)
    settings.calculating_mode = 'REFINE'
    result = False
    try:
        precalc_path = None if geotracker.precalcless else geotracker.precalc_path
        result = gt.refine(current_frame, precalc_path, progress_callback)
    except pkt_module().UnlicensedException as err:
        _log.error(f'UnlicensedException refine_act: {str(err)}')
        show_unlicensed_warning()
        # Return True to prevent doubling dialogs
        return ActionStatus(True, 'Unlicensed error')
    except Exception as err:
        _log.error(f'Unknown Exception refine_act: {str(err)}')
        show_warning_dialog(err)
    finally:
        settings.stop_calculating()
        bpy_progress_end()
        overall_time = time.time() - start_time
        _log.output('Refine calculation time: {:.2f} sec'.format(overall_time))

    _log.output(f'Refined frames: {progress_callback.refined_frames}')
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
    _log.output('REFINE AT: {}'.format(current_frame))

    progress_callback = GTClassLoader.RFProgressCallBack_class()()

    start_time = time.time()
    bpy_progress_begin(0, 100)
    settings.calculating_mode = 'REFINE'
    result = False
    try:
        precalc_path = None if geotracker.precalcless else geotracker.precalc_path
        result = gt.refine_all(precalc_path, progress_callback)
    except pkt_module().UnlicensedException as err:
        _log.error(f'UnlicensedException refine_all_act: {str(err)}')
        show_unlicensed_warning()
        # Return True to prevent doubling dialogs
        return ActionStatus(True, 'Unlicensed error')
    except Exception as err:
        _log.error(f'Unknown Exception refine_all_act: {str(err)}')
        show_warning_dialog(err)
    finally:
        settings.stop_calculating()
        bpy_progress_end()
        overall_time = time.time() - start_time
        _log.output('Refine calculation time: {:.2f} sec'.format(overall_time))

    GTLoader.save_geotracker()
    GTLoader.update_all_viewport_shaders()
    GTLoader.viewport_area_redraw()
    if not result:
        return ActionStatus(False, 'Some problem. See console for details')
    return ActionStatus(True, 'ok')


def clear_between_keyframes_act() -> ActionStatus:
    check_status = common_checks(pinmode=True, is_calculating=True,
                                 reload_geotracker=True, geotracker=True,
                                 camera=True, geometry=True)
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
    GTLoader.update_all_viewport_shaders()
    GTLoader.viewport_area_redraw()
    return ActionStatus(True, 'ok')


def clear_direction_act(forward: bool) -> ActionStatus:
    check_status = common_checks(pinmode=True, is_calculating=True,
                                 reload_geotracker=True, geotracker=True,
                                 camera=True, geometry=True)
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
    GTLoader.update_all_viewport_shaders()
    GTLoader.viewport_area_redraw()
    return ActionStatus(True, 'ok')


def clear_all_act() -> ActionStatus:
    check_status = common_checks(pinmode=True, is_calculating=True,
                                 reload_geotracker=True, geotracker=True,
                                 camera=True, geometry=True)
    if not check_status.success:
        return check_status

    gt = GTLoader.kt_geotracker()
    try:
        gt.remove_all_track_data_and_keyframes()
    except Exception as err:
        _log.error(f'Unknown Exception clear_all_act: {str(err)}')
        show_warning_dialog(err)

    GTLoader.save_geotracker()
    GTLoader.update_all_viewport_shaders()
    GTLoader.viewport_area_redraw()
    return ActionStatus(True, 'ok')


def remove_focal_keyframe_act() -> ActionStatus:
    check_status = common_checks(is_calculating=True,
                                 reload_geotracker=True, geotracker=True,
                                 camera=True)
    if not check_status.success:
        return check_status

    geotracker = get_current_geotracker_item()
    remove_fcurve_point(geotracker.camobj.data, bpy_current_frame(), 'lens')
    return ActionStatus(True, 'ok')


def remove_focal_keyframes_act() -> ActionStatus:
    check_status = common_checks(is_calculating=True,
                                 reload_geotracker=True, geotracker=True,
                                 camera=True)
    if not check_status.success:
        return check_status

    geotracker = get_current_geotracker_item()
    remove_fcurve_from_object(geotracker.camobj.data, 'lens')
    return ActionStatus(True, 'ok')


def remove_pins_act() -> ActionStatus:
    check_status = common_checks(pinmode=True, is_calculating=True,
                                 reload_geotracker=True, geotracker=True,
                                 camera=True, geometry=True)
    if not check_status.success:
        return check_status

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
    check_status = common_checks(pinmode=True, is_calculating=True,
                                 reload_geotracker=True, geotracker=True,
                                 camera=True, geometry=True)
    if not check_status.success:
        return check_status

    gt = GTLoader.kt_geotracker()
    keyframe = bpy_current_frame()
    if gt.pins_count() > 0:
        GTLoader.safe_keyframe_add(keyframe, update=True)
        gt.toggle_pins(keyframe)

    GTLoader.update_all_viewport_shaders()
    GTLoader.viewport_area_redraw()
    return ActionStatus(True, 'ok')


def center_geo_act() -> ActionStatus:
    check_status = common_checks(pinmode=True, is_calculating=True,
                                 reload_geotracker=True, geotracker=True,
                                 camera=True, geometry=True)
    if not check_status.success:
        return check_status

    GTLoader.center_geo()
    GTLoader.update_all_viewport_shaders()
    GTLoader.viewport_area_redraw()
    return ActionStatus(True, 'ok')


def create_animated_empty_act() -> ActionStatus:
    check_status = common_checks(is_calculating=True,
                                 reload_geotracker=True, geotracker=True,
                                 camera=True, geometry=True)
    if not check_status.success:
        return check_status

    geotracker = get_current_geotracker_item()
    action = get_action(geotracker.animatable_object())
    if not action:
        msg = 'Animation is not created on source object'
        _log.error(msg)
        return ActionStatus(False, msg)

    obj = create_empty_object('GTEmpty')
    anim_data = obj.animation_data_create()
    anim_data.action = action
    return ActionStatus(True, 'ok')


def bake_texture_from_frames_act(selected_frames: List) -> ActionStatus:
    # TODO: Make possible to bake in out of Pinmode
    check_status = common_checks(pinmode=True, is_calculating=True,
                                 reload_geotracker=True, geotracker=True,
                                 camera=True, geometry=True, movie_clip=True)
    if not check_status.success:
        return check_status

    geotracker = get_current_geotracker_item()
    built_texture = bake_texture(geotracker, selected_frames)
    preview_material_with_texture(built_texture, geotracker.geomobj)
    return ActionStatus(True, 'ok')


def relative_to_camera_act() -> ActionStatus:
    check_status = common_checks(is_calculating=True,
                                 reload_geotracker=True, geotracker=True,
                                 camera=True, geometry=True)
    if not check_status.success:
        return check_status

    geotracker = get_current_geotracker_item()

    gt = GTLoader.kt_geotracker()
    animated_frames = get_object_keyframe_numbers(geotracker.geomobj)
    matrices = {x:gt.model_mat(x) for x in animated_frames}

    current_frame = bpy_current_frame()
    geomobj = geotracker.geomobj
    camobj = geotracker.camobj

    # Default camera position at (0, 0, 0) and +90 deg rotated on X
    cam_matrix = xy_to_xz_rotation_matrix_4x4()
    for frame in matrices:
        bpy_set_current_frame(frame)
        camobj.matrix_world = cam_matrix
        GTLoader.place_object_relative_to_camera(matrices[frame])
        update_depsgraph()
        create_animation_locrot_keyframe_force(geomobj)

    bpy_set_current_frame(current_frame)
    return ActionStatus(True, 'ok')


def _reset_unsaved_animation_changes_in_frame() -> int:
    current_frame = bpy_current_frame()
    bpy_set_current_frame(current_frame + 1)
    update_depsgraph()
    bpy_set_current_frame(current_frame)
    update_depsgraph()
    return current_frame


def geometry_repositioninig_act() -> ActionStatus:
    check_status = common_checks(is_calculating=True,
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

    current_frame = _reset_unsaved_animation_changes_in_frame()

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


def camera_repositioninig_act() -> ActionStatus:
    check_status = common_checks(is_calculating=True,
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

    current_frame = _reset_unsaved_animation_changes_in_frame()

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
    check_status = common_checks(is_calculating=True,
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

    current_frame = _reset_unsaved_animation_changes_in_frame()

    gt = GTLoader.kt_geotracker()

    all_animated_frames = list(set(geom_animated_frames).union(set(cam_animated_frames)))
    all_animated_frames.sort()
    _log.output(f'ALL FRAMES: {all_animated_frames}')
    all_matrices = {x:gt.model_mat(x) for x in all_animated_frames}
    _log.output(f'ALL: {all_matrices.keys()}')

    for frame in all_matrices:
        bpy_set_current_frame(frame)
        geomobj.matrix_world = geom_matrix
        GTLoader.place_camera_relative_to_object(all_matrices[frame])
        update_depsgraph()
        create_animation_locrot_keyframe_force(camobj)
        delete_locrot_keyframe(geomobj)

    bpy_set_current_frame(current_frame)
    geotracker.solve_for_camera = True
    mark_all_points_in_locrot(camobj, 'JITTER')
    keyframes = [x for x in gt.keyframes()]
    _log.output(f'KEYFRAMES TO MARK: {keyframes}')
    mark_selected_points_in_locrot(camobj, keyframes, 'KEYFRAME')
    return ActionStatus(True, 'ok')
