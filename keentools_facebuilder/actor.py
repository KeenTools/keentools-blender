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

from .utils import manipulate
from .config import Config, get_main_settings
from .utils.exif_reader import (get_sensor_size_35mm_equivalent,
                                update_image_groups)


class FB_OT_Actor(Operator):
    bl_idname = Config.fb_actor_idname
    bl_label = "FaceBuilder in Action"
    bl_options = {'REGISTER'}
    bl_description = "FaceBuilder"

    action: StringProperty(name="Action Name")
    headnum: IntProperty(default=0)
    camnum: IntProperty(default=0)
    num: IntProperty(default=0)

    def draw(self, context):
        pass

    def execute(self, context):
        logger = logging.getLogger(__name__)
        logger.debug("Actor: {}".format(self.action))

        if self.action == 'reconstruct_by_head':
            manipulate.reconstruct_by_head()

        elif self.action == 'unhide_head':
            manipulate.unhide_head(self.headnum)

        elif self.action == 'use_render_frame_size_scaled':
            # Allow converts scenes pinned on default cameras
            manipulate.use_render_frame_size_scaled()  # disabled in interface

        elif self.action == 'group':
            pass

        elif self.action == 'show_groups_info':
            settings = get_main_settings()
            head = settings.get_head(self.headnum)
            head.show_image_groups = not head.show_image_groups

        elif self.action == 'manual_mode':
            settings = get_main_settings()
            head = settings.get_head(self.headnum)
            head.auto_focal_estimation = not head.auto_focal_estimation

        elif self.action == 'reset_image_group':
            settings = get_main_settings()
            head = settings.get_head(settings.current_headnum)
            camera = head.get_camera(settings.current_camnum)
            camera.image_group = 0
            update_image_groups(head)

        elif self.action == 'new_image_group':
            settings = get_main_settings()
            head = settings.get_head(settings.current_headnum)
            camera = head.get_camera(settings.current_camnum)
            groups = [x.image_group for x in head.cameras]
            if len(groups) > 0:
                camera.image_group = max(groups) + 1
            else:
                camera.image_group = 1
            # update_image_groups(head)

        elif self.action == 'to_image_group':
            settings = get_main_settings()
            head = settings.get_head(settings.current_headnum)
            camera = head.get_camera(settings.current_camnum)
            camera.image_group = self.num
            # update_image_groups(head)

        elif self.action == 'make_unique':
            settings = get_main_settings()
            head = settings.get_head(settings.current_headnum)
            camera = head.get_camera(settings.current_camnum)
            camera.image_group = -1
            # update_image_groups(head)

        elif self.action == 'reset_all_image_groups':
            settings = get_main_settings()
            head = settings.get_head(settings.current_headnum)
            for camera in head.cameras:
                camera.image_group = 0
            update_image_groups(head)

        return {'FINISHED'}


class FB_OT_CameraActor(Operator):
    """ Camera Action
    """
    bl_idname = Config.fb_camera_actor_idname
    bl_label = "Camera parameters"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}
    bl_description = "Parameters setup"

    action: StringProperty(name="Action Name")
    headnum: IntProperty(default=0)
    camnum: IntProperty(default=0)

    def draw(self, context):
        pass

    def execute(self, context):
        logger = logging.getLogger(__name__)
        settings = get_main_settings()

        head = settings.get_head(self.headnum)

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
