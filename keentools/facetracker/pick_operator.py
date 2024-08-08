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
                            ft_settings,
                            get_operator,
                            ErrorType,
                            ProductType)
from ..facetracker_config import FTConfig
from ..utils.coords import get_image_space_coord, get_area_region
from ..utils.manipulate import force_undo_push
from ..utils.bpy_common import bpy_view_camera, operator_with_context, bpy_current_frame
from ..blender_independent_packages.pykeentools_loader import module as pkt_module
from .ui_strings import buttons
from ..utils.detect_faces import (get_detected_faces,
                                  set_detected_faces,
                                  sort_detected_faces,
                                  not_enough_face_features_warning)
from ..utils.images import np_array_from_background_image
from ..tracker.tracking_blendshapes import create_relative_shape_keyframe
from ..facetracker.callbacks import recalculate_focal


_log = KTLogger(__name__)


def _init_ft_detected_faces(ft: Any) -> Optional[Any]:
    _log.yellow('_init_ft_detected_faces start')
    settings = _get_settings()
    geotracker = settings.get_current_geotracker_item()
    if not geotracker or not geotracker.camobj:
        return None

    img = np_array_from_background_image(geotracker.camobj)
    if img is None:
        return None

    pixel_aspect_ratio = 1.0
    set_detected_faces(ft.detect_faces(img, pixel_aspect_ratio))

    _log.output('_init_ft_detected_faces end >>>')
    return img


def _get_settings() -> Any:
    return ft_settings()


def _get_loader() -> Any:
    return _get_settings().loader()


def _get_builder() -> Any:
    return _get_loader().kt_geotracker()


def _get_viewport() -> Any:
    return _get_loader().viewport()


def _get_work_area() -> Any:
    return _get_viewport().get_work_area()


def _get_rectangler() -> Any:
    return _get_viewport().rectangler()


def _place_ft_face(rectangle_index: int) -> Optional[bool]:
    _log.yellow(f'_place_ft_face start: r={rectangle_index}')
    faces = get_detected_faces()

    settings = _get_settings()
    geotracker = settings.get_current_geotracker_item()
    if not geotracker:
        _log.error('_place_ft_face: no geotracker')
        return None

    current_frame = bpy_current_frame()
    ft = _get_builder()

    loader = _get_loader()
    loader.safe_keyframe_add(bpy_current_frame(), update=True)
    try:
        result_flag = ft.detect_face_pose(
            current_frame, faces[rectangle_index],
            estimate_focal_length=geotracker.focal_length_estimation,
            throw_if_unlicensed=True)
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
        _log.magenta('_place_ft_face ft.add_preset_pins_and_solve call')
        _log.output(f'\ngeotracker.focal_length_estimation: {geotracker.focal_length_estimation}'
                    f'\ngeotracker.lens_mode: {geotracker.lens_mode}')

        ft.add_preset_pins_and_solve(current_frame)
        recalculate_focal(False)

        _log.output(f'pins\n{[tuple(ft.pin(current_frame, i).img_pos[:]) for i in range(ft.pins_count())]}')

        create_relative_shape_keyframe(current_frame)
        _log.output(f'_place_ft_face kid: {current_frame}')
    else:
        _log.output(f'_place_ft_face failed kid: {current_frame}')

    loader.save_geotracker()
    loader.update_viewport_shaders(adaptive_opacity=True,
                                   wireframe_colors=True,
                                   geomobj_matrix=True,
                                   wireframe=True,
                                   wireframe_data=True,
                                   pins_and_residuals=True,
                                   timeline=True,
                                   tag_redraw=True)

    history_name = 'Add face auto-pins' if result_flag else 'No auto-pins'
    force_undo_push(history_name)
    _log.output('_place_ft_face end >>>')
    return result_flag


