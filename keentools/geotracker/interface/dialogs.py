# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2022-2023 KeenTools

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

from typing import Any
import re

from bpy.types import Operator
from bpy.props import IntProperty

from ...utils.kt_logging import KTLogger
from ...addon_config import Config, ProductType, get_settings, product_name
from ...geotracker_config import GTConfig
from ..ui_strings import buttons


_log = KTLogger(__name__)


def _precalc_file_info(layout, geotracker):
    arr = re.split('\r\n|\n', geotracker.precalc_message)
    for txt in arr:
        layout.label(text=txt)


def _draw_precalc_file_info(layout, geotracker):
    if geotracker.precalc_message == '':
        return

    block = layout.column(align=True)
    box = block.box()
    col = box.column()
    col.scale_y = Config.text_scale_y
    col.label(text=geotracker.precalc_path)
    _precalc_file_info(col, geotracker)


class GT_OT_PrecalcInfo(Operator):
    bl_idname = GTConfig.gt_precalc_info_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'INTERNAL', 'UNDO'}

    product: IntProperty(default=ProductType.UNDEFINED)

    def draw(self, context):
        layout = self.layout
        settings = get_settings(self.product)
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return
        layout.label(text='Precalc file info:')
        _draw_precalc_file_info(layout, geotracker)

    def cancel(self, context):
        _log.output(f'{self.__class__.__name__} cancel '
                    f'[{product_name(self.product)}]')

    def execute(self, context):
        _log.output(f'{self.__class__.__name__} execute '
                    f'[{product_name(self.product)}]')
        return {'FINISHED'}

    def invoke(self, context, event):
        _log.output(f'{self.__class__.__name__} invoke '
                    f'[{product_name(self.product)}]')
        settings = get_settings(self.product)
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return {'CANCELLED'}
        geotracker.reload_precalc()
        return context.window_manager.invoke_popup(self, width=350)


class GT_OT_TextureBakeOptions(Operator):
    bl_idname = GTConfig.gt_texture_bake_options_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'INTERNAL', 'UNDO'}

    product: IntProperty(default=ProductType.UNDEFINED)

    def draw(self, context):
        layout = self.layout
        settings = get_settings(self.product)
        if settings is None:
            return

        col = layout.column(align=True)
        row = col.row()
        row.label(text='Resolution (in pixels)')
        btn = row.column(align=True)
        btn.active = False
        op = btn.operator(GTConfig.gt_reset_texture_resolution_idname,
                          text='', icon='LOOP_BACK', emboss=False,
                          depress=False)
        op.product = self.product

        col.separator(factor=0.4)
        row = col.row(align=True)
        row.prop(settings, 'tex_width', text='W')
        row.prop(settings, 'tex_height', text='H')

        col = layout.column(align=True)
        row = col.row()
        row.label(text='Advanced')
        btn = row.column(align=True)
        btn.active = False
        op = btn.operator(GTConfig.gt_reset_advanced_settings_idname,
                          text='', icon='LOOP_BACK', emboss=False,
                          depress=False)
        op.product = self.product

        col.separator(factor=0.4)
        col.prop(settings, 'tex_face_angles_affection')
        col.prop(settings, 'tex_uv_expand_percents')
        col.separator(factor=0.8)

    def execute(self, context):
        _log.output(f'{self.__class__.__name__} execute '
                    f'[{product_name(self.product)}]')
        return {'FINISHED'}

    def cancel(self, context):
        _log.output(f'{self.__class__.__name__} cancel '
                    f'[{product_name(self.product)}]')

    def invoke(self, context, event):
        _log.output(f'{self.__class__.__name__} invoke '
                    f'[{product_name(self.product)}]')
        return context.window_manager.invoke_props_dialog(self, width=350)
