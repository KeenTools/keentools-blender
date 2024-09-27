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

from typing import Any, Callable, Optional, Tuple, Set, Dict, List
from dataclasses import dataclass
import os

import bpy
from bpy.types import Scene
from bpy.props import PointerProperty

from .utils.kt_logging import KTLogger
from .utils.version import BVersion


_log = KTLogger(__name__)


_PT = 'KEENTOOLS_PT_'


class Config:
    addon_version = '2024.2.2'  # (3/6)
    addon_version_tuple = tuple(map(int, addon_version.split('.')))
    supported_blender_versions = ((2, 80), (2, 81), (2, 82), (2, 83),
                                  (2, 90), (2, 91), (2, 92), (2, 93),
                                  (3, 0), (3, 1), (3, 2), (3, 3), (3, 4),
                                  (3, 5), (3, 6), (4, 0), (4, 1), (4, 2))
    minimal_blender_api = (2, 80, 60)

    fb_tab_category = 'FaceBuilder'
    gt_tab_category = 'GeoTracker'
    ft_tab_category = 'FaceTracker'

    kt_testing_tab_category = 'KeenTools Testing'

    fb_global_var_name = 'keentools_fb_settings'
    gt_global_var_name = 'keentools_gt_settings'
    ft_global_var_name = 'keentools_ft_settings'

    operators = 'keentools'
    prefs_operators = 'keentools_preferences'
    addon_name = 'KeenTools'  # human readable
    package = __package__  # the same as module name

    old_facebuilder_addon_name = 'keentools_facebuilder'  # to remove

    updater_preferences_dict_name = 'keentools_updater'

    keentools_website_url = 'https://keentools.io'
    core_download_website_url = keentools_website_url + '/download/core'

    manual_install_url = keentools_website_url + '/activate'
    pykeentools_license_url = 'https://link.keentools.io/eula'

    # Preferences operators
    kt_uninstall_core_idname = prefs_operators + '.uninstall_core'
    kt_open_pkt_license_page_idname = prefs_operators + '.open_pkt_license_page'
    kt_install_latest_pkt_idname = prefs_operators + '.install_latest_pkt'
    kt_install_pkt_from_file_with_warning_idname = \
        prefs_operators + '.install_pkt_from_file_with_warning'
    kt_install_pkt_from_file_idname = prefs_operators + '.install_pkt_from_file'
    kt_pref_open_url_idname = prefs_operators + '.open_url'
    kt_pref_core_download_url_idname = prefs_operators + '.core_download_url'
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
    kt_share_feedback_idname = operators + '.share_feedback'
    kt_report_bug_idname = operators + '.report_bug'
    kt_upgrade_product_idname = operators + '.upgrade_product'

    kt_warning_idname = operators + '.common_addon_warning'
    kt_interrupt_modal_idname = operators + '.interrupt_modal'

    kt_actor_idname = operators + '.actor'

    kt_move_wrapper_idname = operators + '.move_wrapper'
    kt_pan_detector_idname = operators + '.pan_detector'

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

    # Testing panels
    kt_error_testing = _PT + 'error_testing_panel'
    kt_gt_shader_testing = _PT + 'gt_shader_testing_panel'
    kt_fb_shader_testing = _PT + 'fb_shader_testing_panel'

    kt_gt_shader_testing_idname = operators + '.gt_shader_testing'
    kt_fb_shader_testing_idname = operators + '.fb_shader_testing'

    # Object Custom Properties
    core_version_prop_name = 'keentools_version'
    viewport_state_prop_name = 'keentools_viewport_state'

    # Constants
    pin_size: float = 7.0
    pin_sensitivity: float = 16.0
    surf_pin_size_scale: float = 0.85
    text_scale_y: float = 0.75
    btn_scale_y: float = 1.2
    area_bottom_limit: int = 8

    default_tone_exposure: float = 0.0
    default_tone_gamma: float = 1.0

    default_tex_width: int = 2048
    default_tex_height: int = 2048
    default_tex_face_angles_affection: float = 10.0
    default_tex_uv_expand_percents: float = 0.1

    default_window_width: int = 1920
    default_window_height: int = 1080
    use_ui_scale: bool = True

    focal_length_tolerance: float = 0.01

    license_minimum_days_for_warning: int = 7
    kt_license_recheck_timeout: float = 360.0

    use_explicit_version_check_in_updater: bool = False

    # FaceBuilder Default Colors
    fb_midline_color: Tuple = (0.96, 0.008, 0.615686)
    fb_wireframe_opacity: float = 0.5
    fb_color_schemes: Dict = {
        'red': ((0.3, 0.0, 0.0), (0.0, 0.4, 0.7)),
        'green': ((0.0, 0.2, 0.0), (0.4, 0.0, 0.4)),
        'blue': ((0.0, 0.0, 0.3), (0.4, 0.75, 0.0)),
        'cyan': ((0.0, 0.3, 0.3), (0.4, 0.0, 0.0)),
        'magenta': ((0.3, 0.0, 0.3), (0.0, 0.55, 0.0)),
        'yellow': ((0.2, 0.2, 0.0), (0.0, 0.0, 0.4)),
        'black': ((0.03, 0.03, 0.03), (0.0, 0.0, 0.85)),
        'white': ((1.0, 1.0, 1.0), (0.0, 0.0, 0.4)),
        'default': ((0.03, 0.03, 0.03), (0.0, 0.0, 0.85))
    }
    ft_midline_color: Tuple = (0.05, 1.0, 0.0)
    ft_wireframe_opacity: float = 0.5
    ft_color_schemes: Dict = {
        'red': ((0.3, 0.0, 0.0), (0.0, 0.4, 0.7)),
        'green': ((0.0, 0.2, 0.0), (0.4, 0.0, 0.4)),
        'blue': ((0.0, 0.0, 0.3), (0.4, 0.75, 0.0)),
        'cyan': ((0.0, 0.3, 0.3), (0.4, 0.0, 0.0)),
        'magenta': ((0.3, 0.0, 0.3), (0.0, 0.55, 0.0)),
        'yellow': ((0.2, 0.2, 0.0), (0.0, 0.0, 0.4)),
        'black': ((0.03, 0.03, 0.03), (0.0, 0.0, 0.85)),
        'white': ((1.0, 1.0, 1.0), (0.0, 0.0, 0.4)),
        'default': ((0.02, 0.02, 0.04), (0.0, 0.4, 0.03))
    }
    gt_wireframe_color: Tuple = (0.0, 1.0, 0.0)
    gt_wireframe_opacity: float = 0.5
    gt_mask_3d_color: Tuple = (0.0, 0.0, 1.0)
    gt_mask_3d_opacity: float = 0.4
    gt_mask_2d_color: Tuple = (0.0, 1.0, 0.0)
    gt_mask_2d_opacity: float = 0.4

    # Default UserPreferences
    default_updater_preferences: Dict = {
        'latest_show_datetime_update_reminder': {'value': '', 'type': 'string'},
        'latest_update_skip_version': {'value': '', 'type': 'string'},
        'updater_state': {'value': 1, 'type': 'int'},
        'downloaded_version': {'value': '', 'type': 'string'},
        'latest_installation_skip_version': {'value': '', 'type': 'string'},
        'latest_show_datetime_installation_reminder': {'value': '', 'type': 'string'}
    }
    user_preferences_dict_name: str = 'keentools_facebuilder_addon'
    default_user_preferences: Dict = {
        'prevent_view_rotation': {'value': True, 'type': 'bool'},
        'use_hotkeys': {'value': True, 'type': 'bool'},
        'auto_unbreak_rotation': {'value': True, 'type': 'bool'},

        'pin_size': {'value': 7.0, 'type': 'float'},
        'pin_sensitivity': {'value': 16.0, 'type': 'float'},

        'prevent_fb_view_rotation': {'value': True, 'type': 'bool'},
        'fb_wireframe_color': {'value': fb_color_schemes['default'][0], 'type': 'color'},
        'fb_wireframe_special_color': {'value': fb_color_schemes['default'][1], 'type': 'color'},
        'fb_wireframe_midline_color': {'value': fb_midline_color, 'type': 'color'},
        'fb_wireframe_opacity': {'value': fb_wireframe_opacity, 'type': 'float'},
        'prevent_gt_view_rotation': {'value': True, 'type': 'bool'},
        'gt_wireframe_color': {'value': gt_wireframe_color, 'type': 'color'},
        'gt_wireframe_opacity': {'value': gt_wireframe_opacity, 'type': 'float'},
        'gt_mask_3d_color': {'value': gt_mask_3d_color, 'type': 'color'},
        'gt_mask_3d_opacity': {'value': gt_mask_3d_opacity, 'type': 'float'},
        'gt_mask_2d_color': {'value': gt_mask_2d_color, 'type': 'color'},
        'gt_mask_2d_opacity': {'value': gt_mask_2d_opacity, 'type': 'float'},
    }

    supported_gpu_backends: Set = {'OPENGL', 'Undefined', 'METAL'}
    strict_shader_check: bool = False
    wireframe_offset_constant: float = 0.004

    residual_dashed_line_length: float = 22.0
    residual_dashed_line: Dict = {'start': 0.0, 'step': 6.0, 'threshold': 4.0}
    selection_dashed_line: Dict = {'start': 5.0, 'step': 10.0, 'threshold': 5.5}

    keyframe_line_width: float = 2.0
    keyframe_line_length: float = 1000.0

    integration_enabled: bool = True

    kt_convert_video_scene_name: str = 'kt_convert_video'

    show_ft_licensing: bool = False
    show_trial_warnings: bool = True

    # Colors
    pin_color: Tuple = (1.0, 0.0, 0.0, 1.0)
    disabled_pin_color: Tuple = (1.0, 1.0, 0.0, 1.0)
    selected_pin_color: Tuple = (0.0, 1.0, 1.0, 1.0)
    current_pin_color: Tuple = (0.0, 1.0, 0.0, 1.0)
    surface_point_color: Tuple = (0.0, 1.0, 1.0, 0.5)
    residual_color: Tuple = (0.0, 1.0, 1.0, 0.5)
    timeline_keyframe_color: Tuple = (0.0, 1.0, 0.0, 0.5)

    selected_rectangle_color: Tuple = (0.871, 0.107, 0.001, 1.0)
    regular_rectangle_color: Tuple = (0.024, 0.246, 0.905, 1.0)

    face_selection_frame_width: float = 3.0


