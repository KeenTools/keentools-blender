import logging
from typing import Any, Set

import bpy
from bpy.types import Area

from ..geotracker_config import (GTConfig,
                                 get_gt_settings,
                                 get_current_geotracker_item)
from .gtloader import GTLoader
from ..utils.coords import (get_image_space_coord,
                            image_space_to_frame,
                            nearest_point)
from ..utils.animation import insert_keyframe_in_fcurve
from ..utils.manipulate import force_undo_push
from ..utils.bpy_common import bpy_current_frame


_logger: Any = logging.getLogger(__name__)


def _log_output(message: str) -> None:
    global _logger
    _logger.debug(message)


def _log_error(message: str) -> None:
    global _logger
    _logger.error(message)


class GT_OT_MovePin(bpy.types.Operator):
    bl_idname = GTConfig.gt_movepin_idname
    bl_label = 'GeoTracker MovePin operator'
    bl_description = 'Operator MovePin'
    bl_options = {'REGISTER'}

    test_action: bpy.props.StringProperty(default="")

    pinx: bpy.props.FloatProperty(default=0)
    piny: bpy.props.FloatProperty(default=0)

    new_pin_flag: bpy.props.BoolProperty(default=False)
    dragged: bpy.props.BoolProperty(default=False)
    pin_was_selected: bpy.props.BoolProperty(default=False)

    def _move_pin_mode_on(self) -> None:
        settings = get_gt_settings()
        settings.move_pin_mode = True

    def _move_pin_mode_off(self) -> None:
        settings = get_gt_settings()
        settings.move_pin_mode = False

    def _before_operator_finish(self) -> None:
        self._move_pin_mode_off()

    def _new_pin(self, area: Area, mouse_x: float, mouse_y: float) -> bool:
        frame = bpy_current_frame()
        x, y = get_image_space_coord(mouse_x, mouse_y, area)

        pin = GTLoader.add_pin(frame, (image_space_to_frame(x, y)))
        _log_output(f'_new_pin pin: {pin}')
        pins = GTLoader.viewport().pins()
        if not pin:
            _log_output('_new_pin MISS MODEL')
            pins.reset_current_pin()
            return False
        else:
            pins.add_pin((x, y))
            pins.set_current_pin_num_to_last()
            _log_output(f'_new_pin ADD PIN pins: {pins.arr()}')
            return True

    def init_action(self, context: Any, mouse_x: float, mouse_y: float) -> bool:
        geotracker = get_current_geotracker_item()
        if not geotracker or not geotracker.geomobj or not geotracker.camobj:
            return False

        self.new_pin_flag = False

        vp = GTLoader.viewport()
        vp.update_view_relative_pixel_size(context.area)
        pins = vp.pins()

        GTLoader.load_pins_into_viewport()

        x, y = get_image_space_coord(mouse_x, mouse_y, context.area)
        pins.set_current_pin((x, y))

        nearest, dist2 = nearest_point(x, y, pins.arr())

        if nearest >= 0 and dist2 < vp.tolerance_dist2():
            _log_output(f'init_action PIN FOUND: {nearest}')
            pins.set_current_pin_num(nearest)
            gt = GTLoader.kt_geotracker()
            selected_pins = pins.get_selected_pins()
            keyframe = bpy_current_frame()
            self.pin_was_selected = nearest in selected_pins
            if self.pin_was_selected:
                for i in selected_pins:
                    gt.pin_enable(keyframe, i, True)
            else:
                gt.pin_enable(keyframe, nearest, True)
                if pins.get_add_selection_mode():
                    pins.add_selected_pins([nearest])
                else:
                    pins.set_selected_pins([nearest])
        else:
            self.new_pin_flag = self._new_pin(context.area, mouse_x, mouse_y)
            if not self.new_pin_flag:
                _log_output('GT MISS MODEL CLICK')
                pins.clear_selected_pins()
                return False
            pins.set_selected_pins([pins.current_pin_num()])
            _log_output('GT NEW PIN CREATED')

        vp.create_batch_2d(context.area)
        vp.register_handlers(context)
        return True

    def on_left_mouse_release(self, area: Area) -> Set:
        def _toggle_undragged_pin() -> None:
            if not self.dragged and not self.new_pin_flag \
                    and self.pin_was_selected:
                _log_output('TOGGLE PIN OFF')
                pins = GTLoader.viewport().pins()
                pins.exclude_selected_pin(pins.current_pin_num())

        def _push_action_in_undo_history() -> None:
            if self.new_pin_flag:
                force_undo_push('Add GeoTracker pin')
                self.new_pin_flag = False
            else:
                force_undo_push('Drag GeoTracker pin')

        _toggle_undragged_pin()
        vp = GTLoader.viewport()
        vp.pins().reset_current_pin()

        GTLoader.spring_pins_back()
        GTLoader.save_geotracker()

        GTLoader.update_all_viewport_shaders(area)
        self._before_operator_finish()
        vp.tag_redraw()

        _push_action_in_undo_history()
        return {'FINISHED'}

    @staticmethod
    def _pin_drag(kid: int, area: Area, mouse_x: float, mouse_y: float) -> None:
        def _drag_multiple_pins(kid: int, pin_index: int) -> None:
            gt = GTLoader.kt_geotracker()
            old_x, old_y = gt.pin(kid, pin_index).img_pos
            new_x, new_y = image_space_to_frame(x, y)
            offset = (new_x - old_x, new_y - old_y)
            GTLoader.delta_move_pin(kid, selected_pins, offset)
            GTLoader.load_pins_into_viewport()

        x, y = get_image_space_coord(mouse_x, mouse_y, area)
        pins = GTLoader.viewport().pins()
        pins.set_current_pin((x, y))
        pin_index = pins.current_pin_num()
        pins.arr()[pin_index] = (x, y)
        selected_pins = pins.get_selected_pins()

        if len(selected_pins) == 1:
            GTLoader.move_pin(kid, pin_index, (x, y))
        else:
            _drag_multiple_pins(kid, pin_index)

    def on_mouse_move(self, area: Area, mouse_x: float, mouse_y: float) -> Set:
        def _place_cameras_and_calc_focals(geotracker: Any, frame: int) -> None:
            GTLoader.place_camera()
            if geotracker.focal_length_estimation:
                focal = GTLoader.updated_focal_length()
                if focal is not None:
                    camobj = geotracker.camobj
                    if not GTConfig.use_storage:
                        insert_keyframe_in_fcurve(camobj.data, frame, focal,
                                                  keyframe_type='KEYFRAME',
                                                  data_path='lens', index=0)
                        camobj.data.lens = focal

        geotracker = get_current_geotracker_item()
        if not geotracker:
            return self.on_default_modal()

        frame = bpy_current_frame()
        self._pin_drag(frame, area, mouse_x, mouse_y)

        if not GTLoader.solve():
            self._before_operator_finish()
            return {'FINISHED'}

        self.dragged = True
        _place_cameras_and_calc_focals(geotracker, frame)

        vp = GTLoader.viewport()
        gt = GTLoader.kt_geotracker()
        vp.update_surface_points(gt, geotracker.geomobj, frame)

        if not geotracker.camera_mode():
            wf = vp.wireframer()
            wf.init_geom_data_from_mesh(geotracker.geomobj)
            wf.create_batches()

        vp.create_batch_2d(area)
        vp.update_residuals(gt, area, frame)
        vp.tag_redraw()
        return self.on_default_modal()

    def on_default_modal(self) -> Set:
        if GTLoader.viewport().pins().current_pin() is not None:
            return {'RUNNING_MODAL'}
        else:
            _log_output('MOVE PIN FINISH')
            self._before_operator_finish()
            return {'FINISHED'}

    def invoke(self, context: Any, event: Any) -> Set:
        self.dragged = False
        if not self.init_action(context,
                                event.mouse_region_x, event.mouse_region_y):
            settings = get_gt_settings()
            settings.start_selection(event.mouse_region_x, event.mouse_region_y)
            _log_output('START SELECTION')
            return {'CANCELLED'}

        self._move_pin_mode_on()
        context.window_manager.modal_handler_add(self)
        _log_output('GT START PIN MOVING')
        return {'RUNNING_MODAL'}

    def modal(self, context: Any, event: Any) -> Set:
        mouse_x = event.mouse_region_x
        mouse_y = event.mouse_region_y

        if event.value == 'RELEASE' and event.type == 'LEFTMOUSE':
            _log_output('MOVEPIN LEFT MOUSE RELEASE')
            return self.on_left_mouse_release(context.area)

        if event.type == 'MOUSEMOVE' \
                and GTLoader.viewport().pins().current_pin() is not None:
            _log_output(f'MOVEPIN MOUSEMOVE: {mouse_x} {mouse_y}')
            return self.on_mouse_move(context.area, mouse_x, mouse_y)

        return self.on_default_modal()
