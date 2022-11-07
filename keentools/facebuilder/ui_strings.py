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

from collections import namedtuple

from ..facebuilder_config import FBConfig


Button = namedtuple('Button', ['label', 'description'])

buttons = {
    FBConfig.fb_add_head_operator_idname: Button(
        'FaceBuilder Head',
        'Add FaceBuilder Head into scene'
    ),
    FBConfig.fb_single_filebrowser_exec_idname: Button(
        'File Browser Execute',
        'Change the image file path'
    ),
    FBConfig.fb_single_filebrowser_idname: Button(
        'Open Image',
        'Open single image file'
    ),
    FBConfig.fb_texture_file_export_idname: Button(
        'Export texture',
        'Export the created texture to a file'
    ),
    FBConfig.fb_multiple_filebrowser_exec_idname: Button(
        'Open Images',
        'Load images and create views. You can select multiple images at once'
    ),
    FBConfig.fb_multiple_filebrowser_idname: Button(
        'Open Images',
        'Load images and create views. You can select multiple images at once'
    ),
    FBConfig.fb_animation_filebrowser_idname: Button(
        'Load animation',
        'Open animation file'
    ),
    FBConfig.fb_history_actor_idname: Button(
        'FaceBuilder Action',
        'FaceBuilder'
    ),
    FBConfig.fb_camera_actor_idname: Button(
        'Camera parameters',
        'Parameters setup'
    ),
    FBConfig.fb_blendshapes_warning_idname: Button(
        'Warning',
        ''
    ),
    FBConfig.fb_noblenshapes_until_expression_warning_idname: Button(
        'Blendshapes can\'t be created',
        ''
    ),
    FBConfig.fb_tex_selector_idname: Button(
        'Select images:',
        'Create texture using pinned views'
    ),
    FBConfig.fb_pickmode_idname: Button(
        'FaceBuilder Pick Face mode',
        'Modal Operator for Pick Face mode'
    ),
    FBConfig.fb_pickmode_starter_idname: Button(
        'FaceBuilder Pick Face mode starter',
        'Detect a face on the photo and pin the model to the selected face'
    ),
    FBConfig.fb_pinmode_idname: Button(
        'FaceBuilder Pinmode',
        'Operator for in-Viewport drawing'
    ),
    FBConfig.fb_movepin_idname: Button(
        'FaceBuilder MovePin',
        'FaceBuilder MovePin operator'
    ),
    # Main UI
    FBConfig.fb_select_head_idname: Button(
        'Select head',
        'Select head in the scene'
    ),
    FBConfig.fb_delete_head_idname: Button(
        'Delete head',
        'Delete the head and its cameras from the scene'
    ),
    FBConfig.fb_select_camera_idname: Button(
        'Pin Mode Select Camera',
        'Switch to Pin mode for this view'
    ),
    FBConfig.fb_center_geo_idname: Button(
        'Reset Camera',
        'Place the camera so the model will be centred in the view'
    ),
    FBConfig.fb_unmorph_idname: Button(
        'Reset',
        'Reset shape deformations to the default state. '
        'It will remove all pins as well'
    ),
    FBConfig.fb_remove_pins_idname: Button(
        'Remove pins',
        'Remove all pins on this view'
    ),
    FBConfig.fb_wireframe_color_idname: Button(
        'Wireframe color',
        'Choose the wireframe coloring scheme'
    ),
    FBConfig.fb_filter_cameras_idname: Button(
        'Camera Filter',
        'Select cameras to use for texture baking'
    ),
    FBConfig.fb_delete_camera_idname: Button(
        'Delete View',
        'Delete this view and its camera from the scene'
    ),
    FBConfig.fb_proper_view_menu_exec_idname: Button(
        'View operations',
        'Delete the view or modify the image file path'
    ),
    FBConfig.fb_addon_setup_defaults_idname: Button(
        'Setup FaceBuilder defaults',
        'Open FaceBuilder Settings in Preferences window'
    ),
    FBConfig.fb_bake_tex_idname: Button(
        'Bake Texture',
        'Bake the texture using all selected cameras. '
        'It can take a lot of time, be patient'
    ),
    FBConfig.fb_delete_texture_idname: Button(
        'Delete texture',
        'Delete the created texture from the scene'
    ),
    FBConfig.fb_rotate_image_cw_idname: Button(
        'Rotate Image CW',
        'Rotate image clock-wise'
    ),
    FBConfig.fb_rotate_image_ccw_idname: Button(
        'Rotate Image CCW',
        'Rotate image counter clock-wise'
    ),
    FBConfig.fb_reset_image_rotation_idname: Button(
        'Reset Image Rotation',
        'Reset Image Rotation'
    ),
    FBConfig.fb_reset_expression_idname: Button(
        'Reset expression',
        'Reset expression'
    ),
    FBConfig.fb_show_tex_idname: Button(
        'Show Texture',
        'Create a material from the generated texture and apply it to the model'
    ),
    FBConfig.fb_show_solid_idname: Button(
        'Show Solid',
        'Hide texture and go back to Solid mode'
    ),
    FBConfig.fb_exit_pinmode_idname: Button(
        'Exit Pin mode',
        'Exit Pin mode'
    ),
    FBConfig.fb_create_blendshapes_idname: Button(
        'Create',
        'Create FACS blendshapes'
    ),
    FBConfig.fb_delete_blendshapes_idname: Button(
        'Delete',
        'Delete all blendshapes (Shape Keys), unlink animation'
    ),
    FBConfig.fb_load_animation_from_csv_idname: Button(
        'Load CSV',
        'Load animation keyframes from a CSV file (LiveLinkFace format)'
    ),
    FBConfig.fb_create_example_animation_idname: Button(
        'Example keyframes',
        'Create example animation keyframes for each blendshape'
    ),
    FBConfig.fb_reset_blendshape_values_idname: Button(
        'Reset values',
        'Reset the values of blendshapes (Shape Keys), '
        'so the model will be in the neutral state. '
        'This doesn\'t affect any of the existing keyframes. '
        'If you want to store the neutral state to a keyframe, '
        'you need to do it manually'
    ),
    FBConfig.fb_clear_animation_idname: Button(
        'Clear animation',
        'Unlink animation from blendshapes (Shape Keys). '
        'Effectively, removes the model animation. '
        'You can "reattach" the animation to the head '
        'until you close the project. Once the project is closed '
        'all unlinked animation is lost'
    ),
    FBConfig.fb_export_head_to_fbx_idname: Button(
        'Export as FBX',
        'Export geometry with all blendshapes '
        'and animation to FBX suitable '
        'for game engines (UE4, Unity, etc.)'
    ),
    FBConfig.fb_update_blendshapes_idname: Button(
        'Update',
        'Update blendshapes'
    ),
    FBConfig.fb_unhide_head_idname: Button(
        'Show Head',
        'Show Head'
    ),
    FBConfig.fb_reconstruct_head_idname: Button(
        'Reconstruct!',
        'Reconstruct head by KeenTools attributes on mesh'
    ),
    FBConfig.fb_default_pin_settings_idname: Button(
        'Revert to defaults',
        'Set pin size and active area as in the saved defaults'
    ),
    FBConfig.fb_default_wireframe_settings_idname: Button(
        'Revert to defaults',
        'Set the wireframe colours and opacity as in the saved defaults'
    ),
    FBConfig.fb_select_current_head_idname: Button(
        'Current head',
        'Select current head in the scene'
    ),
    FBConfig.fb_select_current_camera_idname: Button(
        'Current view',
        'Current view. Press to exit from Pin mode'
    ),
    FBConfig.fb_reset_tone_exposure_idname: Button(
        'Reset exposure',
        'Reset exposure in tone mapping'
    ),
    FBConfig.fb_reset_tone_gamma_idname: Button(
        'Reset gamma',
        'Reset gamma in tone mapping'
    ),
    # Help buttons
    FBConfig.fb_help_camera_idname: Button(
        'Camera settings',
        'Show help information about Camera settings panel'
    ),
    FBConfig.fb_help_views_idname: Button(
        'Views',
        'Show help information about Views panel'
    ),
    FBConfig.fb_help_model_idname: Button(
        'Model',
        'Show help information about Model panel'
    ),
    FBConfig.fb_help_appearance_idname: Button(
        'Appearance',
        'Show help information about Appearance panel'
    ),
    FBConfig.fb_help_texture_idname: Button(
        'Texture',
        'Show help information about Texture panel'
    ),
    FBConfig.fb_help_blendshapes_idname: Button(
        'Blendshapes',
        'Show help information about Blendshapes panel'
    ),
}