def is_blender_supported() -> bool:
    ver = bpy.app.version
    for supported_ver in Config.supported_blender_versions:
        if ver[:len(supported_ver)] == supported_ver:
            return True
    return False


def get_addon_preferences() -> Any:
    return bpy.context.preferences.addons[Config.package].preferences


def supported_gpu_backend() -> bool:
    return BVersion.gpu_backend in Config.supported_gpu_backends


def facebuilder_enabled() -> bool:
    prefs = get_addon_preferences()
    return prefs.facebuilder_enabled


def geotracker_enabled() -> bool:
    prefs = get_addon_preferences()
    return prefs.geotracker_enabled


def facetracker_enabled() -> bool:
    prefs = get_addon_preferences()
    return prefs.facetracker_enabled


def fb_settings() -> Optional[Any]:
    return getattr(bpy.context.scene, Config.fb_global_var_name, None)


def gt_settings() -> Optional[Any]:
    return getattr(bpy.context.scene, Config.gt_global_var_name, None)


def ft_settings() -> Optional[Any]:
    return getattr(bpy.context.scene, Config.ft_global_var_name, None)


def gt_pinmode() -> bool:
    if not geotracker_enabled():
        return False
    settings = gt_settings()
    if not settings:
        return False
    return settings.pinmode


def fb_pinmode() -> bool:
    if not facebuilder_enabled():
        return False
    settings = fb_settings()
    if not settings:
        return False
    return settings.pinmode


