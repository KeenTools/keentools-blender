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

from typing import List, Tuple
import os

from bpy_extras.io_utils import ImportHelper, ExportHelper
from bpy.types import Operator, OperatorFileListElement
from bpy.props import BoolProperty, IntProperty, StringProperty, EnumProperty, CollectionProperty
from bpy.path import ensure_ext

from ...utils.kt_logging import KTLogger
from ...addon_config import fb_settings, get_operator
from ...facebuilder_config import FBConfig
from ..fbloader import FBLoader
from ..utils.exif_reader import (read_exif_to_camera,
                                 auto_setup_camera_from_exif)
from ...utils.materials import find_bpy_image_by_name
from ...utils.blendshapes import load_csv_animation_to_blendshapes
from ..ui_strings import buttons
from ...utils.bpy_common import bpy_objects, bpy_images


_log = KTLogger(__name__)


def _image_format_items(default: str = 'PNG',
                        show_exr: bool = False) -> List[Tuple]:
    if default == 'PNG':
        png_num, jpg_num = 0, 1
    else:
        png_num, jpg_num = 1, 0
    exr_num = 2
    arr = [
        ('PNG', 'PNG', 'Default image file format with transparency', png_num),
        ('JPEG', 'JPEG', 'Data loss image format without transparency', jpg_num),
    ]
    if show_exr:
        arr.append(('OPEN_EXR', 'EXR', 'Extended image format with transparency', exr_num))
    return arr


def _filename_ext(file_format: str) -> str:
    ext = '.jpg'
    if file_format == 'PNG':
        ext = '.png'
    elif file_format == 'JPEG':
        ext = '.jpg'
    elif file_format == 'OPEN_EXR':
        ext = '.exr'
    return ext


def _update_format(self, context):
    self.filename_ext = _filename_ext(self.file_format)


class FB_OT_SingleFilebrowserExec(Operator):
    bl_idname = FBConfig.fb_single_filebrowser_exec_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'INTERNAL'}

    def draw(self, context):
        pass

    def execute(self, context):
        settings = fb_settings()

        op = get_operator(FBConfig.fb_single_filebrowser_idname)
        op('INVOKE_DEFAULT', headnum=settings.tmp_headnum,
           camnum=settings.tmp_camnum)

        return {'FINISHED'}


def load_single_image_file(headnum: int, camnum: int, filepath: str) -> bool:
        settings = fb_settings()
        _log.info('Load image file: {}'.format(filepath))

        if not settings.check_heads_and_cams():
            settings.fix_heads()
            return False

        FBLoader.load_model(headnum)

        try:
            img = bpy_images().load(filepath)
            head = settings.get_head(headnum)
            head.get_camera(camnum).cam_image = img
        except RuntimeError:
            _log.error(f'FILE READ ERROR: {filepath}')
            return False

        try:
            read_exif_to_camera(headnum, camnum, filepath)
        except RuntimeError as err:
            _log.error(f'FILE EXIF READ ERROR: {filepath}\n{str(err)}')

        camera = head.get_camera(camnum)
        camera.show_background_image()

        if not camera.auto_focal_estimation:
            auto_setup_camera_from_exif(camera)

        FBLoader.save_fb_serial_and_image_pathes(headnum)
        return True


class FB_OT_SingleFilebrowser(Operator, ImportHelper):
    bl_idname = FBConfig.fb_single_filebrowser_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'UNDO'}

    filter_folder: BoolProperty(
        name='Filter folders',
        default=True,
        options={'HIDDEN'},
    )
    filter_image: BoolProperty(
        name='Filter image',
        default=True,
        options={'HIDDEN'},
    )

    headnum: IntProperty(name='Head index in scene', default=0)
    camnum: IntProperty(name='Camera index', default=0)

    def draw(self, context):
        pass

    def execute(self, context):
        _log.output(f'{self.__class__.__name__} execute')
        if load_single_image_file(self.headnum, self.camnum, self.filepath):
            return {'FINISHED'}

        return {'CANCELLED'}


class FB_OT_TextureFileExport(Operator, ExportHelper):
    bl_idname = FBConfig.fb_texture_file_export_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'INTERNAL'}

    filter_folder: BoolProperty(
        name='Filter folders',
        default=True,
        options={'HIDDEN'},
    )
    filter_image: BoolProperty(
        name='Filter image',
        default=True,
        options={'HIDDEN'},
    )

    file_format: EnumProperty(name='Image file format',
                              description='Choose image file format',
                              items=_image_format_items(default='PNG'),
                              update=_update_format)

    check_existing: BoolProperty(
        name='Check Existing',
        description='Check and warn on overwriting existing files',
        default=True,
        options={'HIDDEN'},
    )

    filename_ext: StringProperty(default=".png")

    filepath: StringProperty(
        default='baked_tex',
        subtype='FILE_PATH'
    )
    headnum: IntProperty(default=0)

    def check(self, context):
        change_ext = False

        filepath = self.filepath
        sp = os.path.splitext(filepath)

        if sp[1] in {'.jpg', '.', '.png', '.PNG', '.JPG', '.JPEG',
                     '.jpeg', '.exr', '.EXR'}:
            filepath = sp[0]

        filepath = ensure_ext(filepath, self.filename_ext)

        if filepath != self.filepath:
            self.filepath = filepath
            change_ext = True

        return change_ext

    def draw(self, context):
        layout = self.layout
        layout.label(text='Image file format')
        layout.prop(self, 'file_format', expand=True)

    def execute(self, context):
        _log.output(f'{self.__class__.__name__} execute')
        _log.output(f'START SAVE TEXTURE: {self.filepath}')
        settings = fb_settings()
        head = settings.get_head(self.headnum)
        if head is None:
            return {'CANCELLED'}

        tex = find_bpy_image_by_name(head.preview_texture_name())
        if tex is None:
            return {'CANCELLED'}
        tex.filepath = self.filepath
        # Blender doesn't change file_format after filepath assigning, so
        fix_for_blender_bug = tex.file_format  # Do not remove!
        tex.file_format = self.file_format
        tex.save()
        _log.output(f'SAVED TEXTURE: {tex.file_format} {self.filepath}')
        return {'FINISHED'}

    def invoke(self, context, event):
        _log.output(f'{self.__class__.__name__} invoke')
        settings = fb_settings()
        head = settings.get_head(self.headnum)
        if head is None:
            return {'CANCELLED'}
        self.filepath = head.preview_texture_name()
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class FB_OT_MultipleFilebrowserExec(Operator):
    bl_idname = FBConfig.fb_multiple_filebrowser_exec_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'UNDO'}

    headnum: IntProperty(name='Head index in scene', default=0)

    def draw(self, context):
        pass

    def execute(self, context):
        _log.output(f'{self.__class__.__name__} execute')
        op = get_operator(FBConfig.fb_multiple_filebrowser_idname)
        op('INVOKE_DEFAULT', headnum=self.headnum)

        return {'FINISHED'}


