# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2019  KeenTools

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

from typing import Optional, Dict, List

import bpy
from bpy.types import Object, Area

from .kt_logging import KTLogger
from .coords import get_area_region
from .localview import (enter_area_localview,
                        exit_area_localview,
                        check_area_active_problem)
from .ui_redraw import get_areas_by_type
from .bpy_common import operator_with_context, bpy_background_mode


_log = KTLogger(__name__)


def has_no_blendshape(obj: Optional[Object]) -> bool:
    return not obj or obj.type != 'MESH' or not obj.data or \
           not obj.data.shape_keys


def has_blendshapes_action(obj: Optional[Object]) -> bool:
    if obj and obj.type == 'MESH' \
           and obj.data.shape_keys \
           and obj.data.shape_keys.animation_data \
           and obj.data.shape_keys.animation_data.action:
        return True
    return False


def force_undo_push(msg: str = 'KeenTools operation') -> None:
    _log.magenta(f'force_undo_push: {msg}')
    bpy.ops.ed.undo_push(message=msg)


def deselect_all():
    bpy.ops.object.select_all(action='DESELECT')


def object_is_on_view_layer(obj: Object) -> bool:
    return obj in bpy.context.view_layer.objects[:]


def switch_to_mode(mode: str = 'OBJECT') -> None:
    bpy.ops.object.mode_set(mode=mode, toggle=False)


def switch_to_object_mode() -> None:
    switch_to_mode(mode='OBJECT')


def switch_to_edit_mode() -> None:
    switch_to_mode(mode='EDIT')


def switch_to_pose_mode() -> None:
    switch_to_mode(mode='POSE')


def select_object_only(obj: Optional[Object]) -> None:
    _log.yellow(f'select_object_only: {obj}')
    if not obj:
        return
    if bpy.context.mode != 'OBJECT':
        switch_to_object_mode()
    deselect_all()
    if object_is_on_view_layer(obj):
        _log.output('object_is_on_view_layer')
        obj.select_set(state=True)
        bpy.context.view_layer.objects.active = obj


def get_vertex_groups(obj: Object) -> Dict:
    vertices = obj.data.vertices
    vertex_groups = [x for x in obj.vertex_groups]
    vg_dict = {}
    for vg in vertex_groups:
        vg_dict[vg.name] = [[v.index, vg.weight(v.index)]
                            for v in vertices
                            if vg.index in [g.group for g in v.groups]]
    return vg_dict


def create_vertex_groups(obj: Object, vg_dict: Dict) -> None:
    for vg_name in vg_dict.keys():
        if vg_name in obj.vertex_groups.keys():
            vg = obj.vertex_groups[vg_name]
        else:
            vg = obj.vertex_groups.new(name=vg_name)
        for i, w in vg_dict[vg_name]:
            vg.add([i], w, 'REPLACE')


def switch_to_camera(area: Area, camobj: Object,
                     select_obj: Optional[Object]=None) -> None:
    _log.yellow(f'switch_to_camera: area={area}'
                f'\ncamobj={camobj}'
                f'\nselect_obj={select_obj}')
    exit_area_localview(area)
    if camobj:
        camobj.hide_set(False)
        select_object_only(camobj)
    enter_area_localview(area)

    # Low-level code instead bpy.ops.view3d.object_as_camera()
    if not check_area_active_problem(area):
        area.spaces.active.camera = camobj
        if area.spaces.active.region_3d:
            area.spaces.active.region_3d.view_perspective = 'CAMERA'

    if select_obj is not None:
        select_object_only(select_obj)


def center_viewport(area, window=None):
    _log.yellow('center_viewport start')
    override_context = {'window': bpy.context.window if window is None else window,
                        'area': area,
                        'region': get_area_region(area)}
    operator_with_context(bpy.ops.view3d.view_selected,
                          override_context,
                          use_all_regions=True)
    _log.output('center_viewport end >>>')


def center_viewports_on_object(obj: Optional[Object]=None) -> None:
    _log.yellow('center_viewports_on_object start')
    if obj is not None:
        select_object_only(obj)
    if bpy_background_mode():
        _log.output('center_viewports_on_object background mode end >>>')
        return

    pairs = get_areas_by_type(area_type='VIEW_3D')
    for area, window in pairs:
        _log.output(area)
        center_viewport(area, window=window)
    _log.output('center_viewports_on_object end >>>')


def select_objects_only(obj_list: List[Object]) -> None:
    _log.yellow('select_objects_only start')
    deselect_all()
    selected = -1
    for i, obj in enumerate(obj_list):
        if obj:
            obj.select_set(state=True)
            if selected < 0:
                selected = i
    if len(obj_list) > 0 and selected >=0:
        bpy.context.view_layer.objects.active = obj_list[selected]
    _log.output('select_objects_only end >>>')
