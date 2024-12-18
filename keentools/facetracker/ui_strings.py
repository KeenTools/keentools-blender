# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2022-2023 KeenTools

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

from ..facetracker_config import FTConfig


Button = namedtuple('Button', ['label', 'description'])

buttons = {
    FTConfig.ft_pinmode_idname: Button(
        'FaceTracker Pinmode',
        'Align geometry with the target in your clip and proceed to tracking'
    ),
    FTConfig.ft_movepin_idname: Button(
        'FaceTracker MovePin',
        'FaceTracker MovePin operator'
    ),
    FTConfig.ft_pickmode_idname: Button(
        'FaceTracker Pick Face mode',
        'Modal Operator for Pick Face mode'
    ),
    FTConfig.ft_pickmode_starter_idname: Button(
        'Auto Align',
        'Auto align mesh in current view'
    ),
    FTConfig.ft_switch_to_camera_mode_idname: Button(
        'Camera',
        'Track Camera'
    ),
    FTConfig.ft_switch_to_geometry_mode_idname: Button(
        'Head',
        'Track Head'
    ),
    FTConfig.ft_actor_idname: Button(
        'Actor Operator',
        'FaceTracker Action'
    ),
    FTConfig.ft_sequence_filebrowser_idname: Button(
        'Load clip',
        'Load a sequence of frames or a movie file'
    ),
    FTConfig.ft_mask_sequence_filebrowser_idname: Button(
        'Load mask sequence',
        'Both image sequences and movie files are supported'
    ),
    FTConfig.ft_choose_precalc_file_idname: Button(
        'Choose analysis filename',
        'Use existing .precalc file or enter new name'
    ),
    FTConfig.ft_split_video_to_frames_idname: Button(
        'Split video to frames',
        'Choose folder'
    ),
    FTConfig.ft_split_video_to_frames_exec_idname: Button(
        'Split video to frames',
        'Choose folder'
    ),
    FTConfig.ft_video_snapshot_idname: Button(
        'Take snapshot',
        'Take snapshot of current frame'
    ),
    FTConfig.ft_bake_from_selected_frames_idname: Button(
        'Create Texture',
        'Project and bake texture from selected frames onto Geometry'
    ),
    FTConfig.ft_reproject_tex_sequence_idname: Button(
        'Save to sequence',
        'Project and bake texture in all frames and save as animated sequence'
    ),
    FTConfig.ft_precalc_info_idname: Button(
        'Analysis file info',
        'Click this button to see .precalc file info'
    ),
    FTConfig.ft_analyze_call_idname: Button(
        'Analyse',
        'Call analyse dialog'
    ),
    FTConfig.ft_confirm_recreate_precalc_idname: Button(
        'Recreate analysis file',
        'Are you sure to recreate analysis file?'
    ),
    FTConfig.ft_texture_bake_options_idname: Button(
        'Texture settings',
        'Setup texture options for baking'
    ),
    FTConfig.ft_texture_file_export_idname: Button(
        'Export texture',
        'Export texture to file'
    ),
    FTConfig.ft_delete_texture_idname: Button(
        'Delete texture',
        'Delete texture from scene'
    ),

    # Main UI
    FTConfig.ft_addon_setup_defaults_idname: Button(
        'FaceTracker settings',
        'Open Preferences/Add-ons for more settings'
    ),
    FTConfig.ft_create_facetracker_idname: Button(
        'Create new FaceTracker',
        'Track facial performance'
    ),
    FTConfig.ft_delete_facetracker_idname: Button(
        'Delete FaceTracker',
        'Delete this FaceTracker object from scene'
    ),
    FTConfig.ft_select_facetracker_objects_idname: Button(
        'Select objects',
        'Select assigned Geometry and Camera in scene'
    ),
    FTConfig.ft_create_precalc_idname: Button(
        'Create precalc',
        'Create precalc for current MovieClip'
    ),
    FTConfig.ft_auto_name_precalc_idname: Button(
        'Generate precalc filename',
        'Generate precalc filename'
    ),
    FTConfig.ft_prev_keyframe_idname: Button(
        'Prev keyframe',
        'Move to the previous FaceTracker keyframe on the timeline',
    ),
    FTConfig.ft_next_keyframe_idname: Button(
        'Next keyframe',
        'Move to the next FaceTracker keyframe on the timeline'
    ),
    FTConfig.ft_toggle_lock_view_idname: Button(
        'Toggle Lock View',
        'Press to toggle Lock for current view'
    ),
    FTConfig.ft_track_to_start_idname: Button(
        'Track to start',
        'Track backwards'
    ),
    FTConfig.ft_track_to_end_idname: Button(
        'Track to end',
        'Track forward'
    ),
    FTConfig.ft_track_next_idname: Button(
        'Track next',
        'Track to next frame'
    ),
    FTConfig.ft_track_prev_idname: Button(
        'Track prev',
        'Track to previous frame'
    ),
    FTConfig.ft_add_keyframe_idname: Button(
        'Add FaceTracker keyframe',
        'add keyframe'
    ),
    FTConfig.ft_remove_keyframe_idname: Button(
        'Remove FaceTracker keyframe',
        'remove keyframe'
    ),
    FTConfig.ft_clear_all_tracking_idname: Button(
        'Clear all',
        'Delete all keyframes'
    ),
    FTConfig.ft_clear_tracking_except_keyframes_idname: Button(
        'Clear tracking data only',
        'Clear tracking data, keep FaceTracker keyframes'
    ),
    FTConfig.ft_clear_tracking_forward_idname: Button(
        'Clear forward',
        'Clear all keyframes to the right of current frame'
    ),
    FTConfig.ft_clear_tracking_backward_idname: Button(
        'Clear backwards',
        'Clear all keyframes to the left of current frame'
    ),
    FTConfig.ft_clear_tracking_between_idname: Button(
        'Clear between',
        'Clear tracking data between nearest FaceTracker keyframes'
    ),
    FTConfig.ft_refine_idname: Button(
        'Refine',
        'Refine tracking data between nearest keyframes'
    ),
    FTConfig.ft_refine_all_idname: Button(
        'Refine All',
        'Refine all tracking data'
    ),
    FTConfig.ft_center_geo_idname: Button(
        'Center Geo',
        'Place target geometry in the center of your viewpoint'
    ),
    FTConfig.ft_magic_keyframe_idname: Button(
        'Magic',
        'Magic keyframe detection'
    ),
    FTConfig.ft_remove_pins_idname: Button(
        'Remove Pins',
        'Delete all or only selected pins'
    ),
    FTConfig.ft_toggle_pins_idname: Button(
        'Toggle Pins',
        'Toggle all or only selected pins'
    ),
    FTConfig.ft_unbreak_rotation_idname: Button(
        'Unbreak Rotation',
        'Fix rotation making it continuous and removing 360 degrees jumps'
    ),
    FTConfig.ft_rescale_window_idname: Button(
        'Scale',
        'Scale scene'
    ),
    FTConfig.ft_move_window_idname: Button(
        'Position',
        'Move scene'
    ),
    FTConfig.ft_rig_window_idname: Button(
        'Rig',
        'Create an Empty with parented Camera and Geometry'
    ),
    FTConfig.ft_export_animated_empty_idname: Button(
        'Export',
        'Create an animated Empty'
    ),
    FTConfig.ft_exit_pinmode_idname: Button(
        'Back to 3D',
        'Back to 3D scene'
    ),
    FTConfig.ft_stop_calculating_idname: Button(
        'Stop calculating',
        'Stop calculating'
    ),
    FTConfig.ft_reset_tone_exposure_idname: Button(
        'Reset',
        'Reset exposure to default value'
    ),
    FTConfig.ft_reset_tone_gamma_idname: Button(
        'Reset',
        'Reset gamma to default value'
    ),
    FTConfig.ft_reset_tone_mapping_idname: Button(
        'Reset',
        'Reset all to default values'
    ),
    FTConfig.ft_default_wireframe_settings_idname: Button(
        'Reset',
        'Reset colour and opacity to default values'
    ),
    FTConfig.ft_default_pin_settings_idname: Button(
        'Reset',
        'Reset all to default values'
    ),
    FTConfig.ft_wireframe_color_idname: Button(
        'Wireframe color',
        'Choose the wireframe coloring scheme'
    ),
    FTConfig.ft_reset_texture_resolution_idname: Button(
        'Reset',
        'Reset texture resolution to default values'
    ),
    FTConfig.ft_reset_advanced_settings_idname: Button(
        'Reset',
        'Reset advanced texture baking settings'
    ),
    FTConfig.ft_check_uv_overlapping_idname: Button(
        'Check',
        'Check for overlapping UVs'
    ),
    FTConfig.ft_repack_overlapping_uv_idname: Button(
        'Repack',
        'Attempt to reorganize UVs as non-overlapping islands'
    ),
    FTConfig.ft_create_non_overlapping_uv_idname: Button(
        'Create Smart UV',
        'Create new non-overlapping UVs'
    ),
    FTConfig.ft_add_bake_frame_idname: Button(
        'Add frame',
        'Add current frame to bake list'
    ),
    FTConfig.ft_remove_bake_frame_idname: Button(
        'Remove frame',
        'Remove selected frame from bake list'
    ),
    FTConfig.ft_go_to_bake_frame_idname: Button(
        'Go to',
        'Jump to this frame'
    ),
    FTConfig.ft_transfer_tracking_idname: Button(
        'Convert',
        'Convert all animation'
    ),
    FTConfig.ft_bake_animation_to_world_idname: Button(
        'Bake animation',
        'Convert animation to world space'
    ),
    FTConfig.ft_remove_focal_keyframe_idname: Button(
        'Remove current',
        'Remove focal length animation key in current keyframe'
    ),
    FTConfig.ft_remove_focal_keyframes_idname: Button(
        'Remove all',
        'Remove all focal length animation keys'
    ),
    FTConfig.ft_render_with_background_idname: Button(
        'Render with background',
        'Enable rendering with background using compositing nodes'
    ),
    FTConfig.ft_revert_default_render_idname: Button(
        'Revert default rendering',
        'Setup scene rendering settings to match default render view'
    ),
    FTConfig.ft_save_facs_idname: Button(
        'Save as .csv',
        'Save facial animation as a .csv file'
    ),
    FTConfig.ft_create_new_head_idname: Button(
        'New',
        'Create new FaceBuilder Head'
    ),
    FTConfig.ft_edit_head_idname: Button(
        'Edit',
        'Edit FaceBuilder Head'
    ),
    FTConfig.ft_choose_frame_mode_idname: Button(
        'Choose frame mode',
        'Add another snapshot of a video frame'
    ),
    FTConfig.ft_cancel_choose_frame_idname: Button(
        'Cancel',
        'Just go back'
    ),
    FTConfig.ft_add_chosen_frame_idname: Button(
        'Take Snapshot',
        'Add current frame as a reference image for FaceBuilder'
    ),
    FTConfig.ft_transfer_facs_animation_idname: Button(
        'Convert',
        'Transfer facial animation to target geometry'
    ),
    FTConfig.ft_transfer_animation_to_rig_idname: Button(
        'Convert',
        'Transfer facial animation to target rig'
    ),
    FTConfig.ft_transfer_animation_to_rig_options_idname: Button(
        'Options',
        'Setup transfer settings'
    ),
    # Menu buttons
    FTConfig.ft_clear_tracking_menu_exec_idname: Button(
        'Clear menu',
        'Clear all or tracking data only'
    ),
    FTConfig.ft_clear_tracking_menu_idname: Button(
        'Clear menu (internal)',
        'Clear menu list (internal)'
    ),
    FTConfig.ft_clip_menu_idname: Button(
        'Clip menu',
        'Load new clip / Make snapshot / Split video'
    ),
    # Help buttons
    FTConfig.ft_help_inputs_idname: Button(
        'Inputs help',
        'Show help information about Inputs panel'
    ),
    FTConfig.ft_help_masks_idname: Button(
        'Masks help',
        'Show help information about Masks panel'
    ),
    FTConfig.ft_help_analyze_idname: Button(
        'Analyze help',
        'Show help information about Analyze panel'
    ),
    FTConfig.ft_help_camera_idname: Button(
        'Camera help',
        'Show help information about Camera settings panel'
    ),
    FTConfig.ft_help_tracking_idname: Button(
        'Tracking help',
        'Show help information about Tracking panel'
    ),
    FTConfig.ft_help_appearance_idname: Button(
        'Appearance help',
        'Show help information about Appearance panel'
    ),
    FTConfig.ft_help_texture_idname: Button(
        'Texture help',
        'Show help information about Texture panel'
    ),
    FTConfig.ft_help_animation_idname: Button(
        'Animation help',
        'Show help information about Animation panel'
    ),
    FTConfig.ft_help_rendering_idname: Button(
        'Rendering help',
        'Show help information about Rendering panel'
    ),
    FTConfig.ft_help_smoothing_idname: Button(
        'Smoothing help',
        'Show help information about Smoothing panel'
    ),
}


