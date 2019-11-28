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

from .utils import cameras, manipulate, coords
from .fbloader import FBLoader
from .fbdebug import FBDebug
from .config import Config, get_main_settings

from functools import wraps
import keentools_facebuilder.blender_independent_packages.pykeentools_loader as pkt


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

    def _no_current_pin(self):
        FBLoader.viewport().current_pin = None
        FBLoader.viewport().current_pin_num = -1

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
            FBDebug.add_event_to_queue(
                'ADD_PIN', mouse_x, mouse_y,
                coords.get_raw_camera_2d_data(context))

            FBLoader.viewport().spins.append((x, y))
            FBLoader.viewport().current_pin_num = \
                len(FBLoader.viewport().spins) - 1
            FBLoader.update_pins_count(headnum, camnum)
        else:
            logger.debug("MISS MODEL")
            FBDebug.add_event_to_queue(
                'MISS_PIN', mouse_x, mouse_y,
                coords.get_raw_camera_2d_data(context))

            self._no_current_pin()
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

        FBLoader.viewport().update_view_relative_pixel_size(context)

        FBLoader.load_all(headnum, camnum)
        FBLoader.viewport().create_batch_2d(context)
        FBLoader.viewport().register_handlers(args, context)

        settings.pinmode = True
        x, y = coords.get_image_space_coord(mouse_x, mouse_y, context)
        FBLoader.viewport().current_pin = (x, y)

        nearest, dist2 = coords.nearest_point(x, y, FBLoader.viewport().spins)

        if nearest >= 0 and dist2 < FBLoader.viewport().tolerance_dist2():
            FBDebug.add_event_to_queue(
                'PIN_FOUND', mouse_x, mouse_y,
                coords.get_raw_camera_2d_data(context))
            FBLoader.viewport().current_pin_num = nearest
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
            fb.set_model_mat(kid, cam.get_tmp_model_mat())

            if not fb.deserialize(head.get_serial_str()):
                logger.warning('DESERIALIZE ERROR: ', head.get_serial_str())

            coords.update_head_mesh(fb, head.headobj)
            FBLoader.update_all_camera_positions(headnum)
            # ---------
            # PUSH Previous
            manipulate.push_head_state_in_undo_history(head, 'Pin Move')
            # ---------
            # Restore last position
            head.set_serial_str(serial_str)
            cam.model_mat = model_mat
            fb.set_model_mat(kid, cam.get_model_mat())

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
        if FBLoader.viewport().current_pin:
            # Move current 2D-pin
            FBLoader.viewport().spins[FBLoader.viewport().current_pin_num] \
                = (x, y)

        self._no_current_pin()
        FBLoader.update_all_camera_focals(head)

        self._push_previous_state()

        fb = FBLoader.get_builder()
        coords.update_head_mesh(fb, head.headobj)
        FBLoader.update_all_camera_positions(headnum)

        # ---------
        # PUSH Last
        FBLoader.fb_save(headnum, camnum)
        manipulate.push_head_state_in_undo_history(head, 'Pin Result')
        # ---------

        # Load 3D pins
        FBLoader.viewport().update_surface_points(fb, head.headobj, kid)
        return {'FINISHED'}

    @staticmethod
    def _pin_drag(kid, context, mouse_x, mouse_y):
        fb = FBLoader.get_builder()
        x, y = coords.get_image_space_coord(mouse_x, mouse_y, context)
        FBLoader.viewport().current_pin = (x, y)
        p_idx = FBLoader.viewport().current_pin_num
        FBLoader.viewport().spins[FBLoader.viewport().current_pin_num] = (x, y)
        fb.move_pin(kid, p_idx, coords.image_space_to_frame(x, y))

    def on_mouse_move(self, context, mouse_x, mouse_y):
        logger = logging.getLogger(__name__)
        settings = get_main_settings()
        headnum = self.get_headnum()
        camnum = self.get_camnum()
        head = settings.get_head(headnum)
        headobj = head.headobj
        cam = head.get_camera(camnum)
        camobj = cam.camobj
        kid = settings.get_keyframe(headnum, camnum)

        self._pin_drag(kid, context, mouse_x, mouse_y)

        fb = FBLoader.get_builder()
        FBLoader.rigidity_setup()
        fb.set_focal_length_estimation(head.auto_focal_estimation)

        try:
            fb.solve_for_current_pins(kid)
        except pkt.module().UnlicensedException:
            logger.error("MOVE PIN LICENSE EXCEPTION")
            settings.force_out_pinmode = True
            settings.license_error = True
            FBLoader.out_pinmode(headnum, camnum)
            return {'FINISHED'}

        FBLoader.auto_focal_estimation_post(head, camobj)

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

        FBLoader.rigidity_post()
        FBLoader.place_cameraobj(kid, camobj, headobj)
        coords.update_head_mesh(fb, headobj)
        FBLoader.viewport().wireframer().init_geom_data(headobj)
        FBLoader.viewport().wireframer().create_batches()
        FBLoader.viewport().create_batch_2d(context)
        # Try to redraw
        if not bpy.app.background:
            context.area.tag_redraw()

        # Load 3D pins
        FBLoader.viewport().update_surface_points(fb, headobj, kid)

        return self.on_default_modal()

    @staticmethod
    def on_default_modal():
        logger = logging.getLogger(__name__)
        if FBLoader.viewport().current_pin:
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

            FBDebug.add_event_to_queue(
                'RELEASE_LEFTMOUSE', mouse_x, mouse_y,
                coords.get_raw_camera_2d_data(context))

            return self.on_left_mouse_release(context, mouse_x, mouse_y)

        if event.type == "MOUSEMOVE" and FBLoader.viewport().current_pin:
            logger.debug("MOUSEMOVE")

            FBDebug.add_event_to_queue(
                'MOUSEMOVE', mouse_x, mouse_y,
                coords.get_raw_camera_2d_data(context))

            return self.on_mouse_move(context, mouse_x, mouse_y)

        return self.on_default_modal()
