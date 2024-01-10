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

from typing import Any, List

from bpy.types import Operator
from bpy.props import BoolProperty, StringProperty, IntProperty

from ..utils.common_operators import KT_OT_OpenURLBase
from ..utils.kt_logging import KTLogger
from ..blender_independent_packages.pykeentools_loader import (
    module as pkt_module,
    core_filename_info as pkt_core_filename_info,
    MINIMUM_VERSION_REQUIRED as pkt_MINIMUM_VERSION_REQUIRED,
    os_name as pkt_os_name)
from ..addon_config import (Config,
                            get_operator,
                            get_addon_preferences,
                            ProductType)
from .formatting import replace_newlines_with_spaces
from ..preferences.progress import InstallationProgress
from ..messages import get_system_info, get_gpu_info
from ..utils.bpy_common import bpy_url_open
from ..ui_strings import buttons


_log = KTLogger(__name__)


_please_accept_eula = 'You need to accept our EULA before installation'


def get_product_license_manager(product: int) -> Any:
    if product == ProductType.FACEBUILDER:
        return pkt_module().FaceBuilder.license_manager()
    elif product == ProductType.GEOTRACKER:
        return pkt_module().GeoTracker.license_manager()
    elif product == ProductType.FACETRACKER:
        return pkt_module().FaceTracker.license_manager()
    assert False, 'get_product_license_manager Wrong product ID'


def _get_hardware_id(product: int = ProductType.FACEBUILDER) -> str:
    lm = get_product_license_manager(product)
    return lm.hardware_id()


def _get_addon_and_core_version_info() -> List[str]:
    txt_arr = []
    try:
        txt_arr.append(f'Addon: {Config.addon_name} {Config.addon_version}')
        txt_arr.append(f'Core version {pkt_module().__version__}, '
                       f'built {pkt_module().build_time}')
    except Exception as err:
        txt_arr.append(str(err))
    return txt_arr


class KTPREF_OT_OpenPktLicensePage(Operator):
    bl_idname = Config.kt_open_pkt_license_page_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        bpy_url_open(url=Config.pykeentools_license_url)
        return {'FINISHED'}


class KTPREF_OT_InstallPkt(Operator):
    bl_idname = Config.kt_install_latest_pkt_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'INTERNAL'}

    license_accepted: BoolProperty()

    def invoke(self, context, event):
        if self.license_accepted:
            return self.execute(context)
        else:
            self.report({'ERROR'}, _please_accept_eula)
            return {'FINISHED'}

    def execute(self, context):
        InstallationProgress.start_download()
        return {'FINISHED'}


class KTPREF_OT_InstalFromFilePktWithWarning(Operator):
    bl_idname = Config.kt_install_pkt_from_file_with_warning_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'INTERNAL'}

    filepath: StringProperty()
    filename: StringProperty()
    warning: StringProperty()
    confirm_install: BoolProperty(
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


class KTPREF_OT_InstallFromFilePkt(Operator):
    bl_idname = Config.kt_install_pkt_from_file_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'INTERNAL'}

    filter_glob: StringProperty(
        default='*.zip',
        options={'HIDDEN'}
    )

    # can only have exactly that name
    filepath: StringProperty(
            name='',
            description='absolute path to keentools core zip file',
            default='',
            subtype='FILE_PATH'
    )

    license_accepted: BoolProperty()

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


class KTPREF_OT_OpenManualInstallPage(Operator):
    bl_idname = Config.kt_open_manual_install_page_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'INTERNAL'}

    product: IntProperty(default=ProductType.UNDEFINED)

    def execute(self, context):
        hardware_id = _get_hardware_id(self.product)
        bpy_url_open(url=Config.manual_install_url + '#' + hardware_id)
        return {'FINISHED'}


class KTPREF_OT_CopyHardwareId(Operator):
    bl_idname = Config.kt_copy_hardware_id_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        hardware_id = _get_hardware_id()
        context.window_manager.clipboard = hardware_id
        self.report({'INFO'}, 'Hardware ID is in clipboard!')
        return {'FINISHED'}


