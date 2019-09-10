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
import keentools_facebuilder.preferences.operators as preferences_operators
import keentools_facebuilder.config
import keentools_facebuilder.blender_independent_packages.pykeentools_loader as pkt
from .formatting import split_by_br_or_newlines


def _multi_line_text_to_output_labels(layout, txt):
    if txt is None:
        return

    all_lines = split_by_br_or_newlines(txt)
    non_empty_lines = filter(len, all_lines)

    for text_line in non_empty_lines:
        layout.label(text=text_line)


class FBAddonPreferences(bpy.types.AddonPreferences):
    bl_idname = keentools_facebuilder.config.Config.addon_name

    license_accepted: bpy.props.BoolProperty(
        name='I have read and I agree to pykeentools End-user License Agreement',
        default=False
    )

    license_id: bpy.props.StringProperty(
        name="license ID", default=""
    )

    license_server: bpy.props.StringProperty(
        name="license server host/IP", default="localhost"
    )

    license_server_port: bpy.props.IntProperty(
        name="license server port", default=7096, min=0, max=65535
    )

    license_server_lock: bpy.props.BoolProperty(
        name="Variables from ENV", default=False
    )

    license_server_auto: bpy.props.BoolProperty(
        name="Auto settings from Environment", default=True
    )

    hardware_id: bpy.props.StringProperty(
        name="hardware ID", default=""
    )

    lic_type: bpy.props.EnumProperty(
        name="Type",
        items=(
            ('ONLINE', "Online", "Online license management", 0),
            ('OFFLINE', "Offline", "Offline license management", 1),
            ('FLOATING', "Floating", "Floating license management", 2)),
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

    def _draw_pykeentools_preferences(self, layout):
        box = layout.box()
        box.label(text='Pykeentools:')

        # if installed then license was accepted at some point before. Don't need to check again
        license_was_accepted = pkt.is_installed() or self.license_accepted

        if not license_was_accepted:
            box.prop(self, 'license_accepted')
            box.operator(preferences_operators.OBJECT_OT_OpenPktLicensePage.bl_idname)

        install_row = box.row()
        install_pkt_op = install_row.operator(preferences_operators.OBJECT_OT_InstallPkt.bl_idname)
        install_pkt_op.license_accepted = license_was_accepted
        install_from_file_pkt_op = install_row.operator(preferences_operators.OBJECT_OT_InstallFromFilePkt.bl_idname)
        install_from_file_pkt_op.license_accepted = license_was_accepted

        if pkt.is_installed():
            try:
                pkt.module()
                assert pkt.loaded()
                box.label(text="Build version '{}', build time '{}'".format(
                    pkt.module().__version__,
                    pkt.module().build_time))
            except ImportError:
                box.label(text='Failed to load pykeentools. Please check the installation')

    def _draw_license_info(self, layout):
        box = layout.box()
        box.label(text='License info:')

        if not pkt.loaded():
            box.label(text='install pykeentools to see license info')
            return

        lm = pkt.module().FaceBuilder.license_manager()

        _multi_line_text_to_output_labels(box, lm.license_status_text(force_check=False))

        box.row().prop(self, "lic_type", expand=True)

        if self.lic_type == 'ONLINE':
            box = layout.box()
            row = box.row()
            row.prop(self, "license_id")
            install_online_op = row.operator(preferences_operators.OBJECT_OT_InstallLicenseOnline.bl_idname)
            install_online_op.license_id = self.license_id

        elif self.lic_type == 'OFFLINE':
            self.hardware_id = lm.hardware_id()

            layout.label(text="Generate license file at our site and install it")
            row = layout.row()
            row.label(text="Visit our site: ")
            row.operator(preferences_operators.OBJECT_OT_OpenManualInstallPage.bl_idname)

            box = layout.box()
            row = box.row()
            row.prop(self, "hardware_id")
            row.operator(preferences_operators.OBJECT_OT_CopyHardwareId.bl_idname)

            row = box.row()
            row.prop(self, "lic_path")
            install_offline_op = row.operator(preferences_operators.OBJECT_OT_InstallLicenseOffline.bl_idname)
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
            row = box.row()
            row.label(text="license server host/IP")
            if self.license_server_lock and self.license_server_auto:
                row.label(text=self.license_server)
            else:
                row.prop(self, "license_server", text="")

            row = box.row()
            row.label(text="license server port")
            if self.license_server_lock and self.license_server_auto:
                row.label(text=str(self.license_server_port))
            else:
                row.prop(self, "license_server_port", text="")

            if self.license_server_lock:
                box.prop(self, "license_server_auto",
                         text="Auto server/port settings")

            floating_install_op = row.operator(preferences_operators.OBJECT_OT_FloatingConnect.bl_idname)
            floating_install_op.license_server = self.license_server
            floating_install_op.license_server_port = self.license_server_port

    def draw(self, context):
        layout = self.layout

        self._draw_license_info(layout)
        self._draw_pykeentools_preferences(layout)
