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
from typing import Any, Callable, Optional

from .kt_logging import KTLogger
from .bpy_common import bpy_timer_register, bpy_timer_unregister


_log: Any = KTLogger(__name__)
_stop_all_timers: bool = False


def stop_all_working_timers(value: bool = True) -> None:
    global _stop_all_timers
    _stop_all_timers = value


class KTTimer:
    def __init__(self):
        self._active: bool = False

    def check_stop_all_timers(self) -> bool:
        if _stop_all_timers:
            _log.output(f'{self.__class__.__name__} stopped by stop_all_timers')
        return _stop_all_timers

    def set_active(self, value: bool=True):
        self._active = value

    def set_inactive(self) -> None:
        self._active = False

    def is_active(self) -> bool:
        return self._active

    def _start(self, callback: Callable, persistent: bool=True) -> None:
        self._stop(callback)
        self.set_active()
        bpy_timer_register(callback, persistent=persistent)
        _log.output('REGISTER TIMER')

    def _stop(self, callback: Callable) -> None:
        if bpy_timer_unregister(callback):
            _log.output('UNREGISTER TIMER')
        self.set_inactive()


class KTStopShaderTimer(KTTimer):
    def __init__(self, get_settings_func: Callable, stop_func: Callable):
        super().__init__()
        self._uuid: str = ''
        self._stop_func: Callable = stop_func
        self._get_settings_func: Callable = get_settings_func

    def check_pinmode(self) -> Optional[float]:
        if self.check_stop_all_timers():
            self._stop_func()
            self.stop()
            return None

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

    def get_uuid(self) -> str:
        return self._uuid

    def start(self, uuid='') -> None:
        self._uuid = uuid
        self._start(self.check_pinmode, persistent=True)

    def stop(self) -> None:
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
