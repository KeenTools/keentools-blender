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

import time
from typing import Any, Callable, Optional, List, Tuple

import bpy
from bpy.types import Area

from ...utils.kt_logging import KTLogger
from ...addon_config import get_operator
from ...geotracker_config import get_gt_settings, GTConfig
from ..gtloader import GTLoader
from ...utils.manipulate import exit_area_localview
from ...utils.ui_redraw import force_ui_redraw
from ...utils.bpy_common import (bpy_current_frame,
                                 bpy_set_current_frame,
                                 bpy_background_mode,
                                 bpy_timer_register)
from ...utils.timer import RepeatTimer
from ...blender_independent_packages.pykeentools_loader import module as pkt_module
from .prechecks import show_warning_dialog
from ..interface.screen_mesages import (revert_default_screen_message,
                                        operation_calculation_screen_message,
                                        staged_calculation_screen_message)


_log = KTLogger(__name__)


class TimerMixin:
    _timers: List = []

    @classmethod
    def active_timers(cls) -> List:
        return cls._timers

    @classmethod
    def add_timer(cls, timer: Any) -> None:
        cls._timers.append(timer)

    @classmethod
    def remove_timer(cls, timer: Any) -> bool:
        if timer in cls._timers:
            cls._timers.remove(timer)
            return True
        return False

    @classmethod
    def clear_timers(cls) -> None:
        cls._timers = []


class CalcTimer(TimerMixin):
    def __init__(self, area: Optional[Area]=None, runner: Optional[Any]=None):
        self._interval: float = 0.001
        self._target_frame: int = -1
        self._runner: Any = runner
        self._state: str = 'none'
        self._start_time: float = 0.0
        self._area: Area = area
        self._active_state_func: Callable = self.dummy_state
        settings = get_gt_settings()
        self._started_in_pinmode = settings.pinmode
        self._start_frame = bpy_current_frame()
        self.add_timer(self)

    def dummy_state(self) -> None:
        pass

    def get_area(self) -> Area:
        return self._area

    def _area_header(self, txt: str=None) -> None:
        area = self.get_area()
        area.header_text_set(txt)

    def finish_calc_mode(self) -> None:
        self._runner.cancel()
        self.remove_timer(self)
        self._state = 'over'
        settings = get_gt_settings()
        settings.stop_calculating()
        revert_default_screen_message(unregister=not settings.pinmode)

        if not settings.pinmode:
            area = self.get_area()
            settings.viewport_state.show_ui_elements(area)
            exit_area_localview(area)

        settings.user_interrupts = True
        bpy_set_current_frame(self._start_frame)
        force_ui_redraw('VIEW_3D')
        _log.info('Calculation is over: {:.2f} sec.'.format(
                  time.time() - self._start_time))

    def finish_calc_mode_with_error(self, err_message: str) -> None:
        self.finish_calc_mode()
        _log.error(err_message)

    def common_checks(self) -> bool:
        settings = get_gt_settings()
        _log.output(f'common_checks: state={self._state} '
                    f'target={self._target_frame} '
                    f'current={bpy_current_frame()}')
        if settings.user_interrupts:
            settings.stop_calculating()
        if not settings.is_calculating():
            self._runner.cancel()
            self.finish_calc_mode()
            geotracker = settings.get_current_geotracker_item()
            geotracker.reload_precalc()
            return False
        return True

    def timeline_state(self) -> Optional[float]:
        if self._target_frame >= 0:
            if bpy_current_frame() == self._target_frame:
                self._target_frame = -1
            else:
                bpy_set_current_frame(self._target_frame)
                return self._interval
        else:
            _log.output(f'FRAME PROBLEM {self._target_frame}')
            self.finish_calc_mode_with_error('Impossible frame number')
            return None
        self._state = 'runner'
        self._active_state_func = self.runner_state
        return self._interval

    def runner_state(self) -> Optional[float]:
        _log.output('runner_state call')
        return self._interval

    def timer_func(self) -> Optional[float]:
        _log.output('timer_func')
        if not self.common_checks():
            _log.output('timer_func common_checks problem')
            return None
        return self._active_state_func()

    def start(self) -> bool:
        return True


