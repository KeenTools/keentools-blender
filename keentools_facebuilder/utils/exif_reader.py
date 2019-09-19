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
import os

from ..blender_independent_packages.exifread import process_file
from ..blender_independent_packages.exifread import \
    DEFAULT_STOP_TAG, FIELD_TYPES

from ..config import Config, get_main_settings, ErrorType


# Convert frac record like '16384/32768' to float 0.5
def _frac_to_float(s):
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
        val = _frac_to_float(data[p].printable)
        logger.debug("{} {}".format(p, val))
        return val
    return None


def _get_units_scale(exif_units):
    # Sensor Units
    if 3.9 <= exif_units <= 4.1:
        return 1.0  # mm (4) non-standard
    elif 2.9 <= exif_units <= 3.1:
        return 10.0  # cm (3)
    elif 1.9 <= exif_units <= 2.1:
        return 25.4  # inch (2)
    else:
        return 25.4  # if undefined


def _get_sensor_size(exif_width, exif_focal_x_res, exif_units):
    try:
        scale = _get_units_scale(exif_units)
        return scale * exif_width / exif_focal_x_res
    except Exception:
        pass
    return None


def get_sensor_size_35mm_equivalent(head):
    if head.exif_image_width > 0.0 and head.exif_image_length > 0.0:
        p = head.exif_image_length / head.exif_image_width
    else:
        p = 24.0 / 36.0
    w = 35.0 * head.exif_focal / head.exif_focal35mm
    h = 35.0 * p * head.exif_focal / head.exif_focal35mm
    return w, h


def _print_out_exif_data(data):
    logger = logging.getLogger(__name__)
    tag_keys = list(data.keys())
    tag_keys.sort()
    for i in tag_keys:
        try:
            logger.info('{} ({}): {}'.format(i,
                FIELD_TYPES[data[i].field_type][2], data[i].printable))
        except:
            logger.error("{} : {}".format(i, str(data[i])))


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
    exif_make = None
    exif_model = None

    try:
        img_file = open(str(filepath), 'rb')
        # get the tags
        data = process_file(img_file, stop_tag=DEFAULT_STOP_TAG,
                            details=True, strict=False,
                            debug=False)
        # This call is needed only for full EXIF review
        # _print_out_exif_data(data)

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
        # Camera Model Name
        if 'Image Make' in data.keys():
            exif_make = data['Image Make']
        if 'Image Model' in data.keys():
            exif_model = data['Image Model']

        img_file.close()

    except IOError:
        logger.error("{}' is unreadable for EXIF".format(filepath))

    return {
        'filepath': os.path.basename(filepath),
        'exif_focal': exif_focal,
        'exif_focal35mm': exif_focal35mm,
        'exif_focal_x_res': exif_focal_x_res,
        'exif_focal_y_res': exif_focal_y_res,
        'exif_width': exif_width,
        'exif_length': exif_length,
        'exif_units': exif_units,
        'exif_make': exif_make,
        'exif_model': exif_model
    }


def init_exif_settings(headnum, data):
    """ Fill Head fields from EXIF data """
    logger = logging.getLogger(__name__)
    settings = get_main_settings()
    head = settings.heads[headnum]
    # Output image size
    message = "EXIF for: {}".format(data['filepath'])

    # Image Size
    if data['exif_width'] is not None and data['exif_length'] is not None:
        head.exif_image_width = data['exif_width']
        head.exif_image_length = data['exif_length']
        message += "\nSize: {} x {}".format(
            int(data['exif_width']), int(data['exif_length']))
    else:
        head.exif_image_width = -1.0
        head.exif_image_length = -1.0

    # Focal
    if data['exif_focal'] is not None:
        head.exif_focal = data['exif_focal']
        message += "\nFocal: {} mm".format(data['exif_focal'])
    else:
        head.exif_focal = -1.0

    # Focal 35mm equivalent
    if data['exif_focal35mm'] is not None:
        head.exif_focal35mm = data['exif_focal35mm']
        message += "\nFocal equiv. 35mm: {:.2f} mm".format(
            data['exif_focal35mm'])
    else:
        head.exif_focal35mm = -1.0

    # Focal X resolution
    if data['exif_focal_x_res'] is not None:
        head.exif_focal_x_res = data['exif_focal_x_res']
    else:
        head.exif_focal_x_res = -1.0

    # Focal Y resolution
    if data['exif_focal_y_res'] is not None:
        head.exif_focal_y_res = data['exif_focal_y_res']
    else:
        head.exif_focal_y_res = -1.0

    # Sensor Width
    if data['exif_width'] is not None and data['exif_focal_x_res'] is not None:
        sensor_width = _get_sensor_size(
            data['exif_width'], data['exif_focal_x_res'], data['exif_units'])

        if sensor_width is not None:
            head.exif_sensor_width = sensor_width
            message += "\nSensor Width: {:.2f} mm".format(sensor_width)
            if data['exif_units'] == 3.0:
                message += " ({:.2f})".format(sensor_width * 2.54)
            else:
                message += " ({:.2f})".format(sensor_width / 2.54)
        else:
            head.exif_sensor_width = -1.0
    else:
        head.exif_sensor_width = -1.0

    # Sensor Length
    if data['exif_length'] is not None and \
            data['exif_focal_y_res'] is not None:
        sensor_length = _get_sensor_size(
            data['exif_length'], data['exif_focal_y_res'], data['exif_units'])

        if sensor_length is not None:
            head.exif_sensor_length = sensor_length
            message += "\nSensor Height: {:.2f} mm".format(sensor_length)
            if data['exif_units'] == 3.0:
                message += " ({:.2f})".format(sensor_length * 2.54)
            else:
                message += " ({:.2f})".format(sensor_length / 2.54)
        else:
            head.exif_sensor_length = -1.0
    else:
        head.exif_sensor_length = -1.0

    # Sensor Units
    if data['exif_units'] == 4.0:  # mm (4) non-standard
        head.exif_units = 4.0
        message += "\nSensor Resolution: pixels per mm"
    if data['exif_units'] == 3.0:  # cm (3)
        head.exif_units = 3.0
        message += "\nSensor Resolution: pixels per cm"
    elif data['exif_units'] == 2.0:
        head.exif_units = 2.0  # inch (2)
        message += "\nSensor Resolution: pixels per inch"
    else:
        head.exif_units = -2.0  # undefined
        message += "\nSensor Resolution: undefined"

    # Sensor via 35mm Equivalent (not used yet)
    if data['exif_focal'] is not None and data['exif_focal35mm'] is not None:
        sc = data['exif_focal'] / data['exif_focal35mm']
        logger.debug("VIA_FOCAL: {} {}".format(36.0 * sc, 24.0 * sc))

    # Camera Model
    if data['exif_model'] is not None:
        make = ' '
        if data['exif_make'] is not None:
            make = "{} ".format(data['exif_make'])
        message += "\nCamera: {}{}".format(make, data['exif_model'])

    return message
