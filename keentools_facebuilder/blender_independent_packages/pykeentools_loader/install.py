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
import sys
from threading import Thread, Lock
from enum import Enum
import bpy

from .config import *


__all__ = ['is_installed', 'uninstall', 'installation_status',
           'install_from_download', 'install_from_download_async',
           'install_core_from_file', 'install_addon_from_file',
           'download_addon_zip_async', 'download_core_zip_async',
           'updates_downloaded', 'loaded', 'module',
           'remove_addon_zip', 'remove_core_zip',
           'install_downloaded_addon', 'install_downloaded_core']


_unpack_mutex = Lock()


class PartInstallation(Enum):
    CORE = 1
    ADDON = 2


def _is_installed_not_locked():
    return os.path.exists(pkt_installation_dir())


def _installation_path_exists():
    _unpack_mutex.acquire()
    try:
        return os.path.exists(
            os.path.join(pkt_installation_dir(),RELATIVE_LIB_DIRECTORY))
    finally:
        _unpack_mutex.release()


def _is_installed_impl():
    _unpack_mutex.acquire()
    try:
        return _is_installed_not_locked()
    finally:
        _unpack_mutex.release()


def _uninstall_not_locked(part_installation=PartInstallation.CORE):
    if part_installation == PartInstallation.CORE:
        if _is_installed_not_locked():
            import shutil
            shutil.rmtree(pkt_installation_dir(), ignore_errors=True)
    elif part_installation == PartInstallation.ADDON:
        if _is_installed_not_locked():
            import shutil
            addons_path = bpy.utils.user_resource('SCRIPTS', "addons")
            fb_path = os.path.join(addons_path, 'keentools_facebuilder')
            shutil.rmtree(fb_path, ignore_errors=True)


def uninstall():
    _unpack_mutex.acquire()
    try:
        _uninstall_not_locked()
        _reset_cached_installation_status()
    finally:
        _unpack_mutex.release()


def _install_from_stream(file_like_object, part_installation):
    _unpack_mutex.acquire()
    try:
        _uninstall_not_locked(part_installation)

        if part_installation == PartInstallation.CORE:
            target_path = pkt_installation_dir()
            os.makedirs(target_path, exist_ok=False)
        elif part_installation == PartInstallation.ADDON:
            target_path = bpy.utils.user_resource('SCRIPTS', "addons")

        import zipfile
        with zipfile.ZipFile(file_like_object) as archive:
            archive.extractall(target_path)
        _reset_cached_installation_status()
    except Exception:
        _uninstall_not_locked()
        raise
    finally:
        _unpack_mutex.release()


