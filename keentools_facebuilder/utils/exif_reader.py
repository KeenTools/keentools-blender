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

from ..config import Config, get_main_settings, ErrorType

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


def init_exif_settings(headnum, data):
    logger = logging.getLogger(__name__)
    settings = get_main_settings()
    head = settings.heads[headnum]
    # Output image size
    message = ""

    # message += "\nSize: {}x{}".format(w, h)

    # Store EXIF data in camera
    if data['exif_units'] == 3.0:
        units_scale = 10.0  # cm (3)
        message += "\nSensor units: cm"
    elif data['exif_units'] == 2.0:
        units_scale = 25.4  # inch (2)
        message += "\nSensor units: inch"
    else:
        units_scale = -25.4  # inch (2)
        message += "\nSensor units: undefined"

    logger.debug("UNIT_SCALE {}".format(units_scale))

    # Focal
    if data['exif_focal'] is not None:
        head.exif_focal = data['exif_focal']
        message += "\nFocal: {}".format(data['exif_focal'])

    # Focal 35mm equivalent
    if data['exif_focal35mm'] is not None:
        head.exif_focal35mm = data['exif_focal35mm']
        message += "\nFocal equiv. 35mm: {:.2f}".format(data['exif_focal35mm'])

    # Sensor Width
    if data['exif_width'] is not None and data['exif_focal_x_res'] is not None:
        sx = 25.4 * data['exif_width'] / data['exif_focal_x_res']
        message += "\nSensor Width: {:.2f} mm".format(sx)
        logger.debug("SX_inch: {}".format(sx))
        sx = 10.0 * data['exif_width'] / data['exif_focal_x_res']
        message += " ({:.2f})".format(sx)
        logger.debug("SX_cm: {}".format(sx))

    # Sensor Length
    if data['exif_length'] is not None and data['exif_focal_y_res'] is not None:
        sy = 25.4 * data['exif_length'] / data['exif_focal_y_res']
        message += "\nSensor Height: {:.2f} mm".format(sy)
        logger.debug("SY_inch: {}".format(sy))
        sy = 10.0 * data['exif_length'] / data['exif_focal_y_res']
        message += " ({:.2f})".format(sy)
        logger.debug("SY_cm: {}".format(sy))

    # Sensor via 35mm Equivalent (not used yet)
    if data['exif_focal'] is not None and data['exif_focal35mm'] is not None:
        sc = data['exif_focal'] / data['exif_focal35mm']
        logger.debug("VIA_FOCAL: {} {}".format(36.0 * sc, 24.0 * sc))
