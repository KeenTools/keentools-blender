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

from threading import Lock

from ..utils.kt_logging import KTLogger
from ..blender_independent_packages.pykeentools_loader import (
    install_from_download_async as pkt_install_from_download_async,
    install_core_from_file as pkt_install_core_from_file,
    MINIMUM_VERSION_REQUIRED as pkt_MINIMUM_VERSION_REQUIRED)
from ..utils.timer import KTTimer
from ..utils.ui_redraw import force_ui_redraw


_log = KTLogger(__name__)


class UpdateProgressTimer(KTTimer):
    def __init__(self):
        super().__init__()
        self._UPDATE_INTERVAL = 0.5
        self._redraw_view3d = False

    def _timer_should_not_work(self):
        return not self.is_active()

    def _check_progress(self):
        if self.check_stop_all_timers():
            return None

        if self._timer_should_not_work():
            _log.output('STOP PROGRESS INACTIVE')
            self.stop()
            force_ui_redraw('PREFERENCES')
            if self._redraw_view3d:
                force_ui_redraw('VIEW_3D')
            return None

        _log.output('NEXT CALL UPDATE TIMER')
        force_ui_redraw('PREFERENCES')
        if self._redraw_view3d:
            force_ui_redraw('VIEW_3D')
        return self._UPDATE_INTERVAL

    def start(self, redraw_view3d=False):
        self._redraw_view3d = redraw_view3d
        self._start(self._check_progress, persistent=False)

    def stop(self):
        self._stop(self._check_progress)


class KTUpdateProgressTimer:
    _timer = UpdateProgressTimer()

    @classmethod
    def start(cls, redraw_view3d=False):
        cls._timer.start(redraw_view3d=redraw_view3d)

    @classmethod
    def stop(cls):
        cls._timer.stop()


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
            KTUpdateProgressTimer.start()
        finally:
            cls._state_mutex.release()

    @classmethod
    def _on_finish_download(cls, status):
        cls._state_mutex.acquire()
        try:
            cls.state = {'active': False, 'progress': 0.0, 'status': status}
            KTUpdateProgressTimer.stop()
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
            'The core library has been downloaded and installed successfully.')

    @classmethod
    def _error_callback(cls, err):
        cls._on_finish_download('Downloading error: {}'.format(str(err)))

    @classmethod
    def start_download(cls):
        if cls._check_another_download_active():
            _log.error('OTHER FILE IS DOWNLOADING (1)')
            return

        cls._on_start_download()
        _log.output('START CORE LIBRARY DOWNLOAD')
        pkt_install_from_download_async(
            version=pkt_MINIMUM_VERSION_REQUIRED,
            progress_callback=cls._progress_callback,
            final_callback=cls._final_callback,
            error_callback=cls._error_callback)

    @classmethod
    def start_zip_install(cls, filepath):
        if cls._check_another_download_active():
            _log.error('OTHER FILE IS DOWNLOADING (2)')
            return

        cls._on_start_download()
        _log.info('START UNPACKING DOWNLOADED CORE LIBRARY')
        try:
            pkt_install_core_from_file(filepath)
        except Exception as err:
            cls._on_finish_download(
                f'Failed to install Core library from file. {str(err)}')
            _log.error(f'CORE UNPACK ERROR\n{str(err)}')
        else:
            cls._on_finish_download(
                'The core library has been installed successfully.')
            _log.info('CORE HAS BEEN UNPACKED')
