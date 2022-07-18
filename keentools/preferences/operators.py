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
import logging

import bpy

from ..blender_independent_packages.pykeentools_loader import (
    module as pkt_module,
    core_filename_info as pkt_core_filename_info,
    MINIMUM_VERSION_REQUIRED as pkt_MINIMUM_VERSION_REQUIRED,
    os_name as pkt_os_name)
from ..addon_config import Config, get_operator, get_addon_preferences
from .formatting import replace_newlines_with_spaces
from ..preferences.progress import InstallationProgress
from ..utils.ui_redraw import (force_ui_redraw,
                               find_modules_by_name_starting_with,
                               filter_module_list_by_name_starting_with,
                               collapse_all_modules,
                               mark_old_modules)
from ..messages import get_system_info, get_gpu_info


_please_accept_eula = 'You need to accept our EULA before installation'


def get_product_license_manager(product):
    if product == 'facebuilder':
        return pkt_module().FaceBuilder.license_manager()
    elif product == 'geotracker':
        return pkt_module().GeoTracker.license_manager()
    assert False, 'Wrong product ID'


def _get_hardware_id(product='facebuilder'):
    lm = get_product_license_manager(product)
    return lm.hardware_id()


def _get_addon_and_core_version_info():
    txt_arr = []
    try:
        txt_arr.append(f'Addon: {Config.addon_name} {Config.addon_version}')
        txt_arr.append(f'Core version {pkt_module().__version__}, '
                       f'built {pkt_module().build_time}')
    except Exception as err:
        txt_arr.append(str(err))
    return txt_arr


class KTPREF_OT_OpenPktLicensePage(bpy.types.Operator):
    bl_idname = Config.kt_open_pkt_license_page_idname
    bl_label = 'read license'
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = "Open KeenTools license in web browser"

    def execute(self, context):
        bpy.ops.wm.url_open(url=Config.pykeentools_license_url)
        return {'FINISHED'}


class KTPREF_OT_InstallPkt(bpy.types.Operator):
    bl_idname = Config.kt_install_latest_pkt_idname
    bl_label = 'Install online'
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = 'Install Core library from website'

    license_accepted: bpy.props.BoolProperty()

    def invoke(self, context, event):
        if self.license_accepted:
            return self.execute(context)
        else:
            self.report({'ERROR'}, _please_accept_eula)
            return {'FINISHED'}

    def execute(self, context):
        InstallationProgress.start_download()
        return {'FINISHED'}


class KTPREF_OT_InstalFromFilePktWithWarning(bpy.types.Operator):
    bl_idname = Config.kt_install_pkt_from_file_with_warning_idname
    bl_label = 'Please confirm installation'
    bl_options = {'REGISTER', 'INTERNAL'}

    filepath: bpy.props.StringProperty()
    filename: bpy.props.StringProperty()
    warning: bpy.props.StringProperty()
    confirm_install: bpy.props.BoolProperty(
        name='Install anyway', default=False)

    content = []

    def _report_canceled(self):
        self.report({'ERROR'}, 'Installation has been canceled '
                               'since it was not accepted')

    def draw(self, context):
        layout = self.layout.column()
        col = layout.column()
        col.scale_y = Config.text_scale_y
        col.alert = True
        col.label(text='You are trying to install "{}"'.format(self.filename))
        col.label(text=self.warning)
        col.label(text=' ')
        layout.prop(self, 'confirm_install')

    def execute(self, context):
        if not self.confirm_install:
            self._report_canceled()
            return {'CANCELLED'}

        InstallationProgress.start_zip_install(self.filepath)
        self.report({'INFO'}, 'The core library has been '
                              'installed successfully.')
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=600)


