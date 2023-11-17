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
    GTConfig.gt_bake_from_selected_frames_idname: Button(
        'Create Texture',
        'Project and bake texture from selected frames onto Geometry'
    ),
    GTConfig.gt_reproject_tex_sequence_idname: Button(
        'Save to sequence',
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
    GTConfig.gt_texture_bake_options_idname: Button(
        'Texture settings',
        'Setup texture options for baking'
    ),
    GTConfig.gt_texture_file_export_idname: Button(
        'Export texture',
        'Export texture to file'
    ),
    GTConfig.gt_delete_texture_idname: Button(
        'Delete texture',
        'Delete texture from scene'
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
    GTConfig.gt_toggle_lock_view_idname: Button(
        'Toggle Lock View',
        'Press to toggle Lock for current view'
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
    GTConfig.gt_share_feedback_idname: Button(
        'Share Feedback',
        'Send feedback. Help us improve'
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
    GTConfig.gt_reset_texture_resolution_idname: Button(
        'Reset',
        'Reset texture resolution to default values'
    ),
    GTConfig.gt_reset_advanced_settings_idname: Button(
        'Reset',
        'Reset advanced texture baking settings'
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
        'Create Smart UV',
        'Create new non-overlapping UVs'
    ),
    GTConfig.gt_add_bake_frame_idname: Button(
        'Add frame',
        'Add current frame to bake list'
    ),
    GTConfig.gt_remove_bake_frame_idname: Button(
        'Remove frame',
        'Remove selected frame from bake list'
    ),
    GTConfig.gt_go_to_bake_frame_idname: Button(
        'Go to',
        'Jump to this frame'
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
        'Select three main elements needed for successful tracking:',
        ' ',
        'Clip - your footage (sequence or a movie file)',
        'Geometry - 3D model of a similar shape to the object you want to track',
        'Camera - the viewing point relevant to which your object will be tracked',
        ' ',
        'Use Analyse option for faster tracking',
    ]),
    GTConfig.gt_help_masks_idname: HelpText(_help_default_width, [
        'Oftentimes various elements in the video get in the way of tracking and that results',
        'in Geometry slipping away from the target object. You can use two types of masks',
        'to exclude problematic areas from tracking.',
        ' ',
        'Surface mask allows you to select polygons right on the surface of your Geometry',
        'to exclude them from tracking. This can be useful when dealing with reflection',
        'or when you need to take out certain elements, like adjacent parts, of your 3D model',
        'from tracking. Switch to Edit Mode and select the polygons you want to mask out,',
        'then go to Object Data Properties and create a new vertex group. Return to Object Mode',
        'and select the newly created group in the Surface mask dropdown list.',
        ' ',
        'Compositing mask works for most overlays like the character’s hand or other elements',
        'in the foreground crossing the path of the track. Go to Blender Movie Clip Editor',
        'and select your clip. Switch the Tracking mode to Mask and click on Add > Circle',
        '(or other shape that fits for your situation). Press Move and place your mask',
        'over the element you want GeoTracker to ignore when tracking. Go back to the 3D viewport',
        'and select your mask in the Compositing mask tab',
    ]),
    GTConfig.gt_help_analyze_idname: HelpText(_help_default_width, [
        'Analyze panel description will be here...',
        ' '
    ]),
    GTConfig.gt_help_camera_idname: HelpText(_help_default_width, [
        'Specify your camera settings to match them with the ones of the camera on the set.',
        ' ',
        'Use automatic focal length estimation if those values are unknown.',
        'Note that it works only for the current frame and you\'ll need to have',
        'at least 4 pins set on the wireframe.',
        ' ',
        'Select whether the focal length in your shot is variable or fixed',
    ]),
    GTConfig.gt_help_tracking_idname: HelpText(_help_default_width, [
        'Select whether you’ll be tracking Geometry or Camera.',
        'Overlay Geometry on top of the shot in Pinmode as precisely as possible.',
        'Track forward or backwards using tracking buttons.',
        'Adjust Geometry position manually whenever you see it\'s off.',
        'Use the Refine button to update tracking data',
    ]),
    GTConfig.gt_help_appearance_idname: HelpText(_help_default_width, [
        'Here you can tweak how pins look and react to mouse and change ',
        'the colours used for the wireframe of FaceBuilder '
        'visible in pin mode.'
    ]),
    GTConfig.gt_help_texture_idname: HelpText(_help_default_width, [
        'Use \'Create Texture\' to project and bake texture '
        'from selected frames onto Geometry.',
        'Use \'Save to Sequence\' to project Clip onto Geometry '
        'frame by frame and save it ',
        'as image sequence.',
    ]),
    GTConfig.gt_help_animation_idname: HelpText(_help_default_width, [
        'Transform: Scale and position your scene in 3D space right from GeoTracker.',
        'You can scale either the whole scene relative to selected Pivot point',
        'or Geometry relevant to Camera, or Camera relevant to Geometry.',
        ' ',
        'You can position your scene by selecting either Camera or Geometry as the pivot point.',
        'Set the Location and Rotation values manually or use preset positions',
        'such as World Origin and 3D Cursor. ',
        ' ',
        'The Rig button lets you create an Empty with parented Camera and/or Geometry',
        'that you can use as a handle when building your 3D scene.',
        ' ',
        'Animation: Convert animation according to your purposes',
        'Convert your Camera animation to Geometry or the vice versa. Note that',
        'if both the Camera and Geometry are animated, pressing the Convert button will convert',
        'all animation to one and then this operation will not be reversible!',
        'Bake animation to World space to unparent Camera and Geometry.',
        ' ',
        'Export your tracking results as an animated Empty.',
        'Select whether it’s the Geometry or Camera animation to be exported.',
        'Use Linked option to keep your animated Empty synced with further tracking data changes.'
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
    ]),
}


class PrecalcStatusMessage:
    broken_file: str = '* Analysis file is broken'
    missing_file: str = '* .precalc file is missing'
    empty: str = ''
