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

import logging

from . import coords


def _unfix_all(fb, head):
    for cam in head.cameras:
        fb.set_focal_length_fixed_at(cam.get_keyframe(), False)


def _fix_all_except_this(fb, head, exclude_kid):
    for cam in head.cameras:
        fb.set_focal_length_fixed_at(cam.get_keyframe(),
                                     cam.get_keyframe() != exclude_kid)


def _fix_all_with_known_focuses(fb, head):
    for cam in head.cameras:
        fb.set_focal_length_fixed_at(cam.get_keyframe(),
                                     not cam.auto_focal_estimation)


def configure_focal_mode_and_fixes(fb, head, camera):
    if head.smart_mode():
        fb.set_varying_focal_length_estimation()
        _fix_all_with_known_focuses(fb, head)
    else:  # Override all
        if head.manual_estimation_mode == 'all_different':
            fb.set_varying_focal_length_estimation()
            _unfix_all(fb, head)
        elif head.manual_estimation_mode == 'current_estimation':
            fb.set_varying_focal_length_estimation()
            _fix_all_except_this(fb, head, camera.get_keyframe())
        elif head.manual_estimation_mode == 'same_focus':
            proj_mat = camera.get_projection_matrix()
            fb.set_static_focal_length_estimation(coords.focal_by_projection_matrix_px(proj_mat))
        elif head.manual_estimation_mode == 'force_focal':
            fb.disable_focal_length_estimation()
        else:
            assert False, 'Unknown mode: {}'.format(
                head.manual_estimation_mode)


def update_camera_focal(camera, fb):
    logger = logging.getLogger()
    kid = camera.get_keyframe()
    logger.debug('update_camera_focal before: {}'.format(camera.focal))
    focal = fb.focal_length_at(kid) / camera.get_focal_length_in_pixels_coef()
    logger.debug('update_camera_focal after: {}'.format(focal))
    camera.focal = focal  # so callback will change camobj.data.lens
