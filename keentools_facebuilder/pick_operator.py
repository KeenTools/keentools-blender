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

from .config import Config, ErrorType, get_main_settings, get_operator
from .fbloader import FBLoader
from .utils import coords
from .utils.focal_length import configure_focal_mode_and_fixes
from .utils.manipulate import push_head_in_undo_history
from .utils.images import load_rgba
from .blender_independent_packages.pykeentools_loader import module as pkt_module


_DETECTED_FACES = []


def reset_detected_faces():
    global _DETECTED_FACES
    _DETECTED_FACES = []


def get_detected_faces():
    global _DETECTED_FACES
    return _DETECTED_FACES


def _set_detected_faces(faces_info):
    global _DETECTED_FACES
    _DETECTED_FACES = faces_info
    logger = logging.getLogger(__name__)
    logger.debug('_DETECTED_FACES: {}'.format(len(_DETECTED_FACES)))


def _get_detected_faces_rectangles():
    faces = get_detected_faces()
    logger = logging.getLogger(__name__)
    logger.debug('_get_detected_faces: {}'.format(faces))
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


def init_detected_faces(fb, headnum, camnum):
    settings = get_main_settings()
    head = settings.get_head(headnum)
    if head is None:
        return None
    camera = head.get_camera(camnum)
    if camera is None:
        return None
    img = load_rgba(camera)
    if img is None:
        return None

    fb.set_use_emotions(head.should_use_emotions())
    _set_detected_faces(fb.detect_faces(img))

    return img


def sort_detected_faces():
    faces = get_detected_faces()
    rects = _get_detected_faces_rectangles()
    logger = logging.getLogger(__name__)
    logger.debug('RECTS BEFORE: {}'.format(rects))
    rects.sort(key=lambda x: x[0])  # order by x1
    logger.debug('RECTS AFTER: {}'.format(rects))
    _set_detected_faces([faces[x[4]] for x in rects])
    return rects


def _add_pins_to_face(headnum, camnum, rectangle_index, context):
    logger = logging.getLogger(__name__)
    fb = FBLoader.get_builder()
    faces = get_detected_faces()

    settings = get_main_settings()
    head = settings.get_head(headnum)
    camera = head.get_camera(camnum)
    kid = camera.get_keyframe()

    fb.set_use_emotions(head.should_use_emotions())
    configure_focal_mode_and_fixes(fb, head)

    try:
        result_flag = fb.detect_face_pose(kid, faces[rectangle_index])
    except pkt_module().UnlicensedException:
        logger.error('UnlicensedException _add_pins_to_face')
        warn = get_operator(Config.fb_warning_idname)
        warn('INVOKE_DEFAULT', msg=ErrorType.NoLicense)
        return None
    except Exception as err:
        logger.error('UNKNOWN EXCEPTION detect_face_pose in _add_pins_to_face')
        logger.error('Exception info: {}'.format(str(err)))
        return None

    if result_flag:
        fb.remove_pins(kid)
        fb.add_preset_pins(kid)
        coords.update_head_mesh_non_neutral(fb, head)
        logger.debug('auto_pins_added kid: {}'.format(kid))
    else:
        logger.debug('detect_face_pose failed kid: {}'.format(kid))

    FBLoader.update_camera_pins_count(headnum, camnum)
    FBLoader.load_pins_into_viewport(headnum, camnum)
    FBLoader.update_all_camera_positions(headnum)
    FBLoader.update_all_camera_focals(headnum)
    FBLoader.update_viewport_shaders(context, headnum, camnum)

    FBLoader.save_fb_serial_and_image_pathes(headnum)

    history_name = 'Add face auto-pins' if result_flag else 'No auto-pins'
    push_head_in_undo_history(head, history_name)
    return result_flag


def _not_enough_face_features_warning():
    error_message = 'Sorry, could not find enough facial features \n' \
                    'to pin the model! Please try pinning the model manually.'
    warn = get_operator(Config.fb_warning_idname)
    warn('INVOKE_DEFAULT', msg=ErrorType.CustomMessage,
         msg_content=error_message)
    logger = logging.getLogger(__name__)
    logger.error('could not find enough facial features')


