# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2019-2022  KeenTools

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

from typing import Any, Set, Optional, Tuple
from uuid import uuid4
from copy import deepcopy

from bpy.types import Area, Operator
from bpy.props import IntProperty, StringProperty, FloatProperty

from ..utils.kt_logging import KTLogger
from ..addon_config import get_operator, fb_pinmode
from ..geotracker_config import GTConfig, get_gt_settings, get_current_geotracker_item
from .gtloader import GTLoader
from ..utils.coords import (point_is_in_area,
                            point_is_in_service_region,
                            get_image_space_coord,
                            nearest_point,
                            change_near_and_far_clip_planes,
                            get_camera_border)

from ..utils.manipulate import (force_undo_push,
                                switch_to_camera,
                                object_is_on_view_layer)
from ..utils.other import (hide_viewport_ui_elements_and_store_on_object,
                           unhide_viewport_ui_elements_from_object)
from ..utils.images import (set_background_image_by_movieclip,
                            set_background_image_mask)
from ..utils.bpy_common import (bpy_current_frame,
                                bpy_background_mode,
                                bpy_is_animation_playing,
                                bpy_view_camera,
                                bpy_render_frame)
from ..utils.video import fit_render_size
from .utils.prechecks import common_checks
from .ui_strings import buttons


_log = KTLogger(__name__)


def _calc_adaptive_opacity(area):
    settings = get_gt_settings()
    rx, ry = bpy_render_frame()
    x1, y1, x2, y2 = get_camera_border(area)
    settings.adaptive_opacity = (x2 - x1) / rx
    vp = GTLoader.viewport()
    vp.update_wireframe_colors()


_playback_mode: bool = False


def _playback_message():
    global _playback_mode
    current_playback_mode = bpy_is_animation_playing()
    if current_playback_mode != _playback_mode:
        _playback_mode = current_playback_mode
        vp = GTLoader.viewport()
        if _playback_mode:
            vp.message_to_screen([
                {'text': 'Playback animation',
                 'color': (0., 1., 0., 0.85),
                 'size': 24,
                 'y': 60},  # line 1
                {'text': 'ESC: Exit | TAB: Hide/Show',
                 'color': (1., 1., 1., 0.5),
                 'size': 20,
                 'y': 30}])  # line 2
        else:
            vp.revert_default_screen_message()


