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

import math
import numpy as np
import os
from typing import Any, List, Optional, Tuple, Dict

import bpy
from bpy.types import Object, Action, FCurve

from .fcurve_operations import *
from .kt_logging import KTLogger
from ..addon_config import Config, get_operator, ErrorType
from ..utils.bpy_common import operator_with_context, extend_scene_timeline_end
from ..facebuilder_config import FBConfig
from ..utils.rig_slider import create_slider, create_rectangle, create_label
from ..utils.coords import (xy_to_xz_rotation_matrix_3x3,
                            xz_to_xy_rotation_matrix_3x3)
from ..utils.manipulate import deselect_all
from ..blender_independent_packages.pykeentools_loader import module as pkt_module


_log = KTLogger(__name__)


def get_blendshape(obj: Object, name: str = '', *,
                   create_basis: bool = False,
                   create: bool = False) -> Tuple[int, Optional[Any], bool]:
    '''
    :return: shape_index, shape, created_flag
    '''
    if not obj.data.shape_keys:
        if create_basis:
            basis = obj.shape_key_add(name='Basis')
            if name == 'Basis':
                return 0, basis, True
        else:
            return -1, None, False

    index = obj.data.shape_keys.key_blocks.find(name)
    if index < 0:
        if not create:
            return -1, None, False
        shape = obj.shape_key_add(name=name)
        index = obj.data.shape_keys.key_blocks.find(name)
        return index, shape, True
    else:
        shape = obj.data.shape_keys.key_blocks[index]

    return index, shape, False


def _has_no_blendshapes(obj: Object) -> bool:
    return not obj.data.shape_keys


def has_blendshapes_action(obj: Object) -> bool:
    return obj.data.shape_keys and obj.data.shape_keys.animation_data and \
           obj.data.shape_keys.animation_data.action


def _create_basis_blendshape(obj: Object) -> None:
    if _has_no_blendshapes(obj):
        obj.shape_key_add(name='Basis')


def _get_all_blendshape_names(obj: Object) -> List[str]:
    if _has_no_blendshapes(obj):
        return []
    res = [kb.name for kb in obj.data.shape_keys.key_blocks]
    return res[1:]


def _get_safe_blendshapes_action(
        obj: Object, action_name: str = FBConfig.default_blendshapes_action_name) -> Optional[Any]:
    if _has_no_blendshapes(obj):
        return None
    animation_data = obj.data.shape_keys.animation_data
    if not animation_data:
        animation_data = obj.data.shape_keys.animation_data_create()
        if not animation_data:
            return None
    if not animation_data.action:
        animation_data.action = \
            bpy.data.actions.new(action_name)
    return animation_data.action


def remove_blendshapes(obj: Object) -> None:
    if _has_no_blendshapes(obj):
        return
    for blendshape in reversed([kb for kb in obj.data.shape_keys.key_blocks]):
        obj.shape_key_remove(blendshape)


def disconnect_blendshapes_action(obj: Object) -> Optional[Action]:
    if has_blendshapes_action(obj):
        action = obj.data.shape_keys.animation_data.action
        obj.data.shape_keys.animation_data.action = None
        obj.data.update()
        return action
    return None


def zero_all_blendshape_weights(obj: Object) -> int:
    if _has_no_blendshapes(obj):
        return -1
    counter = 0
    for kb in obj.data.shape_keys.key_blocks[1:]:
        kb.value = 0
        counter += 1
    return counter


def _get_obj_verts(obj: Object) -> Any:
    assert obj.type == 'MESH'
    mesh = obj.data
    verts = np.empty((len(mesh.vertices), 3), dtype=np.float32)
    mesh.vertices.foreach_get('co', np.reshape(verts, len(mesh.vertices) * 3))
    return verts @ xz_to_xy_rotation_matrix_3x3()


def _get_facs_executor(obj: Object, scale: float) -> Optional[Any]:
    verts = _get_obj_verts(obj)

    try:
        fe = pkt_module().FacsExecutor(verts, scale)
    except pkt_module().FacsLoadingException as err:
        _log.error(f'CANNOT_LOAD_FACS: FacsLoadingException\n{str(err)}')
        return None
    except Exception as err:
        _log.error(f'CANNOT_LOAD_FACS: Unknown Exception\n{str(err)}')
        return None
    if not fe.facs_enabled():
        _log.error('CANNOT_LOAD_FACS: FACS are not enabled')
        return None
    return fe


def _update_blendshape_verts(shape: Any, verts: Any) -> None:
    shape.data.foreach_set(
        'co', (verts @ xy_to_xz_rotation_matrix_3x3()).ravel())


