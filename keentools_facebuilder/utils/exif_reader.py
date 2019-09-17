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

import logging

from ..blender_independent_packages.exifread import process_file
from ..blender_independent_packages.exifread import \
    DEFAULT_STOP_TAG, FIELD_TYPES


def frac_to_float(s):
    try:
        arr = s.split('/')
        if len(arr) == 1:
            val = float(s)
            return val
        elif len(arr) == 2:
            val = float(arr[0]) / float(arr[1])
            return val
    except Exception:
        pass
    return None


def _get_safe_exif_param(p, data):
    logger = logging.getLogger(__name__)
    if p in data.keys():
        val = frac_to_float(data[p].printable)
        logger.debug("{} {}".format(p, val))
        return val
    return None


def read_exif(filepath):
    logger = logging.getLogger(__name__)

    # EXIF reading variables
    exif_focal = None
    exif_focal35mm = None
    exif_focal_x_res = None
    exif_focal_y_res = None
    exif_width = None
    exif_length = None
    exif_units = None
    units_scale = 25.4

    try:
        img_file = open(str(filepath), 'rb')
        # get the tags
        data = process_file(img_file, stop_tag=DEFAULT_STOP_TAG,
                            details=True, strict=False,
                            debug=False)

        # tag_keys = list(data.keys())
        # tag_keys.sort()
        # for i in tag_keys:
        #     try:
        #         logger.info('{} ({}): {}'.format(i,
        #             FIELD_TYPES[data[i].field_type][2], data[i].printable))
        #     except:
        #         logger.error("{} : {}".format(i, str(data[i])))


        exif_focal = _get_safe_exif_param('EXIF FocalLength', data)
        exif_focal35mm = _get_safe_exif_param(
            'EXIF FocalLengthIn35mmFilm', data)
        exif_focal_x_res = _get_safe_exif_param(
            'EXIF FocalPlaneXResolution', data)
        exif_focal_y_res = _get_safe_exif_param(
            'EXIF FocalPlaneYResolution', data)
        exif_width = _get_safe_exif_param('EXIF ExifImageWidth', data)
        exif_length = _get_safe_exif_param('EXIF ExifImageLength', data)
        exif_units = _get_safe_exif_param(
            'EXIF FocalPlaneResolutionUnit', data)
        img_file.close()

    except IOError:
        logger.error("{}' is unreadable for EXIF".format(filepath))

    return {
        'exif_focal': exif_focal,
        'exif_focal35mm': exif_focal35mm,
        'exif_focal_x_res': exif_focal_x_res,
        'exif_focal_y_res': exif_focal_y_res,
        'exif_width': exif_width,
        'exif_length': exif_length,
        'exif_units': exif_units
    }

