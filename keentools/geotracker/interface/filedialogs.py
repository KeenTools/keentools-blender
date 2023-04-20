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
from typing import Optional, List, Tuple
import re

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
from ...geotracker_config import (GTConfig,
                                  get_gt_settings,
                                  get_current_geotracker_item)
from ...utils.images import (set_background_image_by_movieclip,
                             get_sequence_file_number)
from ...utils.video import (convert_movieclip_to_frames,
                            load_movieclip,
                            load_image_sequence,
                            get_movieclip_duration)
from ..gtloader import GTLoader
from ...utils.bpy_common import (bpy_start_frame,
                                 bpy_end_frame,
                                 bpy_current_frame)
from ..utils.textures import (bake_texture,
                              preview_material_with_texture,
                              bake_texture_sequence)
from ..utils.prechecks import common_checks, prepare_camera, revert_camera
from ..ui_strings import buttons
from ..utils.geotracker_acts import (check_uv_exists,
                                     check_uv_overlapping,
                                     bake_texture_from_frames_act)


_log = KTLogger(__name__)


def _load_movieclip(dir_path: str, file_names: List[str]) -> Optional[MovieClip]:
    geotracker = get_current_geotracker_item()
    if not geotracker:
        return None

    new_movieclip = load_movieclip(dir_path, file_names)

    if new_movieclip and new_movieclip.source == 'SEQUENCE':
        file_number = get_sequence_file_number(
            os.path.basename(new_movieclip.filepath))
        if file_number >= 0:
            new_movieclip.frame_start = file_number

    geotracker.movie_clip = new_movieclip
    set_background_image_by_movieclip(geotracker.camobj,
                                      geotracker.movie_clip)
    return new_movieclip


def _image_format_items(default: str='PNG') -> List[Tuple]:
    if default == 'PNG':
        png_num, jpg_num = 0, 1
    else:
        png_num, jpg_num = 1, 0
    return [
        ('PNG', 'PNG', 'Default image file format with transparency', png_num),
        ('JPEG', 'JPEG', 'Data loss image format without transparency', jpg_num),
    ]


def _orientation_items() -> List[Tuple]:
    return [
        ('NORMAL', 'Normal (do not change)', 'Do not change orientation', 0),
        ('CW', '+90 degree (CW)',
         'Rotate every frame on 90 degree clock-wise', 1),
        ('CCW', '-90 degree (CCW)',
         'Rotate every frame on 90 degree counter clock-wise', 2),
    ]


