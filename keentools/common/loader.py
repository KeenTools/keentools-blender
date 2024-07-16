# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2024 KeenTools

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

from typing import Any, List, Dict, Optional, Set
from dataclasses import dataclass

from bpy.types import Area

from ..utils.kt_logging import KTLogger
from .viewport import KTTextViewport
from ..addon_config import Config, fb_settings, gt_settings, ft_settings
from ..facebuilder_config import FBConfig
from ..geotracker_config import GTConfig
from ..facetracker_config import FTConfig


_log = KTLogger(__name__)


@dataclass(frozen=True)
class MessageBusItem:
    item_type: str
    info: Dict
    messages: List


class KTMessageBus:
    def __init__(self):
        self._items: Dict = dict()
        self._last_id: int = 0

    def register_item(self, item_type: str, **kwargs) -> int:
        id = self._last_id
        self._last_id += 1
        self._items[id] = MessageBusItem(item_type, kwargs, list())
        _log.output(f'register_item:\n{self._items}')
        return id

    def clear_all(self) -> None:
        self._items.clear()

    def get_all(self) -> Dict:
        return self._items

    def check_id(self, id: int) -> bool:
        return id in self._items

    def check_type(self, item_type: str) -> bool:
        for item in self._items:
            if item.item_type == item_type:
                return True
        return False

    def get_by_id(self, id: int) -> Optional[Dict]:
        if not self.check_id(id):
            return None
        return self._items[id]

    def get_by_type(self, item_type: str) -> Optional[Dict]:
        return {x: self._items[x] for x in self._items
                if self._items[x].item_type == item_type}

    def get_by_type_filter(self, filter_set: Set) -> Optional[Dict]:
        return {x: self._items[x] for x in self._items
                if self._items[x].item_type in filter_set}

    def remove_by_id(self, id: int) -> Optional[Dict]:
        item = self._items.pop(id, None)
        _log.output(f'remove_by_id:\n{self._items}')
        return item

    def remove_by_type(self, item_type: str) -> int:
        prev_len = len(self._items)
        self._items = {x: self._items[x] for x in self._items
                       if self._items[x].item_type != item_type}
        _log.output(f'remove_by_type:\n{self._items}')
        return prev_len - len(self._items)

    def remove_by_type_filter(self, filter_set: Set) -> int:
        prev_len = len(self._items)
        self._items = {x: self._items[x] for x in self._items
                       if self._items[x].item_type not in filter_set}
        _log.output(f'remove_by_type_filter:\n{self._items}')
        return prev_len - len(self._items)

    def add_message_by_id(self, id: int, message: Dict) -> bool:
        if not self.check_id(id):
            return False
        self._items[id].messages.append(message)
        return True

    def add_message_by_type(self, item_type: str, message: Dict) -> int:
        count = 0
        for id in self._items:
            if self._items[id].item_type == item_type:
                self._items[id].messages.append(message)
                count += 1
        return count


class CommonLoader:
    def __init__(self):
        _log.red(f'{self.__class__.__name__}.__init__')
        self._text_viewport: Any = KTTextViewport()
        self._message_bus: Any = KTMessageBus()
        self._esc_pressed: bool = False
        self._ft_head_mode_state: str = 'NONE'  # 'CHOOSE_FRAME', 'EDIT_HEAD'

    def ft_head_mode(self) -> str:
        if self._ft_head_mode_state == 'EDIT_HEAD':
            settings = fb_settings()
            if not settings or not settings.pinmode:
                self.set_ft_head_mode('NONE')
        return self._ft_head_mode_state

    def set_ft_head_mode(self, value: str) -> None:
        self._ft_head_mode_state = value

    def esc_pressed(self) -> bool:
        return self._esc_pressed

    def set_esc_pressed(self, value: bool) -> None:
        self._esc_pressed = value

    def text_viewport(self) -> Any:
        return self._text_viewport

    def message_bus(self) -> Any:
        return self._message_bus

    def stop_fb_pinmode(self) -> None:
        message_bus = self.message_bus()
        message_bus.remove_by_type(FBConfig.fb_pinmode_idname)

    def stop_gt_pinmode(self) -> None:
        message_bus = self.message_bus()
        message_bus.remove_by_type(GTConfig.gt_pinmode_idname)

    def stop_ft_pinmode(self) -> None:
        message_bus = self.message_bus()
        message_bus.remove_by_type(FTConfig.ft_pinmode_idname)

    def stop_esc_watcher(self) -> None:
        message_bus = self.message_bus()
        message_bus.remove_by_type(Config.kt_interrupt_modal_idname)

    def stop_fb_viewport(self) -> None:
        vp = fb_settings().loader().viewport()
        vp.stop_viewport()

    def stop_gt_viewport(self) -> None:
        vp = gt_settings().loader().viewport()
        vp.stop_viewport()

    def stop_ft_viewport(self) -> None:
        vp = gt_settings().loader().viewport()
        vp.stop_viewport()

    def stop_text_viewport(self) -> None:
        self.text_viewport().stop_viewport()

    def get_current_viewport_area(self) -> Optional[Area]:
        settings = fb_settings()
        if settings.pinmode:
            _log.output('get_current_viewport_area FB')
            return settings.loader().viewport().get_work_area()
        settings = gt_settings()
        if settings.pinmode:
            _log.output('get_current_viewport_area GT')
            return settings.loader().viewport().get_work_area()
        settings = ft_settings()
        if settings.pinmode:
            _log.output('get_current_viewport_area FT')
            return settings.loader().viewport().get_work_area()
        _log.output('get_current_viewport_area TV')
        return self.text_viewport().get_work_area()

    def check_localview_without_pinmode(self, area: Optional[Area]) -> bool:
        if (not area or not area.spaces or not area.spaces.active or
                not area.spaces.active.local_view):
            return False
        settings = fb_settings()
        if settings and settings.pinmode:
            return False
        settings = gt_settings()
        if settings and settings.pinmode:
            return False
        settings = ft_settings()
        if settings and settings.pinmode:
            return False
        if self.ft_head_mode() == 'CHOOSE_FRAME':
            return False
        return True