class _CommonTimer(TimerMixin):
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
        self._prevent_playback: bool = False
        self._start_time: float = 0
        self.add_timer(self)

    def get_stage_info(self) -> Tuple[int, int]:
        return 0, 1

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

        if self._prevent_playback:
            GTLoader.viewport().tag_redraw()
            return self._interval

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
        while attempts < max_attempts and \
                self.tracking_computation.state() == pkt_module().ComputationState.RUNNING:
            attempts += 1
            _log.output(f'TRY TO STOP COMPUTATION. ATTEMPT {attempts}')
            self.tracking_computation.cancel()
            self._safe_resume()
        if attempts >= max_attempts and \
                self.tracking_computation.state() == pkt_module().ComputationState.RUNNING:
            _log.error(f'PROBLEM WITH COMPUTATION STOP')
        revert_default_screen_message()
        self._stop_user_interrupt_operator()
        GTLoader.save_geotracker()
        settings = get_gt_settings()
        settings.stop_calculating()
        self.remove_timer(self)
        if self._revert_current_frame:
            bpy_set_current_frame(self._start_frame)

        GTLoader.viewport().tag_redraw()
        return None

    def _start_user_interrupt_operator(self) -> None:
        op = get_operator(GTConfig.gt_interrupt_modal_idname)
        op('INVOKE_DEFAULT')

    def _stop_user_interrupt_operator(self) -> None:
        settings = get_gt_settings()
        settings.user_interrupts = True

    def _safe_resume(self) -> bool:
        try:
            state = self.tracking_computation.state()
            _log.output(f'_safe_resume: {state}')
            if state == pkt_module().ComputationState.RUNNING:
                self.tracking_computation.resume()
                _log.output(f'_safe_resume _overall_func: {self._overall_func}')
                overall = self._overall_func()
                _log.output(f'_safe_resume overall: {overall}')
                if overall is None:
                    return False
                finished_frames, total_frames = overall
                current_stage, total_stages = self.get_stage_info()
                staged_calculation_screen_message(
                    self._operation_name,
                    finished_frames=finished_frames,
                    total_frames=total_frames,
                    current_stage=current_stage + 1,
                    total_stages=total_stages)
                settings = get_gt_settings()
                total = total_frames if total_frames != 0 else 1
                settings.user_percent = 100 * finished_frames / total
                return True
        except RuntimeError as err:
            msg = f'{self._operation_name} _safe_resume ' \
                  f'Computation Exception.\n{str(err)}'
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
        overall_time = time.time() - self._start_time
        _log.output(f'{self._operation_name} calculation time: {overall_time:.2f} sec')

    def _cancel(self) -> None:
        _log.output(f'{self._operation_name} Cancel call. State={self._state}')
        self.tracking_computation.cancel()

    def timer_func(self) -> Optional[float]:
        return self._active_state_func()

    def start(self) -> None:
        self._start_time = time.time()
        if not bpy_background_mode():
            self._start_user_interrupt_operator()
        operation_calculation_screen_message(self._operation_name)
        settings = get_gt_settings()
        settings.calculating_mode = self._calc_mode

        _func = self.timer_func
        if not bpy_background_mode():
            bpy_timer_register(_func, first_interval=self._interval)
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
        self._operation_name = 'Refining'
        self._calc_mode = 'REFINE'
        self._overall_func = computation.finished_and_total_stage_frames

    def get_stage_info(self) -> Tuple[int, int]:
        return self.tracking_computation.current_stage(), \
               self.tracking_computation.total_stages()


class RefineTimerFast(RefineTimer):
    def __init__(self, computation: Any, from_frame: int = -1):
        super().__init__(computation, from_frame)
        self._prevent_playback = True
