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

from typing import Any, Optional, Tuple, List
import numpy as np

import bpy
from bpy.types import Area
from mathutils import Matrix

from ..utils.kt_logging import KTLogger
from ..addon_config import Config, get_operator, ErrorType, show_user_preferences
from ..geotracker_config import get_gt_settings, get_current_geotracker_item
from .viewport import GTViewport
from ..utils.coords import (image_space_to_frame,
                            calc_bpy_camera_mat_relative_to_model,
                            calc_bpy_model_mat_relative_to_camera,
                            focal_by_projection_matrix_mm,
                            compensate_view_scale,
                            frame_to_image_space,
                            camera_sensor_width)
from ..utils.bpy_common import (bpy_render_frame,
                                bpy_current_frame,
                                get_scene_camera_shift,
                                bpy_is_animation_playing)
from .gt_class_loader import GTClassLoader
from ..utils.timer import KTStopShaderTimer
from ..utils.ui_redraw import force_ui_redraw
from ..utils.localview import exit_area_localview, check_localview
from ..utils.other import unhide_viewport_ui_elements_from_object
from ..blender_independent_packages.pykeentools_loader import module as pkt_module


_log = KTLogger(__name__)


def force_stop_gt_shaders() -> None:
    GTLoader.stop_viewport_shaders()
    force_ui_redraw('VIEW_3D')


def depsgraph_update_handler(scene, depsgraph):
    def _check_updated(depsgraph, name):
        _log.output('COUNT UPDATES: {}'.format(len(depsgraph.updates)))
        _log.output('ids: {}'.format([update.id.name for update in depsgraph.updates]))
        for update in depsgraph.updates:
            if update.id.name != name:
                continue
            if not update.is_updated_transform:
                continue
            _log.output(f'update.id: {update.id.name}')
            _log.output(f'update.is_updated_geometry: {update.is_updated_geometry}')
            _log.output(f'update.is_updated_transform: {update.is_updated_transform}')
            _log.output(f'update.is_updated_shading: {update.is_updated_shading}')
            return True
        return False

    if bpy_is_animation_playing():
        return

    settings = get_gt_settings()
    if not settings.pinmode:
        GTLoader.unregister_undo_redo_handlers()
        return
    if GTLoader.viewport().pins().move_pin_mode():
        return
    geotracker = settings.get_current_geotracker_item()
    if not geotracker:
        return

    geomobj = geotracker.geomobj
    camobj = geotracker.camobj

    if geomobj and _check_updated(depsgraph, geomobj.name):
        GTLoader.update_viewport_shaders()
        return
    if camobj and _check_updated(depsgraph, camobj.name):
        GTLoader.update_viewport_shaders()


def undo_redo_handler(scene):
    _log.output('gt_undo_handler')
    try:
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()
        vp = GTLoader.viewport()
        area = vp.get_work_area()
        if not settings.pinmode or not geotracker or not area:
            GTLoader.unregister_undo_redo_handlers()
            return

        GTLoader.load_geotracker()
        GTLoader.update_viewport_shaders(area)

    except Exception as err:
        _log.error(f'gt_undo_handler {str(err)}')
        GTLoader.unregister_undo_redo_handlers()


def is_registered(app_handlers, handler) -> bool:
    if handler is None:
        return False
    return handler in app_handlers


def register_app_handler(app_handlers, handler) -> None:
    if handler is not None:
        if handler not in app_handlers:
            app_handlers.append(handler)


def unregister_app_handler(app_handlers, handler) -> None:
    if handler is not None:
        if handler in app_handlers:
            app_handlers.remove(handler)


def frame_change_post_handler(scene) -> None:
    _log.output(f'KEYFRAME UPDATED: {scene.name}')
    settings = get_gt_settings()
    geotracker = settings.get_current_geotracker_item()
    if geotracker is None:
        _log.output('EARLY EXIT')
        return
    if settings.calculating_mode == 'ESTIMATE_FL':
        return
    geotracker.reset_focal_length_estimation()
    GTLoader.place_object_or_camera()
    GTLoader.update_viewport_shaders(wireframe=False, geomobj_matrix=True,
                                     timeline=False, mask=True)


