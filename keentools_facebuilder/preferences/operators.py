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
import keentools_facebuilder.preferences.licmanager as licmanager
import keentools_facebuilder.blender_independent_packages.pykeentools_loader as pkt


_ID_NAME_PREFIX = 'preferences'


class OBJECT_OT_InstallPkt(bpy.types.Operator):
    bl_idname = _ID_NAME_PREFIX + '.install_latest_pkt'
    bl_label = 'install'
    bl_options = {'REGISTER', 'INTERNAL'}

    install_type: bpy.props.EnumProperty(
        name='Build',
        items=(
            ('nightly', 'Nightly', 'Install latest nightly build available', 0),
            ('default', 'Default', 'Install the version this addon was tested with', 1),
            ('latest', 'Latest', 'Install the latest release version available', 2)),
        default='nightly')

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        context.window_manager.progress_begin(0, 1)
        try:
            if self.install_type == 'nightly':
                pkt.install_from_download(nightly=True,
                                          progress_callback=context.window_manager.progress_update)
            elif self.install_type == 'default':
                pkt.install_from_download(version=pkt.MINIMUM_VERSION_REQUIRED,
                                          progress_callback=context.window_manager.progress_update)
            elif self.install_type == 'latest':
                pkt.install_from_download(progress_callback=context.window_manager.progress_update)
        finally:
            context.window_manager.progress_end()
        return {"FINISHED"}

    def draw(self, context):
        layout = self.layout
        layout.prop(self, 'install_type')


class OBJECT_OT_UninstallPkt(bpy.types.Operator):
    bl_idname = _ID_NAME_PREFIX + '.uninstall_pkt'
    bl_label = 'uninstall'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        pkt.uninstall()
        return {"FINISHED"}


class OBJECT_OT_LoadPkt(bpy.types.Operator):
    bl_idname = _ID_NAME_PREFIX + '.load_pkt'
    bl_label = 'load'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        pkt.module()
        return {"FINISHED"}


class OBJECT_OT_OpenManualInstallPage(bpy.types.Operator):
    bl_idname = _ID_NAME_PREFIX + '.open_manual_install_page'
    bl_label = 'open license activation webpage'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        bpy.ops.wm.url_open(url="https://keentools.io/manual-installation")
        return {"FINISHED"}


class OBJECT_OT_CopyHardwareId(bpy.types.Operator):
    bl_idname = _ID_NAME_PREFIX + '.lic_hardware_id_copy'
    bl_label = 'copy'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        licmanager.FBLicManager.copy_hardware_id()
        return {"FINISHED"}


class OBJECT_OT_InstallLicenseOnline(bpy.types.Operator):
    bl_idname = _ID_NAME_PREFIX + '.lic_online_install'
    bl_label = 'install'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        licmanager.FBLicManager.install_online_lic()
        return {"FINISHED"}


class OBJECT_OT_InstallLicenseOffline(bpy.types.Operator):
    bl_idname = _ID_NAME_PREFIX + '.lic_offline_install'
    bl_label = 'install'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        licmanager.FBLicManager.install_offline_lic()
        return {"FINISHED"}


class OBJECT_OT_FloatingConnect(bpy.types.Operator):
    bl_idname = _ID_NAME_PREFIX + '.lic_floating_connect'
    bl_label = 'connect'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        licmanager.FBLicManager.connect_floating_lic()
        return {"FINISHED"}
