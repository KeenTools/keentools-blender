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
import keentools_facebuilder.blender_independent_packages.pykeentools_loader \
    as pkt
from keentools_facebuilder.config import Config
from .formatting import replace_newlines_with_spaces
from keentools_facebuilder.preferences.progress import InstallationProgress


_ID_NAME_PREFIX = 'preferences.' + Config.prefix
_please_accept_eula = 'You need to accept our EULA before installation'


class PREF_OT_OpenPktLicensePage(bpy.types.Operator):
    bl_idname = _ID_NAME_PREFIX + '_open_pkt_license_page'
    bl_label = 'read license'
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = "Open KeenTools license in web browser"

    def execute(self, context):
        bpy.ops.wm.url_open(url=Config.pykeentools_license_url)
        return {'FINISHED'}


class PREF_OT_InstallPkt(bpy.types.Operator):
    bl_idname = _ID_NAME_PREFIX + '_install_latest_pkt'
    bl_label = 'Install online'
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = 'Install Core library from website'

    install_type: bpy.props.EnumProperty(
        name='Version',
        items=(
            ('default', 'Latest Stable',
             'Install the latest stable version', 0),
            ('nightly', 'Nightly',
             'Install latest nightly build available. '
             'Be ready to experience bugs and glitches. '
             'Please report them', 1)
        ),
        default= 'default'
    )

    license_accepted: bpy.props.BoolProperty()

    def invoke(self, context, event):
        if self.license_accepted:
            return context.window_manager.invoke_props_dialog(self)
        else:
            self.report({'ERROR'}, _please_accept_eula)
            return {'FINISHED'}

    def execute(self, context):
        InstallationProgress.start_download(self.install_type)
        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        layout.prop(self, 'install_type')


class PREF_OT_InstallFromFilePkt(bpy.types.Operator):
    bl_idname = _ID_NAME_PREFIX + '_install_pkt_from_file'
    bl_label = 'Install from file'
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = 'You can download Core library manually ' \
                     'and install it using this button'

    filter_glob: bpy.props.StringProperty(
        default='*.zip',
        options={'HIDDEN'}
    )

    # can only have exactly that name
    filepath: bpy.props.StringProperty(
            name='',
            description='absolute path to pykeentools zip file',
            default='',
            subtype='FILE_PATH'
    )

    license_accepted: bpy.props.BoolProperty()

    def draw(self, context):
        layout = self.layout
        content = ["You can download",
                   "Core library from ",
                   "our site: keentools.io/downloads"]
        col = layout.column()
        col.scale_y = 0.75
        for c in content:
            col.label(text=c)

        op = layout.operator(
            PREF_OT_OpenURL.bl_idname,
            text='Open downloads page', icon='URL')
        op.url = 'https://keentools.io/downloads'

    def invoke(self, context, event):
        if self.license_accepted:
            context.window_manager.fileselect_add(self)
            return {'RUNNING_MODAL'}
        else:
            self.report({'ERROR'}, _please_accept_eula)
            return {'FINISHED'}

    def execute(self, context):
        InstallationProgress.start_zip_install(self.filepath)
        return {'FINISHED'}


class PREF_OT_OpenManualInstallPage(bpy.types.Operator):
    bl_idname = _ID_NAME_PREFIX + '_open_manual_install_page'
    bl_label = 'Open in web browser'
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = 'Open license activation webpage in browser'

    def execute(self, context):
        bpy.ops.wm.url_open(url=Config.manual_install_url)
        return {'FINISHED'}


class PREF_OT_CopyHardwareId(bpy.types.Operator):
    bl_idname = _ID_NAME_PREFIX + '_lic_hardware_id_copy'
    bl_label = 'Copy'
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = 'Copy Hardware ID to clipboard'

    def execute(self, context):
        hardware_id = pkt.module().FaceBuilder.license_manager().hardware_id()
        context.window_manager.clipboard = hardware_id
        self.report({'INFO'}, 'Hardware ID is in clipboard!')
        return {'FINISHED'}


class PREF_OT_InstallLicenseOnline(bpy.types.Operator):
    bl_idname = _ID_NAME_PREFIX + '_lic_online_install'
    bl_label = 'Install'
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


class PREF_OT_InstallLicenseOffline(bpy.types.Operator):
    bl_idname = _ID_NAME_PREFIX + '_lic_offline_install'
    bl_label = 'Install'
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


class PREF_OT_FloatingConnect(bpy.types.Operator):
    bl_idname = _ID_NAME_PREFIX + '_lic_floating_connect'
    bl_label = 'Connect'
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = 'Connect to floating license server'

    license_server: bpy.props.StringProperty()
    license_server_port: bpy.props.IntProperty()

    def execute(self, context):
        lm = pkt.module().FaceBuilder.license_manager()
        res = lm.install_floating_license(self.license_server,
                                          self.license_server_port)
        if res is not None:
            self.report({'ERROR'}, replace_newlines_with_spaces(res))
        else:
            self.report({'INFO'}, 'Floating server settings saved')
        return {'FINISHED'}


class PREF_OT_ShowURL(bpy.types.Operator):
    bl_idname = _ID_NAME_PREFIX + '_show_url'
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


class PREF_OT_OpenURL(bpy.types.Operator):
    bl_idname = _ID_NAME_PREFIX + '_open_url'
    bl_label = 'Open URL'
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = 'Open URL in web browser'

    url: bpy.props.StringProperty(name='URL', default='')

    def execute(self, context):
        bpy.ops.wm.url_open(url=self.url)
        return {'FINISHED'}


class PREF_OT_DownloadsURL(bpy.types.Operator):
    bl_idname = _ID_NAME_PREFIX + '_downloads_url'
    bl_label = 'Download'
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = 'Open downloads page in web browser'

    url: bpy.props.StringProperty(name='URL', default='')

    def execute(self, context):
        bpy.ops.wm.url_open(url=self.url)
        return {'FINISHED'}


class PREF_OT_ShowWhy(bpy.types.Operator):
    bl_idname = _ID_NAME_PREFIX + '_show_why'
    bl_label = ''
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = 'Find out why additional installation is needed'

    def draw(self, context):
        layout = self.layout
        layout.scale_y = 0.75

        content = ['We cannot ship our core library with addon '
                   'due to Blender license restrictions,',
                   'so you need to install it yourself.',
                   ' ',
                   'You have two options: automatic online '
                   'installation - our addon will ',
                   'try to download and install everything, '
                   'and manual offline installation - you',
                   'download required files and specify the paths.',
                   ' ']

        for t in content:
            layout.label(text=t)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=550)

    def execute(self, context):
        return {'FINISHED'}
