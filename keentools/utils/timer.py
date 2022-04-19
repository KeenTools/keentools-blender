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
    _active = False

    @classmethod
    def set_active(cls, value=True):
        cls._active = value

    @classmethod
    def set_inactive(cls):
        cls._active = False

    @classmethod
    def is_active(cls):
        return cls._active

    @classmethod
    def _start(cls, callback, persistent=True):
        logger = logging.getLogger(__name__)
        cls._stop(callback)
        bpy.app.timers.register(callback, persistent=persistent)
        logger.debug("REGISTER TIMER")
        cls.set_active()

    @classmethod
    def _stop(cls, callback):
        logger = logging.getLogger(__name__)
        if bpy.app.timers.is_registered(callback):
            logger.debug("UNREGISTER TIMER")
            bpy.app.timers.unregister(callback)
        cls.set_inactive()
