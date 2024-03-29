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

from typing import Any, Optional, List, Tuple, Set

from bpy.types import Operator, Area
from bpy.props import IntProperty, BoolProperty

from ..utils.kt_logging import KTLogger
from ..addon_config import (Config,
                            fb_settings,
                            get_operator,
                            ErrorType,
                            ProductType)
from ..facebuilder_config import FBConfig
from ..utils.coords import update_head_mesh_non_neutral, get_image_space_coord
from ..utils.focal_length import configure_focal_mode_and_fixes
from .utils.manipulate import push_head_in_undo_history
from ..utils.images import load_rgba
from ..utils.bpy_common import bpy_view_camera
from ..blender_independent_packages.pykeentools_loader import module as pkt_module
from .ui_strings import buttons
from ..utils.detect_faces import (get_detected_faces,
                                  set_detected_faces,
                                  sort_detected_faces,
                                  not_enough_face_features_warning)


_log = KTLogger(__name__)


def _init_fb_detected_faces(fb: Any, headnum: int, camnum: int) -> Optional[Any]:
    _log.yellow('_init_fb_detected_faces start')
    settings = fb_settings()
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
    pixel_aspect_ratio = fb.pixel_aspect_ratio(camera.get_keyframe())
    set_detected_faces(fb.detect_faces(img, pixel_aspect_ratio))

    _log.output('_init_fb_detected_faces end >>>')
    return img


def _get_settings() -> Any:
    return fb_settings()


def _get_loader() -> Any:
    return _get_settings().loader()


def _get_builder() -> Any:
    return _get_loader().get_builder()


def _get_viewport() -> Any:
    return _get_loader().viewport()


def _get_rectangler() -> Any:
    return _get_viewport().rectangler()


def _add_pins_to_face(headnum: int, camnum: int, rectangle_index: int,
                      area: Any) -> Optional[bool]:
    _log.yellow(f'_add_pins_to_face start: r={rectangle_index}')
    faces = get_detected_faces()

    settings = _get_settings()
    head = settings.get_head(headnum)
    camera = head.get_camera(camnum)
    kid = camera.get_keyframe()

    fb = _get_builder()
    fb.set_use_emotions(head.should_use_emotions())
    configure_focal_mode_and_fixes(fb, head)

    try:
        result_flag = fb.detect_face_pose(kid, faces[rectangle_index])
    except pkt_module().UnlicensedException as err:
        _log.error(f'UnlicensedException _add_pins_to_face\n{str(err)}')
        warn = get_operator(Config.kt_warning_idname)
        warn('INVOKE_DEFAULT', msg=ErrorType.NoLicense)
        return None
    except Exception as err:
        _log.error(f'UNKNOWN EXCEPTION detect_face_pose '
                   f'in _add_pins_to_face\n{str(err)}')
        return None

    if result_flag:
        fb.remove_pins(kid)
        fb.add_preset_pins_and_solve(kid)
        update_head_mesh_non_neutral(fb, head)
        _log.output(f'auto_pins_added kid: {kid}')
    else:
        _log.output(f'detect_face_pose failed kid: {kid}')

    loader = _get_loader()
    loader.update_camera_pins_count(headnum, camnum)
    loader.load_pins_into_viewport(headnum, camnum)
    loader.update_all_camera_positions(headnum)
    loader.update_all_camera_focals(headnum)
    loader.update_fb_viewport_shaders(area=area,
                                      headnum=headnum, camnum=camnum,
                                      camera_pos=True, wireframe=True,
                                      pins_and_residuals=True)
    loader.save_fb_serial_and_image_pathes(headnum)

    history_name = 'Add face auto-pins' if result_flag else 'No auto-pins'
    push_head_in_undo_history(head, history_name)
    _log.output('_add_pins_to_face end >>>')
    return result_flag


