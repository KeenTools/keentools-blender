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

from .utils.kt_logging import KTLogger


_log = KTLogger(__name__)


_PT: str = 'FBUILDER_PT_'
_MT: str = 'FBUILDER_MT_'
prefix: str = 'keentools_fb'


class FBConfig:
    default_fb_object_name = 'FBHead'
    default_fb_mesh_name = 'FBHead_mesh'
    default_fb_collection_name = 'FaceBuilderCol'
    default_fb_camera_data_name = 'fbCamData'
    default_fb_camera_name = 'fbCamera'

    fb_tool_name = 'FaceBuilder'

    operators = 'keentools_fb'

    fb_license_purchase_url = 'https://link.keentools.io/fb-lc-fbbmld?utm_source=fbb-missing-license-dialog'
    coloring_texture_name = '.ktWireframeTexture'
    
    # Operators ids
    fb_select_head_idname = operators + '.select_head'
    fb_select_current_head_idname = operators + '.select_current_head'
    fb_delete_head_idname = operators + '.delete_head'
    fb_select_camera_idname = operators + '.select_camera'
    fb_select_current_camera_idname = operators + '.select_current_camera'
    fb_center_geo_idname = operators + '.center_geo'
    fb_unmorph_idname = operators + '.unmorph'
    fb_remove_pins_idname = operators + '.remove_pins'
    fb_wireframe_color_idname = operators + '.wireframe_color'
    fb_filter_cameras_idname = operators + '.filter_cameras'
    fb_delete_camera_idname = operators + '.delete_camera'
    fb_proper_view_menu_exec_idname = operators + '.proper_view_menu_exec'

    fb_addon_setup_defaults_idname = operators + '.addon_setup_defaults'
    fb_delete_texture_idname = operators + '.delete_texture'

    fb_rotate_image_cw_idname = operators + '.rotate_image_cw'
    fb_rotate_image_ccw_idname = operators + '.rotate_image_ccw'
    fb_reset_image_rotation_idname = operators + '.reset_image_rotation'

    fb_reset_expression_idname = operators + '.reset_expression'

    fb_bake_tex_idname = operators + '.bake_tex'
    fb_show_tex_idname = operators + '.show_tex'
    fb_show_solid_idname = operators + '.show_solid'

    fb_multiple_filebrowser_idname = operators + '.open_multiple_filebrowser'
    fb_multiple_filebrowser_exec_idname = operators + '.open_multiple_filebrowser_exec'
    fb_single_filebrowser_idname = operators + '.open_single_filebrowser'
    fb_single_filebrowser_exec_idname = operators + '.open_single_filebrowser_exec'

    fb_texture_file_export_idname = operators + '.texture_file_export'

    fb_animation_filebrowser_idname = operators + '.open_animation_filebrowser'

    fb_pinmode_idname = operators + '.pinmode'
    fb_movepin_idname = operators + '.movepin'
    fb_pickmode_idname = operators + '.pickmode'
    fb_pickmode_starter_idname = operators + '.pickmode_starter'
    fb_history_actor_idname = operators + '.history_actor'
    fb_camera_actor_idname = operators + '.camera_actor'

    fb_blendshapes_warning_idname = operators + '.blendshapes_warning'
    fb_noblenshapes_until_expression_warning_idname = operators + \
        '.no_blenshapes_until_expression_warning'

    fb_image_info_idname = operators + '.image_info'
    fb_texture_bake_options_idname = operators + '.texture_bake_options'
    fb_reset_texture_resolution_idname = operators + '.reset_texture_resolution'
    fb_reset_advanced_settings_idname = operators + '.reset_advanced_settings'

    fb_exit_pinmode_idname = operators + '.exit_pinmode'

    fb_create_blendshapes_idname = operators + '.create_blendshapes'
    fb_delete_blendshapes_idname = operators + '.delete_blendshapes'
    fb_load_animation_from_csv_idname = operators + '.load_animation_from_csv'
    fb_create_example_animation_idname = operators + '.create_example_animation'
    fb_reset_blendshape_values_idname = operators + '.reset_blendshape_values'
    fb_clear_animation_idname = operators + '.clear_animation'
    fb_update_blendshapes_idname = operators + '.update_blendshapes'
    fb_export_head_to_fbx_idname = operators + '.export_head_to_fbx'

    fb_rotate_head_forward_idname = operators + '.rotate_head_forward'
    fb_rotate_head_backward_idname = operators + '.rotate_head_backward'
    fb_reset_view_idname = operators + '.reset_view'

    fb_unhide_head_idname = operators + '.unhide_head'
    fb_reconstruct_head_idname = operators + '.reconstruct_head'

    fb_add_head_operator_idname = operators + '.add_head'

    fb_user_preferences_reset_all = operators + '.user_pref_reset_all'
    fb_user_preferences_get_colors = operators + '.user_pref_get_colors'

    fb_default_pin_settings_idname = operators + '.default_pin_settings'
    fb_default_wireframe_settings_idname = \
        operators + '.default_wireframe_settings'
    fb_reset_tone_exposure_idname = operators + '.reset_tone_exposure'
    fb_reset_tone_gamma_idname = operators + '.reset_tone_gamma'
    fb_reset_tone_mapping_idname = operators + '.reset_tone_mapping'

    # Integration
    fb_export_to_cc_idname = operators + '.export_to_cc'

    # Panel ids
    fb_header_panel_idname = _PT + 'header_panel'
    fb_views_panel_idname = _PT + 'views_panel'
    fb_options_panel_idname = _PT + 'options_panel'
    fb_model_panel_idname = _PT + 'model_panel'
    fb_appearance_panel_idname = _PT + 'appearance_panel'
    fb_texture_panel_idname = _PT + 'texture_panel'
    fb_blendshapes_panel_idname = _PT + 'blendshapes_panel'
    fb_export_panel_idname = _PT + 'export_panel'
    fb_support_panel_idname = _PT + 'support_panel'

    # Help ids
    fb_help_camera_idname = operators + '.help_camera'
    fb_help_views_idname = operators + '.help_view'
    fb_help_model_idname = operators + '.help_model'
    fb_help_appearance_idname = operators + '.help_appearance'
    fb_help_texture_idname = operators + '.help_texture'
    fb_help_blendshapes_idname = operators + '.help_blendshapes'
    fb_help_export_idname = operators + '.help_export'

    # Updater panels
    fb_update_panel_idname = _PT + 'update_panel'
    fb_download_notification_panel_idname = _PT + 'download_notification'
    fb_downloading_problem_panel_idname = _PT + 'downloading_problem'
    fb_updates_installation_panel_idname = _PT + 'updates_installation_panel'

    # Menu ids
    fb_proper_view_menu_idname = _MT + 'proper_view_menu'

    # Standard names
    tex_builder_filename_template = '{}_baked_tex'
    tex_builder_matname_template = '{}_preview_mat'

    default_driver_name = 'FaceBuilderDriver'
    default_blendshapes_action_name = 'fbBlendShapesAction'
    example_animation_action_name = 'ExampleAnimAction'

    neutral_expression_view_name = '0'
    empty_expression_view_name = ''

    # Object Custom Properties
    version_prop_name = 'keentools_version'
    fb_serial_prop_name = prefix + '_serial'
    fb_images_prop_name = prefix + '_images'
    fb_dir_prop_name = prefix + '_dir'
    fb_camera_prop_name = prefix + '_camera'

    # Save / Reconstruct parameters
    reconstruct_focal_param = 'focal'
    reconstruct_sensor_width_param = 'sensor_width'
    reconstruct_sensor_height_param = 'sensor_height'
    reconstruct_frame_width_param = 'frame_width'
    reconstruct_frame_height_param = 'frame_height'

    # Constants
    surf_pin_size_scale = 0.85

    viewport_redraw_interval = 0.1

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

    wireframe_offset_constant: float = 0.001

    next_head_step = (2.5, 0., 0.)
    face_selection_frame_width = 3.0

    show_markers_at_camera_corners = False
    recreate_vertex_groups = True

    # In Material
    image_node_layout_coord = (-300, 0)

    # Colors
    pin_color = (1.0, 0.0, 0.0, 1.0)
    current_pin_color = (1.0, 0.0, 1.0, 1.0)
    surface_point_color = (0.0, 1.0, 1.0, 0.5)
    residual_color = (0.0, 1.0, 1.0, 0.5)

    selected_rectangle_color = (0.871, 0.107, 0.001, 1.0)
    regular_rectangle_color = (0.024, 0.246, 0.905, 1.0)
