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
from .install import is_installed, installation_path_exists
__all__ = ['loaded', 'module', 'is_python_supported', 'installation_status']


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
    else:
        import importlib
        importlib.invalidate_caches()


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


def is_python_supported():
    ver = sys.version_info[0:3]
    for supported_ver in SUPPORTED_PYTHON_VERSIONS:
        if ver[:len(supported_ver)] == supported_ver:
            return True
    return False


def _import_pykeentools():
    try:
        pk = module()
        return True
    except ImportError:
        return False


def _get_pykeentools_version():
    try:
        pk = module()
        ver = pk.version
        return (ver.major, ver.minor, ver.patch)
    except AttributeError:
        return None


def installation_status():
    if not is_installed():
        return (False, 'NOT_INSTALLED')

    if not installation_path_exists():
        return (False, 'INSTALLED_WRONG')

    if not _import_pykeentools():
        return (False, 'CANNOT_IMPORT')

    ver = _get_pykeentools_version()
    if ver is None:
        return (False, 'NO_VERSION')

    if ver < MINIMUM_VERSION_REQUIRED:
        return (True, 'VERSION_PROBLEM')

    return (True, 'PYKEENTOOLS_OK')
