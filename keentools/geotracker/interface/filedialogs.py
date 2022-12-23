# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2022 KeenTools

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

import os
from typing import Optional, List

from bpy.types import MovieClip, Operator, OperatorFileListElement
from bpy.props import (StringProperty,
                       IntProperty,
                       CollectionProperty,
                       BoolProperty,
                       EnumProperty)
from bpy_extras.io_utils import ImportHelper, ExportHelper
from bpy.path import ensure_ext

from ...utils.kt_logging import KTLogger
from ...addon_config import Config, get_operator
from ...geotracker_config import GTConfig, get_current_geotracker_item
from ...utils.images import set_background_image_by_movieclip
from ...utils.video import (convert_movieclip_to_frames,
                            load_movieclip,
                            load_image_sequence,
                            get_movieclip_duration)
from ..gtloader import GTLoader
from ...utils.bpy_common import (bpy_start_frame,
                                 bpy_end_frame)
from ..utils.textures import (bake_texture,
                              preview_material_with_texture,
                              bake_texture_sequence)
from ..utils.prechecks import common_checks, prepare_camera, revert_camera
from ..ui_strings import buttons


_log = KTLogger(__name__)


def _load_movieclip(dir_path: str, file_names: List[str]) -> Optional[MovieClip]:
    geotracker = get_current_geotracker_item()
    if not geotracker:
        return None

    new_movieclip = load_movieclip(dir_path, file_names)

    geotracker.movie_clip = new_movieclip
    set_background_image_by_movieclip(geotracker.camobj,
                                      geotracker.movie_clip)
    return new_movieclip


class GT_OT_SequenceFilebrowser(Operator, ImportHelper):
    bl_idname = GTConfig.gt_sequence_filebrowser_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    filter_glob: StringProperty(
        default='*.jpg;*.jpeg;*.png;*.tif;*.tiff;*.bmp;*.mp4;*.avi;*.mov;*.mpeg;*.exr',
        options={'HIDDEN'}
    )

    files: CollectionProperty(
        name='File Path',
        type=OperatorFileListElement,
    )

    directory: StringProperty(
            subtype='DIR_PATH',
    )

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.scale_y = Config.text_scale_y
        col.label(text='Load image sequence or movie. ')
        col.label(text='Just select first image in sequence')

    def execute(self, context):
        geotracker = get_current_geotracker_item()
        if not geotracker:
            return {'CANCELLED'}

        new_movieclip = _load_movieclip(self.directory,
                                        [f.name for f in self.files])
        if not new_movieclip:
            return {'CANCELLED'}

        _log.output(f'LOADED MOVIECLIP: {geotracker.movie_clip.name}')
        return {'FINISHED'}


class GT_OT_MaskSequenceFilebrowser(Operator, ImportHelper):
    bl_idname = GTConfig.gt_mask_sequence_filebrowser_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    filter_glob: StringProperty(
        default='*.jpg;*.jpeg;*.png;*.tif;*.tiff;*.bmp;*.mp4;*.avi;*.mov;*.mpeg;*.exr',
        options={'HIDDEN'}
    )

    files: CollectionProperty(
        name='File Path',
        type=OperatorFileListElement,
    )

    directory: StringProperty(
            subtype='DIR_PATH',
    )

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.scale_y = Config.text_scale_y
        col.label(text='Load mask image sequence or movie. ')
        col.label(text='Just select first image in sequence')

    def execute(self, context):
        geotracker = get_current_geotracker_item()
        if not geotracker:
            return {'CANCELLED'}

        new_sequence = load_image_sequence(self.directory,
                                           [f.name for f in self.files])
        if not new_sequence:
            return {'CANCELLED'}

        geotracker.mask_2d = new_sequence.name
        _log.output(f'LOADED MASK: {new_sequence.name}')
        return {'FINISHED'}


