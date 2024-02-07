# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2019-2024  KeenTools

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

from typing import Optional

from ..utils.kt_logging import KTLogger
from ..addon_config import product_name
from ..utils.timer import KTTimer
from .panels import KTUpdater
from ..blender_independent_packages.pykeentools_loader \
    import is_installed as pkt_is_installed


_log = KTLogger(__name__)


class KTUpdateTimer(KTTimer):
    def __init__(self, product: int, interval: float = 120.0):
        super().__init__()
        self._interval: float = interval
        self._product: int = product

    def _callback(self) -> Optional[float]:
        if self.check_stop_all_timers():
            return None

        _log.output(f'CHECK UPDATE FOR {product_name(self._product)}')
        KTUpdater.call_updater(product_name(self._product))
        if not pkt_is_installed():
            _log.error('PYKEENTOOLS WAS DEACTIVATED')
            self.stop()
            return None

        _log.debug(f'UPDATE CHECKING FOR {product_name(self._product)} '
                   f'IS DELAYED FOR {self._interval:.1f} sec.')
        return self._interval

    def start(self) -> None:
        if not self.is_active() and pkt_is_installed():
            self._start(self._callback, persistent=True)

    def stop(self) -> None:
        self._stop(self._callback)
