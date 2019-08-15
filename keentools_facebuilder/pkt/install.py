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


import pkt.config
import os

__all__ = ['is_installed', 'install_from_download', 'uninstall', 'install_from_file']


def is_installed():
    return os.path.exists(pkt.config.pkt_installation_dir())


def uninstall():
    if is_installed():
        import shutil
        shutil.rmtree(pkt.config.pkt_installation_dir(), ignore_errors=True)


def _install_from_stream(file_like_object):
    uninstall()

    try:
        target_path = pkt.config.pkt_installation_dir()
        os.makedirs(target_path, exist_ok=False)

        import zipfile
        with zipfile.ZipFile(file_like_object) as archive:
            archive.extractall(target_path)
    except Exception:
        uninstall()
        raise


def install_from_download(version=None, nightly=False):
    """
    :param version: build to install. KeenTools version (1.5.4 for example) as string. None means latest version
    :param nightly: latest nightly build will be installed if True. version should be None in that case
    """
    import urllib.request
    import io
    url = pkt.config.download_path(version, nightly)
    with io.BytesIO(urllib.request.urlopen(url).read()) as archive_data:
        _install_from_stream(archive_data)


def install_from_file(path):
    """
    Install pykeentools from selected archive
    :param path: a path to a pykeentools bundle zip archive
    """
    with open(path, mode='rb') as file:
        _install_from_stream(file)
