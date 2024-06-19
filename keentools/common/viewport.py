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
from ..utils.screen_text import KTScreenText
from ..utils.viewport import KTViewport


_log = KTLogger(__name__)


_text_opacity: float = 1.0


class KTTextViewport(KTViewport):
    def __init__(self, main_text: str = 'KTTextViewport'):
        super().__init__()
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

    def get_all_shader_objects(self) -> List:
        return [self._texter]