class FB_OT_PickMode(bpy.types.Operator):
    bl_idname = Config.fb_pickmode_idname
    bl_label = 'FaceBuilder Pick Face mode'
    bl_description = 'Modal Operator for Pick Face mode'
    bl_options = {'REGISTER', 'INTERNAL'}

    headnum: bpy.props.IntProperty(default=0)
    camnum: bpy.props.IntProperty(default=0)
    selected: bpy.props.IntProperty(default=-1)

    def _init_rectangler(self, context):
        vp = FBLoader.viewport()
        rectangler = vp.rectangler()
        rectangler.prepare_shader_data(context)
        rectangler.create_batch()
        vp.create_batch_2d(context)

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
        self._show_wireframe()

    def _selected_rectangle(self, context, event):
        rectangler = self._get_rectangler()
        mouse_x, mouse_y = coords.get_image_space_coord(
            event.mouse_region_x, event.mouse_region_y, context)
        return rectangler.active_rectangle_index(mouse_x, mouse_y)

    def _hide_wireframe(self):
        vp = FBLoader.viewport()
        vp.wireframer().hide_shader()
        vp.points2d().hide_shader()
        vp.points3d().hide_shader()
        vp.residuals().hide_shader()

    def _show_wireframe(self):
        vp = FBLoader.viewport()
        vp.wireframer().unhide_shader()
        vp.points2d().unhide_shader()
        vp.points3d().unhide_shader()
        vp.residuals().unhide_shader()

    def invoke(self, context, event):
        logger = logging.getLogger(__name__)
        logger.debug('PickMode invoke call')

        settings = get_main_settings()
        if not settings.pinmode:
            self.report({'INFO'}, 'Not in pinmode')
            return {'FINISHED'}

        self._init_rectangler(context)
        self._hide_wireframe()

        context.window_manager.modal_handler_add(self)
        logger.debug('PICKMODE STARTED')
        return {'RUNNING_MODAL'}

    def execute(self, context):  # Testing purpose only
        logger = logging.getLogger(__name__)
        logger.debug('PickMode execute call')
        if self.selected < 0:
            message = 'No selected rectangle index'
            self.report({'ERROR'}, message)
            logger.error(message)
            return {'CANCELLED'}
        result = _add_pins_to_face(self.headnum, self.camnum, self.selected, context)
        if result is None:
            return {'CANCELLED'}
        if not result:
            message = '_add_pins_to_face fail'
            self.report({'INFO'}, message)
            logger.error(message)
        else:
            message = '_add_pins_to_face success'
            self.report({'INFO'}, message)
            logger.debug(message)

        return {'FINISHED'}

    def modal(self, context, event):
        logger = logging.getLogger(__name__)
        vp = FBLoader.viewport()
        rectangler = vp.rectangler()

        if event.type == 'WINDOW_DEACTIVATE':
            message = 'Face detection was aborted by context changing'
            self.report({'INFO'}, message)
            logger.debug(message)

            self._before_operator_stop(context)
            return {'FINISHED'}

        if event.type in {'WHEELDOWNMOUSE', 'WHEELUPMOUSE', 'MIDDLEMOUSE'}:
            self._update_rectangler_shader(context)
            return {'PASS_THROUGH'}

        if event.type == 'MOUSEMOVE':
            mouse_x, mouse_y = coords.get_image_space_coord(
                event.mouse_region_x, event.mouse_region_y, context)
            index = rectangler.active_rectangle_index(mouse_x, mouse_y)
            rectangler.highlight_rectangle(index,
                                           Config.selected_rectangle_color)
            self._update_rectangler_shader(context)

        if event.value == 'PRESS' and event.type in {'LEFTMOUSE', 'RIGHTMOUSE'}:
            index = self._selected_rectangle(context, event)
            if index >= 0:
                result = _add_pins_to_face(self.headnum, self.camnum, index,
                                           context)
                if result is None:
                    return {'CANCELLED'}
                if not result:
                    message = 'A face was chosen but not pinned'
                    logger.debug(message)
                    _not_enough_face_features_warning()
                else:
                    head = get_main_settings().get_head(self.headnum)
                    head.mark_model_changed_by_pinmode()

                    message = 'A face was chosen and pinned'
                    self.report({'INFO'}, message)
                    logger.debug(message)
            else:
                message = 'Face selection was aborted'
                self.report({'INFO'}, message)
                logger.debug(message)

            self._before_operator_stop(context)
            return {'FINISHED'}

        if event.type == 'ESC' and event.value == 'RELEASE':
            message = 'Face detection was aborted with Esc'
            self.report({'INFO'}, message)
            logger.debug(message)

            self._before_operator_stop(context)
            return {'FINISHED'}

        # Prevent camera rotation by user
        if context.space_data.region_3d.view_perspective != 'CAMERA':
            bpy.ops.view3d.view_camera()

        return {'RUNNING_MODAL'}


