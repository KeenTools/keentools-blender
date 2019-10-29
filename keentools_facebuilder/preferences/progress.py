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

import logging
from threading import Thread

import bpy
import keentools_facebuilder.blender_independent_packages.pykeentools_loader as pkt
from ..utils.other import FBTimer


def _force_ui_redraw(area_type="PREFERENCES"):
    for window in bpy.data.window_managers['WinMan'].windows:
        for area in window.screen.areas:
            if area.type == area_type:
                area.tag_redraw()


class FBUpdateProgressTimer(FBTimer):
    @classmethod
    def check_progress(cls):
        logger = logging.getLogger(__name__)
        # print("STATUS: {} {}".format(cls.is_active(), InstallationProgress.is_active()))
        if not cls.is_active() or not InstallationProgress.is_active():
            # Timer works when shouldn't
            cls.stop()
            logger.debug("STOP PROGRESS INACTIVE")
            return None
        # Timer is active
        _force_ui_redraw()
        logger.debug("NEXT CALL UPDATE TIMER")
        # Interval to next call
        return 0.5

    @classmethod
    def start(cls):
        cls._start(cls.check_progress, persistent=False)

    @classmethod
    def stop(cls):
        cls._stop(cls.check_progress)


def _progress_callback(value):
    InstallationProgress.set_progress(value)


def _final_callback():
    FBUpdateProgressTimer.stop()
    InstallationProgress.reset()
    InstallationProgress.set_status('Core library downloaded and installed.')
    _force_ui_redraw()


def _error_callback(error):
    FBUpdateProgressTimer.stop()
    InstallationProgress.reset()
    InstallationProgress.set_status('Download error: {}'.format(str(error)))
    _force_ui_redraw()


class InstallationProgress:
    _progress = 0.0
    _active = False
    _status = None

    @classmethod
    def get_progress(cls):
        return cls._progress

    @classmethod
    def set_progress(cls, value):
        val = value if value <= 1.0 else 1.0
        cls._progress = val

    @classmethod
    def is_active(cls):
        return cls._active

    @classmethod
    def set_active(cls, value=True):
        cls._active = value

    @classmethod
    def get_status(cls):
        return cls._status

    @classmethod
    def set_status(cls, value):
        cls._status = value

    @classmethod
    def reset(cls):
        cls.set_progress(0.0)
        cls.set_active(False)
        cls.set_status(None)

    @classmethod
    def start_download(cls, install_type):
        logger = logging.getLogger(__name__)
        if cls.is_active():
            logger.error("OTHER FILE DOWNLOADING")
            cls.set_status('Another process is loading the library')
            return

        if install_type == 'nightly':
            cls.set_active(True)
            FBUpdateProgressTimer.start()
            logger.debug("START NIGHTLY CORE LIBRARY DOWNLOAD")
            pkt.install_from_download_async(nightly=True,
                progress_callback=_progress_callback,
                final_callback=_final_callback,
                error_callback=_error_callback)
        elif install_type == 'default':
            cls.set_active(True)
            FBUpdateProgressTimer.start()
            logger.debug("START NIGHTLY CORE LIBRARY DOWNLOAD")
            pkt.install_from_download_async(
                version=pkt.MINIMUM_VERSION_REQUIRED,
                progress_callback=_progress_callback,
                final_callback=_final_callback,
                error_callback=_error_callback)
