# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2019-2022  KeenTools

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
from typing import Optional


_log_colors = {
    'gray': '\x1b[1;30m',
    'red': '\x1b[1;31m',
    'green': '\x1b[1;32m',
    'yellow': '\x1b[1;33m',
    'blue': '\x1b[1;34m',
    'magenta': '\x1b[0;35m',
    'cyan': '\x1b[1;36m',
    'reset': '\x1b[0m'}


class KTLogger():
    def __init__(self, *, output: str='debug',
                 info_color: Optional[str]=None,
                 debug_color: Optional[str]=None,
                 warning_color: Optional[str]='yellow',
                 error_color: Optional[str]='red'):
        self._logger = logging.getLogger(__name__)
        self._info_color = info_color
        self._debug_color = debug_color
        self._error_color = error_color
        self._warning_color = warning_color
        if output == 'info':
            self.output = self.info
        elif output == 'warning':
            self.output = self.warning
        elif output == 'error':
            self.output = self.error
        else:
            self.output = self.debug

    def info(self, message: str) -> None:
        if self._info_color is None:
            self._logger.info(message)
        else:
            self.color(self._info_color, message)

    def warning(self, message: str) -> None:
        if self._warning_color is None:
            self._logger.warning(message)
        else:
            self.color(self._warning_color, message)

    def debug(self, message: str) -> None:
        if self._debug_color is None:
            self._logger.debug(message)
        else:
            self.color(self._debug_color, message)

    def error(self, message: str) -> None:
        if self._error_color is None:
            self._logger.error(message)
        else:
            self.color(self._error_color, message)

    def color(self, color: str, txt: str) -> str:
        ''' Add ASCII color code at start and reset code at end of the text'''
        global _log_colors
        if color not in _log_colors:
            return txt
        return f"{_log_colors[color]}{txt}{_log_colors['reset']}"