class KTPREF_OT_InstallFromFilePkt(bpy.types.Operator):
    bl_idname = Config.kt_install_pkt_from_file_idname
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
            description='absolute path to keentools core zip file',
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
        col.scale_y = Config.text_scale_y
        for txt_row in content:
            col.label(text=str(txt_row))

        op = layout.operator(Config.kt_pref_open_url_idname,
                             text='Open downloads page', icon='URL')
        op.url = Config.core_download_website_url

    def invoke(self, context, event):
        if self.license_accepted:
            context.window_manager.fileselect_add(self)
            return {'RUNNING_MODAL'}
        else:
            self.report({'ERROR'}, _please_accept_eula)
            return {'FINISHED'}

    def execute(self, context):
        filename_info = pkt_core_filename_info(self.filepath)
        warning = None

        if not filename_info.is_zip:
            warning = 'We distribute our Core Library as a ZIP-file. ' +\
                      'The selected file appears to be of a different type'
        elif not filename_info.is_keentools_core:
            warning = 'The selected file name appears to be different from Core library file name'
        elif filename_info.version != pkt_MINIMUM_VERSION_REQUIRED:
            def _version_to_string(version):
                return str(version[0]) + '.' + str(version[1]) + '.' +str(version[2])
            warning = 'Core library version %s doesn\'t match the add-on version %s' %\
                      (_version_to_string(filename_info.version),
                       _version_to_string(pkt_MINIMUM_VERSION_REQUIRED))
        elif filename_info.os != pkt_os_name():
            warning = 'Your OS is %s, you\'re trying to install the core library for %s' %\
                      (pkt_os_name(), filename_info.os)
        elif filename_info.is_nightly:
            warning = 'You\'re installing an unstable nightly build, is this what you really want?'

        if warning is not None:
            install_with_warning = get_operator(Config.kt_install_pkt_from_file_with_warning_idname)
            install_with_warning('INVOKE_DEFAULT',
                filepath=self.filepath, filename=filename_info.filename, warning=warning)
            return {'FINISHED'}

        InstallationProgress.start_zip_install(self.filepath)
        return {'FINISHED'}


class KTPREF_OT_OpenManualInstallPage(bpy.types.Operator):
    bl_idname = Config.kt_open_manual_install_page_idname
    bl_label = 'Open in web browser'
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = 'Open license activation webpage in browser'

    product: bpy.props.StringProperty(default='')

    def execute(self, context):
        hardware_id = _get_hardware_id(self.product)
        bpy.ops.wm.url_open(url=Config.manual_install_url + '#' + hardware_id)
        return {'FINISHED'}


class KTPREF_OT_CopyHardwareId(bpy.types.Operator):
    bl_idname = Config.kt_copy_hardware_id_idname
    bl_label = 'Copy'
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = 'Copy Hardware ID to clipboard'

    def execute(self, context):
        hardware_id = _get_hardware_id()
        context.window_manager.clipboard = hardware_id
        self.report({'INFO'}, 'Hardware ID is in clipboard!')
        return {'FINISHED'}


class KTPREF_OT_InstallLicenseOnline(bpy.types.Operator):
    bl_idname = Config.kt_install_license_online_idname
    bl_label = 'Activate'
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = 'Install online license'

    product: bpy.props.StringProperty(default='')
    license_key: bpy.props.StringProperty()

    def _clear_license_key(self):
        pref = get_addon_preferences()
        pref.license_key = ''

    def execute(self, context):
        logger = logging.getLogger(__name__)
        logger.info('Start InstallLicenseOnline')
        lm = get_product_license_manager(self.product)
        res = lm.install_license_online(self.license_key)

        if res is not None:
            logger.error('InstallLicenseOnline error: {}'.format(res))
            self.report({'ERROR'}, replace_newlines_with_spaces(res))
            return {'CANCELLED'}

        res_tuple = lm.perform_license_and_trial_check(
            strategy=pkt_module().LicenseCheckStrategy.FORCE)
        lic_status = res_tuple[0].license_status
        if lic_status.status == 'failed':
            logger.error('InstallLicenseOnline license check error: '
                         '{}'.format(lic_status.message))
            self.report({'ERROR'},
                        replace_newlines_with_spaces(lic_status.message))
            return {'CANCELLED'}

        self._clear_license_key()
        msg = 'License installed online'
        logger.info(msg)
        self.report({'INFO'}, msg)
        return {'FINISHED'}


class KTPREF_OT_InstallLicenseOffline(bpy.types.Operator):
    bl_idname = Config.kt_install_license_offline_idname
    bl_label = 'Install'
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = 'Install offline license'

    product: bpy.props.StringProperty(default='')
    lic_path: bpy.props.StringProperty()

    def _clear_license_path(self):
        pref = get_addon_preferences()
        pref.fb_lic_path = ''

    def execute(self, context):
        logger = logging.getLogger(__name__)
        logger.info('Start InstallLicenseOffline')
        lm = get_product_license_manager(self.product)
        res = lm.install_license_offline(self.lic_path)

        if res is not None:
            logger.error('InstallLicenseOffline error: {}'.format(res))
            self.report({'ERROR'}, replace_newlines_with_spaces(res))
            return {'CANCELLED'}

        res_tuple = lm.perform_license_and_trial_check(
            strategy=pkt_module().LicenseCheckStrategy.FORCE)
        lic_status = res_tuple[0].license_status
        if lic_status.status == 'failed':
            logger.error('InstallLicenseOffline license check error: '
                         '{}'.format(lic_status.message))
            self.report({'ERROR'},
                        replace_newlines_with_spaces(lic_status.message))
            return {'CANCELLED'}

        self._clear_license_path()
        msg = 'License installed offline'
        logger.info(msg)
        self.report({'INFO'}, msg)
        return {'FINISHED'}