HelpText = namedtuple('HelpText', ['width', 'message'])
_help_default_width = 500


help_texts = {
    FTConfig.ft_help_inputs_idname: HelpText(_help_default_width, [
        'Select three main elements needed for successful tracking:',
        ' ',
        'Clip - your footage (sequence or a movie file)',
        'Head - 3D head with FaceBuilder topology',
        'New - create new FaceBuilder head using snapshots of video frames and image files',
        'Edit - edit face geometry with FaceBuilder',
        'Camera - the viewing point relevant to which your object will be tracked',
        ' ',
        'Use Analyse option for faster tracking',
    ]),
    FTConfig.ft_help_masks_idname: HelpText(_help_default_width, [
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
        'over the element you want FaceTracker to ignore when tracking. Go back to the 3D viewport',
        'and select your mask in the Compositing mask tab',
    ]),
    FTConfig.ft_help_analyze_idname: HelpText(_help_default_width, [
        'Analyze panel description will be here...',
        ' '
    ]),
    FTConfig.ft_help_camera_idname: HelpText(_help_default_width, [
        'Specify your camera settings to match them with the ones of the camera on the set.',
        ' ',
        'Use automatic focal length estimation if those values are unknown.',
        'Note that it works only for the current frame and you\'ll need to have',
        'at least 4 pins set on the wireframe.',
        ' ',
        'Select whether the focal length in your shot is variable or fixed',
    ]),
    FTConfig.ft_help_tracking_idname: HelpText(_help_default_width, [
        'Select Head + facial mocap or Camera + facial mocap.',
        'Use Auto Align for automatic model placement.',
        'Line up face geometry to the background image as precisely as possible using pins.',
        'Track forward or backwards using tracking buttons.',
        'Pause tracking whenever you see the mesh is off, click and drag pins to adjust its position.',
        'Use Refine button to update tracking data.',
    ]),
    FTConfig.ft_help_appearance_idname: HelpText(_help_default_width, [
        'Here you can tweak how pins look and react to mouse and change ',
        'the colours used for the wireframe of FaceBuilder '
        'visible in pin mode.'
    ]),
    FTConfig.ft_help_texture_idname: HelpText(_help_default_width, [
        'Use \'Create Texture\' to project and bake texture '
        'from selected frames onto Geometry.',
        'Use \'Save to Sequence\' to project Clip onto Geometry '
        'frame by frame and save it ',
        'as image sequence.',
    ]),
    FTConfig.ft_help_animation_idname: HelpText(_help_default_width, [
        'Transform: Scale and position your scene in 3D space right from FaceTracker.',
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
    FTConfig.ft_help_rendering_idname: HelpText(_help_default_width, [
        'Rendering panel description will be here...',
        ' '
    ]),
    FTConfig.ft_help_smoothing_idname: HelpText(_help_default_width, [
        'All smoothing settings are effective during tracking and refine only.',
        'Once the tracking is done, changing them will not change the track,',
        'you need to launch tracking or refine again to apply new smoothing settings.',
        'You can tweak them differently for different parts of the footage,',
        'the values are not being saved for different parts of the footage.',
        '0 means no smoothing while 1 makes the smoothed parameter(s) almost static.',
    ]),
}