def ft_pinmode() -> bool:
    if not facetracker_enabled():
        return False
    settings = ft_settings()
    if not settings:
        return False
    return settings.pinmode


def addon_pinmode() -> bool:
    return fb_pinmode() or gt_pinmode() or ft_pinmode()


def add_addon_settings_var(name: str, settings_type: Any) -> None:
    setattr(Scene, name, PointerProperty(type=settings_type))


def remove_addon_settings_var(name: str) -> None:
    delattr(Scene, name)


def check_addon_settings_var_exists(name: str) -> bool:
    return hasattr(Scene, name)


def check_addon_settings_var_type(name: str) -> Any:
    if not hasattr(Scene, name):
        return None
    attr = getattr(Scene, name)
    if BVersion.property_keywords_enabled:
        return attr.keywords['type']
    else:
        return attr[1]['type']


def show_user_preferences(*, facebuilder: Optional[bool] = None,
                          geotracker: Optional[bool] = None,
                          facetracker: Optional[bool] = None) -> None:
    prefs = get_addon_preferences()
    if facebuilder is not None:
        prefs.show_fb_user_preferences = facebuilder
    if geotracker is not None:
        prefs.show_gt_user_preferences = geotracker
    if facetracker is not None:
        prefs.show_ft_user_preferences = facetracker