class FT_OT_PickMode(Operator):
    bl_idname = FTConfig.ft_pickmode_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'INTERNAL'}

    selected: IntProperty(default=-1)

    def _update_rectangler_shader(self) -> None:
        area = _get_work_area()
        if not area:
            return
        rectangler = _get_rectangler()
        rectangler.prepare_shader_data(area)
        rectangler.create_batch()
        area.tag_redraw()

    def _before_operator_stop(self) -> None:
        _log.yellow('_before_operator_stop start')
        rectangler = _get_rectangler()
        rectangler.clear_rectangles()
        self._update_rectangler_shader()
        self._show_wireframe()
        _log.output('_before_operator_stop end >>>')

    def _selected_rectangle(self, event: Any) -> int:
        area = _get_work_area()
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

        settings = _get_settings()
        if not settings.pinmode:
            self.report({'INFO'}, 'Not in pinmode')
            return {'FINISHED'}

        area = _get_work_area()
        if not area:
            self.report({'INFO'}, 'No proper area found')
            return {'FINISHED'}

        self._update_rectangler_shader()
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
        result = _place_ft_face(self.selected)
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
        area = _get_work_area()

        if event.type == 'WINDOW_DEACTIVATE':
            message = 'Face detection was aborted by context changing'
            self.report({'INFO'}, message)
            _log.red(message)

            self._before_operator_stop()
            _log.output(f'{self.__class__.__name__}.modal 1 end >>>')
            return {'FINISHED'}

        if event.type in {'WHEELDOWNMOUSE', 'WHEELUPMOUSE', 'MIDDLEMOUSE'}:
            self._update_rectangler_shader()
            return {'PASS_THROUGH'}

        if event.type == 'MOUSEMOVE':
            mouse_x, mouse_y = get_image_space_coord(
                event.mouse_region_x, event.mouse_region_y, area)
            index = rectangler.active_rectangle_index(mouse_x, mouse_y)
            rectangler.highlight_rectangle(index,
                                           Config.selected_rectangle_color)
            self._update_rectangler_shader()

        if event.value == 'PRESS' and event.type in {'LEFTMOUSE', 'RIGHTMOUSE'}:
            index = self._selected_rectangle(event)
            if index >= 0:
                result = _place_ft_face(index)
                if result is None:
                    _log.output(f'{self.__class__.__name__}.modal 2 cancelled >>>')
                    return {'CANCELLED'}
                if not result:
                    message = 'A face was chosen but not pinned'
                    _log.output(message)
                    not_enough_face_features_warning()
                else:
                    message = 'A face was chosen and pinned'
                    self.report({'INFO'}, message)
                    _log.output(message)
            else:
                message = 'Face selection was aborted'
                self.report({'INFO'}, message)
                _log.output(message)

            self._before_operator_stop()
            _log.output(f'{self.__class__.__name__}.modal 3 end >>>')
            return {'FINISHED'}

        if event.type == 'ESC' and event.value == 'RELEASE':
            message = 'Face detection was aborted with Esc'
            self.report({'INFO'}, message)
            _log.output(message)

            self._before_operator_stop()
            _log.output(f'{self.__class__.__name__}.modal 4 end >>>')
            return {'FINISHED'}

        if context.space_data.region_3d.view_perspective != 'CAMERA':
            # When camera rotated by user
            if _get_settings().preferences().prevent_fb_view_rotation:
                # Return back to the camera view
                bpy_view_camera()
            else:
                self._before_operator_stop()
                _log.output(f'{self.__class__.__name__}.modal 5 end >>>')
                return {'FINISHED'}

        return {'RUNNING_MODAL'}


class FT_OT_PickModeStarter(Operator):
    bl_idname = FTConfig.ft_pickmode_starter_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'INTERNAL'}

    auto_detect_single: BoolProperty(default=False)
    product: IntProperty(default=ProductType.FACETRACKER)

    def _action(self, invoked: bool=True) -> Set:
        _log.yellow(f'{self.__class__.__name__} _action start')

        settings = _get_settings()
        settings.reload_current_geotracker()
        ft = _get_builder()

        if not ft.is_face_detector_available():
            message = 'Align face is unavailable on your system ' \
                      'because Windows 7 doesn\'t support ' \
                      'ONNX neural network runtime'
            self.report({'ERROR'}, message)
            _log.error(message)
            _log.output(f'{self.__class__.__name__} _action 1 cancelled >>>')
            return {'CANCELLED'}

        img = _init_ft_detected_faces(ft)
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
            result = _place_ft_face(rectangle_index=0)
            if result is None:
                _log.output(f'{self.__class__.__name__} _action 3 cancelled >>>')
                return {'CANCELLED'}
            if not result:
                message = 'A face was detected but not pinned'
                _log.output(message)
                if not self.auto_detect_single:
                    not_enough_face_features_warning()
            else:
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
                                         Config.regular_rectangle_color)
            if invoked:
                area = _get_work_area()
                operator_with_context(get_operator(FTConfig.ft_pickmode_idname),
                                      {'area': area,
                                       'region': get_area_region(area)},
                                      'INVOKE_DEFAULT')
        else:
            message = 'Could not detect a face'
            self.report({'ERROR'}, message)
            _log.error(message)

        _log.output(f'{self.__class__.__name__} _action end >>>')
        return {'FINISHED'}

    def invoke(self, context: Any, event: Any) -> Set:
        _log.green(f'{self.__class__.__name__} invoke')
        settings = _get_settings()
        if not settings.pinmode:
            message = 'Not in pinmode call'
            self.report({'ERROR'}, message)
            _log.error(message)
            return {'CANCELLED'}
        return self._action(invoked=True)

    def execute(self, context: Any) -> Set:  # only for integration testing
        _log.green(f'{self.__class__.__name__} execute')
        return self._action(invoked=False)
