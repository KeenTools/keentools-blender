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

from typing import Optional, Any, List

from ..utils.kt_logging import KTLogger
from ..addon_config import (fb_settings,
                            calculation_in_progress,
                            ActionStatus)
from ..utils.bpy_common import bpy_context
from ..facebuilder.utils.manipulate import check_facs_available
from .fbloader import FBLoader


_log = KTLogger(__name__)


def common_fb_checks(*, object_mode: bool = False,
                     pinmode: bool = False,
                     pinmode_out: bool = False,
                     is_calculating: bool = False,
                     fix_facebuilders: bool = False,
                     reload_facebuilder: bool = False,
                     head_only: bool = False,
                     head_and_camera: bool = False,
                     headnum: Optional[int] = None,
                     camnum: Optional[int] = None) -> ActionStatus:
    if object_mode:
        context = bpy_context()
        if not hasattr(context, 'mode'):
            msg = 'Context has no mode attribute'
            _log.error(msg)
            return ActionStatus(False, msg)
        if context.mode != 'OBJECT':
            msg = 'This works only in OBJECT mode'
            _log.error(msg)
            return ActionStatus(False, msg)

    settings = fb_settings()
    if not settings:
        msg = 'No settings in common checks'
        _log.error(msg)
        return ActionStatus(False, msg)

    if is_calculating and calculation_in_progress():
        msg = 'Calculation in progress'
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

    if fix_facebuilders:
        if not settings.check_heads_and_cams():
            heads_deleted, cams_deleted = settings.fix_heads()
            if heads_deleted > 0 or cams_deleted > 0:
                msg = 'FaceBuilder structures have been fixed. Try again'
                _log.warning(msg)
                return ActionStatus(False, msg)
            msg = 'Scene seems damaged'
            _log.warning(msg)
            return ActionStatus(False, msg)

    if reload_facebuilder:
        hnum = headnum if headnum is not None else settings.current_headnum
        if not FBLoader.load_model(hnum):
            msg = 'Cannot load FaceBuilder data'
            _log.error(msg)
            return ActionStatus(False, msg)

    if head_and_camera or head_only:
        hnum = headnum if headnum is not None else settings.current_headnum
        head = settings.get_head(hnum)
        if not head:
            msg = 'No Head structure'
            _log.error(msg)
            return ActionStatus(False, msg)
        if not head.headobj:
            msg = 'No Head mesh in scene'
            _log.error(msg)
            return ActionStatus(False, msg)

        if head_and_camera:
            cnum = camnum if camnum is not None else settings.current_camnum
            camera = head.get_camera(cnum)
            if not camera:
                msg = 'No Camera structure'
                _log.error(msg)
                return ActionStatus(False, msg)
            if not camera.camobj:
                msg = 'No Camera object in scene'
                _log.error(msg)
                return ActionStatus(False, msg)

    return ActionStatus(True, 'Checks have been passed')
