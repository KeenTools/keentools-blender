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
from .config import *

__all__ = ['is_installed', 'install_from_download',
           'uninstall', 'install_from_file']


def is_installed():
    return os.path.exists(pkt_installation_dir())


def uninstall():
    if is_installed():
        import shutil
        shutil.rmtree(pkt_installation_dir(), ignore_errors=True)


def _install_from_stream(file_like_object):
    uninstall()

    try:
        target_path = pkt_installation_dir()
        os.makedirs(target_path, exist_ok=False)

        import zipfile
        with zipfile.ZipFile(file_like_object) as archive:
            archive.extractall(target_path)
    except Exception:
        uninstall()
        raise


def _download_with_progress_callback(url, progress_callback, max_callback_updates_count):
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


def install_from_download(version=None, nightly=False, progress_callback=None, max_callback_updates_count=481):
    """
    :param max_callback_updates_count: max progress_callback calls count
    :param progress_callback: callable getting progress in float [0, 1]
    :param version: build to install. KeenTools version (1.5.4 for example) as string. None means latest version
    :param nightly: latest nightly build will be installed if True. version should be None in that case
    """
    url = download_path(version, nightly)
    with _download_with_progress_callback(url, progress_callback, max_callback_updates_count) as archive_data:
        _install_from_stream(archive_data)


def install_from_file(path):
    """
    Install pykeentools from selected archive
    :param path: a path to a pykeentools bundle zip archive
    """
    with open(path, mode='rb') as file:
        _install_from_stream(file)
