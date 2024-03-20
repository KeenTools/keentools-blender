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
from typing import Any, Callable, Optional, List, Tuple, Set
from enum import Enum

import bpy
from bpy.types import Area

from ..utils.kt_logging import KTLogger
from ..addon_config import (gt_settings,
                            ft_settings,
                            get_operator,
                            ProductType,
                            get_settings)
from ..geotracker_config import GTConfig
from ..facetracker_config import FTConfig
from ..utils.manipulate import exit_area_localview
from ..utils.ui_redraw import force_ui_redraw
from ..utils.bpy_common import (bpy_current_frame,
                                 bpy_set_current_frame,
                                 bpy_background_mode,
                                 bpy_timer_register)
from ..utils.timer import RepeatTimer
from ..blender_independent_packages.pykeentools_loader import module as pkt_module
from ..geotracker.utils.prechecks import show_warning_dialog
from ..geotracker.interface.screen_mesages import (revert_default_screen_message,
                                        operation_calculation_screen_message,
                                        staged_calculation_screen_message)
from ..tracker.tracking_blendshapes import create_relative_shape_keyframe


_log = KTLogger(__name__)


class _ComputationState(Enum):
    RUNNING = 0
    SUCCESS = 1
    ERROR = 2


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
    def get_settings(self) -> Any:
        return get_settings(self.product)

    def __init__(self, area: Optional[Area] = None,
                 runner: Optional[Any] = None, *, product: int):
        self.product = product
        self.current_state: Callable = self.timeline_state

        self._interval: float = 0.001
        self._target_frame: int = -1
        self._operation_name: str = 'CalcTimer operation'
        self._runner: Any = runner
        self._start_time: float = 0.0
        self._area: Area = area

        self.interrupt_operator_name = GTConfig.gt_interrupt_modal_idname \
            if product == ProductType.GEOTRACKER \
            else FTConfig.ft_interrupt_modal_idname

        settings = self.get_settings()
        self._started_in_pinmode: bool = settings.pinmode
        self._start_frame: int = bpy_current_frame()
        self._error_message: str = ''
        self.add_timer(self)

    def set_current_state(self, func: Callable) -> None:
        self.current_state = func

    def set_error_message(self, message: str) -> None:
        self._error_message = message

    def current_state_name(self) -> str:
        states = [('timeline', self.timeline_state),
                  ('runner', self.runner_state),
                  ('finish_success', self.finish_success_state),
                  ('finish_error', self.finish_error_state)]
        names, funcs = zip(*states)
        if self.current_state in funcs:
            return names[funcs.index(self.current_state)]
        return 'unknown'

    def inactive_state(self) -> None:
        pass

    def get_area(self) -> Area:
        return self._area

    def _area_header(self, txt: Optional[str] = None) -> None:
        area = self.get_area()
        area.header_text_set(txt)

    def finish_calc_mode(self) -> None:
        _log.debug('finish_calc_mode start')
        self._runner.cancel()
        self.remove_timer(self)
        settings = self.get_settings()
        settings.stop_calculating()
        revert_default_screen_message(unregister=not settings.pinmode,
                                      product=self.product)

        if not settings.pinmode:
            area = self.get_area()
            settings.viewport_state.show_ui_elements(area)
            exit_area_localview(area)

        settings.user_interrupts = True
        bpy_set_current_frame(self._start_frame)
        force_ui_redraw('VIEW_3D')
        _log.info('Calculation is over: {:.2f} sec.'.format(
                  time.time() - self._start_time))

    def common_checks(self) -> bool:
        settings = self.get_settings()
        _log.output(f'common_checks: state={self.current_state_name()} '
                    f'target={self._target_frame} '
                    f'current={bpy_current_frame()}')
        if settings.user_interrupts:
            _log.error('common_checks settings.user_interrupts detected')
            settings.stop_calculating()
        if not settings.is_calculating():
            self._runner.cancel()
            self.finish_calc_mode()
            geotracker = settings.get_current_geotracker_item()
            geotracker.reload_precalc()
            return False
        return True

    def finish_success_state(self) -> None:
        _log.output(f'{self._operation_name} finish_success_state call')
        self.finish_calc_mode()
        return None

    def finish_error_state(self) -> None:
        _log.output(f'{self._operation_name} finish_error_state call')
        _log.error(self._error_message)
        self.finish_calc_mode()
        return None

    def timeline_state(self) -> Optional[float]:
        if self._target_frame >= 0:
            if bpy_current_frame() == self._target_frame:
                self._target_frame = -1
            else:
                bpy_set_current_frame(self._target_frame)
                return self._interval
        else:
            _log.output(f'FRAME PROBLEM {self._target_frame}')
            self.set_error_message('Impossible frame number')
            self.set_current_state(self.finish_error_state)
            return self.current_state()

        self.set_current_state(self.runner_state)
        return self._interval

    def runner_state(self) -> Optional[float]:
        _log.output('runner_state call')
        return self._interval

    def timer_func(self) -> Optional[float]:
        _log.output('timer_func')
        if not self.common_checks():
            _log.output('timer_func common_checks problem')
            return None
        return self.current_state()

    def start(self) -> bool:
        return True


