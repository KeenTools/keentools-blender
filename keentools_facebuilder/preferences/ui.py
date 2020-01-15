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

import sys

import bpy
import keentools_facebuilder.preferences.operators as preferences_operators
import keentools_facebuilder.blender_independent_packages.pykeentools_loader as pkt
from ..config import (Config, is_blender_supported, is_blender_too_old)
from .formatting import split_by_br_or_newlines
from ..preferences.progress import InstallationProgress


_ERROR_MESSAGES = {
    'WE_CANNOT_SHIP': [
        'We cannot ship our core library with our addon due to Blender ',
        'license limitations, so you need to install it yourself.'],

    'OLD_ADDON': [
        'You have most likely installed an outdated ',
        'version of FaceBuilder. Please download the latest one ',
        'from our web site: https://keentools.io '],

    'OLD_BLENDER': [
        'You are using an outdated version of Blender '
        'which we can\'t support. ',
        'Please install the latest official version '
        'of Blender downloaded from their site.'],

    'UNSUPPORTED_PYTHON': [
        'You are probably using Blender with unsupported ',
        'version of Python built in. Please install an official ',
        'version of Blender.'],

    'PYKEENTOOLS_CONFLICT': [
        'There is conflict with keentools core library namespace.',
        'You have to restart Blender before continue installation.'],

    'NOT_INSTALLED': [
        'Installation error: ',
        'Core library is not installed'],

    'CANNOT_IMPORT': [
        'Installation error: ',
        'The installed core is corrupted. ',
        'Please remove the addon, install it again, ',
        'and then install the proper core library '
        'package again'],

    'NO_VERSION': [
        'Installation error: ',
        'The installed core is corrupted. ',
        'Please remove the addon, install it again, ',
        'and then install the proper core library '
        'package again.'],

    'VERSION_PROBLEM': [
        'Installation error: ',
        'The installed core library is outdated. '
        'You can experience issues. ',
        'We recommend you to update the addon '
        'and the core library.'],

    'OK': ['The core library have been installed successfully'],

    'UNKNOWN': ['Unknown error']
}


def _multi_line_text_to_output_labels(layout, txt):
    if txt is None:
        return

    all_lines = split_by_br_or_newlines(txt)
    non_empty_lines = filter(len, all_lines)

    col = layout.column()
    col.scale_y = Config.text_scale_y
    for text_line in non_empty_lines:
        col.label(text=text_line)


def _split_long_string(txt, length=80):
    return [txt[i:i + length] for i in range(0, len(txt), length)]


