# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2019-2023  KeenTools

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
from bpy.types import Menu, Operator

from ...geotracker_config import GTConfig, get_gt_settings
from ...utils.manipulate import select_object_only
from ...utils.coords import distance_between_objects


class GT_MT_PrecalcMenu(Menu):
    bl_label = 'Precalc operations'
    bl_idname = GTConfig.gt_precalc_menu_idname
    bl_description = 'precalc operations'

    def draw(self, context):
        layout = self.layout
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()

        layout.separator()
        row = layout.row()
        row.prop(geotracker, 'precalc_start')
        row.prop(geotracker, 'precalc_end')
        row.operator(GTConfig.gt_create_precalc_idname,
                     text='Create precalc')
        layout.separator()
        layout.operator(GTConfig.gt_choose_precalc_file_idname,
                        text='Load / New precalc')


class GT_OT_PrecalcWindow(Operator):
    bl_idname = 'kt_geotracker.precalc_window'
    bl_label = ''
    bl_options = {'REGISTER', 'INTERNAL'}

    def draw(self, context) -> None:
        layout = self.layout
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()

        layout.separator()
        row = layout.row()
        row.prop(geotracker, 'precalc_start')
        row.prop(geotracker, 'precalc_end')
        row.operator(GTConfig.gt_create_precalc_idname,
                     text='Create precalc')
        layout.separator()
        layout.operator(GTConfig.gt_choose_precalc_file_idname,
                        text='Load / New precalc')

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_popup(self, width=300)


class GT_OT_ResizeWindow(Operator):
    bl_idname = 'kt_geotracker.resize_window'
    bl_label = 'Resize object & distance'
    bl_options = {'UNDO', 'REGISTER', 'INTERNAL'}

    value: bpy.props.FloatProperty(default=1.0, precision=4, step=0.03)

    def draw(self, context) -> None:
        layout = self.layout
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()

        layout.separator()
        layout.prop(self, 'value', text='Scale:')
        dx, dy, dz = geotracker.geomobj.dimensions
        sx, sy, sz = geotracker.geomobj.scale
        dist = distance_between_objects(geotracker.camobj, geotracker.geomobj)
        row = layout.row()
        col = row.column()
        col.label(text='Dimensions')
        col.label(text=f'X: {dx:.4f}')
        col.label(text=f'Y: {dy:.4f}')
        col.label(text=f'Z: {dz:.4f}')

        col = row.column()
        col.label(text='Scale')
        col.label(text=f'X: {sx:.4f}')
        col.label(text=f'Y: {sy:.4f}')
        col.label(text=f'Z: {sz:.4f}')

        col = row.column()
        col.label(text='Distance:')
        col.label(text=f'{dist:.4f}')

        layout.separator()

    def execute(self, context):
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()
        select_object_only(geotracker.geomobj)
        bpy.ops.transform.resize(value=(self.value, self.value, self.value),
                                 center_override=geotracker.camobj.location)
        return {'FINISHED'}

    def invoke(self, context, event):
        self.value = 1.0
        return context.window_manager.invoke_props_popup(self, event)
