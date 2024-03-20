# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2023 KeenTools

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

from .utils.kt_logging import KTLogger


_log = KTLogger(__name__)


_PT = 'FACETRACKER_PT_'
_MT = 'FACETRACKER_MT_'


class FTConfig:
    operators = 'keentools_ft'
    ft_tool_name = 'FaceTracker'
    ft_tab_category = 'FaceTracker'

    # Operators
    ft_create_facetracker_idname = operators + '.create_facetracker'
    ft_delete_facetracker_idname = operators + '.delete_facetracker'
    ft_select_facetracker_objects_idname = operators + '.select_facetracker'
    ft_actor_idname = operators + '.actor'
    ft_pinmode_idname = operators + '.pinmode'
    ft_movepin_idname = operators + '.movepin'
    ft_switch_to_camera_mode_idname = operators + '.switch_to_camera_mode'
    ft_switch_to_geometry_mode_idname = operators + '.switch_to_geometry_mode'
    ft_create_precalc_idname = operators + '.create_precalc'

    ft_sequence_filebrowser_idname = 'keentools_gt' + '.sequence_filebrowser'  # TODO: Check operator!

    ft_mask_sequence_filebrowser_idname = \
        operators + '.mask_sequence_filebrowser'

    ft_choose_precalc_file_idname = 'keentools_gt' + '.choose_precalc_file'  # TODO: Check operator!

    ft_split_video_to_frames_idname = operators + '.split_video_to_frames'
    ft_split_video_to_frames_exec_idname = \
        operators + '.split_video_to_frames_exec'

    ft_video_snapshot_idname = 'keentools_gt' + '.video_snapshot'  # TODO: Check operator!

    ft_reproject_tex_sequence_idname = operators + '.reproject_tex_sequence'
    ft_texture_file_export_idname = operators + '.texture_file_export'
    ft_delete_texture_idname = operators + '.delete_texture'
    ft_track_to_start_idname = operators + '.track_to_start_btn'
    ft_track_to_end_idname = operators + '.track_to_end_btn'
    ft_track_next_idname = operators + '.track_next_btn'
    ft_track_prev_idname = operators + '.track_prev_btn'
    ft_prev_keyframe_idname = operators + '.prev_keyframe_btn'
    ft_next_keyframe_idname = operators + '.next_keyframe_btn'
    ft_add_keyframe_idname = operators + '.add_keyframe_btn'
    ft_remove_keyframe_idname = operators + '.remove_keyframe_btn'
    ft_clear_all_tracking_idname = operators + '.clear_all_tracking_btn'
    ft_clear_tracking_except_keyframes_idname = \
        operators + '.clear_tracking_except_keyframes_btn'
    ft_clear_tracking_forward_idname = operators + '.clear_tracking_forward_btn'
    ft_clear_tracking_backward_idname = \
        operators + '.clear_tracking_backward_btn'
    ft_clear_tracking_between_idname = operators + '.clear_tracking_between_btn'
    ft_refine_idname = operators + '.refine_btn'
    ft_refine_all_idname = operators + '.refine_all_btn'
    ft_center_geo_idname = operators + '.center_geo_btn'
    ft_magic_keyframe_idname = operators + '.magic_keyframe_btn'
    ft_remove_pins_idname = operators + '.remove_pins_btn'
    ft_toggle_pins_idname = operators + '.toggle_pins_btn'

    ft_toggle_lock_view_idname = operators + '.toggle_lock_view'
    ft_exit_pinmode_idname = operators + '.exit_pinmode_btn'
    ft_interrupt_modal_idname = operators + '.interrupt_modal'
    ft_stop_calculating_idname = operators + '.stop_calculating_btn'
    ft_set_key_idname = operators + '.set_key_btn'
    ft_reset_tone_exposure_idname = operators + '.reset_tone_exposure'
    ft_reset_tone_gamma_idname = operators + '.reset_tone_gamma'
    ft_reset_tone_mapping_idname = operators + '.reset_tone_mapping'
    ft_reset_texture_resolution_idname = operators + '.reset_texture_resolution'
    ft_reset_advanced_settings_idname = operators + '.reset_advanced_settings'
    ft_default_wireframe_settings_idname = \
        operators + '.default_wireframe_settings'
    ft_default_pin_settings_idname = operators + '.default_pin_settings'
    ft_check_uv_overlapping_idname = operators + '.check_uv_overlapping'
    ft_repack_overlapping_uv_idname = operators + '.repack_overlapping_uv'
    ft_create_non_overlapping_uv_idname = \
        operators + '.create_non_overlapping_uv'
    ft_bake_from_selected_frames_idname = operators + '.bake_from_selected_frames'
    ft_add_bake_frame_idname = operators + '.add_bake_frame'
    ft_remove_bake_frame_idname = operators + '.remove_bake_frame'
    ft_go_to_bake_frame_idname = operators + '.go_to_bake_frame'
    ft_texture_bake_options_idname = operators + '.texture_bake_options'

    ft_export_animated_empty_idname = operators + '.export_animated_empty'
    ft_transfer_tracking_idname = operators + '.transfer_tracking'
    ft_bake_animation_to_world_idname = operators + '.bake_animation_to_world'
    ft_remove_focal_keyframe_idname = operators + '.remove_focal_keyframe'
    ft_remove_focal_keyframes_idname = operators + '.remove_focal_keyframes'
    ft_addon_setup_defaults_idname = operators + '.addon_setup_defaults'
    ft_user_preferences_get_colors = operators + '.user_pref_get_colors'
    ft_user_preferences_reset_all = operators + '.user_pref_reset_all'
    ft_wireframe_color_idname = operators + '.wireframe_color'

    ft_render_with_background_idname = operators + '.render_with_background'
    ft_revert_default_render_idname = operators + '.revert_default_render'

    ft_analyze_call_idname = operators + '.analyze_call'
    ft_precalc_info_idname = operators + '.precalc_info'

    ft_confirm_recreate_precalc_idname = operators + '.confirm_recreate_precalc'
    ft_auto_name_precalc_idname = operators + '.auto_name_precalc'
    ft_unbreak_rotation_idname = operators + '.unbreak_rotation'
    ft_share_feedback_idname = operators + '.share_feedback'

    # Window ids
    ft_rescale_window_idname = operators + '.rescale_window'
    ft_move_window_idname = operators + '.move_window'
    ft_rig_window_idname = operators + '.rig_window'
    ft_switch_camera_to_fixed_warning_idname = \
        operators + '.switch_camera_to_fixed_warning_idname'

    # Menu ids
    ft_clip_menu_idname = _MT + 'clip_menu'
    ft_clear_tracking_menu_idname = _MT + 'clear_tracking_menu'
    ft_clear_tracking_menu_exec_idname = operators + '.clip_menu_exec'

    # Panel ids
    ft_facetrackers_panel_idname = _PT + 'facetrackers_panel'
    ft_input_panel_idname = _PT + 'input_panel'
    ft_masks_panel_idname = _PT + 'masks_panel'
    ft_analyze_panel_idname = _PT + 'analyze_panel'
    ft_camera_panel_idname = _PT + 'camera_panel'
    ft_tracking_panel_idname = _PT + 'tracking_panel'
    ft_appearance_panel_idname = _PT + 'appearance_panel'
    ft_scene_panel_idname = _PT + 'scene_panel'
    ft_texture_panel_idname = _PT + 'texture_panel'
    ft_rendering_panel_idname = _PT + 'rendering_panel'
    ft_smoothing_panel_idname = _PT + 'smoothing_panel'
    ft_support_panel_idname = _PT + 'support_panel'

    # Help ids
    ft_help_inputs_idname = operators + '.help_inputs'
    ft_help_masks_idname = operators + '.help_masks'
    ft_help_analyze_idname = operators + '.help_analyze'
    ft_help_camera_idname = operators + '.help_camera'
    ft_help_tracking_idname = operators + '.help_tracking'
    ft_help_appearance_idname = operators + '.help_appearance'
    ft_help_texture_idname = operators + '.help_texture'
    ft_help_animation_idname = operators + '.help_animation'
    ft_help_rendering_idname = operators + '.help_rendering'
    ft_help_smoothing_idname = operators + '.help_smoothing'

    ft_action_name = 'ftAction'
