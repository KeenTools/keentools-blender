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

from typing import Any, List, Set
import re

from bpy.types import Operator
from bpy.props import IntProperty, StringProperty

from ..utils.kt_logging import KTLogger
from ..addon_config import Config, get_operator, ErrorType
from ..facebuilder_config import FBConfig
from ..ui_strings import error_messages


_log = KTLogger(__name__)


_default_width: int = 400


class KT_OT_AddonWarning(Operator):
    bl_idname = Config.kt_warning_idname
    bl_label = ''
    bl_options = {'REGISTER', 'INTERNAL'}

    msg: IntProperty(default=ErrorType.Unknown)
    msg_content: StringProperty(default='')
    msg_width: IntProperty(default=_default_width)

    content: List[str] = []
    width: int = _default_width

    def set_content(self, txt_list: List) -> None:
        self.content = txt_list + [' ']

    def draw(self, context: Any) -> None:
        layout = self.layout.column()
        layout.scale_y = Config.text_scale_y

        for txt in self.content:
            layout.label(text=txt)

        if self.msg == ErrorType.NoLicense:
            op = self.layout.operator(Config.kt_open_url_idname,
                                      text='Purchase a license')
            op.url = FBConfig.fb_license_purchase_url

    def execute(self, context: Any) -> Set:
        if self.msg not in (ErrorType.PktProblem, ErrorType.NoLicense,
                            ErrorType.FBGracePeriod, ErrorType.GTGracePeriod):
            return {'FINISHED'}

        op = get_operator(Config.kt_addon_settings_idname)
        op('EXEC_DEFAULT', show='all')
        return {'FINISHED'}

    def _output_error_to_console(self) -> None:
        _log.warning('\n--- KeenTools Addon Warning [{}] ---\n'
                     '{}\n---\n'.format(self.msg, '\n'.join(self.content)))

    def invoke(self, context: Any, event: Any) -> Set:
        if self.msg == ErrorType.CustomMessage:
            self.set_content(re.split('\r\n|\n', self.msg_content))
            self._output_error_to_console()
            return context.window_manager.invoke_props_dialog(
                self, width=self.msg_width)

        if self.msg not in error_messages.keys():
            return {'FINISHED'}

        message_named_tuple = error_messages[self.msg]
        self.set_content(message_named_tuple.message)
        self._output_error_to_console()
        return context.window_manager.invoke_props_dialog(
            self, width=message_named_tuple.width)
