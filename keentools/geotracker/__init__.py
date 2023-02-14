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

import logging
import bpy

from ..geotracker_config import GTConfig, get_gt_settings
from .settings import FrameListItem, GeoTrackerItem, GTSceneSettings
from .actor import GT_OT_Actor
from .pinmode import GT_OT_PinMode
from .movepin import GT_OT_MovePin
from .interface import CLASSES_TO_REGISTER as INTERFACE_CLASSES
from .operators import BUTTON_CLASSES


CLASSES_TO_REGISTER = (FrameListItem,
                       GeoTrackerItem,
                       GT_OT_Actor,
                       GT_OT_PinMode,
                       GT_OT_MovePin,
                       GTSceneSettings) + BUTTON_CLASSES + INTERFACE_CLASSES


def _add_addon_settings_var():
    setattr(bpy.types.Scene, GTConfig.gt_global_var_name,
            bpy.props.PointerProperty(type=GTSceneSettings))


def _remove_addon_settings_var():
    delattr(bpy.types.Scene, GTConfig.gt_global_var_name)


def tracking_panel(self, context):
    layout = self.layout
    row = layout.row(align=True)
    row.separator()
    row.operator(GTConfig.gt_prev_keyframe_idname, text='',
                 icon='PREV_KEYFRAME')
    row.operator(GTConfig.gt_next_keyframe_idname, text='',
                 icon='NEXT_KEYFRAME')

    settings = get_gt_settings()
    row2 = row.row(align=True)
    row2.active = settings.pinmode
    row2.operator(GTConfig.gt_add_keyframe_idname, text='',
                  icon='KEY_HLT')
    row2.operator(GTConfig.gt_remove_keyframe_idname, text='',
                  icon='KEY_DEHLT')


def _add_buttons_to_timeline():
    bpy.types.TIME_MT_editor_menus.append(tracking_panel)


def _remove_buttons_from_timeline():
    bpy.types.TIME_MT_editor_menus.remove(tracking_panel)


def geotracker_register():
    logger = logging.getLogger(__name__)
    logger.debug('START GEOTRACKER REGISTER CLASSES')

    for cls in CLASSES_TO_REGISTER:
        logger.debug('REGISTER GT CLASS: \n{}'.format(str(cls)))
        bpy.utils.register_class(cls)

    _add_addon_settings_var()
    logger.debug('MAIN GEOTRACKER VARIABLE REGISTERED')
    _add_buttons_to_timeline()


def geotracker_unregister():
    logger = logging.getLogger(__name__)
    logger.debug('START GEOTRACKER UNREGISTER CLASSES')

    _remove_buttons_from_timeline()

    for cls in reversed(CLASSES_TO_REGISTER):
        logger.debug('UNREGISTER CLASS: \n{}'.format(str(cls)))
        bpy.utils.unregister_class(cls)

    _remove_addon_settings_var()
    logger.debug('MAIN GEOTRACKER VARIABLE UNREGISTERED')
