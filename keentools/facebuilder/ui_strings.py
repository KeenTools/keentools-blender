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
        'Add FaceBuilder Head to scene'
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
        'Export',
        'Export texture to a file'
    ),
    FBConfig.fb_multiple_filebrowser_exec_idname: Button(
        'Add more images',
        'New cameras will be created according to number of views'
    ),
    FBConfig.fb_multiple_filebrowser_idname: Button(
        'Open Images',
        'New cameras will be created according to number of views'
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
    FBConfig.fb_image_info_idname: Button(
        'Image info',
        'Show image properties based on file EXIF'
    ),
    FBConfig.fb_texture_bake_options_idname: Button(
        'Texture settings',
        'Source images, size and other texture settings'
    ),
    FBConfig.fb_reset_texture_resolution_idname: Button(
        'Reset',
        'Reset texture resolution to default values'
    ),
    FBConfig.fb_reset_advanced_settings_idname: Button(
        'Reset',
        'Reset advanced texture baking settings'
    ),
    FBConfig.fb_pickmode_idname: Button(
        'FaceBuilder Pick Face mode',
        'Modal Operator for Pick Face mode'
    ),
    FBConfig.fb_pickmode_starter_idname: Button(
        'FaceBuilder Pick Face mode starter',
        'Auto align mesh in current view'
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
        'Delete the head and related cameras from the scene'
    ),
    FBConfig.fb_select_camera_idname: Button(
        'Select Camera',
        'Go to this view to align mesh'
    ),
    FBConfig.fb_center_geo_idname: Button(
        'Reset Camera',
        'Reset camera position so the model is centered in the view'
    ),
    FBConfig.fb_unmorph_idname: Button(
        'Reset',
        'Reset shape deformations to the default state. '
        'It will remove all pins as well'
    ),
    FBConfig.fb_remove_pins_idname: Button(
        'Remove All Pins',
        'Remove all pins in current view'
    ),
    FBConfig.fb_wireframe_color_idname: Button(
        'Wireframe color',
        'Wireframe colour scheme'
    ),
    FBConfig.fb_filter_cameras_idname: Button(
        'Camera Filter',
        'Modify selection'
    ),
    FBConfig.fb_delete_camera_idname: Button(
        'Delete View',
        'Delete this view and related camera from the scene'
    ),
    FBConfig.fb_proper_view_menu_exec_idname: Button(
        'View operations',
        'Delete, rotate, change file path'
    ),
    FBConfig.fb_addon_setup_defaults_idname: Button(
        'Setup FaceBuilder defaults',
        'Open FaceBuilder Settings in Preferences window'
    ),
    FBConfig.fb_bake_tex_idname: Button(
        'Create Texture',
        'Create texture using reference views'
    ),
    FBConfig.fb_delete_texture_idname: Button(
        'Clear',
        'Delete texture from the scene'
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
        'Reset Expression',
        'Reset expression in current view'
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
        'Back to 3D',
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
        'FBX for games',
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
        'Reset',
        'Reset all to default values'
    ),
    FBConfig.fb_default_wireframe_settings_idname: Button(
        'Reset',
        'Reset all to default values'
    ),
    FBConfig.fb_select_current_head_idname: Button(
        'Current head',
        'Select current head in the scene'
    ),
    FBConfig.fb_select_current_camera_idname: Button(
        'Current view',
        'Current view. Press to go back to 3D'
    ),
    FBConfig.fb_reset_tone_exposure_idname: Button(
        'Reset',
        'Reset exposure to default value'
    ),
    FBConfig.fb_reset_tone_gamma_idname: Button(
        'Reset',
        'Reset gamma to default value'
    ),
    FBConfig.fb_reset_tone_mapping_idname: Button(
        'Reset',
        'Reset all to default values'
    ),
    FBConfig.fb_export_to_cc_idname: Button(
        'Character Creator',
        'Export to Character Creator. '
        'Requirements: Character Creator 4.0, Headshot 2.0'
    ),
    FBConfig.fb_rotate_head_forward_idname: Button(
        'Rotate right',
        '45 degree'
    ),
    FBConfig.fb_rotate_head_backward_idname: Button(
        'Rotate left',
        '45 degree'
    ),
    FBConfig.fb_reset_view_idname: Button(
        'Reset View',
        'Remove all pins and reset camera position'
    ),

    # Help buttons
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
    FBConfig.fb_help_export_idname: Button(
        'Export',
        'Show help information about Export panel'
    ),
}


HelpText = namedtuple('HelpText', ['width', 'message'])
_help_default_width = 500

