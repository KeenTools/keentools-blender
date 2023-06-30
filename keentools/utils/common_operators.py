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
from bpy.types import Operator
from bpy.props import StringProperty

from ..addon_config import (Config,
                            show_user_preferences,
                            show_tool_preferences)
from .localview import check_context_localview
from .viewport_state import force_show_ui_overlays
from ..utils.ui_redraw import (force_ui_redraw,
                               find_modules_by_name_starting_with,
                               filter_module_list_by_name_starting_with,
                               collapse_all_modules,
                               mark_old_modules)
from .bpy_common import bpy_localview, bpy_show_addon_preferences, bpy_url_open
from ..ui_strings import buttons


class KT_OT_AddonSettings(Operator):
    bl_idname = Config.kt_addon_settings_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER'}

    show: StringProperty(default='all')

    def draw(self, context):
        pass

    def execute(self, context):
        show_user_preferences(facebuilder=False, geotracker=False)
        if self.show == 'facebuilder':
            show_tool_preferences(facebuilder=True, geotracker=False)
        elif self.show == 'geotracker':
            show_tool_preferences(facebuilder=False, geotracker=True)
        elif self.show == 'all':
            show_tool_preferences(facebuilder=True, geotracker=True)
        elif self.show == 'none':
            show_tool_preferences(facebuilder=False, geotracker=False)
        bpy_show_addon_preferences()
        return {'FINISHED'}


class KT_OT_OpenURLBase:
    bl_options = {'REGISTER', 'INTERNAL'}

    url: StringProperty(name='URL', default='')

    def execute(self, context):
        bpy_url_open(url=self.url)
        return {'FINISHED'}


class KT_OT_OpenURL(KT_OT_OpenURLBase, Operator):
    bl_idname = Config.kt_open_url_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description


class KT_OT_AddonSearch(Operator):
    bl_idname = Config.kt_addon_search_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER'}

    search: StringProperty(default='KeenTools')

    def draw(self, context):
        pass

    def execute(self, context):
        bpy.context.window_manager.addon_search = self.search
        bpy.ops.screen.userpref_show()
        mods = find_modules_by_name_starting_with(self.search)
        if len(mods) > 1:
            collapse_all_modules(mods)
            keentools_fb_mods = filter_module_list_by_name_starting_with(
                mods, 'KeenTools FaceBuilder')
            mark_old_modules(keentools_fb_mods, {'category': 'Add Mesh'})
        force_ui_redraw(area_type='PREFERENCES')
        return {'FINISHED'}


class KT_OT_ExitLocalview(Operator):
    bl_idname = Config.kt_exit_localview_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if not check_context_localview(context):
            self.report({'ERROR', 'Cannot set proper context for operator'})
            return {'CANCELLED'}
        bpy_localview()
        force_show_ui_overlays(context.area)
        return {'FINISHED'}


CLASSES_TO_REGISTER = (KT_OT_AddonSettings,
                       KT_OT_OpenURL,
                       KT_OT_AddonSearch,
                       KT_OT_ExitLocalview,)
