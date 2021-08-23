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
           'pkt_installation_dir', 'addon_installation_dir',
           'face_data_dir','MINIMUM_VERSION_REQUIRED',
           'is_python_supported',
           'os_name', 'download_core_path', 'download_addon_path']


SHADOW_COPIES_DIRECTORY = os.path.join(tempfile.gettempdir(),
                                       'pykeentools_shadow_copies')


RELATIVE_LIB_DIRECTORY = os.path.join('pykeentools_installation', 'pykeentools')


def pkt_installation_dir():
    module_path = inspect.getfile(inspect.currentframe())
    module_dir = os.path.dirname(module_path)
    installation_dir = os.path.join(module_dir, 'pykeentools')
    return os.path.abspath(installation_dir)


def addon_installation_dir():
    addons_path = bpy.utils.user_resource('SCRIPTS', "addons")
    return os.path.join(addons_path, 'keentools_facebuilder')


def face_data_dir():
    face_data_path = os.path.join(pkt_installation_dir(),
                                  'pykeentools_installation/data/face_data')
    return os.path.abspath(face_data_path)


MINIMUM_VERSION_REQUIRED = (2021, 3, 1)  # 2021.3.1
_SUPPORTED_PYTHON_VERSIONS = ((3, 7), (3, 9))


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


def download_core_path(version=None, nightly=False):
    if nightly:
        assert(version is None)
        return 'https://downloads.keentools.io/keentools-core-nightly-{}'.format(os_name())

    if version is None:
        return 'https://downloads.keentools.io/latest-keentools-core-{}'.format(os_name())

    return 'https://downloads.keentools.io/keentools-core-{}-{}'.format(
        '_'.join([str(x) for x in version]), os_name())


def download_addon_path(version=None, nightly=False):
    if nightly:
        assert(version is None)
        return 'https://downloads.keentools.io/keentools-facebuilder-nightly-for-blender'

    if version is None:
        return 'https://downloads.keentools.io/latest-keentools-facebuilder-for-blender'

    return 'https://downloads.keentools.io/keentools-facebuilder-{}-for-blender'.format(
        '_'.join([str(x) for x in version]))
