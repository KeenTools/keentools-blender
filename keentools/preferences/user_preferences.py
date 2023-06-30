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

from typing import Optional, Dict, Any, Callable
from copy import deepcopy

from ..utils.kt_logging import KTLogger
from ..addon_config import Config
from ..blender_independent_packages.pykeentools_loader import (
    module as pkt_module, is_installed as pkt_is_installed)


_log = KTLogger(__name__)


class UserPreferences:
    _DICT_NAME: str = Config.user_preferences_dict_name
    _defaults: Dict = Config.default_user_preferences
    _str_defaults: Dict = {k: str(Config.default_user_preferences[k]['value'])
                           for k in Config.default_user_preferences.keys()}

    _cached_dict: Optional[Dict] = None
    _cache_enabled: bool = True

    type_float: str = 'float'
    type_string: str = 'string'
    type_int: str = 'int'
    type_bool: str = 'bool'
    type_color: str = 'color'

    @classmethod
    def clear_cache(cls) -> None:
        cls._cached_dict = None

    @classmethod
    def get_dict(cls) -> Dict:
        if cls._cache_enabled and cls._cached_dict is not None:
            return cls._cached_dict

        if pkt_is_installed():
            _dict = pkt_module().utils.load_settings(cls._DICT_NAME)
        else:
            _dict = deepcopy(cls._str_defaults)

        if cls._cache_enabled:
            cls._cached_dict = _dict
        return _dict

    @classmethod
    def print_dict(cls) -> None:
        d = pkt_module().utils.load_settings(cls._DICT_NAME)
        _log.output(f'UserPreferences:\n{d}')

    @classmethod
    def _get_value(cls, name: str, type_: str) -> Any:
        _dict = cls.get_dict()

        if name in _dict.keys():
            if type_ == cls.type_int:
                return int(_dict[name])
            elif type_ == cls.type_float:
                return float(_dict[name])
            elif type_ == cls.type_bool:
                return _dict[name] == 'True'
            elif type_ == cls.type_string:
                return _dict[name]
            elif type_ == cls.type_color:
                return eval(_dict[name])
        elif name in cls._defaults.keys():
            row = cls._defaults[name]
            cls.set_value(name, row['value'])
            return row['value']
        _log.error(f'UserPreferences problem: {name} {type_}')
        return None

    @classmethod
    def get_value_safe(cls, name: str, type_: str) -> Any:
        try:
            return cls._get_value(name, type_)
        except Exception as err:
            _log.error(f'UserPreferences Exception info:\n{str(err)}')
            cls.clear_cache()
            if name in cls._defaults.keys():
                row = cls._defaults[name]
                cls.set_value(name, row['value'])
                return row['value']
            else:
                _log.error(f'Property error: {name} {type_}')
                return None

    @classmethod
    def set_value(cls, name: str, value: str) -> None:
        _log.output(f'set_value: {name} {value}')
        _dict = cls.get_dict()
        _dict[name] = str(value)
        cls.save_dict(_dict)

    @classmethod
    def clear_dict(cls) -> None:
        try:
            pkt_module().utils.reset_settings(cls._DICT_NAME)
        except Exception as _:
            _log.error(f'clear_dict: {cls._DICT_NAME}')
        cls.clear_cache()

    @classmethod
    def save_dict(cls, dict_to_save: Dict) -> None:
        try:
            pkt_module().utils.save_settings(cls._DICT_NAME, dict_to_save)
        except Exception as _:
            _log.error(f'save_dict: {dict_to_save}')
        # cls.print_dict()  # Debug only call

    @classmethod
    def reset_parameter_to_default(cls, name):
        if name in cls._defaults.keys():
            row = cls._defaults[name]
            cls.set_value(name, row['value'])

    @classmethod
    def reset_all_to_defaults(cls):
        cls.clear_dict()
        for name in cls._defaults.keys():
            cls.set_value(name, cls._defaults[name]['value'])


class UpdaterPreferences(UserPreferences):
    _DICT_NAME = Config.updater_preferences_dict_name
    _defaults = Config.default_updater_preferences
    _str_defaults = {k: str(Config.default_updater_preferences[k]['value'])
                     for k in Config.default_updater_preferences.keys()}


def universal_direct_getter(name: str, type_: str) -> Callable:
    def _getter(_) -> Any:
        return UserPreferences.get_value_safe(name, type_)
    return _getter


def universal_direct_setter(name: str) -> Callable:
    def _setter(_, value: Any) -> Any:
        UserPreferences.set_value(name, value)
    return _setter


def universal_cached_getter(name: str, type_: str) -> Callable:
    def _getter(self):
        if name in self.keys():
            return self[name]
        else:
            return UserPreferences.get_value_safe(name, type_)
    return _getter


def universal_cached_setter(name: str) -> Callable:
    def _setter(self, value):
        self[name] = value
    return _setter
