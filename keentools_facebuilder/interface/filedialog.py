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
from ..config import Config, get_main_settings, get_operator

from ..utils.exif_reader import (read_exif_to_camera,
                                 update_image_groups,
                                 auto_setup_camera_from_exif)
from ..utils.other import restore_ui_elements
from ..utils.materials import find_bpy_image_by_name
from ..utils.blendshapes import load_csv_animation_to_blendshapes


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

        op = get_operator(Config.fb_single_filebrowser_idname)
        op('INVOKE_DEFAULT', headnum=settings.tmp_headnum,
           camnum=settings.tmp_camnum)

        return {'FINISHED'}


def load_single_image_file(headnum, camnum, filepath):
        logger = logging.getLogger(__name__)
        settings = get_main_settings()
        logger.info('Load image file: {}'.format(filepath))

        if not settings.check_heads_and_cams():
            settings.fix_heads()
            return {'CANCELLED'}

        FBLoader.load_model(headnum)

        try:
            img = bpy.data.images.load(filepath)
            head = settings.get_head(headnum)
            head.get_camera(camnum).cam_image = img
        except RuntimeError:
            logger.error('FILE READ ERROR: {}'.format(filepath))
            return {'CANCELLED'}

        try:
            read_exif_to_camera(headnum, camnum, filepath)
        except RuntimeError:
            logger.error('FILE EXIF READ ERROR: {}'.format(filepath))

        update_image_groups(head)

        camera = head.get_camera(camnum)
        camera.show_background_image()
        auto_setup_camera_from_exif(camera)

        FBLoader.save_only(headnum)
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

    def draw(self, context):
        pass

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
        tex = find_bpy_image_by_name(Config.tex_builder_filename)
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
                     "You can select multiple images at once"

    headnum: bpy.props.IntProperty(name='Head index in scene', default=0)

    def draw(self, context):
        pass

    def execute(self, context):
        restore_ui_elements()

        op = get_operator(Config.fb_multiple_filebrowser_idname)
        op('INVOKE_DEFAULT', headnum=self.headnum)

        return {'FINISHED'}


class FB_OT_MultipleFilebrowser(Operator, ImportHelper):
    bl_idname = Config.fb_multiple_filebrowser_idname
    bl_label = "Open Images"
    bl_description = "Load images and create views. " \
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

    def draw(self, context):
        layout = self.layout
        layout.label(text='Load images and create views. ')
        layout.label(text='You can select multiple images at once')

    def execute(self, context):
        """ Selected files processing"""
        logger = logging.getLogger(__name__)
        settings = get_main_settings()
        if not settings.is_proper_headnum(self.headnum):
            logger.error("WRONG HEADNUM: {}/{}".format(
                self.headnum, settings.get_last_headnum()))
            return {'CANCELLED'}

        if not settings.check_heads_and_cams():
            settings.fix_heads()
            return {'CANCELLED'}

        FBLoader.load_model(self.headnum)

        head = settings.get_head(self.headnum)
        last_camnum = head.get_last_camnum()

        for f in self.files:
            try:
                filepath = os.path.join(self.directory, f.name)
                logger.debug("IMAGE FILE: {}".format(filepath))

                camera = FBLoader.add_new_camera_with_image(self.headnum,
                                                            filepath)
                read_exif_to_camera(
                    self.headnum, head.get_last_camnum(), filepath)
                camera.orientation = camera.exif.orientation

            except RuntimeError as ex:
                logger.error("FILE READ ERROR: {}".format(f.name))

        for i, camera in enumerate(head.cameras):
            if i > last_camnum:
                auto_setup_camera_from_exif(camera)
                FBLoader.center_geo_camera_projection(self.headnum, i)

        update_image_groups(head)

        FBLoader.save_only(self.headnum)
        return {'FINISHED'}


class FB_OT_AnimationFilebrowser(Operator, ImportHelper):
    bl_idname = Config.fb_animation_filebrowser_idname
    bl_label = 'Load animation'
    bl_description = 'Open animation file'
    bl_options = {'REGISTER', 'UNDO'}

    filter_glob: bpy.props.StringProperty(
        default='*.csv',
        options={'HIDDEN'}
    )

    obj_name: bpy.props.StringProperty(name='Object Name in scene')

    def draw(self, context):
        pass

    def execute(self, context):
        obj = bpy.data.objects[self.obj_name]
        assert obj.type == 'MESH'

        res = load_csv_animation_to_blendshapes(obj, self.filepath)

        if res['status']:
            info = 'Loaded animation.'
            if len(res['ignored']) > 0:
                info += ' Ignored {} columns'.format(len(res['ignored']))
            if len(res['read_facs']) > 0:
                info += ' Recognized {} blendshapes'.format(len(res['read_facs']))
            self.report({'INFO'}, info)
        else:
            self.report({'ERROR'}, res['message'])
        return {'FINISHED'}
