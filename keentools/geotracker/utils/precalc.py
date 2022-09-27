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

from typing import Any, Optional, Tuple
import time

import bpy

from ...utils.kt_logging import KTLogger
from ...addon_config import get_operator
from ...geotracker_config import GTConfig, get_gt_settings
from ..gtloader import GTLoader

from ...utils.other import hide_viewport_ui_elements_and_store_on_object
from ...utils.images import (np_image_to_grayscale,
                             np_array_from_background_image,
                             get_background_image_object,
                             check_bpy_image_size,
                             np_array_from_bpy_image,
                             set_background_image_by_movieclip)
from ...utils.coords import render_frame, update_depsgraph
from ...utils.manipulate import switch_to_camera
from ...utils.bpy_common import bpy_current_frame
from ..gt_class_loader import GTClassLoader
from ...utils.timer import RepeatTimer
from .calc_timer import CalcTimer


_log = KTLogger(__name__)


class PrecalcTimer(CalcTimer):
    def finish_calc_mode_with_error(self, err_message: str) -> None:
        super().finish_calc_mode()
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()
        geotracker.precalc_message = err_message

    def runner_state(self) -> Optional[float]:
        settings = get_gt_settings()

        _log.output('runner_state call')
        if self._runner.is_finished():
            self.finish_calc_mode()
            geotracker = settings.get_current_geotracker_item()
            geotracker.reload_precalc()
            return None

        progress, message = self._runner.current_progress()
        _log.output(f'runner_state: {progress} {message}')
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
            _log.output(f'NEXT FRAME IS NOT REACHED: {next_frame} current={current_frame}')
            self._target_frame = next_frame
            self._state = 'timeline'
            self._active_state_func = self.timeline_state
            return self._interval
        geotracker = settings.get_current_geotracker_item()

        np_img = np_array_from_background_image(geotracker.camobj)
        if np_img is None:
            # For testing purpose only
            _log.output('no np_img. possible in bpy.app.background mode')
            bg_img = get_background_image_object(geotracker.camobj)
            if not bg_img.image:
                _log.output('no image in background')
                self.finish_calc_mode_with_error('* Cannot load images')
                return None

            im_user = bg_img.image_user
            update_depsgraph()
            _log.output(bg_img.image.filepath)
            path = bg_img.image.filepath_from_user(image_user=im_user)
            _log.output(f'user_path: {current_frame} {path}')
            img = bpy.data.images.load(path)

            if not check_bpy_image_size(img):
                _log.output('cannot load image')
                self.finish_calc_mode_with_error('* Cannot load images')
                return None

            np_img = np_array_from_bpy_image(img)
            bpy.data.images.remove(img)

        grayscale = np_image_to_grayscale(np_img)
        self._runner.fulfill_loading_request(grayscale)
        return self._interval

    def prepare_camera(self) -> None:
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
        settings.calculating_mode = 'PRECALC'

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
            _log.output(f'timer registered: {res}')
        else:
            timer = RepeatTimer(self._interval, _func)
            timer.start()
            res = True
        return res


def precalc_with_runner_act(context: Any) -> Tuple[bool, str]:
    _log.output('precalc_with_runner_act start')
    settings = get_gt_settings()
    geotracker = settings.get_current_geotracker_item()

    if not geotracker:
        msg = 'No GeoTracker structure'
        _log.error(msg)
        return False, msg
    if not geotracker.camobj:
        msg = 'No camera object in GeoTracker'
        _log.error(msg)
        return False, msg
    if not geotracker.movie_clip:
        msg = 'No image sequence in GeoTracker'
        _log.error(msg)
        return False, msg
    if geotracker.precalc_path == '':
        msg = 'Precalc path is not specified'
        _log.error(msg)
        return False, msg
    if settings.is_calculating():
        msg = 'Other calculation is performing'
        _log.error(msg)
        return False, msg

    vp = GTLoader.viewport()
    vp.texter().register_handler(context)

    _log.output(f'precalc_path: {geotracker.precalc_path}')

    rw, rh = render_frame()
    area = context.area
    runner = GTClassLoader.PrecalcRunner_class()(
        geotracker.precalc_path, rw, rh,
        geotracker.precalc_start, geotracker.precalc_end,
        GTClassLoader.GeoTracker_class().license_manager(), True)

    pt = PrecalcTimer(area, runner)
    if pt.start():
        _log.output('Precalc started')
    else:
        return False, 'Cannot start precalc timer'
    return True, 'ok'
