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
import keentools_facebuilder.blender_independent_packages.pykeentools_loader as pkt
import keentools_facebuilder.config
from .formatting import replace_newlines_with_spaces


_ID_NAME_PREFIX = 'preferences'


class OBJECT_OT_OpenPktLicensePage(bpy.types.Operator):
    bl_idname = _ID_NAME_PREFIX + '.open_pkt_license_page'
    bl_label = 'read license'
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = "Open KeenTools license via web-browser"

    def execute(self, context):
        bpy.ops.wm.url_open(url=keentools_facebuilder.config.Config.pykeentools_license_url)
        return {'FINISHED'}


class OBJECT_OT_InstallPkt(bpy.types.Operator):
    bl_idname = _ID_NAME_PREFIX + '.install_latest_pkt'
    bl_label = 'install from website'
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = 'Install pytkeentools from web-site ' \
                     '(configured SSL in OS is required)'

    install_type: bpy.props.EnumProperty(
        name='Build',
        items=(
            ('default', 'Default', 'Install the version this addon was tested with', 0),
            ('nightly', 'Nightly', 'Install latest nightly build available', 1)
        ),
        default='default'
    )

    license_accepted: bpy.props.BoolProperty()

    def invoke(self, context, event):
        if self.license_accepted:
            return context.window_manager.invoke_props_dialog(self)
        else:
            self.report({'ERROR'}, 'Please accept license before running installation')
            return {'FINISHED'}

    def execute(self, context):
        context.window_manager.progress_begin(0, 1)
        try:
            if self.install_type == 'nightly':
                pkt.install_from_download(nightly=True,
                                          progress_callback=context.window_manager.progress_update)
            elif self.install_type == 'default':
                pkt.install_from_download(version=pkt.MINIMUM_VERSION_REQUIRED,
                                          progress_callback=context.window_manager.progress_update)
                self.report({'INFO'}, 'Installation successful')
        except Exception as error:
            self.report({'ERROR'}, 'Failed to install pykeentools from website. ' + str(error))
        finally:
            context.window_manager.progress_end()
        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        layout.prop(self, 'install_type')


class OBJECT_OT_InstallFromFilePkt(bpy.types.Operator):
    bl_idname = _ID_NAME_PREFIX + '.install_pkt_from_file'
    bl_label = 'install from file'
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = 'You can download pykeentools manually ' \
                     'and install it here'

    # can only have exactly that name
    filepath: bpy.props.StringProperty(
            name='',
            description='absolute path to pykeentools zip file',
            default='',
            subtype='FILE_PATH'
    )

    license_accepted: bpy.props.BoolProperty()

    def invoke(self, context, event):
        if self.license_accepted:
            context.window_manager.fileselect_add(self)
            return {'RUNNING_MODAL'}
        else:
            self.report({'ERROR'}, 'Please accept license before running installation')
            return {'FINISHED'}

    def execute(self, context):
        try:
            pkt.install_from_file(self.filepath)
            self.report({'INFO'}, 'Installation successful')
        except Exception as error:
            self.report({'ERROR'}, 'Failed to install pykeentools from file. ' + str(error))
        return {'FINISHED'}


class OBJECT_OT_OpenManualInstallPage(bpy.types.Operator):
    bl_idname = _ID_NAME_PREFIX + '.open_manual_install_page'
    bl_label = 'open license activation webpage'
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = 'Open license activation webpage in browser'

    def execute(self, context):
        bpy.ops.wm.url_open(url=keentools_facebuilder.config.Config.manual_install_url)
        return {'FINISHED'}


class OBJECT_OT_CopyHardwareId(bpy.types.Operator):
    bl_idname = _ID_NAME_PREFIX + '.lic_hardware_id_copy'
    bl_label = 'copy'
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = 'Copy Hardware ID to clipboard'

    def execute(self, context):
        hardware_id = pkt.module().FaceBuilder.license_manager().hardware_id()
        context.window_manager.clipboard = hardware_id
        self.report({'INFO'}, 'Hardware ID is in clipboard!')
        return {'FINISHED'}


class OBJECT_OT_InstallLicenseOnline(bpy.types.Operator):
    bl_idname = _ID_NAME_PREFIX + '.lic_online_install'
    bl_label = 'install'
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = 'Install online license'

    license_id: bpy.props.StringProperty()

    def execute(self, context):
        lm = pkt.module().FaceBuilder.license_manager()
        res = lm.install_license_online(self.license_id)

        if res is not None:
            self.report({'ERROR'}, replace_newlines_with_spaces(res))
        else:
            self.report({'INFO'}, 'License installed')
        return {'FINISHED'}


class OBJECT_OT_InstallLicenseOffline(bpy.types.Operator):
    bl_idname = _ID_NAME_PREFIX + '.lic_offline_install'
    bl_label = 'install'
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = 'Install offline license'

    lic_path: bpy.props.StringProperty()

    def execute(self, context):
        lm = pkt.module().FaceBuilder.license_manager()
        res = lm.install_license_offline(self.lic_path)

        if res is not None:
            self.report({'ERROR'}, replace_newlines_with_spaces(res))
        else:
            self.report({'INFO'}, 'License installed')
        return {'FINISHED'}


class OBJECT_OT_FloatingConnect(bpy.types.Operator):
    bl_idname = _ID_NAME_PREFIX + '.lic_floating_connect'
    bl_label = 'connect'
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = 'Connect to floating license server'

    license_server: bpy.props.StringProperty()
    license_server_port: bpy.props.IntProperty()

    def execute(self, context):
        lm = pkt.module().FaceBuilder.license_manager()
        res = lm.install_floating_license(self.license_server, self.license_server_port)

        if res is not None:
            self.report({'ERROR'}, replace_newlines_with_spaces(res))
        else:
            self.report({'INFO'}, 'Floating server settings saved')
        return {'FINISHED'}


class OBJECT_OT_ShowURL(bpy.types.Operator):
    bl_idname = _ID_NAME_PREFIX + '.show_url'
    bl_label = 'Show URL'
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = 'Show URL for manual use'

    url: bpy.props.StringProperty(name='URL', default='')

    def draw(self, context):
        layout = self.layout
        layout.prop(self, 'url')

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        return {'FINISHED'}
