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

import pytest
import keentools.blender_independent_packages.pykeentools_loader as pkt


def test_wrong_installations():
    with pytest.raises(FileNotFoundError):
        pkt.install_core_from_file('some/non/existing/file.zip')
    with pytest.raises(Exception):
        pkt.install_core_from_file(__file__)
    assert(not pkt.is_installed())


def test_uninstall():
    pkt.uninstall_core()
    assert(not pkt.is_installed())


def test_download_non_existing_version():
    with pytest.raises(Exception):
        pkt.install_from_download('1.0.1')


def test_non_loaded_uninstalled_load():
    if pkt.loaded():
        return
    pkt.uninstall_core()
    with pytest.raises(ImportError):
        pkt.module()


@pytest.mark.parametrize(
    'use_progress_callback', [(True,), (False,)])
def test_download_latest_nightly(use_progress_callback):
    try:
        if use_progress_callback:
            def testing_progress_callback(progress):
                assert (testing_progress_callback.last_progress <= progress <= 1)
                testing_progress_callback.last_progress = progress

            testing_progress_callback.last_progress = 0
        else:
            testing_progress_callback = None

        pkt.install_from_download(nightly=True, progress_callback=testing_progress_callback)

        if use_progress_callback:
            assert(testing_progress_callback.last_progress == 1.0)
    except Exception:
        # can fail with no network
        return
    assert(pkt.is_installed())
    pykeentools = pkt.module()
    assert(isinstance(pykeentools.__version__, str))
    pkt.uninstall_core()
