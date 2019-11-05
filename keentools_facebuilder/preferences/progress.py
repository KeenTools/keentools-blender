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
from threading import Lock

import keentools_facebuilder.blender_independent_packages.pykeentools_loader as pkt
from ..utils.other import FBTimer, force_ui_redraw


class FBUpdateProgressTimer(FBTimer):
    _UPDATE_INTERVAL = 0.5

    @classmethod
    def _timer_should_not_work(cls):
        return not cls.is_active() or \
               not InstallationProgress.get_state()['active']

    @classmethod
    def _check_progress(cls):
        logger = logging.getLogger(__name__)
        if cls._timer_should_not_work():
            logger.debug("STOP PROGRESS INACTIVE")
            cls.stop()
            force_ui_redraw("PREFERENCES")
            return None

        logger.debug("NEXT CALL UPDATE TIMER")
        force_ui_redraw("PREFERENCES")
        return cls._UPDATE_INTERVAL

    @classmethod
    def start(cls):
        cls._start(cls._check_progress, persistent=False)

    @classmethod
    def stop(cls):
        cls._stop(cls._check_progress)


class InstallationProgress:
    _state_mutex = Lock()

    state = {'active': False, 'progress': 0.0, 'status': None}

    @classmethod
    def get_state(cls):
        cls._state_mutex.acquire()
        try:
            return cls.state.copy()
        finally:
            cls._state_mutex.release()

    @classmethod
    def set_state(cls, state):
        cls._state_mutex.acquire()
        try:
            cls.state = state
        finally:
            cls._state_mutex.release()

    @classmethod
    def _update_progress(cls, value):
        cls._state_mutex.acquire()
        try:
            assert(value <= 1.0)
            assert(cls.state['active'])
            cls.state['progress'] = value
        finally:
            cls._state_mutex.release()

    @classmethod
    def _on_start_download(cls):
        cls._state_mutex.acquire()
        try:
            cls.state = {'active': True, 'progress': 0.0, 'status': None}
        finally:
            cls._state_mutex.release()

    @classmethod
    def _on_finish_download(cls, status):
        cls._state_mutex.acquire()
        try:
            cls.state = {'active': False, 'progress': 0.0, 'status': status}
        finally:
            cls._state_mutex.release()

    @classmethod
    def _check_another_download_active(cls):
        cls._state_mutex.acquire()
        try:
            if cls.state['active']:
                cls.state['status'] = 'Another process is downloading ' \
                                      'the library'
                return True
            return False
        finally:
            cls._state_mutex.release()

    @classmethod
    def _progress_callback(cls, value):
        cls._update_progress(value)

    @classmethod
    def _final_callback(cls):
        cls._on_finish_download(
            'Core library has been downloaded and installed successfully.')

    @classmethod
    def _error_callback(cls, err):
        cls._on_finish_download('Downloading error: {}'.format(str(err)))

    @classmethod
    def start_download(cls, install_type):
        logger = logging.getLogger(__name__)

        if cls._check_another_download_active():
            logger.error("OTHER FILE DOWNLOADING")
            return

        cls._on_start_download()
        FBUpdateProgressTimer.start()
        if install_type == 'nightly':
            logger.debug("START NIGHTLY CORE LIBRARY DOWNLOAD")
            pkt.install_from_download_async(
                nightly=True,
                progress_callback=cls._progress_callback,
                final_callback=cls._final_callback,
                error_callback=cls._error_callback)
        elif install_type == 'default':
            logger.debug("START DEFAULT CORE LIBRARY DOWNLOAD")
            pkt.install_from_download_async(
                version=pkt.MINIMUM_VERSION_REQUIRED,
                progress_callback=cls._progress_callback,
                final_callback=cls._final_callback,
                error_callback=cls._error_callback)

    @classmethod
    def start_zip_install(cls, filepath):
        logger = logging.getLogger(__name__)

        if cls._check_another_download_active():
            logger.error("OTHER FILE DOWNLOADING")
            return

        cls._on_start_download()
        logger.debug("START UNPACK CORE LIBRARY DOWNLOAD")
        try:
            pkt.install_from_file(filepath)
        except Exception as error:
            cls._on_finish_download(
                'Failed to install Core library from file. ' + str(error))
            logger.debug("UNPACK CORE ERROR" + str(error))
        else:
            cls._on_finish_download(
                'Core library has been installed successfully.')
            logger.debug("UNPACK CORE FINISH")
