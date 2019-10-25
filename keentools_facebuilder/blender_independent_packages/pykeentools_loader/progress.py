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


def _force_ui_redraw(area_type="USER_PREFERENCES"):
    for window in bpy.data.window_managers['WinMan'].windows:
        for area in window.screen.areas:
            if area.type == area_type:
                area.tag_redraw()


def _callback(value):
    print("CALLBACK: {}".format(value))
    DownloadManager.set_progress(value)
    _force_ui_redraw()


def _final_callback():
    logger = logging.getLogger()
    logger.info("CORE LIBRARY LOADED")
    DownloadManager.set_active(False)
    _force_ui_redraw()


def _start_proc_stable():
    pkt.install_from_download(version=pkt.MINIMUM_VERSION_REQUIRED,
                              progress_callback=_callback,
                              final_callback=_final_callback)


def _start_proc_nightly():
    pkt.install_from_download(nightly=True,
                              progress_callback=_callback,
                              final_callback=_final_callback)


class DownloadManager:
    _progress = 0.0
    _active = False

    @classmethod
    def get_progress(cls):
        return cls._progress

    @classmethod
    def set_progress(cls, value):
        cls._progress = value

    @classmethod
    def is_active(cls):
        return cls._active

    @classmethod
    def set_active(cls, value):
        cls._active = value

    @classmethod
    def start_download(cls, proc):
        logger = logging.getLogger(__name__)
        if not cls.is_active():
            cls.set_active(True)
            logger.debug("START CORE LIBRARY DOWNLOAD")
            t = Thread(target=proc)
            t.start()
        else:
            logger.error("OTHER FILE DOWNLOADING")

    @classmethod
    def start_download_nightly(cls):
        cls.start_download(_start_proc_nightly)

    @classmethod
    def start_download_stable(cls):
        cls.start_download(_start_proc_stable)

    @classmethod
    def force_ui_redraw(cls):
        _force_ui_redraw()
