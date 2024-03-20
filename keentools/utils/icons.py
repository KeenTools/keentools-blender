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

from typing import Dict, List, Any, Optional
import os

from bpy.utils import previews

from .kt_logging import KTLogger


_log = KTLogger(__name__)


_ICONS_DIR: str = 'icons'
_ICONS: Dict = {
    'align_face': ('align_face.png', 'SHADERFX'),
    'rotate_head_forward': ('rotate_head_forward.png', 'TRIA_RIGHT'),
    'rotate_head_backward': ('rotate_head_backward.png', 'TRIA_LEFT'),

    'track_backward': ('track_backward.png', 'TRACKING_BACKWARDS'),
    'track_forward': ('track_forward.png', 'TRACKING_FORWARDS'),
    'track_backward_single': ('track_backward_single.png',
                              'TRACKING_BACKWARDS_SINGLE'),
    'track_forward_single': ('track_forward_single.png',
                             'TRACKING_FORWARDS_SINGLE')
}


class KTIcons:
    icons: Any = None

    @classmethod
    def register(cls) -> None:
        cls.unregister()
        cls.load_icons()

    @classmethod
    def unregister(cls) -> None:
        if cls.icons is not None:
            previews.remove(cls.icons)

    @classmethod
    def load_icon(cls, name: str, filename: str) -> bool:
        if cls.icons is None:
            cls.icons = previews.new()
        icons_dir = os.path.join(os.path.dirname(__file__), _ICONS_DIR)
        full_path = os.path.join(icons_dir, filename)
        res = cls.icons.load(name, full_path, 'IMAGE')
        _log.output(f'ICON: {name} -- {full_path} -- {res}')
        if res.image_size[0] == 0:
            _log.red(f'Cannot load icon: {name}')
            cls.icons.pop(name)
            return False
        return True

    @classmethod
    def load_icons(cls) -> None:
        _log.yellow('load_icons')
        for name in _ICONS:
            cls.load_icon(name, _ICONS[name][0])
        _log.output(f'icons: {cls.icons.keys()}')

    @classmethod
    def layout_icons(cls, layout: Any, icons: Optional[List] = None):
        icon_list = icons if icons is not None else _ICONS
        col = layout.column()
        for i in icon_list:
            col.label(text=i[0], icon_value=KTIcons.get_id(i[0]))
            col.label(text=i[2], icon=i[2])

    @classmethod
    def get_id(cls, name: str) -> int:
        if cls.icons is None:
            cls.register()

        if name in cls.icons.keys():
            return cls.icons[name].icon_id
        else:
            return 0

    @classmethod
    def key_value(cls, name) -> Dict:
        if cls.icons is None:
            cls.register()

        if name in cls.icons.keys():
            return {'icon_value': cls.icons[name].icon_id}

        if name in _ICONS.keys():
            return {'icon': _ICONS[name][1]}

        _log.error(f'key_value: {name}')
        return {'icon': 'BLANK1'}