help_texts = {
    FBConfig.fb_help_views_idname: HelpText(_help_default_width, [
        'Load reference images and align mesh to face. ',
        ' ',
        'In order to get an accurate 3D head in the end, use photos '
        'showing it ',
        'from different angles. New cameras will be created according '
        'to the number of views. ',
        'Camera focal length is calculated automatically using the EXIF data. ',
        'Turn \'Allow facial expressions\' on if there\'s a smile on the face, '
        'raised eyebrows, ',
        'open mouth or neck turn, i.e. if the facial expression is non-neutral. ',
        ' ',
        'Align mesh to image in each view. Use Auto Align first, '
        'then drag pins ',
        'on the mesh to match it with the image more accurately. ',
        'Create new pins where necessary, delete pins whose positions ',
        'are not immediately apparent.',
        ' ',
        'Use \'Options\' for manual adjustment of ',
        'Focal length: use 35mm equivalent values ',
        'Mesh rigidity: 0 - most flexible, 10 - most rigid'
    ]),
    FBConfig.fb_help_model_idname: HelpText(_help_default_width, [
        'Turn model parts on/off. ',
        ' ',
        'Instantly switch between 3 topology resolutions: high, '
        'mid or low poly. ',
        ' ',
        'Use \'Scale\' to change the absolute size of your model. ',
        'If you need your 3D head to be close to the real-life size, ',
        'set Scale to 0.1, which will make it around 22 cm high.'
    ]),
    FBConfig.fb_help_appearance_idname: HelpText(_help_default_width, [
        'Customise wireframe appearance, pins size and sensitivity. ',
        ' ',
        'Try different wireframe colour schemes and opacity if the mesh ',
        'fades with the background image. ',
        ' ',
        'Adjust size of the pins and their sensitivity. '
    ]),
    FBConfig.fb_help_texture_idname: HelpText(_help_default_width, [
        'Create texture blended from the views using the selected UV layout ',
        'and bake it onto the 3D model.',
        ' ',
        'Available UV maps:',
        # \u2013 - en dash
        '\u2013 Butterfly: reduced distortions, fewest possible number of seams',
        '\u2013 Legacy UV: even less distortions but contains more seams',
        '\u2013 Maxface: highest resolution possible',
        '\u2013 Spherical: improved version of the popular \'cylindrical\' UV',
        '\u2013 MH: MetaHuman compatible UV map.',
        ' ',
        'Customise texture settings by pressing the gear button next to it: ',
        'select and deselect source images and set output texture size.',
        ' ',
        'Advanced texture settings',
        '\u2013 Angle strictness: adjust the blending of colours between '
        'different cameras: ',
        '0 - average colour from all views, ',
        '100 - colour from 90 degree views only.',
        '\u2013 Expand edges: extend texture on the edges using '
        'neighbouring colour.',
        '\u2013 Equalise brightness and Equalise colour: get more consistent '
        'texture colour ',
        'in case of lighting issues in different photos.',
        '\u2013 Autofill: automatically fills the gaps with the generated texture.'
    ]),
    FBConfig.fb_help_blendshapes_idname: HelpText(_help_default_width, [
        'Сreate ARKit-compatible FACS blendshapes, load animation '
        'from a CSV file. ',
        ' ',
        'Press \'Create\' button to generate 51 ARKit-compatible blendshapes. ',
        'Go to Object Data Properties > Shape Keys to control and manually '
        'animate ',
        'your blendshapes.',
        ' ',
        'Upload pre-recorded blendshape animation as a CSV file. '
        'This can be created ',
        'with the Live Link Face app or similar.'
    ]),
    FBConfig.fb_help_export_idname: HelpText(_help_default_width, [
        'You can export your 3D head the usual way. Make sure it’s selected '
        'in the viewport ',
        'or Scene Collection, then go to File > Export, choose the file type '
        'and save the model. ',
        'We recommend using Wavefront (.obj) or Alembic (.abc) to prevent '
        'important data loss.',
        ' ',
        'Use \'FBX for games\' to save your 3D model along with all the '
        'blendshapes and animation. ',
        'It is pre-configured for importing into Unreal Engine and Unity, '
        'though you may select ',
        'different export options in the pop-up export window.',
        ' ',
        'Press \'Export to CC4\' (Windows only) to launch Reallusion '
        'Character Creator 4 and transfer ',
        'your head mesh and texture to CC4 in order to create look-alike '
        '3D characters. ',
        'This operation also requires the Headshot 2 plugin installed '
        'to your computer.'
    ]),
}


Warning = namedtuple('Warning', ['content_red', 'content_white'])
warnings = {
    FBConfig.fb_blendshapes_warning_idname: Warning([
        'Your model contains FACS blendshapes. Once you change',
        'topology, blendshapes will be recreated. All modifications',
        'added to blendshapes as well as custom blendshapes will be lost.',
        ' '
    ], [
        'New blendshapes will be linked to the same Action tracks,',
        'so no animation will be lost, if you had any. Previously',
        'deleted blendshapes will not be recreated.',
        ' ',
        'Back up your project before continuing.',
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
