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
from typing import List, Optional, Any, Callable, Tuple

from bpy.types import Area

from ..utils.kt_logging import KTLogger
from ..addon_config import Config, ActionStatus, ProductType, get_operator, ErrorType
from ..preferences.user_preferences import UserPreferences
from .points import KTScreenPins
from .coords import get_pixel_relative_size, check_area_is_wrong
from ..utils.bpy_common import bpy_window, bpy_window_manager, bpy_background_mode


_log = KTLogger(__name__)


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
        self._prev_camera_state: Tuple = ()
        self._prev_area_state: Tuple = ()

    def product_type(self) -> int:
        return ProductType.UNDEFINED

    def get_all_shader_objects(self) -> List:
        return [self._texter,
                self._points3d,
                self._residuals,
                self._points2d,
                self._wireframer,
                self._rectangler]

    def load_all_shaders(self) -> bool:
        _log.green(f'{self.__class__.__name__}.load_all_shaders start')
        if bpy_background_mode():
            _log.red('load_all_shaders bpy_background_mode True end >>>')
            return True
        tmp_log = f'--- {self.__class__.__name__} Shaders ---'
        show_tmp_log = False
        _log.blue(tmp_log)
        try:
            for shader_object in self.get_all_shader_objects():
                item_type = f'* {shader_object.__class__.__name__}'
                tmp_log += '\n' + item_type + ' -- '

                _log.blue(item_type)
                res = shader_object.init_shaders()

                tmp_log += 'skipped' if res is None else f'{res}'
                if res is not None:
                    show_tmp_log = True
        except Exception as err:
            _log.error(f'{self.__class__.__name__} '
                       f'viewport shaders Exception:\n{tmp_log}\n---\n'
                       f'{str(err)}\n===')
            warn = get_operator(Config.kt_warning_idname)
            warn('INVOKE_DEFAULT', msg=ErrorType.ShaderProblem)
            return False

        _log.blue(f'--- End of {self.__class__.__name__} Shaders ---')
        if show_tmp_log:
            _log.info(tmp_log)
        _log.output(f'{self.__class__.__name__}.load_all_shaders end >>>')
        return True

    def get_work_area(self) -> Optional[Area]:
        return self._work_area

    def set_work_area(self, area: Area) -> bool:
        if check_area_is_wrong(area):
            self._work_area = None
            return False
        else:
            self._work_area = area
            return True

    def clear_work_area(self) -> None:
        self.set_work_area(area=None)

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
            bpy_window_manager().event_timer_remove(
                self._draw_update_timer_handler
            )
        self._draw_update_timer_handler = None

    def register_draw_update_timer(self, time_step: float) -> None:
        self.unregister_draw_update_timer()
        self._draw_update_timer_handler = bpy_window_manager().event_timer_add(
            time_step=time_step, window=bpy_window()
        )

    def tag_redraw(self) -> None:
        area = self.get_work_area()
        if area:
            area.tag_redraw()

    def check_handlers_registered(self) -> bool:
        for shader_object in self.get_all_shader_objects():
            if shader_object.shader_is_working():
                return True
        if self._draw_update_timer_handler is not None:
            return True
        return False

    def check_work_area_exists(self) -> bool:
        return not check_area_is_wrong(self.get_work_area())

    def viewport_is_working(self) -> bool:
        if not self.check_work_area_exists():
            return False
        texter = self.texter()
        if not texter:
            return False
        if not texter.shader_is_working():
            return False
        return True

    def message_to_screen(self, msg: List,
                          register_area: Optional[Area] = None) -> None:
        texter = self.texter()
        if register_area is not None:
            texter.register_handler(area=register_area)
        texter.set_message(msg)

    def revert_default_screen_message(self, unregister: bool = False) -> None:
        texter = self.texter()
        texter.set_message(texter.get_default_text())
        if unregister:
            texter.unregister_handler()

    def check_camera_state_changed(self, rv3d: Any, reset: bool = False) -> bool:
        if not rv3d or reset:
            self._prev_camera_state = ()
            return False
        camera_state = (rv3d.view_camera_zoom, *rv3d.view_camera_offset)
        if camera_state != self._prev_camera_state:
            self._prev_camera_state = camera_state
            return True
        return False

    def check_area_state_changed(self, area: Area, reset: bool = False) -> bool:
        if not area or reset:
            self._prev_area_state = ()
            return False
        area_state = (area.x, area.y, area.width, area.height)
        if area_state != self._prev_area_state:
            self._prev_area_state = area_state
            return True
        return False

    def register_handlers(self, *, area: Any) -> bool:
        _log.blue(f'{self.__class__.__name__}.register_handlers start')
        self.unregister_handlers()
        if self.set_work_area(area=area):
            for shader_object in self.get_all_shader_objects():
                if not shader_object:
                    continue
                shader_object.register_handler(area=area)
        else:
            _log.error(f'{self.__class__.__name__}: '
                       f'Viewport area does not exist')
            return False
        _log.output(f'{self.__class__.__name__}.register_handlers end >>>')
        return True

    def unregister_handlers(self) -> Area:
        _log.blue(f'{self.__class__.__name__}.unregister_handlers start')
        for shader_object in self.get_all_shader_objects():
            if not shader_object:
                continue
            shader_object.unregister_handler()
        area = self.get_work_area()
        self.clear_work_area()
        _log.output(f'{self.__class__.__name__}.unregister_handlers end >>>')
        return area

    def set_shaders_visible(self, state: bool) -> None:
        for shader_object in self.get_all_shader_objects():
            if not shader_object:
                continue
            shader_object.set_shader_visible(state)

    def hide_all_shaders(self) -> None:
        _log.yellow(f'{self.__class__.__name__}.hide_all_shaders start')
        self.set_shaders_visible(False)
        _log.output(f'{self.__class__.__name__}.hide_all_shaders end >>>')

    def unhide_all_shaders(self) -> None:
        _log.yellow(f'{self.__class__.__name__}.unhide_all_shaders start')
        self.set_shaders_visible(True)
        _log.output(f'{self.__class__.__name__}.unhide_all_shaders end >>>')

    def start_viewport(self, *, area: Any) -> ActionStatus:
        _log.green(f'{self.__class__.__name__}.start_viewport start')
        if not self.register_handlers(area=area):
            return ActionStatus(False, 'Could not register handlers')
        self.unhide_all_shaders()
        self.tag_redraw()
        _log.output(f'{self.__class__.__name__}.start_viewport end >>>')
        return ActionStatus(True, 'ok')

    def stop_viewport(self) -> ActionStatus:
        _log.green(f'{self.__class__.__name__}.stop_viewport start')
        area = self.unregister_handlers()
        if area:
            area.tag_redraw()
        _log.output(f'{self.__class__.__name__}.stop_viewport end >>>')
        return ActionStatus(True, 'ok')
