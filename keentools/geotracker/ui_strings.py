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
        'Operator for in-Viewport drawing'
    ),
    GTConfig.gt_movepin_idname: Button(
        'GeoTracker MovePin',
        'GeoTracker MovePin operator'
    ),
    GTConfig.gt_actor_idname: Button(
        'Actor Operator',
        'GeoTracker Action'
    ),
    GTConfig.gt_sequence_filebrowser_idname: Button(
        'Load footage',
        'Both image sequences and movie files are supported'
    ),
    GTConfig.gt_mask_sequence_filebrowser_idname: Button(
        'Load mask sequence',
        'Both image sequences and movie files are supported'
    ),
    GTConfig.gt_choose_precalc_file_idname: Button(
        'Choose precalc filename',
        'Choose an existing .precalc file or just enter a name for a new one'
    ),
    GTConfig.gt_split_video_to_frames_idname: Button(
        'Split video to frames',
        'Choose dir where to place video-file frames'
    ),
    GTConfig.gt_split_video_to_frames_exec_idname: Button(
        'Split video-file.',
        'Choose dir where to place video-file frames.'
    ),
    GTConfig.gt_select_frames_for_bake_idname: Button(
        'Select frames:',
        'Create texture using selected frames'
    ),
    GTConfig.gt_reproject_tex_sequence_idname: Button(
        'Reproject texture sequence',
        'Choose dir where to place resulting sequence'
    ),
    # Main UI
    GTConfig.gt_addon_setup_defaults_idname: Button(
        'Setup GeoTracker defaults',
        'Open GeoTracker Settings in Preferences window'
    ),
    GTConfig.gt_create_geotracker_idname: Button(
        'Create GeoTracker',
        'Create a new GeoTracker object in scene'
    ),
    GTConfig.gt_delete_geotracker_idname: Button(
        'Delete GeoTracker',
        'Delete this GeoTracker object from scene'
    ),
    GTConfig.gt_select_geotracker_objects_idname: Button(
        'Select objects',
        'Select GeoTracker objects in scene'
    ),
    GTConfig.gt_create_precalc_idname: Button(
        'Create precalc',
        'Create precalc for current MovieClip'
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
        'track to start'
    ),
    GTConfig.gt_track_to_end_idname: Button(
        'Track to end',
        'track to end'
    ),
    GTConfig.gt_track_next_idname: Button(
        'Track next',
        'track next'
    ),
    GTConfig.gt_track_prev_idname: Button(
        'Track prev',
        'track prev'
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
        'Clear all tracking data'
    ),
    GTConfig.gt_clear_tracking_forward_idname: Button(
        'Clear forward',
        'Clear tracking data forward'
    ),
    GTConfig.gt_clear_tracking_backward_idname: Button(
        'Clear backward',
        'Clear tracking data backward'
    ),
    GTConfig.gt_clear_tracking_between_idname: Button(
        'Clear between',
        'Clear tracking data between keyframes'
    ),
    GTConfig.gt_refine_idname: Button(
        'refine',
        'Refine tracking between nearest keyframes'
    ),
    GTConfig.gt_refine_all_idname: Button(
        'refine all',
        'Refine all tracking data'
    ),
    GTConfig.gt_center_geo_idname: Button(
        'center geo',
        'Center geometry in the view'
    ),
    GTConfig.gt_magic_keyframe_idname: Button(
        'magic',
        'Magic keyframe detection'
    ),
    GTConfig.gt_remove_pins_idname: Button(
        'remove pins',
        'Remove all pins from view'
    ),
    GTConfig.gt_toggle_pins_idname: Button(
        'toggle pins',
        'toggle pins operation'
    ),
    GTConfig.gt_create_animated_empty_idname: Button(
        'Create animated Empty',
        'Copy animation to Empty'
    ),
    GTConfig.gt_exit_pinmode_idname: Button(
        'Exit Pinmode',
        'Exit from PinMode'
    ),
    GTConfig.gt_stop_calculating_idname: Button(
        'Stop calculating',
        'Stop calculating'
    ),
    GTConfig.gt_reset_tone_exposure_idname: Button(
        'Reset exposure',
        'Reset exposure in tone mapping'
    ),
    GTConfig.gt_reset_tone_gamma_idname: Button(
        'Reset gamma',
        'Reset gamma in tone mapping'
    ),
    GTConfig.gt_reset_tone_mapping_idname: Button(
        'Reset tone mapping',
        'Revert default values in tone mapping'
    ),
    GTConfig.gt_default_wireframe_settings_idname: Button(
        'Revert to defaults',
        'Set the wireframe colours and opacity as in the saved defaults'
    ),
    GTConfig.gt_default_pin_settings_idname: Button(
        'Revert to defaults',
        'Set pin size and active area as in the saved defaults'
    ),
    GTConfig.gt_reproject_frame_idname: Button(
        'Reproject frame',
        'Reproject current frame to get texture'
    ),
    GTConfig.gt_select_all_frames_idname: Button(
        'Select All',
        'Select all keyframes for getting texture by reprojection'
    ),
    GTConfig.gt_deselect_all_frames_idname: Button(
        'Deselect All',
        'Deselect all keyframes for getting texture by reprojection'
    ),
    GTConfig.gt_relative_to_camera_idname: Button(
        'Relative to Camera',
        'Move the Camera to default position and place '
        'the Geometry according to this position'
    ),
    GTConfig.gt_relative_to_geometry_idname: Button(
        'Relative to Geometry',
        'Move the Geometry to default position and place '
        'the Camera according to this position'
    ),
    GTConfig.gt_geometry_repositioning_idname: Button(
        'Geometry repositioning',
        'Move the whole Geometry animation according to '
        'current (changed but not saved) position'
    ),
    GTConfig.gt_camera_repositioning_idname: Button(
        'Camera repositioning',
        'Move the whole Camera animation according to '
        'current (changed but not saved) position'
    ),
    GTConfig.gt_move_tracking_to_camera_idname: Button(
        'Move tracking to Camera',
        'Move both objects animation to Camera only'
    ),
    GTConfig.gt_move_tracking_to_geometry_idname: Button(
        'Move tracking to Geometry',
        'Move both objects animation to Geometry only'
    ),
    GTConfig.gt_remove_focal_keyframe_idname: Button(
        'Remove focal keyframe',
        'Remove a single keyframe in the current frame'
    ),
    GTConfig.gt_remove_focal_keyframes_idname: Button(
        'Remove all focal keyframes',
        'Remove all focal keyframes'
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
}
