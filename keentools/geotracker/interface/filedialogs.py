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

import logging
import os

import bpy
from bpy_extras.io_utils import ImportHelper, ExportHelper

from ...geotracker_config import GTConfig, get_gt_settings
from ...utils.images import set_background_image_by_movieclip
from ..utils.tracking import reload_precalc


def _get_last_movieclip():
    if len(bpy.data.movieclips) > 0:
        return bpy.data.movieclips[-1]
    return None


class GT_OT_MultipleFilebrowser(bpy.types.Operator, ImportHelper):
    bl_idname = GTConfig.gt_multiple_filebrowser_idname
    bl_label = 'Open frame sequence'
    bl_description = 'Load images. ' \
                     'You can select multiple images at once'

    filter_glob: bpy.props.StringProperty(
        default='*.jpg;*.jpeg;*.png;*.tif;*.tiff;*.bmp;',  # *.mp4',
        options={'HIDDEN'}
    )

    files: bpy.props.CollectionProperty(
        name='File Path',
        type=bpy.types.OperatorFileListElement,
    )

    directory: bpy.props.StringProperty(
            subtype='DIR_PATH',
    )

    num: bpy.props.IntProperty(name='Geotracker Index')

    def draw(self, context):
        layout = self.layout
        layout.label(text='Load images for sequence. ')
        layout.label(text='You can select multiple images at once')

    def execute(self, context):
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return {'CANCELLED'}

        logger = logging.getLogger(__name__)
        log_output = logger.debug
        log_output(f'DIR: {self.directory}')

        frame_files = [{'name': f.name} for f in self.files]
        log_output(f'FILES: {frame_files}')

        old_last_movieclip = _get_last_movieclip()
        try:
            bpy.ops.clip.open('EXEC_DEFAULT', files=frame_files, directory=self.directory)
        except RuntimeError as err:
            logger.error('MOVIECLIP OPEN ERROR: {}'.format(str(err)))
            return {'CANCELLED'}

        last_movieclip = _get_last_movieclip()
        if last_movieclip is None or last_movieclip is old_last_movieclip:
            return {'CANCELLED'}

        geotracker.movie_clip = last_movieclip
        set_background_image_by_movieclip(geotracker.camobj,
                                          geotracker.movie_clip)

        return {'FINISHED'}


class GT_OT_ChoosePrecalcFile(bpy.types.Operator, ExportHelper):
    bl_idname = GTConfig.gt_choose_precalc_file_idname
    bl_label = 'Set precalc file'
    bl_description = 'Choose an existing .precalc file ' \
                     'or just enter a name for a new one'
    bl_options = {'REGISTER', 'INTERNAL'}

    filter_glob: bpy.props.StringProperty(
        default='*.precalc',
        options={'HIDDEN'}
    )

    check_existing: bpy.props.BoolProperty(
        name='Check Existing',
        description='Check and warn on overwriting existing files',
        default=True,
        options={'HIDDEN'},
    )

    filename_ext: bpy.props.StringProperty(default='.precalc')

    filepath: bpy.props.StringProperty(
        default=GTConfig.default_precalc_filename,
        subtype='FILE_PATH'
    )

    def check(self, context):
        change_ext = False

        filepath = self.filepath
        sp = os.path.splitext(filepath)

        if sp[1] in {'.precalc', '.'}:
            filepath = sp[0]

        filepath = bpy.path.ensure_ext(filepath, self.filename_ext)

        if filepath != self.filepath:
            self.filepath = filepath
            change_ext = True

        return change_ext

    def draw(self, context):
        layout = self.layout
        layout.label(text='Choose an existing .precalc file')
        layout.label(text='or just enter a name for a new one')

    def execute(self, context):
        logger = logging.getLogger(__name__)
        logger.debug('PRECALC PATH: {}'.format(self.filepath))

        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return {'CANCELLED'}

        if os.path.exists(self.filepath) and os.path.isdir(self.filepath):
            self.report({'ERROR'}, 'Wrong precalc destination!')
            return {'CANCELLED'}

        geotracker.precalc_path = self.filepath
        status, msg = reload_precalc(geotracker)
        if not status:
            self.report({'ERROR'}, msg)

        logger.debug('PRECALC PATH HAS BEEN CHANGED: {}'.format(self.filepath))
        return {'FINISHED'}
