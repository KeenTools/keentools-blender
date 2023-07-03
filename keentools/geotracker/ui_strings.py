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

from collections import namedtuple

from ..geotracker_config import GTConfig


Button = namedtuple('Button', ['label', 'description'])

buttons = {
    GTConfig.gt_pinmode_idname: Button(
        'GeoTracker Pinmode',
        'Align geometry with the target in your clip and proceed to tracking'
    ),
    GTConfig.gt_movepin_idname: Button(
        'GeoTracker MovePin',
        'GeoTracker MovePin operator'
    ),
    GTConfig.gt_switch_to_camera_mode_idname: Button(
        'Camera',
        'Track Camera'
    ),
    GTConfig.gt_switch_to_geometry_mode_idname: Button(
        'Geometry',
        'Track Geometry'
    ),
    GTConfig.gt_actor_idname: Button(
        'Actor Operator',
        'GeoTracker Action'
    ),
    GTConfig.gt_sequence_filebrowser_idname: Button(
        'Load clip',
        'Load a sequence of frames or a movie file'
    ),
    GTConfig.gt_mask_sequence_filebrowser_idname: Button(
        'Load mask sequence',
        'Both image sequences and movie files are supported'
    ),
    GTConfig.gt_choose_precalc_file_idname: Button(
        'Choose analysis filename',
        'Use existing .precalc file or enter new name'
    ),
    GTConfig.gt_split_video_to_frames_idname: Button(
        'Split video to frames',
        'Choose folder'
    ),
    GTConfig.gt_split_video_to_frames_exec_idname: Button(
        'Split video to frames',
        'Choose folder'
    ),
    GTConfig.gt_video_snapshot_idname: Button(
        'Take snapshot',
        'Take snapshot of current frame'
    ),
    GTConfig.gt_select_frames_for_bake_idname: Button(
        'GeoTracker Keyframes',
        'Project and bake texture in selected frames'
    ),
    GTConfig.gt_reproject_tex_sequence_idname: Button(
        'All Frames to Sequence',
        'Project and bake texture in all frames and save as animated sequence'
    ),
    GTConfig.gt_precalc_info_idname: Button(
        'Analysis file info',
        'Click this button to see .precalc file info'
    ),
    GTConfig.gt_analyze_call_idname: Button(
        'Analyse',
        'Call analyse dialog'
    ),
    GTConfig.gt_confirm_recreate_precalc_idname: Button(
        'Recreate analysis file',
        'Are you sure to recreate analysis file?'
    ),
    # Main UI
    GTConfig.gt_addon_setup_defaults_idname: Button(
        'GeoTracker settings',
        'Open Preferences/Add-ons for more settings'
    ),
    GTConfig.gt_create_geotracker_idname: Button(
        'Create new GeoTracker',
        'Track new object'
    ),
    GTConfig.gt_delete_geotracker_idname: Button(
        'Delete GeoTracker',
        'Delete this GeoTracker object from scene'
    ),
    GTConfig.gt_select_geotracker_objects_idname: Button(
        'Select objects',
        'Select assigned Geometry and Camera in scene'
    ),
    GTConfig.gt_create_precalc_idname: Button(
        'Create precalc',
        'Create precalc for current MovieClip'
    ),
    GTConfig.gt_auto_name_precalc_idname: Button(
        'Generate precalc filename',
        'Generate precalc filename'
    ),
    GTConfig.gt_prev_keyframe_idname: Button(
        'Prev keyframe',
        'Move to the previous GeoTracker keyframe on the timeline',
    ),
    GTConfig.gt_next_keyframe_idname: Button(
        'Next keyframe',
        'Move to the next GeoTracker keyframe on the timeline'
    ),
    GTConfig.gt_track_to_start_idname: Button(
        'Track to start',
        'Track backwards'
    ),
    GTConfig.gt_track_to_end_idname: Button(
        'Track to end',
        'Track forward'
    ),
    GTConfig.gt_track_next_idname: Button(
        'Track next',
        'Track to next frame'
    ),
    GTConfig.gt_track_prev_idname: Button(
        'Track prev',
        'Track to previous frame'
    ),
    GTConfig.gt_add_keyframe_idname: Button(
        'Add GeoTracker keyframe',
        'add keyframe'
    ),
    GTConfig.gt_remove_keyframe_idname: Button(
        'Remove GeoTracker keyframe',
        'remove keyframe'
    ),
    GTConfig.gt_clear_all_tracking_idname: Button(
        'Clear all',
        'Delete all keyframes'
    ),
    GTConfig.gt_clear_tracking_except_keyframes_idname: Button(
        'Clear tracking data only',
        'Clear tracking data, keep GeoTracker keyframes'
    ),
    GTConfig.gt_clear_tracking_forward_idname: Button(
        'Clear forward',
        'Clear all keyframes to the right of current frame'
    ),
    GTConfig.gt_clear_tracking_backward_idname: Button(
        'Clear backwards',
        'Clear all keyframes to the left of current frame'
    ),
    GTConfig.gt_clear_tracking_between_idname: Button(
        'Clear between',
        'Clear tracking data between nearest GeoTracker keyframes'
    ),
    GTConfig.gt_refine_idname: Button(
        'Refine',
        'Refine tracking data between nearest keyframes'
    ),
    GTConfig.gt_refine_all_idname: Button(
        'Refine All',
        'Refine all tracking data'
    ),
    GTConfig.gt_center_geo_idname: Button(
        'Center Geo',
        'Place target geometry in the center of your viewpoint'
    ),
    GTConfig.gt_magic_keyframe_idname: Button(
        'Magic',
        'Magic keyframe detection'
    ),
    GTConfig.gt_remove_pins_idname: Button(
        'Remove Pins',
        'Delete all or only selected pins'
    ),
    GTConfig.gt_toggle_pins_idname: Button(
        'Toggle Pins',
        'Toggle all or only selected pins'
    ),
    GTConfig.gt_unbreak_rotation_idname: Button(
        'Unbreak Rotation',
        'Fix rotation making it continuous and removing 360 degrees jumps'
    ),
    GTConfig.gt_rescale_window_idname: Button(
        'Scale',
        'Scale scene'
    ),
    GTConfig.gt_move_window_idname: Button(
        'Position',
        'Move scene'
    ),
    GTConfig.gt_rig_window_idname: Button(
        'Rig',
        'Create an Empty with parented Camera and Geometry'
    ),
    GTConfig.gt_export_animated_empty_idname: Button(
        'Export',
        'Create an animated Empty'
    ),
    GTConfig.gt_exit_pinmode_idname: Button(
        'Exit Pinmode',
        'Back to 3D scene'
    ),
    GTConfig.gt_stop_calculating_idname: Button(
        'Stop calculating',
        'Stop calculating'
    ),
    GTConfig.gt_reset_tone_exposure_idname: Button(
        'Reset',
        'Reset exposure to default value'
    ),
    GTConfig.gt_reset_tone_gamma_idname: Button(
        'Reset',
        'Reset gamma to default value'
    ),
    GTConfig.gt_reset_tone_mapping_idname: Button(
        'Reset',
        'Reset all to default values'
    ),
    GTConfig.gt_default_wireframe_settings_idname: Button(
        'Reset',
        'Reset colour and opacity to default values'
    ),
    GTConfig.gt_default_pin_settings_idname: Button(
        'Reset',
        'Reset all to default values'
    ),
    GTConfig.gt_check_uv_overlapping_idname: Button(
        'Check',
        'Check for overlapping UVs'
    ),
    GTConfig.gt_repack_overlapping_uv_idname: Button(
        'Repack',
        'Attempt to reorganize UVs as non-overlapping islands'
    ),
    GTConfig.gt_create_non_overlapping_uv_idname: Button(
        'Create smart UV',
        'Create new non-overlapping UVs'
    ),
    GTConfig.gt_reproject_frame_idname: Button(
        'Current Frame',
        'Project and bake texture in current frame'
    ),
    GTConfig.gt_select_all_bake_frames_idname: Button(
        'All',
        'Select all'
    ),
    GTConfig.gt_deselect_all_bake_frames_idname: Button(
        'None',
        'Deselect all'
    ),
    GTConfig.gt_transfer_tracking_idname: Button(
        'Convert',
        'Convert all animation'
    ),
    GTConfig.gt_bake_animation_to_world_idname: Button(
        'Bake animation',
        'Convert animation to world space'
    ),
    GTConfig.gt_remove_focal_keyframe_idname: Button(
        'Remove current',
        'Remove focal length animation key in current keyframe'
    ),
    GTConfig.gt_remove_focal_keyframes_idname: Button(
        'Remove all',
        'Remove all focal length animation keys'
    ),
    GTConfig.gt_render_with_background_idname: Button(
        'Render with background',
        'Enable rendering with background using compositing nodes'
    ),
    GTConfig.gt_revert_default_render_idname: Button(
        'Revert default rendering',
        'Setup scene rendering settings to match default render view'
    ),
    GTConfig.gt_interrupt_modal_idname: Button(
        'GeoTracker Interruptor',
        'Interrupt current operation by Esc'
    ),
    # Menu buttons
    GTConfig.gt_clear_tracking_menu_exec_idname: Button(
        'Clear menu',
        'Clear all or tracking data only'
    ),
    GTConfig.gt_clear_tracking_menu_idname: Button(
        'Clear menu (internal)',
        'Clear menu list (internal)'
    ),
    GTConfig.gt_clip_menu_idname: Button(
        'Clip menu',
        'Load new clip / Make snapshot / Split video'
    ),
    # Help buttons
    GTConfig.gt_help_inputs_idname: Button(
        'Inputs help',
        'Show help information about Inputs panel'
    ),
    GTConfig.gt_help_masks_idname: Button(
        'Masks help',
        'Show help information about Masks panel'
    ),
    GTConfig.gt_help_analyze_idname: Button(
        'Analyze help',
        'Show help information about Analyze panel'
    ),
    GTConfig.gt_help_camera_idname: Button(
        'Camera help',
        'Show help information about Camera settings panel'
    ),
    GTConfig.gt_help_tracking_idname: Button(
        'Tracking help',
        'Show help information about Tracking panel'
    ),
    GTConfig.gt_help_appearance_idname: Button(
        'Appearance help',
        'Show help information about Appearance panel'
    ),
    GTConfig.gt_help_texture_idname: Button(
        'Texture help',
        'Show help information about Texture panel'
    ),
    GTConfig.gt_help_animation_idname: Button(
        'Animation help',
        'Show help information about Animation panel'
    ),
    GTConfig.gt_help_rendering_idname: Button(
        'Rendering help',
        'Show help information about Rendering panel'
    ),
    GTConfig.gt_help_smoothing_idname: Button(
        'Smoothing help',
        'Show help information about Smoothing panel'
    ),
}


