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
from .viewport import KTTextViewport


class KTMessageBus:
    def __init__(self):
        # Bus item format
        # id: int -> {item_type: str, info: Dict, messages: List[Dict]}
        self._items: Dict = dict()
        self._last_id: int = 0

    def register_item(self, item_type: str, **kwargs) -> int:
        id = self._last_id
        self._last_id += 1
        self._items[id] = {'item_type': item_type, 'info': kwargs, 'messages': []}
        return id

    def clear_all(self) -> None:
        self._items.clear()

    def get_all(self) -> Dict:
        return self._items

    def check_id(self, id: int) -> bool:
        return id in self._items

    def check_type(self, item_type: str) -> bool:
        for x in self._items:
            if x['item_type'] == item_type:
                return True
        return False

    def get_by_id(self, id: int) -> Optional[Dict]:
        if not self.check_id(id):
            return None
        return self._items[id]

    def get_by_type(self, item_type: str) -> Optional[Dict]:
        return {x: self._items[x] for x in self._items
                if x['item_type'] == item_type}

    def get_by_type_filter(self, filter_set: Set) -> Optional[Dict]:
        return {x: self._items[x] for x in self._items
                if x['item_type'] in filter_set}

    def remove_by_id(self, id: int) -> None:
        return self._items.pop(id, None)

    def remove_by_type(self, item_type: str) -> None:
        self._items = {x: self._items[x] for x in self._items
                       if x['item_type'] != item_type}

    def remove_by_type_filter(self, filter_set: Set) -> None:
        self._items = {x: self._items[x] for x in self._items
                       if x['item_type'] not in filter_set}

    def add_message_by_id(self, id: int, message: Dict) -> bool:
        if not self.check_id(id):
            return False
        self._items[id]['messages'].append(message)
        return True

    def add_message_by_type(self, item_type: str, message: Dict) -> int:
        count = 0
        for id in self._items:
            if self._items[id]['item_type'] == item_type:
                self._items[id]['messages'].append(message)
                count += 1
        return count


class CommonLoader:
    _text_viewport: Any = KTTextViewport()
    _message_bus: Any = KTMessageBus()
    _viewports: Any = KTMessageBus()

    @classmethod
    def text_viewport(cls) -> Any:
        return cls._text_viewport

    @classmethod
    def message_bus(cls) -> Any:
        return cls._message_bus

    @classmethod
    def viewports(cls) -> Any:
        return cls._viewports
