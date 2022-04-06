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
from uuid import uuid4
import numpy as np

import bpy

from .utils import manipulate, coords, cameras
from .config import Config, get_main_settings, get_operator, ErrorType
from .fbloader import FBLoader
from .utils.focal_length import update_camera_focal
from .utils.other import (FBStopShaderTimer, force_ui_redraw,
                          hide_viewport_ui_elements_and_store_on_object)
from .utils.html import split_long_string


_undo_handler = None


def undo_handler(scene):
    logger = logging.getLogger(__name__)
    logger.debug('undo_handler')
    try:
        settings = get_main_settings()
        if not settings.pinmode or settings.current_headnum < 0:
            unregister_undo_handler()
            return
        head = settings.get_head(settings.current_headnum)
        head.need_update = True
    except Exception as err:
        logger.error('undo_handler {}'.format(str(err)))
        unregister_undo_handler()


def unregister_undo_handler():
    global _undo_handler
    if _undo_handler is not None:
        if _undo_handler in bpy.app.handlers.undo_post:
            bpy.app.handlers.undo_post.remove(_undo_handler)
    _undo_handler = None


def register_undo_handler():
    global _undo_handler
    unregister_undo_handler()
    _undo_handler = undo_handler
    bpy.app.handlers.undo_post.append(_undo_handler)


