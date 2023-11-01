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

from bpy.types import Panel

from ..addon_config import Config, ErrorType
from ..utils.icons import KTIcons


def _get_all_error_type_values():
    arr = sorted([(getattr(ErrorType, name), name)
                  for name in dir(ErrorType)
                  if not callable(getattr(ErrorType, name))
                  and not name.startswith('__')],
                 key=lambda x: x[0])
    return arr


class KTErrorMessagePanel(Panel):
    bl_idname = Config.kt_error_testing
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = 'Error messages'
    bl_category = Config.kt_testing_tab_category
    bl_context = 'objectmode'
    bl_options = {'DEFAULT_CLOSED'}

    def _draw_error_buttons(self, layout):
        layout.label(text='Error Messages')
        for value, name in _get_all_error_type_values():
            op = layout.operator(Config.kt_warning_idname,
                                 text=f'{value}: {name}')
            op.msg = value

    def draw(self, context):
        layout = self.layout
        self._draw_error_buttons(layout)

        layout.label(text='--- Icons ---')
        KTIcons.layout_icons(layout)


class GTShaderTestingPanel(Panel):
    bl_idname = Config.kt_gt_shader_testing
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = 'GeoTracker Shader Tests'
    bl_category = Config.kt_testing_tab_category
    bl_context = 'objectmode'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        for action in ['all', 'stop', 'points2d', 'points3d',
                       'residuals', 'wireframer', 'selector',
                       'mask2d', 'timeliner', 'texter']:
            op = layout.operator(Config.kt_gt_shader_testing_idname,
                                 text=action)
            op.action = action


class FBShaderTestingPanel(Panel):
    bl_idname = Config.kt_fb_shader_testing
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = 'FaceBuilder Shader Tests'
    bl_category = Config.kt_testing_tab_category
    bl_context = 'objectmode'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        for action in ['all', 'stop', 'points2d', 'points3d', 'residuals',
                       'wireframer', 'rectangler', 'texter']:
            op = layout.operator(Config.kt_fb_shader_testing_idname,
                                 text=action)
            op.action = action
