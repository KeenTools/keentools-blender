# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2019-2022 KeenTools

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

from typing import Dict
from collections import namedtuple

from .addon_config import Config, ErrorType


Button = namedtuple('Button', ['label', 'description'])

buttons = {
    # Preferences
    Config.kt_open_pkt_license_page_idname: Button(
        'read license',
        'Open KeenTools license in web browser'
    ),
    Config.kt_install_latest_pkt_idname: Button(
        'Install online',
        'Install Core library from website'
    ),
    Config.kt_install_pkt_from_file_with_warning_idname: Button(
        'Please confirm installation',
        ''
    ),
    Config.kt_install_pkt_from_file_idname: Button(
        'Install from file',
        'You can download Core library manually '
        'and install it using this button'
    ),
    Config.kt_open_manual_install_page_idname: Button(
        'Open in web browser',
        'Open license activation webpage in browser'
    ),
    Config.kt_copy_hardware_id_idname: Button(
        'Copy',
        'Copy Hardware ID to clipboard'
    ),
    Config.kt_install_license_online_idname: Button(
        'Activate',
        'Install online license'
    ),
    Config.kt_install_license_offline_idname: Button(
        'Install',
        'Install offline license'
    ),
    Config.kt_floating_connect_idname: Button(
        'Connect',
        'Connect to floating license server'
    ),
    Config.kt_pref_open_url_idname: Button(
        'Open URL',
        'Open URL in web browser'
    ),
    Config.kt_pref_downloads_url_idname: Button(
        'Download',
        'Open downloads page in web browser'
    ),
    Config.kt_pref_computer_info_idname: Button(
        'Computer info',
        'Copy computer info to clipboard'
    ),
    Config.kt_addon_settings_idname: Button(
        'Addon Settings',
        'Open Addon Settings in Preferences window'
    ),
    Config.kt_addon_search_idname: Button(
        'Addon Search',
        'Open Addon Search in Preferences window'
    ),
    Config.kt_open_url_idname: Button(
        'Open URL',
        'Open URL in web browser'
    ),
    Config.kt_uninstall_core_idname: Button(
        'Uninstall Core',
        'Uninstall Core Library'
    ),
    # Updater
    Config.kt_download_the_update_idname: Button(
        'Download the update',
        'Download and install the latest version of FaceBuilder'
    ),
    Config.kt_remind_later_idname: Button(
        'Remind later',
        'Remind about this update tomorrow'
    ),
    Config.kt_skip_version_idname: Button(
        'Skip this version',
        'Skip this version'
    ),
    Config.kt_retry_download_the_update_idname: Button(
        'Retry download',
        'Try downloading again'
    ),
    Config.kt_come_back_to_update_idname: Button(
        'Cancel',
        'Cancel updating'
    ),
    Config.kt_install_updates_idname: Button(
        '',
        'Press to install the update and relaunch Blender'
    ),
    Config.kt_remind_install_later_idname: Button(
        'Remind install tomorrow',
        'Remind install tomorrow'
    ),
    Config.kt_skip_installation_idname: Button(
        'Skip installation',
        'Skip installation'
    ),
    # Common operators
    Config.kt_exit_localview_idname: Button(
        'Exit Local view',
        'Exit Local view'
    ),
}


ErrorMessage = namedtuple('ErrorMessage', ['width', 'message'])


_default_width = 400


error_messages: Dict = {
    ErrorType.NoLicense: ErrorMessage(_default_width, [
        'License is not found',
        ' ',
        'You have 0 days of trial left and there is no license installed',
        'or something wrong has happened with the installed license.',
        'Please check the license settings.'
    ]),
    ErrorType.SceneDamaged: ErrorMessage(_default_width, [
        'Scene was damaged',
        ' ',
        'Some objects created by FaceBuilder were missing from the scene.',
        'The scene was restored automatically.'
    ]),
    ErrorType.CannotReconstruct: ErrorMessage(_default_width, [
        'Reconstruction is impossible',
        ' ',
        'Object parameters are invalid or missing.'
    ]),
    ErrorType.CannotCreateObject: ErrorMessage(_default_width, [
        'Cannot create object',
        ' ',
        'An error occurred while creating an object.'
    ]),
    ErrorType.MeshCorrupted: ErrorMessage(_default_width, [
        'Wrong topology',
        ' ',
        'The FaceBuilder mesh is damaged and cannot be used.'
    ]),
    ErrorType.PktProblem: ErrorMessage(_default_width, [
        'KeenTools Core is missing',
        ' ',
        'You need to install KeenTools Core library before using KeenTools addon.'
    ]),
    ErrorType.PktModelProblem: ErrorMessage(_default_width, [
        'KeenTools Core corrupted',
        ' ',
        'Model data cannot be loaded. You need to reinstall KeenTools addon.'
    ]),
    ErrorType.DownloadingProblem: ErrorMessage(650, [
        'Downloading error',
        ' ',
        'An unknown error encountered. The downloaded files might be corrupted. ',
        'You can try downloading them again, '
        'restarting Blender or installing the update manually.',
        'If you want to manually update the add-on: remove the old add-on, ',
        'restart Blender and install the new version of the add-on.'
    ]),
    ErrorType.FBGracePeriod: ErrorMessage(_default_width, [
        'Sorry, there\'s a problem with your FaceBuilder subscription.',
        ' ',
        'If you\'re using \'Online\' mode, please check that your ',
        'payment method is still valid and you have sufficient funds on your account.',
        'We\'ll try to charge the subscription fee again in the next couple of days.',
        ' ',
        'If you\'re using \'Offline\' mode and have generated the license file manually,',
        'it\'s time to renew the file. Please log in to User Portal, ',
        'download a new file and activate it as you did before.'
    ]),
    ErrorType.GTGracePeriod: ErrorMessage(_default_width, [
        'Sorry, there\'s a problem with your GeoTracker subscription.',
        ' ',
        'If you\'re using \'Online\' mode, please check that your ',
        'payment method is still valid and you have sufficient funds on your account.',
        'We\'ll try to charge the subscription fee again in the next couple of days.',
        ' ',
        'If you\'re using \'Offline\' mode and have generated the license file manually,',
        'it\'s time to renew the file. Please log in to User Portal, ',
        'download a new file and activate it as you did before.'
    ]),
    ErrorType.ShaderProblem: ErrorMessage(_default_width, [
        'Shader problem',
        ' ',
        'Something happened during shader compilation.',
        'See the System Console to get a detailed error information.'
    ]),
    ErrorType.UnsupportedGPUBackend: ErrorMessage(_default_width, [
        'GPU-backend is not supported',
        ' ',
        'Error (1120): this version of addon does not support Metal shaders. ',
        'You won\'t be able to use its full functionality ',
        'until you change the back-end to OpenGL.',
        ' ',
        'You can switch to OpenGL back-end in Blender Preferences -> System.',
        'Just select \'OpenGL\' instead of \'Metal\' in dropdown menu.',
        'Then you must restart Blender to apply these changes.',
        ' ',
        'We are working hard to support new shaders in our next versions '
        'of the addon.'
    ]),
}
