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

from .bpy_common import (link_object_to_current_scene_collection,
                         bpy_create_object,
                         bpy_create_empty)


def create_label(name, label='Label', size=0.2):
    text_curve = bpy.data.curves.new(name + 'LabelSpline', type='FONT')
    text_obj = bpy_create_object(name + 'Label', text_curve)
    text_curve.body = label
    text_curve.size = size
    text_obj.hide_select = True
    text_obj.hide_render = True
    link_object_to_current_scene_collection(text_obj)
    return text_obj


def create_rectangle(name, width=1.0, height=0.2):
    curve = bpy.data.curves.new(name + 'Curve', 'CURVE')
    curve.dimensions = '2D'

    pline = curve.splines.new('POLY')
    pline.points.add(3)

    point_weight = 1.0
    pline.points[0].co = (0, -0.5 * height, 0, point_weight)
    pline.points[1].co = (width, -0.5 * height, 0, point_weight)
    pline.points[2].co = (width, 0.5 * height, 0, point_weight)
    pline.points[3].co = (0, 0.5 * height, 0, point_weight)
    pline.use_cyclic_u = True  # closed spline

    obj = bpy_create_object(name, curve)
    link_object_to_current_scene_collection(obj)
    return obj


def create_slider(name, label='Label', width=1.0, height=0.2):
    rect = create_rectangle(name + 'Rect', width, height)

    control = bpy_create_empty(name + 'Slider')
    link_object_to_current_scene_collection(control)

    control.empty_display_type = 'CIRCLE'
    control.empty_display_size = 0.35 * height
    control.parent = rect
    control.rotation_euler = (0.5 * math.pi, 0, 0)
    control.location = (0, 0, 0)

    text_obj = create_label(name, label, height)
    text_obj.parent = rect
    text_obj.location = (0, 0.6 * height, 0)

    constraint = control.constraints.new('LIMIT_LOCATION')
    constraint.owner_space = 'LOCAL'
    constraint.use_transform_limit = True
    constraint.use_min_x = True
    constraint.use_max_x = True
    constraint.use_min_y = True
    constraint.use_max_y = True
    constraint.use_min_z = True
    constraint.use_max_z = True
    constraint.min_x = 0
    constraint.max_x = 1.0
    constraint.min_y = 0
    constraint.max_y = constraint.min_y
    constraint.min_z = 0
    constraint.max_z = constraint.min_z
    return {'label': text_obj, 'rectangle': rect,
            'slider': control, 'constraint': constraint}
