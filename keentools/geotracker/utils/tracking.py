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
from dataclasses import dataclass
from typing import Tuple, Optional, Any

from ...utils.coords import render_frame
from ...blender_independent_packages.pykeentools_loader import module as pkt_module


@dataclass(frozen=True)
class PrecalcStatus:
    success: bool = False
    error_message: str = None


def get_precalc_info(precalc_path: str) -> Tuple[Optional[Any], str]:
    logger = logging.getLogger(__name__)
    log_error = logger.error
    try:
        loader = pkt_module().precalc.Loader(precalc_path)
        precalc_info = loader.load_info()
        w = precalc_info.image_w
        h = precalc_info.image_h
        if not isinstance(w, int) or not isinstance(h, int):
            msg = 'Problem with precalc image size'
            log_error(msg)
            return None, msg
        if w <= 0 or h <= 0:
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


def check_precalc(precalc_path: str,
                  frame_from: Optional[int]=None,
                  frame_to: Optional[int]=None) -> Tuple[bool, str]:
    logger = logging.getLogger(__name__)
    log_error = logger.error
    precalc_info, msg = get_precalc_info(precalc_path)
    if precalc_info is None:
        return False, 'Precalc is damaged'

    if frame_from is not None and frame_to is not None:
        if (not precalc_info.left_precalculated_frame <= frame_from <=
                precalc_info.right_precalculated_frame) or \
                (not precalc_info.left_precalculated_frame <= frame_to <=
                     precalc_info.right_precalculated_frame):
            msg = 'Frames are not in precalculated range'
            log_error(msg)
            return False, msg

    rw, rh = render_frame()
    if rw != precalc_info.image_w or rh != precalc_info.image_h:
        msg = 'Render size differs from precalculated'
        log_error(msg)
        return False, msg

    return True, 'ok'


def reload_precalc(geotracker: Any) -> Tuple[bool, str]:
    precalc_path = geotracker.precalc_path
    if os.path.exists(precalc_path):
        precalc_info, msg = get_precalc_info(precalc_path)
        if precalc_info is None:
            geotracker.precalc_message = '* Precalc file is corrupted'
            return False, 'Warning! Precalc file seems corrupted'
        else:
            geotracker.precalc_message = get_precalc_message(precalc_info)
    else:
        geotracker.precalc_message = '* Precalc needs to be built'
        geotracker.precalc_path = precalc_path
    return True, 'ok'
