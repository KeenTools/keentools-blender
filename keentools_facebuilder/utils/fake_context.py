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

import bpy


# -------------------
# Get Context objects
def get_space(area):
    if area is None:
        return None
    for sp in area.spaces:
        if sp.type == 'VIEW_3D':
            return sp
    return None


def get_region(area):
    if area is None:
        return None
    for reg in area.regions:
        if reg.type == 'WINDOW':
            return reg
    return None


def get_area():
    window = bpy.context.window
    screen = window.screen
    for area in screen.areas:
        if area.type == 'VIEW_3D':
            return area
    return None


def get_override_context():
    window = bpy.context.window
    screen = window.screen
    override = bpy.context.copy()
    area = get_area()
    if area is not None:
        override['window'] = window
        override['screen'] = screen
        override['area'] = area
        override['region'] = get_region(area)
    return override


def get_fake_context():
    area = get_area()
    space = get_space(area)

    fake_context = lambda: None
    fake_context.area = area
    fake_context.region = get_region(area)
    fake_context.space_data = lambda: None
    if space is not None:
        fake_context.space_data.region_3d = space.region_3d
    fake_context.scene = bpy.context.scene
    return fake_context
