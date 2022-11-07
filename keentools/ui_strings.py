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
}