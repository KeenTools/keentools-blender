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

from .utils import manipulate, coords, cameras
from .config import Config, get_main_settings, get_operators, ErrorType
from .fbdebug import FBDebug
from .fbloader import FBLoader
from .utils.other import FBStopShaderTimer, force_ui_redraw, hide_ui_elements

import keentools_facebuilder.blender_independent_packages.pykeentools_loader as pkt


class FB_OT_PinMode(bpy.types.Operator):
    """ On Screen Face Builder Draw Operator """
    bl_idname = Config.fb_pinmode_idname
    bl_label = "FaceBuilder Pinmode"
    bl_description = "Operator for in-Viewport drawing"
    bl_options = {'REGISTER', 'UNDO'}

    headnum: bpy.props.IntProperty(default=0)
    camnum: bpy.props.IntProperty(default=0)

    _shift_pressed = False

    @classmethod
    def _set_shift_pressed(cls, val):
        cls._shift_pressed = val

    @classmethod
    def _is_shift_pressed(cls):
        return cls._shift_pressed

    def _fix_heads_with_warning(self):
        logger = logging.getLogger(__name__)
        settings = get_main_settings()
        heads_deleted, cams_deleted = settings.fix_heads()
        if heads_deleted > 0 or cams_deleted > 0:
            logger.warning("HEADS AND CAMERAS FIXED")
        if heads_deleted == 0:
            warn = getattr(get_operators(), Config.fb_warning_callname)
            warn('INVOKE_DEFAULT', msg=ErrorType.SceneDamaged)

    def _coloring_special_parts(self, headobj, opacity):
        settings = get_main_settings()
        if settings.show_specials:
            special_indices = FBLoader.viewport().get_special_indices(
                FBLoader.get_builder_type())
            special_color = (*settings.wireframe_special_color,
                             opacity * settings.wireframe_opacity)
            FBLoader.viewport().wireframer().init_special_areas(
                headobj.data, special_indices, special_color)

    def _init_wireframer_colors(self, opacity):
        settings = get_main_settings()
        head = settings.get_head(settings.current_headnum)
        headobj = head.headobj

        FBLoader.viewport().wireframer().init_geom_data(headobj)
        FBLoader.viewport().wireframer().init_edge_indices(headobj)

        FBLoader.viewport().wireframer().init_color_data(
            (*settings.wireframe_color, opacity * settings.wireframe_opacity))
        self._coloring_special_parts(headobj, opacity)

        FBLoader.viewport().wireframer().create_batches()

    def _delete_found_pin(self, nearest, context):
        logger = logging.getLogger(__name__)
        settings = get_main_settings()
        headnum = settings.current_headnum
        camnum = settings.current_camnum
        head = settings.get_head(headnum)
        kid = settings.get_keyframe(headnum, camnum)
        cam = head.get_camera(camnum)
        camobj = cam.camobj

        fb = FBLoader.get_builder()
        fb.remove_pin(kid, nearest)
        del FBLoader.viewport().spins[nearest]
        logging.debug("PIN REMOVED {}".format(nearest))

        FBLoader.rigidity_setup()
        fb.set_focal_length_estimation(head.auto_focal_estimation)

        try:
            fb.solve_for_current_pins(kid)
        except pkt.module().UnlicensedException:
            settings.force_out_pinmode = True
            settings.license_error = True
            FBLoader.out_pinmode(headnum, camnum)
            logger.error("PINMODE LICENSE EXCEPTION")
            return {'FINISHED'}

        FBLoader.auto_focal_estimation_post(head, camobj)

        FBLoader.update_pins_count(headnum, camnum)
        coords.update_head_mesh(fb, head.headobj)
        FBLoader.update_all_camera_positions(headnum)
        FBLoader.viewport().update_surface_points(fb, head.headobj, kid)
        FBLoader.shader_update(head.headobj)
        # Save result
        FBLoader.fb_save(headnum, camnum)
        manipulate.push_head_state_in_undo_history(head, 'Pin remove')

        FBLoader.viewport().create_batch_2d(context)
        return {"RUNNING_MODAL"}

    def _undo_detected(self):
        settings = get_main_settings()
        headnum = settings.current_headnum
        camnum = settings.current_camnum
        head = settings.get_head(headnum)

        head.need_update = False
        # Reload pins surface points
        FBLoader.load_all(headnum, camnum)
        kid = settings.get_keyframe(headnum, camnum)
        FBLoader.viewport().update_surface_points(
            FBLoader.get_builder(), head.headobj, kid)

        FBLoader.shader_update(head.headobj)

        FBDebug.add_event_to_queue('UNDO_CALLED', 0, 0)
        FBDebug.add_event_to_queue('FORCE_SNAPSHOT', 0, 0)
        FBDebug.make_snapshot()

    def on_right_mouse_press(self, context, mouse_x, mouse_y):
        FBDebug.add_event_to_queue(
            'IN_PINMODE_PRESS_RIGHTMOUSE', mouse_x, mouse_y,
            coords.get_raw_camera_2d_data(context))

        FBLoader.viewport().update_view_relative_pixel_size(context)

        x, y = coords.get_image_space_coord(mouse_x, mouse_y, context)

        nearest, dist2 = coords.nearest_point(x, y, FBLoader.viewport().spins)
        if nearest >= 0 and dist2 < FBLoader.viewport().tolerance_dist2():
            return self._delete_found_pin(nearest, context)

        FBLoader.viewport().create_batch_2d(context)
        return {"RUNNING_MODAL"}

    def on_left_mouse_press(self, context, mouse_x, mouse_y):
        FBLoader.viewport().update_view_relative_pixel_size(context)

        FBDebug.add_event_to_queue(
            'DRAW_OPERATOR_PRESS_LEFTMOUSE',
            (mouse_x, mouse_y), coords.get_raw_camera_2d_data(context))

        if not coords.is_in_area(context, mouse_x, mouse_y):
            return {'PASS_THROUGH'}

        if coords.is_safe_region(context, mouse_x, mouse_y):
            FBDebug.add_event_to_queue(
                'CALL_MOVE_PIN_OPERATOR', mouse_x, mouse_y,
                coords.get_raw_camera_2d_data(context))

            settings = get_main_settings()

            # Movepin operator Call
            op = getattr(get_operators(), Config.fb_movepin_callname)
            op('INVOKE_DEFAULT', pinx=mouse_x, piny=mouse_y,
               headnum=settings.current_headnum,
               camnum=settings.current_camnum)
            return {'PASS_THROUGH'}

        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        logger = logging.getLogger(__name__)
        args = (self, context)
        settings = get_main_settings()
        head = settings.get_head(self.headnum)
        headobj = head.headobj

        logger.debug("PINMODE ENTER: CH{} CC{}".format(
            settings.current_headnum, settings.current_camnum))

        if not FBLoader.check_mesh(headobj):
            logger.error("MESH IS CORRUPTED")
            warn = getattr(get_operators(), Config.fb_warning_callname)
            warn('INVOKE_DEFAULT', msg=ErrorType.MeshCorrupted)
            return {'CANCELLED'}

        # We had to finish last operation if we are in Pinmode
        if settings.pinmode:
            if settings.current_headnum >= 0 and settings.current_camnum >= 0:
                FBLoader.out_pinmode(
                    settings.current_headnum,
                    settings.current_camnum
                )
                logger.debug("PINMODE FORCE FINISH: H{} C{}".format(
                    settings.current_headnum, settings.current_camnum))
        else:
            FBLoader.builder().sync_version(head.mod_ver)
            head.mod_ver = FBLoader.get_builder_version()

        if not settings.check_heads_and_cams():
            self._fix_heads_with_warning()
            return {'FINISHED'}

        hide_ui_elements()

        # Current headnum & camnum in global settings object
        settings.current_headnum = self.headnum
        settings.current_camnum = self.camnum

        logger.debug("PINMODE START H{} C{}".format(self.headnum, self.camnum))
        FBDebug.add_event_to_queue(
            'PINMODE_START', self.headnum, self.camnum,
            coords.get_raw_camera_2d_data(context))

        FBLoader.load_all(self.headnum, self.camnum)

        # Hide geometry
        headobj.hide_set(True)
        cameras.hide_other_cameras(self.headnum, self.camnum)
        # Start our shader
        self._init_wireframer_colors(settings.overall_opacity)
        FBLoader.viewport().create_batch_2d(context)
        FBLoader.viewport().register_handlers(args, context)
        context.window_manager.modal_handler_add(self)

        kid = settings.get_keyframe(self.headnum, self.camnum)
        # Load 3D pins
        FBLoader.viewport().update_surface_points(
            FBLoader.get_builder(), headobj, kid)

        # Can start much more times when not out from pinmode
        if not settings.pinmode:
            logger.debug("STOPPER START")
            FBStopShaderTimer.start()
        settings.pinmode = True
        return {"RUNNING_MODAL"}

    def _wireframe_view_toggle(self):
        logger = logging.getLogger(__name__)
        settings = get_main_settings()

        settings.overall_opacity = \
            0.0 if settings.overall_opacity > 0.5 else 1.0
        logger.debug("OVERALL_OPACITY BY TAB {}".format(
            settings.overall_opacity))
        self._init_wireframer_colors(settings.overall_opacity)
        force_ui_redraw("VIEW_3D")

    def modal(self, context, event):
        logger = logging.getLogger(__name__)
        settings = get_main_settings()

        headnum = settings.current_headnum
        camnum = settings.current_camnum
        head = settings.get_head(headnum)

        # Quit if Screen changed
        if context.area is None:  # Different operation Space
            logger.debug("CONTEXT LOST")
            FBLoader.out_pinmode(headnum, camnum)
            return {'FINISHED'}

        if headnum < 0:
            logger.error("HEAD LOST")
            FBLoader.out_pinmode(headnum, camnum)
            return {'FINISHED'}

        if not head.headobj.hide_get():
            logger.debug("FORCE MESH HIDE")
            head.headobj.hide_set(True)

        # Quit if Force Pinmode Out flag is set (by ex. license, pin problem)
        if settings.force_out_pinmode:
            logger.debug("FORCE PINMODE OUT")
            FBLoader.out_pinmode(headnum, camnum)
            settings.force_out_pinmode = False
            if settings.license_error:
                # Show License Warning
                warn = getattr(get_operators(), Config.fb_warning_callname)
                warn('INVOKE_DEFAULT', msg=ErrorType.NoLicense)
                settings.license_error = False
            return {'FINISHED'}

        # Quit when camera rotated by user
        if context.space_data.region_3d.view_perspective != 'CAMERA':
            logger.debug("CAMERA ROTATED PINMODE OUT")
            FBLoader.out_pinmode(headnum, camnum)
            return {'FINISHED'}

        if event.type == 'ESC':
            FBLoader.out_pinmode(headnum, camnum)
            # --- PROFILING ---
            if FBLoader.viewport().profiling:
                pr = FBLoader.viewport().pr
                pr.dump_stats('facebuilder.pstat')
            # --- PROFILING ---
            bpy.ops.view3d.view_camera()
            return {'FINISHED'}

        if event.value == 'PRESS' and event.type == 'TAB':
            self._wireframe_view_toggle()
            return {'RUNNING_MODAL'}

        if event.value == 'PRESS' and event.type == 'LEFTMOUSE':
            return self.on_left_mouse_press(
                context, event.mouse_region_x, event.mouse_region_y)

        if event.value == 'PRESS' and event.type == 'RIGHTMOUSE':
            return self.on_right_mouse_press(
                context, event.mouse_region_x, event.mouse_region_y)

        # SHIFT-press control
        if event.type in {'LEFT_SHIFT', 'RIGHT_SHIFT'} \
                and event.value == 'PRESS':
            self._set_shift_pressed(True)

        if event.type in {'LEFT_SHIFT', 'RIGHT_SHIFT'} \
                and event.value == 'RELEASE':
            self._set_shift_pressed(False)

        return self.on_final(context, head)

    def on_final(self, context, head):
        logger = logging.getLogger(__name__)
        settings = get_main_settings()
        headnum = settings.current_headnum
        camnum = settings.current_camnum
        kid = settings.get_keyframe(headnum, camnum)

        if head.need_update:
            # Undo was called so Model redraw is needed
            logger.debug("UNDO CALL DETECTED")
            self._undo_detected()

        # Catch if wireframer is off
        if not (FBLoader.viewport().wireframer().is_working()):
            logger.debug("WIREFRAME IS OFF")
            FBLoader.out_pinmode(headnum, camnum)
            return {'FINISHED'}

        FBLoader.viewport().create_batch_2d(context)
        FBLoader.viewport().update_residuals(
            FBLoader.get_builder(), context, head.headobj, kid)

        if FBLoader.viewport().current_pin:
            return {"RUNNING_MODAL"}
        else:
            return {"PASS_THROUGH"}