class FB_OT_PickMode(Operator):
    bl_idname = FBConfig.fb_pickmode_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'INTERNAL'}

    headnum: IntProperty(default=0)
    camnum: IntProperty(default=0)
    selected: IntProperty(default=-1)

    def _init_rectangler(self, area: Area) -> None:
        _log.yellow('_init_rectangler start')
        rectangler = _get_rectangler()
        rectangler.prepare_shader_data(area)
        rectangler.create_batch()
        vp = _get_viewport()
        vp.create_batch_2d(area)
        _log.output('_init_rectangler end >>>')

    def _update_rectangler_shader(self, area: Area) -> None:
        _log.yellow('_update_rectangler_shader start')
        rectangler = _get_rectangler()
        rectangler.prepare_shader_data(area)
        rectangler.create_batch()
        area.tag_redraw()
        _log.output('_update_rectangler_shader end >>>')

    def _before_operator_stop(self, area: Area) -> None:
        _log.yellow('_before_operator_stop start')
        rectangler = _get_rectangler()
        rectangler.clear_rectangles()
        self._update_rectangler_shader(area)
        self._show_wireframe()
        _log.output('_before_operator_stop end >>>')

    def _selected_rectangle(self, area: Area, event: Any) -> int:
        rectangler = _get_rectangler()
        mouse_x, mouse_y = get_image_space_coord(event.mouse_region_x,
                                                 event.mouse_region_y, area)
        return rectangler.active_rectangle_index(mouse_x, mouse_y)

    def _hide_wireframe(self) -> None:
        _log.yellow('_hide_wireframe start')
        vp = _get_viewport()
        vp.wireframer().hide_shader()
        vp.points2d().hide_shader()
        vp.points3d().hide_shader()
        vp.residuals().hide_shader()
        _log.output('_hide_wireframe end >>>')

    def _show_wireframe(self) -> None:
        _log.yellow('_show_wireframe start')
        vp = _get_viewport()
        vp.wireframer().unhide_shader()
        vp.points2d().unhide_shader()
        vp.points3d().unhide_shader()
        vp.residuals().unhide_shader()
        _log.output('_show_wireframe end >>>')

    def invoke(self, context: Any, event: Any) -> Set:
        _log.green(f'{self.__class__.__name__}.invoke start')

        settings = fb_settings()
        if not settings.pinmode:
            self.report({'INFO'}, 'Not in pinmode')
            return {'FINISHED'}

        self._init_rectangler(context.area)
        self._hide_wireframe()

        context.window_manager.modal_handler_add(self)
        _log.output(f'{self.__class__.__name__}.invoke end >>>')
        return {'RUNNING_MODAL'}

    def execute(self, context: Any) -> Set:  # Testing purpose only
        _log.green(f'{self.__class__.__name__}.execute start')
        if self.selected < 0:
            message = 'No selected rectangle index'
            self.report({'ERROR'}, message)
            _log.error(message)
            return {'CANCELLED'}
        result = _add_pins_to_face(self.headnum, self.camnum, self.selected, context)
        if result is None:
            return {'CANCELLED'}
        if not result:
            message = '_add_pins_to_face fail'
            self.report({'INFO'}, message)
            _log.error(message)
        else:
            message = '_add_pins_to_face success'
            self.report({'INFO'}, message)
            _log.output(message)

        _log.output(f'{self.__class__.__name__}.execute end >>>')
        return {'FINISHED'}

    def modal(self, context: Any, event: Any) -> Set:
        rectangler = _get_rectangler()
        area = context.area

        if event.type == 'WINDOW_DEACTIVATE':
            message = 'Face detection was aborted by context changing'
            self.report({'INFO'}, message)
            _log.output(message)

            self._before_operator_stop(area)
            return {'FINISHED'}

        if event.type in {'WHEELDOWNMOUSE', 'WHEELUPMOUSE', 'MIDDLEMOUSE'}:
            self._update_rectangler_shader(area)
            return {'PASS_THROUGH'}

        if event.type == 'MOUSEMOVE':
            mouse_x, mouse_y = get_image_space_coord(
                event.mouse_region_x, event.mouse_region_y, area)
            index = rectangler.active_rectangle_index(mouse_x, mouse_y)
            rectangler.highlight_rectangle(index,
                                           FBConfig.selected_rectangle_color)
            self._update_rectangler_shader(area)

        if event.value == 'PRESS' and event.type in {'LEFTMOUSE', 'RIGHTMOUSE'}:
            index = self._selected_rectangle(area, event)
            if index >= 0:
                result = _add_pins_to_face(self.headnum, self.camnum,
                                           index, area)
                if result is None:
                    return {'CANCELLED'}
                if not result:
                    message = 'A face was chosen but not pinned'
                    _log.output(message)
                    not_enough_face_features_warning()
                else:
                    head = fb_settings().get_head(self.headnum)
                    head.mark_model_changed_by_pinmode()

                    message = 'A face was chosen and pinned'
                    self.report({'INFO'}, message)
                    _log.output(message)
            else:
                message = 'Face selection was aborted'
                self.report({'INFO'}, message)
                _log.output(message)

            self._before_operator_stop(context.area)
            return {'FINISHED'}

        if event.type == 'ESC' and event.value == 'RELEASE':
            message = 'Face detection was aborted with Esc'
            self.report({'INFO'}, message)
            _log.output(message)

            self._before_operator_stop(context.area)
            return {'FINISHED'}

        # Prevent camera rotation by user
        if context.space_data.region_3d.view_perspective != 'CAMERA':
            bpy_view_camera()

        return {'RUNNING_MODAL'}


