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
    import module as pkt_module, is_installed as pkt_is_installed


_log = KTLogger(__name__)


class KTGraceTimer(KTTimer):
    def __init__(self, product: str):
        super().__init__()
        self._interval: float = 1.0
        self._product: str = product
        self._is_started: bool = False

    def _callback(self) -> Optional[float]:
        lm = get_product_license_manager(product=self._product)
        res_tuple = lm.perform_license_and_trial_check(
            strategy=pkt_module().LicenseCheckStrategy.LAZY)
        state = res_tuple[0].state
        if state == 'unknown state':
            return self._interval
        if state == 'running grace period':
            if self._product == 'facebuilder':
                warn = get_operator(Config.kt_warning_idname)
                warn('INVOKE_DEFAULT', msg=ErrorType.FBGracePeriod)
            elif self._product == 'geotracker':
                warn = get_operator(Config.kt_warning_idname)
                warn('INVOKE_DEFAULT', msg=ErrorType.GTGracePeriod)
            self.stop()
            _log.output(f'{self._product} GRACE PERIOD HAS BEEN DETECTED. '
                        f'TIMER IS SWITCHED OFF')
            return None
        if state == 'running':
            self.stop()
            _log.output(f'{self._product} LICENSING IS RUNNING. '
                        f'TIMER IS DELAYED')
            return 3600.0  # 60 min * 60 secs
        return self._interval

    def start(self) -> None:
        if not self._is_started and pkt_is_installed():
            self._start(self._callback, persistent=True)
            self._is_started = True

    def stop(self) -> None:
        self._stop(self._callback)
