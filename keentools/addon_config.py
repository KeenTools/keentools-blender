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


class Config:
    # Version dependent
    addon_version = '2021.4.0'  # (5/5)
    supported_blender_versions = ((2, 80), (2, 81), (2, 82), (2, 83),
                                  (2, 90), (2, 91), (2, 92), (2, 93),
                                  (3, 0), (3, 1))
    minimal_blender_api = (2, 80, 60)

    prefix = _company + '_fb'
    operators = 'keentools'
    addon_name = __package__  # the same as module name
    addon_human_readable_name = 'KeenTools'

    user_preferences_dict_name = 'keentools_facebuilder_addon'
    updater_preferences_dict_name = 'keentools_updater'

    keentools_website_url = 'https://keentools.io'
    core_download_website_url = keentools_website_url + '/download/core'

    manual_install_url = keentools_website_url + '/manual-installation'
    pykeentools_license_url = 'https://link.keentools.io/eula'

    coloring_texture_name = 'ktWireframeTexture'

    kt_addon_settings_id = operators + '.addon_settings'
    kt_open_url_id = operators + '.open_url'
    kt_uninstall_core_id = operators + '.uninstall_core'

    # Object Custom Properties
    core_version_prop_name = _company + '_version'

    # Constants
    surf_pin_size_scale = 0.85
    text_scale_y = 0.75
    btn_scale_y = 1.2

    viewport_redraw_interval = 0.1

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
    wireframe_opacity = 0.45

    pin_color = (1.0, 0.0, 0.0, 1.0)
    current_pin_color = (1.0, 0.0, 1.0, 1.0)
    surface_point_color = (0.0, 1.0, 1.0, 0.5)
    residual_color = (0.0, 1.0, 1.0, 0.5)

    selected_rectangle_color = (0.871, 0.107, 0.001, 1.0)
    regular_rectangle_color = (0.024, 0.246, 0.905, 1.0)

    default_user_preferences = {
        'pin_size': {'value': 7.0, 'type': 'float'},
        'pin_sensitivity': {'value': 16.0, 'type': 'float'},
        'prevent_view_rotation': {'value': True, 'type': 'bool'},
        'wireframe_color': {'value': color_schemes['default'][0], 'type': 'color'},
        'wireframe_special_color': {'value': color_schemes['default'][1], 'type': 'color'},
        'wireframe_midline_color': {'value': midline_color, 'type': 'color'},
        'wireframe_opacity': {'value': wireframe_opacity, 'type': 'float'}
    }

    default_updater_preferences = {
        'latest_show_datetime_update_reminder': {'value': '', 'type': 'string'},
        'latest_update_skip_version': {'value': '', 'type': 'string'},
        'updater_state': {'value': 1, 'type': 'int'},
        'downloaded_version': {'value': '', 'type': 'string'},
        'latest_installation_skip_version': {'value': '', 'type': 'string'},
        'latest_show_datetime_installation_reminder': {'value': '', 'type': 'string'}
    }
    mock_update_for_testing_flag = False
    mock_update_version = (int(addon_version.partition('.')[0]), 6, 3)

    @classmethod
    def mock_update_for_testing(cls, value=True, ver=None):
        if ver is not None:
            cls.mock_update_version = ver
        cls.mock_update_for_testing_flag = value


def is_blender_supported():
    ver = bpy.app.version
    for supported_ver in Config.supported_blender_versions:
        if ver[:len(supported_ver)] == supported_ver:
            return True
    return False


def get_addon_preferences():
    return bpy.context.preferences.addons[Config.addon_name].preferences


def get_operator(operator_id_name):
    def _rgetattr(obj, attr, *args):
        import functools
        def _getattr(obj, attr):
            return getattr(obj, attr, *args)
        return functools.reduce(_getattr, [obj] + attr.split('.'))
    return _rgetattr(bpy.ops, operator_id_name)
