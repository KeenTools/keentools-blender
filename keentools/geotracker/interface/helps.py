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

from typing import Any, Callable

from bpy.types import Operator

from ...addon_config import Config
from ...geotracker_config import GTConfig
from ..ui_strings import buttons, help_texts


def _universal_draw(id: str) -> Callable:
    def _draw(self, context: Any) -> None:
        layout = self.layout
        col = layout.column()
        col.scale_y = Config.text_scale_y
        content = help_texts[id].message

        for txt in content:
            col.label(text=txt)
        layout.separator()
    return _draw


def _universal_invoke(id: str) -> Callable:
    def _invoke(self, context: Any, event: Any) -> None:
        return context.window_manager.invoke_props_dialog(
            self, width=help_texts[id].width)
    return _invoke


class GTHELP_Common:
    bl_options = {'REGISTER', 'INTERNAL'}
    def execute(self, context):
        return {'FINISHED'}


class GTHELP_OT_InputsHelp(GTHELP_Common, Operator):
    bl_idname = GTConfig.gt_help_inputs_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    draw = _universal_draw(bl_idname)
    invoke = _universal_invoke(bl_idname)


class GTHELP_OT_MasksHelp(GTHELP_Common, Operator):
    bl_idname = GTConfig.gt_help_masks_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    draw = _universal_draw(bl_idname)
    invoke = _universal_invoke(bl_idname)


class GTHELP_OT_AnalyzeHelp(GTHELP_Common, Operator):
    bl_idname = GTConfig.gt_help_analyze_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    draw = _universal_draw(bl_idname)
    invoke = _universal_invoke(bl_idname)


class GTHELP_OT_CameraHelp(GTHELP_Common, Operator):
    bl_idname = GTConfig.gt_help_camera_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    draw = _universal_draw(bl_idname)
    invoke = _universal_invoke(bl_idname)


class GTHELP_OT_TrackingHelp(GTHELP_Common, Operator):
    bl_idname = GTConfig.gt_help_tracking_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    draw = _universal_draw(bl_idname)
    invoke = _universal_invoke(bl_idname)


class GTHELP_OT_AppearanceHelp(GTHELP_Common, Operator):
    bl_idname = GTConfig.gt_help_appearance_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    draw = _universal_draw(bl_idname)
    invoke = _universal_invoke(bl_idname)


class GTHELP_OT_TextureHelp(GTHELP_Common, Operator):
    bl_idname = GTConfig.gt_help_texture_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    draw = _universal_draw(bl_idname)
    invoke = _universal_invoke(bl_idname)


class GTHELP_OT_AnimationHelp(GTHELP_Common, Operator):
    bl_idname = GTConfig.gt_help_animation_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    draw = _universal_draw(bl_idname)
    invoke = _universal_invoke(bl_idname)


class GTHELP_OT_RenderingHelp(GTHELP_Common, Operator):
    bl_idname = GTConfig.gt_help_rendering_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    draw = _universal_draw(bl_idname)
    invoke = _universal_invoke(bl_idname)


class GTHELP_OT_SmoothingHelp(GTHELP_Common, Operator):
    bl_idname = GTConfig.gt_help_smoothing_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    draw = _universal_draw(bl_idname)
    invoke = _universal_invoke(bl_idname)
