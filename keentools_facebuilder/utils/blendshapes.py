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
import bpy
import numpy as np

from ..utils.rig_slider import create_slider, create_rectangle, create_label
from ..fbloader import FBLoader
import keentools_facebuilder.blender_independent_packages.pykeentools_loader as pkt


def _all_blendshape_names():
    return [
        'eyeBlinkRight', 'eyeLookDownRight', 'eyeLookInRight',
        'eyeLookOutRight', 'eyeLookUpRight', 'eyeSquintRight',
        'eyeWideRight', 'eyeBlinkLeft', 'eyeLookDownLeft',
        'eyeLookInLeft', 'eyeLookOutLeft', 'eyeLookUpLeft',
        'eyeSquintLeft', 'eyeWideLeft', 'jawForward', 'jawRight',
        'jawLeft', 'jawOpen', 'mouthClose', 'mouthFunnel',
        'mouthPucker', 'mouthRight', 'mouthLeft', 'mouthSmileRight',
        'mouthSmileLeft', 'mouthFrownRight', 'mouthFrownLeft',
        'mouthDimpleRight', 'mouthDimpleLeft', 'mouthStretchRight',
        'mouthStretchLeft', 'mouthRollLower', 'mouthRollUpper',
        'mouthShrugLower', 'mouthShrugUpper', 'mouthPressRight',
        'mouthPressLeft', 'mouthLowerDownRight', 'mouthLowerDownLeft',
        'mouthUpperUpRight', 'mouthUpperUpLeft', 'browDownRight',
        'browDownLeft', 'browInnerUp', 'browOuterUpRight',
        'browOuterUpLeft', 'cheekPuff', 'cheekSquintRight',
        'cheekSquintLeft', 'noseSneerRight', 'noseSneerLeft',
        'tongueOut',
        'HeadYaw', 'HeadPitch', 'HeadRoll',
        'LeftEyeYaw', 'LeftEyePitch', 'LeftEyeRoll',
        'RightEyeYaw', 'RightEyePitch', 'RightEyeRoll']


def default_blendshape_names():
    return _all_blendshape_names()[:52]


def has_no_blendshapes(obj):
    return not obj.data.shape_keys


def _create_basis_blendshape(obj):
    if has_no_blendshapes(obj):
        obj.shape_key_add(name='Basis')


def _move_vertices(shape, vec):
    count = len(shape.data)
    verts = np.empty((count, 3), 'f')
    shape.data.foreach_get('co', np.reshape(verts, count * 3))
    verts += vec
    shape.data.foreach_set('co', verts.ravel())


def create_fake_blendshapes(obj, names):
    _create_basis_blendshape(obj)
    counter = 0
    for name in names:
        if obj.data.shape_keys.key_blocks.find(name) < 0:
            shape = obj.shape_key_add(name=name)
            counter += 1
            phi = np.random.uniform(0, np.pi * 2)
            vec = np.array((np.cos(phi), 0, np.sin(phi)))
            _move_vertices(shape, vec)
    return counter


def create_facs_blendshapes(obj):
    fb = FBLoader.get_builder()
    geo = fb.applied_args_model()
    pc = pkt.module().ProgressCallback()
    fe = pkt.module().FacsExecutor(geo, pc)
    if not fe.facs_enabled():
        return 0

    _create_basis_blendshape(obj)
    counter = 0
    for i, name in enumerate(fe.facs_names):
        if obj.data.shape_keys.key_blocks.find(name) < 0:
            shape = obj.shape_key_add(name=name)
            counter += 1
            verts = fe.get_facs_blendshape(i)
            rot = np.array([[1., 0., 0.], [0., 0., 1.], [0., -1., 0]])
            shape.data.foreach_set('co', (verts @ rot).ravel())
    return counter


def get_all_blendshape_names(obj):
    if has_no_blendshapes(obj):
        return []
    res = [kb.name for kb in obj.data.shape_keys.key_blocks]
    return res[1:]


def create_driver(target, control_obj, control_prop='location.x'):
    res = target.driver_add('value')
    res.driver.type = 'AVERAGE'
    drv_var = res.driver.variables.new()
    drv_var.name = 'DriverName'
    drv_var.type = 'SINGLE_PROP'
    drv_var.targets[0].id = control_obj
    drv_var.targets[0].data_path = control_prop
    return res


