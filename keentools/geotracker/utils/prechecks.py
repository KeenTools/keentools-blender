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
                             calculation_in_progress,
                             tool_pinmode,
                             stop_fb_pinmode,
                             stop_gt_pinmode,
                             stop_ft_pinmode,
                             ErrorType,
                             ActionStatus,
                             ProductType,
                             product_name)
from ...utils.html import split_long_string
from ...utils.manipulate import exit_area_localview, switch_to_camera
from ...utils.bpy_common import (bpy_all_scene_objects,
                                 bpy_scene_selected_objects,
                                 bpy_background_mode,
                                 bpy_context)
from ...facebuilder.utils.manipulate import check_facs_available


_log = KTLogger(__name__)


def prepare_camera(area: Area, *, product: int) -> None:
    _log.yellow(f'prepare_camera product={product} start')
    settings = get_settings(product)
    geotracker = settings.get_current_geotracker_item()
    if not settings.pinmode:
        switch_to_camera(area, geotracker.camobj,
                         geotracker.animatable_object())
        settings.viewport_state.hide_ui_elements(area)

    geotracker.setup_background_image()
    geotracker.reload_background_image()
    _log.output('prepare_camera end >>>')


def revert_camera(area: Area, *, product: int) -> None:
    _log.yellow(f'revert_camera product={product} start')
    settings = get_settings(product)
    if not settings.pinmode:
        settings.viewport_state.show_ui_elements(area)
        exit_area_localview(area)
    _log.output('revert_camera end >>>')


def get_alone_object_in_selection_by_type(*,
        selection: List, obj_type: str, exclude_list: List) -> Optional[Object]:
    found_obj = None
    for obj in selection:
        if obj in exclude_list:
            continue
        if obj.type == obj_type:
            if found_obj is not None:
                return None
            found_obj = obj
    return found_obj


def get_alone_object_in_scene_by_type(
        obj_type: str, exclude_list: List) -> Optional[Object]:
    return get_alone_object_in_selection_by_type(
        selection=bpy_all_scene_objects(), obj_type=obj_type,
        exclude_list=exclude_list)


def get_alone_object_in_scene_selection_by_type(
        obj_type: str, exclude_list: List) -> Optional[Object]:
    return get_alone_object_in_selection_by_type(
        selection=bpy_scene_selected_objects(), obj_type=obj_type,
        exclude_list=exclude_list)


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
    _log.yellow('show_warning_dialog start')
    user_message = '\n'.join(split_long_string(str(err), limit=limit))
    if bpy_background_mode():
        _log.error(f'Warning operator is in background mode.\n{user_message}')
        return

    warn = get_operator(Config.kt_warning_idname)

    if not bpy_context().window:
        _log.error(f'\nCannot output warning: No window object in context\n'
                   f'{user_message}')
        return

    warn('INVOKE_DEFAULT', msg=ErrorType.CustomMessage,
         msg_content=user_message)
    _log.output('show_warning_dialog end >>>')


def common_checks(*, object_mode: bool = False,
                  pinmode: bool = False,
                  pinmode_out: bool = False,
                  stop_other_pinmode: bool = False,
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
    if is_calculating:
        calc_status = calculation_in_progress()
        if not calc_status.success:
            _log.error(calc_status.error_message)
            return calc_status
    if pinmode and not settings.pinmode:
        msg = 'This operation works only in Pinmode'
        _log.error(msg)
        return ActionStatus(False, msg)
    if pinmode_out and settings.pinmode:
        msg = 'This operation does not work in Pinmode'
        _log.error(msg)
        return ActionStatus(False, msg)

    if stop_other_pinmode:
        pm = tool_pinmode(facebuilder=True, geotracker=True, facetracker=True)
        if pm is not None:
            if pm == ProductType.FACEBUILDER:
                if pm != product:
                    stop_fb_pinmode()
                    msg = 'FaceBuilder interactive mode stopped'
                    _log.warning(msg)
                    _log.output(f'{pm} != {product}')
                    return ActionStatus(False, msg)
            elif pm == ProductType.GEOTRACKER:
                if pm != product:
                    stop_gt_pinmode()
                    msg = 'GeoTracker interactive mode stopped'
                    _log.warning(msg)
                    _log.output(f'{pm} != {product}')
                    return ActionStatus(False, msg)
            elif pm == ProductType.FACETRACKER:
                if pm != product:
                    stop_ft_pinmode()
                    msg = 'FaceTracker interactive mode stopped'
                    _log.warning(msg)
                    _log.output(f'{pm} != {product}')
                    return ActionStatus(False, msg)
            else:
                msg = f'Unknown product type in common check [{pm}]'
                _log.error(msg)
                return ActionStatus(False, msg)

    if reload_geotracker:
        if not settings.reload_current_geotracker():
            msg = f'Cannot load {product_name(product)} data'
            _log.error(msg)
            return ActionStatus(False, msg)
        settings.reload_mask_3d()

    geotracker_item = settings.get_current_geotracker_item()
    if geotracker and not geotracker_item:
        msg = f'{product_name(product)} item is not found'
        _log.error(msg)
        return ActionStatus(False, msg)
    if camera and not geotracker_item.camobj:
        msg = f'{product_name(product)} camera is not found'
        _log.error(msg)
        return ActionStatus(False, msg)
    if geometry and not geotracker_item.geomobj:
        msg = f'{product_name(product)} geometry is not found'
        _log.error(msg)
        return ActionStatus(False, msg)
    if movie_clip and not geotracker_item.movie_clip:
        msg = f'{product_name(product)} movie clip is not found'
        _log.error(msg)
        return ActionStatus(False, msg)
    if constraints:
        if not geotracker_item.camobj:
            msg = f'{product_name(product)} does not contain Camera object!'
            _log.error(msg)
            return ActionStatus(False, msg)
        if len(geotracker_item.camobj.constraints) != 0:
            msg = 'Camera object has constraints!'
            _log.error(msg)
            return ActionStatus(False, msg)
        if not geotracker_item.geomobj:
            msg = f'{product_name(product)} does not contain Geometry object!'
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
            msg = 'Analyse clip before tracking!'
            _log.error(msg)
            return ActionStatus(False, msg)
    else:
        check_status = common_checks(product=product, movie_clip=True)
        if not check_status.success:
            return check_status

    return ActionStatus(True, 'ok')
