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
from typing import Any, Callable, Optional, List
import time

import bpy
from bpy.types import Area

from ...addon_config import get_operator
from ...geotracker_config import GTConfig, get_gt_settings
from ..gtloader import GTLoader
from ...utils.ui_redraw import force_ui_redraw
from ...utils.other import (hide_viewport_ui_elements_and_store_on_object,
                            unhide_viewport_ui_elements_from_object)
from ...utils.images import (np_image_to_grayscale,
                             np_array_from_background_image,
                             set_background_image_by_movieclip)
from ...utils.coords import render_frame
from ...utils.manipulate import (switch_to_camera,
                                 exit_area_localview)
from ..gt_class_loader import GTClassLoader
from ..utils.tracking import reload_precalc


class PrecalcTimer:
    def __init__(self):
        self._interval: float = 0.001
        self._target_frame: int = -1
        self._runner: Any = None
        self._state: str = 'none'
        self._start_time: int = 0
        self._area: Area = None
        self._active_state_func: Callable = self.dummy_state

    def dummy_state(self) -> None:
        pass

    def set_runner(self, area: Area, runner: Optional[Any]=None) -> None:
        self._area = area
        self._runner = runner

    def get_area(self) -> Area:
        return self._area

    def _area_header(self, txt: str=None) -> None:
        area = self.get_area()
        area.header_text_set(txt)

    def finish_precalc_mode(self) -> None:
        self._state = 'over'
        settings = get_gt_settings()
        settings.precalc_mode = False
        geotracker = settings.get_current_geotracker_item()
        unhide_viewport_ui_elements_from_object(self.get_area(), geotracker.camobj)
        # self._area_header(None)
        area = self.get_area()
        exit_area_localview(area)
        force_ui_redraw('VIEW_3D')
        revert_default_screen_message()
        settings.user_interrupts = True

        logger = logging.getLogger(__name__)
        logger.info('Precalc is over: {:.2f} sec.'.format(
                    time.time() - self._start_time))

    def common_checks(self) -> bool:
        logger = logging.getLogger(__name__)
        log_output = logger.info
        settings = get_gt_settings()
        log_output(f'Timer: state={self._state} target={self._target_frame} '
                   f'current={settings.current_frame()}')
        if settings.user_interrupts:
            settings.precalc_mode = False
        if not settings.precalc_mode:
            self._runner.cancel()
            self.finish_precalc_mode()
            geotracker = settings.get_current_geotracker_item()
            reload_precalc(geotracker)
            return False
        return True

    def timeline_state(self) -> Optional[float]:
        logger = logging.getLogger(__name__)
        log_output = logger.info
        settings = get_gt_settings()
        if self._target_frame >= 0:
            if settings.current_frame() == self._target_frame:
                self._target_frame = -1
                self._state = 'runner'
                self._active_state_func = self.runner_state
                return self._interval
            settings.set_current_frame(self._target_frame)
            return self._interval
        else:
            log_output(f'FRAME PROBLEM {self._target_frame}')
        return self._interval

    def runner_state(self) -> Optional[float]:
        logger = logging.getLogger(__name__)
        log_output = logger.info
        settings = get_gt_settings()

        if self._runner.is_finished():
            self.finish_precalc_mode()
            geotracker = settings.get_current_geotracker_item()
            reload_precalc(geotracker)
            return None

        progress, message = self._runner.current_progress()
        log_output(f'{progress} {message}')
        message_to_screen([{'text': 'Precalc calculating... Please wait', 'y': 60,
                            'color': (1.0, 0.0, 0.0, 0.7)},
                           {'text': message, 'y': 30,
                            'color': (1.0, 1.0, 1.0, 0.7)}])
        next_frame = self._runner.is_loading_frame_requested()
        if next_frame is None:
            return self._interval
        settings.user_percent = progress * 100
        current_frame = settings.current_frame()
        if current_frame != next_frame:
            log_output(f'NEXT FRAME IS NOT REACHED: {next_frame} current={current_frame}')
            self._target_frame = next_frame
            self._state = 'timeline'
            self._active_state_func = self.timeline_state
            return self._interval
        geotracker = settings.get_current_geotracker_item()
        np_img = np_array_from_background_image(geotracker.camobj)
        if np_img is None:
            return None
        grayscale = np_image_to_grayscale(np_img)
        self._runner.fulfill_loading_request(grayscale)
        return self._interval

    def timer_func(self) -> Optional[float]:
        if not self.common_checks():
            return None
        return self._active_state_func()

    def start(self) -> None:
        settings = get_gt_settings()
        settings.precalc_mode = True
        self._state = 'runner'
        self._active_state_func = self.runner_state
        self._start_time = time.time()
        # self._area_header('Precalc is calculating... Please wait')
        message_to_screen([{'text':'Precalc is calculating... Please wait', 'color': (1.0, 0., 0., 0.7)}])
        op = get_operator(GTConfig.gt_interrupt_modal_idname)
        op('INVOKE_DEFAULT')
        bpy.app.timers.register(self.timer_func, first_interval=self._interval)


def precalc_with_runner_act(context: Any) -> bool:
    logger = logging.getLogger(__name__)
    log_output = logger.info
    log_output('precalc_with_runner_act start')
    settings = get_gt_settings()
    geotracker = settings.get_current_geotracker_item()
    rw, rh = render_frame()

    area = context.area

    if not geotracker or not geotracker.camobj:
        return False

    if geotracker.precalc_path == '':
        return False

    vp = GTLoader.viewport()
    vp.texter().register_handler(context)

    log_output(f'precalc_path: {geotracker.precalc_path}')

    runner = GTClassLoader.PrecalcRunner_class()(
        geotracker.precalc_path, rw, rh,
        geotracker.precalc_start, geotracker.precalc_end,
        GTClassLoader.GeoTracker_class().license_manager(), True)

    switch_to_camera(area, geotracker.camobj, geotracker.animatable_object())
    hide_viewport_ui_elements_and_store_on_object(area, geotracker.camobj)
    set_background_image_by_movieclip(geotracker.camobj, geotracker.movie_clip)
    geotracker.reload_background_image()

    pt = PrecalcTimer()
    pt.set_runner(area, runner)
    pt.start()
    return True


def message_to_screen(msg: List) -> None:
    vp = GTLoader.viewport()
    texter = vp.texter()
    texter.set_message(msg)


def revert_default_screen_message(unregister=True) -> None:
    vp = GTLoader.viewport()
    texter = vp.texter()
    texter.set_message(texter.get_default_text())
    if unregister:
        texter.unregister_handler()
