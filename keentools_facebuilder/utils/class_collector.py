# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2019  KeenTools

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

from ..preferences import CLASSES_TO_REGISTER as PREFERENCES_CLASSES
from ..interface import CLASSES_TO_REGISTER as INTERFACE_CLASSES
from ..head import MESH_OT_FBAddHead
from ..body import MESH_OT_FBAddBody
from ..settings import FBExifItem, FBCameraItem, FBHeadItem, FBSceneSettings
from ..main_operator import CLASSES_TO_REGISTER as OPERATOR_CLASSES
from ..pinmode import OBJECT_OT_FBPinMode
from ..movepin import OBJECT_OT_FBMovePin
from ..actor import OBJECT_OT_FBActor, OBJECT_OT_FBCameraActor


CLASSES_TO_REGISTER = (
    MESH_OT_FBAddHead,
    MESH_OT_FBAddBody,
    FBExifItem,
    FBCameraItem,
    FBHeadItem,
    FBSceneSettings,
    OBJECT_OT_FBPinMode,
    OBJECT_OT_FBMovePin,
    OBJECT_OT_FBActor,
    OBJECT_OT_FBCameraActor) + OPERATOR_CLASSES + \
                      PREFERENCES_CLASSES + INTERFACE_CLASSES
