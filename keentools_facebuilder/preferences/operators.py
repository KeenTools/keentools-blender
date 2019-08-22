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


class OBJECT_OT_InstallNightlyPkt(bpy.types.Operator):
    bl_idname = _ID_NAME_PREFIX + '.install_latest_nightly_pkt'
    bl_label = 'install latest nightly pykeentools'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        pkt.install_from_download(nightly=True)
        return {"FINISHED"}


class OBJECT_OT_UninstallPkt(bpy.types.Operator):
    bl_idname = _ID_NAME_PREFIX + '.uninstall_pkt'
    bl_label = 'uninstall pykeentools'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        pkt.uninstall()
        return {"FINISHED"}


class OBJECT_OT_LoadPkt(bpy.types.Operator):
    bl_idname = _ID_NAME_PREFIX + '.load_pkt'
    bl_label = 'load pykeentools'
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