class _CommonTimer(TimerMixin):
    @classmethod
    def get_settings(cls) -> Any:
        return gt_settings()

    @classmethod
    def user_interrupt_operator_name(cls):
        return GTConfig.gt_interrupt_modal_idname

    def __init__(self, computation: Any, from_frame: int = -1,
                 revert_current_frame: bool=False,
                 *, success_callback: Optional[Callable] = None,
                 error_callback: Optional[Callable] = None,
                 product: int):

        self.product = product
        self.current_state: Callable = self.timeline_state
        self.tracking_computation: Any = computation

        self._interval: float = 0.001
        self._target_frame: int = from_frame
        self._operation_name: str = 'common operation'
        self._operation_help: str = 'ESC to cancel'
        self._calc_mode: str = 'NONE'
        self._overall_func: Callable = lambda: None
        self._start_frame: int = from_frame
        self._revert_current_frame: bool = revert_current_frame
        self._prevent_playback: bool = False
        self._start_time: float = 0
        self._performed_frames: Set = set()
        self._success_callback: Optional[Callable] = success_callback
        self._error_callback: Optional[Callable] = error_callback
        self.add_timer(self)

    def create_shape_keyframe(self):
        _log.magenta(f'{self.__class__.__name__} empty create_shape_keyframe')

    def set_current_state(self, func: Callable) -> None:
        self.current_state = func

    def current_state_name(self) -> str:
        states = [('timeline', self.timeline_state),
                  ('computation', self.computation_state),
                  ('finish_success', self.finish_success_state),
                  ('finish_error', self.finish_error_state)]
        names, funcs = zip(*states)
        if self.current_state in funcs:
            return names[funcs.index(self.current_state)]
        return 'unknown'

    def add_performed_frame(self, frame: int) -> bool:
        if frame in self._performed_frames:
            _log.output(_log.color('red', f'add_performed_frame: * {frame} *'))
            return False
        _log.output(f'add_performed_frame: {frame}')
        self._performed_frames.add(frame)
        return True

    def performed_frames(self) -> List:
        return sorted(self._performed_frames)

    def get_stage_info(self) -> Tuple[int, int]:
        return 0, 1

    def timeline_state(self) -> Optional[float]:
        settings = self.get_settings()
        if settings.user_interrupts or not settings.pinmode:
            self._cancel()

        if bpy_current_frame() == self._target_frame:
            self.set_current_state(self.computation_state)
            return self.current_state()
        bpy_set_current_frame(self._target_frame)
        _log.output(f'{self._operation_name} timeline_state: '
                    f'set_current_frame({self._target_frame})')
        return self._interval

    def computation_state(self) -> Optional[float]:
        settings = self.get_settings()
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

        if result in [_ComputationState.RUNNING, _ComputationState.SUCCESS]:
            self.add_performed_frame(tracking_current_frame)
            self.create_shape_keyframe()

        if result == _ComputationState.SUCCESS:
            self.set_current_state(self.finish_success_state)
            return self.current_state()

        overall = self._overall_func()
        if result != _ComputationState.RUNNING or overall is None:
            _log.output(f'\nresult: {result}\noverall: {overall}')
            self.set_current_state(self.finish_error_state)
            return self.current_state()

        if self._prevent_playback:
            settings.loader().viewport().tag_redraw()
            return self._interval

        if result and tracking_current_frame != current_frame:
            self._target_frame = tracking_current_frame
            self.set_current_state(self.timeline_state)
            bpy_set_current_frame(self._target_frame)
            return self._interval

        return self._interval

    def finish_success_state(self) -> None:
        _log.output(_log.color('red', f'{self._operation_name} '
                                      f'finish_success_state call'))
        self._finish_computation()
        if self._success_callback is not None:
            self._success_callback(self.performed_frames())
        return None

    def finish_error_state(self) -> None:
        _log.output(_log.color('red', f'{self._operation_name} '
                                      f'finish_error_state call'))
        self._finish_computation()
        if self._error_callback is not None:
            self._error_callback(self.performed_frames())
        return None

    def _finish_computation(self) -> None:
        _log.output(f'{self._operation_name} _finish_computation call')
        self._output_statistics()
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
        revert_default_screen_message(product=self.product)
        self._stop_user_interrupt_operator()
        settings = self.get_settings()
        loader = settings.loader()
        loader.save_geotracker()
        settings.stop_calculating()
        self.remove_timer(self)
        if self._revert_current_frame:
            bpy_set_current_frame(self._start_frame)

        loader.viewport().tag_redraw()
        return None

    def _start_user_interrupt_operator(self) -> None:
        op = get_operator(self.user_interrupt_operator_name())
        op('INVOKE_DEFAULT')

    def _stop_user_interrupt_operator(self) -> None:
        settings = self.get_settings()
        settings.user_interrupts = True

    def _safe_resume(self) -> _ComputationState:
        try:
            state = self.tracking_computation.state()
            _log.output(f'_safe_resume: {state}')
            if state == pkt_module().ComputationState.RUNNING:
                self.tracking_computation.resume()
                _log.output(f'_safe_resume _overall_func: {self._overall_func}')
                overall = self._overall_func()
                _log.output(f'_safe_resume overall: {overall}')
                if overall is None:
                    return _ComputationState.ERROR
                finished_frames, total_frames = overall
                current_stage, total_stages = self.get_stage_info()
                staged_calculation_screen_message(
                    self._operation_name, self._operation_help,
                    finished_frames=finished_frames,
                    total_frames=total_frames,
                    current_stage=current_stage + 1,
                    total_stages=total_stages,
                    product=self.product)
                settings = self.get_settings()
                total = total_frames if total_frames != 0 else 1
                settings.user_percent = 100 * finished_frames / total
                return _ComputationState.RUNNING
            if state == pkt_module().ComputationState.SUCCESS:
                return _ComputationState.SUCCESS
        except RuntimeError as err:
            msg = f'{self._operation_name} _safe_resume ' \
                  f'Computation Exception.\n{str(err)}'
            _log.error(msg)
            show_warning_dialog(err)
        except Exception as err:
            msg = f'{self._operation_name} _safe_resume Exception. {str(err)}'
            _log.error(msg)
            show_warning_dialog(err)
        return _ComputationState.ERROR

    def _output_statistics(self) -> None:
        overall = self._overall_func()
        _log.output(f'--- {self._operation_name} statistics ---')
        _log.output(f'Total calc frames: {overall}')
        settings = self.get_settings()
        gt = settings.loader().kt_geotracker()
        _log.output(f'KEYFRAMES: {gt.keyframes()}')
        _log.output(f'TRACKED FRAMES: {gt.track_frames()}\n')
        _log.output(f'PERFORMED FRAMES: {self.performed_frames()}')
        overall_time = time.time() - self._start_time
        _log.output(f'{self._operation_name} calculation time: {overall_time:.2f} sec')

    def _cancel(self) -> None:
        _log.output(f'{self._operation_name} Cancel call. State={self.current_state_name()}')
        self.tracking_computation.cancel()

    def timer_func(self) -> Optional[float]:
        return self.current_state()

    def start(self) -> None:
        self._start_time = time.time()
        if not bpy_background_mode():
            self._start_user_interrupt_operator()
        operation_calculation_screen_message(self._operation_name,
                                             self._operation_help,
                                             product=self.product)
        settings = self.get_settings()
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
    def __init__(self, computation: Any, from_frame: int = -1,
                 *, success_callback: Optional[Callable] = None,
                 error_callback: Optional[Callable] = None,
                 product: int = ProductType.GEOTRACKER):
        super().__init__(computation, from_frame,
                         success_callback=success_callback,
                         error_callback=error_callback,
                         product=product)
        self._operation_name = 'Tracking'
        self._operation_help = 'ESC to stop'
        self._calc_mode = 'TRACKING'
        self._overall_func = computation.finished_and_total_frames


