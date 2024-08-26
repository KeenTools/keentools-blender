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

from typing import Any
from functools import partial

from bpy.types import Area

from ..utils.kt_logging import KTLogger
from ..addon_config import ft_settings, fb_settings
from ..utils.localview import exit_area_localview
from ..utils.viewport_state import force_show_ui_overlays
from ..utils.bpy_common import bpy_timer_register


_log = KTLogger(__name__)


def ft_pinmode_escaper(area: Area) -> None:
    _log.error('FaceTracker extreme pinmode exit')
    settings_ft = ft_settings()
    settings_ft.loader().out_pinmode()

    settings_fb = fb_settings()
    if settings_fb.pinmode:
        settings_fb.pinmode = False

    exit_area_localview(area)
    force_show_ui_overlays(area)
    return None


def start_ft_pinmode_escaper(context: Any) -> None:
    if context.area:
        bpy_timer_register(partial(ft_pinmode_escaper, context.area),
                           first_interval=0.01)


def fb_pinmode_escaper_check() -> bool:
    settings = fb_settings()
    return settings.pinmode and not settings.loader().viewport().viewport_is_working()


def ft_pinmode_escaper_check() -> bool:
    settings = ft_settings()
    return settings.pinmode and not settings.loader().viewport().viewport_is_working()
