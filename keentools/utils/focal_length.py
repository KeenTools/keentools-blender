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

__all__ = [
    'update_camera_focal',
    'configure_focal_mode_and_fixes',
    'update_camera_focal'
]

from ..utils.kt_logging import KTLogger


_log = KTLogger(__name__)


def _unfix_all(fb, head):
    for cam in head.cameras:
        fb.set_focal_length_fixed_at(cam.get_keyframe(), False)


def configure_focal_mode_and_fixes(fb, head):
    fb.set_varying_focal_length_estimation()
    for cam in head.cameras:
        fb.set_focal_length_fixed_at(cam.get_keyframe(),
                                     not cam.auto_focal_estimation)


def update_camera_focal(camera, fb):
    kid = camera.get_keyframe()
    before = camera.focal
    focal = fb.focal_length_at(kid) / camera.get_focal_length_in_pixels_coef()
    _log.output(f'update_camera_focal {before} --> {focal}')
    camera.focal = focal  # so callback will change camobj.data.lens
