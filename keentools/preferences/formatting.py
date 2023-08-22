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

import re
from typing import List


def split_by_br_or_newlines_ignore_empty(text: str) -> List[str]:
    res = re.split('<br />|<br>|<br/>|\r\n|\n', text)
    return list(filter(None, res))


def replace_newlines_with_spaces(text: str) -> str:
    return ' '.join(split_by_br_or_newlines_ignore_empty(text))


if __name__ == '__main__':
    assert(replace_newlines_with_spaces('test\n\n\ntest1') == 'test test1')