class GT_OT_ChoosePrecalcFile(Operator, ExportHelper):
    bl_idname = GTConfig.gt_choose_precalc_file_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    filter_glob: StringProperty(
        default='*.precalc',
        options={'HIDDEN'}
    )

    check_existing: BoolProperty(
        name='Check Existing',
        description='Check and warn on overwriting existing files',
        default=True,
        options={'HIDDEN'},
    )

    filename_ext: StringProperty(default='.precalc')

    filepath: StringProperty(
        default=GTConfig.default_precalc_filename,
        subtype='FILE_PATH'
    )

    def check(self, context):
        change_ext = False

        filepath = self.filepath
        sp = os.path.splitext(filepath)

        if sp[1] in {'.precalc', '.'}:
            filepath = sp[0]

        filepath = ensure_ext(filepath, self.filename_ext)

        if filepath != self.filepath:
            self.filepath = filepath
            change_ext = True

        return change_ext

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.scale_y = Config.text_scale_y
        col.label(text='Choose an existing .precalc file')
        col.label(text='or just enter a name for a new one')

    def execute(self, context):
        _log.output('PRECALC PATH: {}'.format(self.filepath))
        geotracker = get_current_geotracker_item()
        if not geotracker:
            _log.error('Current GeoTracker is wrong')
            return {'CANCELLED'}

        if os.path.exists(self.filepath) and os.path.isdir(self.filepath):
            _log.error(f'Wrong precalc destination: {self.filepath}')
            self.report({'ERROR'}, 'Wrong precalc destination!')
            return {'CANCELLED'}

        geotracker.precalc_path = self.filepath
        status, msg, _ = geotracker.reload_precalc()
        if not status:
            _log.error(msg)
            self.report({'ERROR'}, msg)

        _log.output('PRECALC PATH HAS BEEN CHANGED: {}'.format(self.filepath))
        return {'FINISHED'}


class _DirSelectionTemplate(Operator, ExportHelper):
    bl_label = 'Choose dir'
    bl_description = 'Choose dir where to place files'
    bl_options = {'REGISTER', 'INTERNAL'}

    use_filter: BoolProperty(default=True)
    use_filter_folder: BoolProperty(default=True)

    filter_glob: StringProperty(
          options={'HIDDEN'}
    )
    filepath: StringProperty(
        default='',
        subtype='FILE_PATH'
    )
    file_format: EnumProperty(name='Image file format', items=[
        ('PNG', 'PNG', 'Default image file format with transparency', 0),
        ('JPEG', 'JPEG', 'Data loss image format without transparency', 1),
    ], description='Choose image file format')
    from_frame: IntProperty(name='from', default=1)
    to_frame: IntProperty(name='to', default=1)
    filename_ext: StringProperty()

    def draw(self, context):
        layout = self.layout
        layout.label(text='Output files format:')
        layout.prop(self, 'file_format', expand=True)
        layout.label(text='Frame range:')
        row = layout.row()
        row.prop(self, 'from_frame', expand=True)
        row.prop(self, 'to_frame', expand=True)


class GT_OT_SplitVideo(_DirSelectionTemplate):
    bl_idname = GTConfig.gt_split_video_to_frames_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        self.filename_ext = '.png' if self.file_format == 'PNG' else '.jpg'
        _log.output(f'OUTPUT filepath: {self.filepath}')

        geotracker = get_current_geotracker_item()
        if not geotracker or not geotracker.movie_clip:
            return {'CANCELLED'}

        output_path = convert_movieclip_to_frames(geotracker.movie_clip,
                                                  self.filepath,
                                                  file_format=self.file_format,
                                                  start_frame=self.from_frame,
                                                  end_frame=self.to_frame)
        _log.output(f'OUTPUT PATH2: {output_path}')
        if output_path is not None:
            new_movieclip = _load_movieclip(os.path.dirname(output_path),
                                            [os.path.basename(output_path)])
            _log.output(f'new_movieclip: {new_movieclip}')
        return {'FINISHED'}


class GT_OT_SplitVideoExec(Operator):
    bl_idname = GTConfig.gt_split_video_to_frames_exec_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'INTERNAL'}

    def draw(self, context):
        pass

    def execute(self, context):
        _log.output('GT_OT_SplitVideoExec')
        geotracker = get_current_geotracker_item()
        if not geotracker or not geotracker.movie_clip:
            return {'CANCELLED'}

        op = get_operator(GTConfig.gt_split_video_to_frames_idname)
        op('INVOKE_DEFAULT', from_frame=1,
           to_frame=get_movieclip_duration(geotracker.movie_clip),
           filepath=os.path.join(os.path.dirname(geotracker.movie_clip.filepath),''))
        return {'FINISHED'}


