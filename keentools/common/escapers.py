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

from typing import Any, Optional
from functools import partial

from bpy.types import Area, Window, Screen

from ..utils.kt_logging import KTLogger
from ..addon_config import (Config,
                            fb_settings,
                            gt_settings,
                            ft_settings,
                            get_settings,
                            ProductType,
                            common_loader)
from ..utils.localview import exit_area_localview
from ..utils.viewport_state import force_show_ui_overlays
from ..utils.bpy_common import bpy_timer_register


_log = KTLogger(__name__)


def fb_pinmode_escaper_check() -> bool:
    settings = fb_settings()
    return (settings.pinmode and
            not settings.loader().viewport().viewport_is_working())


def fb_pinmode_escaper(area: Area, window: Optional[Window],
                       screen: Optional[Screen]) -> None:
    _log.error('FaceBuilder extreme pinmode exit')
    if not fb_pinmode_escaper_check():
        _log.error('fb_pinmode_escaper_check failed')
        return None

    settings = fb_settings()
    exit_area_localview(area, window, screen)
    settings.pinmode = False
    settings.viewport_state.show_ui_elements(area)
    return None


def gt_pinmode_escaper_check() -> bool:
    settings = gt_settings()
    return (settings.pinmode and
            not settings.loader().viewport().viewport_is_working())


def gt_pinmode_escaper(area: Area) -> None:
    _log.error('GeoTracker extreme pinmode exit')
    if not gt_pinmode_escaper_check():
        _log.error('gt_pinmode_escaper_check failed')
        return None

    settings = gt_settings()
    settings.loader().out_pinmode()
    if not area:
        return None
    exit_area_localview(area)
    force_show_ui_overlays(area)
    return None


def ft_pinmode_escaper_check() -> bool:
    settings = ft_settings()
    return (settings.pinmode and
            not settings.loader().viewport().viewport_is_working())


def ft_pinmode_escaper(area: Area) -> None:
    _log.error('FaceTracker extreme pinmode exit')
    if not ft_pinmode_escaper_check():
        _log.error('ft_pinmode_escaper_check failed')
        return None

    settings_ft = ft_settings()
    settings_ft.loader().out_pinmode()

    settings_fb = fb_settings()
    if settings_fb.pinmode:
        settings_fb.pinmode = False
    if not area:
        return None
    exit_area_localview(area)
    force_show_ui_overlays(area)
    return None


def gt_calculating_escaper_check() -> bool:
    settings = gt_settings()
    return (not settings.pinmode and settings.is_calculating()
            and settings.calculating_mode in ('TRACKING', 'REFINE'))


def gt_calculating_escaper() -> None:
    _log.error('GeoTracker extreme calculation stop')
    if not gt_calculating_escaper_check():
        _log.error('gt_calculating_escaper_check failed')
        return None

    settings = gt_settings()
    settings.stop_calculating()
    settings.user_interrupts = True
    return None


def ft_calculating_escaper_check() -> bool:
    settings = ft_settings()
    return (not settings.pinmode and settings.is_calculating()
            and settings.calculating_mode in ('TRACKING', 'REFINE'))


def ft_calculating_escaper() -> None:
    _log.error('FaceTracker extreme calculation stop')
    if not ft_calculating_escaper_check():
        _log.error('ft_calculating_escaper_check failed')
        return None

    settings = ft_settings()
    settings.stop_calculating()
    settings.user_interrupts = True


def start_fb_pinmode_escaper(context: Any) -> None:
    if not hasattr(context, 'area') or not context.area:
        return None
    bpy_timer_register(partial(fb_pinmode_escaper, context.area, context.window,
                               context.screen), first_interval=0.01)


def start_gt_pinmode_escaper(context: Any) -> None:
    if not hasattr(context, 'area') or not context.area:
        return None
    bpy_timer_register(partial(gt_pinmode_escaper, context.area),
                       first_interval=0.01)


def start_ft_pinmode_escaper(context: Any) -> None:
    if not hasattr(context, 'area') or not context.area:
        return None
    bpy_timer_register(partial(ft_pinmode_escaper, context.area),
                       first_interval=0.01)


def start_gt_calculating_escaper() -> None:
    bpy_timer_register(gt_calculating_escaper, first_interval=0.01)


def start_ft_calculating_escaper() -> None:
    bpy_timer_register(ft_calculating_escaper, first_interval=0.01)


def exit_from_localview_button(layout: Any, context: Any,
                               product: int = ProductType.UNDEFINED) -> None:
    if not common_loader().check_localview_without_pinmode(context.area):
        return
    settings = get_settings(product)
    if settings.is_calculating():
        return
    col = layout.column()
    col.alert = True
    col.scale_y = 2.0
    col.operator(Config.kt_exit_localview_idname)