HelpText = namedtuple('HelpText', ['width', 'message'])
_help_default_width = 500

help_texts = {
    FBConfig.fb_help_camera_idname: HelpText(_help_default_width, [
        'To get a quality model you need to know one important thing about',
        'your photos — the 35mm equivalent focal length the photos '
        'were taken with.',
        'Usually we can automatically get this data from EXIF of the '
        'loaded pictures.',
        ' ',
        'Unfortunately it\'s not a rare case when this data is stripped '
        'out of the photos.',
        'In this case you still can get a quality model manually '
        'setting up the focal',
        'length if you know it. In all other cases we recommend using '
        'focal length estimation.',
        ' ',
        'If you don\'t know the focal length, we recommend you to not '
        'change anything. ',
        'Please rely on automatic settings, that should provide you '
        'the best possible results.',
        ' ',
        'If you know the focal length and want to check that '
        'everything\'s correct,',
        'you can open this panel and see the detected 35mm equiv. '
        'focal length. ',
        'You can change it if you switch into manual mode using '
        'the advanced setting menu',
        'in the header of the camera settings panel.',
        ' ',
        'When we detect similar 35mm equiv. focal length across a number '
        'of photographs',
        'we add them into one group, it helps our face morphing algorithm '
        'in cases ',
        'when there are more than one groups with different focal lengths. '
        'You can also ',
        'add different pictures with unknown focal length into one '
        'group manually,',
        'so the FL estimation algorithm will treat them all as if they '
        'were taken with ',
        'the same 35mm equiv. focal length, but we recommend to only do '
        'so if you really ',
        'know what you\'re doing.'
    ]),
    FBConfig.fb_help_views_idname: HelpText(_help_default_width, [
        'On this panel you can load and remove images '
        'automatically creating ',
        'and removing views, replace image files, set the Frame size '
        'and go into Pin Mode ',
        'for each of the Views.',
        ' ',
        'Please note that all images loaded into stack should have '
        'the same dimensions,',
        'they should be shot with the same camera settings (sensor '
        'size and focal length),',
        'should not be cropped (or the camera settings should be '
        'modified accordingly),',
        'should be shot in the same orientation (vertical or horizontal).'
    ]),
    FBConfig.fb_help_model_idname: HelpText(_help_default_width, [
        'On this panel you can modify the 3D model of the '
        'head in different ways: ',
        'switch on and off different parts of the model (pins '
        'created on the disabled parts ',
        'remain intact), reset the model to the default state '
        '(also removing all pins ',
        'on all views), and finally you can modify the rigidity '
        'of the model — ',
        'the less is the number, the softer the model becomes '
        'and the more pins ',
        'affect its shape.'
    ]),
    FBConfig.fb_help_appearance_idname: HelpText(_help_default_width, [
        'Here you can tweak how pins look and react to mouse and change ',
        'the colours used for the wireframe of FaceBuilder '
        'visible in pin mode.'
    ]),
    FBConfig.fb_help_texture_idname: HelpText(_help_default_width, [
        'This panel gives you access to an experimental functionality '
        'of automatic texture ',
        'grabbing and stitching. You can change the resolution '
        'of the texture, its layout. ',
        'You can choose which views to use in the grabbing process '
        'after clicking ',
        'the "Create Texture" button, also you can apply '
        'the material created ',
        'automatically from the grabbed texture to the head object. ',
        ' ',
        'Finally you can tweak the grabbing and stitching algorithm: ',
        '— Brightness equalisation is a highly experimental '
        'feature that will try ',
        'to normalise the brightness of different texture parts '
        'across different views. ',
        '— Colour equalisation is similar to Brightness equalisation '
        'only it affects ',
        'colour instead of brightness.',
        '— Angle strictness determines how much the angle of view '
        'of the polygon affects ',
        'the weight of the colour information grabbed for each pixel. '
        'The value range ',
        'is 0-100. When you have multiple frames containing '
        'the same pixel, 0 would mean ',
        'that in the texture you’ll get an average colour of that pixel '
        'between colours ',
        'from all frames where the pixel was found. The larger '
        'the number — the more ',
        'the algorithm prefers frames where the angle '
        'of view of the pixel ',
        'is closer to 90°, still mixing colours from all frames '
        'but with different strength.',
        '— Expanding edges can help with hiding stitches on texture '
        'edges visible when ',
        'the texture is applied to the object. It basically takes '
        'the colour of the last ',
        'pixel on the edge and duplicates it on the next empty pixel.'
    ]),
    FBConfig.fb_help_blendshapes_idname: HelpText(_help_default_width, [
        'On this panel you can create FACS ARKit-compatible blendshapes '
        'for the head ',
        'you\'ve built, load animation from a CSV file and export the head '
        'with all blendshapes ',
        'and animation to a game engine.',
        ' ',
        'Once you press "Create" button, 51 blendshapes will be created. '
        'You can change ',
        'how they affect the shape of the head here: '
        'Object Data Properties > Shape Keys.',
        'If you change the topology, the blendshapes will be recreated. '
        'When you change ',
        'the shape of the head using pins in Pin Mode, and also when you '
        'change the scale ',
        'of the model, you\'ll be asked if you want to update '
        'the blendshapes, note that ',
        'the old blendshapes become useless once you make such changes.',
        ' ',
        'The blendshapes are fully compatible with the ARKit '
        'specifications, which can found ',
        'at Apple Developer portal.',
        ' ',
        'You can animate the blendshapes manually creating keyframes '
        'for each Shape Key.',
        ' ',
        'If you have LiveLinkFace (or similar) application, you can record '
        'the facial animation ',
        'using the iOS device with the True Depth sensor (iPhone X '
        'and newer), ',
        'export a CSV file and then import it here.',
        ' ',
        'To export the head with all its blendshapes and animation, '
        'you need to know ',
        'where you want to import this 3D model to. In most cases '
        'the Export button ',
        'presented here will work for Unreal Engine and Unity, it will '
        'pre-setup the Blender ',
        'export dialog for you. Your free to change the settings before '
        'saving the file if you need.'
    ]),
}

Warning = namedtuple('Warning', ['content_red', 'content_white'])
warnings = {
    FBConfig.fb_blendshapes_warning_idname: Warning([
        'Your model has FaceBuilder FACS blendshapes attached to it.',
        'Once you change the topology, the blendshapes will be recreated.',
        'All modifications added to the standard blendshapes, ',
        'as well as all custom blendshapes are going to be lost.',
        ' '
    ], [
        'If you have animated the model using old blendshapes, ',
        'the new ones will be linked to the same Action track,',
        'so you\'re not going to lose your animation.',
        'If you have deleted some of the standard FaceBuilder '
        'FACS blendshapes, ',
        'they\'re not going to be recreated again.',
        ' ',
        'We recommend saving a backup file before changing the topology.',
        ' '
    ]),
    FBConfig.fb_noblenshapes_until_expression_warning_idname: Warning([
        'Unfortunately, expressions extracted from photos ',
        'can\'t be mixed with FACS blendshapes. ',
        'You need a neutral expression in order to create FACS blendshapes.',
        ' '
    ], [
    ]),
}