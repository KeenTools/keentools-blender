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


class BuilderType:
    """ Types for Builder selection """
    NoneBuilder = -1
    FaceBuilder = 0
    BodyBuilder = 1
    BothBuilder = 2


class config:
    addon_name = __package__  # the same as module name
    addon_version = '1.5.3 (Beta)'
    addon_search = 'KeenTools'
    addon_global_var_name = _prefix + '_settings'
    addon_full_name = 'Keentools Face Builder for Blender'
    fb_panel_label = 'Face Builder (Beta)'
    fb_tab_category = 'Face Builder'
    default_builder = BuilderType.FaceBuilder

    # Operators ids
    fb_main_operator_idname = 'object.' + _prefix + '_main_operator'
    fb_main_select_camera_idname = 'object.' + _prefix + '_main_select_camera'
    fb_main_center_geo_idname = 'object.' + _prefix + '_main_center_geo'
    fb_main_unmorph_idname = 'object.' + _prefix + '_main_unmorph'
    fb_main_remove_pins_idname = 'object.' + _prefix + '_main_remove_pins'
    fb_main_wireframe_color_idname = 'object.' + _prefix + \
                                     '_main_wireframe_color'
    fb_main_filter_cameras_idname = 'object.' + _prefix + \
                                    '_main_filter_cameras'
    fb_main_delete_camera_idname = 'object.' + _prefix + '_main_delete_camera'
    fb_main_add_camera_idname = 'object.' + _prefix + '_main_add_camera'
    fb_main_fix_size_idname = 'object.' + _prefix + '_main_fix_size'
    fb_main_camera_fix_size_idname = 'object.' + _prefix + \
                                     '_main_camera_fix_size'
    fb_main_addon_settings_idname = 'object.' + _prefix + \
                                    '_main_addon_settings'
    fb_main_bake_tex_idname = 'object.' + _prefix + '_main_bake_tex'
    fb_main_bake_tex_callname = _prefix + '_main_bake_tex'
    fb_main_show_tex_idname = 'object.' + _prefix + '_main_show_tex'
    fb_main_show_tex_callname = _prefix + '_main_show_tex'

    fb_filedialog_operator_idname = _prefix + '_import.open_filebrowser'
    fb_draw_operator_idname = 'object.' + _prefix + '_draw'
    fb_draw_operator_callname = _prefix + '_draw'
    fb_movepin_operator_idname = 'object.' + _prefix + '_move_pin'
    fb_movepin_operator_callname = _prefix + '_move_pin'
    fb_actor_operator_idname = 'object.' + _prefix + '_actor'
    fb_actor_operator_callname = _prefix + '_actor'
    fb_warning_operator_idname = 'wm.' + _prefix + '_addon_warning'
    fb_warning_operator_callname = _prefix + '_addon_warning'
    fb_add_head_operator_idname = 'mesh.' + _prefix + '_add_head'
    fb_add_head_operator_callname = _prefix + '_add_head'
    fb_add_body_operator_idname = 'mesh.' + _prefix + '_add_body'
    fb_add_body_operator_callname = _prefix + '_add_body'

    # Panels ids
    fb_panel_idname = 'OBJECT_PT_' + _prefix + '_panel_id'
    fb_tb_panel_idname = 'OBJECT_PT_' + _prefix + '_tb_panel_id'
    fb_colors_panel_idname = 'OBJECT_PT_' + _prefix + '_colors_panel_id'
    fb_parts_panel_idname = 'OBJECT_PT_' + _prefix + '_parts_panel_id'
    fb_settings_panel_idname = 'OBJECT_PT_' + _prefix + '_settings_panel_id'

    # Menu ids
    fb_fix_frame_menu_idname = 'OBJECT_MT_' + _prefix + '_fix_frame_menu_id'
    fb_fix_camera_frame_menu_idname = 'OBJECT_MT_' + _prefix + \
                                      '_fix_camera_frame_menu_id'

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
    fb_dir_prop_name =  (_prefix + '_dir',)
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
    return getattr(bpy.context.scene, config.addon_global_var_name)


class ErrorType:
    """ Types for Builder selection """
    Unknown = -1
    NoLicense = 0
    SceneDamaged = 1
    BackgroundsDiffer = 2
    IllegalIndex = 3
    CannotReconstruct = 4
    CannotCreate = 5
    CustomMessage = 6
    AboutFrameSize = 7