class FTTrackTimer(TrackTimer):
    @classmethod
    def get_settings(cls) -> Any:
        return ft_settings()

    @classmethod
    def user_interrupt_operator_name(cls):
        return FTConfig.ft_interrupt_modal_idname

    def create_shape_keyframe(self):
        create_relative_shape_keyframe(bpy_current_frame())


class RefineTimer(_CommonTimer):
    def __init__(self, computation: Any, from_frame: int = -1,
                 *, success_callback: Optional[Callable] = None,
                 error_callback: Optional[Callable] = None,
                 product: int):
        super().__init__(computation, from_frame, revert_current_frame=True,
                         success_callback=success_callback,
                         error_callback=error_callback, product=product)
        self._operation_name = 'Refining'
        self._operation_help = 'ESC to abort. Changes have NOT yet been applied'
        self._calc_mode = 'REFINE'
        self._overall_func = computation.finished_and_total_stage_frames

    def get_stage_info(self) -> Tuple[int, int]:
        return self.tracking_computation.current_stage(), \
               self.tracking_computation.total_stages()


class FTRefineTimer(RefineTimer):
    @classmethod
    def get_settings(cls) -> Any:
        return ft_settings()

    @classmethod
    def user_interrupt_operator_name(cls):
        return FTConfig.ft_interrupt_modal_idname

    def create_shape_keyframe(self):
        _log.red(f'{self.__class__.__name__} create_shape_keyframe')
        create_relative_shape_keyframe(bpy_current_frame())


class RefineTimerFast(RefineTimer):
    def __init__(self, computation: Any, from_frame: int = -1,
                 *, success_callback: Optional[Callable] = None,
                 error_callback: Optional[Callable] = None, product: int):
        super().__init__(computation, from_frame,
                         success_callback=success_callback,
                         error_callback=error_callback, product=product)
        self._prevent_playback = True


class FTRefineTimerFast(RefineTimerFast):
    @classmethod
    def get_settings(cls) -> Any:
        return ft_settings()

    @classmethod
    def user_interrupt_operator_name(cls):
        return FTConfig.ft_interrupt_modal_idname
