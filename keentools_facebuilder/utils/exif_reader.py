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
    if data is not None and p in data.keys():
        val = _frac_to_float(data[p].printable)
        logger.debug("{} {}".format(p, val))
        return val
    return None


def _get_safe_exif_param_str(p, data):
    if data is not None and p in data.keys():
        return data[p]
    return None


def _get_exif_units(tag):
    # Sensor Units
    if tag == 4.0:  # mm (4) non-standard
        return 'mm'
    elif tag == 3.0:  # cm (3)
        return 'cm'
    elif tag == 2.0:
        return 'inch'  # inch (2)
    else:
        return 'undefined'  # undefined


def _get_units_scale(exif_units):
    # Sensor Units
    if exif_units == 'mm':
        return 1.0  # mm (4) non-standard
    elif exif_units == 'cm':
        return 10.0  # cm (3)
    elif exif_units == 'inch':
        return 25.4  # inch (2)
    else:
        return 25.4  # if undefined


def _get_sensor_size(exif_width, exif_focal_x_res, exif_units):
    try:
        scale = _get_units_scale(exif_units)
        return scale * exif_width / exif_focal_x_res
    except Exception:
        return -1.0


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


def get_sensor_size_35mm_equivalent(head):
    if head.exif_image_width > 0.0 and head.exif_image_length > 0.0:
        p = head.exif_image_length / head.exif_image_width
    else:
        p = 24.0 / 36.0
    w = 35.0 * head.exif_focal / head.exif_focal35mm
    h = 35.0 * p * head.exif_focal / head.exif_focal35mm
    return w, h


def read_exif(filepath):
    logger = logging.getLogger(__name__)

    try:
        with open(str(filepath), 'rb') as img_file:
            data = process_file(img_file, stop_tag=DEFAULT_STOP_TAG,
                                details=True, strict=False,
                                debug=False)

        # This call is needed only for full EXIF review
        # _print_out_exif_data(data)

    except IOError:
        logger.error("{}' is unreadable for EXIF".format(filepath))
        data = None

    return {
        'filepath': os.path.basename(filepath),
        'exif_focal': _get_safe_exif_param('EXIF FocalLength', data),
        'exif_focal35mm': _get_safe_exif_param(
            'EXIF FocalLengthIn35mmFilm', data),
        'exif_focal_x_res': _get_safe_exif_param(
            'EXIF FocalPlaneXResolution', data),
        'exif_focal_y_res': _get_safe_exif_param(
            'EXIF FocalPlaneYResolution', data),
        'exif_width': _get_safe_exif_param('EXIF ExifImageWidth', data),
        'exif_length': _get_safe_exif_param('EXIF ExifImageLength', data),
        'exif_units': _get_safe_exif_param(
            'EXIF FocalPlaneResolutionUnit', data),
        'exif_make': _get_safe_exif_param_str('Image Make', data),
        'exif_model': _get_safe_exif_param_str('Image Model', data)
    }


def _safe_parameter(data, name):
    if data[name] is not None:
        return data[name]
    else:
        return -1.0


def init_exif_settings(headnum, data):
    """ Fill Head fields from EXIF data """
    settings = get_main_settings()
    head = settings.heads[headnum]

    head.exif_units = _get_exif_units(data['exif_units'])

    head.exif_image_width = _safe_parameter(data, 'exif_width')
    head.exif_image_length = _safe_parameter(data, 'exif_length')
    head.exif_focal = _safe_parameter(data, 'exif_focal')
    head.exif_focal35mm = _safe_parameter(data, 'exif_focal35mm')
    head.exif_focal_x_res = _safe_parameter(data, 'exif_focal_x_res')
    head.exif_focal_y_res = _safe_parameter(data, 'exif_focal_y_res')

    # Sensor Width
    if head.exif_image_width > 0.0 and head.exif_focal_x_res > 0.0:
        head.exif_sensor_width = _get_sensor_size(
            head.exif_image_width, head.exif_focal_x_res, head.exif_units)
    else:
        head.exif_sensor_width = -1.0

    # Sensor Length
    if head.exif_image_length > 0.0 and head.exif_focal_y_res > 0.0:
        head.exif_sensor_length = _get_sensor_size(
            head.exif_image_length, head.exif_focal_y_res, head.exif_units)
    else:
        head.exif_sensor_length = -1.0


def exif_message(headnum, data):
    """ Fill Head fields from EXIF data """
    settings = get_main_settings()
    head = settings.heads[headnum]

    # Output image info
    message = "EXIF for: {}".format(data['filepath'])

    # Size: W x H
    if head.exif_image_width > 0.0 and head.exif_image_length > 0.0:
        message += "\nSize: {} x {}".format(
            int(head.exif_image_width), int(head.exif_image_length))

    # Focal
    if head.exif_focal > 0.0:
        message += "\nFocal: {} mm".format(head.exif_focal)

    # Focal 35 mm equiv.
    if head.exif_focal35mm > 0.0:
        message += "\nFocal 35mm equiv.: {:.2f} mm".format(head.exif_focal35mm)

    # Sensor Width
    if head.exif_sensor_width > 0.0:
        message += "\nSensor Width: {:.2f} mm".format(head.exif_sensor_width)

    # Sensor Height
    if head.exif_sensor_length > 0.0:
        message += "\nSensor Height: {:.2f} mm".format(head.exif_sensor_length)

    # Camera: Maker Model
    if data['exif_model'] is not None:
        make = ' '
        if data['exif_make'] is not None:
            make = "{} ".format(data['exif_make'])
        message += "\nCamera: {}{}".format(make, data['exif_model'])

    return message
