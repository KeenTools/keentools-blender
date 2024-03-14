# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2019-2023  KeenTools

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

from typing import Any

from ..utils.kt_logging import KTLogger
from ..addon_config import gt_settings, ProductType, ActionStatus
from ..tracker.loader import Loader


_log = KTLogger(__name__)


class GTLoader(Loader):
    @classmethod
    def product_type(cls):
        return ProductType.GEOTRACKER

    @classmethod
    def get_settings(cls) -> Any:
        return gt_settings()

    @classmethod
    def start_viewport(cls, *, area: Any) -> ActionStatus:
        _log.green(f'{cls.__name__}.start_viewport start')
        vp = cls.viewport()
        if not vp.load_all_shaders():
            msg = 'Problem with loading shaders (see console)'
            _log.error(msg)
            _log.output(f'{cls.__name__}.start_viewport loading shaders error >>>')
            return ActionStatus(False, msg)

        vp.register_handlers(area=area)
        vp.unhide_all_shaders()
        vp.tag_redraw()
        _log.output(f'{cls.__name__}.start_viewport end >>>')
        return ActionStatus(True, 'ok')


GTLoader.init_handlers()
