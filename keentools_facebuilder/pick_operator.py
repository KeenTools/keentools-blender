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
import logging
import bpy

from .config import Config, get_main_settings, get_operator
from .fbloader import FBLoader
from .utils import coords


_DETECTED_FACES = None


def _get_np_image(headnum, camnum):
    settings = get_main_settings()
    head = settings.get_head(headnum)
    camera = head.get_camera(camnum)

    image = camera.cam_image
    w, h = image.size[:2]
    return np.asarray(image.pixels[:]).reshape((h, w, 4))


def _get_detected_faces():
    global _DETECTED_FACES
    return _DETECTED_FACES


def _set_detected_faces(img):
    global _DETECTED_FACES
    fb = FBLoader.get_builder()
    _DETECTED_FACES = fb.detect_faces(img)


def _get_detected_faces_rectangles():
    faces = _get_detected_faces()
    rects = []
    for i, face in enumerate(faces):
        x1, y1 = face.xy_min
        x2, y2 = face.xy_max
        if x2 < x1:
            x1, x2 = x2, x1
        if y2 < y1:
            y1, y2 = y2, y1
        rects.append((x1, y1, x2, y2, i))
    return rects


def _sort_detected_faces():
    global _DETECTED_FACES
    rects = _get_detected_faces_rectangles()
    rects.sort(key=lambda x: x[0])  # order by x1
    _DETECTED_FACES = [_DETECTED_FACES[x[4]] for x in rects]
    return rects


def _reset_detected_faces():
    global _DETECTED_FACES
    _DETECTED_FACES = None


def _add_pins_to_face(headnum, camnum, index):
    logger = logging.getLogger(__name__)
    fb = FBLoader.get_builder()
    faces = _get_detected_faces()

    settings = get_main_settings()
    kid = settings.get_keyframe(headnum, camnum)

    fb.remove_pins(kid)
    fb.detect_face_pose(kid, faces[index])
    fb.add_preset_pins(kid)
    logger.debug('auto_pins_added kid: {}'.format(kid))
    FBLoader.save_only(headnum)

    FBLoader.fb_redraw(headnum, camnum)
    FBLoader.update_pins_count(headnum, camnum)
    FBLoader.update_all_camera_positions(headnum)
    FBLoader.update_all_camera_focals(headnum)


class FB_OT_PickMode(bpy.types.Operator):
    bl_idname = Config.fb_pickmode_idname
    bl_label = 'FaceBuilder Pick Face mode'
    bl_description = 'Operator for in-Viewport picking'
    bl_options = {'REGISTER', 'UNDO'}

    headnum: bpy.props.IntProperty(default=0)
    camnum: bpy.props.IntProperty(default=0)

    def _init_rectangler(self, context):
        vp = FBLoader.viewport()
        rectangler = vp.rectangler()
        rectangler.prepare_shader_data(context)
        rectangler.create_batch()
        vp.create_batch_2d(context)

    def invoke(self, context, event):
        logger = logging.getLogger(__name__)
        logger.debug('PickMode call')

        settings = get_main_settings()
        if not settings.pinmode:
            self.report({'INFO'}, 'Not in pinmode')
            return {'FINISHED'}

        self._init_rectangler(context)

        context.window_manager.modal_handler_add(self)
        logger.debug('PICKMODE STARTED')
        return {'RUNNING_MODAL'}

    def _get_rectangler(self):
        return FBLoader.viewport().rectangler()

    def _update_rectangler_shader(self, context):
        rectangler = self._get_rectangler()
        rectangler.prepare_shader_data(context)
        rectangler.create_batch()
        context.area.tag_redraw()

    def _before_operator_stop(self, context):
        logger = logging.getLogger(__name__)
        logger.debug('_before_operator_stop')
        rectangler = self._get_rectangler()
        rectangler.clear_rectangles()
        self._update_rectangler_shader(context)

    def _selected_rectangle(self, context, event):
        rectangler = self._get_rectangler()
        mouse_x, mouse_y = coords.get_image_space_coord(
            event.mouse_region_x, event.mouse_region_y, context)
        return rectangler.active_rectangle_index(mouse_x, mouse_y)

    def modal(self, context, event):
        logger = logging.getLogger(__name__)
        vp = FBLoader.viewport()
        rectangler = vp.rectangler()

        if event.type == 'WINDOW_DEACTIVATE':
            self._before_operator_stop(context)
            return {'FINISHED'}

        if event.type in {'WHEELDOWNMOUSE', 'WHEELUPMOUSE', 'MIDDLEMOUSE'}:
            self._update_rectangler_shader(context)
            return {'PASS_THROUGH'}

        if event.type == 'MOUSEMOVE':
            mouse_x, mouse_y = coords.get_image_space_coord(
                event.mouse_region_x, event.mouse_region_y, context)
            index = rectangler.active_rectangle_index(mouse_x, mouse_y)
            logger.debug('active_rectangle_index: {}'.format(index))
            rectangler.highlight_rectangle(index,
                                           Config.selected_rectangle_color)
            self._update_rectangler_shader(context)

        if event.type == 'ESC':
            message = 'Operator stopped by ESC'
            self.report({'INFO'}, message)
            logger.debug(message)

            self._before_operator_stop(context)
            return {'FINISHED'}

        if event.value == 'PRESS' and event.type in {'LEFTMOUSE', 'RIGHTMOUSE'}:
            message = 'Rectangle selected'
            self.report({'INFO'}, message)
            logger.debug(message)

            index = self._selected_rectangle(context, event)
            if index >= 0:
                _add_pins_to_face(self.headnum, self.camnum, index)

            self._before_operator_stop(context)
            return {'FINISHED'}

        return {'RUNNING_MODAL'}


class FB_OT_PickModeStarter(bpy.types.Operator):
    bl_idname = Config.fb_pickmode_starter_idname
    bl_label = 'FaceBuilder Pick Face mode starter'
    bl_description = 'Operator for in-Viewport picking'
    bl_options = {'REGISTER', 'UNDO'}

    headnum: bpy.props.IntProperty(default=0)
    camnum: bpy.props.IntProperty(default=0)

    def invoke(self, context, event):
        logger = logging.getLogger(__name__)
        logger.debug('PickModeStarter call')

        settings = get_main_settings()
        if not settings.pinmode:
            self.report({'INFO'}, 'Not in pinmode')
            return {'FINISHED'}

        img = _get_np_image(self.headnum, self.camnum)
        h, w, _ = img.shape

        _set_detected_faces(img)
        rects = _sort_detected_faces()

        vp = FBLoader.viewport()
        rectangler = vp.rectangler()
        rectangler.clear_rectangles()

        if len(rects) > 1:
            for x1, y1, x2, y2, _ in rects:
                rectangler.add_rectangle(x1, y1, x2, y2, w, h,
                                         Config.regular_rectangle_color)

            op = get_operator(Config.fb_pickmode_idname)
            op('INVOKE_DEFAULT', headnum=self.headnum, camnum=self.camnum)
        elif len(rects) == 1:
            _add_pins_to_face(self.headnum, self.camnum, 0)
        else:
            self.report({'ERROR'}, 'Cannot find face on image')

        return {'FINISHED'}
