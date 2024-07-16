# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2022 KeenTools

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
from ..tracker.settings import FrameListItem
from .settings import GeoTrackerItem, GTSceneSettings
from .pinmode import GT_OT_PinMode
from .movepin import GT_OT_MovePin
from .interface import CLASSES_TO_REGISTER as INTERFACE_CLASSES
from .operators import BUTTON_CLASSES
from ..preferences.hotkeys import all_keymaps_unregister
from .actor import GT_OT_Actor


_log = KTLogger(__name__)


CLASSES_TO_REGISTER = (FrameListItem,
                       GeoTrackerItem,
                       GT_OT_Actor,
                       GT_OT_PinMode,
                       GT_OT_MovePin,
                       GTSceneSettings) + BUTTON_CLASSES + INTERFACE_CLASSES


def geotracker_register() -> None:
    _log.green('--- START GEOTRACKER REGISTER ---')

    _log.output('START GEOTRACKER REGISTER CLASSES')
    for cls in CLASSES_TO_REGISTER:
        _log.output(f'REGISTER GT CLASS: \n{str(cls)}')
        register_class(cls)

    _log.output('MAIN GEOTRACKER VARIABLE REGISTER')
    add_addon_settings_var(Config.gt_global_var_name, GTSceneSettings)

    _log.green('=== GEOTRACKER REGISTERED ===')


def geotracker_unregister() -> None:
    _log.green('--- START GEOTRACKER UNREGISTER ---')

    _log.output('GEOTRACKER KEYMAPS UNREGISTER')
    all_keymaps_unregister()

    _log.output('START GEOTRACKER UNREGISTER CLASSES')
    for cls in reversed(CLASSES_TO_REGISTER):
        _log.output(f'UNREGISTER CLASS: \n{str(cls)}')
        unregister_class(cls)

    _log.output('MAIN GEOTRACKER VARIABLE UNREGISTER')
    remove_addon_settings_var(Config.gt_global_var_name)

    _log.green('=== GEOTRACKER UNREGISTERED ===')
