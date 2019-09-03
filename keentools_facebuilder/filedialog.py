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

import bpy
import os

from bpy_extras.io_utils import ImportHelper
from bpy.types import Operator

from . fbloader import FBLoader
from . config import Config, get_main_settings, ErrorType

from . blender_independent_packages.exifread import process_file
from . blender_independent_packages.exifread import \
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


def get_safe_exif_param(p, data):
    logger = logging.getLogger(__name__)
    if p in data.keys():
        val = frac_to_float(data[p].printable)
        logger.debug("{} {}".format(p, val))
        return val
    return None


class WM_OT_FBOpenFilebrowser(Operator, ImportHelper):
    bl_idname = Config.fb_filedialog_operator_idname
    bl_label = "Open Image(s)"
    bl_description = "Automatically creates Camera(s) from selected " \
                     "Image(s). All images must be the same size. " \
                     "You can select multiple images at once"

    filter_glob: bpy.props.StringProperty(
        default='*.jpg;*.jpeg;*.png;*.tif;*.tiff;*.bmp',
        options={'HIDDEN'}
    )

    filename_ext = ""

    files: bpy.props.CollectionProperty(
        name="File Path",
        type=bpy.types.OperatorFileListElement,
    )

    directory: bpy.props.StringProperty(
            subtype='DIR_PATH',
    )

    headnum: bpy.props.IntProperty(name='Head index in scene', default=0)

    update_render_size: bpy.props.EnumProperty(name="UV", items=[
        ('yes', 'Update', 'Update render size to images resolution', 0),
        ('no', 'Leave unchanged', 'Leave the render size unchanged', 1),
    ], description="Update Render size")

    # use_exif: bpy.props.EnumProperty(name="Use EXIF Data", items=[
    #    ('yes', 'Use EXIF', 'Update camera data if exists in EXIF', 0),
    #    ('no', 'Leave unchanged', 'Leave camera parameters unchanged', 1),
    #], description="EXIF using")

    def draw(self, context):
        layout = self.layout

        #layout.label(text='EXIF for cameras (Focal, Sensor)')
        #layout.prop(self, 'use_exif', expand=True)

        layout.label(text='Update Scene Render Size')
        layout.prop(self, 'update_render_size', expand=True)

        col = layout.column()
        col.scale_y = 0.75
        txt = ['All frames for FaceBuilder',
               'should have the same size.',
               'So Update option is the best choice',
               'for standard workflow. [Update]',
               'changes Render Size of your Scene!']
        for t in txt:
            col.label(text=t)

    def execute(self, context):
        """ Selected files processing"""
        logger = logging.getLogger(__name__)
        settings = get_main_settings()
        if len(settings.heads) <= self.headnum:
            op = getattr(bpy.ops.wm, Config.fb_warning_operator_callname)
            op('INVOKE_DEFAULT', msg=ErrorType.IllegalIndex)
            return {'CANCELLED'}
        # if Settings structure is broken
        if not settings.check_heads_and_cams():
            settings.fix_heads()  # Fix

        directory = self.directory

        changes = 0
        w = -1
        h = -1

        exif_focal = None
        exif_focal35mm = None
        exif_focal_x_res = None
        exif_focal_y_res = None
        exif_width = None
        exif_length = None
        exif_units = 2.0
        units_scale = 25.4
        message = ""

        for f in self.files:
            filepath = os.path.join(directory, f.name)
            logger.debug("FILE: {}".format(filepath))

            exif_focal = None
            exif_focal35mm = None
            exif_focal_x_res = None
            exif_focal_y_res = None
            exif_width = None
            exif_length = None
            exif_units = 2.0
            units_scale = 25.4

            try:
                img_file = open(str(filepath), 'rb')
                detailed = True
                stop_tag = DEFAULT_STOP_TAG
                debug = False
                strict = False
                color = False
                # get the tags
                data = process_file(img_file, stop_tag=stop_tag,
                                    details=detailed, strict=strict,
                                    debug=debug)
                tag_keys = list(data.keys())
                # tag_keys.sort()

                for i in tag_keys:
                    try:
                        logger.info('{} ({}): {}'.format(i,
                                    FIELD_TYPES[data[i].field_type][2],
                                    data[i].printable))
                    except:
                        logger.error("{} : {}".format(i, str(data[i])))
                # print("TAGS:", data)

                exif_focal = get_safe_exif_param('EXIF FocalLength', data)
                exif_focal35mm = get_safe_exif_param('EXIF FocalLengthIn35mmFilm', data)
                exif_focal_x_res = get_safe_exif_param(
                    'EXIF FocalPlaneXResolution', data)
                exif_focal_y_res = get_safe_exif_param(
                    'EXIF FocalPlaneYResolution', data)
                exif_width = get_safe_exif_param('EXIF ExifImageWidth', data)
                exif_length = get_safe_exif_param('EXIF ExifImageLength', data)
                exif_units = get_safe_exif_param('EXIF FocalPlaneResolutionUnit',
                                                 data)

                img_file.close()
                # Output filename
                message = "EXIF for: {}".format(f.name)

            except IOError:
                logger.error("{}' is unreadable for EXIF".format(filepath))
                continue

            img, camera = FBLoader.add_camera_image(self.headnum, filepath)
            if img.size[0] != w or img.size[1] != h:
                w, h = img.size
                changes += 1

            # Output image size
            message += "\n({}x{})".format(w, h)

            # Store EXIF data in camera
            if exif_units == 3.0:
                units_scale = 10.0  # cm (3)
                # message += "\nSensor units: cm"
            else:
                units_scale = 25.4  # inch (2)
                # message += "\nSensor units: inch"
            logger.debug("UNIT_SCALE {}".format(units_scale))

            # Focal
            if exif_focal is not None:
                camera.exif_focal = exif_focal
                message += "\nFocal: {}".format(exif_focal)

            # Focal 35mm equivalent
            if exif_focal35mm is not None:
                camera.exif_focal35mm = exif_focal35mm
                message += "\nFocal equiv. 35mm: {:.2f}".format(exif_focal35mm)

            # Sensor Width
            if exif_width is not None and exif_focal_x_res is not None:
                sx = 25.4 * exif_width / exif_focal_x_res
                message += "\nSensor Width: {:.2f} mm".format(sx)
                logger.debug("SX_inch: {}".format(sx))
                sx = 10.0 * exif_width / exif_focal_x_res
                message += " ({:.2f})".format(sx)
                logger.debug("SX_cm: {}".format(sx))

            # Sensor Length
            if exif_length is not None and exif_focal_y_res is not None:
                sy = 25.4 * exif_length / exif_focal_y_res
                message += "\nSensor Height: {:.2f} mm".format(sy)
                logger.debug("SY_inch: {}".format(sy))
                sy = 10.0 * exif_length / exif_focal_y_res
                message += " ({:.2f})".format(sy)
                logger.debug("SY_cm: {}".format(sy))

            # Sensor via 35mm Equivalent (not used yet)
            if exif_focal is not None and exif_focal35mm is not None:
                sc = exif_focal / exif_focal35mm
                logger.debug("VIA_FOCAL: {} {}".format(36.0 * sc, 24.0 * sc))

        # We update Render Size in accordance to image size
        if self.update_render_size == 'yes' and changes == 1:
            render = bpy.context.scene.render
            render.resolution_x = w
            render.resolution_y = h
            settings.frame_width = w
            settings.frame_height = h

        # Start EXIF results performing
        head = settings.heads[self.headnum]
        if not head.use_exif:
            # User don't want EXIF
            head.exif_message = ""
            return {'FINISHED'}  # (1)

        # If there is focal35mm equivalent, use it instead real sensor size
        if exif_focal35mm is not None:
            head.sensor_width = 36
            head.sensor_height = 24
            head.focal = exif_focal35mm
            logger.debug("UPDATE via EXIF focal35mm")
            head.exif_message = message
            return {'FINISHED'}  # (2)

        # Focal Length if found
        if exif_focal is not None:
            head.focal = exif_focal
            logger.debug("UPDATE via EXIF focal")

        # Sensor Width calculated via EXIF
        if exif_width is not None and exif_focal_x_res is not None:
            # assumed inches instead EXIF units_scale
            sx = 25.4 * exif_width / exif_focal_x_res
            head.sensor_width = sx

        if exif_length is not None and exif_focal_y_res is not None:
            # assumed inches instead EXIF units_scale
            sy = 25.4 * exif_length / exif_focal_y_res
            head.sensor_height = sy

        head.exif_message = message

        return {'FINISHED'}  # (3)
