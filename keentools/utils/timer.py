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
import bpy


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
        logger = logging.getLogger(__name__)
        self._stop(callback)
        bpy.app.timers.register(callback, persistent=persistent)
        logger.debug("REGISTER TIMER")
        self.set_active()

    def _stop(self, callback):
        logger = logging.getLogger(__name__)
        if bpy.app.timers.is_registered(callback):
            logger.debug("UNREGISTER TIMER")
            bpy.app.timers.unregister(callback)
        self.set_inactive()
