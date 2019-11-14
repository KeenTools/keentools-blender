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
from bpy.props import (
    StringProperty,
    IntProperty,
)
from bpy.types import Operator

from .utils import manipulate, materials
from .config import Config, ErrorType, get_main_settings
from .utils.exif_reader import (read_exif, init_exif_settings, exif_message,
                                get_sensor_size_35mm_equivalent)


class FB_OT_Actor(Operator):
    """ Face Builder Action
    """
    bl_idname = Config.fb_actor_idname
    bl_label = "FaceBuilder in Action"
    bl_options = {'REGISTER'}
    bl_description = "FaceBuilder"

    action: StringProperty(name="Action Name")
    headnum: IntProperty(default=0)
    camnum: IntProperty(default=0)

    def draw(self, context):
        """ No need to show panel so empty draw"""
        pass

    def execute(self, context):
        logger = logging.getLogger(__name__)
        settings = get_main_settings()

        if self.action == 'reconstruct_by_head':
            manipulate.reconstruct_by_head()

        elif self.action == 'force_show_tex':
            mat = materials.show_texture_in_mat(
                Config.tex_builder_filename, Config.tex_builder_matname)
            # Assign Material to Head Object
            materials.assign_mat(
                settings.heads[self.headnum].headobj, mat)
            # Switch to Material Mode or Back
            materials.toggle_mode(('MATERIAL',))

        elif self.action == 'bake_tex':
            materials.bake_tex(self.headnum, Config.tex_builder_filename)
            mat = materials.show_texture_in_mat(
                Config.tex_builder_filename, Config.tex_builder_matname)
            # Assign Material to Head Object
            materials.assign_mat(
                settings.heads[self.headnum].headobj, mat)

        elif self.action == 'unhide_head':
            manipulate.unhide_head(self.headnum)

        elif self.action == 'about_fix_frame_warning':
            warn = getattr(bpy.ops.wm, Config.fb_warning_operator_callname)
            warn('INVOKE_DEFAULT', msg=ErrorType.AboutFrameSize)

        elif self.action == 'use_render_frame_size_scaled':
            # Allow converts scenes pinned on default cameras
            manipulate.use_render_frame_size_scaled()  # disabled in interface

        elif self.action == 'read_file_exif':
            head = settings.heads[self.headnum]
            camera = head.cameras[self.camnum]
            if camera.cam_image is not None:
                exif_data = read_exif(camera.cam_image.filepath)
                init_exif_settings(self.headnum, exif_data)
                message = exif_message(self.headnum, exif_data)
                head.exif.message = message
                self.report({'INFO'}, 'EXIF read success')

        elif self.action == 'delete_camera_image':
            head = settings.heads[self.headnum]
            head.cameras[self.camnum].cam_image = None

        logger.debug("Actor: {}".format(self.action))
        return {'FINISHED'}


class FB_OT_CameraActor(Operator):
    """ Camera Action
    """
    bl_idname = Config.fb_camera_actor_operator_idname
    bl_label = "Action for camera parameters"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Parameters setup"

    action: StringProperty(name="Action Name")
    headnum: IntProperty(default=0)
    camnum: IntProperty(default=0)

    def draw(self, context):
        """ No need to show panel so empty draw"""
        pass

    def execute(self, context):
        logger = logging.getLogger(__name__)
        settings = get_main_settings()
        head = settings.heads[self.headnum]

        if self.action == 'sensor_36x24mm':
            head.sensor_width = 36.0
            head.sensor_height = 24.0

        elif self.action == 'focal_50mm':
            head.focal = 50.0

        elif self.action == 'auto_focal_on':
            head.auto_focal_estimation = True

        elif self.action == 'auto_focal_off':
            head.auto_focal_estimation = False

        elif self.action == 'exif_focal':
            if head.exif.focal > 0.0:
                head.focal = head.exif.focal

        elif self.action == 'exif_focal35mm':
            if head.exif.focal35mm > 0.0:
                head.focal = head.exif.focal35mm

        # ------------------
        # Menu: Sensor Settings
        # ------------------
        elif self.action == 'exif_sensor_and_focal':
            # Get Sensor & Focal from EXIF
            if head.exif.focal > 0.0 and head.exif.sensor_width > 0.0 and \
                    head.exif.sensor_length > 0.0:
                head.focal = head.exif.focal
                head.sensor_width = head.exif.sensor_width
                head.sensor_height = head.exif.sensor_length

        elif self.action == 'exif_focal_and_sensor_via_35mm':
            # Get Sensor & Focal from EXIF 35mm equiv.
            if head.exif.focal > 0.0 and head.exif.focal35mm > 0.0:
                w, h = get_sensor_size_35mm_equivalent(head)
                head.sensor_width = w
                head.sensor_height = h
                head.focal = head.exif.focal

        elif self.action == 'standard_sensor_and_exif_focal35mm':
            # 35 mm Sensor & EXIF Focal 35mm equiv.
            if head.exif.focal35mm > 0.0:
                w = 36.0
                h = 24.0
                head.sensor_width = w
                head.sensor_height = h
                head.focal = head.exif.focal35mm

        # ------------------
        elif self.action == 'exif_sensor':
            # EXIF --> Sensor Size
            if head.exif.sensor_width > 0.0 and head.exif.sensor_length > 0.0:
                head.sensor_width = head.exif.sensor_width
                head.sensor_height = head.exif.sensor_length

        elif self.action == 'exif_sensor_via_35mm':
            # EXIF 35mm --> calc. Sensor Size
            if head.exif.focal35mm > 0.0:
                w, h = get_sensor_size_35mm_equivalent(head)
                head.sensor_width = w
                head.sensor_height = h

        logger.debug("Camera Actor: {}".format(self.action))
        return {'FINISHED'}
