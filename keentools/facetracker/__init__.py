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

from bpy.utils import register_class, unregister_class

from ..utils.kt_logging import KTLogger
from ..addon_config import (Config,
                            add_addon_settings_var,
                            remove_addon_settings_var)
from .settings import FaceTrackerItem, FTSceneSettings
from .pinmode import FT_OT_PinMode
from .movepin import FT_OT_MovePin
from .pick_operator import FT_OT_PickMode, FT_OT_PickModeStarter
from .interface import CLASSES_TO_REGISTER as INTERFACE_CLASSES
from .operators import BUTTON_CLASSES
from ..preferences.hotkeys import facetracker_keymaps_unregister


_log = KTLogger(__name__)


CLASSES_TO_REGISTER = (FaceTrackerItem,
                       FT_OT_PinMode,
                       FT_OT_MovePin,
                       FT_OT_PickMode,
                       FT_OT_PickModeStarter,
                       FTSceneSettings) + BUTTON_CLASSES + INTERFACE_CLASSES


def facetracker_register() -> None:
    _log.green('--- START FACETRACKER REGISTER ---')

    _log.output('START FACETRACKER REGISTER CLASSES')
    for cls in CLASSES_TO_REGISTER:
        _log.output(f'REGISTER FT CLASS: \n{str(cls)}')
        register_class(cls)

    _log.output('MAIN FACETRACKER VARIABLE REGISTER')
    add_addon_settings_var(Config.ft_global_var_name, FTSceneSettings)

    _log.green('=== FACETRACKER REGISTERED ===')


def facetracker_unregister() -> None:
    _log.green('--- START FACETRACKER UNREGISTER ---')

    _log.output('FACETRACKER KEYMAPS UNREGISTER')
    facetracker_keymaps_unregister()

    _log.output('START FACETRACKER UNREGISTER CLASSES')
    for cls in reversed(CLASSES_TO_REGISTER):
        _log.output(f'UNREGISTER FT CLASS: \n{str(cls)}')
        unregister_class(cls)

    _log.output('MAIN FACETRACKER VARIABLE UNREGISTER')
    remove_addon_settings_var(Config.ft_global_var_name)

    _log.green('=== FACETRACKER UNREGISTERED ===')
