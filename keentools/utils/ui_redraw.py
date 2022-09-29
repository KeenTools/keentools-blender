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
import addon_utils


def get_areas_by_type(area_type='VIEW_3D'):
    areas = []
    for window in bpy.data.window_managers['WinMan'].windows:
        for area in window.screen.areas:
            if area.type == area_type:
                areas.append(area)
    return areas


def get_all_areas():
    return [area for window in bpy.data.window_managers['WinMan'].windows
                 for area in window.screen.areas]


def force_ui_redraw(area_type='PREFERENCES'):
    areas = get_areas_by_type(area_type)
    for area in areas:
        area.tag_redraw()


def show_ui_panel(context):
    try:
        area = context.area
        area.spaces[0].show_region_ui = True
    except Exception:
        pass


def find_modules_by_name_starting_with(name_start='KeenTools'):
    return [mod for mod in addon_utils.modules() if
            mod.bl_info['name'][:len(name_start)].lower() == name_start.lower()]


def filter_module_list_by_name_starting_with(module_list, name_start):
    return [mod for mod in module_list if
            mod.bl_info['name'][:len(name_start)].lower() == name_start.lower()]


def collapse_all_modules(mods):
    for mod in mods:
        mod.bl_info['show_expanded'] = False


def mark_old_modules(mods, filter_dict):
    def _mark_outdated(mod):
        mark_text = ' OUTDATED \u2014 REMOVE THIS'  # \u2014 - em dash
        if mod.bl_info['name'][-len(mark_text):] != mark_text:
            mod.bl_info['name'] = mod.bl_info['name'] + mark_text
        mod.bl_info[
            'description'] = 'This add-on is outdated. Please remove it.'
        mod.bl_info['location'] = ''
        mod.bl_info['show_expanded'] = True

    for mod in mods:
        if all([mod.bl_info[key] == filter_dict[key]
                for key in filter_dict.keys()]):
            _mark_outdated(mod)


def total_redraw_ui():
    if not bpy.app.background:
        bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