def _download_with_progress_callback(url, progress_callback,
                                     max_callback_updates_count):
    import requests
    import io
    response = requests.get(url, stream=True)
    if progress_callback is None:
        return io.BytesIO(response.content)

    length = response.headers.get('content-length')
    if length:
        length = int(length)
        chunk_size = max(8 * 1024, length // max_callback_updates_count)
    else:
        chunk_size = 1024 * 1024

    result = io.BytesIO()
    downloaded = 0
    it = 0

    for chunk in response.iter_content(chunk_size=chunk_size):
        result.write(chunk)
        downloaded += len(chunk)
        if length:
            progress_callback(downloaded / length)
        else:
            import math
            # use exponential CDF as fallback
            # will go from 0 to 1 as it goes from 0 to infinity
            exp_lambda = 0.2
            progress_callback(1.0 - math.exp(-exp_lambda * it))
        it += 1

    progress_callback(1.0)

    return result


def install_from_download(version=None, nightly=False, progress_callback=None,
                          final_callback=None, error_callback=None,
                          max_callback_updates_count=481):
    """
    :param max_callback_updates_count: max progress_callback calls count
    :param progress_callback: callable getting progress in float [0, 1]
    :param version: build to install. KeenTools version (1.5.4 for example) as string. None means latest version
    :param nightly: latest nightly build will be installed if True. version should be None in that case
    """
    try:
        url = download_core_path(version, nightly)
        with _download_with_progress_callback(url,
                progress_callback, max_callback_updates_count) as archive_data:
            _install_from_stream(archive_data, PartInstallation.CORE)
    except Exception as error:
        if error_callback is not None:
            error_callback(error)
    else:
        if final_callback is not None:
            final_callback()


def install_from_download_async(**kwargs):
    """
    The same as :func:`install_from_download`
    """
    t = Thread(target=install_from_download, kwargs=kwargs)
    t.start()


def install_core_from_file(path):
    """
    Install pykeentools from selected archive
    :param path: a path to a pykeentools bundle zip archive
    """
    with open(path, mode='rb') as file:
        _install_from_stream(file, PartInstallation.CORE)


def install_addon_from_file(path):
    with open(path, mode='rb') as file:
        _install_from_stream(file, PartInstallation.ADDON)


def install_from_file(path, part_installation):
    with open(path, mode='rb') as file:
        _install_from_stream(file, part_installation)


def _download_file_name(part_installation):
    file_name = 'keentools_'
    if part_installation == PartInstallation.CORE:
        file_name += 'core'
    elif part_installation == PartInstallation.ADDON:
        file_name += 'addon'
    file_name += '.zip'
    return file_name


def _download_zip(part_installation, version=None, nightly=False, final_callback=None):
    url = None
    if part_installation == PartInstallation.CORE:
        url = download_core_path(version, nightly)
    elif part_installation == PartInstallation.ADDON:
        url = download_addon_path(version, nightly)
    import requests
    r = requests.get(url)
    file_path = _download_file_path(part_installation)
    with open(file_path, 'wb') as code:
        code.write(r.content)
    if final_callback is not None:
        final_callback()


def download_addon_zip_async(**kwargs):
    kwargs['part_installation'] = PartInstallation.ADDON
    t = Thread(target=_download_zip, kwargs=kwargs)
    t.start()


def download_core_zip_async(**kwargs):
    kwargs['part_installation'] = PartInstallation.CORE
    t = Thread(target=_download_zip, kwargs=kwargs)
    t.start()


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


def _installation_status_impl():
    if not _is_installed_impl():
        return (False, 'NOT_INSTALLED')

    if not _installation_path_exists():
        return (False, 'INSTALLED_WRONG')

    if not _import_pykeentools():
        return (False, 'CANNOT_IMPORT')

    ver = _get_pykeentools_version()
    if ver is None:
        return (False, 'NO_VERSION')

    if ver < MINIMUM_VERSION_REQUIRED:
        return (False, 'VERSION_PROBLEM')

    return (True, 'PYKEENTOOLS_OK')


_CACHED_PYKEENTOOLS_INSTALLATION_STATUS = None


def _reset_cached_installation_status():
    global _CACHED_PYKEENTOOLS_INSTALLATION_STATUS
    _CACHED_PYKEENTOOLS_INSTALLATION_STATUS = None


def installation_status(force_recheck=False):
    if force_recheck:
        _reset_cached_installation_status()

    global _CACHED_PYKEENTOOLS_INSTALLATION_STATUS
    if _CACHED_PYKEENTOOLS_INSTALLATION_STATUS is None:
        _CACHED_PYKEENTOOLS_INSTALLATION_STATUS = _installation_status_impl()
    return _CACHED_PYKEENTOOLS_INSTALLATION_STATUS


def is_installed(force_recheck=False):
    return installation_status(force_recheck)[0]


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


def module():
    """
    A function to load pykeentools library
    :raises ImportError
    :return: pykeentools module
    """
    if not loaded() and _is_installed_impl():
        _add_pykeentools_to_sys_path()

    import pykeentools
    return pykeentools


def _download_file_path(part_installation):
    file_name = _download_file_name(part_installation)
    return os.path.join(module().utils.caches_dir(), file_name)


def updates_downloaded():
    return os.path.exists(_download_file_path(PartInstallation.CORE)) and \
           os.path.exists(_download_file_path(PartInstallation.ADDON))


def _remove_download(part_installation):
    os.remove(_download_file_path(part_installation))


def remove_addon_zip():
    _remove_download(PartInstallation.ADDON)


def remove_core_zip():
    _remove_download(PartInstallation.CORE)


def _install_download(part_installation, remove_zip=False):
    install_from_file(_download_file_path(part_installation), part_installation)
    if remove_zip:
        _remove_download(part_installation)


def install_downloaded_addon(remove_zip):
    _install_download(PartInstallation.ADDON, remove_zip)


def install_downloaded_core(remove_zip):
    _install_download(PartInstallation.CORE, remove_zip)
