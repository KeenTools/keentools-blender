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

from functools import wraps

from bpy.types import Operator
from bpy.props import IntProperty, FloatProperty, StringProperty

from ..utils.kt_logging import KTLogger
from ..utils.bpy_common import bpy_background_mode
from ..utils.coords import (get_image_space_coord,
                            image_space_to_frame,
                            update_head_mesh_non_neutral,
                            nearest_point)
from .fbloader import FBLoader
from ..addon_config import fb_settings
from ..facebuilder_config import FBConfig
from .utils.manipulate import push_head_in_undo_history
from .ui_strings import buttons


_log = KTLogger(__name__)


# Decorator for profiling
def profile_this(fn):
    @wraps(fn)
    def wrapped(arg1, arg2, arg3):
        if FBLoader.viewport().profiling:
            pr = FBLoader.viewport().pr
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

    def get_headnum(self):
        return self.headnum

    def get_camnum(self):
        return self.camnum

    def _new_pin(self, area, mouse_x, mouse_y):
        settings = fb_settings()
        headnum = self.get_headnum()
        camnum = self.get_camnum()
        kid = settings.get_keyframe(headnum, camnum)

        x, y = get_image_space_coord(mouse_x, mouse_y, area)

        pin = FBLoader.get_builder().add_pin(
            kid, (image_space_to_frame(x, y))
        )
        pins = FBLoader.viewport().pins()
        if pin is not None:
            _log.output('ADD PIN')
            pins.add_pin((x, y))
            pins.set_current_pin_num_to_last()
            FBLoader.update_camera_pins_count(headnum, camnum)
        else:
            _log.output('MISS MODEL')
            pins.reset_current_pin()
            return {"FINISHED"}
        return None

    def init_action(self, context, mouse_x, mouse_y):
        settings = fb_settings()
        headnum = self.get_headnum()
        camnum = self.get_camnum()

        head = settings.get_head(headnum)
        if head is None:
            return {'CANCELLED'}

        area = context.area
        cam = head.get_camera(camnum)
        if cam is None:
            return {'CANCELLED'}

        vp = FBLoader.viewport()
        vp.update_view_relative_pixel_size(area)

        FBLoader.load_model(headnum)
        FBLoader.place_camera(headnum, camnum)
        FBLoader.load_pins_into_viewport(headnum, camnum)

        vp.create_batch_2d(area)

        x, y = get_image_space_coord(mouse_x, mouse_y, area)

        nearest, dist2 = nearest_point(x, y, vp.pins().arr())

        if nearest >= 0 and dist2 < vp.tolerance_dist2():
            vp.pins().set_current_pin_num(nearest)
        else:
            return self._new_pin(area, mouse_x, mouse_y)

    def on_left_mouse_release(self, area, mouse_x, mouse_y):
        _log.yellow(f'{self.__class__.__name__} on_left_mouse_release start')
        settings = fb_settings()
        headnum = self.get_headnum()
        camnum = self.get_camnum()
        head = settings.get_head(headnum)
        kid = head.get_keyframe(camnum)

        x, y = get_image_space_coord(mouse_x, mouse_y, area)
        vp = FBLoader.viewport()
        pins = vp.pins()
        if pins.current_pin():
            # Move current 2D-pin
            pins.arr()[pins.current_pin_num()] = (x, y)

        FBLoader.update_head_camobj_focals(headnum)

        fb = FBLoader.get_builder()

        update_head_mesh_non_neutral(fb, head)

        FBLoader.update_all_camera_positions(headnum)
        FBLoader.update_all_camera_focals(headnum)

        FBLoader.save_fb_serial_and_image_pathes(headnum)

        # Load 3D pins
        vp.update_surface_points(fb, head.headobj, kid)
        vp.update_residuals(fb, kid, area)

        pins.reset_current_pin()

        push_head_in_undo_history(head, 'Pin Move')
        _log.output(f'{self.__class__.__name__} on_left_mouse_release end >>>')
        return {'FINISHED'}

    @staticmethod
    def _pin_drag(kid, area, mouse_x, mouse_y):
        fb = FBLoader.get_builder()
        x, y = get_image_space_coord(mouse_x, mouse_y, area)
        pins = FBLoader.viewport().pins()
        pin_idx = pins.current_pin_num()
        pins.arr()[pin_idx] = (x, y)
        fb.move_pin(kid, pin_idx, image_space_to_frame(x, y))

    def on_mouse_move(self, area, mouse_x, mouse_y):
        settings = fb_settings()
        headnum = self.get_headnum()
        camnum = self.get_camnum()
        head = settings.get_head(headnum)
        headobj = head.headobj
        kid = head.get_keyframe(camnum)

        self._pin_drag(kid, area, mouse_x, mouse_y)

        if not FBLoader.solve(headnum, camnum):
            _log.error('MOVE PIN PROBLEM')
            return {'FINISHED'}

        fb = FBLoader.get_builder()

        FBLoader.place_camera(headnum, camnum)

        geo = fb.applied_args_model_at(kid)
        vp = FBLoader.viewport()
        wf = vp.wireframer()
        camobj = head.get_camera(camnum).camobj
        wf.set_object_world_matrix(headobj.matrix_world)
        wf.set_camera_pos(headobj.matrix_world, camobj.matrix_world)
        wf.init_geom_data_from_core(*FBLoader.get_geo_shader_data(geo))
        wf.create_batches()

        vp.update_surface_points(fb, headobj, kid)
        vp.create_batch_2d(area)

        # Try to force viewport redraw
        if not bpy_background_mode():
            vp.tag_redraw()

        return self.on_default_modal()

    @staticmethod
    def on_default_modal():
        if FBLoader.viewport().pins().current_pin():
            return {'RUNNING_MODAL'}

        _log.output('MOVE PIN FINISH')
        return {'FINISHED'}

    # Integration testing purpose only
    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        if self.test_action == 'add_pin':
            _log.output('ADD PIN TEST')
            self.init_action(context, self.pinx, self.piny)
        elif self.test_action == 'mouse_move':
            _log.output('MOUSE MOVE TEST')
            self.on_mouse_move(context.area, self.pinx, self.piny)
        elif self.test_action == 'mouse_release':
            _log.output('MOUSE RELEASE TEST')
            self.on_left_mouse_release(context.area, self.pinx, self.piny)
        return {'FINISHED'}

    @profile_this
    def invoke(self, context, event):
        _log.green(f'{self.__class__.__name__} invoke')
        ret = self.init_action(
            context, event.mouse_region_x, event.mouse_region_y)
        if ret in {'CANCELLED', 'FINISHED'}:
            _log.red(f'{self.__class__.__name__} init_action {ret} >>>')
            return ret
        FBLoader.viewport().create_batch_2d(context.area)
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

        if event.type == 'MOUSEMOVE' \
                and FBLoader.viewport().pins().current_pin():
            _log.output(f'MOUSEMOVE {mouse_x} {mouse_y}')
            return self.on_mouse_move(context.area, mouse_x, mouse_y)

        return self.on_default_modal()
