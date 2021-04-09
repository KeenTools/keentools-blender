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

from ..config import Config
from ..blender_independent_packages.pykeentools_loader import (
    module as pkt_module,
    is_installed as pkt_is_installed)


class UserPrefDict:
    _DICT_NAME = Config.user_preferences_dict_name
    defaults = {
        'pin_size': {'value': 7.0, 'type': 'float'},
        'pin_sensitivity': {'value': 16.0, 'type': 'float'},
        'prevent_view_rotation': {'value': True, 'type': 'bool'},
    }

    @classmethod
    def get_dict(cls):
        _dict = pkt_module().utils.load_settings(cls._DICT_NAME)
        return _dict

    @classmethod
    def print_dict(cls):
        d = pkt_module().utils.load_settings(cls._DICT_NAME)
        print(d)

    @classmethod
    def get_value(cls, name, type='str'):
        _dict = cls.get_dict()

        if name in _dict.keys():
            if type == 'int':
                return int(_dict[name])
            elif type == 'float':
                return float(_dict[name])
            elif type == 'bool':
                return _dict[name] == 'True'
            elif type == 'str':
                return _dict[name]
        elif name in cls.defaults.keys():
            row = cls.defaults[name]
            cls.set_value(name, row['value'])
            return row['value']
        return None

    @classmethod
    def set_value(cls, name, value):
        _dict = cls.get_dict()
        _dict[name] = str(value)
        cls.save_dict(_dict)

    @classmethod
    def clear_dict(cls):
        pkt_module().utils.reset_settings(cls._DICT_NAME)

    @classmethod
    def save_dict(cls, dict_to_save):
        pkt_module().utils.save_settings(cls._DICT_NAME, dict_to_save)
        cls.print_dict()

    @classmethod
    def reset_parameter_to_default(cls, name):
        if name in cls.defaults.keys():
            row = cls.defaults[name]
            cls.set_value(name, row['value'])

    @classmethod
    def reset_all_to_defaults(cls):
        cls.clear_dict()
        for name in cls.defaults.keys():
            cls.set_value(name, cls.defaults[name]['value'])