def create_facs_blendshapes(obj: Object, scale: float) -> int:
    facs_executor = _get_facs_executor(obj, scale)
    if not facs_executor:
        return -1

    _create_basis_blendshape(obj)
    counter = 0
    for i, name in enumerate(facs_executor.facs_names):
        if obj.data.shape_keys.key_blocks.find(name) < 0:
            shape = obj.shape_key_add(name=name)
            verts = facs_executor.get_facs_blendshape(i)
            _update_blendshape_verts(shape, verts)
            counter += 1
    return counter


def update_facs_blendshapes(obj: Object, scale: float) -> int:
    assert not _has_no_blendshapes(obj)
    facs_executor = _get_facs_executor(obj, scale)
    if not facs_executor:
        return -1

    counter = 0
    for i, name in enumerate(facs_executor.facs_names):
        index = obj.data.shape_keys.key_blocks.find(name)
        if index >= 0:
            shape = obj.data.shape_keys.key_blocks[index]
            verts = facs_executor.get_facs_blendshape(i)
            _update_blendshape_verts(shape, verts)
            counter += 1
    obj.data.update()
    return counter


def restore_facs_blendshapes(obj: Object, scale: float,
                             restore_names: List[str]) -> int:
    _create_basis_blendshape(obj)
    facs_executor = _get_facs_executor(obj, scale)
    if not facs_executor:
        return -1

    counter = 0
    for i, name in enumerate(facs_executor.facs_names):
        if obj.data.shape_keys.key_blocks.find(name) < 0 \
                and (name in restore_names):
            shape = obj.shape_key_add(name=name)
            verts = facs_executor.get_facs_blendshape(i)
            _update_blendshape_verts(shape, verts)
            counter += 1
    obj.data.update()
    return counter


def _cleanup_interval(start_keyframe: float, end_keyframe: float):
    return min(start_keyframe, round(start_keyframe)), end_keyframe


def _animation_interval(start_keyframe: float,
                        end_keyframe: float) -> Tuple[int, int]:
    return round(start_keyframe), math.floor(end_keyframe)


def _cleanup_keys_in_interval(fcurve: FCurve, start_keyframe: float,
                              end_keyframe: float) -> None:
    for p in reversed(fcurve.keyframe_points):
        if start_keyframe <= p.co[0] <= end_keyframe:
            fcurve.keyframe_points.remove(p)
    fcurve.update()


def _add_zero_keys_at_start_and_end(fcurve: FCurve, start_keyframe: float,
                                    end_keyframe: float) -> None:
    left_keyframe, right_keyframe = _animation_interval(start_keyframe,
                                                        end_keyframe)
    anim_data = [(left_keyframe, 0), (right_keyframe,0)]
    put_anim_data_in_fcurve(fcurve, anim_data)


def _snap_keys_in_interval(fcurve: FCurve, start_keyframe: float,
                           end_keyframe: float) -> None:
    anim_data = [(x, fcurve.evaluate(x)) for x in
                 range(*_animation_interval(start_keyframe, end_keyframe))]
    _cleanup_keys_in_interval(fcurve, *_cleanup_interval(start_keyframe,
                                                         end_keyframe))
    put_anim_data_in_fcurve(fcurve, anim_data)


