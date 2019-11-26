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
        arr = str(s).split('/')
        if len(arr) == 1:
            val = float(s)
            return val
        elif len(arr) == 2:
            val = float(arr[0]) / float(arr[1])
            return val
    except (ValueError, ZeroDivisionError):
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
    if tag == 4.0:
        return 'mm'
    elif tag == 3.0:
        return 'cm'
    elif tag == 2.0:
        return 'inch'
    else:
        return 'undefined'


def _get_units_scale_in_mm(exif_units):
    if exif_units == 'mm':
        return 1.0
    elif exif_units == 'cm':
        return 10.0
    elif exif_units == 'inch':
        return 25.4
    else:
        return 25.4


def _get_sensor_size(exif_size, exif_focal_res, exif_units):
    wrong_result = -1.0
    try:
        if exif_size > 0.0 and exif_focal_res > 0.0:
            scale = _get_units_scale_in_mm(exif_units)
            return scale * float(exif_size) / float(exif_focal_res)
        else:
            return wrong_result
    except (TypeError, ValueError, ZeroDivisionError):
        return wrong_result


def _print_out_exif_data(data):
    logger = logging.getLogger(__name__)
    tag_keys = list(data.keys())
    tag_keys.sort()
    for i in tag_keys:
        try:
            logger.info('{} ({}): {}'.format(
                i, FIELD_TYPES[data[i].field_type][2], data[i].printable))
        except Exception:
            logger.error("{} : {}".format(i, str(data[i])))


def get_sensor_size_35mm_equivalent(head):
    w, h = head.exif.calculated_image_size()
    if w > 0.0 and h > 0.0:
        p = h / w
    else:
        p = 24.0 / 36.0
    w = 36.0 * head.exif.focal / head.exif.focal35mm
    h = 36.0 * p * head.exif.focal / head.exif.focal35mm
    return w, h


def _read_exif(filepath):
    logger = logging.getLogger(__name__)

    status = False
    try:
        with open(str(filepath), 'rb') as img_file:
            data = process_file(img_file, stop_tag=DEFAULT_STOP_TAG,
                                details=True, strict=False,
                                debug=False)
            status = True

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
        'image_width': _get_safe_exif_param('Image ImageWidth', data),
        'image_length': _get_safe_exif_param('Image ImageLength', data),
        'exif_units': _get_safe_exif_param(
            'EXIF FocalPlaneResolutionUnit', data),
        'exif_make': _get_safe_exif_param_str('Image Make', data),
        'exif_model': _get_safe_exif_param_str('Image Model', data),
        'status': status
    }


def _safe_parameter(data, name):
    if data[name] is not None:
        return data[name]
    else:
        return -1.0


def _init_exif_settings(headnum, data):
    settings = get_main_settings()
    exif = settings.get_head(headnum).exif

    exif.units = _get_exif_units(data['exif_units'])

    exif.image_width = _safe_parameter(data, 'image_width')
    exif.image_length = _safe_parameter(data, 'image_length')
    exif.exif_width = _safe_parameter(data, 'exif_width')
    exif.exif_length = _safe_parameter(data, 'exif_length')

    exif.focal = _safe_parameter(data, 'exif_focal')
    exif.focal35mm = _safe_parameter(data, 'exif_focal35mm')
    exif.focal_x_res = _safe_parameter(data, 'exif_focal_x_res')
    exif.focal_y_res = _safe_parameter(data, 'exif_focal_y_res')

    exif.sensor_width = _get_sensor_size(
            exif.image_width, exif.focal_x_res, exif.units)

    exif.sensor_length = _get_sensor_size(
            exif.image_length, exif.focal_y_res, exif.units)


def _exif_info_message(headnum, data):
    settings = get_main_settings()
    exif = settings.get_head(headnum).exif

    message = "Source file: {}".format(data['filepath'])

    if exif.focal > 0.0:
        message += "\nFocal length: {}mm".format(exif.focal)

    if exif.focal35mm > 0.0:
        message += \
            "\n35mm equiv.: {:.2f}mm".format(exif.focal35mm)

    if exif.sensor_width > 0.0 and exif.sensor_length > 0.0:
        message += "\nSensor: {:.2f} x {:.2f}mm".format(exif.sensor_width,
                                                      exif.sensor_length)
    elif exif.sensor_width > 0.0:
        message += "\nSensor Width: {:.2f}mm".format(exif.sensor_width)

    elif exif.sensor_length > 0.0:
        message += "\nSensor Height: {:.2f}mm".format(exif.sensor_length)

    if data['exif_model'] is not None:
        make = ' '
        if data['exif_make'] is not None:
            make = "{} ".format(data['exif_make'])
        message += "\nCamera: {}{}".format(make, data['exif_model'])

    return message


def _exif_sizes_message(headnum, image):
    settings = get_main_settings()
    head = settings.get_head(headnum)

    if image is None:
        rw = -1
        rh = -1
    else:
        rw, rh = image.size

    iw = head.exif.image_width
    ih = head.exif.image_length

    ew = head.exif.exif_width
    eh = head.exif.exif_length

    r_msg = "{}x{}px".format(rw, rh)
    i_msg = "{}x{}px".format(int(iw), int(ih))
    e_msg = "{}x{}px".format(int(ew), int(eh))
    no_msg = "-1x-1px"

    sec_msg = no_msg
    trd_msg = no_msg

    # Main logic
    if i_msg != e_msg:
        if i_msg == r_msg:
            sec_msg = e_msg  # r == i != e
        else:
            sec_msg = i_msg
            if e_msg != r_msg:
                trd_msg = e_msg  # All different
    else:
        if i_msg == r_msg:
            pass
        else:
            sec_msg = e_msg

    # Output
    if rw > 0 and rh > 0:
        message = "Real size: {}".format(r_msg)
    else:
        message = "Real size: N/A"

    if sec_msg == no_msg and trd_msg == no_msg:
        return message

    if sec_msg != no_msg and trd_msg != no_msg:
        message += "\nEXIF: Multiple({} / {})".format(sec_msg, trd_msg)
        return message

    if sec_msg != no_msg:
        message += "\nEXIF: {}".format(sec_msg)
        return message

    if trd_msg != no_msg:
        message += "\nEXIF: {}".format(trd_msg)
        return message

    return message


def read_exif_to_head(headnum, filepath):
    settings = get_main_settings()
    head = settings.get_head(headnum)

    exif_data = _read_exif(filepath)
    _init_exif_settings(headnum, exif_data)
    head.exif.info_message = _exif_info_message(headnum, exif_data)
    return exif_data['status']


def update_exif_sizes_message(headnum, image):
    settings = get_main_settings()
    head = settings.get_head(headnum)
    if head is None:
        return False

    head.exif.sizes_message = _exif_sizes_message(headnum, image)
    return True


def read_exif_from_camera(headnum, camnum):
    settings = get_main_settings()
    head = settings.get_head(headnum)
    if head is None:
        return False

    camera = head.get_camera(camnum)
    if camera is None:
        return False

    abspath = camera.get_abspath()
    if abspath is None:
        return False

    status = read_exif_to_head(headnum, abspath)
    update_exif_sizes_message(headnum, camera.cam_image)
    return status
