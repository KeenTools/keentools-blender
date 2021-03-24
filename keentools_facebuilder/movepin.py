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

from .utils import manipulate, coords
from .fbloader import FBLoader
from .config import Config, get_main_settings

from functools import wraps


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


class FB_OT_MovePin(bpy.types.Operator):
    """ On Screen Face Builder MovePin Operator """
    bl_idname = Config.fb_movepin_idname
    bl_label = "FaceBuilder MovePin operator"
    bl_description = "Operator MovePin"
    bl_options = {'REGISTER'}

    headnum: bpy.props.IntProperty(default=0)
    camnum: bpy.props.IntProperty(default=0)
    test_action: bpy.props.StringProperty(default="")

    pinx: bpy.props.FloatProperty(default=0)
    piny: bpy.props.FloatProperty(default=0)

    # Headnum & camnum unstable because of Blender operator params may changing
    # Possible we need store initial values, but unsure
    # So created some getter functions
    def get_headnum(self):
        return self.headnum

    def get_camnum(self):
        return self.camnum

    def _new_pin(self, context, mouse_x, mouse_y):
        logger = logging.getLogger(__name__)
        settings = get_main_settings()
        headnum = self.get_headnum()
        camnum = self.get_camnum()
        kid = settings.get_keyframe(headnum, camnum)

        x, y = coords.get_image_space_coord(mouse_x, mouse_y, context)

        pin = FBLoader.get_builder().add_pin(
            kid, (coords.image_space_to_frame(x, y))
        )
        if pin is not None:
            logger.debug("ADD PIN")
            vp = FBLoader.viewport()
            vp.pins().add_pin((x, y))
            vp.pins().set_current_pin_num_to_last()
            FBLoader.update_pins_count(headnum, camnum)

            manipulate.push_neutral_head_in_undo_history(
                settings.get_head(headnum), kid, 'New Pin.')
        else:
            logger.debug("MISS MODEL")
            FBLoader.viewport().pins().reset_current_pin()
            return {"FINISHED"}
        return None

    def init_action(self, context, mouse_x, mouse_y):
        args = (self, context)

        settings = get_main_settings()
        headnum = self.get_headnum()
        camnum = self.get_camnum()

        head = settings.get_head(headnum)
        if head is None:
            return {'CANCELLED'}

        cam = head.get_camera(camnum)
        if cam is None:
            return {'CANCELLED'}

        # Init old state values
        head.tmp_serial_str = ''
        cam.tmp_model_mat = ''

        vp = FBLoader.viewport()
        vp.update_view_relative_pixel_size(context)

        FBLoader.load_model(headnum)
        FBLoader.place_camera(headnum, camnum)
        FBLoader.load_pins(headnum, camnum)

        vp.create_batch_2d(context)
        vp.register_handlers(args, context)

        x, y = coords.get_image_space_coord(mouse_x, mouse_y, context)
        vp.pins().set_current_pin((x, y))

        nearest, dist2 = coords.nearest_point(x, y, vp.pins().arr())

        if nearest >= 0 and dist2 < vp.tolerance_dist2():
            vp.pins().set_current_pin_num(nearest)
        else:
            return self._new_pin(context, mouse_x, mouse_y)

    def _push_previous_state(self):
        logger = logging.getLogger(__name__)
        settings = get_main_settings()
        headnum = self.get_headnum()
        camnum = self.get_camnum()
        head = settings.get_head(headnum)
        cam = head.get_camera(camnum)
        kid = cam.get_keyframe()

        fb = FBLoader.get_builder()
        # Save state to vars
        serial_str = head.serial_str
        model_mat = cam.model_mat

        # Prepare previous state to push in history
        if head.tmp_serial_str != '':
            cam.model_mat = cam.tmp_model_mat
            head.set_serial_str(head.get_tmp_serial_str())

            if not fb.deserialize(head.get_serial_str()):
                logger.warning('DESERIALIZE ERROR: ', head.get_serial_str())

            FBLoader.update_all_camera_positions(headnum)
            # ---------
            # PUSH Previous
            manipulate.push_neutral_head_in_undo_history(head, kid, 'Move Pin.')
            # ---------
            # Restore last position
            head.set_serial_str(serial_str)
            cam.model_mat = model_mat

            if not fb.deserialize(head.get_serial_str()):
                logger.warning("DESERIALIZE ERROR: {}", head.get_serial_str())
        else:
            # There was only one click
            # Save current state
            head.set_serial_str(fb.serialize())
            cam.set_model_mat(fb.model_mat(kid))

    def on_left_mouse_release(self, context, mouse_x, mouse_y):
        settings = get_main_settings()
        headnum = self.get_headnum()
        camnum = self.get_camnum()
        head = settings.get_head(headnum)
        kid = settings.get_keyframe(headnum, camnum)

        x, y = coords.get_image_space_coord(mouse_x, mouse_y, context)
        vp = FBLoader.viewport()
        pins = vp.pins()
        if pins.current_pin() is not None:
            # Move current 2D-pin
            pins.arr()[pins.current_pin_num()] = (x, y)

        FBLoader.update_head_camobj_focals(head)

        fb = FBLoader.get_builder()

        if head.should_reduce_pins():
            fb.reduce_pins()
            FBLoader.save_only(headnum)
            pins.set_pins(vp.img_points(fb, kid))

        self._push_previous_state()

        FBLoader.update_all_camera_positions(headnum)
        FBLoader.update_all_camera_focals(headnum)
        FBLoader.fb_save(headnum, camnum)
        # ---------
        # PUSH Last
        manipulate.push_neutral_head_in_undo_history(head, kid, 'Pin Result.')
        # ---------

        # Load 3D pins
        vp.update_surface_points(fb, head.headobj, kid)
        vp.update_residuals(fb, context, head.headobj, kid)
        head.mark_model_changed_by_pinmode()

        pins.reset_current_pin()
        return {'FINISHED'}

    @staticmethod
    def _pin_drag(kid, context, mouse_x, mouse_y):
        fb = FBLoader.get_builder()
        x, y = coords.get_image_space_coord(mouse_x, mouse_y, context)
        pins = FBLoader.viewport().pins()
        pins.set_current_pin((x, y))
        pin_idx = pins.current_pin_num()
        pins.arr()[pin_idx] = (x, y)
        fb.move_pin(kid, pin_idx, coords.image_space_to_frame(x, y))

    def on_mouse_move(self, context, mouse_x, mouse_y):

        settings = get_main_settings()
        headnum = self.get_headnum()
        camnum = self.get_camnum()
        head = settings.get_head(headnum)
        headobj = head.headobj
        cam = head.get_camera(camnum)
        kid = settings.get_keyframe(headnum, camnum)

        self._pin_drag(kid, context, mouse_x, mouse_y)

        if not FBLoader.solve(headnum, camnum):
            logger = logging.getLogger(__name__)
            logger.error("MOVE PIN PROBLEM")
            return {'FINISHED'}

        fb = FBLoader.get_builder()
        # --------------
        # Pin lag solve
        # --------------
        head = settings.get_head(headnum)
        # Store in tmp previous state
        head.tmp_serial_str = head.serial_str
        cam.tmp_model_mat = cam.model_mat
        # Save current state
        head.set_serial_str(fb.serialize())
        cam.set_model_mat(fb.model_mat(kid))
        # --------------

        FBLoader.place_camera(headnum, camnum)
        coords.update_head_mesh(settings, fb, head)

        vp = FBLoader.viewport()
        vp.wireframer().init_geom_data(headobj)
        vp.wireframer().update_edges_vertices()
        vp.wireframer().create_batches()
        vp.create_batch_2d(context)
        # Try to redraw
        if not bpy.app.background:
            context.area.tag_redraw()

        # Load 3D pins
        vp.update_surface_points(fb, headobj, kid)

        return self.on_default_modal()

    @staticmethod
    def on_default_modal():
        logger = logging.getLogger(__name__)
        if FBLoader.viewport().pins().current_pin() is not None:
            return {"RUNNING_MODAL"}
        else:
            logger.debug("MOVE PIN FINISH")
            return {'FINISHED'}

    # Integration testing purpose only
    def execute(self, context):
        logger = logging.getLogger(__name__)

        if self.test_action == "add_pin":
            logger.debug("ADD PIN TEST")
            self.init_action(context, self.pinx, self.piny)
        elif self.test_action == "mouse_move":
            logger.debug("MOUSE MOVE TEST")
            self.on_mouse_move(context, self.pinx, self.piny)
        elif self.test_action == "mouse_release":
            logger.debug("MOUSE RELEASE TEST")
            self.on_left_mouse_release(context, self.pinx, self.piny)
        return {"FINISHED"}

    @profile_this
    def invoke(self, context, event):
        logger = logging.getLogger(__name__)
        ret = self.init_action(
            context, event.mouse_region_x, event.mouse_region_y)
        if ret in {'CANCELLED', 'FINISHED'}:
            return ret
        FBLoader.viewport().create_batch_2d(context)
        context.window_manager.modal_handler_add(self)
        logger.debug("START PIN MOVING")
        return {"RUNNING_MODAL"}

    @profile_this
    def modal(self, context, event):
        logger = logging.getLogger(__name__)
        mouse_x = event.mouse_region_x
        mouse_y = event.mouse_region_y

        if event.value == "RELEASE" and event.type == "LEFTMOUSE":
            logger.debug("LEFT MOUSE RELEASE")
            return self.on_left_mouse_release(context, mouse_x, mouse_y)

        if event.type == "MOUSEMOVE" \
                and FBLoader.viewport().pins().current_pin() is not None:
            logger.debug("MOUSEMOVE {} {}".format(mouse_x, mouse_y))
            return self.on_mouse_move(context, mouse_x, mouse_y)

        return self.on_default_modal()
