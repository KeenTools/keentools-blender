# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2019-2024  KeenTools

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

from typing import Any, Optional, List, Tuple, Set

from ..utils.kt_logging import KTLogger
from ..addon_config import Config, get_operator, ErrorType


_log = KTLogger(__name__)


_DETECTED_FACES: List = []


def reset_detected_faces() -> None:
    global _DETECTED_FACES
    _DETECTED_FACES = []


def get_detected_faces() -> List[Any]:
    global _DETECTED_FACES
    return _DETECTED_FACES


def set_detected_faces(faces_info: List[Any]) -> None:
    global _DETECTED_FACES
    _DETECTED_FACES = faces_info
    _log.yellow(f'set_detected_faces: {len(_DETECTED_FACES)}')


def get_detected_faces_rectangles() -> List[Tuple]:
    faces = get_detected_faces()
    _log.yellow(f'get_detected_faces_rectangles:\n{faces}')
    rects = []
    for i, face in enumerate(faces):
        x1, y1 = face.xy_min
        x2, y2 = face.xy_max
        if x2 < x1:
            x1, x2 = x2, x1
        if y2 < y1:
            y1, y2 = y2, y1
        rects.append((x1, y1, x2, y2, i))
    return rects


def sort_detected_faces() -> List[Tuple]:
    _log.yellow('sort_detected_faces start')
    faces = get_detected_faces()
    rects = get_detected_faces_rectangles()
    _log.output(f'RECTS BEFORE: {rects}')
    rects.sort(key=lambda x: x[0])  # order by x1
    _log.output(f'RECTS AFTER: {rects}')
    set_detected_faces([faces[x[4]] for x in rects])
    _log.output('sort_detected_faces end >>>')
    return rects


def not_enough_face_features_warning() -> None:
    error_message = 'Sorry, can\'t find enough facial features for ' \
                    'auto alignment. Try to align it manually\n' \
                    'by creating pins and dragging them to match ' \
                    'the mesh with the image'
    warn = get_operator(Config.kt_warning_idname)
    warn('INVOKE_DEFAULT', msg=ErrorType.CustomMessage,
         msg_content=error_message)
    _log.error('could not find enough facial features')
