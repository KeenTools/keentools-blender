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

from ...addon_config import Config
from ...geotracker_config import GTConfig, get_gt_settings
from ...utils.images import set_background_image_by_movieclip


def _get_new_movieclip(old_movieclips):
    for movieclip in bpy.data.movieclips:
        if movieclip not in old_movieclips:
            return movieclip
    return None


def _find_movieclip(filepath):
    if not os.path.exists(filepath):
        return None
    for movieclip in bpy.data.movieclips:
        if os.path.samefile(movieclip.filepath, filepath):
            return movieclip
    return None


class GT_OT_MultipleFilebrowser(bpy.types.Operator, ImportHelper):
    bl_idname = GTConfig.gt_multiple_filebrowser_idname
    bl_label = 'Open frame sequence'
    bl_description = 'Load image sequence. ' \
                     'Just select first image in sequence'

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
        col = layout.column()
        col.scale_y = Config.text_scale_y
        col.label(text='Load image sequence. ')
        col.label(text='Just select first image in sequence')

    def execute(self, context):
        logger = logging.getLogger(__name__)
        log_output = logger.info
        log_error = logger.error

        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return {'CANCELLED'}

        frame_files = [{'name': f.name} for f in self.files]
        log_output(f'DIR: {self.directory}')
        log_output(f'FILES: {frame_files}')

        old_movieclips = bpy.data.movieclips[:]
        try:
            bpy.ops.clip.open('EXEC_DEFAULT', files=frame_files, directory=self.directory)
        except RuntimeError as err:
            log_error('MOVIECLIP OPEN ERROR: {}'.format(str(err)))
            return {'CANCELLED'}

        new_movieclip = _get_new_movieclip(old_movieclips)
        if new_movieclip is None:
            log_error('NO NEW MOVIECLIP HAS BEEN CREATED')
            if len(self.files) == 0:
                log_error('NO FILES HAVE BEEN SELECTED')
                return {'CANCELLED'}

            new_movieclip = _find_movieclip(os.path.join(self.directory, self.files[0].name))
            if new_movieclip is None:
                log_error('NO NEW MOVIECLIP IN EXISTING')
                return {'CANCELLED'}
            else:
                log_output(f'EXISTING MOVICLIP HAS BEEN FOUND: {new_movieclip}')

        geotracker.movie_clip = new_movieclip
        set_background_image_by_movieclip(geotracker.camobj,
                                          geotracker.movie_clip)
        log_output(f'LOADED MOVIECLIP: {geotracker.movie_clip.name}')
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
        col = layout.column()
        col.scale_y = Config.text_scale_y
        col.label(text='Choose an existing .precalc file')
        col.label(text='or just enter a name for a new one')

    def execute(self, context):
        logger = logging.getLogger(__name__)
        log_output = logger.debug
        log_error = logger.error
        log_output('PRECALC PATH: {}'.format(self.filepath))

        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            log_error('Current GeoTracker is wrong')
            return {'CANCELLED'}

        if os.path.exists(self.filepath) and os.path.isdir(self.filepath):
            log_error(f'Wrong precalc destination: {self.filepath}')
            self.report({'ERROR'}, 'Wrong precalc destination!')
            return {'CANCELLED'}

        geotracker.precalc_path = self.filepath
        status, msg, _ = geotracker.reload_precalc()
        if not status:
            log_error(msg)
            self.report({'ERROR'}, msg)

        log_output('PRECALC PATH HAS BEEN CHANGED: {}'.format(self.filepath))
        return {'FINISHED'}
