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

from .utils import manipulate
from .config import Config, get_main_settings
from .utils.exif_reader import (get_sensor_size_35mm_equivalent,
                                update_image_groups,
                                auto_setup_camera_from_exif)


class FB_OT_Actor(bpy.types.Operator):
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

        return {'FINISHED'}


class FB_OT_CameraActor(bpy.types.Operator):
    bl_idname = Config.fb_camera_actor_idname
    bl_label = "Camera parameters"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}
    bl_description = "Parameters setup"

    action: StringProperty(name="Action Name")
    headnum: IntProperty(default=0)
    camnum: IntProperty(default=0)
    num: IntProperty(default=0)

    def draw(self, context):
        pass

    def execute(self, context):
        logger = logging.getLogger(__name__)
        logger.debug('Camera Actor: {}'.format(self.action))

        settings = get_main_settings()
        head = settings.get_head(self.headnum)
        camera = head.get_camera(settings.current_camnum)

        if self.action == 'show_groups_info':
            head.show_image_groups = not head.show_image_groups

        elif self.action == 'manual_mode':
            head.smart_mode_toggle()

        elif self.action == 'reset_image_group':
            camera.image_group = 0
            update_image_groups(head)

        elif self.action == 'new_image_group':
            groups = [x.image_group for x in head.cameras if x.image_group > 0]
            if len(groups) > 0:
                camera.image_group = max(groups) + 1
            else:
                camera.image_group = 1

        elif self.action == 'to_image_group':
            camera.image_group = self.num

        elif self.action == 'make_unique':
            camera.image_group = -1

        elif self.action == 'make_all_unique':
            for camera in head.cameras:
                camera.image_group = -1

        elif self.action == 'reset_all_image_groups':
            for camera in head.cameras:
                camera.image_group = 0
            update_image_groups(head)

        elif self.action == 'settings_by_exif':
            camera.image_group = 0
            auto_setup_camera_from_exif(camera)
            update_image_groups(head)

        elif self.action == 'reset_all_camera_settings':
            for camera in head.cameras:
                camera.image_group = 0
                auto_setup_camera_from_exif(camera)
            if not head.smart_mode():
                head.smart_mode_toggle()
            update_image_groups(head)

        return {'FINISHED'}
