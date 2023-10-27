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

from bpy.utils import register_class, unregister_class

from ..utils.kt_logging import KTLogger
from .operators import GTShaderTestOperator, FBShaderTestOperator
from .panels import (KTErrorMessagePanel,
                     GTShaderTestingPanel,
                     FBShaderTestingPanel)
from ..utils.icons import KTIcons


_log = KTLogger(__name__)


CLASSES_TO_REGISTER = (GTShaderTestOperator,
                       FBShaderTestOperator,
                       GTShaderTestingPanel,
                       FBShaderTestingPanel,
                       KTErrorMessagePanel,)


def testing_register():
    _log.output('START REGISTER TESTING CLASSES')

    for cls in CLASSES_TO_REGISTER:
        _log.output('REGISTER GT CLASS: \n{}'.format(str(cls)))
        register_class(cls)

    _log.output('REGISTER ICONS')
    KTIcons.register()

    _log.output('TESTING CLASSES WERE REGISTERED')


def testing_unregister():
    _log.output('START UNREGISTER TESTING CLASSES')

    for cls in reversed(CLASSES_TO_REGISTER):
        _log.output('UNREGISTER CLASS: \n{}'.format(str(cls)))
        unregister_class(cls)

    _log.output('UNREGISTER ICONS')
    KTIcons.unregister()

    _log.output('TESTING CLASSES WERE UNREGISTERED')