class KTPREF_OT_InstallLicenseOnline(Operator):
    bl_idname = Config.kt_install_license_online_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'INTERNAL'}

    product: IntProperty(default=ProductType.UNDEFINED)
    license_key: StringProperty()

    def _clear_license_key(self):
        prefs = get_addon_preferences()
        if self.product == ProductType.FACEBUILDER:
            prefs.fb_license_key = ''
        elif self.product == ProductType.GEOTRACKER:
            prefs.gt_license_key = ''

    def execute(self, context):
        _log.info('Start InstallLicenseOnline')
        lm = get_product_license_manager(self.product)
        res = lm.install_license_online(self.license_key)

        if res is not None:
            _log.error(f'InstallLicenseOnline error:\n{res}')
            self.report({'ERROR'}, replace_newlines_with_spaces(res))
            return {'CANCELLED'}

        res_tuple = lm.perform_license_and_trial_check(
            strategy=pkt_module().LicenseCheckStrategy.FORCE)
        lic_status = res_tuple[0].license_status
        if lic_status.status == 'failed':
            _log.error(f'InstallLicenseOnline license check '
                       f'error:\n{lic_status.message}')
            self.report({'ERROR'},
                        replace_newlines_with_spaces(lic_status.message))
            return {'CANCELLED'}

        self._clear_license_key()
        msg = 'License installed online'
        _log.info(msg)
        self.report({'INFO'}, msg)
        return {'FINISHED'}


class KTPREF_OT_InstallLicenseOffline(Operator):
    bl_idname = Config.kt_install_license_offline_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'INTERNAL'}

    product: IntProperty(default=ProductType.UNDEFINED)
    lic_path: StringProperty()

    def _clear_license_path(self):
        pref = get_addon_preferences()
        pref.fb_lic_path = ''

    def execute(self, context):
        _log.info('Start InstallLicenseOffline')
        lm = get_product_license_manager(self.product)
        res = lm.install_license_offline(self.lic_path)

        if res is not None:
            _log.error(f'InstallLicenseOffline error: {res}')
            self.report({'ERROR'}, replace_newlines_with_spaces(res))
            return {'CANCELLED'}

        res_tuple = lm.perform_license_and_trial_check(
            strategy=pkt_module().LicenseCheckStrategy.FORCE)
        lic_status = res_tuple[0].license_status
        if lic_status.status == 'failed':
            _log.error(f'InstallLicenseOffline license check error: '
                       f'{lic_status.message}')
            self.report({'ERROR'},
                        replace_newlines_with_spaces(lic_status.message))
            return {'CANCELLED'}

        self._clear_license_path()
        msg = 'License installed offline'
        _log.info(msg)
        self.report({'INFO'}, msg)
        return {'FINISHED'}


class KTPREF_OT_FloatingConnect(Operator):
    bl_idname = Config.kt_floating_connect_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'INTERNAL'}

    product: IntProperty(default=ProductType.UNDEFINED)
    license_server: StringProperty()
    license_server_port: IntProperty()

    def execute(self, context):
        _log.info('Start FloatingConnect')
        lm = get_product_license_manager(self.product)
        res = lm.install_floating_license(self.license_server,
                                          self.license_server_port)
        if res is not None:
            _log.error(f'FloatingConnect error: {res}')
            self.report({'ERROR'}, replace_newlines_with_spaces(res))
            return {'CANCELLED'}

        res_tuple = lm.perform_license_and_trial_check(
            strategy=pkt_module().LicenseCheckStrategy.FORCE)
        lic_status = res_tuple[0].floating_status
        if lic_status.status == 'failed':
            _log.error(f'FloatingConnect license check error: '
                       f'{lic_status.message}')
            self.report({'ERROR'},
                        replace_newlines_with_spaces(lic_status.message))
            return {'CANCELLED'}

        msg = 'Floating server settings saved'
        _log.info(msg)
        self.report({'INFO'}, msg)
        return {'FINISHED'}


class KTPREF_OT_OpenURL(KT_OT_OpenURLBase, Operator):
    bl_idname = Config.kt_pref_open_url_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description


class KTPREF_OT_DownloadsURL(KT_OT_OpenURLBase, Operator):
    bl_idname = Config.kt_pref_downloads_url_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description


class KTPREF_OT_ComputerInfo(Operator):
    bl_idname = Config.kt_pref_computer_info_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        addon_info = ['---'] + _get_addon_and_core_version_info()
        system_info = ['---'] + get_system_info()
        gpu_info = ['---'] + get_gpu_info()
        all_info = '\n'.join(addon_info + system_info + gpu_info + ['---', ''])
        context.window_manager.clipboard = all_info
        _log.info('\n' + all_info)
        self.report({'INFO'}, 'Computer info is in clipboard!')
        return {'FINISHED'}


class KTPREFS_OT_UninstallCore(Operator):
    bl_idname = Config.kt_uninstall_core_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        from ..blender_independent_packages.pykeentools_loader import uninstall_core as pkt_uninstall
        _log.info('START CORE UNINSTALL')
        pkt_uninstall()
        _log.info('FINISH CORE UNINSTALL')
        return {'FINISHED'}
