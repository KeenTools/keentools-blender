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

from ..fbloader import FBLoader
from ..config import Config, get_main_settings, get_operators, ErrorType

from ..utils.exif_reader import read_exif, init_exif_settings, exif_message


class FB_OT_SingleFilebrowserExec(Operator):
    bl_idname = Config.fb_single_filebrowser_exec_idname
    bl_label = "File Browser Execute"
    bl_options = {'REGISTER', 'INTERNAL'}  # UNDO
    bl_description = "Change the image file path"

    def draw(self, context):
        pass

    def execute(self, context):
        settings = get_main_settings()

        op = getattr(get_operators(), Config.fb_single_filebrowser_callname)
        op('INVOKE_DEFAULT', headnum=settings.tmp_headnum,
           camnum=settings.tmp_camnum)

        return {'FINISHED'}


class FB_OT_SingleFilebrowser(Operator, ImportHelper):
    bl_idname = Config.fb_single_filebrowser_idname
    bl_label = "Open Image"
    bl_description = "Open single image file"

    filter_glob: bpy.props.StringProperty(
        default='*.jpg;*.jpeg;*.png;*.tif;*.tiff;*.bmp',
        options={'HIDDEN'}
    )

    headnum: bpy.props.IntProperty(name='Head index in scene', default=0)
    camnum: bpy.props.IntProperty(name='Camera index', default=0)

    update_render_size: bpy.props.EnumProperty(name="Update Size", items=[
        ('yes', 'Update', 'Update render size to images resolution', 0),
        ('no', 'Leave unchanged', 'Leave the render size unchanged', 1),
    ], description="Update Render size")

    def draw(self, context):
        layout = self.layout

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
        logger = logging.getLogger(__name__)
        settings = get_main_settings()
        logger.info('Load image file: {}'.format(self.filepath))

        try:
            img = bpy.data.images.load(self.filepath)
            head = settings.heads[self.headnum]
            head.cameras[self.camnum].cam_image = img
        except RuntimeError:
            logger.error("FILE READ ERROR: {}".format(self.filepath))
            return {'FINISHED'}

        exif_data = read_exif(self.filepath)
        init_exif_settings(self.headnum, exif_data)
        message = exif_message(self.headnum, exif_data)
        head.exif.message = message
        return {'FINISHED'}


class FB_OT_MultipleFilebrowser(Operator, ImportHelper):
    bl_idname = Config.fb_multiple_filebrowser_idname
    bl_label = "Open Image(s)"
    bl_description = "Load images and create views. " \
                     "All images must be of the same size. " \
                     "You can select multiple images at once"

    filter_glob: bpy.props.StringProperty(
        default='*.jpg;*.jpeg;*.png;*.tif;*.tiff;*.bmp',
        options={'HIDDEN'}
    )

    files: bpy.props.CollectionProperty(
        name="File Path",
        type=bpy.types.OperatorFileListElement,
    )

    directory: bpy.props.StringProperty(
            subtype='DIR_PATH',
    )

    headnum: bpy.props.IntProperty(name='Head index in scene', default=0)

    update_render_size: bpy.props.EnumProperty(name="Update Size", items=[
        ('yes', 'Update', 'Update render size to images resolution', 0),
        ('no', 'Leave unchanged', 'Leave the render size unchanged', 1),
    ], description="Update Render size")

    def draw(self, context):
        layout = self.layout

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

    def _read_exif(self, filepath):
        settings = get_main_settings()
        head = settings.get_head(self.headnum)
        exif_data = read_exif(filepath)
        init_exif_settings(self.headnum, exif_data)
        message = exif_message(self.headnum, exif_data)
        head.exif.message = message

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

        # Loaded image sizes
        w = -1
        h = -1
        # Count image size changes over all files
        changes = 0
        exif_allready_read_once = False

        for f in self.files:
            filepath = os.path.join(self.directory, f.name)
            logger.debug("FILE: {}".format(filepath))

            try:
                img, camera = FBLoader.add_camera_image(self.headnum, filepath)
                if img.size[0] != w or img.size[1] != h:
                    w, h = img.size
                    changes += 1

                    if not exif_allready_read_once \
                            and img.size[0] > 0.0 and img.size[1] > 0.0:
                        self._read_exif(filepath)
                        exif_allready_read_once = True

            except RuntimeError as ex:
                logger.error("FILE READ ERROR: {}".format(filepath))

        # We update Render Size in accordance to image size
        # only if all images have the same size
        if self.update_render_size == 'yes' \
                and changes == 1 and w > 0.0 and h > 0.0:
            render = bpy.context.scene.render
            render.resolution_x = w
            render.resolution_y = h
            settings.frame_width = w
            settings.frame_height = h

        return {'FINISHED'}