class FB_OT_MultipleFilebrowser(Operator, ImportHelper):
    bl_idname = FBConfig.fb_multiple_filebrowser_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    filter_folder: BoolProperty(
        name='Filter folders',
        default=True,
        options={'HIDDEN'},
    )
    filter_image: BoolProperty(
        name='Filter image',
        default=True,
        options={'HIDDEN'},
    )

    files: CollectionProperty(
        name='File Path',
        type=OperatorFileListElement,
    )

    directory: StringProperty(
            subtype='DIR_PATH',
    )

    headnum: IntProperty(name='Head index in scene', default=0)

    def draw(self, context):
        layout = self.layout
        layout.label(text='Load images and create views. ')
        layout.label(text='You can select multiple images at once')

    def execute(self, context):
        _log.output(f'{self.__class__.__name__} execute')
        settings = fb_settings()
        if not settings.is_proper_headnum(self.headnum):
            _log.error(f'WRONG HEADNUM: {self.headnum}/'
                       f'{settings.get_last_headnum()}')
            return {'CANCELLED'}

        if not settings.check_heads_and_cams():
            settings.fix_heads()
            return {'CANCELLED'}

        FBLoader.load_model(self.headnum)

        head = settings.get_head(self.headnum)
        last_camnum = head.get_last_camnum()
        _log.output(f'last_camnum: {last_camnum}')

        for f in self.files:
            try:
                filepath = os.path.join(self.directory, f.name)
                _log.output(f'{self.__class__.__name__} IMAGE:\n{filepath}')

                camera = FBLoader.add_new_camera_with_image(self.headnum,
                                                            filepath)
                _log.output(f'read_exif_to_camera')
                read_exif_to_camera(
                    self.headnum, head.get_last_camnum(), filepath)
                camera.orientation = camera.exif.orientation

            except RuntimeError as ex:
                _log.error(f'FILE READ ERROR: {f.name}')

        fb = FBLoader.get_builder()
        for i, camera in enumerate(head.cameras):
            if i > last_camnum:
                _log.output(f'auto_setup_camera_from_exif: {i}')
                auto_setup_camera_from_exif(camera)

                mode = fb.focal_length_estimation_mode()
                _log.output(f'focal_length_estimation_mode: {mode}')
                if mode in ['FB_ESTIMATE_VARYING_FOCAL_LENGTH',
                            'FB_ESTIMATE_STATIC_FOCAL_LENGTH']:
                    fb.set_focal_length_at(
                        camera.get_keyframe(),
                        camera.get_focal_length_in_pixels_coef() * camera.focal)

                FBLoader.center_geo_camera_projection(self.headnum, i)

        FBLoader.save_fb_serial_and_image_pathes(self.headnum)
        return {'FINISHED'}


class FB_OT_AnimationFilebrowser(Operator, ImportHelper):
    bl_idname = FBConfig.fb_animation_filebrowser_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'UNDO'}

    filter_glob: StringProperty(
        default='*.csv',
        options={'HIDDEN'}
    )

    obj_name: StringProperty(name='Object Name in scene')

    def draw(self, context):
        pass

    def execute(self, context):
        _log.output(f'{self.__class__.__name__} execute')
        obj = bpy_objects()[self.obj_name]
        assert obj.type == 'MESH'

        res = load_csv_animation_to_blendshapes(obj, self.filepath)

        if res['status']:
            info = res['message']
            if len(res['ignored']) > 0:
                info += ' Ignored {} columns'.format(len(res['ignored']))
            if len(res['read_facs']) > 0:
                info += ' Recognized {} blendshapes'.format(len(res['read_facs']))
            self.report({'INFO'}, info)
        else:
            self.report({'ERROR'}, res['message'])
        return {'FINISHED'}


CLASSES_TO_REGISTER = (FB_OT_SingleFilebrowser,
                       FB_OT_SingleFilebrowserExec,
                       FB_OT_TextureFileExport,
                       FB_OT_AnimationFilebrowser,
                       FB_OT_MultipleFilebrowser,
                       FB_OT_MultipleFilebrowserExec)