def create_blendshape_controls(obj):
    if has_no_blendshapes(obj):
        return {}
    blendshape_names = get_all_blendshape_names(obj)
    controls = {}
    for name in blendshape_names:
        slider_dict = create_slider(name, name, width=1.0, height=0.2)
        driver = create_driver(obj.data.shape_keys.key_blocks[name],
                               slider_dict['slider'], 'location.x')
        controls[name] = {'control': slider_dict, 'driver': driver}
    return controls


def make_control_panel(controls_dict):
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


def load_csv_animation(obj, filepath):
    pass


def get_blendshapes_drivers(obj):
    if has_no_blendshapes(obj):
        return {}
    drivers_dict = {}
    for drv in obj.data.shape_keys.animation_data.drivers:
        blendshape_name = drv.data_path.split('"')[1]
        drivers_dict[blendshape_name] = {
            'driver': drv, 'slider': drv.driver.variables[0].targets[0].id}
    return drivers_dict


def get_safe_blendshapes_action(obj):
    if has_no_blendshapes(obj):
        return None
    anim_data = obj.data.shape_keys.animation_data
    if not anim_data:
        anim_data = obj.data.shape_keys.animation_data_create()
        if not anim_data:
            return None
    if not anim_data.action:
        anim_data.action = bpy.data.actions.new('fbBlendShapesAction')
    return anim_data.action


def get_action_fcurve(action, data_path, index=0):
    return action.fcurves.find(data_path, index=index)


def get_safe_action_fcurve(action, data_path, index=0):
    fcurve = get_action_fcurve(action, data_path, index=index)
    if fcurve:
        return fcurve
    return action.fcurves.new(data_path, index=index)


def get_fcurve_data(fcurve):
    if not fcurve:
        return []
    return [p.co for p in fcurve.keyframe_points]


def clear_fcurve(fcurve):
    for p in reversed(fcurve.keyframe_points):
        fcurve.keyframe_points.remove(p)


def put_anim_data_in_fcurve(fcurve, anim_data):
    if not fcurve:
        return
    start_index = len(fcurve.keyframe_points)
    fcurve.keyframe_points.add(len(anim_data))
    for i, point in enumerate(anim_data):
        fcurve.keyframe_points[start_index + i].co = point


def convert_control_animation_to_blendshape(obj):
    if has_no_blendshapes(obj):
        return False
    all_dict = get_blendshapes_drivers(obj)
    blend_action = get_safe_blendshapes_action(obj)
    if not blend_action:
        return False
    for name in all_dict:
        item = all_dict[name]
        control_action = item['slider'].animation_data.action
        control_fcurve = get_action_fcurve(control_action, 'location', index=0)
        anim_data = get_fcurve_data(control_fcurve)
        fcurve = get_safe_action_fcurve(blend_action,
                                        'key_blocks["{}"].value'.format(name),
                                        index=0)
        clear_fcurve(fcurve)
        put_anim_data_in_fcurve(fcurve, anim_data)
    return True


def remove_blendshape_drivers(obj):
    all_dict = get_blendshapes_drivers(obj)
    for name in all_dict:
        obj.data.shape_keys.animation_data.drivers.remove(all_dict[name]['driver'])


def _find_all_children(obj, obj_list):
    for child in obj.children:
        _find_all_children(child, obj_list)
    obj_list.append(obj)


def delete_with_children(obj):
    arr = []
    _find_all_children(obj, arr)
    if arr:
        bpy.ops.object.delete({'selected_objects': arr})


def select_control_panel_sliders(panel_obj):
    arr = []
    _find_all_children(panel_obj, arr)
    empties = [obj for obj in arr if obj.type == 'EMPTY']
    counter = 0
    if empties:
        bpy.ops.object.select_all(action='DESELECT')
        for obj in empties:
            obj.select_set(state=True)
            counter += 1
    return counter


def get_control_panel_by_drivers(obj):
    drivers_dict = get_blendshapes_drivers(obj)
    if len(drivers_dict) == 0:
        return None
    name = [*drivers_dict.keys()][0]
    rect = drivers_dict[name]['slider'].parent
    if not rect:
        return None
    return rect.parent


def blendshapes_have_animation(obj):
    if has_no_blendshapes(obj):
        return False
    anim_data = obj.data.shape_keys.animation_data
    if not anim_data:
        return False
    return True