HelpText = namedtuple('HelpText', ['width', 'message'])
_help_default_width = 500


help_texts = {
    GTConfig.gt_help_inputs_idname: HelpText(_help_default_width, [
        'Inputs panel description will be here...',
        ' '
    ]),
    GTConfig.gt_help_masks_idname: HelpText(_help_default_width, [
        'Masks panel description will be here...',
        ' '
    ]),
    GTConfig.gt_help_analyze_idname: HelpText(_help_default_width, [
        'Analyze panel description will be here...',
        ' '
    ]),
    GTConfig.gt_help_camera_idname: HelpText(_help_default_width, [
        'Camera panel description will be here...',
        ' '
    ]),
    GTConfig.gt_help_tracking_idname: HelpText(_help_default_width, [
        'Tracking panel description will be here...',
        ' '
    ]),
    GTConfig.gt_help_appearance_idname: HelpText(_help_default_width, [
        'Appearance panel description will be here...',
        ' '
    ]),
    GTConfig.gt_help_texture_idname: HelpText(_help_default_width, [
        'Texture panel description will be here...',
        ' '
    ]),
    GTConfig.gt_help_animation_idname: HelpText(_help_default_width, [
        'Animation panel description will be here...',
        ' '
    ]),
    GTConfig.gt_help_rendering_idname: HelpText(_help_default_width, [
        'Rendering panel description will be here...',
        ' '
    ]),
    GTConfig.gt_help_smoothing_idname: HelpText(_help_default_width, [
        'All smoothing settings are effective during tracking and refine only.',
        'Once the tracking is done, changing them will not change the track,',
        'you need to launch tracking or refine again to apply new smoothing settings.',
        'You can tweak them differently for different parts of the footage,',
        'the values are not being saved for different parts of the footage.',
        '0 means no smoothing while 1 makes the smoothed parameter(s) almost static.',
        ' '
    ]),
}


class PrecalcStatusMessage:
    broken_file: str = '* Analysis file is broken'
    missing_file: str = '* .precalc file is missing'
    empty: str = ''
