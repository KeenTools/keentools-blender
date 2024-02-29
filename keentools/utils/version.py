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

from sys import platform
import os
from typing import Tuple, Optional

import bpy
from bpy.app import version_string as ver_string, version as ver

from .kt_logging import KTLogger


_log = KTLogger(__name__)


def _os_name() -> str:
    if platform == 'win32':
        return 'windows'
    if platform == 'linux' or platform == 'linux2':
        return 'linux'
    if platform == 'darwin':
        return 'macos'


def _get_gpu_backend(property_exists: bool=False) -> Optional[str]:
    if property_exists:
        try:
            return bpy.context.preferences.system.gpu_backend
        except Exception as err:
            _log.error(f'_get_gpu_backend Exception: {str(err)}')
    return 'Undefined'


class BVersion:
    version: Tuple[int, int, int] = ver
    version_string: str = ver_string

    open_dialog_overrides_area: bool = ver < (2, 81, 0)
    dynamic_tooltip_exists: bool = ver >= (2, 81, 0)
    uv_select_overlap_exists: bool = ver >= (2, 81, 0)
    blender_srgb_to_framebuffer_space_enabled: bool = ver >= (2, 83, 0)
    pixels_foreach_methods_exist: bool = ver >= (2, 83, 0)
    bound_box_has_foreach_get: bool = ver >= (2, 83, 0)
    property_keywords_enabled: bool = ver >= (2, 93, 0)
    LocRotScale_exist: bool = version >= (3, 0, 0)
    operator_with_context_exists: bool = ver >= (3, 2, 0)
    property_gpu_backend_exists: bool = ver >= (3, 5, 0)
    use_old_bgl_shaders: bool = ver < (3, 4, 0)
    blf_size_takes_3_arguments: bool = ver < (4, 0, 0)
    principled_shader_has_specular: bool = ver < (4, 0, 0)

    pack_uv_problem_exists: bool = ver == (3, 6, 0)

    os_name: str = _os_name()
    gpu_backend: str = _get_gpu_backend(property_gpu_backend_exists)
    # Property fields of operators cannot be inherited in old Blenders (< 2.93)

    demo_mode: bool = 'KEENTOOLS_ENABLE_DEMO_MODE' in os.environ
