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

import threading
from typing import Any

import bpy

from .kt_logging import KTLogger


_log: Any = KTLogger(__name__)


class KTTimer:
    def __init__(self):
        self._active = False

    def set_active(self, value=True):
        self._active = value

    def set_inactive(self):
        self._active = False

    def is_active(self):
        return self._active

    def _start(self, callback, persistent=True):
        self._stop(callback)
        bpy.app.timers.register(callback, persistent=persistent)
        _log.output('REGISTER TIMER')
        self.set_active()

    def _stop(self, callback):
        if bpy.app.timers.is_registered(callback):
            _log.output('UNREGISTER TIMER')
            bpy.app.timers.unregister(callback)
        self.set_inactive()


class KTStopShaderTimer(KTTimer):
    def __init__(self, get_settings_func, stop_func):
        super().__init__()
        self._uuid = ''
        self._stop_func = stop_func
        self._get_settings_func = get_settings_func

    def check_pinmode(self):
        settings = self._get_settings_func()
        if not self.is_active():
            # Timer works when shouldn't
            _log.output('STOP SHADER INACTIVE')
            return None
        # Timer is active
        if not settings.pinmode:
            # But we are not in pinmode
            _log.output('CALL STOP SHADERS')
            self._stop_func()
            self.stop()
            _log.output('STOP SHADER FORCE')
            return None
        else:
            if settings.pinmode_id != self.get_uuid():
                # pinmode id externally changed
                _log.output('CALL STOP SHADERS')
                self._stop_func()
                self.stop()
                _log.output('STOP SHADER FORCED BY PINMODE_ID')
                return None
        # Interval to next call
        return 1.0

    def get_uuid(self):
        return self._uuid

    def start(self, uuid=''):
        self._uuid = uuid
        self._start(self.check_pinmode, persistent=True)

    def stop(self):
        self._stop(self.check_pinmode)


class RepeatTimer(threading.Timer):
    def run(self):
        interval = self.interval
        _log.output('RepeatTimer start')
        while not self.finished.wait(interval):
            _log.output(f'RepeatTimer: {interval}')
            interval = self.function()
            if interval == None:
                _log.output('RepeatTimer out')
                break
