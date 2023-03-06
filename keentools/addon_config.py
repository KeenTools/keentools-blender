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

from typing import Any, Callable, Optional, Tuple
import os

import bpy
from dataclasses import dataclass


_company = 'keentools'
_PT = 'KEENTOOLS_PT_'


class Config:
    addon_version = '2023.1.0'  # (5/5)
    supported_blender_versions = ((2, 80), (2, 81), (2, 82), (2, 83),
                                  (2, 90), (2, 91), (2, 92), (2, 93),
                                  (3, 0), (3, 1), (3, 2), (3, 3), (3, 4))
    minimal_blender_api = (2, 80, 60)

    fb_tab_category = 'FaceBuilder'
    gt_tab_category = 'GeoTracker'

    fb_global_var_name = 'keentools_fb_settings'
    gt_global_var_name = 'keentools_gt_settings'

    operators = 'keentools'
    prefs_operators = 'keentools_preferences'
    addon_name = __package__  # the same as module name

    old_facebuilder_addon_name = 'keentools_facebuilder'  # to remove

    updater_preferences_dict_name = 'keentools_updater'

    keentools_website_url = 'https://keentools.io'
    core_download_website_url = keentools_website_url + '/download/core'

    manual_install_url = keentools_website_url + '/manual-installation'
    pykeentools_license_url = 'https://link.keentools.io/eula'

    # Preferences operators
    kt_uninstall_core_idname = prefs_operators + '.uninstall_core'
    kt_open_pkt_license_page_idname = prefs_operators + '.open_pkt_license_page'
    kt_install_latest_pkt_idname = prefs_operators + '.install_latest_pkt'
    kt_install_pkt_from_file_with_warning_idname = \
        prefs_operators + '.install_pkt_from_file_with_warning'
    kt_install_pkt_from_file_idname = prefs_operators + '.install_pkt_from_file'
    kt_pref_open_url_idname = prefs_operators + '.open_url'
    kt_pref_downloads_url_idname = prefs_operators + '.downloads_url'
    kt_pref_computer_info_idname = prefs_operators + '.computer_info'

    kt_open_manual_install_page_idname = prefs_operators + '.gt_open_manual_install_page'
    kt_copy_hardware_id_idname = prefs_operators + '.copy_hardware_id'
    kt_install_license_online_idname = prefs_operators + '.install_license_online'
    kt_install_license_offline_idname = prefs_operators + '.install_license_offline'
    kt_floating_connect_idname = prefs_operators + '.floating_connect'

    kt_user_preferences_changer = operators + '.user_pref_changer'
    kt_user_preferences_reset_all_warning_idname = \
        operators + '.user_pref_reset_all_warning'
    # Common operators
    kt_addon_settings_idname = operators + '.addon_settings'
    kt_open_url_idname = operators + '.open_url'
    kt_addon_search_idname = operators + '.addon_search'
    kt_exit_localview_idname = operators + '.exit_localview'

    kt_warning_idname = operators + '.common_addon_warning'

    # Updater panels
    kt_update_panel_idname = _PT + 'update_panel'
    kt_download_notification_panel_idname = _PT + 'download_notification'
    kt_downloading_problem_panel_idname = _PT + 'downloading_problem'
    kt_updates_installation_panel_idname = _PT + 'updates_installation_panel'

    # Updater operators
    kt_download_the_update_idname = operators + '.download_the_update'
    kt_retry_download_the_update_idname = operators + '.retry_download_the_update'
    kt_remind_later_idname = operators + '.remind_later'
    kt_skip_version_idname = operators + '.skip_version'
    kt_come_back_to_update_idname = operators + '.come_back_to_update'
    kt_install_updates_idname = operators + '.install_updates'
    kt_remind_install_later_idname = operators + '.remind_install_later'
    kt_skip_installation_idname = operators + '.skip_installation'

    # Object Custom Properties
    core_version_prop_name = _company + '_version'
    viewport_state_prop_name = _company + '_viewport_state'

    # Constants
    surf_pin_size_scale = 0.85
    text_scale_y = 0.75
    btn_scale_y = 1.2

    default_tone_exposure = 0.0
    default_tone_gamma = 1.0

    default_updater_preferences = {
        'latest_show_datetime_update_reminder': {'value': '', 'type': 'string'},
        'latest_update_skip_version': {'value': '', 'type': 'string'},
        'updater_state': {'value': 1, 'type': 'int'},
        'downloaded_version': {'value': '', 'type': 'string'},
        'latest_installation_skip_version': {'value': '', 'type': 'string'},
        'latest_show_datetime_installation_reminder': {'value': '', 'type': 'string'}
    }
    user_preferences_dict_name = 'keentools_facebuilder_addon'
    default_user_preferences = {
        'pin_size': {'value': 7.0, 'type': 'float'},
        'pin_sensitivity': {'value': 16.0, 'type': 'float'},
        'prevent_fb_view_rotation': {'value': True, 'type': 'bool'},
        'fb_wireframe_color': {'value': (0.039, 0.04 , 0.039), 'type': 'color'},
        'fb_wireframe_special_color': {'value': (0.0, 0.0, 0.85098), 'type': 'color'},
        'fb_wireframe_midline_color': {'value': (0.960784, 0.007843, 0.615686), 'type': 'color'},
        'fb_wireframe_opacity': {'value': 0.5, 'type': 'float'},
        'prevent_gt_view_rotation': {'value': True, 'type': 'bool'},
        'gt_wireframe_color': {'value': (0.0, 1.0, 0.0), 'type': 'color'},
        'gt_wireframe_opacity': {'value': 0.5, 'type': 'float'},
        'gt_mask_3d_color': {'value': (0.0, 0.0, 1.0), 'type': 'color'},
        'gt_mask_3d_opacity': {'value': 0.4, 'type': 'float'},
        'gt_mask_2d_color': {'value': (0.0, 1.0, 0.0), 'type': 'color'},
        'gt_mask_2d_opacity': {'value': 0.35, 'type': 'float'},
    }

    mock_update_for_testing_flag = False
    mock_update_version = (int(addon_version.partition('.')[0]), 6, 3)
    mock_update_addon_path = 'http://localhost/addon.zip'
    mock_update_core_path = 'http://localhost/core.zip'
    mock_product = None

    hide_geotracker = not 'KEENTOOLS_ENABLE_BLENDER_GEOTRACKER' in os.environ
    allow_use_gpu_instead_of_bgl = False

    @classmethod
    def mock_update_for_testing(cls, value: bool=True, *,
                                ver: Optional[Tuple]=None,
                                addon_path: Optional[str]=None,
                                core_path: Optional[str]=None,
                                product: Optional[str]=None) -> None:
        if ver is not None:
            cls.mock_update_version = ver

        cls.mock_update_addon_path = addon_path
        cls.mock_update_core_path = core_path
        cls.mock_product = product
        cls.mock_update_for_testing_flag = value


