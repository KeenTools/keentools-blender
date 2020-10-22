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

from ..utils.rig_slider import create_slider, create_rectangle


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


def _create_basis_blendshape(obj):
    if not obj.data.shape_keys:
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


def get_all_blendshape_names(obj):
    if not obj.data.shape_keys:
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
    if not obj.data.shape_keys:
        return
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

    main_rect = create_rectangle('rig', panel_width, panel_height)
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