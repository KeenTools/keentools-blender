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
from typing import List, Optional, Any, Callable

import bpy
from bpy.types import Area

from ..preferences.user_preferences import UserPreferences
from .points import KTScreenPins
from .coords import get_pixel_relative_size


class KTViewport:
    def __init__(self):
        self.profiling: bool = False
        # --- PROFILING ---
        if self.profiling:
            pr = cProfile.Profile()
            pr.disable()
        # --- PROFILING ---
        # Current View Pins draw
        self._points2d: Optional[Any] = None
        # Surface points draw
        self._points3d: Optional[Any] = None
        # Text output in Modal mode
        self._texter: Optional[Any] = None
        # Wireframe shader object
        self._wireframer: Optional[Any] = None
        # Update timer
        self._draw_update_timer_handler: Optional[Callable] = None
        # Residuals dashed lines
        self._residuals: Optional[Any] = None
        # Rectangles for Face picking
        self._rectangler: Optional[Any] = None
        # Timeline shader
        self._timeliner: Optional[Any] = None
        # Selection shader
        self._selector: Optional[Any] = None
        # Pins
        self._pins: Any = KTScreenPins()
        self._point_sensitivity: float = UserPreferences.get_value_safe(
            'pin_sensitivity', UserPreferences.type_float)
        self._pixel_size: float = 0.1  # Auto Calculated
        self._work_area: Optional[Area] = None

    def get_work_area(self) -> Optional[Area]:
        return self._work_area

    def set_work_area(self, area: Area) -> None:
        self._work_area = area

    def clear_work_area(self) -> None:
        self.set_work_area(None)

    def pins(self) -> Any:
        return self._pins

    def points2d(self) -> Any:
        return self._points2d

    def points3d(self) -> Any:
        return self._points3d

    def texter(self) -> Any:
        return self._texter

    def wireframer(self) -> Any:
        return self._wireframer

    def residuals(self) -> Any:
        return self._residuals

    def rectangler(self) -> Any:
        return self._rectangler

    def timeliner(self) -> Any:
        return self._timeliner

    def selector(self) -> Any:
        return self._selector

    def update_view_relative_pixel_size(self, area: Area) -> None:
        ps = get_pixel_relative_size(area)
        self._pixel_size = ps

    def tolerance_dist(self) -> float:  # distance * sensitivity
        return self._point_sensitivity * self._pixel_size

    def tolerance_dist2(self) -> float:  # squared distance
        return self.tolerance_dist()**2

    def in_pin_drag(self) -> bool:
        pins = self.pins()
        return pins.current_pin_num() >= 0

    def unregister_draw_update_timer(self) -> None:
        if self._draw_update_timer_handler is not None:
            bpy.context.window_manager.event_timer_remove(
                self._draw_update_timer_handler
            )
        self._draw_update_timer_handler = None

    def register_draw_update_timer(self, time_step: float) -> None:
        self.unregister_draw_update_timer()
        self._draw_update_timer_handler = bpy.context.window_manager.event_timer_add(
            time_step=time_step, window=bpy.context.window
        )

    def tag_redraw(self) -> None:
        area = self.get_work_area()
        if area:
            area.tag_redraw()

    def is_working(self) -> bool:
        wf = self.wireframer()
        if wf is None:
            return False
        return wf.is_working()

    def set_visible(self, state: bool) -> None:
        self.wireframer().set_visible(state)
        self.points2d().set_visible(state)
        self.points3d().set_visible(state)
        self.residuals().set_visible(state)

    def message_to_screen(self, msg: List, register: bool=False,
                          context: Optional[Any]=None) -> None:
        texter = self.texter()
        if register and context is not None:
            texter.register_handler(context)
        texter.set_message(msg)

    def revert_default_screen_message(self, unregister=False) -> None:
        texter = self.texter()
        texter.set_message(texter.get_default_text())
        if unregister:
            texter.unregister_handler()