class GT_OT_SequenceFilebrowser(Operator, ImportHelper):
    bl_idname = GTConfig.gt_sequence_filebrowser_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

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
    filter_movie: BoolProperty(
        name='Filter movie',
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
    filter_movie: BoolProperty(
        name='Filter movie',
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


class GT_OT_SplitVideo(Operator, ExportHelper):
    bl_idname = GTConfig.gt_split_video_to_frames_idname
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

    file_format: EnumProperty(name='Image file format',
                              items=_image_format_items(default='JPEG'),
                              description='Choose image file format')
    quality: IntProperty(name='Image quality', default=100,
                         min=0, max=100)
    from_frame: IntProperty(name='from', default=1)
    to_frame: IntProperty(name='to', default=1)
    filename_ext: StringProperty()

    orientation: EnumProperty(name='Orientation',
                              items=_orientation_items(),
                              description='Change orientation')

    def draw(self, context):
        layout = self.layout
        layout.label(text='Output files format:')
        layout.prop(self, 'file_format', expand=True)
        layout.label(text='Frame range:')
        row = layout.row()
        row.prop(self, 'from_frame', expand=True)
        row.prop(self, 'to_frame', expand=True)
        if self.file_format == 'JPEG':
            layout.prop(self, 'quality', slider=True)

        layout.label(text='Rotation:')
        layout.prop(self, 'orientation', text='')

    def execute(self, context):
        self.filename_ext = '.png' if self.file_format == 'PNG' else '.jpg'
        _log.output(f'OUTPUT filepath: {self.filepath}')

        geotracker = get_current_geotracker_item()
        if not geotracker or not geotracker.movie_clip:
            return {'CANCELLED'}

        orientation = 0
        if self.orientation == 'CW':
            orientation = -1
        elif self.orientation == 'CCW':
            orientation = 1
        output_path = convert_movieclip_to_frames(
            geotracker.movie_clip, self.filepath,
            file_format=self.file_format,
            quality=self.quality,
            start_frame=self.from_frame,
            end_frame=self.to_frame,
            orientation=orientation,
            video_scene_name=Config.kt_convert_video_scene_name)
        _log.output(f'OUTPUT PATH2: {output_path}')
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


class GT_OT_VideoSnapshot(Operator, ExportHelper):
    bl_idname = GTConfig.gt_video_snapshot_idname
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
    filepath: StringProperty(
        default='',
        subtype='FILE_PATH'
    )
    digits: IntProperty(default=4)
    file_format: EnumProperty(name='Image file format',
                              items=_image_format_items(default='JPEG'),
                              description='Choose image file format')
    quality: IntProperty(name='Image quality', default=100, min=0, max=100)
    from_frame: IntProperty(name='from', default=1)
    to_frame: IntProperty(name='to', default=1)
    filename_ext: StringProperty()

    def draw(self, context):
        layout = self.layout
        layout.label(text='Output files format:')
        layout.prop(self, 'file_format', expand=True)
        if self.file_format == 'JPEG':
            layout.prop(self, 'quality', slider=True)

    def invoke(self, context, event):
        self.filepath = str(bpy_current_frame()).zfill(self.digits)
        return super().invoke(context, event)

    def execute(self, context):
        self.filename_ext = '.png' if self.file_format == 'PNG' else '.jpg'
        _log.output(f'OUTPUT filepath: {self.filepath}')

        geotracker = get_current_geotracker_item()
        if not geotracker or not geotracker.movie_clip:
            return {'CANCELLED'}

        current_frame = bpy_current_frame()
        output_path = convert_movieclip_to_frames(
            geotracker.movie_clip, self.filepath,
            file_format=self.file_format,
            quality=self.quality,
            single_frame=True,
            start_frame=current_frame,
            end_frame=current_frame,
            video_scene_name=Config.kt_convert_video_scene_name)
        _log.output(f'OUTPUT PATH: {output_path}')
        return {'FINISHED'}


class GT_OT_ReprojectTextureSequence(Operator, ExportHelper):
    bl_idname = GTConfig.gt_reproject_tex_sequence_idname
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

    filepath: StringProperty(
        default='',
        subtype='FILE_PATH'
    )
    file_format: EnumProperty(name='Image file format',
                              items=_image_format_items(default='PNG'),
                              description='Choose image file format')
    quality: IntProperty(name='Image quality', default=100, min=0, max=100)
    from_frame: IntProperty(name='from', default=1)
    to_frame: IntProperty(name='to', default=1)
    filename_ext: StringProperty()

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

        if self.to_frame < self.from_frame:
            msg = 'Wrong frame range'
            _log.error(msg)
            self.report({'ERROR'}, msg)
            return {'CANCELLED'}
        frames = [x for x in range(self.from_frame, self.to_frame + 1)]
        bake_texture_sequence(context, geotracker, filepath_pattern,
                              frames=frames,
                              file_format=self.file_format,
                              width=self.width, height=self.height)
        return {'FINISHED'}


def _precalc_file_info(layout, geotracker):
    arr = re.split('\r\n|\n', geotracker.precalc_message)
    for txt in arr:
        layout.label(text=txt)


def _draw_precalc_file_info(layout, geotracker):
    if geotracker.precalc_message == '':
        return

    block = layout.column(align=True)
    box = block.box()
    col = box.column()
    col.scale_y = Config.text_scale_y
    col.label(text=geotracker.precalc_path)
    _precalc_file_info(col, geotracker)


class GT_OT_PrecalcInfo(Operator):
    bl_idname = GTConfig.gt_precalc_info_idname
    bl_label = 'Precalc info'
    bl_description = 'Precalc file info'
    bl_options = {'REGISTER', 'INTERNAL', 'UNDO'}

    def draw(self, context):
        layout = self.layout
        geotracker = get_current_geotracker_item()
        if not geotracker:
            return
        layout.label(text='Precalc file info:')
        _draw_precalc_file_info(layout, geotracker)

    def cancel(self, context):
        _log.output('CANCEL PRECALC INFO')

    def execute(self, context):
        _log.output('EXECUTE PRECALC INFO')
        return {'FINISHED'}

    def invoke(self, context, event):
        geotracker = get_current_geotracker_item()
        if not geotracker:
            return {'CANCELLED'}
        geotracker.reload_precalc()
        return context.window_manager.invoke_popup(self, width=350)


class GT_OT_AnalyzeCall(Operator):
    bl_idname = GTConfig.gt_analyze_call_idname
    bl_label = 'Analyze'
    bl_description = 'Call analyze dialog'
    bl_options = {'REGISTER', 'INTERNAL'}

    precalc_start: IntProperty(default=1, name='from',
                               description='starting frame', min=0)
    precalc_end: IntProperty(default=250, name='to',
                             description='ending frame', min=0)

    def check_precalc_range(self) -> bool:
        scene_start = bpy_start_frame()
        scene_end = bpy_end_frame()
        return (self.precalc_start < self.precalc_end) and \
               (scene_start <= self.precalc_start <= scene_end) and \
               (scene_start <= self.precalc_end <= scene_end)

    def _precalc_range_row(self, layout, geotracker):
        row = layout.row()
        row.alert = not self.check_precalc_range()
        row.prop(self, 'precalc_start')
        row.prop(self, 'precalc_end')

    def draw(self, context):
        layout = self.layout
        geotracker = get_current_geotracker_item()
        if not geotracker:
            return
        self._precalc_range_row(layout, geotracker)

    def invoke(self, context, event):
        geotracker = get_current_geotracker_item()
        if not geotracker:
            return {'CANCELLED'}
        if geotracker.precalc_path == '':
            op = get_operator(GTConfig.gt_choose_precalc_file_idname)
            op('INVOKE_DEFAULT')
            return {'FINISHED'}
        self.precalc_start = bpy_start_frame()
        self.precalc_end = bpy_end_frame()
        return context.window_manager.invoke_props_dialog(self)

    def cancel(self, context):
        _log.output('CANCEL ANALYZE')

    def execute(self, context):
        _log.output('START ANALYZE')
        geotracker = get_current_geotracker_item()
        if not geotracker or geotracker.precalc_path == '':
            return {'FINISHED'}

        if self.precalc_start >= self.precalc_end:
            msg = 'Precalc start should be lower than precalc end'
            self.report({'ERROR'}, msg)
            return {'CANCELLED'}

        try:
            geotracker.precalc_start = self.precalc_start
            geotracker.precalc_end = self.precalc_end
            if not os.path.exists(geotracker.precalc_path):
                op = get_operator(GTConfig.gt_create_precalc_idname)
                op('EXEC_DEFAULT')
            else:
                op = get_operator(GTConfig.gt_confirm_recreate_precalc_idname)
                op('INVOKE_DEFAULT')
            return {'FINISHED'}
        except RuntimeError as err:
            _log.error(f'ANALYZE Exception:\n{str(err)}')
            self.report({'ERROR'}, str(err))
        return {'FINISHED'}


class GT_OT_ConfirmRecreatePrecalc(Operator):
    bl_idname = GTConfig.gt_confirm_recreate_precalc_idname
    bl_label = 'Recreate precalc'
    bl_description = 'Are you sure?'
    bl_options = {'REGISTER', 'INTERNAL'}

    def draw(self, context):
        layout = self.layout
        info = ['All your previous precalc data will be lost!',
                'Do you really want to rebuild precalc file?',
                ' ',
                'Click outside of this window to keep old precalc file',
                'or press Ok to start calculation']
        col = layout.column(align=True)
        col.scale_y = Config.text_scale_y
        for txt in info:
            col.label(text=txt)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=400)

    def execute(self, context):
        try:
            op = get_operator(GTConfig.gt_create_precalc_idname)
            op('EXEC_DEFAULT')
        except RuntimeError as err:
            _log.error(f'PRECACLC Exception:\n{str(err)}')
            self.report({'ERROR'}, str(err))
        return {'FINISHED'}
