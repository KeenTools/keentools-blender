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

import bpy

_company = 'keentools'
_PT = 'GEOTRACKER_PT_'
_MT = 'GEOTRACKER_MT_'
prefix = _company + '_gt'


class GTConfig:
    operators = 'keentools_gt'
    gt_tool_name = 'GeoTracker'
    gt_tab_category = 'GeoTracker'
    gt_global_var_name = prefix + '_settings'

    # Properties
    viewport_state_prop_name = 'keentools_viewport_state'

    # Operators
    gt_create_geotracker_idname = operators + '.create_geotracker'
    gt_delete_geotracker_idname = operators + '.delete_geotracker'
    gt_actor_idname = operators + '.actor'
    gt_pinmode_idname = operators + '.pinmode'
    gt_movepin_idname = operators + '.movepin'
    gt_multiple_filebrowser_idname = operators + '.multiple_filebrowser'
    gt_choose_precalc_file_idname = operators + '.choose_precalc_file'
    gt_track_to_start_idname = operators + '.track_to_start_btn'
    gt_track_to_end_idname = operators + '.track_to_end_btn'
    gt_track_next_idname = operators + '.track_next_btn'
    gt_track_prev_idname = operators + '.track_prev_btn'
    gt_prev_keyframe_idname = operators + '.prev_keyframe_btn'
    gt_next_keyframe_idname = operators + '.next_keyframe_btn'
    gt_add_keyframe_idname = operators + '.add_keyframe_btn'
    gt_remove_keyframe_idname = operators + '.remove_keyframe_btn'
    gt_clear_all_tracking_idname = operators + '.clear_all_tracking_btn'
    gt_clear_tracking_forward_idname = operators + '.clear_tracking_forward_btn'
    gt_clear_tracking_backward_idname = operators + '.clear_tracking_backward_btn'
    gt_clear_tracking_between_idname = operators + '.clear_tracking_between_btn'
    gt_refine_idname = operators + '.refine_btn'
    gt_refine_all_idname = operators + '.refine_all_btn'
    gt_center_geo_idname = operators + '.center_geo_btn'
    gt_magic_keyframe_idname = operators + '.magic_keyframe_btn'
    gt_remove_pins_idname = operators + '.remove_pins_btn'
    gt_create_animated_empty_idname = operators + '.create_animated_empty_btn'
    gt_exit_pinmode_idname = operators + '.exit_pinmode_btn'
    gt_interrupt_modal_idname = operators + '.interrupt_modal'
    gt_stop_precalc_idname = operators + '.stop_precalc_btn'
    gt_set_key_idname = operators + '.set_key_btn'

    # Panel ids
    gt_geotrackers_panel_idname = _PT + 'geotrackers_panel'
    gt_input_panel_idname = _PT + 'input_panel'
    gt_analyze_panel_idname = _PT + 'analyze_panel'
    gt_camera_panel_idname = _PT + 'camera_panel'
    gt_tracking_panel_idname = _PT + 'tracking_panel'
    gt_colors_panel_idname = _PT + 'colors_panel'
    gt_animation_panel_idname = _PT + 'animation_panel'

    # Constants
    text_scale_y = 0.75
    default_precalc_filename = 'geotracker.precalc'
    viewport_redraw_interval = 0.15
    show_markers_at_camera_corners = True
    pin_size = 6.0
    surf_pin_size_scale = 1.5

    matrix_rtol = 1e-05
    matrix_atol = 1e-07

    # Colors
    pin_color = (1.0, 0.0, 0.0, 1.0)
    current_pin_color = (1.0, 0.0, 1.0, 1.0)
    surface_point_color = (0.0, 1.0, 1.0, 0.5)
    residual_color = (0.0, 1.0, 1.0, 0.5)
    timeline_keyframe_color = (0.0, 1.0, 0.0, 0.5)

    wireframe_color = (0.0, 1.0, 0.0)
    wireframe_opacity = 0.1

    serial_prop_name = prefix + '_serial'
    version_prop_name = prefix + '_version'

    prevent_view_rotation = True
    use_storage = True


def get_gt_settings():
    return getattr(bpy.context.scene, GTConfig.gt_global_var_name)