class FB_OT_PickModeStarter(Operator):
    bl_idname = FBConfig.fb_pickmode_starter_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'INTERNAL'}

    headnum: IntProperty(default=0)
    camnum: IntProperty(default=0)

    auto_detect_single: BoolProperty(default=False)
    product: IntProperty(default=ProductType.FACEBUILDER)

    def _action(self, context: Any, event: Any, invoked: bool=True) -> Set:
        _log.yellow(f'{self.__class__.__name__} _action start')

        loader = _get_loader()
        loader.load_model(self.headnum)
        fb = _get_builder()

        if not fb.is_face_detector_available():
            message = 'Align face is unavailable on your system ' \
                      'because Windows 7 doesn\'t support ' \
                      'ONNX neural network runtime'
            self.report({'ERROR'}, message)
            _log.error(message)
            _log.output(f'{self.__class__.__name__} _action 1 cancelled >>>')
            return {'CANCELLED'}

        img = _init_fb_detected_faces(fb, self.headnum, self.camnum)
        if img is None:
            message = 'Face detection failed because of a corrupted image'
            self.report({'ERROR'}, message)
            _log.error(message)
            _log.output(f'{self.__class__.__name__} _action 2 cancelled >>>')
            return {'CANCELLED'}

        h, w, _ = img.shape
        rects = sort_detected_faces()

        rectangler = _get_rectangler()
        rectangler.clear_rectangles()

        if len(rects) == 1:
            result = _add_pins_to_face(self.headnum, self.camnum,
                                       rectangle_index=0, area=context.area)
            if result is None:
                _log.output(f'{self.__class__.__name__} _action 3 cancelled >>>')
                return {'CANCELLED'}
            if not result:
                message = 'A face was detected but not pinned'
                _log.output(message)
                if not self.auto_detect_single:
                    not_enough_face_features_warning()
            else:
                head = fb_settings().get_head(self.headnum)
                head.mark_model_changed_by_pinmode()

                message = 'A face was detected and pinned'
                self.report({'INFO'}, message)
                _log.output(message)

            _log.output(f'{self.__class__.__name__} _action 1 end >>>')
            return {'FINISHED'}

        if self.auto_detect_single:
            _log.output(f'{self.__class__.__name__} _action 4 cancelled >>>')
            return {'CANCELLED'}

        if len(rects) > 1:
            for x1, y1, x2, y2, _ in rects:
                rectangler.add_rectangle(x1, y1, x2, y2, w, h,
                                         FBConfig.regular_rectangle_color)
            if invoked:
                op = get_operator(FBConfig.fb_pickmode_idname)
                op('INVOKE_DEFAULT', headnum=self.headnum, camnum=self.camnum)
        else:
            message = 'Could not detect a face'
            self.report({'ERROR'}, message)
            _log.error(message)

        _log.output(f'{self.__class__.__name__} _action end >>>')
        return {'FINISHED'}

    def invoke(self, context: Any, event: Any) -> Set:
        _log.green(f'{self.__class__.__name__} invoke')
        settings = fb_settings()
        if not settings.pinmode:
            message = 'Not in pinmode call'
            self.report({'ERROR'}, message)
            _log.error(message)
            return {'CANCELLED'}
        return self._action(context, event, invoked=True)

    def execute(self, context: Any) -> Set:  # Used only for integration testing
        _log.green(f'{self.__class__.__name__} execute')
        return self._action(context, event=None, invoked=False)