class FB_OT_PinMode(bpy.types.Operator):
    """ On Screen Face Builder Draw Operator """
    bl_idname = Config.fb_pinmode_idname
    bl_label = "FaceBuilder Pinmode"
    bl_description = "Operator for in-Viewport drawing"
    bl_options = {'REGISTER', 'INTERNAL'}

    headnum: bpy.props.IntProperty(default=0)
    camnum: bpy.props.IntProperty(default=0)

    pinmode_id: bpy.props.StringProperty(default='')

    _shift_pressed = False
    _prev_camera_state = ()

    @classmethod
    def _check_camera_state_changed(cls, rv3d):
        camera_state = (rv3d.view_camera_zoom, rv3d.view_camera_offset)

        if camera_state != cls._prev_camera_state:
            cls._prev_camera_state = camera_state
            return True

        return False

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
            warn = get_operator(Config.fb_warning_idname)
            warn('INVOKE_DEFAULT', msg=ErrorType.SceneDamaged)

    def _init_wireframer_colors(self, opacity):
        settings = get_main_settings()
        head = settings.get_head(settings.current_headnum)

        wf = FBLoader.viewport().wireframer()
        wf.init_colors((settings.wireframe_color,
                       settings.wireframe_special_color,
                       settings.wireframe_midline_color),
                       settings.wireframe_opacity * opacity)

        fb = FBLoader.get_builder()
        if not wf.init_wireframe_image(fb, settings.show_specials):
            wf.switch_to_simple_shader()

        wf.init_geom_data_from_fb(fb, head.headobj,
                                  head.get_keyframe(settings.current_camnum))
        wf.init_edge_indices(fb)
        wf.create_batches()

    def _delete_found_pin(self, nearest, context):
        logger = logging.getLogger(__name__)
        settings = get_main_settings()
        headnum = settings.current_headnum
        camnum = settings.current_camnum
        head = settings.get_head(headnum)
        kid = settings.get_keyframe(headnum, camnum)

        fb = FBLoader.get_builder()
        fb.remove_pin(kid, nearest)
        del FBLoader.viewport().pins().arr()[nearest]
        logging.debug('PIN REMOVED {}'.format(nearest))

        if not FBLoader.solve(headnum, camnum):
            logger.error('DELETE PIN PROBLEM')
            unregister_undo_handler()
            return {'FINISHED'}

        if head.should_reduce_pins():
            if fb.pins_count(kid) > 0:
                fb.reduce_pins()

        coords.update_head_mesh_non_neutral(fb, head)
        FBLoader.update_camera_pins_count(headnum, camnum)

        FBLoader.update_all_camera_positions(headnum)
        # Save result
        FBLoader.save_fb_serial_and_image_pathes(headnum)
        manipulate.push_head_in_undo_history(head, 'Pin Remove')

        FBLoader.load_pins_into_viewport(headnum, camnum)
        FBLoader.update_viewport_shaders(context, headnum, camnum)

        return {"RUNNING_MODAL"}

    def _undo_detected(self, context):
        logger = logging.getLogger(__name__)
        logger.debug('UNDO DETECTED')
        settings = get_main_settings()
        headnum = settings.current_headnum
        camnum = settings.current_camnum
        head = settings.get_head(headnum)

        head.need_update = False
        FBLoader.load_model(headnum)
        FBLoader.place_camera(headnum, camnum)
        FBLoader.load_pins_into_viewport(headnum, camnum)
        FBLoader.update_viewport_shaders(context, headnum, camnum)

    def _on_right_mouse_press(self, context, mouse_x, mouse_y):
        vp = FBLoader.viewport()
        vp.update_view_relative_pixel_size(context)

        x, y = coords.get_image_space_coord(mouse_x, mouse_y, context)

        nearest, dist2 = coords.nearest_point(x, y, vp.pins().arr())
        if nearest >= 0 and dist2 < FBLoader.viewport().tolerance_dist2():
            return self._delete_found_pin(nearest, context)

        FBLoader.viewport().create_batch_2d(context)
        return {"RUNNING_MODAL"}

    def _on_left_mouse_press(self, context, mouse_x, mouse_y):
        FBLoader.viewport().update_view_relative_pixel_size(context)

        if not coords.is_in_area(context, mouse_x, mouse_y):
            return {'PASS_THROUGH'}

        if coords.is_safe_region(context, mouse_x, mouse_y):
            settings = get_main_settings()
            # Movepin operator Call
            op = get_operator(Config.fb_movepin_idname)
            op('INVOKE_DEFAULT', pinx=mouse_x, piny=mouse_y,
               headnum=settings.current_headnum,
               camnum=settings.current_camnum)
            return {'PASS_THROUGH'}

        return {'PASS_THROUGH'}

    def _check_keyframes(self, fb, head):
        for cam in head.cameras:
            if not fb.is_key_at(cam.get_keyframe()):
                return False
        return True

    def invoke(self, context, event):
        logger = logging.getLogger(__name__)
        args = (self, context)
        settings = get_main_settings()

        logger.debug('PINMODE ENTER. CURRENT_HEAD: {} CURRENT_CAM: {}'.format(
            settings.current_headnum, settings.current_camnum))

        if not settings.check_heads_and_cams():
            self._fix_heads_with_warning()
            return {'CANCELLED'}

        head = settings.get_head(self.headnum)
        if not head or not head.headobj:
            logger.error('CANNOT FIND head or headobj')
            return {'CANCELLED'}
        headobj = head.headobj
        first_start = True

        vp = FBLoader.viewport()
        # Stopped shaders means that we need to restart pinmode
        if not vp.wireframer().is_working():
            settings.pinmode = False

        if settings.wrong_pinmode_id():
            settings.pinmode = False

        # We have to fix last operation if we are in Pinmode
        if settings.pinmode and \
                settings.current_headnum >= 0 and settings.current_camnum >= 0:

            old_head = settings.get_head(settings.current_headnum)
            old_camera = old_head.get_camera(settings.current_camnum)
            old_camera.reset_tone_mapping()

            FBLoader.save_pinmode_state(settings.current_headnum)
            logger.debug("PINMODE FORCE FINISH: H{} C{}".format(
                settings.current_headnum, settings.current_camnum))
            first_start = False
        else:
            FBLoader.update_cameras_from_old_version(self.headnum)

        settings.current_headnum = self.headnum
        settings.current_camnum = self.camnum
        settings.pinmode = True

        camera = head.get_camera(settings.current_camnum)
        camera.update_scene_frame_size()
        camera.update_background_image_scale()
        kid = camera.get_keyframe()

        camera.apply_tone_mapping()

        cameras.switch_to_fb_camera(camera, context)

        logger.debug("PINMODE START H{} C{}".format(settings.current_headnum,
                                                    settings.current_camnum))
        # Start working with current model
        try:
            if not FBLoader.load_model_throw_exception(settings.current_headnum):
                raise Exception('Cannot load the model data from '
                                'the serialised string. Perhaps your file '
                                'or the scene data got corrupted.')
        except Exception as err:
            logger.error('MODEL CANNOT BE LOADED IN PINMODE')

            FBLoader.out_pinmode_without_save(self.headnum)
            cameras.exit_localview(context)

            logger.error('DESERIALIZE load_model_throw_exception: \n'
                         '{}'.format(str(err)))
            error_message = '\n'.join(split_long_string(str(err), limit=64))
            warn = get_operator(Config.fb_warning_idname)
            warn('INVOKE_DEFAULT', msg=ErrorType.CustomMessage,
                 msg_content=error_message)
            return {'CANCELLED'}

        if not FBLoader.check_mesh(headobj):
            fb = FBLoader.get_builder()
            logger.error('MESH IS CORRUPTED {} != {}'.format(
                len(headobj.data.vertices), len(fb.applied_args_vertices())))

            FBLoader.out_pinmode_without_save(self.headnum)
            cameras.exit_localview(context)

            warn = get_operator(Config.fb_warning_idname)
            warn('INVOKE_DEFAULT', msg=ErrorType.MeshCorrupted)
            return {'CANCELLED'}

        fb = FBLoader.get_builder()
        fb.set_use_emotions(head.should_use_emotions())

        if not self._check_keyframes(fb, head):
            logger.debug("PINMODE NO KEYFRAME")
            for cam in head.cameras:
                kfnum = cam.get_keyframe()
                logger.debug("UPDATE KEYFRAME: {}".format(kfnum))
                if not fb.is_key_at(kfnum):
                    logger.error('\nUNKNOWN KEYFRAME: {}\n'.format(kfnum))
                    fb.set_keyframe(kfnum, np.eye(4))
        try:
            FBLoader.place_camera(settings.current_headnum,
                                  settings.current_camnum)
        except Exception:
            logger.debug("UPDATE KEYFRAME PROBLEM")
            return {'CANCELLED'}

        FBLoader.load_pins_into_viewport(settings.current_headnum, settings.current_camnum)
        coords.update_head_mesh_non_neutral(FBLoader.get_builder(), head)

        update_camera_focal(camera, fb)

        if first_start:
            hide_viewport_ui_elements_and_store_on_object(headobj)

            logger.debug("START SHADERS")
            self._init_wireframer_colors(settings.overall_opacity)
            vp.create_batch_2d(context)
            logger.debug("REGISTER SHADER HANDLERS")
            vp.register_handlers(args, context)

            context.window_manager.modal_handler_add(self)

            logger.debug("SHADER STOPPER START")
            self.pinmode_id = str(uuid4())
            settings.pinmode_id = self.pinmode_id
            FBStopShaderTimer.start(self.pinmode_id)
            logger.debug('pinmode_id: {}'.format(self.pinmode_id))
        else:
            logger.debug("SHADER UPDATE ONLY")
            self._init_wireframer_colors(settings.overall_opacity)

        bpy.ops.view3d.view_center_camera()

        vp.update_surface_points(FBLoader.get_builder(), headobj, kid)
        manipulate.push_head_in_undo_history(head, 'Pin Mode Start.')
        if not first_start:
            logger.debug('PINMODE SWITCH ONLY')
            return {'FINISHED'}

        register_undo_handler()
        logger.debug('PINMODE STARTED')
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

    def _modal_should_finish(self, context, event):
        logger = logging.getLogger(__name__)
        settings = get_main_settings()
        headnum = settings.current_headnum

        # Quit if Screen changed
        if context.area is None:  # Different operation Space
            logger.debug("CONTEXT LOST")
            FBLoader.out_pinmode(headnum)
            return True

        if headnum < 0:
            logger.error("HEAD LOST")
            FBLoader.out_pinmode(headnum)
            return True

        # Quit if Force Pinmode Out flag is set (by ex. license, pin problem)
        if settings.force_out_pinmode:
            logger.debug("FORCE PINMODE OUT")
            FBLoader.out_pinmode(headnum)
            settings.force_out_pinmode = False
            if settings.license_error:
                # Show License Warning
                warn = get_operator(Config.fb_warning_idname)
                warn('INVOKE_DEFAULT', msg=ErrorType.NoLicense)
                settings.license_error = False
                settings.hide_user_preferences()
            return True

        # Quit when camera rotated by user
        if context.space_data.region_3d.view_perspective != 'CAMERA':
            if settings.preferences().prevent_view_rotation:
                # Return back to the camera view
                bpy.ops.view3d.view_camera()
            else:
                logger.debug("CAMERA ROTATED PINMODE OUT")
                logger.debug(context.space_data.region_3d.view_perspective)
                FBLoader.out_pinmode(headnum)
                return True

        if event.type == 'ESC' and event.value == 'RELEASE':
            FBLoader.out_pinmode(headnum)
            # --- PROFILING ---
            if FBLoader.viewport().profiling:
                pr = FBLoader.viewport().pr
                pr.dump_stats('facebuilder.pstat')
            # --- PROFILING ---
            bpy.ops.view3d.view_camera()
            return True

        return False

    def modal(self, context, event):
        logger = logging.getLogger(__name__)
        settings = get_main_settings()

        if self.pinmode_id != settings.pinmode_id:
            logger.error('Extreme pinmode operator stop')
            logger.error('{} != {}'.format(self.pinmode_id, settings.pinmode_id))
            unregister_undo_handler()
            cameras.exit_localview(context)
            return {'FINISHED'}

        headnum = settings.current_headnum
        head = settings.get_head(headnum)

        if self._modal_should_finish(context, event):
            unregister_undo_handler()
            cameras.exit_localview(context)
            return {'FINISHED'}

        if self._check_camera_state_changed(context.space_data.region_3d):
            logger.debug("FORCE TAG REDRAW")
            context.area.tag_redraw()

        if event.value == 'PRESS' and event.type == 'TAB':
            self._wireframe_view_toggle()
            return {'RUNNING_MODAL'}

        if event.value == 'PRESS' and event.type == 'LEFTMOUSE':
            return self._on_left_mouse_press(
                context, event.mouse_region_x, event.mouse_region_y)

        if event.value == 'PRESS' and event.type == 'RIGHTMOUSE':
            return self._on_right_mouse_press(
                context, event.mouse_region_x, event.mouse_region_y)

        if event.type in {'LEFT_SHIFT', 'RIGHT_SHIFT'} \
                and event.value == 'PRESS':
            self._set_shift_pressed(True)

        if event.type in {'LEFT_SHIFT', 'RIGHT_SHIFT'} \
                and event.value == 'RELEASE':
            self._set_shift_pressed(False)

        camnum = settings.current_camnum
        kid = settings.get_keyframe(headnum, camnum)

        if head.need_update:
            logger.debug("UNDO CALL DETECTED")
            self._undo_detected(context)

        vp = FBLoader.viewport()
        if not (vp.wireframer().is_working()):
            logger.debug("WIREFRAME IS OFF")
            unregister_undo_handler()
            FBLoader.out_pinmode(headnum)
            return {'FINISHED'}

        vp.create_batch_2d(context)
        vp.update_residuals(FBLoader.get_builder(), head.headobj, kid, context)

        if vp.pins().current_pin() is not None:
            return {"RUNNING_MODAL"}
        else:
            return {"PASS_THROUGH"}
