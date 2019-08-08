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
from .config import config, get_main_settings, ErrorType


class WM_OT_FBOpenFilebrowser(Operator, ImportHelper):
    """ Open selected image sequence as cameras """

    bl_idname = config.fb_filedialog_operator_idname
    bl_label = "Open Image(s)"

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

    def draw(self, context):
        layout = self.layout
        layout.label(text='Update Scene Render Size')
        layout.prop(self, 'update_render_size', expand=True)

        txt = ['All frames for FaceBuilder',
               'should have the same size.',
               'So Update option is the best choice',
               'for standard workflow. [Update]',
               'changes Render Size of your Scene!']
        for t in txt:
            layout.label(text=t)

    def execute(self, context):
        """ Selected files processing"""
        logger = logging.getLogger(__name__)
        settings = get_main_settings()
        if len(settings.heads) <= self.headnum:
            op = getattr(bpy.ops.wm, config.fb_warning_operator_callname)
            op('INVOKE_DEFAULT', msg=ErrorType.IllegalIndex)
            return {'CANCELLED'}
        # if Settings structure is broken
        if not settings.check_heads_and_cams():
            settings.fix_heads()  # Fix

        directory = self.directory

        changes = 0
        w = -1
        h = -1
        for f in self.files:
            filepath = os.path.join(directory, f.name)
            logger.debug("FILE: {}".format(filepath))
            img = FBLoader.add_camera_image(self.headnum, filepath)
            if img.size[0] != w or img.size[1] != h:
                w, h = img.size
                changes += 1

        if self.update_render_size == 'yes' and changes == 1:

            render = bpy.context.scene.render
            render.resolution_x = w
            render.resolution_y = h
            settings.frame_width = w
            settings.frame_height = h

        return {'FINISHED'}