def load_csv_animation_to_blendshapes(obj: Object, filepath: str) -> Dict:
    try:
        _log.info(f'LOADING CSV FILE: {filepath}')
        fan = pkt_module().FacsAnimation()
        read_facs, ignored_columns = fan.load_from_csv_file(filepath)
        facs_names = pkt_module().FacsExecutor.facs_names
    except pkt_module().FacsLoadingException as err:
        _log.error(f'CANNOT_LOAD_CSV_ANIMATION:\n{str(err)}')
        return {'status': False, 'message': str(err),
                'ignored': [], 'read_facs': []}
    except pkt_module().UnlicensedException as err:
        _log.error(f'UnlicensedException load_csv_animation_to_blendshapes:\n'
                   f'{str(err)}')
        warn = get_operator(Config.kt_warning_idname)
        warn('INVOKE_DEFAULT', msg=ErrorType.NoLicense)
        # status=True in result for non-conflict operator report as {'INFO'}
        return {'status': True, 'message': 'No FaceBuilder license',
                'ignored': [], 'read_facs': []}
    except Exception as err:
        _log.error(f'CANNOT_LOAD_CSV_ANIMATION!:\n{str(err)}')
        return {'status': False, 'message': str(err),
                'ignored': [], 'read_facs': []}

    action_name = os.path.splitext(os.path.basename(filepath))[0]
    blendshapes_action = _get_safe_blendshapes_action(obj, action_name)

    scene = bpy.context.scene
    fps = scene.render.fps
    start = scene.frame_current
    if not fan.timecodes_enabled():
        fps = 1
    keyframes = [start + x * fps for x in fan.keyframes()]
    if len(keyframes) > 0:
        start_keyframe = keyframes[0]
        end_keyframe = keyframes[-1]
    else:
        start_keyframe = 0
        end_keyframe = -1

    for name in facs_names:
        blendshape_fcurve = get_safe_action_fcurve(
            blendshapes_action, 'key_blocks["{}"].value'.format(name), index=0)
        _cleanup_keys_in_interval(blendshape_fcurve,
                                  start_keyframe, end_keyframe)
        if name in read_facs:
            anim_data = [x for x in zip(keyframes, fan.at_name(name))]
            put_anim_data_in_fcurve(blendshape_fcurve, anim_data)
            _snap_keys_in_interval(blendshape_fcurve,
                                   start_keyframe, end_keyframe)
        else:
            _add_zero_keys_at_start_and_end(blendshape_fcurve,
                                            start_keyframe, end_keyframe)
    obj.data.update()
    if len(keyframes) > 0:
        extend_scene_timeline_end(int(keyframes[-1]))

    _log.info(f'FACS CSV-Animation file: {filepath}')
    _log.info(f'Timecodes enabled: {fan.timecodes_enabled()}')
    if len(ignored_columns) > 0:
        _log.info(f'Ignored columns: {ignored_columns}')
    if len(read_facs) > 0:
        _log.info('Read facs: {read_facs}')
    return {'status': True, 'message': 'Loaded animation.',
            'ignored': ignored_columns, 'read_facs': read_facs}


def create_facs_test_animation_on_blendshapes(obj: Object,
                                              start_time: float=1,
                                              dtime: float=4) -> int:
    if _has_no_blendshapes(obj):
        return -1
    counter = 0
    blendshapes_action = _get_safe_blendshapes_action(
        obj, FBConfig.example_animation_action_name)
    time = start_time
    for kb in obj.data.shape_keys.key_blocks[1:]:
        blendshape_fcurve = get_safe_action_fcurve(
            blendshapes_action,
            'key_blocks["{}"].value'.format(kb.name),
            index=0)
        anim_data = [(time, 0.0), (time + dtime, 1.0), (time + 2 * dtime, 0)]
        time += dtime * 2
        put_anim_data_in_fcurve(blendshape_fcurve, anim_data)
        counter += 1
    obj.data.update()
    extend_scene_timeline_end(int(time))
    return counter


def _create_driver(target: Any, control_obj: Object, driver_name: str,
                   control_prop: str = 'location.x') -> Any:
    res = target.driver_add('value')
    res.driver.type = 'AVERAGE'
    drv_var = res.driver.variables.new()
    drv_var.name = driver_name
    drv_var.type = 'SINGLE_PROP'
    drv_var.targets[0].id = control_obj
    drv_var.targets[0].data_path = control_prop
    return res


def create_blendshape_controls(obj: Object) -> Dict:
    if _has_no_blendshapes(obj):
        return {}
    blendshape_names = _get_all_blendshape_names(obj)
    controls = {}
    for name in blendshape_names:
        slider_dict = create_slider(name, name, width=1.0, height=0.2)
        driver = _create_driver(obj.data.shape_keys.key_blocks[name],
                                slider_dict['slider'],
                                FBConfig.default_driver_name, 'location.x')
        controls[name] = {'control': slider_dict, 'driver': driver}
    return controls


def make_control_panel(controls_dict: Dict) -> Object:
    count = len(controls_dict)
    columns_count = 4
    max_in_column = (count + columns_count - 1) // columns_count

    width = 1.0
    height = 0.2

    step_x = width * 2
    step_y = height * 2.4
    panel_width = step_x * columns_count
    panel_height = step_y * (max_in_column + 1)

    start_x = width * 0.5
    start_y = 0.5 * panel_height - 2 * height

    name = 'ControlPanel'
    main_rect = create_rectangle(name, panel_width, panel_height)
    label = create_label(name, label='Blendshape controls', size=2 * height)
    label.parent = main_rect
    label.location = (0, 0.5 * panel_height + 0.5 * height, 0)

    i = 0
    j = 0
    for name in controls_dict:
        rect = controls_dict[name]['control']['rectangle']
        rect.parent = main_rect
        rect.location = (start_x + j * step_x, start_y - i * step_y, 0)
        rect.hide_select = True
        i += 1
        if (i >= max_in_column):
            j += 1
            i = 0

    return main_rect