def is_blender_supported() -> bool:
    ver = bpy.app.version
    for supported_ver in Config.supported_blender_versions:
        if ver[:len(supported_ver)] == supported_ver:
            return True
    return False


def get_addon_preferences() -> Any:
    return bpy.context.preferences.addons[Config.addon_name].preferences


def facebuilder_enabled() -> bool:
    prefs = get_addon_preferences()
    return prefs.facebuilder_enabled


def geotracker_enabled() -> bool:
    prefs = get_addon_preferences()
    return prefs.geotracker_enabled


def _get_fb_settings() -> Optional[Any]:
    name = Config.fb_global_var_name
    if not hasattr(bpy.context.scene, name):
        return None
    return getattr(bpy.context.scene, name)


def _get_gt_settings() -> Optional[Any]:
    name = Config.gt_global_var_name
    if not hasattr(bpy.context.scene, name):
        return None
    return getattr(bpy.context.scene, name)


fb_settings: Callable = _get_fb_settings
gt_settings: Callable = _get_gt_settings


def set_fb_settings_func(func: Callable) -> None:
    global fb_settings
    fb_settings = func


def set_gt_settings_func(func: Callable) -> None:
    global gt_settings
    gt_settings = func


def gt_pinmode() -> bool:
    if not geotracker_enabled():
        return False
    settings = _get_gt_settings()
    return settings.pinmode


def fb_pinmode() -> bool:
    if not facebuilder_enabled():
        return False
    settings = _get_fb_settings()
    return settings.pinmode


def addon_pinmode() -> bool:
    return fb_pinmode() or gt_pinmode()


def show_user_preferences(*, facebuilder: Optional[bool]=None,
                          geotracker: Optional[bool]=None) -> None:
    prefs = get_addon_preferences()
    if facebuilder is not None:
        prefs.show_fb_user_preferences = facebuilder
    if geotracker is not None:
        prefs.show_gt_user_preferences = geotracker


def show_tool_preferences(*, facebuilder: Optional[bool]=None,
                          geotracker: Optional[bool]=None) -> None:
    prefs = get_addon_preferences()
    if facebuilder is not None:
        prefs.facebuilder_expanded = facebuilder
    if geotracker is not None:
        prefs.geotracker_expanded = geotracker


def get_operator(operator_id_name: str) -> Any:
    def _rgetattr(obj, attr, *args):
        import functools
        def _getattr(obj, attr):
            return getattr(obj, attr, *args)
        return functools.reduce(_getattr, [obj] + attr.split('.'))
    return _rgetattr(bpy.ops, operator_id_name)


class ErrorType:
    Unknown = -1
    CustomMessage = 0
    NoLicense = 1
    SceneDamaged = 2
    CannotReconstruct = 3
    CannotCreateObject = 4
    MeshCorrupted = 5
    PktProblem = 6
    PktModelProblem = 7
    DownloadingProblem = 8
    FBGracePeriod = 9
    GTGracePeriod = 10


@dataclass(frozen=True)
class ActionStatus:
    success: bool = False
    error_message: str = None
