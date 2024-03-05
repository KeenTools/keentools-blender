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


import os
import inspect
import tempfile

import bpy


__all__ = ['SHADOW_COPIES_DIRECTORY', 'RELATIVE_LIB_DIRECTORY',
           'pkt_installation_dir', 'addon_installation_dir', 'MINIMUM_VERSION_REQUIRED',
           'is_python_supported',
           'os_name', 'download_core_path', 'download_addon_path',
           'set_mock_update_paths']


SHADOW_COPIES_DIRECTORY = os.path.join(tempfile.gettempdir(),
                                       'pykeentools_shadow_copies')


RELATIVE_LIB_DIRECTORY = os.path.join('pykeentools_installation', 'pykeentools')


def pkt_installation_dir():
    module_path = inspect.getfile(inspect.currentframe())
    module_dir = os.path.dirname(module_path)
    installation_dir = os.path.join(module_dir, 'pykeentools')
    return os.path.abspath(installation_dir)


def addon_installation_dir():
    addons_path = bpy.utils.user_resource('SCRIPTS', path='addons')
    return os.path.join(addons_path, 'keentools')


MINIMUM_VERSION_REQUIRED = (2024, 1, 0)  # 2024.1.0 (4/5)
_SUPPORTED_PYTHON_VERSIONS = ((3, 7), (3, 9), (3, 10), (3, 11))


def is_python_supported():
    import sys
    ver = sys.version_info[0:3]
    for supported_ver in _SUPPORTED_PYTHON_VERSIONS:
        if ver[:len(supported_ver)] == supported_ver:
            return True
    return False


def os_name():
    from sys import platform
    if platform == "win32":
        return 'windows'
    if platform == "linux" or platform == "linux2":
        return 'linux'
    if platform == "darwin":
        return 'macos'


_mock_update_addon_path = None
_mock_update_core_path = None


def set_mock_update_paths(addon_path=None, core_path=None):
    global _mock_update_addon_path, _mock_update_core_path
    _mock_update_addon_path = addon_path
    _mock_update_core_path = core_path


def download_core_path(version=None, nightly=False):
    global _mock_update_core_path
    if _mock_update_core_path is not None:
        return _mock_update_core_path
    if nightly:
        assert(version is None)
        return 'https://downloads.keentools.io/keentools-core-nightly-{}'.format(os_name())

    if version is None:
        return 'https://downloads.keentools.io/latest-keentools-core-{}'.format(os_name())

    return 'https://downloads.keentools.io/keentools-core-{}-{}'.format(
        '_'.join([str(x) for x in version]), os_name())


def download_addon_path(version=None, nightly=False):
    global _mock_update_addon_path
    if _mock_update_addon_path is not None:
        return _mock_update_addon_path
    if nightly:
        assert(version is None)
        return 'https://downloads.keentools.io/keentools-nightly-for-blender'

    if version is None:
        return 'https://downloads.keentools.io/latest-keentools-for-blender'

    return 'https://downloads.keentools.io/keentools-{}-for-blender'.format(
        '_'.join([str(x) for x in version]))
