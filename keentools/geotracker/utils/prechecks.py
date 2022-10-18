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

import bpy
from bpy.types import Object, Area

from ...utils.kt_logging import KTLogger
from ...addon_config import Config, get_operator, ErrorType, ActionStatus
from ...geotracker_config import get_gt_settings, get_current_geotracker_item
from ...utils.html import split_long_string
from ...utils.manipulate import exit_area_localview, switch_to_camera
from ...utils.other import (unhide_viewport_ui_elements_from_object,
                            hide_viewport_ui_elements_and_store_on_object)
from ...utils.images import set_background_image_by_movieclip


_log = KTLogger(__name__)


def prepare_camera(area: Area) -> None:
    settings = get_gt_settings()
    geotracker = settings.get_current_geotracker_item()
    if not settings.pinmode:
        switch_to_camera(area, geotracker.camobj,
                         geotracker.animatable_object())
        hide_viewport_ui_elements_and_store_on_object(area,
                                                      geotracker.camobj)
    set_background_image_by_movieclip(geotracker.camobj,
                                      geotracker.movie_clip)
    geotracker.reload_background_image()


def revert_camera(area: Area) -> None:
    settings = get_gt_settings()
    geotracker = settings.get_current_geotracker_item()
    if not settings.pinmode:
        unhide_viewport_ui_elements_from_object(area, geotracker.camobj)
        exit_area_localview(area)


def find_object_in_selection(obj_type: str='MESH',
                             selection: Optional[List]=None) -> Optional[Object]:
    def _get_any_alone_object(obj_type: str) -> Optional[Object]:
        all_objects = [obj for obj in bpy.data.objects if obj.type == obj_type]
        return None if len(all_objects) != 1 else all_objects[0]

    context_obj = bpy.context.object if hasattr(bpy.context, 'object') else None
    if context_obj and context_obj.type == obj_type:
        return context_obj
    if selection is not None:
        objects = selection
    else:
        if hasattr(bpy.context, 'selected_objects'):
            objects = bpy.context.selected_objects
        else:
            objects = []
    selected_objects = [obj for obj in objects if obj.type == obj_type]
    if len(selected_objects) == 1:
        return selected_objects[0]
    return None if selection is not None else _get_any_alone_object(obj_type)


def show_warning_dialog(err: Any, limit=70) -> None:
    _log.output('show_warning_dialog call')
    user_message = '\n'.join(split_long_string(str(err), limit=limit))
    warn = get_operator(Config.kt_warning_idname)
    warn('INVOKE_DEFAULT', msg=ErrorType.CustomMessage,
         msg_content=user_message)


def show_unlicensed_warning() -> None:
    _log.output('show_unlicensed_warning call')
    warn = get_operator(Config.kt_warning_idname)
    warn('INVOKE_DEFAULT', msg=ErrorType.NoLicense)


def common_checks(*, object_mode: bool=False,
                  pinmode: bool=False,
                  pinmode_out: bool=False,
                  is_calculating: bool=False,
                  reload_geotracker: bool = False,
                  geotracker: bool=False,
                  camera: bool=False,
                  geometry: bool=False,
                  movie_clip: bool=False) -> ActionStatus:

    if object_mode:
        if not hasattr(bpy.context, 'mode'):
            msg = 'Context has no mode attribute'
            _log.error(msg)
            return ActionStatus(False, msg)
        if bpy.context.mode != 'OBJECT':
            msg = 'This works only in OBJECT mode'
            _log.error(msg)
            return ActionStatus(False, msg)

    settings = get_gt_settings()
    if is_calculating and settings.is_calculating():
        msg = 'Calculation is performing'
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

    if reload_geotracker:
        if not settings.reload_current_geotracker():
            msg = 'Cannot load GeoTracker data'
            _log.error(msg)
            return ActionStatus(False, msg)
        settings.reload_mask_3d()

    geotracker_item = get_current_geotracker_item()
    if geotracker and not geotracker_item:
        msg = 'GeoTracker item is not found'
        _log.error(msg)
        return ActionStatus(False, msg)
    if camera and not geotracker_item.camobj:
        msg = 'GeoTracker camera is not found'
        _log.error(msg)
        return ActionStatus(False, msg)
    if geometry and not geotracker_item.geomobj:
        msg = 'GeoTracker geometry is not found'
        _log.error(msg)
        return ActionStatus(False, msg)
    if movie_clip and not geotracker_item.movie_clip:
        msg = 'GeoTracker movie clip is not found'
        _log.error(msg)
        return ActionStatus(False, msg)
    return ActionStatus(True, 'Checks have been passed')


def track_checks() -> ActionStatus:
    check_status = common_checks(object_mode=True, pinmode=True,
                                 is_calculating=True, reload_geotracker=True,
                                 geotracker=True, camera=True, geometry=True)
    if not check_status.success:
        return check_status

    settings = get_gt_settings()
    geotracker = settings.get_current_geotracker_item()

    if not geotracker.precalcless:
        status, msg, precalc_info = geotracker.reload_precalc()
        if not status or precalc_info is None:
            msg = 'Precalc has problems. Check it'
            _log.error(msg)
            return ActionStatus(False, msg)
    else:
        check_status = common_checks(movie_clip=True)
        if not check_status.success:
            return check_status

    return ActionStatus(True, 'ok')
