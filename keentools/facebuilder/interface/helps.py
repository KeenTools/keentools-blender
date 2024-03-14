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

from typing import Any, Callable

from bpy.types import Operator

from ...addon_config import Config
from ...facebuilder_config import FBConfig
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


class FBHELP_Common:
    bl_options = {'REGISTER', 'INTERNAL'}
    def execute(self, context):
        return {'FINISHED'}


class FBHELP_OT_ViewsHelp(FBHELP_Common, Operator):
    bl_idname = FBConfig.fb_help_views_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    draw = _universal_draw(bl_idname)
    invoke = _universal_invoke(bl_idname)


class FBHELP_OT_ModelHelp(FBHELP_Common, Operator):
    bl_idname = FBConfig.fb_help_model_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    draw = _universal_draw(bl_idname)
    invoke = _universal_invoke(bl_idname)


class FBHELP_OT_AppearanceHelp(FBHELP_Common, Operator):
    bl_idname = FBConfig.fb_help_appearance_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    draw = _universal_draw(bl_idname)
    invoke = _universal_invoke(bl_idname)


class FBHELP_OT_TextureHelp(FBHELP_Common, Operator):
    bl_idname = FBConfig.fb_help_texture_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    draw = _universal_draw(bl_idname)
    invoke = _universal_invoke(bl_idname)


class FBHELP_OT_BlendshapesHelp(FBHELP_Common, Operator):
    bl_idname = FBConfig.fb_help_blendshapes_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    draw = _universal_draw(bl_idname)
    invoke = _universal_invoke(bl_idname)


class FBHELP_OT_ExportHelp(FBHELP_Common, Operator):
    bl_idname = FBConfig.fb_help_export_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    draw = _universal_draw(bl_idname)
    invoke = _universal_invoke(bl_idname)


CLASSES_TO_REGISTER = (FBHELP_OT_ViewsHelp,
                       FBHELP_OT_ModelHelp,
                       FBHELP_OT_AppearanceHelp,
                       FBHELP_OT_TextureHelp,
                       FBHELP_OT_BlendshapesHelp,
                       FBHELP_OT_ExportHelp)
