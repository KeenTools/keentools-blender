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
from dataclasses import dataclass
from typing import Optional
import bpy
from bpy.types import Object

from ...addon_config import get_operator
from ...geotracker_config import GTConfig, get_gt_settings
from ..gtloader import GTLoader
from ...utils.manipulate import switch_to_camera
from ...utils.other import hide_viewport_ui_elements_and_store_on_object


@dataclass(frozen=True)
class ActionStatus:
    success: bool = False
    error_message: str = None


def find_object_in_selection(obj_type: str='MESH',
                             selection: Optional[list]=None) -> Optional[Object]:
    def _get_any_alone_object(obj_type: str) -> Optional[Object]:
        all_objects = [obj for obj in bpy.data.objects if obj.type == obj_type]
        return None if len(all_objects) != 1 else all_objects[0]

    context_obj = bpy.context.object
    if context_obj and context_obj.type == obj_type:
        return context_obj
    objects = bpy.context.selected_objects if selection is None else selection
    selected_objects = [obj for obj in objects if obj.type == obj_type]
    if len(selected_objects) == 1:
        return selected_objects[0]
    return None if selection is not None else _get_any_alone_object(obj_type)


def create_geotracker_act() -> int:
    settings = get_gt_settings()
    num = settings.add_geotracker_item()
    settings.current_geotracker_num = num
    GTLoader.new_kt_geotracker()
    geotracker = settings.get_current_geotracker_item()
    obj = find_object_in_selection('MESH')
    if obj is not None:
        geotracker.geomobj = obj
    camobj = find_object_in_selection('CAMERA')
    if camobj is not None:
        geotracker.camobj = camobj
    else:
        camobj = bpy.context.scene.camera
        if camobj:
            geotracker.camobj = camobj
    return num


def enter_pinmode_act() -> ActionStatus:
    logger = logging.getLogger(__name__)
    settings = get_gt_settings()
    geotracker = settings.get_current_geotracker_item()
    if not geotracker:
        return ActionStatus(False, 'No geotracker')

    if not geotracker.geomobj:
        return ActionStatus(False, 'No geometry in geotracker')

    if geotracker.geomobj.mode != 'OBJECT':
        return ActionStatus(False, 'Geometry should be in OBJECT mode')

    if not GTLoader.load_geotracker():
        logger.debug('NEW GEOTRACKER')
        GTLoader.new_kt_geotracker()
        GTLoader.save_geotracker()

    if geotracker.camobj:
        GTLoader.place_camera()
        switch_to_camera(bpy.context, geotracker.camobj,
                         geotracker.animatable_object())
        hide_viewport_ui_elements_and_store_on_object(geotracker.geomobj)

        # set_background_image_by_movieclip(geotracker.camobj, geotracker.movie_clip)

        pinmode_op = get_operator(GTConfig.gt_pinmode_idname)
        if not bpy.app.background:
            pinmode_op('INVOKE_DEFAULT')
    return ActionStatus(True, 'Ok')
