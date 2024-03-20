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
        'Press to download and install Core Library online'
    ),
    Config.kt_install_pkt_from_file_with_warning_idname: Button(
        'Please confirm installation',
        ''
    ),
    Config.kt_install_pkt_from_file_idname: Button(
        'Install from file',
        'Install Core Library offline'
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
        'Open Core Library download page in web browser'
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
        'Remind tomorrow',
        'Remind me to install tomorrow'
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
    Config.kt_share_feedback_idname: Button(
        'Share Feedback',
        'Send feedback. Help us improve'
    ),
    Config.kt_report_bug_idname: Button(
        'Report Bug',
        'Report a Bug'
    ),
}


ErrorMessage = namedtuple('ErrorMessage', ['width', 'message'])


_default_width = 400


error_messages: Dict = {
    ErrorType.Unknown: ErrorMessage(_default_width, [
        'Unknown error',
        ' ',
        'You should never see this error message. Let us now if it happened.'
    ]),
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
        'Error (1120): Looks like a backend problem. ',
        'This version of add-on supports OpenGL and Metal. ',
        'If you see this error, please contact our support. ',
        'We\'ll do our best to figure it out.'
    ]),
}
