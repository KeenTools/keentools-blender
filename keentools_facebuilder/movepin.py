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

import bpy
from . fbloader import FBLoader
from . fbdebug import FBDebug
from . utils import FBCalc
from . config import config, get_main_settings, BuilderType

from pykeentools import UnlicensedException


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

    def invoke(self, context, event):
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

        FBLoader.update_pixel_size(context)

        # Load serialized model Uncentered (False param)
        FBLoader.load_all(headnum, camnum, False)

        FBLoader.create_batch_2d(context)
        FBLoader.register_handlers(args, context)

        # Pinmode
        settings.pinmode = True
        x, y = FBCalc.get_image_space_coord(context, (self.pinx, self.piny))
        FBLoader.current_pin = (x, y)

        nearest, dist2 = FBCalc.nearest_point(x, y, FBLoader.spins)

        if nearest >= 0 and dist2 < FBLoader.tolerance_dist2():
            # Nearest pin found
            FBLoader.current_pin_num = nearest
            # === Debug only ===
            FBDebug.add_event_to_queue(
                'PIN_FOUND', FBCalc.get_mouse_coords(event, context),
                FBCalc.get_raw_camera_2d_data(context))
            # === Debug only ===
        else:
            # We need new pin
            pin = FBLoader.get_builder().add_pin(
                kid, (FBCalc.image_space_to_frame(x, y))
            )

            if pin is not None:
                # === Debug only ===
                FBDebug.add_event_to_queue(
                    'ADD_PIN', FBCalc.get_mouse_coords(event, context),
                    FBCalc.get_raw_camera_2d_data(context))
                # === Debug only ===

                FBLoader.spins.append((x, y))
                FBLoader.current_pin_num = len(FBLoader.spins) - 1
                FBLoader.update_pins_count(headnum, camnum)
            else:
                # === Debug only ===
                FBDebug.add_event_to_queue(
                    'MISS_PIN', FBCalc.get_mouse_coords(event, context),
                    FBCalc.get_raw_camera_2d_data(context))
                # === Debug only ===

                FBLoader.current_pin = None
                FBLoader.current_pin_num = -1
                # User miss Head  object
                self.report({'INFO'}, "Miss model")
                return {"FINISHED"}

        FBLoader.create_batch_2d(context)

        context.window_manager.modal_handler_add(self)
        self.report({'INFO'}, "Start pin moving")
        return {"RUNNING_MODAL"}

    def on_left_mouse_release(self, context, event):
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
            'RELEASE_LEFTMOUSE', FBCalc.get_mouse_coords(event, context),
            FBCalc.get_raw_camera_2d_data(context))
        # === Debug only ===

        print('Left Up')

        x, y = FBCalc.get_image_space_coord(
            context, FBCalc.get_mouse_coords(event, context))
        if FBLoader.current_pin:
            # Move current pin
            FBLoader.spins[FBLoader.current_pin_num] = (x, y)

        FBLoader.current_pin = None
        FBLoader.current_pin_num = -1

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
                print('DESERIALIZE ERROR: ', head.get_serial_str())

            FBCalc.update_head_mesh(fb, head.headobj)
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
            print("PUSH 1")

            # Restore last position
            head.set_serial_str(serial_str)
            cam.model_mat = model_mat
            fb.set_model_mat(kid, cam.get_model_mat())

            if not fb.deserialize(head.get_serial_str()):
                print('DESERIALIZE ERROR: ', head.get_serial_str())
        else:
            # There was only one click
            # Save current state
            head.set_serial_str(fb.serialize())
            cam.set_model_mat(fb.model_mat(kid))

        FBCalc.update_head_mesh(fb, head.headobj)
        # Update all cameras position
        FBLoader.update_cameras(headnum)

        # ---------
        FBLoader.fb_save(headnum, camnum)

        head.need_update = True
        FBLoader.force_undo_push('Pin Result')
        head.need_update = False
        print("PUSH 2")
        # ---------

        # Load 3D pins
        FBLoader.update_surface_points(headobj, kid)

        self.report({'INFO'}, "Release LM")
        return {'FINISHED'}

    def on_mouse_move(self, context, event):
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
            'MOUSEMOVE', FBCalc.get_mouse_coords(event, context),
            FBCalc.get_raw_camera_2d_data(context))
        # === Debug only ===

        # Pin drag
        x, y = FBCalc.get_image_space_coord(
            context, FBCalc.get_mouse_coords(event, context))
        FBLoader.current_pin = (x, y)

        p_idx = FBLoader.current_pin_num
        FBLoader.spins[FBLoader.current_pin_num] = (x, y)

        fb.move_pin(kid, p_idx, FBCalc.image_space_to_frame(x, y))

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
            FBLoader.out_pinmode(context, headnum, camnum)
            self.report({'INFO'}, "MOVE PIN LICENSE EXCEPTION")
            return {'FINISHED'}

        #--------------
        # Pin lag solve
        #--------------
        head = settings.heads[headnum]
        # Store in tmp previous state
        head.tmp_serial_str = head.serial_str
        cam.tmp_model_mat = cam.model_mat
        # Save current state
        head.set_serial_str(fb.serialize())
        cam.set_model_mat(fb.model_mat(kid))
        #--------------

        # Update Rigidity
        if settings.check_auto_rigidity and (
                FBLoader.get_builder_type() == BuilderType.FaceBuilder):
            rg = fb.current_rigidity()
            settings.rigidity = rg

        # Camera update
        FBLoader.place_cameraobj(kid, camobj, headobj)

        # Head Mesh update
        FBCalc.update_head_mesh(fb, headobj)
        FBLoader.wireframer.init_geom_data(headobj)
        FBLoader.wireframer.create_batches()

        FBLoader.create_batch_2d(context)
        # Try to redraw
        context.area.tag_redraw()

        # Load 3D pins
        FBLoader.update_surface_points(headobj, kid)

        return self.on_default_modal()

    def on_default_modal(self):
        if FBLoader.current_pin:
            return {"RUNNING_MODAL"}
        else:
            self.report({'INFO'}, "Finish MovePin")
            return {'FINISHED'}

    def modal(self, context, event):
        # print('EVENT: {} VALUE: {}'.format(event.type, event.value))

        # Pin is set
        if event.value == "RELEASE":
            if event.type == "LEFTMOUSE":
                return self.on_left_mouse_release(context, event)

        if event.type == "MOUSEMOVE":
            if FBLoader.current_pin:
                return self.on_mouse_move(context, event)

        return self.on_default_modal()