def remove_blendshape_drivers(obj: Object) -> None:
    all_dict = _get_blendshapes_drivers(obj)
    for name in all_dict:
        obj.data.shape_keys.animation_data.drivers.remove(all_dict[name]['driver'])


def _find_all_children(obj: Object, obj_list: List) -> None:
    for child in obj.children:
        _find_all_children(child, obj_list)
    obj_list.append(obj)


def delete_with_children(obj: Object) -> None:
    arr = []
    _find_all_children(obj, arr)
    if arr:
        operator_with_context(bpy.ops.object.delete,
                              {'selected_objects': arr})


def select_control_panel_sliders(panel_obj: Object) -> int:
    arr = []
    _find_all_children(panel_obj, arr)
    empties = [obj for obj in arr if obj.type == 'EMPTY']
    counter = 0
    if empties:
        deselect_all()
        for obj in empties:
            obj.select_set(state=True)
            counter += 1
    return counter


def _get_blendshapes_drivers(obj: Object) -> Dict:
    if _has_no_blendshapes(obj):
        return {}
    drivers_dict = {}
    for drv in obj.data.shape_keys.animation_data.drivers:
        blendshape_name = drv.data_path.split('"')[1]
        drivers_dict[blendshape_name] = {
            'driver': drv, 'slider': drv.driver.variables[0].targets[0].id}
    return drivers_dict


def get_control_panel_by_drivers(obj: Object) -> Object:
    drivers_dict = _get_blendshapes_drivers(obj)
    if len(drivers_dict) == 0:
        return None
    name = [*drivers_dict.keys()][0]
    rect = drivers_dict[name]['slider'].parent
    if not rect:
        return None
    return rect.parent


def convert_controls_animation_to_blendshapes(obj: Object) -> bool:
    if _has_no_blendshapes(obj):
        return False
    all_dict = _get_blendshapes_drivers(obj)
    blend_action = _get_safe_blendshapes_action(obj)
    if not blend_action:
        return False
    for name in all_dict:
        item = all_dict[name]
        control_action = item['slider'].animation_data.action
        control_fcurve = get_action_fcurve(control_action, 'location', index=0)
        anim_data = get_fcurve_data(control_fcurve)
        blendshape_fcurve = get_safe_action_fcurve(
            blend_action, 'key_blocks["{}"].value'.format(name), index=0)
        clear_fcurve(blendshape_fcurve)
        put_anim_data_in_fcurve(blendshape_fcurve, anim_data)
    return True


def convert_blendshapes_animation_to_controls(obj: Object) -> bool:
    if _has_no_blendshapes(obj):
        return False
    all_dict = _get_blendshapes_drivers(obj)
    blend_action = _get_safe_blendshapes_action(obj)
    if not blend_action:
        return False
    for name in all_dict:
        blendshape_fcurve = get_action_fcurve(
            blend_action, 'key_blocks["{}"].value'.format(name), index=0)
        if not blendshape_fcurve:
            continue
        anim_data = get_fcurve_data(blendshape_fcurve)

        item = all_dict[name]
        if not item['slider'].animation_data:
            item['slider'].animation_data_create()
        if not item['slider'].animation_data.action:
            item['slider'].animation_data.action = bpy.data.actions.new(name + 'Action')
        control_action = item['slider'].animation_data.action
        control_fcurve = get_safe_action_fcurve(control_action, 'location', index=0)
        clear_fcurve(control_fcurve)
        put_anim_data_in_fcurve(control_fcurve, anim_data)
    return True


def create_facs_test_animation_on_sliders(obj: Object, start_time: float = 1,
                                          dtime: float = 4) -> bool:
    if _has_no_blendshapes(obj):
        return False
    all_dict = _get_blendshapes_drivers(obj)
    time = start_time
    for name in all_dict:
        item = all_dict[name]
        if not item['slider'].animation_data:
            item['slider'].animation_data_create()
        if not item['slider'].animation_data.action:
            item['slider'].animation_data.action = bpy.data.actions.new(name + 'Action')
        control_action = item['slider'].animation_data.action
        control_fcurve = get_safe_action_fcurve(control_action, 'location', index=0)
        anim_data = [(time, 0.0), (time + dtime, 1.0), (time + 2 * dtime, 0)]
        time += dtime * 2
        put_anim_data_in_fcurve(control_fcurve, anim_data)
    return True
