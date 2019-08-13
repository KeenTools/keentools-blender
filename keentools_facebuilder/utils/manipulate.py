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

from .. config import get_main_settings, ErrorType, Config


def show_all_cameras(headnum):
    settings = get_main_settings()
    head = settings.heads[headnum]
    for i, c in enumerate(head.cameras):
        # Unhide camera
        c.camobj.hide_set(False)


def hide_other_cameras(headnum, camnum):
    settings = get_main_settings()
    head = settings.heads[headnum]
    for i, c in enumerate(head.cameras):
        if i != camnum:
            # Hide camera
            c.camobj.hide_set(True)


def inc_operation():
    """ Debug purpose """
    settings = get_main_settings()
    settings.opnum += 1


def get_operation():
    """ Debug purpose """
    settings = get_main_settings()
    return settings.opnum


def force_undo_push(msg='KeenTools operation'):
    inc_operation()
    bpy.ops.ed.undo_push(message=msg)


def keyframe_by_camnum(headnum, camnum):
    settings = get_main_settings()
    if headnum >= len(settings.heads):
        return -1
    if camnum >= len(settings.heads[headnum].cameras):
        return -1
    return settings.heads[headnum].cameras[camnum].keyframe_id


def switch_to_mode(mode='MATERIAL'):
    # Switch to Mode
    areas = bpy.context.workspace.screens[0].areas
    for area in areas:
        for space in area.spaces:
            if space.type == 'VIEW_3D':
                space.shading.type = mode


def toggle_mode(modes=('SOLID', 'MATERIAL')):
    # Switch to Mode
    areas = bpy.context.workspace.screens[0].areas
    for area in areas:
        for space in area.spaces:
            if space.type == 'VIEW_3D':
                cur_mode = space.shading.type
                ind = 0
                if cur_mode in modes:
                    ind = modes.index(cur_mode)
                    ind += 1
                    if ind >= len(modes):
                        ind = 0
                space.shading.type = modes[ind]


def check_settings():
    settings = get_main_settings()
    if not settings.check_heads_and_cams():
        # Settings structure is broken
        # Fix Heads and cameras
        heads_deleted, cams_deleted = settings.fix_heads()
        if heads_deleted == 0:
            warn = getattr(bpy.ops.wm, Config.fb_warning_operator_callname)
            warn('INVOKE_DEFAULT', msg=ErrorType.SceneDamaged)
        return False
    return True