class GT_OT_FrameSelector(Operator):
    bl_idname = GTConfig.gt_select_frames_for_bake_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'INTERNAL'}

    def draw(self, context):
        geotracker = get_current_geotracker_item()
        if not geotracker or not geotracker.movie_clip:
            return {'CANCELLED'}

        layout = self.layout
        checked_views = False

        box = layout.box()
        col = box.column(align=True)
        col.scale_y = Config.text_scale_y
        for item in geotracker.selected_frames:
            row = col.row(align=True)
            row.prop(item, 'selected', text='')
            row.label(text=f'{item.num}', icon='FILE_IMAGE')
            if item.selected:
                checked_views = True

        row = box.row(align=True)
        row.operator(GTConfig.gt_select_all_frames_idname, text='All')
        row.operator(GTConfig.gt_deselect_all_frames_idname, text='None')

        col = layout.column()
        col.scale_y = Config.text_scale_y

        if checked_views:
            col.label(text='Please note: texture creation is very '
                           'time consuming.')
        else:
            col.alert = True
            col.label(text='You need to select at least one image '
                           'to create texture.')

    def invoke(self, context, event):
        check_status = common_checks(object_mode=True, is_calculating=True,
                                     reload_geotracker=True, geotracker=True,
                                     camera=True, geometry=True,
                                     movie_clip=True)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        geotracker = get_current_geotracker_item()
        gt = GTLoader.kt_geotracker()
        selected_frames = geotracker.selected_frames
        old_selected_frame_numbers = set([x.num for x in selected_frames if x.selected])
        selected_frames.clear()
        for frame in gt.keyframes():
            item = selected_frames.add()
            item.num = frame
            item.selected = frame in old_selected_frame_numbers

        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        check_status = common_checks(object_mode=True, is_calculating=True,
                                     geotracker=True, camera=True,
                                     geometry=True, movie_clip=True)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        geotracker = get_current_geotracker_item()
        selected_keyframes = [x.num for x in geotracker.selected_frames if x.selected]
        if len(selected_keyframes) == 0:
            self.report({'ERROR'}, 'No keyframes have been selected')
            return {'CANCELLED'}

        _log.output('GT START TEXTURE CREATION')
        area = context.area
        prepare_camera(area)
        built_texture = bake_texture(geotracker, selected_keyframes)
        if built_texture is None:
            _log.error('GT TEXTURE HAS NOT BEEN CREATED')
        else:
            preview_material_with_texture(built_texture, geotracker.geomobj)
            _log.output('GT TEXTURE HAS BEEN CREATED')
        revert_camera(area)
        return {'FINISHED'}


class GT_OT_ReprojectTextureSequence(_DirSelectionTemplate):
    bl_idname = GTConfig.gt_reproject_tex_sequence_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    width: IntProperty(default=2048, description='Texture width')
    height: IntProperty(default=2048, description='Texture height')

    def draw(self, context):
        layout = self.layout
        layout.label(text='Output files format:')
        layout.prop(self, 'file_format', expand=True)

        layout.label(text='Texture size:')
        row = layout.row(align=True)
        row.prop(self, 'width', text='Width')
        row.prop(self, 'height', text='Height')

        layout.label(text='Frame range:')
        row = layout.row()
        row.prop(self, 'from_frame', expand=True)
        row.prop(self, 'to_frame', expand=True)

        layout.separator()

        layout.label(text='Output file names:')
        col = layout.column(align=True)
        col.scale_y = Config.text_scale_y
        file_pattern = self._file_pattern()
        col.label(text=file_pattern.format(str(self.from_frame).zfill(4)))
        col.label(text='...')
        col.label(text=file_pattern.format(str(self.to_frame).zfill(4)))

    def invoke(self, context, _event):
        check_status = common_checks(object_mode=True, is_calculating=True,
                                     reload_geotracker=True,
                                     geotracker=True, camera=True,
                                     geometry=True, movie_clip=True)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        self.filepath = ''
        self.from_frame = bpy_start_frame()
        self.to_frame = bpy_end_frame()
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def _file_pattern(self):
        return f'{self.filepath}' + '{}' + f'{self._filename_ext()}'

    def _filename_ext(self):
        return '.png' if self.file_format == 'PNG' else '.jpg'

    def execute(self, context):
        check_status = common_checks(object_mode=True, is_calculating=True,
                                     reload_geotracker=True,
                                     geotracker=True, camera=True,
                                     geometry=True, movie_clip=True)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        self.filename_ext = self._filename_ext()
        _log.output(f'OUTPUT reproject filepath: {self.filepath}')

        geotracker = get_current_geotracker_item()
        if not geotracker or not geotracker.movie_clip:
            return {'CANCELLED'}

        filepath_pattern = self._file_pattern()

        bake_texture_sequence(context, geotracker, filepath_pattern,
                              from_frame=self.from_frame,
                              to_frame=self.to_frame,
                              file_format=self.file_format,
                              width=self.width, height=self.height)
        return {'FINISHED'}
