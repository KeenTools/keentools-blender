# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2019-2022 KeenTools

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

import cProfile
import bpy

from ..preferences.user_preferences import UserPreferences
from .points import KTScreenPins
from .coords import get_pixel_relative_size


class KTViewport:
    def __init__(self):
        self.profiling = False
        # --- PROFILING ---
        if self.profiling:
            pr = cProfile.Profile()
            pr.disable()
        # --- PROFILING ---
        # Current View Pins draw
        self._points2d = None
        # Surface points draw
        self._points3d = None
        # Text output in Modal mode
        self._texter = None
        # Wireframe shader object
        self._wireframer = None
        # Update timer
        self._draw_update_timer_handler = None
        # Residuals dashed lines
        self._residuals = None
        # Rectangles for Face picking
        self._rectangler = None
        # Timeline shader
        self._timeliner = None
        # Selection shader
        self._selector = None
        # Pins
        self._pins = KTScreenPins()
        self._point_sensitivity = UserPreferences.get_value_safe(
            'pin_sensitivity', UserPreferences.type_float)
        self._pixel_size = 0.1  # Auto Calculated
        self._work_area = None

    def get_work_area(self):
        return self._work_area

    def set_work_area(self, area):
        self._work_area = area

    def clear_work_area(self):
        self.set_work_area(None)

    def pins(self):
        return self._pins

    def points2d(self):
        return self._points2d

    def points3d(self):
        return self._points3d

    def texter(self):
        return self._texter

    def wireframer(self):
        return self._wireframer

    def residuals(self):
        return self._residuals

    def rectangler(self):
        return self._rectangler

    def timeliner(self):
        return self._timeliner

    def selector(self):
        return self._selector

    def update_view_relative_pixel_size(self, area):
        ps = get_pixel_relative_size(area)
        self._pixel_size = ps

    def tolerance_dist(self):  # distance * sensitivity
        return self._point_sensitivity * self._pixel_size

    def tolerance_dist2(self):  # squared distance
        return self.tolerance_dist()**2

    def in_pin_drag(self):
        pins = self.pins()
        return pins.current_pin_num() >= 0

    def unregister_draw_update_timer(self):
        if self._draw_update_timer_handler is not None:
            bpy.context.window_manager.event_timer_remove(
                self._draw_update_timer_handler
            )
        self._draw_update_timer_handler = None

    def register_draw_update_timer(self, time_step):
        self.unregister_draw_update_timer()
        self._draw_update_timer_handler = bpy.context.window_manager.event_timer_add(
            time_step=time_step, window=bpy.context.window
        )

    def tag_redraw(self):
        area = self.get_work_area()
        if area:
            area.tag_redraw()

    def is_working(self):
        wf = self.wireframer()
        if wf is None:
            return False
        return wf.is_working()
