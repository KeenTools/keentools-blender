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

from bpy_extras.io_utils import ImportHelper, ExportHelper
from bpy.types import Operator

from ..fbloader import FBLoader
from ..config import Config, get_main_settings, get_operators, ErrorType

from ..utils.exif_reader import read_exif_to_head, update_exif_sizes_message
from ..utils.other import restore_ui_elements
from ..utils.materials import find_tex_by_name


class FB_OT_SingleFilebrowserExec(Operator):
    bl_idname = Config.fb_single_filebrowser_exec_idname
    bl_label = "File Browser Execute"
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = "Change the image file path"

    def draw(self, context):
        pass

    def execute(self, context):
        settings = get_main_settings()
        restore_ui_elements()

        op = getattr(get_operators(), Config.fb_single_filebrowser_callname)
        op('INVOKE_DEFAULT', headnum=settings.tmp_headnum,
           camnum=settings.tmp_camnum)

        return {'FINISHED'}


def load_single_image_file(headnum, camnum, filepath):
        logger = logging.getLogger(__name__)
        settings = get_main_settings()
        logger.info('Load image file: {}'.format(filepath))

        # if Settings structure is broken
        if not settings.check_heads_and_cams():
            settings.fix_heads()  # Fix
            return {'CANCELLED'}

        try:
            img = bpy.data.images.load(filepath)
            head = settings.get_head(headnum)
            head.get_camera(camnum).cam_image = img
        except RuntimeError:
            logger.error("FILE READ ERROR: {}".format(filepath))
            return {'CANCELLED'}

        read_exif_to_head(headnum, filepath)
        update_exif_sizes_message(headnum, img)

        return {'FINISHED'}


class FB_OT_SingleFilebrowser(Operator, ImportHelper):
    bl_idname = Config.fb_single_filebrowser_idname
    bl_label = "Open Image"
    bl_description = "Open single image file"
    bl_options = {'REGISTER', 'UNDO'}

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

        layout.label(text='Update Scene Render size')
        layout.prop(self, 'update_render_size', expand=True)

        col = layout.column()
        col.scale_y = 0.75
        txt = ['Please keep in mind that',
               'all frames for FaceBuilder',
               'should have the same size.']
        for t in txt:
            col.label(text=t)

    def execute(self, context):
        return load_single_image_file(self.headnum, self.camnum, self.filepath)


def update_format(self, context):
    ext = ".png" if self.file_format == "PNG" else ".jpg"
    self.filename_ext = ext


class FB_OT_TextureFileExport(Operator, ExportHelper):
    bl_idname = Config.fb_texture_file_export_idname
    bl_label = "Export texture"
    bl_description = "Export the created texture to a file"
    bl_options = {'REGISTER', 'INTERNAL'}

    filter_glob: bpy.props.StringProperty(
        default='*.jpg;*.jpeg;*.png;*.tif;*.tiff;*.bmp',
        options={'HIDDEN'}
    )

    file_format: bpy.props.EnumProperty(name="Image file format", items=[
        ('PNG', 'PNG', 'Default image file format', 0),
        ('JPEG', 'JPEG', 'Data loss image format', 1),
    ], description="Choose image file format", update=update_format)

    check_existing: bpy.props.BoolProperty(
        name="Check Existing",
        description="Check and warn on overwriting existing files",
        default=True,
        options={'HIDDEN'},
    )

    filename_ext: bpy.props.StringProperty(default=".png")

    filepath: bpy.props.StringProperty(
        default=Config.tex_builder_filename,
        subtype='FILE_PATH'
    )

    def check(self, context):
        change_ext = False

        filepath = self.filepath
        sp = os.path.splitext(filepath)

        if sp[1] in {'.jpg', '.', '.png', '.PNG', '.JPG', '.JPEG'}:
            filepath = sp[0]

        filepath = bpy.path.ensure_ext(filepath, self.filename_ext)

        if filepath != self.filepath:
            self.filepath = filepath
            change_ext = True

        return change_ext

    def draw(self, context):
        layout = self.layout
        layout.label(text='Image file format')
        layout.prop(self, 'file_format', expand=True)

    def execute(self, context):
        logger = logging.getLogger(__name__)
        logger.debug("START SAVE TEXTURE: {}".format(self.filepath))
        tex = find_tex_by_name(Config.tex_builder_filename)
        if tex is None:
            return {'CANCELLED'}
        tex.filepath = self.filepath
        # Blender doesn't change file_format after filepath assigning, so
        fix_for_blender_bug = tex.file_format  # Do not remove!
        tex.file_format = self.file_format
        tex.save()
        logger.debug("SAVED TEXTURE: {} {}".format(tex.file_format,
                                                   self.filepath))
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class FB_OT_MultipleFilebrowserExec(Operator):
    bl_idname = Config.fb_multiple_filebrowser_exec_idname
    bl_label = "Open Images"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Load images and create views. " \
                     "All images must be of the same size. " \
                     "You can select multiple images at once"

    headnum: bpy.props.IntProperty(name='Head index in scene', default=0)
    auto_update_frame_size: bpy.props.BoolProperty(
        name='Auto update frame size', default=True)

    def draw(self, context):
        pass

    def execute(self, context):
        restore_ui_elements()

        auto_update = 'yes' if self.auto_update_frame_size else 'no'
        op = getattr(get_operators(), Config.fb_multiple_filebrowser_callname)
        op('INVOKE_DEFAULT', headnum=self.headnum,
           update_render_size=auto_update)

        return {'FINISHED'}


class FB_OT_MultipleFilebrowser(Operator, ImportHelper):
    bl_idname = Config.fb_multiple_filebrowser_idname
    bl_label = "Open Images"
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

        layout.label(text='Update Scene Render size')
        layout.prop(self, 'update_render_size', expand=True)

        col = layout.column()
        col.scale_y = 0.75
        txt = ['Please keep in mind that',
               'all frames for FaceBuilder',
               'should have the same size.']
        for t in txt:
            col.label(text=t)

    def execute(self, context):
        """ Selected files processing"""
        logger = logging.getLogger(__name__)
        settings = get_main_settings()
        if len(settings.heads) <= self.headnum:
            warn = getattr(get_operators(), Config.fb_warning_callname)
            warn('INVOKE_DEFAULT', msg=ErrorType.IllegalIndex)
            return {'CANCELLED'}

        # if Settings structure is broken
        if not settings.check_heads_and_cams():
            settings.fix_heads()  # Fix & Out
            return {'CANCELLED'}

        # Flag to prevent EXIF load if the head already has cameras
        exif_allready_read_once = settings.head_has_cameras(self.headnum)

        # Loaded image sizes
        w = -1
        h = -1
        # Count image size changes over all files
        changes = 0
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
                        read_exif_to_head(self.headnum, filepath)
                        update_exif_sizes_message(self.headnum, img)

                        exif_allready_read_once = True

            except RuntimeError as ex:
                logger.error("FILE READ ERROR: {}".format(filepath))

        # We update Render Size in accordance to image size
        # only if 1) all images have the same size and 2) user want it
        if self.update_render_size == 'yes' \
                and changes == 1 and w > 0.0 and h > 0.0:
            render = bpy.context.scene.render
            render.resolution_x = w
            render.resolution_y = h
            settings.frame_width = w
            settings.frame_height = h

        return {'FINISHED'}
