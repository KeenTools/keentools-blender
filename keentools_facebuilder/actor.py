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
import math
import numpy as np


import bpy
from bpy.props import (
    StringProperty,
    IntProperty,
)

from .utils import manipulate
from .config import Config, get_main_settings, get_operators, ErrorType
from .utils.exif_reader import (update_image_groups,
                                auto_setup_camera_from_exif,
                                is_size_compatible_with_group)
from .utils.blendshapes import (default_blendshape_names,
                                create_fake_blendshapes,
                                create_blendshape_controls,
                                make_control_panel,
                                convert_control_animation_to_blendshape,
                                remove_blendshape_drivers,
                                delete_with_children)


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
        logger.debug('headnum: {} camnum: {} num: {}'.format(
            self.headnum, self.camnum, self.num))

        if self.action == 'reconstruct_by_head':
            manipulate.reconstruct_by_head()

        elif self.action == 'unhide_head':
            manipulate.unhide_head(self.headnum)

        elif self.action == 'generate_facs_blendshapes':
            head = manipulate.get_current_head()
            if head:
                counter = create_fake_blendshapes(head.headobj,
                                                  default_blendshape_names())
                self.report({'INFO'}, '{} Blendshapes created'.format(counter))

        elif self.action == 'generate_control_panel':
            head = manipulate.get_current_head()
            if head:
                controls = create_blendshape_controls(head.headobj)
                if len(controls) > 0:
                    control_panel = make_control_panel(controls)
                    # Positioning control panel near head
                    offset = np.eye(4)
                    offset[3][0] = 2  # Step on X
                    rot = np.array([[1., 0., 0., 0.],
                                    [0., 0., 1., 0.],
                                    [0., -1., 0., 0.],
                                    [0., 0., 0., 1.]])
                    control_panel.matrix_world = offset @ rot @ \
                        np.array(head.headobj.matrix_world).transpose()

                    # Hide dashed lines between parented objects
                    bpy.context.space_data.overlay.show_relationship_lines = False
                    head.headobj.data.update()  # update for drivers affection

                    head.blendshapes_control_panel = control_panel
                else:
                    self.report({'ERROR'}, 'No Blendshapes found. '
                                           'Create blendshapes first')

        elif self.action == 'load_csv_animation':
            headnum = manipulate.get_current_headnum()
            if headnum >= 0:
                op = getattr(get_operators(),
                             Config.fb_animation_filebrowser_callname)
                op('INVOKE_DEFAULT', headnum=headnum)

        elif self.action == 'convert_controls_to_blendshapes':
            head = manipulate.get_current_head()
            if head and head.control_panel_exists():
                if not convert_control_animation_to_blendshape(head.headobj):
                    self.report({'ERROR'}, 'Conversion could not be performed')
                else:
                    remove_blendshape_drivers(head.headobj)
                    delete_with_children(head.blendshapes_control_panel)
                    self.report({'INFO'}, 'Conversion completed')
            else:
                self.report({'ERROR'}, 'Control panel not found')

        elif self.action == 'delete_control_panel':
            head = manipulate.get_current_head()
            if head and head.control_panel_exists():
                remove_blendshape_drivers(head.headobj)
                delete_with_children(head.blendshapes_control_panel)
            else:
                self.report({'ERROR'}, 'Control panel not found')

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
        logger.debug('headnum: {} camnum: {} num: {}'.format(
            self.headnum, self.camnum, self.num))

        settings = get_main_settings()
        head = settings.get_head(self.headnum)
        camera = head.get_camera(settings.current_camnum)

        if self.action == 'toggle_group_info':
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
            head.show_image_groups = True

        elif self.action == 'to_image_group':
            if is_size_compatible_with_group(head, camera, self.num):
                camera.image_group = self.num
                head.show_image_groups = True
            else:
                error_message = "Wrong Image Size\n\n" \
                    "This image {} can't be added into group {} \n" \
                    "because they have different " \
                    "dimensions.".format(camera.get_image_name(), self.num)

                warn = getattr(get_operators(), Config.fb_warning_callname)
                warn('INVOKE_DEFAULT', msg=ErrorType.CustomMessage,
                     msg_content=error_message)

        elif self.action == 'make_unique':
            camera.image_group = -1
            head.show_image_groups = True

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
