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
import tempfile
import shutil
import logging
import subprocess
import re
from threading import Thread, Lock
from enum import Enum
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

import bpy

from .config import *


__all__ = ['is_installed', 'uninstall_core', 'installation_status',
           'install_from_download_async', 'install_core_from_file',
           'download_addon_zip_async', 'download_core_zip_async',
           'updates_downloaded', 'loaded', 'module',
           'remove_downloaded_zips', 'install_downloaded_zips']


_unpack_mutex = Lock()


class PartInstallation(Enum):
    CORE = 1
    ADDON = 2


def _is_core_installed_not_locked():
    return os.path.exists(pkt_installation_dir())


def _is_addon_installed_not_locked():
    return os.path.exists(addon_installation_dir())


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
        return _is_core_installed_not_locked()
    finally:
        _unpack_mutex.release()


def _uninstall_not_locked(part_installation=PartInstallation.CORE):
    if part_installation == PartInstallation.CORE:
        if _is_core_installed_not_locked():
            import shutil
            shutil.rmtree(pkt_installation_dir(), ignore_errors=True)
    elif part_installation == PartInstallation.ADDON:
        if _is_addon_installed_not_locked():
            import shutil
            shutil.rmtree(addon_installation_dir(), ignore_errors=True)


def uninstall_core():
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
            target_path = bpy.utils.user_resource('SCRIPTS', path='addons')

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
                                     max_callback_updates_count, timeout):
    import requests
    import io
    session = requests.Session()
    retry = Retry(connect=3, backoff_factor=0.2)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('https://', adapter)

    response = session.get(url, stream=True, timeout=timeout)
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


_MAX_CALLBACK_UPDATES_COUNT = 481


def install_from_download(version=None, nightly=False, progress_callback=None,
                          final_callback=None, error_callback=None,
                          max_callback_updates_count=_MAX_CALLBACK_UPDATES_COUNT):
    url = download_core_path(version, nightly)

    def install_process(data):
        _install_from_stream(data, PartInstallation.CORE)

    _download_and_process(url, install_process, progress_callback, final_callback,
                          error_callback, max_callback_updates_count, None)


def _download_zip(part_installation, timeout, version=None, nightly=False, progress_callback=None,
                  final_callback=None, error_callback=None,
                  max_callback_updates_count=_MAX_CALLBACK_UPDATES_COUNT):
    if part_installation == PartInstallation.CORE:
        url = download_core_path(version, nightly)
    else:
        url = download_addon_path(version, nightly)

    def write_process(data):
        file_path = _download_file_path(part_installation)
        with open(file_path, 'wb') as code:
            code.write(data.getbuffer())

    _download_and_process(url, write_process, progress_callback, final_callback,
                          error_callback, max_callback_updates_count, timeout)


def _download_and_process(url, process_callback, progress_callback=None,
                          final_callback=None, error_callback=None,
                          max_callback_updates_count=_MAX_CALLBACK_UPDATES_COUNT, timeout=None):
    """
    :param max_callback_updates_count: max progress_callback calls count
    :param progress_callback: callable getting progress in float [0, 1]
    :param version: build to install. KeenTools version (1.5.4 for example) as string. None means latest version
    :param nightly: latest nightly build will be installed if True. version should be None in that case
    """
    try:
        with _download_with_progress_callback(url, progress_callback,
                                              max_callback_updates_count, timeout) as archive_data:
            process_callback(archive_data)
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


def _install_from_file(path, part_installation):
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


def _remove_dir(dir):
    try:
        shutil.rmtree(dir, ignore_errors=True)
    except Exception as err:
        logger = logging.getLogger(__name__)
        logger.error('remove_dir: Cannot delete dir {}'.format(dir))
        logger.error('Exception info: {}'.format(str(err)))


def _get_all_pids_on_windows():
    assert os_name() == 'windows'
    try:
        output = subprocess.run(['tasklist', '/NH', '/FO', 'CSV'],
                                capture_output=True)
    except FileNotFoundError as err:
        logger = logging.getLogger(__name__)
        logger.error('_get_all_pids_on_windows error: {}'.format(str(err)))
        return None
    except Exception as err:
        logger = logging.getLogger(__name__)
        logger.error('_get_all_pids_on_windows Exception: {}'.format(str(err)))
        return None
    rows = re.split(b'\n', output.stdout)
    pids = []
    for row in rows:
        elems = re.split(b'","', row)
        try:
            pid = int(elems[1])
            pids.append(pid)
        except Exception:
            pass
    return pids


def _all_dirs_in_dir(dir):
    return [f for f in os.listdir(dir) if os.path.isdir(os.path.join(dir, f))]


def _remove_old_dirs(base_dir):
    dirs = _all_dirs_in_dir(base_dir)
    pids = _get_all_pids_on_windows()
    if pids is None:
        return
    for name in dirs:
        pid_str = name.split('_')[0]  # '_' is delimiter between pid and random
        full_path = os.path.join(base_dir, name)
        can_be_deleted = True
        try:
            pid = int(pid_str)
            can_be_deleted = pid not in pids
        except ValueError:
            pass
        if can_be_deleted:
            _remove_dir(full_path)


def _do_pkt_shadow_copy():
    logger = logging.getLogger(__name__)
    logger.debug('_do_pkt_shadow_copy start')
    os.makedirs(SHADOW_COPIES_DIRECTORY, exist_ok=True)
    _remove_old_dirs(SHADOW_COPIES_DIRECTORY)

    pid = os.getpid()
    shadow_copy_base_dir = tempfile.mkdtemp(prefix='{}_'.format(pid),
                                            dir=SHADOW_COPIES_DIRECTORY)
    shadow_copy_dir = os.path.join(shadow_copy_base_dir, 'pykeentools')
    shutil.copytree(pkt_installation_dir(), shadow_copy_dir)
    logger.debug('shadow_copy_dir: {}'.format(shadow_copy_dir))
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
    path = _download_file_path(part_installation)
    if os.path.exists(path):
        os.remove(path)


def remove_downloaded_zips():
    _remove_download(PartInstallation.ADDON)
    _remove_download(PartInstallation.CORE)


def _install_download(part_installation, remove_zip=False):
    _install_from_file(_download_file_path(part_installation), part_installation)
    if remove_zip:
        _remove_download(part_installation)


def install_downloaded_zips(remove_zip):
    _install_download(PartInstallation.ADDON, remove_zip)
    _install_download(PartInstallation.CORE, remove_zip)
