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
import os
from typing import Tuple, Optional, Any, Callable

import bpy

from ...addon_config import get_operator
from ...geotracker_config import GTConfig, get_gt_settings
from ...utils.coords import render_frame
from ...blender_independent_packages.pykeentools_loader import module as pkt_module


class PreviewTimer:
    def __init__(self, from_frame: int=-1, to_frame: int=-1):
        self._interval: float = 0.02
        self._target_frame: int = -1
        self._state: str = 'none'
        self._active_state_func: Callable = self.timeline_state
        self._from_frame: int = from_frame
        self._to_frame: int = to_frame
        self._step = 1 if from_frame <= to_frame else -1

    def timeline_state(self) -> Optional[float]:
        logger = logging.getLogger(__name__)
        log_output = logger.info
        settings = get_gt_settings()
        if settings.user_interrupts:
            return None  # Finish
        if settings.current_frame() == self._target_frame:
            if self._target_frame == self._to_frame:
                return None  # Finish
            self._target_frame += self._step
            return self._interval
        settings.set_current_frame(self._target_frame)
        log_output(f'Preview command: set_current_frame({self._target_frame})')
        return self._interval

    def timer_func(self) -> Optional[float]:
        return self._active_state_func()

    def start(self) -> None:
        self._target_frame = self._from_frame
        self._state = 'timeline'
        self._active_state_func = self.timeline_state
        op = get_operator(GTConfig.gt_interrupt_modal_idname)
        op('INVOKE_DEFAULT')
        bpy.app.timers.register(self.timer_func, first_interval=self._interval)


def get_precalc_info(precalc_path: str) -> Tuple[Optional[Any], str]:
    logger = logging.getLogger(__name__)
    log_error = logger.error
    try:
        loader = pkt_module().precalc.Loader(precalc_path)
        precalc_info = loader.load_info()
        if precalc_info.image_w <= 0 or precalc_info.image_h <= 0:
            msg = 'Wrong precalc image size'
            log_error(msg)
            return None, msg
        left = precalc_info.left_precalculated_frame
        right = precalc_info.right_precalculated_frame
        if not isinstance(left, int) or not isinstance(right, int):
            msg = 'Problem with frame indices'
            log_error(msg)
            return None, msg
        if left <= 0 or right <= 0 or right < left:
            msg = 'Wrong frame indices'
            log_error(msg)
            return None, msg
    except pkt_module().precalc.PrecalcLoadingException:
        msg = 'Precalc is damaged'
        log_error(msg)
        return None, msg
    except Exception as err:
        msg = str(err)
        log_error(msg)
        return None, msg
    return precalc_info, 'ok'


def get_precalc_message(precalc_info: Any) -> str:
    return f'Frame size: {precalc_info.image_w}x{precalc_info.image_h}\n' \
           f'Frames from: {precalc_info.left_precalculated_frame} ' \
           f'to {precalc_info.right_precalculated_frame}'


def check_precalc(precalc_info: Any,
                  frame_from: Optional[int]=None,
                  frame_to: Optional[int]=None) -> Tuple[bool, str]:
    logger = logging.getLogger(__name__)
    log_error = logger.error

    left = precalc_info.left_precalculated_frame
    right = precalc_info.right_precalculated_frame
    if frame_from is not None and frame_to is not None:
        if (not left <= frame_from <= right) or \
                (not left <= frame_to <= right):
            msg = 'Frames are not in precalculated range'
            log_error(msg)
            return False, msg

    rw, rh = render_frame()
    if rw != precalc_info.image_w or rh != precalc_info.image_h:
        msg = 'Render size differs from precalculated'
        log_error(msg)
        return False, msg

    return True, 'ok'


def reload_precalc(geotracker: Any) -> Tuple[bool, str, Any]:
    precalc_path = geotracker.precalc_path
    if os.path.exists(precalc_path):
        precalc_info, msg = get_precalc_info(precalc_path)
        if precalc_info is None:
            geotracker.precalc_message = '* Precalc file is corrupted'
            return False, 'Warning! Precalc file seems corrupted', None
        else:
            geotracker.precalc_message = get_precalc_message(precalc_info)
            return True, 'ok', precalc_info

    geotracker.precalc_message = '* Precalc needs to be built'
    geotracker.precalc_path = precalc_path
    return True, 'Precalc file has not created yet', None


def get_next_tracking_keyframe(kt_geotracker: Any, current_frame: int) -> int:
    keyframes = kt_geotracker.keyframes()
    next_keyframes = [x for x in filter(lambda i: i > current_frame, keyframes)]
    if len(next_keyframes) > 0:
        return next_keyframes[0]
    else:
        return current_frame


def get_previous_tracking_keyframe(kt_geotracker: Any, current_frame: int) -> int:
    keyframes = kt_geotracker.keyframes()
    prev_keyframes = [x for x in filter(lambda i: i < current_frame, keyframes)]
    if len(prev_keyframes) > 0:
        return prev_keyframes[-1]
    else:
        return current_frame
