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
from typing import Any, Callable, Optional

from bpy.types import Area

from ...utils.kt_logging import KTLogger
from ...geotracker_config import get_gt_settings
from ..gtloader import GTLoader
from ...utils.bpy_common import bpy_current_frame, bpy_set_current_frame
from ...utils.other import unhide_viewport_ui_elements_from_object
from ...utils.manipulate import exit_area_localview
from ...utils.ui_redraw import force_ui_redraw


_log = KTLogger(__name__)


class CalcTimer():
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

    def dummy_state(self) -> None:
        pass

    def get_area(self) -> Area:
        return self._area

    def _area_header(self, txt: str=None) -> None:
        area = self.get_area()
        area.header_text_set(txt)

    def finish_calc_mode(self) -> None:
        self._state = 'over'
        settings = get_gt_settings()
        settings.stop_calculating()
        GTLoader.viewport().revert_default_screen_message(
            unregister=not settings.pinmode)

        geotracker = settings.get_current_geotracker_item()
        if not settings.pinmode:
            area = self.get_area()
            unhide_viewport_ui_elements_from_object(area, geotracker.camobj)
            exit_area_localview(area)
        settings.user_interrupts = True
        force_ui_redraw('VIEW_3D')

        _log.info('Calculation is over: {:.2f} sec.'.format(
                  time.time() - self._start_time))

    def finish_calc_mode_with_error(self, err_message: str) -> None:
        self.finish_calc_mode()
        _log.error(err_message)

    def common_checks(self) -> bool:
        settings = get_gt_settings()
        _log.output(f'Timer: state={self._state} target={self._target_frame} '
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
                self._state = 'runner'
                self._active_state_func = self.runner_state
                return self._interval
            bpy_set_current_frame(self._target_frame)
            return self._interval
        else:
            _log.output(f'FRAME PROBLEM {self._target_frame}')
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