class GTLoader:
    _viewport: Any = GTViewport()
    _geo: Any = None
    _geomobj_edit_mode: str = 'OBJECT'

    _geo_input: Any = None
    _image_input: Any = None
    _camera_input: Any = None
    _kt_geotracker: Any = None
    _mask2d: Any = None

    _check_shader_timer: Any = KTStopShaderTimer(get_gt_settings,
                                                 force_stop_gt_shaders)
    _geotracker_item: Optional[Any] = None

    @classmethod
    def get_geotracker_item(cls) -> Optional[Any]:
        return cls._geotracker_item

    @classmethod
    def set_geotracker_item(cls, geotracker: Optional[Any]):
        cls._geotracker_item = geotracker

    @classmethod
    def start_shader_timer(cls, uuid: str):
        cls._check_shader_timer.start(uuid)

    @classmethod
    def update_geomobj_mesh(cls) -> None:
        _log.output('update_geomobj_mesh UPDATE')
        geotracker = get_current_geotracker_item()
        if geotracker and geotracker.geomobj:
            geotracker.geomobj.update_from_editmode()

    @classmethod
    def get_geomobj_mode(cls) -> str:
        geotracker = get_current_geotracker_item()
        if not geotracker or not geotracker.geomobj:
            return 'OBJECT'
        return geotracker.geomobj.mode

    @classmethod
    def store_geomobj_mode(cls, mode: str='OBJECT') -> None:
        cls._geomobj_edit_mode = mode

    @classmethod
    def get_stored_geomobj_mode(cls) -> str:
        return cls._geomobj_edit_mode

    @classmethod
    def geomobj_mode_changed_to_object(cls, update: bool=True) -> bool:
        stored_mode: str = cls.get_stored_geomobj_mode()
        current_mode: str = cls.get_geomobj_mode()
        if stored_mode == current_mode:
            return False
        if update:
            cls.store_geomobj_mode(current_mode)
        if current_mode == 'OBJECT':
            return True
        return False

    @classmethod
    def viewport(cls) -> Any:
        return cls._viewport

    @classmethod
    def geo(cls) -> Any:
        return cls._geo

    @classmethod
    def new_kt_geotracker(cls) -> Any:
        _log.output(_log.color('magenta', '*** new_kt_geotracker ***'))
        cls._geo_input = GTClassLoader.GTGeoInput_class()()
        cls._image_input = GTClassLoader.GTImageInput_class()()
        cls._camera_input = GTClassLoader.GTCameraInput_class()()
        cls._mask2d = GTClassLoader.GTMask2DInput_class()()
        cls._storage = GTClassLoader.GTGeoTrackerResultsStorage_class()()

        cls._kt_geotracker = GTClassLoader.GeoTracker_class()(
            cls._geo_input,
            cls._camera_input,
            cls._image_input,
            cls._mask2d,
            cls._storage
        )
        return cls._kt_geotracker

    @classmethod
    def kt_geotracker(cls) -> Any:
        if cls._kt_geotracker is None:
            return cls.new_kt_geotracker()
        return cls._kt_geotracker

    @classmethod
    def add_pin(cls, keyframe: int, pos: Tuple[float, float]) -> Optional[Any]:
        _log.output(f'add_pin ADD PIN: {pos}')
        gt = cls.kt_geotracker()
        return gt.add_pin(keyframe, pos)

    @classmethod
    def move_pin(cls, keyframe: int, pin_idx: int, pos: Tuple[float, float],
                 shift_x: float=0.0, shift_y: float=0.0) -> None:
        gt = cls.kt_geotracker()
        if pin_idx < gt.pins_count():
            gt.move_pin(keyframe, pin_idx,
                        image_space_to_frame(*pos, shift_x, shift_y))

    @classmethod
    def delta_move_pin(cls, keyframe: int, indices: List[int],
                       offset: Tuple[float, float]) -> None:
        gt = cls.kt_geotracker()
        pins_count = gt.pins_count()
        for i in indices:
            if i < pins_count:
                x, y = gt.pin(keyframe, i).img_pos
                gt.move_pin(keyframe, i, (x + offset[0], y + offset[1]))

    @classmethod
    def load_pins_into_viewport(cls) -> None:
        keyframe = bpy_current_frame()
        vp = cls.viewport()
        gt = cls.kt_geotracker()
        w, h = bpy_render_frame()
        kt_pins = gt.projected_pins(keyframe)
        pins = vp.pins()
        pins.set_pins([frame_to_image_space(*pin.img_pos, w, h,
                                            *get_scene_camera_shift())
                       for pin in kt_pins])
        pins.set_disabled_pins([i for i, pin in enumerate(kt_pins)
                                if not pin.enabled])

    @classmethod
    def viewport_area_redraw(cls):
        vp = cls.viewport()
        vp.tag_redraw()

    @classmethod
    def place_object_or_camera(cls) -> None:
        geotracker = get_current_geotracker_item()
        if not geotracker:
            return
        gt = cls.kt_geotracker()
        keyframe = bpy_current_frame()
        if not gt.is_key_at(keyframe):
            return
        gt_model_mat = gt.model_mat(keyframe)
        if geotracker.camera_mode():
            cls.place_camera_relative_to_object(gt_model_mat)
        else:
            cls.place_object_relative_to_camera(gt_model_mat)

    @classmethod
    def place_object_relative_to_camera(cls, gt_model_mat: Any) -> None:
        geotracker = get_current_geotracker_item()
        if not geotracker or not geotracker.geomobj or not geotracker.camobj:
            return
        mat = calc_bpy_model_mat_relative_to_camera(
                geotracker.geomobj.matrix_world,
                geotracker.camobj.matrix_world, gt_model_mat)
        geotracker.geomobj.matrix_world = mat

    @classmethod
    def place_camera_relative_to_object(cls, gt_model_mat: Any) -> None:
        geotracker = get_current_geotracker_item()
        if not geotracker or not geotracker.geomobj or not geotracker.camobj:
            return

        mat = calc_bpy_camera_mat_relative_to_model(
            geotracker.geomobj.matrix_world,
            geotracker.camobj.matrix_world, gt_model_mat)
        geotracker.camobj.matrix_world = mat

    @classmethod
    def updated_focal_length(cls, force: bool=False) -> Optional[float]:
        geotracker = get_current_geotracker_item()
        if not geotracker:
            return None
        gt = GTLoader.kt_geotracker()
        frame = bpy_current_frame()
        if not force and not gt.is_key_at(frame):
            return None
        proj_mat = gt.projection_mat(frame)
        focal = focal_by_projection_matrix_mm(
            proj_mat, camera_sensor_width(geotracker.camobj))
        _log.output('FOCAL ESTIMATED: {}'.format(focal))
        return focal * compensate_view_scale()

    @classmethod
    def center_geo(cls) -> None:
        keyframe = bpy_current_frame()
        gt = cls.kt_geotracker()
        cls.safe_keyframe_add(keyframe, update=True)
        gt.center_geo(keyframe)

    @classmethod
    def calc_model_matrix(cls) -> Any:
        geotracker = get_current_geotracker_item()
        if not geotracker:
            return np.eye(4)
        return geotracker.calc_model_matrix()

    @classmethod
    def safe_keyframe_add(cls, keyframe: int, update: bool=False) -> None:
        gt = cls.kt_geotracker()
        if not gt.is_key_at(keyframe):
            mat = cls.calc_model_matrix()
            gt.set_keyframe(keyframe, mat)
        elif update:
            mat = cls.calc_model_matrix()
            gt.update_model_mat(keyframe, mat)

    @classmethod
    def solve(cls) -> bool:
        _log.output('GTloader.solve called')
        geotracker = get_current_geotracker_item()
        gt = cls.kt_geotracker()
        keyframe = bpy_current_frame()
        try:
            if geotracker.focal_length_mode == 'STATIC_FOCAL_LENGTH':
                gt.set_focal_length_mode(GTClassLoader.GeoTracker_class().FocalLengthMode.STATIC_FOCAL_LENGTH)
            elif geotracker.focal_length_mode == 'ZOOM_FOCAL_LENGTH':
                gt.set_focal_length_mode(GTClassLoader.GeoTracker_class().FocalLengthMode.ZOOM_FOCAL_LENGTH)
            else:
                gt.set_focal_length_mode(GTClassLoader.GeoTracker_class().FocalLengthMode.CAMERA_FOCAL_LENGTH)
                geotracker.focal_length_estimation = False

            gt.solve_for_current_pins(keyframe, geotracker.focal_length_estimation)

        except pkt_module().UnlicensedException as err:
            _log.error(f'solve UnlicensedException: \n{str(err)}')
            cls.out_pinmode()
            show_user_preferences(facebuilder=False, geotracker=False)
            warn = get_operator(Config.kt_warning_idname)
            warn('INVOKE_DEFAULT', msg=ErrorType.NoLicense)
            return False
        except Exception as err:
            _log.error(f'solve UNKNOWN EXCEPTION: \n{str(err)}')
            return False
        _log.output('GTloader.solve finished')
        return True

    @classmethod
    def save_geotracker(cls) -> None:
        _log.output('save_geotracker call')
        geotracker = get_current_geotracker_item()
        if not geotracker:
            return

        gt = cls.kt_geotracker()
        geotracker.save_serial_str(gt.serialize())
        geotracker.store_serial_str_on_geomobj()

    @classmethod
    def _deserialize_global_options(cls):
        settings = get_gt_settings()
        gt = cls.kt_geotracker()
        with settings.ui_write_mode_context():
            try:
                settings.wireframe_backface_culling = gt.back_face_culling()
            except Exception as err:
                _log.error(f'_deserialize_global_options:\n{str(err)}')

    @classmethod
    def load_geotracker(cls) -> bool:
        _log.output('load_geotracker')
        geotracker = get_current_geotracker_item()
        if not geotracker:
            return False

        serial = geotracker.get_serial_str()

        _log.output(_log.color('cyan', f'SERIAL:\n{serial}'))
        if serial == '':
            settings = get_gt_settings()
            _log.warning(f'EMPTY SERIAL ERROR: {settings.current_geotracker_num}')
            return False

        gt = cls.kt_geotracker()
        try:
            if not gt.deserialize(serial):
                _log.warning(f'DESERIALIZE ERROR: {serial}')
                return False
        except Exception as err:
            _log.error(f'load_geotracker Exception:\n{str(err)}')
            return False
        cls._deserialize_global_options()
        return True

    @classmethod
    def update_viewport_wireframe(cls, normals: bool=False) -> None:
        settings = get_gt_settings()
        geotracker = get_current_geotracker_item()
        if not geotracker or not geotracker.geomobj:
            return

        vp = cls.viewport()
        wf = vp.wireframer()
        wf.init_geom_data_from_mesh(geotracker.geomobj)
        if normals:
            wf.init_vertex_normals(geotracker.geomobj)
        wf.init_color_data((*settings.wireframe_color,
                            settings.wireframe_opacity * settings.get_adaptive_opacity()))
        wf.init_selection_from_mesh(geotracker.geomobj, geotracker.mask_3d,
                                    geotracker.mask_3d_inverted)
        wf.set_backface_culling(settings.wireframe_backface_culling)
        wf.set_lit_wireframe(settings.lit_wireframe)
        wf.create_batches()

    @classmethod
    def update_viewport_pins_and_residuals(cls, area: Area) -> None:
        vp = cls.viewport()
        cls.load_pins_into_viewport()
        vp.create_batch_2d(area)
        gt = cls.kt_geotracker()

        geotracker = get_current_geotracker_item()
        if not geotracker or not geotracker.geomobj:
            return

        kid = bpy_current_frame()
        vp.update_surface_points(gt, geotracker.geomobj, kid)
        vp.update_residuals(gt, area, kid)

    @classmethod
    def update_viewport_shaders(cls, area: Optional[Area]=None, *,
                                geomobj_matrix: bool = False,
                                wireframe: bool=True,
                                normals: bool=False,
                                pins_and_residuals: bool=True,
                                timeline: bool=True,
                                mask: bool=False) -> None:
        if area is None:
            vp = cls.viewport()
            area = vp.get_work_area()
            if not area:
                return
        if geomobj_matrix:
            wf = cls.viewport().wireframer()
            geotracker = get_current_geotracker_item()
            if geotracker and geotracker.geomobj:
                wf.set_object_world_matrix(geotracker.geomobj.matrix_world)
        if mask:
            geotracker = get_current_geotracker_item()
            if geotracker.mask_source == 'COMP_MASK':
                geotracker.update_compositing_mask()
        if wireframe:
            cls.update_viewport_wireframe(normals)
        if pins_and_residuals:
            cls.update_viewport_pins_and_residuals(area)
        if timeline:
            cls.update_timeline()

    @classmethod
    def _update_all_timelines(cls) -> None:
        areas = bpy.context.workspace.screens[0].areas
        for area in areas:
            if area.type == 'DOPESHEET_EDITOR':
                area.tag_redraw()

    @classmethod
    def update_timeline(cls) -> None:
        vp = GTLoader.viewport()
        timeliner = vp.timeliner()
        gt = cls.kt_geotracker()
        timeliner.set_keyframes(gt.keyframes())
        timeliner.create_batch()
        cls._update_all_timelines()

    @classmethod
    def spring_pins_back(cls) -> None:
        geotracker = get_current_geotracker_item()
        if not geotracker:
            return

        if geotracker.spring_pins_back:
            gt = cls.kt_geotracker()
            current_frame = bpy_current_frame()
            if gt.is_key_at(current_frame):
                gt.spring_pins_back(current_frame)

    @classmethod
    def get_work_area(cls) -> Optional[Area]:
        vp = cls.viewport()
        return vp.get_work_area()

    @classmethod
    def stop_viewport_shaders(cls) -> None:
        cls._check_shader_timer.stop()
        vp = cls.viewport()
        vp.unregister_handlers()
        _log.output('GT VIEWPORT SHADERS HAVE BEEN STOPPED')

    @classmethod
    def status_info(cls):
        settings = get_gt_settings()
        txt = f'settings.pinmode: {settings.pinmode}\n'
        txt += f'settings.pinmode_id: {settings.pinmode_id}\n'
        txt += f'settings.current_geotracker_num: {settings.current_geotracker_num}\n'
        area = cls.get_work_area()
        txt += f'area: {area}\n'
        txt += f'check_localview(area): {check_localview(area)}\n'
        txt += f'viewport is working: {GTLoader.viewport().is_working()}\n'
        txt += f'cls._check_shader_timer.is_active(): ' \
               f'{cls._check_shader_timer.is_active()}\n'
        txt += f'is_registered(bpy.app.handlers.undo_post, undo_redo_handler): ' \
               f'{is_registered(bpy.app.handlers.undo_post, undo_redo_handler)}\n'
        txt += f'is_registered(bpy.app.handlers.redo_post, undo_redo_handler): ' \
               f'{is_registered(bpy.app.handlers.redo_post, undo_redo_handler)}\n'
        txt += f'is_registered(bpy.app.handlers.depsgraph_update_post, ' \
               f'depsgraph_update_handler): ' \
               f'{is_registered(bpy.app.handlers.depsgraph_update_post, depsgraph_update_handler)}\n'
        txt += f'is_registered(bpy.app.handlers.frame_change_post, ' \
               f'frame_change_post_handler): ' \
               f'{is_registered(bpy.app.handlers.frame_change_post, frame_change_post_handler)}\n'
        return txt

    @classmethod
    def out_pinmode(cls) -> None:
        settings = get_gt_settings()
        _log.output(f'out_pinmode call')
        _log.output(f'\n--- Before out\n{cls.status_info()}')
        settings.pinmode = False

        cls.unregister_undo_redo_handlers()
        area = cls.get_work_area()
        cls.stop_viewport_shaders()
        try:
            exit_area_localview(area)
        except Exception as err:
            _log.error(_log.color(
                'magenta',
                f'out_pinmode CANNOT OUT FROM LOCALVIEW:\n{str(err)}'))

        settings.reset_pinmode_id()

        geotracker = cls.get_geotracker_item()
        if geotracker is None:
            geotracker = settings.get_current_geotracker_item()
        if geotracker is None:
            _log.error(f'out_pinmode error: No geotracker')
            return

        geotracker.reset_focal_length_estimation()
        if geotracker.geomobj:
            unhide_viewport_ui_elements_from_object(area, geotracker.geomobj)

        cls.set_geotracker_item(None)
        _log.output(f'\n--- After out\n{cls.status_info()}')

    @classmethod
    def register_undo_redo_handlers(cls):
        cls.unregister_undo_redo_handlers()
        register_app_handler(bpy.app.handlers.undo_post, undo_redo_handler)
        register_app_handler(bpy.app.handlers.redo_post, undo_redo_handler)
        register_app_handler(bpy.app.handlers.depsgraph_update_post,
                             depsgraph_update_handler)
        register_app_handler(bpy.app.handlers.frame_change_post,
                             frame_change_post_handler)

    @staticmethod
    def unregister_undo_redo_handlers():
        unregister_app_handler(bpy.app.handlers.frame_change_post,
                               frame_change_post_handler)
        unregister_app_handler(bpy.app.handlers.depsgraph_update_post,
                               depsgraph_update_handler)
        unregister_app_handler(bpy.app.handlers.undo_post, undo_redo_handler)
        unregister_app_handler(bpy.app.handlers.redo_post, undo_redo_handler)
