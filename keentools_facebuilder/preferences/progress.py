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

import bpy
import keentools_facebuilder.blender_independent_packages.pykeentools_loader as pkt
from ..utils.other import FBTimer


rw_mutex = Lock()


def _force_ui_redraw(area_type="PREFERENCES"):
    for window in bpy.data.window_managers['WinMan'].windows:
        for area in window.screen.areas:
            if area.type == area_type:
                area.tag_redraw()


class FBUpdateProgressTimer(FBTimer):
    @classmethod
    def _timer_should_not_work(cls):
        rw_mutex.acquire()
        try:
            return not cls.is_active() or not InstallationProgress.is_active()
        except Exception as error:
            raise error
        finally:
            rw_mutex.release()

    @classmethod
    def check_progress(cls):
        logger = logging.getLogger(__name__)
        if cls._timer_should_not_work():
            logger.debug("STOP PROGRESS INACTIVE")
            cls.stop()
            _force_ui_redraw()
            return None

        logger.debug("NEXT CALL UPDATE TIMER")
        # This updates download progress value in preferences UI
        _force_ui_redraw()
        # Interval to next call
        return 0.5

    @classmethod
    def start(cls):
        cls._start(cls.check_progress, persistent=False)

    @classmethod
    def stop(cls):
        cls._stop(cls.check_progress)


class InstallationProgress:
    state = {'active': False, 'progress': 0.0, 'status':''}

    @classmethod
    def get_state(cls):
        return cls.state

    @classmethod
    def _get_state_prop(cls, name):
        return cls.state[name]

    @classmethod
    def _set_state_prop(cls, name, value):
        cls.state[name] = value

    @classmethod
    def get_progress(cls):
        return cls._get_state_prop('progress')

    @classmethod
    def set_progress(cls, value):
        val = value if value <= 1.0 else 1.0
        cls._set_state_prop('progress', val)

    @classmethod
    def is_active(cls):
        return cls._get_state_prop('active')

    @classmethod
    def set_active(cls, value=True):
        cls._set_state_prop('active', value)

    @classmethod
    def get_status(cls):
        return cls._get_state_prop('status')

    @classmethod
    def set_status(cls, value):
        cls._set_state_prop('status', value)

    @classmethod
    def reset(cls, msg=''):
        cls.state = {'active': False, 'progress': 0.0, 'status': msg}

    @classmethod
    def _progress_callback(cls, value):
        rw_mutex.acquire()
        try:
            cls.set_progress(value)
        except Exception as error:
            raise error
        finally:
            rw_mutex.release()

    @classmethod
    def _final_callback(cls):
        rw_mutex.acquire()
        try:
            cls.reset('Core library downloaded and installed.')
        except Exception as error:
            raise error
        finally:
            rw_mutex.release()

    @classmethod
    def _error_callback(cls, err):
        rw_mutex.acquire()
        try:
            cls.reset('Download error: {}'.format(str(err)))
        except Exception as error:
            raise error
        finally:
            rw_mutex.release()

    @classmethod
    def start_download(cls, install_type):
        logger = logging.getLogger(__name__)
        rw_mutex.acquire()
        try:
            if cls.is_active():
                logger.error("OTHER FILE DOWNLOADING")
                cls.set_status('Another process is loading the library')
                return

            if install_type == 'nightly':
                cls.set_active(True)
                FBUpdateProgressTimer.start()
                logger.debug("START NIGHTLY CORE LIBRARY DOWNLOAD")
                pkt.install_from_download_async(
                    nightly=True,
                    progress_callback=cls._progress_callback,
                    final_callback=cls._final_callback,
                    error_callback=cls._error_callback)
            elif install_type == 'default':
                cls.set_active(True)
                FBUpdateProgressTimer.start()
                logger.debug("START NIGHTLY CORE LIBRARY DOWNLOAD")
                pkt.install_from_download_async(
                    version=pkt.MINIMUM_VERSION_REQUIRED,
                    progress_callback=cls._progress_callback,
                    final_callback=cls._final_callback,
                    error_callback=cls._error_callback)
        except Exception as error:
            raise error
        finally:
            rw_mutex.release()


