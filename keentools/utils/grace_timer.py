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

from typing import Optional

from ..utils.kt_logging import KTLogger
from ..addon_config import Config, get_operator, ErrorType
from .timer import KTTimer
from ..preferences.operators import get_product_license_manager
from ..blender_independent_packages.pykeentools_loader \
    import is_installed as pkt_is_installed


_log = KTLogger(__name__)


class KTGraceTimer(KTTimer):
    def __init__(self, product: str, interval: float = 600.0):
        super().__init__()
        self._interval: float = interval
        self._product: str = product

    def _callback(self) -> Optional[float]:
        if self.check_stop_all_timers():
            return None

        _log.debug(f'CHECK GRACE PERIOD FOR {self._product}')
        if not pkt_is_installed():
            _log.error('PYKEENTOOLS WAS DEACTIVATED')
            self.stop()
            return None

        lm = get_product_license_manager(product=self._product)
        if lm.is_grace_period_active():
            if self._product == 'facebuilder':
                warn = get_operator(Config.kt_warning_idname)
                warn('INVOKE_DEFAULT', msg=ErrorType.FBGracePeriod)
            elif self._product == 'geotracker':
                warn = get_operator(Config.kt_warning_idname)
                warn('INVOKE_DEFAULT', msg=ErrorType.GTGracePeriod)
            _log.output(f'{self._product} GRACE PERIOD HAS BEEN DETECTED. '
                        f'TIMER IS SWITCHED OFF')
            self.stop()
            return None
        else:
            _log.debug(f'GRACE PERIOD CHECKING FOR {self._product} '
                       f'IS DELAYED FOR {self._interval:.1f} sec.')
        return self._interval

    def start(self) -> None:
        if not self.is_active() and pkt_is_installed():
            self._start(self._callback, persistent=True)

    def stop(self) -> None:
        self._stop(self._callback)
