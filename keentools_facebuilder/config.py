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
import math
import bpy


_company = 'keentools'
_PT = 'FACEBUILDER_PT_'
_MT = 'FACEBUILDER_MT_'


class Config:
    # Version dependent
    addon_version = '2021.1.0'
    supported_blender_versions = ((2, 80), (2, 81), (2, 82), (2, 83),
                                  (2, 90), (2.91))
    minimal_blender_api = (2, 80, 60)

    # Version independent
    prefix = _company + '_fb'
    operators = _company + '_facebuilder'
    addon_name = __package__  # the same as module name
    addon_human_readable_name = 'FaceBuilder'

    default_fb_object_name = 'FaceBuilderHead'
    default_fb_mesh_name = 'FaceBuilderHead_mesh'
    default_fb_collection_name = 'FaceBuilderCol'
    default_fb_camera_data_name = 'fbCamData'
    default_fb_camera_name = 'fbCamera'

    addon_search = 'KeenTools'
    addon_global_var_name = prefix + '_settings'
    addon_full_name = 'Keentools FaceBuilder for Blender'
    fb_views_panel_label = 'Views'
    fb_camera_panel_label = 'Camera'
    fb_tab_category = addon_human_readable_name
    keentools_website_url = 'https://keentools.io'
    core_download_website_url = keentools_website_url + '/download/core'

    manual_install_url = keentools_website_url + '/manual-installation'
    pykeentools_license_url = 'https://link.keentools.io/eula'
    license_purchase_url = 'https://link.keentools.io/fb-lc-fbbmld?utm_source=fbb-missing-license-dialog'
    coloring_texture_name = 'ktWireframeTexture'
    
    # Operators ids
    fb_select_head_idname = operators + '.' + 'select_head'

    fb_delete_head_idname = operators + '.' + 'delete_head'

    fb_select_camera_idname = operators + '.' + 'select_camera'

    fb_center_geo_idname = operators + '.' + 'center_geo'

    fb_unmorph_idname = operators + '.' + 'unmorph'

    fb_remove_pins_idname = operators + '.' + 'remove_pins'

    fb_wireframe_color_idname = operators + '.' + 'wireframe_color'

    fb_filter_cameras_idname = operators + '.' + 'filter_cameras'

    fb_delete_camera_idname = operators + '.' + 'delete_camera'

    fb_proper_view_menu_exec_idname = operators + '.' + 'proper_view_menu_exec'

    fb_view_to_frame_size_idname = operators + '.' + 'view_to_frame_size'

    fb_addon_settings_idname = operators + '.' + 'addon_settings'

    fb_delete_texture_idname = operators + '.' + 'delete_texture'

    fb_rotate_image_cw_idname = operators + '.' + 'rotate_image_cw'

    fb_rotate_image_ccw_idname = operators + '.' + 'rotate_image_ccw'

    fb_reset_image_rotation_idname = operators + '.' + 'reset_image_rotation'

    fb_reset_expression_idname = operators + '.' + 'reset_expression'

    fb_bake_tex_idname = operators + '.' + 'bake_tex'

    fb_show_tex_idname = operators + '.' + 'show_tex'

    fb_show_solid_idname = operators + '.' + 'show_solid'

    # Not in use
    fb_default_sensor_idname = operators + '.' + 'default_sensor'
    # Not in use

    fb_multiple_filebrowser_idname = operators + '.' + 'open_multiple_filebrowser'

    fb_multiple_filebrowser_exec_idname = operators + '.' + 'open_multiple_filebrowser_exec'

    fb_single_filebrowser_idname = operators + '.' + 'open_single_filebrowser'

    fb_single_filebrowser_exec_idname = operators + '.' + 'open_single_filebrowser_exec'

    fb_texture_file_export_idname = operators + '.' + 'texture_file_export'

    fb_animation_filebrowser_idname = operators + '.' + 'open_animation_filebrowser'

    fb_pinmode_idname = operators + '.' + 'pinmode'

    fb_movepin_idname = operators + '.' + 'movepin'

    fb_history_actor_idname = operators + '.' + 'history_actor'

    fb_camera_actor_idname = operators + '.' + 'camera_actor'

    fb_warning_idname = operators + '.' + 'addon_warning'

    fb_blendshapes_warning_idname = operators + '.' + 'blendshapes_warning'

    fb_exif_selector_idname = operators + '.' + 'exif_selector'

    fb_read_exif_idname = operators + '.' + 'read_exif'

    fb_read_exif_menu_exec_idname = operators + '.' + 'read_exif_menu_exec'

    fb_image_group_menu_exec_idname = operators + '.' + 'image_group_menu_exec'

    fb_camera_panel_menu_exec_idname = operators + '.' + 'camera_panel_menu_exec'

    fb_tex_selector_idname = operators + '.tex_selector'

    fb_exit_pinmode_idname = operators + '.exit_pinmode'

    fb_create_blendshapes_idname = operators + '.create_blendshapes'

    fb_delete_blendshapes_idname = operators + '.delete_blendshapes'

    fb_load_animation_from_csv_idname = operators + '.load_animation_from_csv'

    fb_create_example_animation_idname = operators + '.create_example_animation'

    fb_reset_blendshape_values_idname = operators + '.reset_blendshape_values'

    fb_clear_animation_idname = operators + '.clear_animation'

    fb_export_head_to_fbx_idname = operators + '.export_head_to_fbx'

    fb_update_blendshapes_idname = operators + '.update_blendshapes'

    fb_unhide_head_idname = operators + '.unhide_head'

    fb_reconstruct_head_idname = operators + '.reconstruct_head'

    # Add Mesh commands
    fb_add_head_operator_idname = operators + '.add_head'

    fb_add_body_operator_idname = operators + '.add_body'

    # Panel ids
    fb_header_panel_idname = _PT + 'header_panel'
    fb_camera_panel_idname = _PT + 'camera_panel'
    fb_update_panel_idname = _PT + 'update_panel'
    fb_views_panel_idname = _PT + 'views_panel'
    fb_exif_panel_idname = _PT + 'exif_panel'
    fb_texture_panel_idname = _PT + 'texture_panel'
    fb_colors_panel_idname = _PT + 'colors_panel'
    fb_model_panel_idname = _PT + 'model_panel'
    fb_pin_settings_panel_idname = _PT + 'pin_settings_panel'
    fb_blendshapes_panel_idname = _PT + 'blendshapes_panel'

    # Help ids
    fb_help_camera_idname = operators + '.' + 'help_camera'

    fb_help_views_idname = operators + '.' + 'help_view'

    fb_help_model_idname = operators + '.' + 'help_model'

    fb_help_pin_settings_idname = operators + '.' + 'help_pin_settings'

    fb_help_wireframe_settings_idname = operators + '.' + 'help_wireframe_settings'

    fb_help_texture_idname = operators + '.' + 'help_texture'

    fb_help_blendshapes_idname = operators + '.' + 'help_blendshapes'

    fb_open_url_idname = operators + '.' + 'open_url'

    fb_remind_later_idname = operators + '.' + 'remind_later'

    fb_skip_version_idname = operators + '.' + 'skip_version'

    fb_uninstall_core_idname = operators + '.' + 'uninstall_core'

    # Menu ids
    fb_proper_view_menu_idname = _MT + 'proper_view_menu'

    fb_read_exif_menu_idname = _MT + 'read_exif_menu'

    fb_image_group_menu_idname = _MT + 'image_group_menu'

    fb_camera_panel_menu_idname = _MT + 'camera_panel_menu'

    # Standard names
    tex_builder_filename = 'kt_facebuilder_texture'
    tex_builder_matname = 'kt_facebuilder_material'

    default_driver_name = 'FaceBuilderDriver'
    default_blendshapes_action_name = 'fbBlendShapesAction'
    example_animation_action_name = 'ExampleAnimAction'

    # Object Custom Properties
    # Tuples instead simple values are used to load custom properties
    # if they have different names (from old scenes by ex. or if they will be
    # renamed in future).
    # Only first value in tuple is used for new custom property creation.
    version_prop_name = (_company + '_version',)
    fb_serial_prop_name = (prefix + '_serial',)
    fb_images_prop_name = (prefix + '_images',)
    fb_dir_prop_name = (prefix + '_dir',)
    fb_camera_prop_name = (prefix + '_camera',)
    fb_mod_ver_prop_name = (prefix + '_mod_ver',)
    # Save / Reconstruct parameters
    reconstruct_focal_param = ('focal',)
    reconstruct_sensor_width_param = ('sensor_width',)
    reconstruct_sensor_height_param = ('sensor_height',)
    reconstruct_frame_width_param = ('frame_width', 'width')
    reconstruct_frame_height_param = ('frame_height', 'height')

    # Constants
    default_pin_size = 7.0
    surf_pin_size_scale = 0.85
    default_point_sensitivity = 16.0
    text_scale_y = 0.75

    viewport_redraw_interval = 0.1
    unknown_mod_ver = -1

    default_focal_length = 50.0
    default_sensor_width = 36.0
    default_sensor_height = 24.0
    default_frame_width = 1920
    default_frame_height = 1080
    default_camera_display_size = 0.75

    default_camera_rotation = (math.pi * 0.5, 0, 0)
    camera_x_step = 2.0
    camera_y_step = 5
    camera_z_step = 0.5

    # In Material
    image_node_layout_coord = (-300, 0)

    # Colors
    midline_color = (0.960784, 0.007843, 0.615686)
    color_schemes = {
        'red': ((0.3, 0.0, 0.0), (0.0, 0.4, 0.7)),
        'green': ((0.0, 0.2, 0.0), (0.4, 0.0, 0.4)),
        'blue': ((0.0, 0.0, 0.3), (0.4, 0.75, 0.0)),
        'cyan': ((0.0, 0.3, 0.3), (0.4, 0.0, 0.0)),
        'magenta': ((0.3, 0.0, 0.3), (0.0, 0.55, 0.0)),
        'yellow': ((0.2, 0.2, 0.0), (0.0, 0.0, 0.4)),
        'black': ((0.039, 0.04 , 0.039), (0.0, 0.0, 0.85098)),
        'white': ((1.0, 1.0, 1.0), (0.0, 0.0, 0.4)),
        'default': ((0.039, 0.04 , 0.039), (0.0, 0.0, 0.85098))
    }

    pin_color = (1.0, 0.0, 0.0, 1.0)
    current_pin_color = (1.0, 0.0, 1.0, 1.0)
    surface_point_color = (0.0, 1.0, 1.0, 0.5)
    residual_color = (0.0, 1.0, 1.0, 0.5)


def is_blender_supported():
    ver = bpy.app.version
    for supported_ver in Config.supported_blender_versions:
        if ver[:len(supported_ver)] == supported_ver:
            return True
    return False


def get_main_settings():
    return getattr(bpy.context.scene, Config.addon_global_var_name)


def get_operator(operator_id_name):
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