class GT_OT_PinMode(Operator):
    bl_idname = GTConfig.gt_pinmode_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'INTERNAL'}

    geotracker_num: IntProperty(default=-1)
    pinmode_id: StringProperty(default='')

    camera_clip_start: FloatProperty(default=0.1)
    camera_clip_end: FloatProperty(default=1000.0)

    _shift_pressed: bool = False
    _prev_camera_state: Tuple = ()
    _prev_area_state: Tuple = ()

    @classmethod
    def _check_camera_state_changed(cls, rv3d: Any) -> bool:
        camera_state = (rv3d.view_camera_zoom, *rv3d.view_camera_offset)
        if camera_state != cls._prev_camera_state:
            cls._prev_camera_state = camera_state
            return True
        return False

    @classmethod
    def _check_area_state_changed(cls, area: Area) -> bool:
        area_state = (area.x, area.y, area.width, area.height)
        if area_state != cls._prev_area_state:
            cls._prev_area_state = area_state
            return True
        return False

    @classmethod
    def _set_shift_pressed(cls, val: bool) -> None:
        cls._shift_pressed = val

    @classmethod
    def _is_shift_pressed(cls) -> bool:
        return cls._shift_pressed

    def _on_left_mouse_press(self, area: Area, event: Any) -> Set:
        mouse_x, mouse_y = event.mouse_region_x, event.mouse_region_y
        vp = GTLoader.viewport()
        vp.update_view_relative_pixel_size(area)

        if not point_is_in_area(area, mouse_x, mouse_y):
            _log.output('LEFT CLICK OUTSIDE OF VIEWPORT AREA')
            return {'PASS_THROUGH'}

        if point_is_in_service_region(area, mouse_x, mouse_y):
            _log.output('LEFT CLICK IN SERVICE REGION OF AREA')
            return {'PASS_THROUGH'}

        if not vp.points2d().is_visible():
            _log.output('OBJECT IS IN EDIT MODE. LEFT CLICK HAS BEEN IGNORED')
            return {'PASS_THROUGH'}

        pins = vp.pins()
        if not pins.get_add_selection_mode():
            op = get_operator(GTConfig.gt_movepin_idname)
            op('INVOKE_DEFAULT', pinx=mouse_x, piny=mouse_y,
               camera_clip_start=self.camera_clip_start,
               camera_clip_end=self.camera_clip_end)
            return {'PASS_THROUGH'}

        x, y = get_image_space_coord(mouse_x, mouse_y, area)
        nearest, dist2 = nearest_point(x, y, vp.pins().arr())
        if nearest >= 0 and dist2 < vp.tolerance_dist2():
            _log.output(f'CHANGE SELECTION PIN FOUND: {nearest}')
            pins.set_current_pin_num(nearest)
            selected_pins = pins.get_selected_pins()

            if nearest in selected_pins:
                pins.exclude_selected_pin(nearest)
            else:
                pins.add_selected_pins([nearest])
        else:
            settings = get_gt_settings()
            settings.start_selection(mouse_x, mouse_y)
        GTLoader.update_viewport_shaders()
        vp.tag_redraw()
        return {'PASS_THROUGH'}

    def _on_right_mouse_press(self, area: Area, event: Any) -> Set:
        mouse_x, mouse_y = event.mouse_region_x, event.mouse_region_y

        if not point_is_in_area(area, mouse_x, mouse_y):
            _log.output('RIGHT CLICK OUTSIDE OF VIEWPORT AREA')
            return {'PASS_THROUGH'}

        if point_is_in_service_region(area, mouse_x, mouse_y):
            _log.output('RIGHT CLICK IN SERVICE REGION OF AREA')
            return {'PASS_THROUGH'}

        vp = GTLoader.viewport()
        vp.update_view_relative_pixel_size(area)
        x, y = get_image_space_coord(mouse_x, mouse_y, area)

        nearest, dist2 = nearest_point(x, y, vp.pins().arr())
        if nearest >= 0 and dist2 < vp.tolerance_dist2():
            return self._delete_found_pin(nearest, area)

        vp.pins().clear_selected_pins()
        vp.create_batch_2d(area)
        vp.tag_redraw()
        return {'RUNNING_MODAL'}

    def _delete_found_pin(self, nearest: int, area: Area) -> Set:
        gt = GTLoader.kt_geotracker()
        gt.remove_pin(nearest)
        GTLoader.viewport().pins().remove_pin(nearest)
        _log.output('PIN REMOVED {}'.format(nearest))

        geotracker = get_current_geotracker_item()
        if not geotracker:
            return {'FINISHED'}

        kid = bpy_current_frame()
        GTLoader.safe_keyframe_add(kid)

        if not GTLoader.solve():
            _log.error('DELETE PIN PROBLEM')
            return {'FINISHED'}

        GTLoader.load_pins_into_viewport()
        GTLoader.place_object_or_camera()

        vp = GTLoader.viewport()
        vp.update_surface_points(gt, geotracker.geomobj, kid)

        if not geotracker.camera_mode():
            wf = vp.wireframer()
            wf.init_geom_data_from_mesh(geotracker.geomobj)
            wf.create_batches()

        vp.create_batch_2d(area)
        vp.update_residuals(gt, area, kid)
        vp.tag_redraw()

        GTLoader.save_geotracker()
        force_undo_push('Delete GeoTracker pin')
        return {'RUNNING_MODAL'}

    def _new_pinmode_id(self) -> None:
        settings = get_gt_settings()
        self.pinmode_id = str(uuid4())
        settings.pinmode_id = self.pinmode_id

    def _init_pinmode(self, area: Area, context: Optional[Any]=None) -> None:
        if not GTLoader.load_geotracker():
            _log.output('NEW KT_GEOTRACKER')
            GTLoader.new_kt_geotracker()

        _log.output('GT START SHADERS')
        GTLoader.load_pins_into_viewport()

        settings = get_gt_settings()
        settings.reload_mask_2d()
        _calc_adaptive_opacity(area)

        vp = GTLoader.viewport()
        vp.create_batch_2d(area)
        _log.output('GT REGISTER SHADER HANDLERS')
        GTLoader.update_viewport_shaders(area, normals=settings.lit_wireframe)

        geotracker = get_current_geotracker_item()
        self.camera_clip_start = geotracker.camobj.data.clip_start
        self.camera_clip_end = geotracker.camobj.data.clip_end
        if GTConfig.auto_increase_far_clip_distance and geotracker.camobj and \
                change_near_and_far_clip_planes(geotracker.camobj, geotracker.geomobj,
                                                prev_clip_start=self.camera_clip_start,
                                                prev_clip_end=self.camera_clip_end):
            near = geotracker.camobj.data.clip_start
            far = geotracker.camobj.data.clip_end
            default_txt = deepcopy(vp.texter().get_default_text())
            default_txt[0]['text'] = f'Camera clip planes ' \
                                     f'have been changed ' \
                                     f'to {near:.1f} / {far:.1f}'
            default_txt[0]['color'] = (1.0, 0.0, 1.0, 0.85)
            GTLoader.viewport().message_to_screen(default_txt)

        if context is not None:
            vp.register_handlers(context)
        vp.tag_redraw()

    def _start_new_pinmode(self, context: Any) -> None:
        _log.output('_start_new_pinmode')
        settings = get_gt_settings()
        settings.pinmode = True
        self._new_pinmode_id()
        _log.output(f'_new_pinmode_id: {settings.pinmode_id}')

        self._set_new_geotracker(context.area)
        self._init_pinmode(context.area, context)

    def _set_new_geotracker(self, area: Area, num: Optional[int]=None) -> None:
        _log.output(f'_set_new_geotracker: area={id(area)} num={num}')
        settings = get_gt_settings()
        if num is not None:
            settings.change_current_geotracker(num)
        geotracker = settings.get_current_geotracker_item()

        set_background_image_by_movieclip(geotracker.camobj,
                                          geotracker.movie_clip)
        set_background_image_mask(geotracker.camobj, geotracker.mask_2d)

        GTLoader.place_object_or_camera()
        switch_to_camera(area, geotracker.camobj,
                         geotracker.animatable_object())

        hide_viewport_ui_elements_and_store_on_object(area, geotracker.geomobj)

    def _switch_to_new_geotracker(self, num: int) -> None:
        _log.output('_switch_to_new_geotracker')
        settings = get_gt_settings()
        settings.pinmode = True

        area = GTLoader.get_work_area()
        old_geotracker = settings.get_current_geotracker_item()
        unhide_viewport_ui_elements_from_object(area, old_geotracker.geomobj)

        self._set_new_geotracker(area, num)
        self._init_pinmode(area)

    def _change_wireframe_visibility(self, *, toggle: bool=True,
                                     value: bool=True) -> None:
        vp = GTLoader.viewport()
        flag = not vp.wireframer().is_visible() if toggle else value
        vp.set_visible(flag)
        if flag:
            vp.revert_default_screen_message(unregister=False)
        else:
            default_txt = deepcopy(vp.texter().get_default_text())
            default_txt[0]['text'] = 'Wireframe is hidden. Press Tab to reveal'
            default_txt[0]['color'] = (1., 0., 1., 0.85)
            GTLoader.viewport().message_to_screen(default_txt)

    def invoke(self, context: Any, event: Any) -> Set:
        _log.output(f'INVOKE PINMODE: {self.geotracker_num}')

        check_status = common_checks(object_mode=True, is_calculating=True,
                                     reload_geotracker=True, geotracker=True,
                                     camera=True, geometry=True,
                                     movie_clip=False)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        if fb_pinmode():
            msg = 'Cannot start while FaceBuilder is in Pin mode!'
            _log.error(msg)
            self.report({'ERROR'}, msg)
            return {'CANCELLED'}

        settings = get_gt_settings()
        old_geotracker_num = settings.current_geotracker_num
        new_geotracker_num = old_geotracker_num if \
            self.geotracker_num == -1 else self.geotracker_num

        if not settings.is_proper_geotracker_number(new_geotracker_num):
            _log.error(f'WRONG GEOTRACKER NUMBER: {new_geotracker_num}')
            return {'CANCELLED'}

        vp = GTLoader.viewport()
        vp.pins().on_start()
        self._change_wireframe_visibility(toggle=False, value=True)

        if settings.pinmode and not vp.is_working():
            _log.error(f'VIEWPORT DOES NOT WORK IN PINMODE -- FIX IT')
            settings.pinmode = False

        if settings.pinmode and old_geotracker_num == new_geotracker_num and vp.is_working():
            _log.output(f'SAME GEOTRACKER. NOTHING TO DO: {new_geotracker_num}')
            return {'CANCELLED'}

        new_geotracker = settings.get_geotracker_item(new_geotracker_num)

        if not new_geotracker.geomobj or \
                not object_is_on_view_layer(new_geotracker.geomobj):
            msg = f'No Geometry object in GeoTracker {new_geotracker_num}'
            _log.error(msg)
            self.report({'INFO'}, msg)
            return {'CANCELLED'}

        if not new_geotracker.camobj:
            msg = f'No Camera object in GeoTracker {new_geotracker_num}'
            _log.error(msg)
            self.report({'INFO'}, msg)
            return {'CANCELLED'}

        _log.output('GEOTRACKER PINMODE CHECKS PASSED')

        fit_render_size(new_geotracker.movie_clip)
        if settings.pinmode:
            self._switch_to_new_geotracker(new_geotracker_num)
            return {'FINISHED'}

        settings.change_current_geotracker(new_geotracker_num)
        _log.output(f'START GEOTRACKER PINMODE: {new_geotracker_num}')

        self._start_new_pinmode(context)
        GTLoader.start_shader_timer(settings.pinmode_id)
        context.window_manager.modal_handler_add(self)
        GTLoader.register_undo_redo_handlers()
        vp.unhide_all_shaders()
        _log.output('PINMODE STARTED')
        return {'RUNNING_MODAL'}

    def modal(self, context: Any, event: Any) -> Set:
        settings = get_gt_settings()
        vp = GTLoader.viewport()

        if self.pinmode_id != settings.pinmode_id:
            _log.output('Extreme GeoTracker pinmode operator stop')
            _log.output(f'{self.pinmode_id} != {settings.pinmode_id}')
            return {'FINISHED'}

        if not context.space_data:
            _log.output('VIEWPORT IS CLOSED')
            GTLoader.out_pinmode()
            return {'FINISHED'}

        if context.space_data.region_3d.view_perspective != 'CAMERA':
            if settings.preferences().prevent_gt_view_rotation:
                # Return back to the camera view
                bpy_view_camera()
            else:
                _log.output('CAMERA ROTATED PINMODE OUT')
                GTLoader.out_pinmode()
                return {'FINISHED'}

        _playback_message()

        if event.type in {'LEFT_SHIFT', 'RIGHT_SHIFT'} \
                and event.value == 'PRESS':
            self._set_shift_pressed(True)
            if not settings.selection_mode:
                vp.pins().set_add_selection_mode(True)

        if event.type in {'LEFT_SHIFT', 'RIGHT_SHIFT'} \
                and event.value == 'RELEASE':
            self._set_shift_pressed(False)
            if not settings.selection_mode:
                vp.pins().set_add_selection_mode(False)

        if settings.selection_mode:
            if event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
                settings.end_selection(context.area, event.mouse_region_x, event.mouse_region_y)
                GTLoader.update_viewport_shaders()
            else:
                settings.do_selection(event.mouse_region_x, event.mouse_region_y)
            vp.tag_redraw()
            return {'RUNNING_MODAL'}

        if event.type == 'ESC' and event.value == 'PRESS':
            if settings.selection_mode:
                settings.cancel_selection()
                settings.set_add_selection_mode(False)
                vp.tag_redraw()
                return {'RUNNING_MODAL'}
            if not bpy_background_mode() and bpy_is_animation_playing():
                _log.output('STOP ANIMATION PLAYBACK')
                return {'PASS_THROUGH'}
            _log.output('Exit pinmode by ESC')
            GTLoader.out_pinmode()
            return {'FINISHED'}

        if event.type == 'TAB' and event.value == 'PRESS':
            if point_is_in_area(context.area,
                                event.mouse_region_x, event.mouse_region_y):
                self._change_wireframe_visibility()
                vp.tag_redraw()
                return {'RUNNING_MODAL'}

        if GTLoader.geomobj_mode_changed_to_object():
            _log.output(_log.color('green', 'RETURNED TO OBJECT_MODE'))
            self._change_wireframe_visibility(toggle=False, value=True)
            GTLoader.update_viewport_shaders()

        if self._check_camera_state_changed(context.space_data.region_3d) \
                or self._check_area_state_changed(GTLoader.get_work_area()):
            _log.output('FORCE TAG REDRAW BY VIEWPORT ZOOM/OFFSET')

            _calc_adaptive_opacity(context.area)
            vp.create_batch_2d(context.area)
            vp.update_residuals(GTLoader.kt_geotracker(), context.area,
                                bpy_current_frame())
            vp.tag_redraw()

        if event.type == 'TIMER' and GTLoader.get_stored_geomobj_mode() == 'EDIT':
            _log.output('TIMER IN EDIT_MODE')
            vp.message_to_screen([
                {'text': 'Object is in EDIT MODE',
                 'color': (1., 0., 1., 0.85),
                 'size': 24,
                 'y': 60},  # line 1
                {'text': 'ESC: Exit | TAB: Hide/Show',
                 'color': (1., 1., 1., 0.5),
                 'size': 20,
                 'y': 30}])  # line 2
            GTLoader.update_geomobj_mesh()
            vp.hide_pins_and_residuals()
            settings = get_gt_settings()
            settings.lit_wireframe = False
            GTLoader.update_viewport_shaders()
            return {'PASS_THROUGH'}

        if event.value == 'PRESS' and event.type == 'LEFTMOUSE':
            return self._on_left_mouse_press(context.area, event)

        if event.value == 'PRESS' and event.type == 'RIGHTMOUSE':
            return self._on_right_mouse_press(context.area, event)

        return {'PASS_THROUGH'}
