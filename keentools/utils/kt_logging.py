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
from typing import Optional, List


_log_colors = {
    'gray': '\x1b[1;30m',
    'red': '\x1b[1;31m',
    'green': '\x1b[1;32m',
    'yellow': '\x1b[1;33m',
    'blue': '\x1b[1;34m',
    'magenta': '\x1b[0;35m',
    'cyan': '\x1b[1;36m',
    'reset': '\x1b[0m'}


_module_names: List[str] = []


def _add_module_name(name: str) -> None:
    global _module_names
    _module_names.append(name)


class KTLogger():
    def __init__(self, name, *, output: str = 'debug',
                 info_color: Optional[str] = None,
                 debug_color: Optional[str] = None,
                 warning_color: Optional[str] = 'yellow',
                 error_color: Optional[str] = 'red'):
        self._logger = logging.getLogger(name)
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

        _add_module_name(name)
        self.green(f'import: {name}')

    def info(self, message: str) -> None:
        if self._info_color is None:
            self._logger.info(message)
        else:
            self._logger.info(self.color(self._info_color, message))

    def warning(self, message: str) -> None:
        if self._warning_color is None:
            self._logger.warning(message)
        else:
            self._logger.warning(self.color(self._warning_color, message))

    def debug(self, message: str) -> None:
        if self._debug_color is None:
            self._logger.debug(message)
        else:
            self._logger.debug(self.color(self._debug_color, message))

    def error(self, message: str) -> None:
        if self._error_color is None:
            self._logger.error(message)
        else:
            self._logger.error(self.color(self._error_color, message))

    def color(self, color: str, txt: str) -> str:
        ''' Add an ASCII color code at the beginning
            and a reset code at the end of the text
        '''
        global _log_colors
        if color not in _log_colors:
            return txt
        return f"{_log_colors[color]}{txt}{_log_colors['reset']}"

    def gray(self, txt: str) -> None:
        self.output(self.color('gray', txt))

    def red(self, txt: str) -> None:
        self.output(self.color('red', txt))

    def green(self, txt: str) -> None:
        self.output(self.color('green', txt))

    def yellow(self, txt: str) -> None:
        self.output(self.color('yellow', txt))

    def blue(self, txt: str) -> None:
        self.output(self.color('blue', txt))

    def magenta(self, txt: str) -> None:
        self.output(self.color('magenta', txt))

    def cyan(self, txt: str) -> None:
        self.output(self.color('cyan', txt))

    def module_names(self) -> List[str]:
        return (_module_names)


_log = KTLogger(__name__)
