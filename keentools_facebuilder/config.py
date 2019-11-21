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
import bpy


_company = 'keentools'
_PT = 'FACEBUILDER_PT_'
_MT = 'FACEBUILDER_MT_'


class BuilderType:
    """ Types for Builder selection """
    NoneBuilder = -1
    FaceBuilder = 1
    BodyBuilder = 2


class Config:
    prefix = _company + '_fb'
    operators = _company + '_facebuilder'
    addon_name = __package__  # the same as module name
    addon_human_readable_name = 'FaceBuilder'
    addon_version = '1.5.6 (Beta)'
    addon_search = 'KeenTools'
    addon_global_var_name = prefix + '_settings'
    addon_full_name = 'Keentools FaceBuilder for Blender'
    fb_views_panel_label = 'Views'
    fb_camera_panel_label = 'Camera settings'
    fb_tab_category = addon_human_readable_name
    default_builder = BuilderType.FaceBuilder
    keentools_website_url = 'https://keentools.io'
    manual_install_url = keentools_website_url + '/manual-installation'
    pykeentools_license_url = 'https://link.keentools.io/eula'
    
    # Operators ids
    fb_select_head_callname = prefix + '_main_select_head'
    fb_select_head_idname = 'object.' + fb_select_head_callname
    fb_main_delete_head_callname = prefix + '_main_delete_head'
    fb_main_delete_head_idname = 'object.' + fb_main_delete_head_callname
    fb_main_select_camera_callname = prefix + '_main_select_camera'
    fb_main_select_camera_idname = 'object.' + fb_main_select_camera_callname

    fb_center_geo_callname = 'center_geo'
    fb_center_geo_idname = operators + '.' + fb_center_geo_callname

    fb_main_unmorph_callname = prefix + '_main_unmorph'
    fb_main_unmorph_idname = 'object.' + fb_main_unmorph_callname

    fb_remove_pins_callname = 'remove_pins'
    fb_remove_pins_idname = operators + '.' + fb_remove_pins_callname

    fb_main_wireframe_color_callname = prefix + '_main_wireframe_color'
    fb_main_wireframe_color_idname = 'object.' + \
                                     fb_main_wireframe_color_callname
    fb_main_filter_cameras_idname = 'object.' + prefix + \
                                    '_main_filter_cameras'
    fb_main_delete_camera_callname = prefix + '_main_delete_camera'
    fb_main_delete_camera_idname = 'object.' + fb_main_delete_camera_callname
    fb_main_add_camera_callname = prefix + '_main_add_camera'
    fb_main_add_camera_idname = 'object.' + fb_main_add_camera_callname
    fb_main_fix_size_callname = prefix + '_main_fix_size'
    fb_main_fix_size_idname = 'object.' + fb_main_fix_size_callname
    fb_main_set_sensor_width_callname = prefix + '_main_set_sensor_width'
    fb_main_set_sensor_width_idname = 'object.' + \
                                      fb_main_set_sensor_width_callname
    fb_main_sensor_width_window_callname = prefix + '_main_sensor_width_window'
    fb_main_sensor_width_window_idname = 'object.' + \
                                      fb_main_sensor_width_window_callname
    fb_main_focal_length_menu_exec_callname = prefix + '_main_set_focal_length'
    fb_main_focal_length_menu_exec_idname = \
        'object.' + fb_main_focal_length_menu_exec_callname

    fb_main_camera_fix_size_idname = 'object.' + prefix + \
                                     '_main_camera_fix_size'

    fb_proper_view_menu_exec_callname = 'proper_view_menu_exec'
    fb_proper_view_menu_exec_idname = \
        operators + '.' + fb_proper_view_menu_exec_callname

    fb_improper_view_menu_exec_callname = 'improper_view_menu_exec'
    fb_improper_view_menu_exec_idname = \
        operators + '.' + fb_improper_view_menu_exec_callname

    fb_view_to_frame_size_callname = 'view_to_frame_size'
    fb_view_to_frame_size_idname = \
        operators + '.' + fb_view_to_frame_size_callname

    fb_most_frequent_frame_size_callname = 'most_frequent_frame_size'
    fb_most_frequent_frame_size_idname = \
        operators + '.' + fb_most_frequent_frame_size_callname

    fb_render_size_to_frame_size_callname = 'render_size_to_frame_size'
    fb_render_size_to_frame_size_idname = \
        operators + '.' + fb_render_size_to_frame_size_callname

    fb_main_addon_settings_callname = prefix + '_main_addon_settings'
    fb_main_addon_settings_idname = 'object.' + fb_main_addon_settings_callname

    fb_bake_tex_callname = 'bake_tex'
    fb_bake_tex_idname = operators + '.' + fb_bake_tex_callname
    fb_show_tex_callname = 'show_tex'
    fb_show_tex_idname = operators + '.' + fb_show_tex_callname
    fb_show_solid_callname = 'show_solid'
    fb_show_solid_idname = operators + '.' + fb_show_solid_callname

    fb_main_default_sensor_callname = prefix + '_main_default_sensor'
    fb_main_default_sensor_idname = 'object.' + fb_main_default_sensor_callname
    fb_main_all_unknown_callname = prefix + '_main_all_unknown'
    fb_main_all_unknown_idname = 'object.' + fb_main_all_unknown_callname

    fb_multiple_filebrowser_callname = 'open_multiple_filebrowser'
    fb_multiple_filebrowser_idname = \
        operators + '.' + fb_multiple_filebrowser_callname
    fb_multiple_filebrowser_exec_callname = 'open_multiple_filebrowser_exec'
    fb_multiple_filebrowser_exec_idname = \
        operators + '.' + fb_multiple_filebrowser_exec_callname

    fb_single_filebrowser_callname = 'open_single_filebrowser'
    fb_single_filebrowser_idname = \
        operators + '.' + fb_single_filebrowser_callname
    fb_single_filebrowser_exec_callname = 'open_single_filebrowser_exec'
    fb_single_filebrowser_exec_idname = \
        operators + '.' + fb_single_filebrowser_exec_callname

    fb_pinmode_operator_callname = prefix + '_pinmode'
    fb_pinmode_operator_idname = 'object.' + fb_pinmode_operator_callname

    fb_movepin_operator_idname = 'object.' + prefix + '_move_pin'
    fb_movepin_operator_callname = prefix + '_move_pin'

    fb_actor_callname = 'actor'
    fb_actor_idname = operators + '.' + fb_actor_callname

    fb_camera_actor_operator_callname = prefix + '_camera_actor'
    fb_camera_actor_operator_idname = 'object.' + \
                                      fb_camera_actor_operator_callname
    fb_warning_operator_callname = prefix + '_addon_warning'
    fb_warning_operator_idname = 'wm.' + fb_warning_operator_callname

    fb_exif_selector_callname = 'exif_selector'
    fb_exif_selector_idname = operators + '.' + fb_exif_selector_callname

    fb_read_exif_callname = 'read_exif'
    fb_read_exif_idname = operators + '.' + fb_read_exif_callname

    fb_read_exif_menu_exec_callname = 'read_exif_menu_exec'
    fb_read_exif_menu_exec_idname = \
        operators + '.' + fb_read_exif_menu_exec_callname

    fb_tex_selector_callname = 'tex_selector'
    fb_tex_selector_idname = operators + '.' + fb_tex_selector_callname

    fb_exit_pinmode_callname = 'exit_pinmode'
    fb_exit_pinmode_idname = operators + '.' + fb_exit_pinmode_callname

    # Add Mesh commands
    fb_add_head_operator_callname = 'add_head'
    fb_add_head_operator_idname = operators + '.' \
                                  + fb_add_head_operator_callname
    fb_add_body_operator_callname = 'add_body'
    fb_add_body_operator_idname = operators + '.' \
                                  + fb_add_body_operator_callname

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

    # Help ids
    fb_help_camera_callname = 'help_camera'
    fb_help_camera_idname = operators + '.' + fb_help_camera_callname

    fb_help_views_callname = 'help_view'
    fb_help_views_idname = operators + '.' + fb_help_views_callname

    fb_help_exif_callname = 'help_exif'
    fb_help_exif_idname = operators + '.' + fb_help_exif_callname

    fb_help_model_callname = 'help_model'
    fb_help_model_idname = operators + '.' + fb_help_model_callname

    fb_help_pin_settings_callname = 'help_pin_settings'
    fb_help_pin_settings_idname = operators + '.' \
                                  + fb_help_pin_settings_callname

    fb_help_wireframe_settings_callname = 'help_wireframe_settings'
    fb_help_wireframe_settings_idname = \
        operators + '.' + fb_help_wireframe_settings_callname

    fb_help_texture_callname = 'help_texture'
    fb_help_texture_idname = operators + '.' + fb_help_texture_callname

    fb_open_url_callname = 'open_url'
    fb_open_url_idname = operators + '.' + fb_open_url_callname

    # Menu ids
    fb_fix_frame_size_menu_idname = _MT + '_fix_frame_size_menu'

    fb_proper_view_menu_idname = _MT + 'proper_view_menu'
    fb_improper_view_menu_idname = _MT + 'improper_view_menu'

    fb_focal_length_menu_idname = _MT + 'focal_length_menu'
    fb_sensor_width_menu_idname = _MT + 'sensor_width_menu'

    fb_read_exif_menu_idname = _MT + 'read_exif_menu'


    # Standard names
    tex_builder_filename = 'kt_facebuilder_texture'
    tex_builder_matname = 'kt_facebuilder_material'

    # Object Custom Properties
    # Tuples instead simple values are used to load custom properties
    # if they have different names (from old scenes by ex. or if they will be
    # renamed in future).
    # Only first value in tuple is used for new custom property creation.
    object_type_prop_name = (_company + '_type',)
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
    default_POINT_SENSITIVITY = 16.0
    default_FB_COLLECTION_NAME = 'FaceBuilderCol'

    unknown_mod_ver = -1

    # In Material
    image_node_layout_coord = (-300, 0)

    # Colors
    red_color = (1.0, 0.0, 0.0)
    red_scheme1 = (0.3, 0.0, 0.0)
    # red_scheme2 = (0.0, 0.2, 0.4)
    red_scheme2 = (0.0, 0.4, 0.7)
    green_color = (0.0, 1.0, 0.0)
    green_scheme1 = (0.0, 0.2, 0.0)
    green_scheme2 = (0.4, 0.0, 0.4)
    blue_color = (0.0, 0.0, 1.0)
    blue_scheme1 = (0.0, 0.0, 0.3)
    blue_scheme2 = (0.4, 0.75, 0.0)
    cyan_color = (0.0, 1.0, 1.0)
    cyan_scheme1 = (0.0, 0.3, 0.3)
    cyan_scheme2 = (0.4, 0.0, 0.0)
    magenta_color = (1.0, 0.0, 1.0)
    magenta_scheme1 = (0.3, 0.0, 0.3)
    magenta_scheme2 = (0.0, 0.55, 0.0)
    yellow_color = (1.0, 1.0, 0.0)
    yellow_scheme1 = (0.2, 0.2, 0.0)
    yellow_scheme2 = (0.0, 0.0, 0.4)
    black_color = (0.0, 0.0, 0.0)
    black_scheme1 = (0.2, 0.2, 0.2)
    black_scheme2 = (0.0, 0.0, 1.0)
    white_color = (1.0, 1.0, 1.0)
    white_scheme1 = (1.0, 1.0, 1.0)
    white_scheme2 = (0.0, 0.0, 0.4)

    default_scheme1 = (0.05, 0.05, 0.1)
    default_scheme2 = (0.0, 0.0, 1.0)

    pin_color = (1.0, 0.0, 0.0, 1.0)
    current_pin_color = (1.0, 0.0, 1.0, 1.0)
    surface_point_color = (0.0, 1.0, 1.0, 0.5)
    residual_color = (0.0, 1.0, 1.0, 0.5)


def get_main_settings():
    """ Main addon settings"""
    return getattr(bpy.context.scene, Config.addon_global_var_name)


def get_operators():
    return getattr(bpy.ops, Config.operators)


class ErrorType:
    """ Types for Builder selection """
    Unknown = -1
    CustomMessage = 0
    NoLicense = 1
    SceneDamaged = 2
    BackgroundsDiffer = 3
    IllegalIndex = 4
    CannotReconstruct = 5
    CannotCreateObject = 6
    PktProblem = 7
    AboutFrameSize = 8
