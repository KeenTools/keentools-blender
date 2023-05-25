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


def get_override_context(*, window=None, screen=None, area=None):
    win = bpy.context.window if window is None else window
    scr = bpy.context.screen if screen is None else screen
    ar = get_area() if area is None else area
    override = bpy.context.copy()
    override['window'] = win
    override['screen'] = scr
    override['area'] = ar
    override['region'] = get_region(area)
    return override


def get_fake_context(*, window=None, screen=None, area=None,
                     region=None, space=None, scene=None):
    win = bpy.context.window if window is None else window
    scr = bpy.context.screen if screen is None else screen
    ar = get_area() if area is None else area
    reg = get_region(ar) if region is None else region
    sp = get_space(ar) if space is None else space
    scn = bpy.context.scene if scene is None else scene

    fake_context = lambda: None
    fake_context.window = win
    fake_context.screen = scr
    fake_context.area = ar
    fake_context.region = reg
    fake_context.space_data = lambda: None
    if sp is not None:
        fake_context.space_data.region_3d = sp.region_3d
    fake_context.scene = scn
    return fake_context
