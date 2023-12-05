# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2022-2023 KeenTools

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

from typing import Any

import bpy

from ..utils.kt_logging import KTLogger
from ..addon_config import ActionStatus

from ..geotracker.gtloader import GTLoader

from ..utils.bpy_common import (create_empty_object,
                                 bpy_current_frame,
                                 bpy_set_current_frame,
                                 update_depsgraph,
                                 reset_unsaved_animation_changes_in_frame,
                                 bpy_scene,
                                 bpy_render_single_frame,
                                 bpy_scene_selected_objects,
                                 bpy_active_object)
from ..blender_independent_packages.pykeentools_loader import module as pkt_module
from ..utils.manipulate import (select_object_only,
                                 select_objects_only,
                                 center_viewport,
                                 switch_to_mode)
from ..geotracker.utils.prechecks import (common_checks,
                        track_checks,
                        get_alone_object_in_scene_selection_by_type,
                        get_alone_object_in_scene_by_type,
                        prepare_camera,
                        revert_camera,
                        show_warning_dialog,
                        show_unlicensed_warning)
from .prechecks import common_checks_with_settings, track_checks_with_settings


_log = KTLogger(__name__)


def create_tracker_action(settings: Any) -> ActionStatus:
    _log.output('create_tracker_action start')
    check_status = common_checks_with_settings(settings, object_mode=True,
                                               pinmode_out=True,
                                               is_calculating=True)
    if not check_status.success:
        return check_status

    num = settings.add_geotracker_item()
    settings.current_geotracker_num = num
    settings.loader().new_kt_geotracker()

    selected_objects = bpy_scene_selected_objects()
    active_object = bpy_active_object()

    geotracker = settings.get_current_geotracker_item()
    obj = get_alone_object_in_scene_selection_by_type('MESH')
    if obj is None:
        obj = get_alone_object_in_scene_by_type('MESH')
    geotracker.geomobj = obj

    camobj = get_alone_object_in_scene_selection_by_type('CAMERA')
    if camobj is None:
        camobj = get_alone_object_in_scene_by_type('CAMERA')
    geotracker.camobj = camobj

    settings.reload_current_geotracker()

    select_objects_only(selected_objects)
    bpy_active_object(active_object)
    _log.output('create_tracker_action end')
    return ActionStatus(True, 'Tracker has been added')


def delete_tracker_action(settings: Any, geotracker_num: int) -> ActionStatus:
    check_status = common_checks_with_settings(settings, object_mode=True,
                                               pinmode_out=True,
                                               is_calculating=True)
    if not check_status.success:
        return check_status

    res = settings.remove_geotracker_item(geotracker_num)
    if not res:
        msg = 'Could not delete a Tracker'
        _log.error(msg)
        return ActionStatus(False, msg)
    settings.reload_current_geotracker()
    return ActionStatus(True, 'Tracker has been removed')


def select_tracker_objects_action(settings: Any, geotracker_num: int) -> ActionStatus:
    check_status = common_checks_with_settings(settings, object_mode=True,
                                               is_calculating=True,
                                               pinmode_out=True)
    if not check_status.success:
        return check_status

    settings.fix_geotrackers()
    if not settings.change_current_geotracker_safe(geotracker_num):
        return ActionStatus(False, f'Cannot switch to Geotracker '
                                   f'{geotracker_num}')

    geotracker = settings.get_current_geotracker_item()
    if not geotracker.geomobj and not geotracker.camobj:
        return ActionStatus(False, f'Geotracker {geotracker_num} '
                                   f'does not contain any objects')
    if geotracker.camera_mode():
        select_objects_only([geotracker.camobj, geotracker.geomobj])
    else:
        select_objects_only([geotracker.geomobj, geotracker.camobj])

    center_viewport(bpy.context.area)

    return ActionStatus(True, 'ok')
