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

from typing import Tuple

from bpy.app import version as ver


class BVersion:
    version: Tuple[int, int, int] = ver
    property_keywords_enabled: bool = ver >= (2, 93, 0)
    blender_srgb_to_framebuffer_space_enabled: bool = ver >= (2, 83, 0)
    LocRotScale_exist: bool = version >= (3, 0, 0)
    operator_with_context_exists: bool = ver >= (3, 2, 0)
    pixels_foreach_methods_exist: bool = ver >= (2, 83, 0)
    property_gpu_backend_exists: bool = ver >= (3, 5, 0)
