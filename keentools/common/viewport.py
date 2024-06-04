# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2019-2024 KeenTools

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

from typing import List, Optional, Any, Dict

from bpy.types import Area, SpaceView3D

from ..utils.kt_logging import KTLogger
from ..addon_config import ActionStatus
from ..utils.screen_text import KTScreenText


_log = KTLogger(__name__)


_text_opacity: float = 1.0


def _area_is_wrong(area: Optional[Area]) -> bool:
    return not area or len(area.regions) == 0


class KTTextViewport:
    def __init__(self, main_text: str = 'KTTextViewport'):
        self._work_area: Optional[Area] = None
        self._texter = KTScreenText(SpaceView3D)
        default_text: List[Dict] = [
            {'text': main_text,
             'color': (0.871, 0.107, 0.001, _text_opacity),
             'size': 24,
             'y': 60},  # line 1
            {'text': 'ESC: Exit',
             'color': (1., 1., 1., _text_opacity),
             'size': 20,
             'y': 30}  # line 2
        ]
        self._texter.set_default_text(default_text)
        self._texter.set_message(default_text)

    def texter(self) -> Any:
        return self._texter

    def get_work_area(self) -> Optional[Area]:
        return self._work_area

    def set_work_area(self, area: Area) -> bool:
        if _area_is_wrong(area):
            self._work_area = None
            return False
        else:
            self._work_area = area
            return True

    def clear_work_area(self) -> None:
        self.set_work_area(area=None)

    def tag_redraw(self) -> None:
        area = self.get_work_area()
        if area:
            area.tag_redraw()

    def check_work_area_exists(self, auto_unregister: bool = False) -> bool:
        area = self.get_work_area()
        if area is None:
            return False
        if _area_is_wrong(area):
            if auto_unregister:
                _log.red(f'{self.__class__.__name__}.check_work_area_exists: '
                         f'auto unregister')
                self.set_work_area(area=None)
                self.unregister_handlers()
            return False
        return True

    def is_working(self, auto_unregister: bool = False) -> bool:
        if not self.check_work_area_exists(auto_unregister=auto_unregister):
            return False
        texter = self.texter()
        if not texter:
            return False
        if not texter.is_working():
            if auto_unregister:
                _log.red(f'{self.__class__.__name__}.is_working: '
                         f'auto unregister')
                self.unregister_handlers()
            return False
        return True

    def set_visible(self, state: bool) -> None:
        self.texter().set_visible(state)

    def message_to_screen(self, msg: List,
                          register_area: Optional[Area] = None) -> None:
        texter = self.texter()
        if register_area is not None:
            texter.register_handler(area=register_area)
        texter.set_message(msg)

    def revert_default_screen_message(self) -> None:
        texter = self.texter()
        texter.set_message(texter.get_default_text())

    def register_handlers(self, *, area: Any) -> bool:
        _log.yellow(f'{self.__class__.__name__}.register_handlers start')
        self.unregister_handlers()
        if self.set_work_area(area=area):
            self.texter().register_handler(area=area)
        else:
            _log.error(f'{self.__class__.__name__}: '
                       f'Viewport area does not exist')
            return False
        _log.output(f'{self.__class__.__name__}.register_handlers end >>>')
        return True

    def unregister_handlers(self) -> None:
        _log.yellow(f'{self.__class__.__name__}.unregister_handlers start')
        self.texter().unregister_handler()
        _log.output(f'{self.__class__.__name__}.unregister_handlers end >>>')

    def start_viewport(self, *, area: Any) -> ActionStatus:
        _log.green(f'{self.__class__.__name__}.start_viewport start')
        if not self.register_handlers(area=area):
            return ActionStatus(False, 'Could not register handlers')
        self.tag_redraw()
        _log.output(f'{self.__class__.__name__}.start_viewport end >>>')
        return ActionStatus(True, 'ok')

    def stop_viewport(self) -> ActionStatus:
        _log.green(f'{self.__class__.__name__}.stop_viewport start')
        self.unregister_handlers()
        self.clear_work_area()
        _log.output(f'{self.__class__.__name__}.stop_viewport end >>>')
        return ActionStatus(True, 'ok')


class CommonLoader:
    _text_viewport: Any = KTTextViewport()

    @classmethod
    def text_viewport(cls) -> Any:
        return cls._text_viewport
