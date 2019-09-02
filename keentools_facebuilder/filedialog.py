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
from . blender_independent_packages.exifread import DEFAULT_STOP_TAG, FIELD_TYPES


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


def get_safe_param(p, data):
    logger = logging.getLogger(__name__)
    if p in data.keys():
        val = frac_to_float(data[p].printable)
        logger.debug("{} {}".format(p, val))
        return val


class WM_OT_FBOpenFilebrowser(Operator, ImportHelper):
    bl_idname = Config.fb_filedialog_operator_idname
    bl_label = "Open Image(s)"
    bl_description = "Automatically creates Camera(s) from selected Image(s). " \
                     "All images must be the same size. " \
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

        exif_focal = -1.0
        exif_focal35mm = -1.0
        exif_focal_x_res = -1.0
        exif_focal_y_res = -1.0
        exif_width = -1.0
        exif_length = -1.0
        exif_units = 2.0
        units_scale = 25.4
        for f in self.files:
            filepath = os.path.join(directory, f.name)
            logger.debug("FILE: {}".format(filepath))

            exif_focal = -1.0
            exif_focal35mm = -1.0
            exif_focal_x_res = -1.0
            exif_focal_y_res = -1.0
            exif_width = -1.0
            exif_length = -1.0
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

                exif_focal = get_safe_param('EXIF FocalLength', data)
                exif_focal35mm = get_safe_param('EXIF FocalLengthIn35mmFilm', data)
                exif_focal_x_res = get_safe_param(
                    'EXIF FocalPlaneXResolution', data)
                exif_focal_y_res = get_safe_param(
                    'EXIF FocalPlaneYResolution', data)
                exif_width = get_safe_param('EXIF ExifImageWidth', data)
                exif_length = get_safe_param('EXIF ExifImageLength', data)
                exif_units = get_safe_param('EXIF FocalPlaneResolutionUnit',
                    data)

                img_file.close()

            except IOError:
                logger.error("{}' is unreadable for EXIF".format(filepath))
                continue

            img, camera = FBLoader.add_camera_image(self.headnum, filepath)
            if img.size[0] != w or img.size[1] != h:
                w, h = img.size
                changes += 1

            # Store EXIF data in camera
            if exif_units == 3.0:
                units_scale = 10.0  # cm (3)
            else:
                units_scale = 25.4  # inch (2)

            if exif_focal is not None:
                camera.exif_focal = exif_focal
            if exif_focal35mm is not None:
                camera.exif_focal35mm = exif_focal35mm
            logger.debug("UNIT_SCALE {}".format(units_scale))
            if exif_width is not None and exif_focal_x_res is not None:
                sx = 25.4 * exif_width / exif_focal_x_res
                logger.debug("SX_inch: {}".format(sx))
                sx = 10.0 * exif_width / exif_focal_x_res
                logger.debug("SX_cm: {}".format(sx))

            if exif_length is not None and exif_focal_y_res is not None:
                sy = 25.4 * exif_length / exif_focal_y_res
                logger.debug("SY_inch: {}".format(sy))
                sy = 10.0 * exif_length / exif_focal_y_res
                logger.debug("SY_cm: {}".format(sy))

            if exif_focal is not None and exif_focal35mm is not None:
                sc = exif_focal / exif_focal35mm
                logger.debug("VIA_FOCAL: {} {}".format(36.0 * sc, 24.0 * sc))

        if self.update_render_size == 'yes' and changes == 1:

            render = bpy.context.scene.render
            render.resolution_x = w
            render.resolution_y = h
            settings.frame_width = w
            settings.frame_height = h

        head = settings.heads[self.headnum]
        if not head.use_exif:
            return {'FINISHED'}

        if exif_focal35mm is not None and exif_focal35mm > 0:
            head.sensor_width = 36
            head.sensor_height = 24
            head.focal = exif_focal35mm
            logger.debug("UPDATE via EXIF focal35mm")
            return {'FINISHED'}

        if exif_focal is not None and exif_focal > 0:
            head.focal = exif_focal
            logger.debug("UPDATE via EXIF focal")

        if exif_width is not None and exif_focal_x_res is not None \
                and exif_width > 0 and exif_focal_x_res > 0:
            sx = 25.4 * exif_width / exif_focal_x_res
            head.sensor_width = sx

        if exif_length is not None and exif_focal_y_res is not None \
                and exif_length > 0 and exif_focal_y_res > 0:
            sy = 25.4 * exif_length / exif_focal_y_res
            head.sensor_height = sy

        return {'FINISHED'}
