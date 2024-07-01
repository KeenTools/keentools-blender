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

from typing import Tuple, Optional
import logging
import os
import inspect
import tempfile


__all__ = ['SHADOW_COPIES_DIRECTORY', 'RELATIVE_LIB_DIRECTORY',
           'ADDON_PARENT_DIRECTORY', 'pkt_installation_dir',
           'addon_installation_dir', 'MINIMUM_VERSION_REQUIRED',
           'is_python_supported',
           'os_name', 'download_core_path', 'download_addon_path',
           'set_mock_update_paths']


logger = logging.getLogger(__name__)
log_error = logger.error
log_output = logger.debug


MINIMUM_VERSION_REQUIRED: Tuple = (2024, 1, 1)  # 2024.1.1 (4/6)
_SUPPORTED_PYTHON_VERSIONS: Tuple = ((3, 7), (3, 9), (3, 10), (3, 11))

_this_file_path: str = inspect.getfile(inspect.currentframe())
SHADOW_COPIES_DIRECTORY: str = os.path.join(tempfile.gettempdir(),
                                            'pykeentools_shadow_copies')
RELATIVE_LIB_DIRECTORY: str = os.path.join('pykeentools_installation', 'pykeentools')
ADDON_PARENT_DIRECTORY: str = os.path.abspath(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.dirname(_this_file_path)))))

log_output(f'SHADOW_COPIES_DIRECTORY:\n{SHADOW_COPIES_DIRECTORY}')
log_output(f'RELATIVE_LIB_DIRECTORY:\n{RELATIVE_LIB_DIRECTORY}')
log_output(f'ADDON_PARENT_DIRECTORY:\n{ADDON_PARENT_DIRECTORY}')


def pkt_installation_dir() -> str:
    module_dir = os.path.dirname(_this_file_path)
    installation_dir = os.path.join(module_dir, 'pykeentools')
    path = os.path.abspath(installation_dir)
    log_output(f'pkt_installation_dir:\n{path}')
    return path


def addon_installation_dir() -> str:
    path = os.path.join(ADDON_PARENT_DIRECTORY, 'keentools')
    return path


def is_python_supported() -> bool:
    import sys
    ver = sys.version_info[0:3]
    for supported_ver in _SUPPORTED_PYTHON_VERSIONS:
        if ver[:len(supported_ver)] == supported_ver:
            return True
    return False


def os_name() -> str:
    from sys import platform
    if platform == 'win32':
        return 'windows'
    if platform == 'linux' or platform == 'linux2':
        return 'linux'
    if platform == 'darwin':
        return 'macos'


_mock_update_addon_path: Optional[str] = None
_mock_update_core_path: Optional[str] = None


def set_mock_update_paths(addon_path: Optional[str] = None,
                          core_path: Optional[str] = None) -> None:
    global _mock_update_addon_path, _mock_update_core_path
    _mock_update_addon_path = addon_path
    _mock_update_core_path = core_path


def download_core_path(version: Optional[Tuple] = None) -> str:
    global _mock_update_core_path
    if _mock_update_core_path is not None:
        return _mock_update_core_path

    if version is None:
        return 'https://downloads.keentools.io/latest-keentools-core-{}'.format(os_name())

    return 'https://downloads.keentools.io/keentools-core-{}-{}'.format(
        '_'.join([str(x) for x in version]), os_name())


def download_addon_path(version: Optional[Tuple] = None) -> str:
    global _mock_update_addon_path
    if _mock_update_addon_path is not None:
        return _mock_update_addon_path

    if version is None:
        return 'https://downloads.keentools.io/latest-keentools-for-blender'

    return 'https://downloads.keentools.io/keentools-{}-for-blender'.format(
        '_'.join([str(x) for x in version]))
