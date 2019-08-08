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

from . utils import coords
from . fbloader import FBLoader
from . fbdebug import FBDebug
from . config import config, get_main_settings, BuilderType

from pykeentools import UnlicensedException
from functools import wraps


# Decorator for profiling
def profile_this(fn):
    @wraps(fn)
    def wrapped(arg1, arg2, arg3):
        if FBLoader.viewport.profiling:
            pr = FBLoader.viewport.pr
            pr.enable()
            ret = fn(arg1, arg2, arg3)
            pr.disable()
            return ret
        else:
            ret = fn(arg1, arg2, arg3)
            return ret
    return wrapped


class OBJECT_OT_FBMovePin(bpy.types.Operator):
    """ On Screen Face Builder MovePin Operator """
    bl_idname = config.fb_movepin_operator_idname
    bl_label = "FaceBuilder MovePin operator"
    bl_description = "Operator MovePin"
    bl_options = {'REGISTER'}  # 'UNDO'

    headnum: bpy.props.IntProperty(default=0)
    camnum: bpy.props.IntProperty(default=0)

    pinx: bpy.props.FloatProperty(default=0)
    piny: bpy.props.FloatProperty(default=0)

    # Headnum & camnum unstable because of Blender operator params may changing
    # Possible we need store initial values, but unsure
    # So created some getter functions
    def get_headnum(self):
        return self.headnum

    def get_camnum(self):
        return self.camnum

    @profile_this
    def invoke(self, context, event):
        logger = logging.getLogger(__name__)
        args = (self, context)
        scene = context.scene
        settings = get_main_settings()
        headnum = self.get_headnum()
        camnum = self.get_camnum()
        kid = FBLoader.keyframe_by_camnum(headnum, camnum)

        # Checks for operator parameters
        if headnum < 0:
            return {'CANCELED'}
        head = settings.heads[headnum]
        if camnum < 0 or camnum >= len(head.cameras):
            return {'CANCELED'}
        cam = head.cameras[camnum]

        # Init old state values
        head.tmp_serial_str = ''
        cam.tmp_model_mat = ''

        FBLoader.viewport.update_pixel_size(context)

        # Load serialized model Uncentered (False param)
        FBLoader.load_all(headnum, camnum, False)

        FBLoader.viewport.create_batch_2d(context)
        FBLoader.viewport.register_handlers(args, context)

        # Pinmode
        settings.pinmode = True
        x, y = coords.get_image_space_coord(context, (self.pinx, self.piny))
        FBLoader.viewport.current_pin = (x, y)

        nearest, dist2 = coords.nearest_point(x, y, FBLoader.viewport.spins)

        if nearest >= 0 and dist2 < FBLoader.viewport.tolerance_dist2():
            # Nearest pin found
            FBLoader.viewport.current_pin_num = nearest
            # === Debug only ===
            FBDebug.add_event_to_queue(
                'PIN_FOUND', coords.get_mouse_coords(event, context),
                coords.get_raw_camera_2d_data(context))
            # === Debug only ===
        else:
            # We need new pin
            pin = FBLoader.get_builder().add_pin(
                kid, (coords.image_space_to_frame(x, y))
            )

            if pin is not None:
                # === Debug only ===
                FBDebug.add_event_to_queue(
                    'ADD_PIN', coords.get_mouse_coords(event, context),
                    coords.get_raw_camera_2d_data(context))
                # === Debug only ===

                FBLoader.viewport.spins.append((x, y))
                FBLoader.viewport.current_pin_num = \
                    len(FBLoader.viewport.spins) - 1
                FBLoader.update_pins_count(headnum, camnum)
            else:
                # === Debug only ===
                FBDebug.add_event_to_queue(
                    'MISS_PIN', coords.get_mouse_coords(event, context),
                    coords.get_raw_camera_2d_data(context))
                # === Debug only ===

                FBLoader.viewport.current_pin = None
                FBLoader.viewport.current_pin_num = -1
                # User miss Head  object
                logger.debug("MISS MODEL")
                return {"FINISHED"}

        FBLoader.viewport.create_batch_2d(context)

        context.window_manager.modal_handler_add(self)
        logger.debug("START PIN MOVING")
        return {"RUNNING_MODAL"}

    def on_left_mouse_release(self, context, event):
        logger = logging.getLogger(__name__)
        scene = context.scene
        settings = get_main_settings()
        headnum = self.get_headnum()
        camnum = self.get_camnum()
        head = settings.heads[headnum]
        headobj = settings.heads[headnum].headobj
        cam = head.cameras[camnum]
        kid = FBLoader.keyframe_by_camnum(headnum, camnum)

        # === Debug only ===
        FBDebug.add_event_to_queue(
            'RELEASE_LEFTMOUSE', coords.get_mouse_coords(event, context),
            coords.get_raw_camera_2d_data(context))
        # === Debug only ===

        logger.debug("LEFT MOUSE RELEASE")

        x, y = coords.get_image_space_coord(
            context, coords.get_mouse_coords(event, context))
        if FBLoader.viewport.current_pin:
            # Move current pin
            FBLoader.viewport.spins[FBLoader.viewport.current_pin_num] = (x, y)

        FBLoader.viewport.current_pin = None
        FBLoader.viewport.current_pin_num = -1

        # --------------
        # Pin lag solve
        # --------------
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
            # Update all cameras position
            FBLoader.update_cameras(headnum)
            # ---------
            # Undo push
            # ---------
            head = settings.heads[headnum]
            # if head.serial_str != head.tmp_serial_str:
            head.need_update = True
            FBLoader.force_undo_push('Pin Move')
            head.need_update = False
            # End of PUSH 1
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

        coords.update_head_mesh(fb, head.headobj)
        # Update all cameras position
        FBLoader.update_cameras(headnum)

        # ---------
        FBLoader.fb_save(headnum, camnum)

        head.need_update = True
        FBLoader.force_undo_push('Pin Result')
        head.need_update = False
        # End of PUSH 2
        # ---------

        # Load 3D pins
        FBLoader.viewport.update_surface_points(fb, headobj, kid)
        return {'FINISHED'}

    def on_mouse_move(self, context, event):
        logger = logging.getLogger(__name__)
        scene = context.scene
        settings = get_main_settings()
        headnum = self.get_headnum()
        camnum = self.get_camnum()
        headobj = settings.heads[headnum].headobj
        cam = settings.heads[headnum].cameras[camnum]
        camobj = cam.camobj
        kid = FBLoader.keyframe_by_camnum(headnum, camnum)

        fb = FBLoader.get_builder()

        # === Debug only ===
        FBDebug.add_event_to_queue(
            'MOUSEMOVE', coords.get_mouse_coords(event, context),
            coords.get_raw_camera_2d_data(context))
        # === Debug only ===

        # Pin drag
        x, y = coords.get_image_space_coord(
            context, coords.get_mouse_coords(event, context))
        FBLoader.viewport.current_pin = (x, y)

        p_idx = FBLoader.viewport.current_pin_num
        FBLoader.viewport.spins[FBLoader.viewport.current_pin_num] = (x, y)

        fb.move_pin(kid, p_idx, coords.image_space_to_frame(x, y))

        # sleep(0.5)  # Test purpose only

        # Setup Rigidity
        if FBLoader.get_builder_type() == BuilderType.FaceBuilder:
            fb.set_auto_rigidity(settings.check_auto_rigidity)
            fb.set_rigidity(settings.rigidity)

        try:
            # Solver
            fb.solve_for_current_pins(kid)
        except UnlicensedException:
            settings.force_out_pinmode = True
            settings.license_error = True
            FBLoader.out_pinmode(headnum, camnum)
            logger.error("MOVE PIN LICENSE EXCEPTION")
            return {'FINISHED'}

        # --------------
        # Pin lag solve
        # --------------
        head = settings.heads[headnum]
        # Store in tmp previous state
        head.tmp_serial_str = head.serial_str
        cam.tmp_model_mat = cam.model_mat
        # Save current state
        head.set_serial_str(fb.serialize())
        cam.set_model_mat(fb.model_mat(kid))
        # --------------

        # Update Rigidity
        if settings.check_auto_rigidity and (
                FBLoader.get_builder_type() == BuilderType.FaceBuilder):
            rg = fb.current_rigidity()
            settings.rigidity = rg

        # Camera update
        FBLoader.place_cameraobj(kid, camobj, headobj)

        # Head Mesh update
        coords.update_head_mesh(fb, headobj)
        FBLoader.viewport.wireframer.init_geom_data(headobj)
        # FBLoader.wireframer.init_edge_indices(headobj)
        FBLoader.viewport.wireframer.create_batches()

        FBLoader.viewport.create_batch_2d(context)
        # Try to redraw
        context.area.tag_redraw()

        # Load 3D pins
        FBLoader.viewport.update_surface_points(fb, headobj, kid)

        return self.on_default_modal()

    def on_default_modal(self):
        logger = logging.getLogger(__name__)
        if FBLoader.viewport.current_pin:
            return {"RUNNING_MODAL"}
        else:
            logger.debug("MOVE PIN FINISH")
            return {'FINISHED'}

    @profile_this
    def modal(self, context, event):
        # Pin is set
        if event.value == "RELEASE":
            if event.type == "LEFTMOUSE":
                return self.on_left_mouse_release(context, event)

        if event.type == "MOUSEMOVE":
            if FBLoader.viewport.current_pin:
                return self.on_mouse_move(context, event)

        return self.on_default_modal()