def show_tool_preferences(*, facebuilder: Optional[bool] = None,
                          geotracker: Optional[bool] = None,
                          facetracker: Optional[bool] = None) -> None:
    prefs = get_addon_preferences()
    if facebuilder is not None:
        prefs.facebuilder_expanded = facebuilder
    if geotracker is not None:
        prefs.geotracker_expanded = geotracker
    if facetracker is not None:
        prefs.facetracker_expanded = facetracker


def get_operator(operator_id_name: str) -> Any:
    def _rgetattr(obj, attr, *args):
        import functools
        def _getattr(obj, attr):
            return getattr(obj, attr, *args)
        return functools.reduce(_getattr, [obj] + attr.split('.'))
    return _rgetattr(bpy.ops, operator_id_name)


class ErrorType:
    Unknown: int = -1
    CustomMessage: int = 0
    NoFaceBuilderLicense: int = 1
    NoGeoTrackerLicense: int = 2
    NoFaceTrackerLicense: int = 3
    SceneDamaged: int = 4
    CannotReconstruct: int = 5
    CannotCreateObject: int = 6
    MeshCorrupted: int = 7
    PktProblem: int = 8
    PktModelProblem: int = 9
    DownloadingProblem: int = 10
    FBGracePeriod: int = 11
    GTGracePeriod: int = 12
    FTGracePeriod: int = 13
    ShaderProblem: int = 14
    UnsupportedGPUBackend: int = 15


@dataclass(frozen=True)
class ActionStatus:
    success: bool = False
    error_message: str = None


class ProductType:
    UNDEFINED: int = -1
    FACEBUILDER: int = 0
    GEOTRACKER: int = 1
    FACETRACKER: int = 2
    ADDON: int = 3


def get_settings(product: int) -> Any:
    if product == ProductType.GEOTRACKER:
        return gt_settings()
    if product == ProductType.FACETRACKER:
        return ft_settings()
    if product == ProductType.FACEBUILDER:
        return fb_settings()
    assert False, f'get_settings: Improper product {product}'


def product_name(product: int) -> str:
    if product == ProductType.FACEBUILDER:
        return 'FaceBuilder'
    if product == ProductType.GEOTRACKER:
        return 'GeoTracker'
    if product == ProductType.FACETRACKER:
        return 'FaceTracker'
    if product == ProductType.ADDON:
        return 'KeenTools'
    assert False, f'product_name: Improper product {product}'


def product_type_by_name(product_str: str) -> int:
    if product_str == 'FaceBuilder':
        return ProductType.FACEBUILDER
    if product_str == 'GeoTracker':
        return ProductType.GEOTRACKER
    if product_str == 'FaceTracker':
        return ProductType.FACETRACKER
    if product_str == 'KeenTools':
        return ProductType.ADDON
    return ProductType.UNDEFINED


