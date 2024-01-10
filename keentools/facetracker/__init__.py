# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2023 KeenTools

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

from bpy.types import Scene, TIME_MT_editor_menus
from bpy.utils import register_class, unregister_class

from ..utils.kt_logging import KTLogger
from ..addon_config import (Config,
                            ft_settings,
                            add_addon_settings_var,
                            remove_addon_settings_var)
from ..facetracker_config import FTConfig
from .settings import FaceTrackerItem, FTSceneSettings
from .pinmode import FT_OT_PinMode
from .movepin import FT_OT_MovePin
from .interface import CLASSES_TO_REGISTER as INTERFACE_CLASSES
from .operators import BUTTON_CLASSES


_log = KTLogger(__name__)


CLASSES_TO_REGISTER = (FaceTrackerItem,
                       FT_OT_PinMode,
                       FT_OT_MovePin,
                       FTSceneSettings) + BUTTON_CLASSES + INTERFACE_CLASSES


def tracking_panel(self, context: Any) -> None:
    layout = self.layout
    row = layout.row(align=True)
    row.separator()
    row.operator(FTConfig.ft_prev_keyframe_idname, text='',
                 icon='PREV_KEYFRAME')
    row.operator(FTConfig.ft_next_keyframe_idname, text='',
                 icon='NEXT_KEYFRAME')

    settings = ft_settings()
    if not settings.pinmode:
        return

    row2 = row.row(align=True)
    row2.active = settings.pinmode
    row2.operator(FTConfig.ft_add_keyframe_idname, text='',
                  icon='KEY_HLT')
    row2.operator(FTConfig.ft_remove_keyframe_idname, text='',
                  icon='KEY_DEHLT')

    row2.separator()
    row2.prop(settings, 'stabilize_viewport_enabled',
              icon='LOCKED' if settings.stabilize_viewport_enabled else 'UNLOCKED')


def _add_buttons_to_timeline() -> None:
    TIME_MT_editor_menus.append(tracking_panel)


def _remove_buttons_from_timeline() -> None:
    TIME_MT_editor_menus.remove(tracking_panel)


def facetracker_register() -> None:
    _log.output('--- START FACETRACKER REGISTER ---')

    _log.output('START FACETRACKER REGISTER CLASSES')
    for cls in CLASSES_TO_REGISTER:
        _log.output(f'REGISTER FT CLASS: \n{str(cls)}')
        register_class(cls)

    _log.output('MAIN FACETRACKER VARIABLE REGISTER')
    add_addon_settings_var(Config.ft_global_var_name, FTSceneSettings)

    # _log.output('BUTTONS ON TIMELINE REGISTER')
    # _add_buttons_to_timeline()

    _log.output('=== FACETRACKER REGISTERED ===')


def facetracker_unregister() -> None:
    _log.output('--- START FACETRACKER UNREGISTER ---')

    # _log.output('BUTTONS ON TIMELINE UNREGISTER')
    # _remove_buttons_from_timeline()

    _log.output('START FACETRACKER UNREGISTER CLASSES')
    for cls in reversed(CLASSES_TO_REGISTER):
        _log.output(f'UNREGISTER FT CLASS: \n{str(cls)}')
        unregister_class(cls)

    _log.output('MAIN FACETRACKER VARIABLE UNREGISTER')
    remove_addon_settings_var(Config.ft_global_var_name)

    _log.output('=== FACETRACKER UNREGISTERED ===')
