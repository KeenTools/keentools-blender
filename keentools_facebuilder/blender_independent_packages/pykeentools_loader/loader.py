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


import sys
import os
from .config import *
from .install import is_installed
__all__ = ['loaded', 'module']


def _do_pkt_shadow_copy():
    import tempfile
    import shutil

    shutil.rmtree(SHADOW_COPIES_DIRECTORY, ignore_errors=True)
    os.makedirs(SHADOW_COPIES_DIRECTORY, exist_ok=True)

    shadow_copy_base_dir = tempfile.mkdtemp(dir=SHADOW_COPIES_DIRECTORY)
    shadow_copy_dir = os.path.join(shadow_copy_base_dir, 'pykeentools')

    shutil.copytree(pkt_installation_dir(), shadow_copy_dir)

    return shadow_copy_dir


def _add_pykeentools_to_sys_path():
    if os_name() == 'windows':
        pkt_directory = _do_pkt_shadow_copy()
    else:
        pkt_directory = pkt_installation_dir()

    pkt_lib_directory = os.path.join(pkt_directory, RELATIVE_LIB_DIRECTORY)
    if pkt_lib_directory not in sys.path:
        sys.path.append(pkt_lib_directory)


def loaded():
    return 'pykeentools' in sys.modules


# TODO add custom exceptions with helpful error message
# TODO check loaded pykeentools version > MIN_VERSION
def module():
    """
    A function to load pykeentools library
    :raises ImportError
    :return: pykeentools module
    """
    if not loaded() and is_installed():
        _add_pykeentools_to_sys_path()

    import pykeentools
    return pykeentools
