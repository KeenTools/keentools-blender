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

from . utils import manipulate, materials
from . config import Config, ErrorType, get_main_settings


class OBJECT_OT_FBActor(Operator):
    """ Face Builder Action
    """
    bl_idname = Config.fb_actor_operator_idname
    bl_label = "FaceBuilder in Action"
    bl_options = {'REGISTER'}
    bl_description = "FaceBuilder"

    action: StringProperty(name="Action Name")
    headnum: IntProperty(default=0)
    camnum: IntProperty(default=0)

    tex_name = Config.tex_builder_filename
    mat_name = Config.tex_builder_matname

    def draw(self, context):
        """ No need to show panel so empty draw"""
        pass

    def execute(self, context):
        logger = logging.getLogger(__name__)
        if self.action == "reconstruct_by_head":
            manipulate.reconstruct_by_head()

        elif self.action == 'show_tex':
            settings = get_main_settings()
            mat = materials.show_texture_in_mat(self.tex_name, self.mat_name)
            # Assign Material to Head Object
            materials.assign_mat(
                settings.heads[settings.current_headnum].headobj, mat)
            # Switch to Material Mode or Back
            materials.toggle_mode(('SOLID', 'MATERIAL'))

        elif self.action == 'bake_tex':
            settings = get_main_settings()
            materials.bake_tex(self.headnum, self.tex_name)
            mat = materials.show_texture_in_mat(self.tex_name, self.mat_name)
            # Assign Material to Head Object
            materials.assign_mat(
                settings.heads[settings.current_headnum].headobj, mat)

        elif self.action == "unhide_head":
            manipulate.unhide_head(self.headnum)

        elif self.action == "about_fix_frame_warning":
            warn = getattr(bpy.ops.wm, Config.fb_warning_operator_callname)
            warn('INVOKE_DEFAULT', msg=ErrorType.AboutFrameSize)

        elif self.action == "auto_detect_frame_size":
            manipulate.auto_detect_frame_size()

        elif self.action == 'use_render_frame_size':
            manipulate.use_render_frame_size()

        elif self.action == 'use_camera_frame_size':
            # Current camera Background --> Render size (by Fix button)
            settings = get_main_settings()
            manipulate.use_camera_frame_size(
                settings.current_headnum, settings.current_camnum)

        elif self.action == 'use_this_camera_frame_size':
            # Current camera Background --> Render size (by mini-button)
            settings = get_main_settings()
            manipulate.use_camera_frame_size(
                settings.tmp_headnum, settings.tmp_camnum)

        elif self.action == 'use_render_frame_size_scaled':
            # Allow converts scenes pinned on default cameras
            manipulate.use_render_frame_size_scaled()  # disabled in interface

        logger.debug("Actor: {}".format(self.action))

        return {'FINISHED'}
