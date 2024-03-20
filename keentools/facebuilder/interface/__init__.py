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

from .menus import CLASSES_TO_REGISTER as MENUS_CLASSES
from .panels import CLASSES_TO_REGISTER as PANELS_CLASSES
from .dialogs import CLASSES_TO_REGISTER as DIALOGS_CLASSES
from .filedialog import CLASSES_TO_REGISTER as FILEDIALOG_CLASSES
from .helps import CLASSES_TO_REGISTER as HELPS_CLASSES


CLASSES_TO_REGISTER = MENUS_CLASSES + PANELS_CLASSES + FILEDIALOG_CLASSES + HELPS_CLASSES + DIALOGS_CLASSES