class KTPREF_OT_FloatingConnect(bpy.types.Operator):
    bl_idname = Config.kt_floating_connect_idname
    bl_label = 'Connect'
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = 'Connect to floating license server'

    product: bpy.props.StringProperty(default='')
    license_server: bpy.props.StringProperty()
    license_server_port: bpy.props.IntProperty()

    def execute(self, context):
        logger = logging.getLogger(__name__)
        logger.info('Start FloatingConnect')
        lm = get_product_license_manager(self.product)
        res = lm.install_floating_license(self.license_server,
                                          self.license_server_port)
        if res is not None:
            logger.error('FloatingConnect error: {}'.format(res))
            self.report({'ERROR'}, replace_newlines_with_spaces(res))
            return {'CANCELLED'}

        res_tuple = lm.perform_license_and_trial_check(
            strategy=pkt_module().LicenseCheckStrategy.FORCE)
        lic_status = res_tuple[0].floating_status
        if lic_status.status == 'failed':
            logger.error('FloatingConnect license check error: '
                         '{}'.format(lic_status.message))
            self.report({'ERROR'},
                        replace_newlines_with_spaces(lic_status.message))
            return {'CANCELLED'}

        msg = 'Floating server settings saved'
        logger.info(msg)
        self.report({'INFO'}, msg)
        return {'FINISHED'}


class KTPREF_OT_OpenURL(bpy.types.Operator):
    bl_idname = Config.kt_pref_open_url_idname
    bl_label = 'Open URL'
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = 'Open URL in web browser'

    url: bpy.props.StringProperty(name='URL', default='')

    def execute(self, context):
        bpy.ops.wm.url_open(url=self.url)
        return {'FINISHED'}


class KTPREF_OT_DownloadsURL(bpy.types.Operator):
    bl_idname = Config.kt_pref_downloads_url_idname
    bl_label = 'Download'
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = 'Open downloads page in web browser'

    url: bpy.props.StringProperty(name='URL', default='')

    def execute(self, context):
        bpy.ops.wm.url_open(url=self.url)
        return {'FINISHED'}


class KTPREF_OT_ComputerInfo(bpy.types.Operator):
    bl_idname = Config.kt_pref_computer_info_idname
    bl_label = 'Computer info'
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = 'Copy computer info to clipboard'

    def execute(self, context):
        addon_info = ['---'] + _get_addon_and_core_version_info()
        system_info = ['---'] + get_system_info()
        gpu_info = ['---'] + get_gpu_info()
        all_info = '\n'.join(addon_info + system_info + gpu_info + ['---', ''])
        context.window_manager.clipboard = all_info
        logger = logging.getLogger(__name__)
        logger.info('\n' + all_info)
        self.report({'INFO'}, 'Computer info is in clipboard!')
        return {'FINISHED'}


class KT_OT_AddonSettings(bpy.types.Operator):
    bl_idname = Config.kt_addon_settings_idname
    bl_label = 'Addon Settings'
    bl_options = {'REGISTER'}
    bl_description = 'Open Addon Settings in Preferences window'

    def draw(self, context):
        pass

    def execute(self, context):
        bpy.ops.preferences.addon_show(module=Config.addon_name)
        return {'FINISHED'}


class KT_OT_AddonSearch(bpy.types.Operator):
    bl_idname = Config.kt_addon_search_idname
    bl_label = 'Addon Search'
    bl_options = {'REGISTER'}
    bl_description = 'Open Addon Search in Preferences window'

    search: bpy.props.StringProperty(default='KeenTools')

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


class KT_OT_OpenURL(bpy.types.Operator):
    bl_idname = Config.kt_open_url_idname
    bl_label = 'Open URL'
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = 'Open URL in web browser'

    url: bpy.props.StringProperty(name='URL', default='')

    def execute(self, context):
        bpy.ops.wm.url_open(url=self.url)
        return {'FINISHED'}


class KT_OT_UninstallCore(bpy.types.Operator):
    bl_idname = Config.kt_uninstall_core_idname
    bl_label = 'Uninstall Core'
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = 'Uninstall Core Library'

    def execute(self, context):
        logger = logging.getLogger(__name__)
        from ..blender_independent_packages.pykeentools_loader import uninstall_core as pkt_uninstall
        logger.debug("START CORE UNINSTALL")
        pkt_uninstall()
        logger.debug("FINISH CORE UNINSTALL")
        return {'FINISHED'}