class FB_OT_PickModeStarter(bpy.types.Operator):
    bl_idname = Config.fb_pickmode_starter_idname
    bl_label = 'FaceBuilder Pick Face mode starter'
    bl_description = 'Detect a face on the photo ' \
                     'and pin the model to the selected face'
    bl_options = {'REGISTER', 'INTERNAL'}

    headnum: bpy.props.IntProperty(default=0)
    camnum: bpy.props.IntProperty(default=0)

    def _action(self, context, event, invoked=True):
        logger = logging.getLogger(__name__)
        logger.debug('PickModeStarter action call')

        FBLoader.load_model(self.headnum)
        fb = FBLoader.get_builder()

        if not fb.is_face_detector_available():
            message = 'Face detector is not available'
            self.report({'ERROR'}, message)
            logger.error(message)
            return {'CANCELLED'}

        img = init_detected_faces(fb, self.headnum, self.camnum)
        if img is None:
            message = 'Face detection failed because of a corrupted image'
            self.report({'ERROR'}, message)
            logger.error(message)
            return {'CANCELLED'}

        h, w, _ = img.shape
        rects = sort_detected_faces()

        vp = FBLoader.viewport()
        rectangler = vp.rectangler()
        rectangler.clear_rectangles()

        if len(rects) > 1:
            for x1, y1, x2, y2, _ in rects:
                rectangler.add_rectangle(x1, y1, x2, y2, w, h,
                                         Config.regular_rectangle_color)
            if invoked:
                op = get_operator(Config.fb_pickmode_idname)
                op('INVOKE_DEFAULT', headnum=self.headnum, camnum=self.camnum)
        elif len(rects) == 1:
            result = _add_pins_to_face(self.headnum, self.camnum,
                                       rectangle_index=0, context=context)
            if result is None:
                return {'CANCELLED'}
            if not result:
                message = 'A face was detected but not pinned'
                logger.debug(message)
                _not_enough_face_features_warning()
            else:
                head = get_main_settings().get_head(self.headnum)
                head.mark_model_changed_by_pinmode()

                message = 'A face was detected and pinned'
                self.report({'INFO'}, message)
                logger.debug(message)
        else:
            message = 'Could not detect a face'
            self.report({'ERROR'}, message)
            logger.error(message)

        return {'FINISHED'}

    def invoke(self, context, event):
        logger = logging.getLogger(__name__)
        logger.debug('PickModeStarter invoke call')
        settings = get_main_settings()
        if not settings.pinmode:
            message = 'Not in pinmode call'
            self.report({'ERROR'}, message)
            logger.error(message)
            return {'CANCELLED'}
        return self._action(context, event, invoked=True)

    def execute(self, context):  # Used only for integration testing
        logger = logging.getLogger(__name__)
        logger.debug('PickModeStarter execute call')
        return self._action(context, event=None, invoked=False)
