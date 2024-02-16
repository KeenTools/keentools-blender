# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2019-2023  KeenTools

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

from typing import Any, Set, Tuple, List

import bpy
from bpy.types import Area

from ..utils.kt_logging import KTLogger
from ..geotracker_config import GTConfig
from ..utils.coords import (get_image_space_coord,
                            image_space_to_frame,
                            nearest_point,
                            point_is_in_area,
                            point_is_in_service_region,
                            change_near_and_far_clip_planes,
                            focal_mm_to_px,
                            camera_focal_length,
                            camera_sensor_width)
from ..utils.manipulate import force_undo_push
from ..utils.bpy_common import (bpy_current_frame,
                                bpy_set_current_frame,
                                get_scene_camera_shift,
                                bpy_render_frame,
                                bpy_is_animation_playing)
from ..geotracker.interface.screen_mesages import (revert_default_screen_message,
                                                   clipping_changed_screen_message)


_log = KTLogger(__name__)


class MovePin(bpy.types.Operator):
    @classmethod
    def get_settings(cls) -> Any:
        assert False, 'MovePin: get_settings'

    def _move_pin_mode_on(self) -> None:
        settings = self.get_settings()
        settings.loader().viewport().pins().set_move_pin_mode(True)

    def _move_pin_mode_off(self) -> None:
        settings = self.get_settings()
        settings.loader().viewport().pins().set_move_pin_mode(False)

    def _before_operator_finish(self) -> None:
        self._move_pin_mode_off()

    def _new_pin(self, area: Area, mouse_x: float, mouse_y: float) -> bool:
        frame = bpy_current_frame()
        shift_x, shift_y = get_scene_camera_shift()
        x, y = get_image_space_coord(mouse_x, mouse_y, area, shift_x, shift_y)

        settings = self.get_settings()
        loader = settings.loader()
        pin = loader.add_pin(
            frame, (image_space_to_frame(x, y, shift_x, shift_y)))
        _log.output(f'_new_pin pin: {pin}')
        pins = loader.viewport().pins()
        if not pin:
            _log.output('_new_pin MISS MODEL')
            pins.reset_current_pin()
            return False
        else:
            pins.add_pin((x, y))
            pins.set_current_pin_num_to_last()
            _log.output(f'_new_pin ADD PIN pins: {pins.arr()}')
            return True

    def init_action(self, context: Any, mouse_x: float, mouse_y: float) -> bool:
        def _enable_pin_safe(gt, keyframe, pin_index):
            pin = gt.pin(keyframe, pin_index)
            if pin and not pin.enabled:
                gt.pin_enable(keyframe, pin_index, True)

        settings = self.get_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker or not geotracker.geomobj or not geotracker.camobj:
            return False

        self.new_pin_flag = False

        loader = settings.loader()
        vp = loader.viewport()
        vp.update_view_relative_pixel_size(context.area)
        pins = vp.pins()

        loader.load_pins_into_viewport()

        x, y = get_image_space_coord(mouse_x, mouse_y, context.area,
                                     *get_scene_camera_shift())
        pins.set_current_pin((x, y))

        nearest, dist2 = nearest_point(x, y, pins.arr())

        if nearest >= 0 and dist2 < vp.tolerance_dist2():
            _log.output(f'init_action PIN FOUND: {nearest}')
            pins.set_current_pin_num(nearest)
            gt = loader.kt_geotracker()
            keyframe = bpy_current_frame()
            if not nearest in pins.get_selected_pins():
                pins.set_selected_pins([nearest])
            for i in pins.get_selected_pins():
                _enable_pin_safe(gt, keyframe, i)
        else:
            self.new_pin_flag = self._new_pin(context.area, mouse_x, mouse_y)
            if not self.new_pin_flag:
                _log.output('GT MISS MODEL CLICK')
                pins.clear_selected_pins()
                return False

            pins.set_selected_pins([pins.current_pin_num()])
            _log.output('GT NEW PIN CREATED')

        vp.create_batch_2d(context.area)
        vp.register_handlers(context)
        return True

    def update_focal_length_in_all_keyframes(self) -> None:
        settings = self.get_settings()
        geotracker = settings.get_current_geotracker_item()
        if geotracker.focal_length_mode != 'STATIC_FOCAL_LENGTH':
            return
        new_focal_length = focal_mm_to_px(
            camera_focal_length(geotracker.camobj),
            *bpy_render_frame(), camera_sensor_width(geotracker.camobj))

        _log.output(_log.color('red', f'old: {self.old_focal_length} '
                                      f'new: {new_focal_length}'))

        if self.old_focal_length != new_focal_length:
            current_frame = bpy_current_frame()
            settings.calculating_mode = 'ESTIMATE_FL'
            gt = settings.loader().kt_geotracker()
            gt.recalculate_model_for_new_focal_length(self.old_focal_length,
                                                      new_focal_length, False,
                                                      current_frame)
            bpy_set_current_frame(current_frame)
            settings.stop_calculating()
            _log.output('FOCAL LENGTH CHANGED')

    def update_wireframe(self):
        pass

    def on_left_mouse_release(self, area: Area) -> Set:
        def _push_action_in_undo_history() -> None:
            if self.new_pin_flag:
                force_undo_push('Add GeoTracker pin')
                self.new_pin_flag = False
            else:
                force_undo_push('Drag GeoTracker pin')

        settings = self.get_settings()
        loader = settings.loader()
        loader.viewport().pins().reset_current_pin()

        self.update_on_left_mouse_release()

        if self.dragged:
            self.update_focal_length_in_all_keyframes()
            loader.spring_pins_back()
        loader.save_geotracker()

        self._before_operator_finish()

        if not bpy_is_animation_playing() \
                and not settings.is_calculating():
            settings.stabilize_viewport(reset=True)

        loader.update_viewport_shaders(area, wireframe=True,
                                       geomobj_matrix=True,
                                       pins_and_residuals=True,
                                       timeline=True)
        loader.viewport_area_redraw()

        _push_action_in_undo_history()
        return {'FINISHED'}

    def update_on_left_mouse_release(self) -> None:
        pass

    def _pin_drag(self, kid: int, area: Area, mouse_x: float, mouse_y: float) -> bool:
        def _drag_multiple_pins(kid: int, pin_index: int,
                                selected_pins: List[int]) -> None:
            settings = self.get_settings()
            loader = settings.loader()
            gt = loader.kt_geotracker()
            old_x, old_y = gt.pin(kid, pin_index).img_pos
            new_x, new_y = image_space_to_frame(x, y, *get_scene_camera_shift())
            offset = (new_x - old_x, new_y - old_y)
            loader.delta_move_pin(kid, selected_pins, offset)
            loader.load_pins_into_viewport()

        settings = self.get_settings()
        loader = settings.loader()
        shift_x, shift_y = get_scene_camera_shift()
        x, y = get_image_space_coord(mouse_x, mouse_y, area, shift_x, shift_y)
        pins = loader.viewport().pins()
        pins.set_current_pin((x, y))
        pin_index = pins.current_pin_num()
        pins.arr()[pin_index] = (x, y)
        selected_pins = pins.get_selected_pins()

        loader.safe_keyframe_add(kid)

        if len(selected_pins) == 1:
            loader.move_pin(kid, pin_index, (x, y), shift_x, shift_y)
            return loader.solve()

        _drag_multiple_pins(kid, pin_index, selected_pins)
        return loader.solve()

    def on_mouse_move(self, area: Area, mouse_x: float, mouse_y: float) -> Set:
        settings = self.get_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return self.on_default_modal()

        product = settings.product_type()
        frame = bpy_current_frame()

        if not self._pin_drag(frame, area, mouse_x, mouse_y):
            self._before_operator_finish()
            return {'FINISHED'}

        self.dragged = True
        loader = settings.loader()
        vp = loader.viewport()

        loader.place_object_or_camera()
        if GTConfig.auto_increase_far_clip_distance and geotracker.camobj and \
                change_near_and_far_clip_planes(geotracker.camobj, geotracker.geomobj,
                                                prev_clip_start=self.camera_clip_start,
                                                prev_clip_end=self.camera_clip_end):
            near = geotracker.camobj.data.clip_start
            far = geotracker.camobj.data.clip_end
            if near == self.camera_clip_start and far == self.camera_clip_end:
                revert_default_screen_message(product=product)
            else:
                clipping_changed_screen_message(near, far, product=product)

        self.update_wireframe()

        gt = loader.kt_geotracker()
        vp.update_surface_points(gt, geotracker.geomobj, frame)

        wf = vp.wireframer()
        wf.set_object_world_matrix(geotracker.geomobj.matrix_world)
        wf.set_lit_light_matrix(geotracker.geomobj.matrix_world,
                                geotracker.camobj.matrix_world)

        vp.create_batch_2d(area)
        vp.update_residuals(gt, area, frame)
        vp.tag_redraw()
        return self.on_default_modal()

    def on_default_modal(self) -> Set:
        settings = self.get_settings()
        if settings.loader().viewport().pins().current_pin() is not None:
            return {'RUNNING_MODAL'}
        else:
            _log.output('MOVE PIN FINISH')
            self._before_operator_finish()
            return {'FINISHED'}

    def invoke(self, context: Any, event: Any) -> Set:
        _log.output('GT MOVEPIN invoke')
        self.dragged = False
        settings = self.get_settings()
        loader = settings.loader()
        area = loader.get_work_area()
        mouse_x, mouse_y = event.mouse_region_x, event.mouse_region_y
        if not point_is_in_area(context.area, mouse_x, mouse_y):
            _log.output(f'OUT OF AREA: {mouse_x}, {mouse_y}')
            return {'CANCELLED'}
        if point_is_in_service_region(area, mouse_x, mouse_y):
            _log.output(f'OUT OF SAFE REGION: {mouse_x}, {mouse_y}')
            return {'CANCELLED'}

        if not self.init_action(context, mouse_x, mouse_y):
            settings.start_selection(mouse_x, mouse_y)
            _log.output(f'START SELECTION: {mouse_x}, {mouse_y}')
            return {'CANCELLED'}

        self._move_pin_mode_on()
        geotracker = settings.get_current_geotracker_item()
        self.old_focal_length = focal_mm_to_px(
            camera_focal_length(geotracker.camobj),
            *bpy_render_frame(), camera_sensor_width(geotracker.camobj))

        keyframe = bpy_current_frame()
        gt = loader.kt_geotracker()
        if gt.is_key_at(keyframe):
            gt.fixate_pins(keyframe)

        context.window_manager.modal_handler_add(self)
        _log.output('GT START PIN MOVING')
        return {'RUNNING_MODAL'}

    def modal(self, context: Any, event: Any) -> Set:
        mouse_x = event.mouse_region_x
        mouse_y = event.mouse_region_y

        if event.value == 'RELEASE' and event.type == 'LEFTMOUSE':
            _log.output('MOVEPIN LEFT MOUSE RELEASE')
            return self.on_left_mouse_release(context.area)

        settings = self.get_settings()
        if event.type == 'MOUSEMOVE' \
                and settings.loader().viewport().pins().current_pin() is not None:
            _log.output(f'MOVEPIN MOUSEMOVE: {mouse_x} {mouse_y}')
            return self.on_mouse_move(context.area, mouse_x, mouse_y)

        return self.on_default_modal()
