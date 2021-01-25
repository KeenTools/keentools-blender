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

from .config import Config, get_main_settings
from .fbloader import FBLoader
from .utils import coords


class FB_OT_PickMode(bpy.types.Operator):
    bl_idname = Config.fb_pickmode_idname
    bl_label = 'FaceBuilder Pick Face mode'
    bl_description = 'Operator for in-Viewport picking'
    bl_options = {'REGISTER', 'UNDO'}

    def invoke(self, context, event):
        logger = logging.getLogger(__name__)
        logger.debug('PickMode call')

        settings = get_main_settings()
        if not settings.pinmode:
            self.report({'INFO'}, 'Not in pinmode')
            return {'FINISHED'}

        vp = FBLoader.viewport()
        rectangler = vp.rectangler()
        rectangler.clear_rectangles()

        rectangler.add_rectangle(
            20, 20, 960, 1060, 1920, 1080,
            (0.0, 0.5, 0.0, 0.8)
        )

        rectangler.add_rectangle(
            960, 20, 1900, 1060, 1920, 1080,
            (0.0, 0.0, 0.5, 0.8)
        )

        rectangler.prepare_data(context)
        rectangler.create_batch()
        vp.create_batch_2d(context)

        context.window_manager.modal_handler_add(self)
        logger.debug('PICKMODE STARTED')
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        print('MODAL PICKMODE: ', event.type)
        if event.type == 'MOUSEMOVE':
            mouse_x, mouse_y = coords.get_image_space_coord(event.mouse_region_x, event.mouse_region_y, context)
            vp = FBLoader.viewport()
            rectangler = vp.rectangler()
            rectangler.active_rectangle(mouse_x, mouse_y, (1.0, 0.0, 0.0, 1.0))
            rectangler.prepare_data(context)
            rectangler.create_batch()
            context.area.tag_redraw()
        logger = logging.getLogger(__name__)
        if event.type == 'ESC':
            self.report({'INFO'}, 'Operator finish')
            return {'FINISHED'}
        if event.value == 'PRESS' and event.type == 'LEFTMOUSE':
            self.report({'INFO'}, 'Operator result selected')
            return {'FINISHED'}
        return {'PASS_THROUGH'}
