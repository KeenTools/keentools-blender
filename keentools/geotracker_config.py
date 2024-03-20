# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2022 KeenTools

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

from typing import Callable
import os

from .utils.kt_logging import KTLogger
from .addon_config import gt_settings


_log = KTLogger(__name__)


_PT = 'GEOTRACKER_PT_'
_MT = 'GEOTRACKER_MT_'


class GTConfig:
    operators = 'keentools_gt'
    gt_tool_name = 'GeoTracker'
    gt_tab_category = 'GeoTracker'

    # Operators
    gt_create_geotracker_idname = operators + '.create_geotracker'
    gt_delete_geotracker_idname = operators + '.delete_geotracker'
    gt_select_geotracker_objects_idname = operators + '.select_geotracker'
    gt_actor_idname = operators + '.actor'
    gt_pinmode_idname = operators + '.pinmode'
    gt_movepin_idname = operators + '.movepin'
    gt_switch_to_camera_mode_idname = operators + '.switch_to_camera_mode'
    gt_switch_to_geometry_mode_idname = operators + '.switch_to_geometry_mode'
    gt_create_precalc_idname = operators + '.create_precalc'
    gt_sequence_filebrowser_idname = operators + '.sequence_filebrowser'
    gt_mask_sequence_filebrowser_idname = \
        operators + '.mask_sequence_filebrowser'
    gt_choose_precalc_file_idname = operators + '.choose_precalc_file'
    gt_split_video_to_frames_idname = operators + '.split_video_to_frames'
    gt_split_video_to_frames_exec_idname = \
        operators + '.split_video_to_frames_exec'
    gt_video_snapshot_idname = operators + '.video_snapshot'
    gt_reproject_tex_sequence_idname = operators + '.reproject_tex_sequence'
    gt_texture_file_export_idname = operators + '.texture_file_export'
    gt_delete_texture_idname = operators + '.delete_texture'
    gt_track_to_start_idname = operators + '.track_to_start_btn'
    gt_track_to_end_idname = operators + '.track_to_end_btn'
    gt_track_next_idname = operators + '.track_next_btn'
    gt_track_prev_idname = operators + '.track_prev_btn'
    gt_prev_keyframe_idname = operators + '.prev_keyframe_btn'
    gt_next_keyframe_idname = operators + '.next_keyframe_btn'
    gt_add_keyframe_idname = operators + '.add_keyframe_btn'
    gt_remove_keyframe_idname = operators + '.remove_keyframe_btn'
    gt_clear_all_tracking_idname = operators + '.clear_all_tracking_btn'
    gt_clear_tracking_except_keyframes_idname = \
        operators + '.clear_tracking_except_keyframes_btn'
    gt_clear_tracking_forward_idname = operators + '.clear_tracking_forward_btn'
    gt_clear_tracking_backward_idname = \
        operators + '.clear_tracking_backward_btn'
    gt_clear_tracking_between_idname = operators + '.clear_tracking_between_btn'
    gt_refine_idname = operators + '.refine_btn'
    gt_refine_all_idname = operators + '.refine_all_btn'
    gt_center_geo_idname = operators + '.center_geo_btn'
    gt_magic_keyframe_idname = operators + '.magic_keyframe_btn'
    gt_remove_pins_idname = operators + '.remove_pins_btn'
    gt_toggle_pins_idname = operators + '.toggle_pins_btn'

    gt_toggle_lock_view_idname = operators + '.toggle_lock_view'
    gt_exit_pinmode_idname = operators + '.exit_pinmode_btn'
    gt_interrupt_modal_idname = operators + '.interrupt_modal'
    gt_stop_calculating_idname = operators + '.stop_calculating_btn'
    gt_set_key_idname = operators + '.set_key_btn'
    gt_reset_tone_exposure_idname = operators + '.reset_tone_exposure'
    gt_reset_tone_gamma_idname = operators + '.reset_tone_gamma'
    gt_reset_tone_mapping_idname = operators + '.reset_tone_mapping'
    gt_reset_texture_resolution_idname = operators + '.reset_texture_resolution'
    gt_reset_advanced_settings_idname = operators + '.reset_advanced_settings'
    gt_default_wireframe_settings_idname = \
        operators + '.default_wireframe_settings'
    gt_default_pin_settings_idname = operators + '.default_pin_settings'
    gt_check_uv_overlapping_idname = operators + '.check_uv_overlapping'
    gt_repack_overlapping_uv_idname = operators + '.repack_overlapping_uv'
    gt_create_non_overlapping_uv_idname = \
        operators + '.create_non_overlapping_uv'
    gt_bake_from_selected_frames_idname = operators + '.bake_from_selected_frames'
    gt_add_bake_frame_idname = operators + '.add_bake_frame'
    gt_remove_bake_frame_idname = operators + '.remove_bake_frame'
    gt_go_to_bake_frame_idname = operators + '.go_to_bake_frame'
    gt_texture_bake_options_idname = operators + '.texture_bake_options'

    gt_export_animated_empty_idname = operators + '.export_animated_empty'
    gt_transfer_tracking_idname = operators + '.transfer_tracking'
    gt_bake_animation_to_world_idname = operators + '.bake_animation_to_world'
    gt_remove_focal_keyframe_idname = operators + '.remove_focal_keyframe'
    gt_remove_focal_keyframes_idname = operators + '.remove_focal_keyframes'
    gt_addon_setup_defaults_idname = operators + '.addon_setup_defaults'
    gt_user_preferences_get_colors = operators + '.user_pref_get_colors'
    gt_user_preferences_reset_all = operators + '.user_pref_reset_all'

    gt_render_with_background_idname = operators + '.render_with_background'
    gt_revert_default_render_idname = operators + '.revert_default_render'
    gt_analyze_call_idname = operators + '.analyze_call'
    gt_precalc_info_idname = operators + '.precalc_info'
    gt_confirm_recreate_precalc_idname = operators + '.confirm_recreate_precalc'
    gt_auto_name_precalc_idname = operators + '.auto_name_precalc'
    gt_unbreak_rotation_idname = operators + '.unbreak_rotation'
    gt_share_feedback_idname = operators + '.share_feedback'

    # Window ids
    gt_rescale_window_idname = operators + '.rescale_window'
    gt_move_window_idname = operators + '.move_window'
    gt_rig_window_idname = operators + '.rig_window'
    gt_switch_camera_to_fixed_warning_idname = \
        operators + '.switch_camera_to_fixed_warning_idname'

    # Menu ids
    gt_clip_menu_idname = _MT + 'clip_menu'
    gt_clear_tracking_menu_idname = _MT + 'clear_tracking_menu'
    gt_clear_tracking_menu_exec_idname = operators + '.clip_menu_exec'

    # Panel ids
    gt_geotrackers_panel_idname = _PT + 'geotrackers_panel'
    gt_input_panel_idname = _PT + 'input_panel'
    gt_masks_panel_idname = _PT + 'masks_panel'
    gt_analyze_panel_idname = _PT + 'analyze_panel'
    gt_camera_panel_idname = _PT + 'camera_panel'
    gt_tracking_panel_idname = _PT + 'tracking_panel'
    gt_appearance_panel_idname = _PT + 'appearance_panel'
    gt_scene_panel_idname = _PT + 'scene_panel'
    gt_texture_panel_idname = _PT + 'texture_panel'
    gt_rendering_panel_idname = _PT + 'rendering_panel'
    gt_smoothing_panel_idname = _PT + 'smoothing_panel'
    gt_support_panel_idname = _PT + 'support_panel'

    # Help ids
    gt_help_inputs_idname = operators + '.help_inputs'
    gt_help_masks_idname = operators + '.help_masks'
    gt_help_analyze_idname = operators + '.help_analyze'
    gt_help_camera_idname = operators + '.help_camera'
    gt_help_tracking_idname = operators + '.help_tracking'
    gt_help_appearance_idname = operators + '.help_appearance'
    gt_help_texture_idname = operators + '.help_texture'
    gt_help_animation_idname = operators + '.help_animation'
    gt_help_rendering_idname = operators + '.help_rendering'
    gt_help_smoothing_idname = operators + '.help_smoothing'

    # Updater panels
    gt_update_panel_idname = _PT + 'update_panel'
    gt_download_notification_panel_idname = _PT + 'download_notification'
    gt_downloading_problem_panel_idname = _PT + 'downloading_problem'
    gt_updates_installation_panel_idname = _PT + 'updates_installation_panel'

    # Constants
    text_scale_y = 0.75
    default_precalc_filename = 'geotracker.precalc'
    viewport_redraw_interval = 0.15
    show_markers_at_camera_corners = False

    pin_size = 7.0
    pin_sensitivity = 16.0
    surf_pin_size_scale = 0.85

    # Colors
    pin_color = (1.0, 0.0, 0.0, 1.0)
    disabled_pin_color = (1.0, 1.0, 0.0, 1.0)
    selected_pin_color = (0.0, 1.0, 1.0, 1.0)
    current_pin_color = (0.0, 1.0, 0.0, 1.0)
    surface_point_color = (0.0, 1.0, 1.0, 0.5)
    residual_color = (0.0, 1.0, 1.0, 0.5)
    timeline_keyframe_color = (0.0, 1.0, 0.0, 0.5)

    wireframe_color = (0.0, 1.0, 0.0, 0.4)
    mask_2d_color = (0.0, 1.0, 0.0, 0.4)
    mask_3d_color = (0.0, 0.0, 1.0, 0.4)

    prevent_view_rotation = True
    auto_render_size = True
    auto_time_length = True
    auto_increase_far_clip_distance = True

    gt_empty_name = 'gtEmpty'
    gt_background_name = 'geotracker_footage'
    gt_background_mask_name = 'geotracker_mask'
    gt_rendered_mask_image_name = 'gt_rendered_mask'
    gt_shadow_compositing_scene_name = 'gt_shadow_compositing_scene'
    gt_precalc_folder = f'/tmp{os.path.sep}kt_analysis{os.path.sep}'

    tex_builder_filename_template = '{}_baked_tex'
    tex_builder_matname_template = '{}_preview_mat'

    hidden_feature: bool = True
