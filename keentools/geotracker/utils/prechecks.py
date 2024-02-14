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
from ...addon_config import (Config,
                             get_settings,
                             get_operator,
                             ErrorType,
                             ActionStatus,
                             ProductType)
from ...utils.html import split_long_string
from ...utils.manipulate import exit_area_localview, switch_to_camera
from ...utils.bpy_common import (bpy_all_scene_objects,
                                 bpy_scene_selected_objects,
                                 bpy_background_mode)
from ...facebuilder.utils.manipulate import check_facs_available


_log = KTLogger(__name__)


def prepare_camera(area: Area, *,
                   product: int = ProductType.GEOTRACKER) -> None:
    settings = get_settings(product)
    geotracker = settings.get_current_geotracker_item()
    if not settings.pinmode:
        switch_to_camera(area, geotracker.camobj,
                         geotracker.animatable_object())
        settings.viewport_state.hide_ui_elements(area)

    geotracker.setup_background_image()
    geotracker.reload_background_image()


def revert_camera(area: Area, *,
                  product: int = ProductType.GEOTRACKER) -> None:
    settings = get_settings(product)
    if not settings.pinmode:
        settings.viewport_state.show_ui_elements(area)
        exit_area_localview(area)


def get_alone_object_in_selection_by_type(
        selection: List, obj_type: str = 'MESH') -> Optional[Object]:
    found_obj = None
    for obj in selection:
        if obj.type == obj_type:
            if found_obj is not None:
                return None
            found_obj = obj
    return found_obj


def get_alone_object_in_scene_by_type(
        obj_type: str = 'MESH') -> Optional[Object]:
    return get_alone_object_in_selection_by_type(bpy_all_scene_objects(),
                                                 obj_type)


def get_alone_object_in_scene_selection_by_type(
        obj_type: str = 'MESH') -> Optional[Object]:
    return get_alone_object_in_selection_by_type(bpy_scene_selected_objects(),
                                                 obj_type)


def get_alone_ft_object_in_selection(selection: List) -> Optional[Object]:
    obj_type = 'MESH'
    found_obj = None
    for obj in selection:
        if obj.type == obj_type and check_facs_available(len(obj.data.vertices)):
            if found_obj is not None:
                return None
            found_obj = obj
    return found_obj


def get_alone_ft_object_in_scene():
    return get_alone_ft_object_in_selection(bpy_all_scene_objects())


def get_alone_ft_object_in_scene_selection():
    return get_alone_ft_object_in_selection(bpy_scene_selected_objects())


def show_warning_dialog(err: Any, limit=70) -> None:
    _log.output('show_warning_dialog call')
    user_message = '\n'.join(split_long_string(str(err), limit=limit))
    if bpy_background_mode():
        _log.error(f'Warning operator is in background mode.\n{user_message}')
        return
    warn = get_operator(Config.kt_warning_idname)
    warn('INVOKE_DEFAULT', msg=ErrorType.CustomMessage,
         msg_content=user_message)


def show_unlicensed_warning() -> None:
    _log.output('show_unlicensed_warning call')
    warn = get_operator(Config.kt_warning_idname)
    warn('INVOKE_DEFAULT', msg=ErrorType.NoLicense)


def common_checks(*, object_mode: bool = False,
                  pinmode: bool = False,
                  pinmode_out: bool = False,
                  is_calculating: bool = False,
                  reload_geotracker: bool = False,
                  geotracker: bool = False,
                  camera: bool = False,
                  geometry: bool = False,
                  movie_clip: bool = False,
                  constraints: bool = False,
                  product: int = ProductType.GEOTRACKER) -> ActionStatus:

    if object_mode:
        if not hasattr(bpy.context, 'mode'):
            msg = 'Context has no mode attribute'
            _log.error(msg)
            return ActionStatus(False, msg)
        if bpy.context.mode != 'OBJECT':
            msg = 'This works only in OBJECT mode'
            _log.error(msg)
            return ActionStatus(False, msg)

    settings = get_settings(product)
    if is_calculating and settings.is_calculating():
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

    if reload_geotracker:
        if not settings.reload_current_geotracker():
            msg = 'Cannot load GeoTracker data'
            _log.error(msg)
            return ActionStatus(False, msg)
        settings.reload_mask_3d()

    geotracker_item = settings.get_current_geotracker_item()
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
    if constraints:
        if not geotracker_item.camobj:
            msg = 'GeoTracker does not contain Camera object!'
            _log.error(msg)
            return ActionStatus(False, msg)
        if len(geotracker_item.camobj.constraints) != 0:
            msg = 'Camera object has constraints!'
            _log.error(msg)
            return ActionStatus(False, msg)
        if not geotracker_item.geomobj:
            msg = 'GeoTracker does not contain Geometry object!'
            _log.error(msg)
            return ActionStatus(False, msg)
        if len(geotracker_item.geomobj.constraints) != 0:
            msg = 'Geometry object has constraints!'
            _log.error(msg)
            return ActionStatus(False, msg)
    return ActionStatus(True, 'Checks have been passed')


def track_checks(*, product: int) -> ActionStatus:
    check_status = common_checks(product=product,
                                 object_mode=True, pinmode=True,
                                 is_calculating=True, reload_geotracker=True,
                                 geotracker=True, camera=True, geometry=True)
    if not check_status.success:
        return check_status

    settings = get_settings(product)
    geotracker = settings.get_current_geotracker_item()

    if not geotracker.precalcless:
        status, msg, precalc_info = geotracker.reload_precalc()
        if not status or precalc_info is None:
            msg = 'Precalc has problems. Check it'
            _log.error(msg)
            return ActionStatus(False, msg)
    else:
        check_status = common_checks(product=product, movie_clip=True)
        if not check_status.success:
            return check_status

    return ActionStatus(True, 'ok')
