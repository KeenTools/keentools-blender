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
from typing import Any, Callable, Optional, List, Tuple
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
                             get_background_image_object,
                             check_bpy_image_size,
                             np_array_from_bpy_image,
                             set_background_image_by_movieclip)
from ...utils.coords import render_frame, update_depsgraph
from ...utils.manipulate import (switch_to_camera,
                                 exit_area_localview)
from ...utils.bpy_common import bpy_current_frame, bpy_set_current_frame
from ..gt_class_loader import GTClassLoader
from ...utils.timer import RepeatTimer


_logger: Any = logging.getLogger(__name__)


def _log_output(message: str) -> None:
    global _logger
    _logger.debug(message)


def _log_error(message: str) -> None:
    global _logger
    _logger.error(message)


def _log_info(message: str) -> None:
    global _logger
    _logger.info(message)


class PrecalcTimer:
    def __init__(self, area: Optional[Area]=None, runner: Optional[Any]=None):
        self._interval: float = 0.001
        self._target_frame: int = -1
        self._runner: Any = runner
        self._state: str = 'none'
        self._start_time: int = 0
        self._area: Area = area
        self._active_state_func: Callable = self.dummy_state
        settings = get_gt_settings()
        self._started_in_pinmode = settings.pinmode

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
        GTLoader.revert_default_screen_message(unregister=not settings.pinmode)

        geotracker = settings.get_current_geotracker_item()
        if not settings.pinmode:
            unhide_viewport_ui_elements_from_object(self.get_area(), geotracker.camobj)
            # self._area_header(None)
            area = self.get_area()
            exit_area_localview(area)
        settings.user_interrupts = True
        force_ui_redraw('VIEW_3D')

        _log_info('Precalc is over: {:.2f} sec.'.format(
                  time.time() - self._start_time))

    def common_checks(self) -> bool:
        settings = get_gt_settings()
        _log_output(f'Timer: state={self._state} target={self._target_frame} '
                    f'current={bpy_current_frame()}')
        if settings.user_interrupts:
            settings.precalc_mode = False
        if not settings.precalc_mode:
            self._runner.cancel()
            self.finish_precalc_mode()
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
            _log_output(f'FRAME PROBLEM {self._target_frame}')
        return self._interval

    def runner_state(self) -> Optional[float]:
        settings = get_gt_settings()

        _log_output('runner_state call')
        if self._runner.is_finished():
            self.finish_precalc_mode()
            geotracker = settings.get_current_geotracker_item()
            geotracker.reload_precalc()
            return None

        progress, message = self._runner.current_progress()
        _log_output(f'runner_state: {progress} {message}')
        GTLoader.message_to_screen(
            [{'text': 'Precalc calculating... Please wait', 'y': 60,
              'color': (1.0, 0.0, 0.0, 0.7)},
             {'text': message, 'y': 30,
              'color': (1.0, 1.0, 1.0, 0.7)}])
        next_frame = self._runner.is_loading_frame_requested()
        if next_frame is None:
            return self._interval
        settings.user_percent = progress * 100
        current_frame = bpy_current_frame()
        if current_frame != next_frame:
            _log_output(f'NEXT FRAME IS NOT REACHED: {next_frame} current={current_frame}')
            self._target_frame = next_frame
            self._state = 'timeline'
            self._active_state_func = self.timeline_state
            return self._interval
        geotracker = settings.get_current_geotracker_item()

        np_img = np_array_from_background_image(geotracker.camobj)
        if np_img is None:
            # For testing purpose only
            _log_output('no np_img. possible in bpy.app.background mode')
            bg_img = get_background_image_object(geotracker.camobj)

            im_user = bg_img.image_user
            update_depsgraph()
            _log_output(bg_img.image.filepath)
            path = bg_img.image.filepath_from_user(image_user=im_user)
            _log_output(f'user_path: {current_frame} {path}')
            img = bpy.data.images.load(path)

            if not check_bpy_image_size(img):
                _log_output('cannot load image')
                return None

            np_img = np_array_from_bpy_image(img)
            bpy.data.images.remove(img)

        grayscale = np_image_to_grayscale(np_img)
        self._runner.fulfill_loading_request(grayscale)
        return self._interval

    def timer_func(self) -> Optional[float]:
        _log_output('timer_func')
        if not self.common_checks():
            _log_output('timer_func common_checks problem')
            return None
        return self._active_state_func()

    def prepare_camera(self):
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()
        if not settings.pinmode:
            switch_to_camera(self._area, geotracker.camobj,
                             geotracker.animatable_object())
            hide_viewport_ui_elements_and_store_on_object(self._area, geotracker.camobj)
        set_background_image_by_movieclip(geotracker.camobj,
                                          geotracker.movie_clip)
        geotracker.reload_background_image()

    def start(self) -> bool:
        self.prepare_camera()
        settings = get_gt_settings()
        settings.precalc_mode = True
        self._state = 'runner'
        self._active_state_func = self.runner_state
        self._start_time = time.time()
        # self._area_header('Precalc is calculating... Please wait')
        GTLoader.message_to_screen(
            [{'text':'Precalc is calculating... Please wait',
              'color': (1.0, 0., 0., 0.7)}])

        _func = self.timer_func
        if not bpy.app.background:
            op = get_operator(GTConfig.gt_interrupt_modal_idname)
            op('INVOKE_DEFAULT')
            bpy.app.timers.register(_func, first_interval=self._interval)
            res = bpy.app.timers.is_registered(_func)
            _log_output(f'timer registered: {res}')
        else:
            timer = RepeatTimer(self._interval, _func)
            timer.start()
            res = True
        return res


def precalc_with_runner_act(context: Any) -> Tuple[bool, str]:
    _log_output('precalc_with_runner_act start')
    settings = get_gt_settings()
    geotracker = settings.get_current_geotracker_item()

    if not geotracker:
        msg = 'No GeoTracker structure'
        _log_error(msg)
        return False, msg
    if not geotracker.camobj:
        msg = 'No camera object in GeoTracker'
        _log_error(msg)
        return False, msg
    if not geotracker.movie_clip:
        msg = 'No image sequence in GeoTracker'
        _log_error(msg)
        return False, msg
    if geotracker.precalc_path == '':
        msg = 'Precalc path is not specified'
        _log_error(msg)
        return False, msg
    if settings.calculation_mode():
        msg = 'Other calculation is performing'
        _log_error(msg)
        return False, msg

    vp = GTLoader.viewport()
    vp.texter().register_handler(context)

    _log_output(f'precalc_path: {geotracker.precalc_path}')

    rw, rh = render_frame()
    area = context.area
    runner = GTClassLoader.PrecalcRunner_class()(
        geotracker.precalc_path, rw, rh,
        geotracker.precalc_start, geotracker.precalc_end,
        GTClassLoader.GeoTracker_class().license_manager(), True)

    pt = PrecalcTimer(area, runner)
    if pt.start():
        _log_output('Precalc started')
    else:
        return False, 'Cannot start precalc timer'
    return True, 'ok'
