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

from .utils import *


CLASSES_TO_REGISTER = (KT_OT_DownloadTheUpdate,  # operators
                       KT_OT_RemindLater,
                       KT_OT_SkipVersion,
                       KT_OT_RetryDownloadUpdate,
                       KT_OT_ComeBackToUpdate,
                       KT_OT_InstallUpdates,
                       KT_OT_RemindInstallLater,
                       KT_OT_SkipInstallation)
