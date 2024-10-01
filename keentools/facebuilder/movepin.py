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

from typing import Any, List, Set
from functools import wraps

from bpy.types import Operator, Area
from bpy.props import IntProperty, FloatProperty, StringProperty, BoolProperty

from ..utils.kt_logging import KTLogger
from ..utils.bpy_common import bpy_background_mode, get_scene_camera_shift
from ..utils.coords import (get_image_space_coord,
                            image_space_to_frame,
                            update_head_mesh_non_neutral,
                            nearest_point,
                            point_is_in_area,
                            point_is_in_service_region)
from ..addon_config import fb_settings
from ..facebuilder_config import FBConfig
from .utils.manipulate import push_head_in_undo_history
from .ui_strings import buttons


_log = KTLogger(__name__)


# Decorator for profiling
def profile_this(fn):
    @wraps(fn)
    def wrapped(arg1, arg2, arg3):
        settings = fb_settings()
        loader = settings.loader()
        if loader.viewport().profiling:
            pr = loader.viewport().pr
            pr.enable()
            ret = fn(arg1, arg2, arg3)
            pr.disable()
            return ret
        else:
            ret = fn(arg1, arg2, arg3)
            return ret
    return wrapped


class FB_OT_MovePin(Operator):
    """ On Screen Face Builder MovePin Operator """
    bl_idname = FBConfig.fb_movepin_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER'}

    headnum: IntProperty(default=0)
    camnum: IntProperty(default=0)
    test_action: StringProperty(default='')

    pinx: FloatProperty(default=0)
    piny: FloatProperty(default=0)

    new_pin_flag: BoolProperty(default=False)
    dragged: BoolProperty(default=False)

    def get_headnum(self) -> int:
        return self.headnum

    def get_camnum(self) -> int:
        return self.camnum

    def _new_pin(self, area: Area, mouse_x: float, mouse_y: float) -> bool:
        settings = fb_settings()
        loader = settings.loader()
        headnum = self.get_headnum()
        camnum = self.get_camnum()
        kid = settings.get_keyframe(headnum, camnum)

        x, y = get_image_space_coord(mouse_x, mouse_y, area)

        pins = loader.viewport().pins()
        fb = loader.get_builder()
        pin = fb.add_pin(kid, (image_space_to_frame(x, y)))
        if not pin:
            _log.output('_new_pin MISS MODEL')
            pins.reset_current_pin()
            return False
        else:
            pins.add_pin((x, y))
            pins.set_current_pin_num_to_last()
            _log.green(f'_new_pin ADD PIN pins: {pins.arr()}')
            loader.update_camera_pins_count(headnum, camnum)
            return True

    def init_action(self, area: Any, mouse_x: float, mouse_y: float) -> bool:
        settings = fb_settings()
        headnum = self.get_headnum()
        camnum = self.get_camnum()

        head = settings.get_head(headnum)
        if head is None:
            return False

        cam = head.get_camera(camnum)
        if cam is None:
            return False

        self.new_pin_flag = False

        loader = settings.loader()
        vp = loader.viewport()
        vp.update_view_relative_pixel_size(area)

        loader.load_model(headnum)
        loader.place_camera(headnum, camnum)
        loader.load_pins_into_viewport(headnum, camnum)

        vp.create_batch_2d(area)

        x, y = get_image_space_coord(mouse_x, mouse_y, area)

        pins = vp.pins()
        nearest, dist2 = nearest_point(x, y, pins.arr())
        if nearest >= 0 and dist2 < vp.tolerance_dist2():
            pins.set_current_pin_num(nearest)
            if nearest not in pins.get_selected_pins():
                pins.set_selected_pins([nearest])
            return True
        else:
            self.new_pin_flag = self._new_pin(area, mouse_x, mouse_y)
            if not self.new_pin_flag:
                _log.output('FB MISS MODEL CLICK')
                pins.clear_selected_pins()
                return False

            pins.set_selected_pins([pins.current_pin_num()])
            _log.output('FB NEW PIN CREATED')
            return True

    def on_left_mouse_release(self, area: Area,
                              mouse_x: float, mouse_y: float) -> Set:
        _log.yellow(f'{self.__class__.__name__} on_left_mouse_release start')
        settings = fb_settings()
        loader = settings.loader()
        headnum = self.get_headnum()
        camnum = self.get_camnum()
        head = settings.get_head(headnum)
        kid = head.get_keyframe(camnum)

        loader.update_head_camobj_focals(headnum)

        fb = loader.get_builder()

        update_head_mesh_non_neutral(fb, head)

        loader.update_all_camera_positions(headnum)
        loader.update_all_camera_focals(headnum)

        loader.save_fb_serial_and_image_pathes(headnum)

        vp = loader.viewport()
        vp.update_surface_points(fb, head.headobj, kid)
        vp.update_residuals(fb, kid, area)

        if self.new_pin_flag:
            push_head_in_undo_history(head, 'Add FaceBuilder pin')
            self.new_pin_flag = False
        else:
            push_head_in_undo_history(head, 'Drag FaceBuilder pin')

        _log.output(f'{self.__class__.__name__} on_left_mouse_release end >>>')
        return {'FINISHED'}

    def _pin_drag(self, kid: int, area: Area, mouse_x: float, mouse_y: float) -> bool:
        def _drag_multiple_pins(kid: int, pin_index: int,
                                selected_pins: List[int],
                                x: float, y: float) -> None:
            settings = fb_settings()
            loader = settings.loader()
            fb = loader.get_builder()
            old_x, old_y = fb.pin(kid, pin_index).img_pos
            new_x, new_y = image_space_to_frame(x, y, *get_scene_camera_shift())
            offset = (new_x - old_x, new_y - old_y)
            loader.delta_move_pin(kid, selected_pins, offset)
            loader.load_pins_into_viewport(settings.current_headnum,
                                           settings.current_camnum)

        settings = fb_settings()
        loader = settings.loader()
        shift_x, shift_y = get_scene_camera_shift()
        x, y = get_image_space_coord(mouse_x, mouse_y, area, shift_x, shift_y)
        pins = loader.viewport().pins()
        pin_index = pins.current_pin_num()
        pins.arr()[pin_index] = (x, y)
        selected_pins = pins.get_selected_pins()

        if len(selected_pins) == 1:
            loader.move_pin(kid, pin_index, (x, y), shift_x, shift_y)
            return loader.solve(settings.current_headnum,
                                settings.current_camnum)

        _drag_multiple_pins(kid, pin_index, selected_pins, x, y)
        return loader.solve(settings.current_headnum, settings.current_camnum)

    def on_mouse_move(self, area, mouse_x, mouse_y):
        settings = fb_settings()
        loader = settings.loader()
        headnum = self.get_headnum()
        camnum = self.get_camnum()
        head = settings.get_head(headnum)
        headobj = head.headobj
        kid = head.get_keyframe(camnum)

        self._pin_drag(kid, area, mouse_x, mouse_y)

        if not loader.solve(headnum, camnum):
            _log.error('MOVE PIN PROBLEM')
            return {'FINISHED'}

        fb = loader.get_builder()

        loader.place_camera(headnum, camnum)

        geo = fb.applied_args_model_at(kid)
        vp = loader.viewport()
        wf = vp.wireframer()
        camobj = head.get_camera(camnum).camobj
        wf.set_object_world_matrix(headobj.matrix_world)
        wf.set_camera_pos(headobj.matrix_world, camobj.matrix_world)
        wf.init_geom_data_from_core(*loader.get_geo_shader_data(geo))
        wf.create_batches()

        vp.update_surface_points(fb, headobj, kid)
        vp.create_batch_2d(area)

        # Try to force viewport redraw
        if not bpy_background_mode():
            vp.tag_redraw()

        return {'RUNNING_MODAL'}

    @staticmethod
    def on_default_modal():
        settings = fb_settings()
        loader = settings.loader()
        if loader.viewport().pins().current_pin():
            return {'RUNNING_MODAL'}

        _log.output('MOVE PIN FINISH')
        return {'FINISHED'}

    # Integration testing purpose only
    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        if self.test_action == 'add_pin':
            _log.output('ADD PIN TEST')
            self.init_action(context.area, self.pinx, self.piny)
        elif self.test_action == 'mouse_move':
            _log.output('MOUSE MOVE TEST')
            self.on_mouse_move(context.area, self.pinx, self.piny)
        elif self.test_action == 'mouse_release':
            _log.output('MOUSE RELEASE TEST')
            self.on_left_mouse_release(context.area, self.pinx, self.piny)
        return {'FINISHED'}

    @profile_this
    def invoke(self, context, event):
        _log.green(f'{self.__class__.__name__} invoke start')
        self.dragged = False
        settings = fb_settings()
        loader = settings.loader()
        area = context.area
        mouse_x, mouse_y = event.mouse_region_x, event.mouse_region_y
        if not point_is_in_area(area, mouse_x, mouse_y):
            _log.output(f'OUT OF AREA: {mouse_x}, {mouse_y}')
            _log.output(f'{self.__class__.__name__} invoke 1 cancel >>>')
            return {'CANCELLED'}
        if point_is_in_service_region(area, mouse_x, mouse_y):
            _log.output(f'OUT OF SAFE REGION: {mouse_x}, {mouse_y}')
            _log.output(f'{self.__class__.__name__} invoke 2 cancel >>>')
            return {'CANCELLED'}

        if not self.init_action(area, mouse_x, mouse_y):
            settings.start_selection(mouse_x, mouse_y)
            _log.output(f'START SELECTION: {mouse_x}, {mouse_y}')
            _log.red(f'{self.__class__.__name__} init_action False >>>')
            return {'CANCELLED'}

        loader.viewport().create_batch_2d(context.area)
        context.window_manager.modal_handler_add(self)
        _log.red(f'{self.__class__.__name__} Start move pin modal >>>')
        return {'RUNNING_MODAL'}

    @profile_this
    def modal(self, context, event):
        mouse_x = event.mouse_region_x
        mouse_y = event.mouse_region_y

        if event.value == 'RELEASE' and event.type == 'LEFTMOUSE':
            _log.output('LEFT MOUSE RELEASE')
            return self.on_left_mouse_release(context.area, mouse_x, mouse_y)

        settings = fb_settings()
        if event.type == 'MOUSEMOVE' \
                and settings.loader().viewport().pins().current_pin():
            _log.output(f'MOUSEMOVE {mouse_x} {mouse_y}')
            return self.on_mouse_move(context.area, mouse_x, mouse_y)

        return self.on_default_modal()
