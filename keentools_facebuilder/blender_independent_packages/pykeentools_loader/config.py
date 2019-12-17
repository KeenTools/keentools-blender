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
__all__ = ['SHADOW_COPIES_DIRECTORY', 'RELATIVE_LIB_DIRECTORY',
           'pkt_installation_dir', 'MINIMUM_VERSION_REQUIRED',
           'os_name', 'download_path']


SHADOW_COPIES_DIRECTORY = os.path.join(tempfile.gettempdir(),
                                       'pykeentools_shadow_copies')


RELATIVE_LIB_DIRECTORY = os.path.join('pykeentools', 'pykeentools')


def pkt_installation_dir():
    module_path = inspect.getfile(inspect.currentframe())
    module_dir = os.path.dirname(module_path)
    installation_dir = os.path.join(module_dir, 'pykeentools')
    return os.path.abspath(installation_dir)


MINIMUM_VERSION_REQUIRED = '1.5.7'


def os_name():
    from sys import platform
    if platform == "win32":
        return 'WIN'
    if platform == "linux" or platform == "linux2":
        return 'LINUX'
    if platform == "darwin":
        return 'OSX'


def download_path(version=None, nightly=False):
    if nightly:
        assert(version is None)
        version = 'LATEST_NIGHTLY'
    else:
        version = 'LATEST' if version is None else version.replace('.', '_')
    return 'https://downloads.keentools.io/{}_{}_PYKEENTOOLS'.format(
        version, os_name())
