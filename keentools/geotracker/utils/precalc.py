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
import os

import bpy

from ...utils.kt_logging import KTLogger
from ...addon_config import get_operator, ActionStatus, get_settings

from ...utils.images import (np_image_to_grayscale,
                             np_array_from_background_image,
                             get_background_image_object,
                             check_bpy_image_size,
                             np_array_from_bpy_image)
from ...utils.bpy_common import (bpy_render_frame,
                                 bpy_current_frame,
                                 update_depsgraph,
                                 bpy_background_mode,
                                 bpy_timer_register)
from ...tracker.class_loader import KTClassLoader
from ...utils.timer import RepeatTimer
from .prechecks import common_checks, prepare_camera
from ...blender_independent_packages.pykeentools_loader import module as pkt_module
from .prechecks import show_warning_dialog, show_unlicensed_warning
from ..interface.screen_mesages import analysing_screen_message
from ...tracker.calc_timer import CalcTimer


_log = KTLogger(__name__)


class PrecalcTimer(CalcTimer):
    def finish_error_state(self) -> None:
        self.finish_calc_mode()
        settings = self.get_settings()
        geotracker = settings.get_current_geotracker_item()
        geotracker.precalc_message = self._error_message
        _log.error(f'precalc error message: {self._error_message}')
        return None

    def runner_state(self) -> Optional[float]:
        _log.output('runner_state call')

        settings = self.get_settings()
        if self._runner.is_finished():
            _log.output('runner is_finished')
            err = self._runner.exception()
            if err is not None:
                _log.error(f'runner Exception:\n{str(err)}\n{type(err)}')
                try:
                    if type(err) == pkt_module().precalc.PrecalcUnlicensedException:
                        show_unlicensed_warning()
                    elif type(err) == pkt_module().precalc.PrecalcOpenFileException:
                        show_warning_dialog('Precalc file is locked.\n'
                                            'See the System Console to get\n'
                                            'a detailed error information.')
                    else:
                        show_warning_dialog(str(err))
                except Exception as err2:
                    show_warning_dialog(str(err) + '\n\n' + str(err2))
            self.finish_calc_mode()
            geotracker = settings.get_current_geotracker_item()
            geotracker.reload_precalc()
            return None

        progress, message = self._runner.current_progress()
        _log.output(f'precalc runner_state: {progress} {message}')
        analysing_screen_message(message, product=self.product)

        next_frame = self._runner.is_loading_frame_requested()
        if next_frame is None:
            return self._interval
        _log.output(f'loading_frame: {next_frame}')
        settings.user_percent = progress * 100
        current_frame = bpy_current_frame()

        if current_frame != next_frame:
            _log.output(f'NEXT FRAME IS NOT REACHED: {next_frame} current={current_frame}')
            self._target_frame = next_frame
            self.set_current_state(self.timeline_state)
            return self._interval

        geotracker = settings.get_current_geotracker_item()

        np_img = np_array_from_background_image(geotracker.camobj, index=0)
        if np_img is None:
            if not bpy_background_mode():
                msg = f'Cannot load image at frame: {current_frame}' \
                      f'\nPlease check your footage!'
                show_warning_dialog(msg)
                self.set_error_message(msg)
                self.set_current_state(self.finish_error_state)
                return self.current_state()

            # For testing purpose only
            _log.output('no np_img in bpy.app.background mode. try direct loading')
            bg_img = get_background_image_object(geotracker.camobj)
            if not bg_img or not bg_img.image:
                self.set_error_message('* Cannot load images 1')
                self.set_current_state(self.finish_error_state)
                return self.current_state()

            im_user = bg_img.image_user
            update_depsgraph()
            _log.output(f'bg_img.image.filepath: {bg_img.image.filepath}')
            path = bg_img.image.filepath_from_user(image_user=im_user)
            _log.output(f'user_path: {current_frame} {path}')

            try:
                img = bpy.data.images.load(path)
            except Exception as err:
                _log.error(f'runner_state load image Exception:\n{str(err)}')
                self.set_error_message('* Cannot load images 2')
                self.set_current_state(self.finish_error_state)
                return self.current_state()

            if not check_bpy_image_size(img):
                self.set_error_message('* Cannot load images 3')
                self.set_current_state(self.finish_error_state)
                return self.current_state()

            np_img = np_array_from_bpy_image(img)
            bpy.data.images.remove(img)

        self._runner.fulfill_loading_request(np_img[:, :, :3])
        return self._interval

    def start(self) -> bool:
        self._start_time = time.time()
        prepare_camera(self.get_area(), product=self.product)
        settings = self.get_settings()
        settings.calculating_mode = 'PRECALC'

        self.set_current_state(self.runner_state)
        # self._area_header('Precalc is calculating... Please wait')
        analysing_screen_message('Initialization', product=self.product)

        _func = self.timer_func
        if not bpy_background_mode():
            op = get_operator(self.interrupt_operator_name)
            op('INVOKE_DEFAULT')
            bpy_timer_register(_func, first_interval=self._interval)
            res = bpy.app.timers.is_registered(_func)
            _log.output(f'timer registered: {res}')
        else:
            timer = RepeatTimer(self._interval, _func)
            timer.start()
            res = True
        return res


def precalc_with_runner_act(context: Any, *, product: int) -> ActionStatus:
    check_status = common_checks(product=product, object_mode=True,
                                 is_calculating=True, reload_geotracker=True,
                                 geotracker=True, camera=True, movie_clip=True)
    if not check_status.success:
        return check_status

    settings = get_settings(product)
    geotracker = settings.get_current_geotracker_item()

    if geotracker.precalc_path == '':
        msg = 'Precalc path is not specified'
        _log.error(msg)
        return ActionStatus(False, msg)

    precalc_path = os.path.abspath(geotracker.precalc_path)
    _log.output(f'\nprecalc_path: {geotracker.precalc_path}\n'
                f'abs_path: {precalc_path}')

    dirpath, filename = os.path.split(precalc_path)
    try:
        os.makedirs(dirpath, exist_ok=True)
    except Exception as err:
        show_warning_dialog(f'An error occurred while trying '
                            f'to create a folder:\n{str(err)}')
        return ActionStatus(True, 'Folder access error')

    if not os.path.exists(dirpath) or not os.path.isdir(dirpath):
        return ActionStatus(False, 'Target folder cannot be created')

    if geotracker.precalc_start >= geotracker.precalc_end:
        return ActionStatus(False, 'Precalc start should be lower than precalc end')

    _log.output('precalc_with_runner_act start')
    vp = settings.loader().viewport()
    if not settings.pinmode:
        vp.texter().register_handler(context)

    rw, rh = bpy_render_frame()
    area = context.area
    runner = KTClassLoader.PrecalcRunner_class()(
        precalc_path, rw, rh,
        geotracker.precalc_start, geotracker.precalc_end,
        KTClassLoader.GeoTracker_class().license_manager(), True)

    pt = PrecalcTimer(area, runner, product=product)
    if pt.start():
        _log.output('Precalc started')
    else:
        return ActionStatus(False, 'Cannot start precalc timer')
    return ActionStatus(True, 'ok')
