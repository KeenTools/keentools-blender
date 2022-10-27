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
import re
import bpy

from ..utils.kt_logging import KTLogger
from ..addon_config import Config, get_operator, ErrorType
from ..facebuilder_config import FBConfig


_log = KTLogger(__name__)


_default_width = 400
_ERROR_MESSAGES = {
    ErrorType.NoLicense: {
        'width': _default_width,
        'message': [
                'License is not found',
                ' ',
                'You have 0 days of trial left and there is no license '
                'installed',
                'or something wrong has happened with the installed license.',
                'Please check the license settings.'
            ],
    },
    ErrorType.SceneDamaged: {
        'width': _default_width,
        'message': [
                'Scene was damaged',
                ' ',
                'Some objects created by FaceBuilder were missing '
                'from the scene.',
                'The scene was restored automatically.'
            ],
    },
    ErrorType.CannotReconstruct: {
        'width': _default_width,
        'message': [
                'Reconstruction is impossible',
                ' ',
                'Object parameters are invalid or missing.'
            ],
    },
    ErrorType.CannotCreateObject: {
        'width': _default_width,
        'message': [
                'Cannot create object',
                ' ',
                'An error occurred while creating an object.'
            ],
    },
    ErrorType.MeshCorrupted: {
        'width': _default_width,
        'message': [
                'Wrong topology',
                ' ',
                'The FaceBuilder mesh is damaged and cannot be used.'
            ],
    },
    ErrorType.PktProblem: {
        'width': _default_width,
        'message': [
                'KeenTools Core is missing',
                ' ',
                'You need to install KeenTools Core library '
                'before using FaceBuilder.'
            ],
    },
    ErrorType.PktModelProblem: {
        'width': _default_width,
        'message': [
                'KeenTools Core corrupted',
                ' ',
                'Model data cannot be loaded. You need to reinstall '
                'FaceBuilder.'
            ],
    },
    ErrorType.DownloadingProblem: {
        'width': 650,
        'message': [
                'Downloading error',
                ' ',
                'An unknown error encountered. The downloaded files might be corrupted. ',
                'You can try downloading them again, '
                'restarting Blender or installing the update manually.',
                'If you want to manually update the add-on: remove the old add-on, ',
                'restart Blender and install the new version of the add-on.'
            ],
    },
}


class KT_OT_AddonWarning(bpy.types.Operator):
    bl_idname = Config.kt_warning_idname
    bl_label = ''
    bl_options = {'REGISTER', 'INTERNAL'}

    msg: bpy.props.IntProperty(default=ErrorType.Unknown)
    msg_content: bpy.props.StringProperty(default='')
    msg_width: bpy.props.IntProperty(default=_default_width)

    content = []
    width = _default_width

    def set_content(self, txt_list):
        self.content = txt_list
        self.content.append(' ')  # Additional line at the end

    def draw(self, context):
        layout = self.layout.column()
        layout.scale_y = Config.text_scale_y

        for txt in self.content:
            layout.label(text=txt)

        if self.msg == ErrorType.NoLicense:
            op = self.layout.operator(Config.kt_open_url_idname,
                                      text='Purchase a license')
            op.url = FBConfig.fb_license_purchase_url

    def execute(self, context):
        if self.msg not in (ErrorType.PktProblem, ErrorType.NoLicense):
            return {'FINISHED'}

        op = get_operator(Config.kt_addon_settings_idname)
        op('EXEC_DEFAULT', show='all')
        return {'FINISHED'}

    def _output_error_to_console(self):
        _log.warning('\n--- KeenTools Addon Warning [{}] ---\n'
                     '{}\n---\n'.format(self.msg, '\n'.join(self.content)))

    def invoke(self, context, event):
        if self.msg == ErrorType.CustomMessage:
            self.set_content(re.split('\r\n|\n', self.msg_content))
            self._output_error_to_console()
            return context.window_manager.invoke_props_dialog(self, width=self.msg_width)

        if self.msg not in _ERROR_MESSAGES.keys():
            return {'FINISHED'}

        message_dict = _ERROR_MESSAGES[self.msg]
        self.set_content(message_dict['message'])
        self._output_error_to_console()
        return context.window_manager.invoke_props_dialog(
            self, width=message_dict['width'])
