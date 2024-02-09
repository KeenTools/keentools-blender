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

from typing import Any, Set, Tuple, List

from bpy.props import StringProperty, FloatProperty, BoolProperty

from ..utils.kt_logging import KTLogger
from ..addon_config import ft_settings
from ..facetracker_config import FTConfig
from .ui_strings import buttons
from ..tracker.movepin import MovePin
from ..utils.bpy_common import bpy_current_frame

from ..tracker.tracking_blendshapes import create_relative_shape_keyframe


_log = KTLogger(__name__)


class FT_OT_MovePin(MovePin):
    bl_idname = FTConfig.ft_movepin_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER'}

    test_action: StringProperty(default="")

    pinx: FloatProperty(default=0)
    piny: FloatProperty(default=0)

    new_pin_flag: BoolProperty(default=False)
    dragged: BoolProperty(default=False)

    shift_x: FloatProperty(default=0.0)
    shift_y: FloatProperty(default=0.0)

    camera_clip_start: FloatProperty(default=0.1)
    camera_clip_end: FloatProperty(default=1000.0)

    old_focal_length: FloatProperty(default=50.0)

    @classmethod
    def get_settings(cls) -> Any:
        return ft_settings()

    def update_wireframe(self):
        settings = self.get_settings()
        settings.loader().update_viewport_shaders(wireframe_data=True,
                                                  geomobj_matrix=True,
                                                  wireframe=True)

    def update_on_left_mouse_release(self) -> None:
        create_relative_shape_keyframe(bpy_current_frame())
