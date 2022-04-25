# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2019-2022  KeenTools

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


def enter_context_localview(context):
    if context.space_data and not context.space_data.local_view:
        bpy.ops.view3d.localview()
        return True
    return False


def exit_context_localview(context):
    if context.space_data and context.space_data.local_view:
        bpy.ops.view3d.localview()
        return True
    return False


def exit_area_localview(area):
    if area and area.spaces.active.local_view:
        bpy.ops.view3d.localview({'area':area})
        return True
    return False
