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
    addon_version = '2.1.1'
    supported_blender_versions = ((2, 80), (2, 81), (2, 82), (2, 83), (2, 90))
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
    fb_select_head_callname = 'select_head'
    fb_select_head_idname = operators + '.' + fb_select_head_callname

    fb_delete_head_callname = 'delete_head'
    fb_delete_head_idname = operators + '.' + fb_delete_head_callname

    fb_select_camera_callname = 'select_camera'
    fb_select_camera_idname = operators + '.' + fb_select_camera_callname

    fb_center_geo_callname = 'center_geo'
    fb_center_geo_idname = operators + '.' + fb_center_geo_callname

    fb_unmorph_callname = 'unmorph'
    fb_unmorph_idname = operators + '.' + fb_unmorph_callname

    fb_remove_pins_callname = 'remove_pins'
    fb_remove_pins_idname = operators + '.' + fb_remove_pins_callname

    fb_wireframe_color_callname = 'wireframe_color'
    fb_wireframe_color_idname = operators + '.' + fb_wireframe_color_callname

    fb_filter_cameras_callname = 'filter_cameras'
    fb_filter_cameras_idname = operators + '.' + fb_filter_cameras_callname

    fb_delete_camera_callname = 'delete_camera'
    fb_delete_camera_idname = operators + '.' + fb_delete_camera_callname

    fb_proper_view_menu_exec_callname = 'proper_view_menu_exec'
    fb_proper_view_menu_exec_idname = \
        operators + '.' + fb_proper_view_menu_exec_callname

    fb_view_to_frame_size_callname = 'view_to_frame_size'
    fb_view_to_frame_size_idname = \
        operators + '.' + fb_view_to_frame_size_callname

    fb_addon_settings_callname = 'addon_settings'
    fb_addon_settings_idname = operators + '.' + fb_addon_settings_callname

    fb_delete_texture_callname = 'delete_texture'
    fb_delete_texture_idname = operators + '.' + fb_delete_texture_callname

    fb_rotate_image_cw_callname = 'rotate_image_cw'
    fb_rotate_image_cw_idname = operators + '.' + fb_rotate_image_cw_callname

    fb_rotate_image_ccw_callname = 'rotate_image_ccw'
    fb_rotate_image_ccw_idname = operators + '.' + fb_rotate_image_ccw_callname

    fb_reset_image_rotation_callname = 'reset_image_rotation'
    fb_reset_image_rotation_idname = \
        operators + '.' + fb_reset_image_rotation_callname

    fb_reset_expression_callname = 'reset_expression'
    fb_reset_expression_idname = operators + '.' + fb_reset_expression_callname

    fb_bake_tex_callname = 'bake_tex'
    fb_bake_tex_idname = operators + '.' + fb_bake_tex_callname

    fb_show_tex_callname = 'show_tex'
    fb_show_tex_idname = operators + '.' + fb_show_tex_callname

    fb_show_solid_callname = 'show_solid'
    fb_show_solid_idname = operators + '.' + fb_show_solid_callname

    # Not in use
    fb_default_sensor_callname = 'default_sensor'
    fb_default_sensor_idname = operators + '.' + fb_default_sensor_callname
    # Not in use

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

    fb_texture_file_export_callname = 'texture_file_export'
    fb_texture_file_export_idname = \
        operators + '.' + fb_texture_file_export_callname

    fb_pinmode_callname = 'pinmode'
    fb_pinmode_idname = operators + '.' + fb_pinmode_callname

    fb_movepin_callname = 'movepin'
    fb_movepin_idname = operators + '.' + fb_movepin_callname

    fb_actor_callname = 'actor'
    fb_actor_idname = operators + '.' + fb_actor_callname

    fb_camera_actor_callname = 'camera_actor'
    fb_camera_actor_idname = operators + '.' + fb_camera_actor_callname

    fb_warning_callname = 'addon_warning'
    fb_warning_idname = operators + '.' + fb_warning_callname

    fb_exif_selector_callname = 'exif_selector'
    fb_exif_selector_idname = operators + '.' + fb_exif_selector_callname

    fb_read_exif_callname = 'read_exif'
    fb_read_exif_idname = operators + '.' + fb_read_exif_callname

    fb_read_exif_menu_exec_callname = 'read_exif_menu_exec'
    fb_read_exif_menu_exec_idname = \
        operators + '.' + fb_read_exif_menu_exec_callname

    fb_image_group_menu_exec_callname = 'image_group_menu_exec'
    fb_image_group_menu_exec_idname = \
        operators + '.' + fb_image_group_menu_exec_callname

    fb_camera_panel_menu_exec_callname = 'camera_panel_menu_exec'
    fb_camera_panel_menu_exec_idname = \
        operators + '.' + fb_camera_panel_menu_exec_callname

    fb_tex_selector_callname = 'tex_selector'
    fb_tex_selector_idname = operators + '.' + fb_tex_selector_callname

    fb_exit_pinmode_callname = 'exit_pinmode'
    fb_exit_pinmode_idname = operators + '.' + fb_exit_pinmode_callname

    # Add Mesh commands
    fb_add_head_operator_callname = 'add_head'
    fb_add_head_operator_idname = \
        operators + '.' + fb_add_head_operator_callname

    fb_add_body_operator_callname = 'add_body'
    fb_add_body_operator_idname = \
        operators + '.' + fb_add_body_operator_callname

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

    fb_remind_later_callname = 'remind_later'
    fb_remind_later_idname = operators + '.' + fb_remind_later_callname

    fb_skip_version_callname = 'skip_version'
    fb_skip_version_idname = operators + '.' + fb_skip_version_callname

    fb_uninstall_core_callname = 'uninstall_core'
    fb_uninstall_core_idname = operators + '.' + fb_uninstall_core_callname

    # Menu ids
    fb_proper_view_menu_idname = _MT + 'proper_view_menu'

    fb_read_exif_menu_idname = _MT + 'read_exif_menu'

    fb_image_group_menu_idname = _MT + 'image_group_menu'

    fb_camera_panel_menu_idname = _MT + 'camera_panel_menu'

    # Standard names
    tex_builder_filename = 'kt_facebuilder_texture'
    tex_builder_matname = 'kt_facebuilder_material'

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


def get_operators():
    return getattr(bpy.ops, Config.operators)


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
