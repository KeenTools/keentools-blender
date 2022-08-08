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

import logging

import bpy


def check_area_active_problem(area):
    return not area or not area.spaces or not area.spaces.active


def enter_area_localview(area):
    if check_area_active_problem(area):
        return False
    if not area.spaces.active.local_view:
        bpy.ops.view3d.localview({'area':area})
        return True
    return False


def exit_area_localview(area):
    logger = logging.getLogger(__name__)
    log_output = logger.debug
    log_output(f'exit_area_localview: area={id(area)}')
    if check_area_active_problem(area):
        return False
    if area.spaces.active.local_view:
        bpy.ops.view3d.localview({'area':area})
        log_output('exit_area_localview success')
        return True
    return False
