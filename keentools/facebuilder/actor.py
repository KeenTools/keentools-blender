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

import numpy as np

import bpy
from bpy.props import StringProperty, IntProperty
from mathutils import Vector, Matrix
from math import radians

from ..utils.kt_logging import KTLogger
from .utils.manipulate import get_current_head
from ..utils.coords import xy_to_xz_rotation_matrix_4x4
from ..addon_config import fb_settings, get_operator
from ..facebuilder_config import FBConfig
from ..facebuilder.utils.exif_reader import auto_setup_camera_from_exif
from ..utils.blendshapes import (create_blendshape_controls,
                                 make_control_panel,
                                 convert_controls_animation_to_blendshapes,
                                 remove_blendshape_drivers,
                                 delete_with_children,
                                 select_control_panel_sliders,
                                 has_blendshapes_action,
                                 convert_blendshapes_animation_to_controls)
from .ui_strings import buttons
from .fbloader import FBLoader
from ..utils.coords import xz_to_xy_rotation_matrix_4x4


_log = KTLogger(__name__)


class FB_OT_HistoryActor(bpy.types.Operator):
    bl_idname = FBConfig.fb_history_actor_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'UNDO'}

    action: StringProperty(name='Action Name')

    def draw(self, context):
        pass

    def execute(self, context):
        _log.output(f'History Actor: {self.action}')

        if self.action == 'generate_control_panel':
            head = get_current_head()
            if head:
                controls = create_blendshape_controls(head.headobj)
                if len(controls) > 0:
                    control_panel = make_control_panel(controls)
                    # Positioning control panel near head
                    offset = np.eye(4)
                    offset[3][0] = 2 * head.model_scale # Step on X
                    rot = xy_to_xz_rotation_matrix_4x4()
                    control_panel.matrix_world = offset @ rot @ \
                        np.array(head.headobj.matrix_world).transpose()

                    # Hide dashed lines between parented objects
                    bpy.context.space_data.overlay.show_relationship_lines = False
                    head.headobj.data.update()  # update for drivers affection

                    head.blendshapes_control_panel = control_panel
                    if has_blendshapes_action(head.headobj):
                        convert_blendshapes_animation_to_controls(head.headobj)
                else:
                    self.report({'ERROR'}, 'No Blendshapes found. '
                                           'Create blendshapes first')
                return {'FINISHED'}

        elif self.action == 'delete_control_panel':
            head = get_current_head()
            if head and head.control_panel_exists():
                remove_blendshape_drivers(head.headobj)
                delete_with_children(head.blendshapes_control_panel)
            else:
                self.report({'ERROR'}, 'Control panel not found')
            return {'FINISHED'}

        elif self.action == 'select_control_panel_sliders':
            head = get_current_head()
            if head and head.control_panel_exists():
                counter = select_control_panel_sliders(
                    head.blendshapes_control_panel)
                self.report(
                    {'INFO'}, '{} Sliders has been selected'.format(counter))
            else:
                self.report({'ERROR'}, 'Control panel not found')
            return {'FINISHED'}

        elif self.action == 'convert_controls_to_blendshapes':
            head = get_current_head()
            if head and head.control_panel_exists():
                if not convert_controls_animation_to_blendshapes(head.headobj):
                    self.report({'ERROR'}, 'Conversion could not be performed')
                else:
                    remove_blendshape_drivers(head.headobj)
                    delete_with_children(head.blendshapes_control_panel)
                    self.report({'INFO'}, 'Conversion completed')
            else:
                self.report({'ERROR'}, 'Control panel not found')
            return {'FINISHED'}

        return {'CANCELLED'}