def output_import_statistics() -> None:
    names = "\n".join(_log.module_names())
    _log.output('import sequence:\n' + _log.color('green', f'{names}'))


def tool_pinmode(facebuilder: bool = True, geotracker: bool = True,
                 facetracker: bool = True) -> Optional[int]:
    if facebuilder and fb_pinmode():
        return ProductType.FACEBUILDER
    if geotracker and gt_pinmode():
        return ProductType.GEOTRACKER
    if facetracker and ft_pinmode():
        return ProductType.FACETRACKER
    return None


def stop_fb_pinmode():
    settings = fb_settings()
    if not settings:
        return
    loader = settings.loader()
    area = loader.get_work_area()
    loader.out_pinmode_without_save()
    settings.viewport_state.show_ui_elements(area)
    settings.reset_pinmode_id()
    settings.pinmode = False


def stop_gt_pinmode():
    settings = gt_settings()
    if settings and settings.pinmode:
        settings.loader().out_pinmode()
    settings.pinmode = False


def stop_ft_pinmode():
    settings = ft_settings()
    if settings and settings.pinmode:
        settings.loader().out_pinmode()
    settings.pinmode = False


def calculation_in_progress(facebuilder: bool = True,
                            geotracker: bool = True,
                            facetracker: bool = True) -> ActionStatus:
    if geotracker:
        settings_gt = gt_settings()
        if settings_gt and settings_gt.is_calculating():
            return ActionStatus(False, 'GeoTracker calculation is in progress')

    if facetracker:
        settings_ft = ft_settings()
        if settings_ft and settings_ft.is_calculating():
            return ActionStatus(False, 'FaceTracker calculation is in progress')

    if facebuilder:
        settings_fb = fb_settings()
        if settings_fb and settings_fb.is_calculating():
            return ActionStatus(False, 'FaceBuilder calculation is in progress')
    return ActionStatus(True, 'No calculation is in progress')


_common_loader_instance: Optional[Any]
_common_loader_func: Callable
_fb_loader_instance: Optional[Any]
_fb_loader_func: Callable
_gt_loader_instance: Optional[Any]
_gt_loader_func: Callable
_ft_loader_instance: Optional[Any]
_ft_loader_func: Callable


def _init_common_loader() -> Any:
    from .common.loader import CommonLoader
    global _common_loader_instance
    _common_loader_instance = CommonLoader()
    global _common_loader_func
    _common_loader_func = _get_common_loader
    return _common_loader_instance


def _init_fb_loader() -> Any:
    from .facebuilder.fbloader import FBLoader
    global _fb_loader_instance
    _fb_loader_instance = FBLoader
    global _fb_loader_func
    _fb_loader_func = _get_fb_loader
    return FBLoader


def _init_gt_loader() -> Any:
    from .geotracker.gtloader import GTLoader
    global _gt_loader_instance
    _gt_loader_instance = GTLoader
    global _gt_loader_func
    _gt_loader_func = _get_gt_loader
    return GTLoader


def _init_ft_loader() -> Any:
    from .facetracker.ftloader import FTLoader
    global _ft_loader_instance
    _ft_loader_instance = FTLoader
    global _ft_loader_func
    _ft_loader_func = _get_ft_loader
    return FTLoader


def _get_common_loader() -> Any:
    return _common_loader_instance


def _get_fb_loader() -> Any:
    return _fb_loader_instance


def _get_gt_loader() -> Any:
    return _gt_loader_instance


def _get_ft_loader() -> Any:
    return _ft_loader_instance


def common_loader() -> Any:
    return _common_loader_func()


def fb_loader() -> Any:
    return _fb_loader_func()


def gt_loader() -> Any:
    return _gt_loader_func()


def ft_loader() -> Any:
    return _ft_loader_func()


_common_loader_instance = None
_common_loader_func = _init_common_loader
_fb_loader_instance = None
_fb_loader_func = _init_fb_loader
_gt_loader_instance = None
_gt_loader_func = _init_gt_loader
_ft_loader_instance = None
_ft_loader_func = _init_ft_loader


def license_checker_module() -> Any:
    from .common import license_checker
    return license_checker
