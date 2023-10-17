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

from typing import List, Tuple, Any

from bpy.types import Scene, TIME_MT_editor_menus
from bpy.props import PointerProperty
from bpy.utils import register_class, unregister_class

from ..utils.kt_logging import KTLogger
from ..geotracker_config import GTConfig, get_gt_settings
from .settings import FrameListItem, GeoTrackerItem, GTSceneSettings
from .actor import GT_OT_Actor
from .pinmode import GT_OT_PinMode
from .movepin import GT_OT_MovePin
from .interface import CLASSES_TO_REGISTER as INTERFACE_CLASSES
from .operators import BUTTON_CLASSES
from ..utils.bpy_common import bpy_window_manager


_log = KTLogger(__name__)


CLASSES_TO_REGISTER = (FrameListItem,
                       GeoTrackerItem,
                       GT_OT_Actor,
                       GT_OT_PinMode,
                       GT_OT_MovePin,
                       GTSceneSettings) + BUTTON_CLASSES + INTERFACE_CLASSES


def _add_addon_settings_var() -> None:
    setattr(Scene, GTConfig.gt_global_var_name,
            PointerProperty(type=GTSceneSettings))


def _remove_addon_settings_var() -> None:
    delattr(Scene, GTConfig.gt_global_var_name)


def tracking_panel(self, context: Any) -> None:
    layout = self.layout
    row = layout.row(align=True)
    row.separator()
    row.operator(GTConfig.gt_prev_keyframe_idname, text='',
                 icon='PREV_KEYFRAME')
    row.operator(GTConfig.gt_next_keyframe_idname, text='',
                 icon='NEXT_KEYFRAME')

    settings = get_gt_settings()
    if not settings.pinmode:
        return

    row2 = row.row(align=True)
    row2.active = settings.pinmode
    row2.operator(GTConfig.gt_add_keyframe_idname, text='',
                  icon='KEY_HLT')
    row2.operator(GTConfig.gt_remove_keyframe_idname, text='',
                  icon='KEY_DEHLT')
    row2.separator()
    row2.prop(settings, 'stabilize_viewport_enabled',
              icon='LOCKED' if settings.stabilize_viewport_enabled else 'UNLOCKED')


def _add_buttons_to_timeline() -> None:
    TIME_MT_editor_menus.append(tracking_panel)


def _remove_buttons_from_timeline() -> None:
    TIME_MT_editor_menus.remove(tracking_panel)


_geotracker_keymaps: List[Tuple] = []


def _geotracker_keymaps_register() -> None:
    global _geotracker_keymaps
    kc = bpy_window_manager().keyconfigs.addon
    km = kc.keymaps.new(name='Window', space_type='EMPTY')
    kmi1 = km.keymap_items.new(idname=GTConfig.gt_prev_keyframe_idname,
                               type='LEFT_ARROW',
                               value='PRESS', alt=True)
    kmi2 = km.keymap_items.new(idname=GTConfig.gt_next_keyframe_idname,
                               type='RIGHT_ARROW',
                               value='PRESS', alt=True)
    _geotracker_keymaps.append((km, kmi1))
    _geotracker_keymaps.append((km, kmi2))
    km = kc.keymaps.new(name='3D View Generic', space_type='VIEW_3D')
    kmi3 = km.keymap_items.new(idname=GTConfig.gt_toggle_lock_viewport_idname,
                               type='L',
                               value='PRESS')
    _geotracker_keymaps.append((km, kmi3))


def _geotracker_keymaps_unregister() -> None:
    global _geotracker_keymaps
    try:
        for km, kmi in _geotracker_keymaps:
            km.keymap_items.remove(kmi)
    except Exception as err:
        _log.error(f'_geotracker_keymaps_unregister Exception:\n{str(err)}')
    _geotracker_keymaps = []


def geotracker_register() -> None:
    _log.output('--- START GEOTRACKER REGISTER ---')

    _log.output('START GEOTRACKER REGISTER CLASSES')
    for cls in CLASSES_TO_REGISTER:
        _log.output('REGISTER GT CLASS: \n{}'.format(str(cls)))
        register_class(cls)

    _log.output('MAIN GEOTRACKER VARIABLE REGISTER')
    _add_addon_settings_var()
    _log.output('BUTTONS ON TIMELINE REGISTER')
    _add_buttons_to_timeline()

    _log.output('GEOTRACKER KEYMAPS REGISTER')
    _geotracker_keymaps_register()

    _log.output('=== GEOTRACKER REGISTERED ===')


def geotracker_unregister() -> None:
    _log.output('--- START GEOTRACKER UNREGISTER ---')

    _log.output('BUTTONS ON TIMELINE UNREGISTER')
    _remove_buttons_from_timeline()

    _log.output('START GEOTRACKER UNREGISTER CLASSES')
    for cls in reversed(CLASSES_TO_REGISTER):
        _log.output('UNREGISTER CLASS: \n{}'.format(str(cls)))
        unregister_class(cls)

    _log.output('MAIN GEOTRACKER VARIABLE UNREGISTER')
    _remove_addon_settings_var()
    _log.output('GEOTRACKER KEYMAPS UNREGISTER')
    _geotracker_keymaps_unregister()

    _log.output('=== GEOTRACKER UNREGISTERED ===')