class FB_OT_CameraActor(bpy.types.Operator):
    bl_idname = FBConfig.fb_camera_actor_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    action: StringProperty(name="Action Name")
    headnum: IntProperty(default=0)
    camnum: IntProperty(default=0)
    num: IntProperty(default=0)

    def draw(self, context):
        pass

    def execute(self, context):
        _log.output(f'Camera Actor: {self.action}')
        _log.output(f'headnum: {self.headnum} camnum: {self.camnum} '
                    f'num: {self.num}')

        settings = fb_settings()
        head = settings.get_head(self.headnum)
        camera = head.get_camera(settings.current_camnum)

        if self.action == 'settings_by_exif':
            auto_setup_camera_from_exif(camera)

        elif self.action == 'reset_all_camera_settings':
            for camera in head.cameras:
                auto_setup_camera_from_exif(camera)

        elif self.action == 'reset_view':
            op = get_operator(FBConfig.fb_reset_expression_idname)
            op('INVOKE_DEFAULT', headnum=self.headnum, camnum=self.camnum)

            op = get_operator(FBConfig.fb_center_geo_idname)
            op('INVOKE_DEFAULT', headnum=self.headnum, camnum=self.camnum)

            op = get_operator(FBConfig.fb_remove_pins_idname)
            op('INVOKE_DEFAULT', headnum=self.headnum, camnum=self.camnum)

            # -----
            vp = FBLoader.viewport()
            vp.update_wireframe_colors()
            wf = vp.wireframer()
            fb = FBLoader.get_builder()
            wf.init_wireframe_image(fb, settings.show_specials)

            keyframe = head.get_keyframe(settings.current_camnum)
            wf.init_edge_indices(fb)

            wf.set_object_world_matrix(head.headobj.matrix_world)
            camobj = head.get_camera(settings.current_camnum).camobj
            wf.set_camera_pos(camobj, head.headobj)
            geo = fb.applied_args_model_at(keyframe)
            wf.init_geom_data_from_core(*FBLoader.get_geo_shader_data(geo))

            wf.create_batches()
            # -----

        elif self.action == 'rotate_forward':
            op = get_operator(FBConfig.fb_remove_pins_idname)
            op('INVOKE_DEFAULT', headnum=self.headnum, camnum=self.camnum)
            head_mat = head.headobj.matrix_world
            camera_mat = camera.camobj.matrix_world
            rot_mat = Matrix.Rotation(radians(-90.0), 4, 'Z')
            camera.camobj.matrix_world = head_mat @ rot_mat @ head_mat.inverted() @ camera_mat

            fb = FBLoader.get_builder()
            mat = np.array(camera.camobj.matrix_world.inverted() @ head_mat, dtype=np.float32) @ xz_to_xy_rotation_matrix_4x4()
            fb.update_model_mat(camera.get_keyframe(), mat)
            FBLoader.save_fb_serial_and_image_pathes(self.headnum)

            # -----
            vp = FBLoader.viewport()
            vp.update_wireframe_colors()
            wf = vp.wireframer()
            fb = FBLoader.get_builder()
            wf.init_wireframe_image(fb, settings.show_specials)

            keyframe = head.get_keyframe(settings.current_camnum)
            wf.init_edge_indices(fb)

            wf.set_object_world_matrix(head.headobj.matrix_world)
            camobj = head.get_camera(settings.current_camnum).camobj
            wf.set_camera_pos(camobj, head.headobj)
            geo = fb.applied_args_model_at(keyframe)
            wf.init_geom_data_from_core(*FBLoader.get_geo_shader_data(geo))

            wf.create_batches()
            # -----

        elif self.action == 'rotate_backward':
            op = get_operator(FBConfig.fb_remove_pins_idname)
            op('INVOKE_DEFAULT', headnum=self.headnum, camnum=self.camnum)
            head_mat = head.headobj.matrix_world
            camera_mat = camera.camobj.matrix_world
            rot_mat = Matrix.Rotation(radians(90.0), 4, 'Z')
            camera.camobj.matrix_world = head_mat @ rot_mat @ head_mat.inverted() @ camera_mat

            fb = FBLoader.get_builder()
            mat = np.array(camera.camobj.matrix_world.inverted() @ head_mat, dtype=np.float32) @ xz_to_xy_rotation_matrix_4x4()
            fb.update_model_mat(camera.get_keyframe(), mat)
            FBLoader.save_fb_serial_and_image_pathes(self.headnum)

            # -----
            vp = FBLoader.viewport()
            vp.update_wireframe_colors()
            wf = vp.wireframer()
            fb = FBLoader.get_builder()
            wf.init_wireframe_image(fb, settings.show_specials)

            keyframe = head.get_keyframe(settings.current_camnum)
            wf.init_edge_indices(fb)

            wf.set_object_world_matrix(head.headobj.matrix_world)
            camobj = head.get_camera(settings.current_camnum).camobj
            wf.set_camera_pos(camobj, head.headobj)
            geo = fb.applied_args_model_at(keyframe)
            wf.init_geom_data_from_core(*FBLoader.get_geo_shader_data(geo))

            wf.create_batches()
            # -----

        return {'FINISHED'}
