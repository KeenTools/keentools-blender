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
_prefix = _company + '_fb'  # for FaceBuilder
_PT = 'FACEBUILDER_PT_'
_MT = 'FACEBUILDER_MT_'


class BuilderType:
    """ Types for Builder selection """
    NoneBuilder = -1
    FaceBuilder = 1
    BodyBuilder = 2


class Config:
    prefix = _prefix
    addon_name = __package__  # the same as module name
    addon_human_readable_name = 'FaceBuilder'
    addon_version = '1.5.5 (Beta)'
    addon_search = 'KeenTools'
    addon_global_var_name = _prefix + '_settings'
    addon_full_name = 'Keentools FaceBuilder for Blender'
    fb_views_panel_label = 'Views'
    fb_camera_panel_label = 'Camera parameters'
    fb_tab_category = addon_human_readable_name
    default_builder = BuilderType.FaceBuilder
    keentools_website_url = 'https://keentools.io'
    manual_install_url = keentools_website_url + '/manual-installation'
    pykeentools_license_url = 'https://link.keentools.io/eula'
    pykeentools_manual_download_url = 'https://www.keentools.io/nightly-builds'
    
    # Operators ids
    fb_main_operator_callname = _prefix + '_main_operator'
    fb_main_operator_idname = 'object.' + fb_main_operator_callname
    fb_main_select_head_callname = _prefix + '_main_select_head'
    fb_main_select_head_idname = 'object.' + fb_main_select_head_callname
    fb_main_delete_head_callname = _prefix + '_main_delete_head'
    fb_main_delete_head_idname = 'object.' + fb_main_delete_head_callname
    fb_main_select_camera_callname = _prefix + '_main_select_camera'
    fb_main_select_camera_idname = 'object.' + fb_main_select_camera_callname
    fb_main_center_geo_callname = _prefix + '_main_center_geo'
    fb_main_center_geo_idname = 'object.' + fb_main_center_geo_callname
    fb_main_unmorph_callname = _prefix + '_main_unmorph'
    fb_main_unmorph_idname = 'object.' + fb_main_unmorph_callname
    fb_main_remove_pins_callname = _prefix + '_main_remove_pins'
    fb_main_remove_pins_idname = 'object.' + fb_main_remove_pins_callname
    fb_main_wireframe_color_callname = _prefix + '_main_wireframe_color'
    fb_main_wireframe_color_idname = 'object.' + \
                                     fb_main_wireframe_color_callname
    fb_main_filter_cameras_idname = 'object.' + _prefix + \
                                    '_main_filter_cameras'
    fb_main_delete_camera_callname = _prefix + '_main_delete_camera'
    fb_main_delete_camera_idname = 'object.' + fb_main_delete_camera_callname
    fb_main_add_camera_callname = _prefix + '_main_add_camera'
    fb_main_add_camera_idname = 'object.' + fb_main_add_camera_callname
    fb_main_fix_size_callname = _prefix + '_main_fix_size'
    fb_main_fix_size_idname = 'object.' + fb_main_fix_size_callname
    fb_main_set_sensor_width_callname = _prefix + '_main_set_sensor_width'
    fb_main_set_sensor_width_idname = 'object.' + \
                                      fb_main_set_sensor_width_callname
    fb_main_set_focal_length_callname = _prefix + '_main_set_focal_length'
    fb_main_set_focal_length_idname = 'object.' + \
                                      fb_main_set_focal_length_callname

    fb_main_camera_fix_size_idname = 'object.' + _prefix + \
                                     '_main_camera_fix_size'
    fb_main_addon_settings_idname = 'object.' + _prefix + \
                                    '_main_addon_settings'
    fb_main_bake_tex_callname = _prefix + '_main_bake_tex'
    fb_main_bake_tex_idname = 'object.' + fb_main_bake_tex_callname
    fb_main_show_tex_callname = _prefix + '_main_show_tex'
    fb_main_show_tex_idname = 'object.' + fb_main_show_tex_callname
    fb_main_default_sensor_callname = _prefix + '_main_default_sensor'
    fb_main_default_sensor_idname = 'object.' + fb_main_default_sensor_callname
    fb_main_all_unknown_callname = _prefix + '_main_all_unknown'
    fb_main_all_unknown_idname = 'object.' + fb_main_all_unknown_callname

    fb_multiple_filebrowser_operator_idname = \
        _prefix + '_import.open_multiple_filebrowser'
    fb_single_filebrowser_operator_idname = \
        _prefix + '_import.open_single_filebrowser'
    fb_pinmode_operator_callname = _prefix + '_pinmode'
    fb_pinmode_operator_idname = 'object.' + fb_pinmode_operator_callname

    fb_movepin_operator_idname = 'object.' + _prefix + '_move_pin'
    fb_movepin_operator_callname = _prefix + '_move_pin'
    fb_actor_operator_callname = _prefix + '_actor'
    fb_actor_operator_idname = 'object.' + fb_actor_operator_callname
    fb_camera_actor_operator_callname = _prefix + '_camera_actor'
    fb_camera_actor_operator_idname = 'object.' + \
                                      fb_camera_actor_operator_callname
    fb_warning_operator_callname = _prefix + '_addon_warning'
    fb_warning_operator_idname = 'wm.' + fb_warning_operator_callname
    fb_tex_selector_operator_callname = _prefix + '_tex_selector'
    fb_tex_selector_operator_idname = 'wm.' + fb_tex_selector_operator_callname
    fb_add_head_operator_callname = _prefix + '_add_head'
    fb_add_head_operator_idname = 'mesh.' + fb_add_head_operator_callname
    fb_add_body_operator_callname = _prefix + '_add_body'
    fb_add_body_operator_idname = 'mesh.' + fb_add_body_operator_callname

    # Panels ids
    fb_header_panel_idname = _PT + _prefix + '_header_panel_id'
    fb_camera_panel_idname = _PT + _prefix + 'camera_panel_id'
    fb_views_panel_idname = _PT + _prefix + '_views_panel_id'
    fb_tb_panel_idname = _PT + _prefix + '_tb_panel_id'
    fb_colors_panel_idname = _PT + _prefix + '_colors_panel_id'
    fb_parts_panel_idname = _PT + _prefix + '_parts_panel_id'
    fb_settings_panel_idname = _PT + _prefix + '_settings_panel_id'

    # Menu ids
    fb_fix_frame_menu_idname = _MT + _prefix + '_fix_frame_menu_id'
    fb_fix_camera_frame_menu_idname = _MT + _prefix + \
                                      '_fix_camera_frame_menu_id'
    fb_focal_length_menu_idname = _MT + _prefix + '_focal_length_menu_id'
    fb_sensor_width_menu_idname = _MT + _prefix + '_sensor_width_menu_id'

    # Standard names
    tex_builder_filename = 'texbuilder_baked'
    tex_builder_matname = 'texbuilder_view_mat'

    # Object Custom Properties
    # Tuples instead simple values are used to load custom properties
    # if they have different names (from old scenes by ex. or if they will be
    # renamed in future).
    # Only first value in tuple is used for new custom property creation.
    object_type_prop_name = (_company + '_type',)
    version_prop_name = (_company + '_version',)
    fb_serial_prop_name = (_prefix + '_serial',)
    fb_images_prop_name = (_prefix + '_images',)
    fb_dir_prop_name = (_prefix + '_dir',)
    fb_camera_prop_name = (_prefix + '_camera',)
    fb_mod_ver_prop_name = (_prefix + '_mod_ver',)
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