class FBAddonPreferences(bpy.types.AddonPreferences):
    bl_idname = Config.addon_name

    license_accepted: bpy.props.BoolProperty(
        name='I have read and I agree to KeenTools End-user License Agreement',
        default=False
    )

    license_id: bpy.props.StringProperty(
        name="License ID", default=""
    )

    license_server: bpy.props.StringProperty(
        name="License Server host/IP", default="localhost"
    )

    license_server_port: bpy.props.IntProperty(
        name="License Server port", default=7096, min=0, max=65535
    )

    license_server_lock: bpy.props.BoolProperty(
        name="Variables from ENV", default=False
    )

    license_server_auto: bpy.props.BoolProperty(
        name="Auto settings from Environment", default=True
    )

    hardware_id: bpy.props.StringProperty(
        name="Hardware ID", default=""
    )

    lic_type: bpy.props.EnumProperty(
        name="Type",
        items=(
            ('ONLINE', "Online", "Online license management", 0),
            ('OFFLINE', "Offline", "Offline license management", 1),
            ('FLOATING', "Floating", "Floating license management", 2)),
        default='ONLINE')

    install_type: bpy.props.EnumProperty(
        name="Type",
        items=(
            ('ONLINE', "Online", "Online installation", 0),
            ('OFFLINE', "Offline", "Offline installation", 1)),
        default='ONLINE')

    lic_status: bpy.props.StringProperty(
        name="license status", default=""
    )

    lic_path: bpy.props.StringProperty(
            name="License file path",
            description="absolute path to license file",
            default="",
            subtype="FILE_PATH"
    )

    def _license_was_accepted(self):
        return pkt.is_installed() or self.license_accepted

    def _draw_license_info(self, layout):
        layout.label(text='License info:')
        box = layout.box()

        lm = pkt.module().FaceBuilder.license_manager()

        _multi_line_text_to_output_labels(box, lm.license_status_text(force_check=False))

        box.row().prop(self, "lic_type", expand=True)

        if self.lic_type == 'ONLINE':
            box = layout.box()
            row = box.split(factor=0.85)
            row.prop(self, "license_id")
            install_online_op = row.operator(preferences_operators.PREF_OT_InstallLicenseOnline.bl_idname)
            install_online_op.license_id = self.license_id

        elif self.lic_type == 'OFFLINE':
            self.hardware_id = lm.hardware_id()

            row = layout.split(factor=0.65)
            row.label(text="Get an activated license file at our site:")
            row.operator(
                preferences_operators.PREF_OT_OpenManualInstallPage.bl_idname,
                icon='URL')

            box = layout.box()
            row = box.split(factor=0.85)
            row.prop(self, "hardware_id")
            row.operator(preferences_operators.PREF_OT_CopyHardwareId.bl_idname)

            row = box.split(factor=0.85)
            row.prop(self, "lic_path")
            install_offline_op = row.operator(preferences_operators.PREF_OT_InstallLicenseOffline.bl_idname)
            install_offline_op.lic_path = self.lic_path

        elif self.lic_type == 'FLOATING':
            env = pkt.module().LicenseManager.env_server_info()
            if env is not None:
                self.license_server = env[0]
                self.license_server_port = env[1]
                self.license_server_lock = True
            else:
                self.license_server_lock = False

            box = layout.box()
            row = box.split(factor=0.35)
            row.label(text="License Server host/IP")
            if self.license_server_lock and self.license_server_auto:
                row.label(text=self.license_server)
            else:
                row.prop(self, "license_server", text="")

            row = box.split(factor=0.35)
            row.label(text="License Server port")
            if self.license_server_lock and self.license_server_auto:
                row.label(text=str(self.license_server_port))
            else:
                row.prop(self, "license_server_port", text="")

            if self.license_server_lock:
                box.prop(self, "license_server_auto",
                         text="Auto server/port settings")

            floating_install_op = row.operator(preferences_operators.PREF_OT_FloatingConnect.bl_idname)
            floating_install_op.license_server = self.license_server
            floating_install_op.license_server_port = self.license_server_port

    def _draw_warning_labels(self, layout, content, alert=True, icon='INFO'):
        col = layout.column()
        col.alert = alert
        col.scale_y = Config.text_scale_y
        for i, c in enumerate(content):
            icon_first = icon if i == 0 else 'BLANK1'
            col.label(text=c, icon=icon_first)
        return col

    def _draw_download_install_buttons(self, layout):
        # Install online / Install from disk / Download
        row = layout.split(factor=0.35)
        box2 = row.box()
        row2 = box2.row()
        if not self.license_accepted:
            row2.active = False
            # row2.alert = True

        op = row2.operator(
            preferences_operators.PREF_OT_InstallPkt.bl_idname,
            text='Install online', icon='WORLD')
        op.license_accepted = self._license_was_accepted()

        box2 = row.box()
        row2 = box2.split(factor=0.6)
        if not self.license_accepted:
            row2.active = False
            # row2.alert = True

        op = row2.operator(
            preferences_operators.PREF_OT_InstallFromFilePkt.bl_idname,
            text='Install from disk', icon='FILEBROWSER')
        op.license_accepted = self._license_was_accepted()

        op = row2.operator(
            preferences_operators.PREF_OT_DownloadsURL.bl_idname,
            text='Download', icon='URL')
        op.url = Config.core_download_website_url

    def _draw_please_accept_license(self, layout):
        box = layout.box()
        self._draw_warning_labels(box, _ERROR_MESSAGES['WE_CANNOT_SHIP'])

        box2 = box.box()
        row = box2.split(factor=0.85)
        row.prop(self, 'license_accepted')

        row.operator(
            preferences_operators.PREF_OT_OpenPktLicensePage.bl_idname,
            text='Read', icon='URL'
        )

        self._draw_download_install_buttons(box)
        return box

    def _draw_accepted_license(self, layout):
        box = layout.box()
        row = box.split(factor=0.75)
        row.label(text='KeenTools End-User License Agreement [accepted]')
        row.operator(
            preferences_operators.PREF_OT_OpenPktLicensePage.bl_idname,
            text='Read', icon='URL')
        return box

    def _draw_download_progress(self, layout):
        col = layout.column()
        col.scale_y = Config.text_scale_y
        download_state = InstallationProgress.get_state()
        if download_state['active']:
            col.label(text="Downloading: {:.1f}%".format(
                100 * download_state['progress']))
        if download_state['status'] is not None:
            col.label(text="{}".format(download_state['status']))

    def _draw_pkt_detail_report(self, layout):
        state, status = pkt.installation_status()

        status = status if status in _ERROR_MESSAGES.keys() else 'UNKNOWN'
        self._draw_warning_labels(
            layout, _ERROR_MESSAGES[status], alert=True, icon='ERROR')

        if status in ('CANNOT_IMPORT', 'NO_VERSION', 'VERSION_PROBLEM'):
            # Core Uninstall button
            layout.operator(Config.fb_uninstall_core_idname)

    def _draw_version(self, layout):
        box = layout.box()
        try:
            arr = ["Version {}, built {}".format(pkt.module().__version__,
                                                 pkt.module().build_time),
                   'The core library have been installed successfully']
            self._draw_warning_labels(box, arr, alert=False, icon='INFO')
            return box
        except Exception:
            pass

        self._draw_pkt_detail_report(box)
        self._draw_system_info(layout)
        return box

    def _draw_old_addon(self, layout):
        box = layout.box()
        self._draw_warning_labels(box, _ERROR_MESSAGES['OLD_ADDON'])
        return box

    def _draw_wrong_blender(self, layout):
        box = layout.box()
        self._draw_warning_labels(box, _ERROR_MESSAGES['UNSUPPORTED_PYTHON'])
        return box

    def _draw_blender_too_old(self, layout):
        box = layout.box()
        self._draw_warning_labels(box, _ERROR_MESSAGES['OLD_BLENDER'])
        return box

    def _draw_unsupported_python(self, layout):
        if is_blender_supported():
            self._draw_wrong_blender(layout)
        else:
            self._draw_old_addon(layout)
            row = layout.split(factor=0.35)
            op = row.operator(
                preferences_operators.PREF_OT_DownloadsURL.bl_idname,
                text='Download', icon='URL')
            op.url = Config.core_download_website_url

    def _draw_problem_library(self, layout):
        col = layout.column()
        col.scale_y = Config.text_scale_y
        if 'pykeentools' in sys.modules:
            arr = _split_long_string(str(sys.modules['pykeentools']))
            for t in arr:
                col.label(text=t)
        return col

    def _draw_please_restart(self, layout):
        box = layout.box()
        self._draw_warning_labels(box, _ERROR_MESSAGES['PYKEENTOOLS_CONFLICT'])
        return box

    def _draw_system_info(self, layout):
        box = layout.box()
        col = box.column()
        col.scale_y = Config.text_scale_y
        col.label(
            text="Blender version: {} API: {}.{}.{}".format(
                bpy.app.version_string, *bpy.app.version))
        col.label(text="Python: {}".format(sys.version))
        import platform
        arch = platform.architecture()
        col.label(text="Platform: {} / {}".format(arch[1], arch[0]))
        return box

    def draw(self, context):
        layout = self.layout

        if is_blender_too_old():
            self._draw_blender_too_old(layout)
            self._draw_system_info(layout)
            return

        if not pkt.is_python_supported():
            self._draw_unsupported_python(layout)
            self._draw_system_info(layout)
            return

        if pkt.is_installed():
            self._draw_version(layout)
            # self._draw_license_info(layout)
        else:
            if pkt.loaded():
                box = self._draw_please_restart(layout)
                self._draw_problem_library(box)
                self._draw_system_info(layout)
                return

            self._draw_please_accept_license(layout)

        self._draw_download_progress(layout)
