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

from typing import Any, Optional, Tuple, List
import numpy as np

import bpy
import bmesh
from bpy.types import Object, Area, Mesh

from ..utils.kt_logging import KTLogger
from ..addon_config import fb_settings
from ..facebuilder_config import FBConfig
from ..utils.coords import (xy_to_xz_rotation_matrix_3x3,
                            focal_by_projection_matrix_mm,
                            calc_model_mat)
from ..utils.focal_length import (configure_focal_mode_and_fixes,
                                  update_camera_focal)
from ..utils.attrs import mark_keentools_object, get_obj_collection
from ..facebuilder.utils.exif_reader import reload_all_camera_exif
from ..utils.timer import KTStopShaderTimer
from ..utils.ui_redraw import force_ui_redraw
from .viewport import FBViewport
from ..blender_independent_packages.pykeentools_loader import module as pkt_module
from ..utils.bpy_common import (bpy_create_object,
                                bpy_create_camera_data,
                                bpy_link_to_scene,
                                bpy_render_frame)


_log = KTLogger(__name__)


def _create_mesh_from_pydata(mesh_name: str,
                             vertices: List, faces: List) -> Mesh:
    mesh = bpy.data.meshes.new(mesh_name)

    bm = bmesh.new()
    verts = [bm.verts.new(v) for v in vertices]
    bm.verts.index_update()
    for face in faces:
        bm.faces.new(verts[i] for i in face)

    bm.to_mesh(mesh)
    bm.free()
    return mesh


def force_stop_fb_shaders() -> None:
    FBLoader.stop_viewport_shaders()
    force_ui_redraw('VIEW_3D')


class FBLoader:
    _camera_input: Optional[Any] = None
    _builder_instance: Optional[Any] = None
    _viewport: Any = FBViewport()
    _check_shader_timer: Any = KTStopShaderTimer(fb_settings,
                                                 force_stop_fb_shaders)

    @classmethod
    def start_shader_timer(cls, uuid: str) -> None:
        cls._check_shader_timer.start(uuid)

    @classmethod
    def viewport(cls) -> Any:
        return cls._viewport

    @classmethod
    def wireframer(cls) -> Any:
        vp = cls.viewport()
        return vp.wireframer()

    @classmethod
    def viewport_is_active(cls) -> bool:
        return cls.wireframer().is_working()

    @classmethod
    def new_builder(cls) -> Any:
        from .camera_input import FaceBuilderCameraInput
        cls._camera_input = FaceBuilderCameraInput()
        cls._builder_instance = pkt_module().FaceBuilder(cls._camera_input)
        return cls._builder_instance

    @classmethod
    def get_builder(cls) -> Any:
        if cls._builder_instance is not None:
            return cls._builder_instance
        return cls.new_builder()

    @classmethod
    def is_not_loaded(cls) -> bool:
        return cls._builder_instance is None

    @classmethod
    def update_cam_image_size(cls, cam_item: Any) -> None:
        cam_item.update_image_size()

    @classmethod
    def update_head_camobj_focals(cls, headnum: int) -> None:
        _log.output('update_head_camobj_focals call')
        settings = fb_settings()
        head = settings.get_head(headnum)
        if not head:
            return
        for i, c in enumerate(head.cameras):
            c.camobj.data.lens = c.focal
            _log.output(f'camera: {i} focal: {c.focal}')

    @classmethod
    def set_keentools_attributes(cls, obj: Object) -> None:
        if obj:
            mark_keentools_object(obj)

    @classmethod
    def check_mesh(cls, headobj: Object) -> bool:
        try:
            fb = cls.get_builder()
            if len(headobj.data.vertices) == len(fb.applied_args_vertices()):
                return True
        except Exception:
            pass
        return False

    @classmethod
    def in_pin_drag(cls) -> bool:
        vp = cls.viewport()
        return vp.in_pin_drag()

    @classmethod
    def save_pinmode_state(cls, headnum: int) -> None:
        cls.save_fb_serial_and_image_pathes(headnum)

        vp = cls.viewport()
        vp.pins().reset_current_pin()

        cls.update_head_camobj_focals(headnum)
        _log.output('PINMODE STATE SAVED')

    @classmethod
    def stop_viewport_shaders(cls) -> None:
        cls._check_shader_timer.stop()
        vp = cls.viewport()
        vp.unregister_handlers()
        _log.output('VIEWPORT SHADERS/STOPPER HAS BEEN STOPPED')

    @classmethod
    def out_pinmode_without_save(cls, headnum: int) -> None:
        cls.stop_viewport_shaders()
        settings = fb_settings()
        head = settings.get_head(headnum)
        if head and head.headobj:
            head.headobj.hide_set(False)
            area = FBLoader.get_work_area()
             # TODO: Need to think about better architecture
            if area is None:
                area = bpy.context.area
                _log.output('working area was redefined from context')
            _log.output(f'out_pinmode_without_save area={area}')
            settings.viewport_state.show_ui_elements(area)

        settings.pinmode = False
        _log.output('OUT PINMODE')
        camera = head.get_camera(settings.current_camnum)
        if camera:
            camera.reset_tone_mapping()

    @classmethod
    def out_pinmode(cls, headnum: int) -> None:
        cls.save_pinmode_state(headnum)
        cls.out_pinmode_without_save(headnum)

    @classmethod
    def save_fb_serial_str(cls, headnum: int) -> None:
        settings = fb_settings()
        head = settings.get_head(headnum)
        if not head:
            return
        fb = cls.get_builder()
        head.store_serial_str_in_head_and_on_headobj(fb.serialize())

    @classmethod
    def _save_fb_images_and_keentools_attribute_on_headobj(
            cls, headnum: int) -> None:
        settings = fb_settings()
        head = settings.get_head(headnum)
        if not head or not head.headobj:
            return
        head.save_images_src_on_headobj()
        cls.set_keentools_attributes(head.headobj)  # to update by current ver.

    @classmethod
    def save_fb_serial_and_image_pathes(cls, headnum: int) -> None:
        cls.save_fb_serial_str(headnum)
        cls._save_fb_images_and_keentools_attribute_on_headobj(headnum)

    @classmethod
    def rigidity_setup(cls) -> None:
        fb = cls.get_builder()
        settings = fb_settings()
        fb.set_shape_rigidity(settings.shape_rigidity)
        fb.set_expressions_rigidity(settings.expression_rigidity)

        fb.set_blinking_rigidity(settings.blinking_rigidity)
        fb.set_neck_movement_rigidity(settings.neck_movement_rigidity)

    @classmethod
    def update_all_camera_positions(cls, headnum: int) -> None:
        settings = fb_settings()
        head = settings.get_head(headnum)

        for camnum, camera in enumerate(head.cameras):
            if camera.has_pins():
                cls.place_camera(headnum, camnum)

    @classmethod
    def update_one_camera_focal(cls, camera: Any) -> None:
        if not camera.has_pins():
            return

        fb = cls.get_builder()
        kid = camera.get_keyframe()
        proj_mat = fb.projection_mat(kid)
        focal = focal_by_projection_matrix_mm(proj_mat,
                                              FBConfig.default_sensor_width)
        camera.focal = focal * camera.compensate_view_scale()

    @classmethod
    def update_all_camera_focals(cls, headnum: int) -> None:
        _log.output('update_all_camera_focals')
        settings = fb_settings()
        head = settings.get_head(headnum)
        if not head:
            return

        for i, cam in enumerate(head.cameras):
            cls.update_one_camera_focal(cam)
            _log.output(f'cam.focal: {i} {cam.focal}')

    @classmethod
    def center_geo_camera_projection(cls, headnum: int, camnum: int) -> None:
        settings = fb_settings()
        camera = settings.get_camera(headnum, camnum)
        if camera is None:
            return
        fb = FBLoader.get_builder()
        keyframe = camera.get_keyframe()
        if not fb.is_key_at(keyframe):
            fb.set_centered_geo_keyframe(keyframe)
        else:
            fb.center_geo(keyframe)

    @classmethod
    def update_camera_pins_count(cls, headnum: int, camnum: int) -> None:
        settings = fb_settings()
        head = settings.get_head(headnum)
        cam = head.get_camera(camnum)
        fb = cls.get_builder()
        kid = settings.get_keyframe(headnum, camnum)
        pins_count = fb.pins_count(kid)
        cam.pins_count = pins_count
        _log.output(f'PINS_COUNT H:{headnum} C:{camnum} '
                    f'k:{kid} count:{pins_count}')

    @classmethod
    def get_next_keyframe(cls) -> int:
        fb = cls.get_builder()
        kfs = fb.keyframes()
        if kfs:
            return max(kfs) + 1
        return 1

    @classmethod
    def select_uv_set(cls, builder: Any, uv_set: str) -> None:
        try:
            uv_num = int(uv_set[2:])
            builder.select_uv_set(uv_num)
        except ValueError:
            raise ValueError('Incompatible UV number')
        except pkt_module().InvalidArgumentException:
            raise ValueError('Invalid UV index is out of bounds')
        except TypeError:
            raise TypeError('Invalid UV index')
        except Exception:
            raise Exception('Unknown error in UV selector')

    @classmethod
    def get_builder_mesh(cls, builder: Any, mesh_name: str = 'keentools_mesh',
                         masks: List = (), uv_set: str = 'uv0',
                         keyframe: Optional[int] = None) -> Any:
        for i, m in enumerate(masks):
            builder.set_mask(i, m)

        cls.select_uv_set(builder, uv_set)

        if keyframe is not None:
            geo = builder.applied_args_model_at(keyframe)
        else:
            geo = builder.applied_args_model()
        me = geo.mesh(0)

        v_count = me.points_count()
        vertices = np.empty((v_count, 3), dtype=np.float32)
        for i in range(v_count):
            vertices[i] = me.point(i)

        vertices2 = vertices @ xy_to_xz_rotation_matrix_3x3()
        faces = [[me.face_point(i, j) for j in range(me.face_size(i))]
                 for i in range(me.faces_count())]

        mesh = _create_mesh_from_pydata(mesh_name, vertices2, faces)

        # Normals are not in use yet
        # Init Custom Normals (work on Shading Flat only!)
        # normals = [tuple(me.normal(i) @ rot) for i in range(me.normals_count())]
        # mesh.calc_normals_split()
        # mesh.normals_split_custom_set(normals)

        # Simple Shade Smooth analog
        values = [True] * len(mesh.polygons)
        mesh.polygons.foreach_set('use_smooth', values)

        uvtex = mesh.uv_layers.new()
        uvmap = uvtex.data
        # Fill uvs in uvmap
        uvs_count = me.uvs_count()
        for i in range(uvs_count):
            uvmap[i].uv = me.uv(i)

        mesh.update()

        # Warning! our autosmooth settings work on Shading Flat!
        # mesh.use_auto_smooth = True
        # mesh.auto_smooth_angle = math.pi

        return mesh

    @classmethod
    def universal_mesh_loader(cls, mesh_name: str = 'keentools_mesh',
                              masks: List = (), uv_set: str = 'uv0',
                              keyframe: Optional[int]=None) -> None:
        builder = cls.new_builder()
        mesh = cls.get_builder_mesh(builder, mesh_name, masks, uv_set, keyframe)
        return mesh

    @classmethod
    def _load_model_from_head(cls, head: Any) -> bool:
        _log.output('_load_model_from_head')
        fb = cls.get_builder()
        if not fb.deserialize(head.get_serial_str()):
            _log.warning(f'DESERIALIZE ERROR: {head.get_serial_str()}')
            return False
        return True

    @classmethod
    def load_model_throw_exception(cls, headnum: int) -> bool:
        _log.output('load_model_throw_exception')
        settings = fb_settings()
        head = settings.get_head(headnum)
        if head is None:
            return False
        return cls._load_model_from_head(head)

    @classmethod
    def _deserialize_global_options(cls, headnum: int) -> None:
        _log.output('_deserialize_global_options call')
        settings = fb_settings()
        head = settings.get_head(headnum)  # we assume that head is checked
        fb = cls.get_builder()
        with settings.ui_write_mode_context():
            try:
                head.use_emotions = fb.use_emotions()
                head.lock_blinking = fb.blinking_locked()
                head.lock_neck_movement = fb.neck_movement_locked()
                settings.shape_rigidity = fb.shape_rigidity()
                settings.expression_rigidity = fb.expressions_rigidity()
                settings.blinking_rigidity = fb.blinking_rigidity()
                settings.neck_movement_rigidity = fb.neck_movement_rigidity()
            except Exception as err:
                _log.error(f'_deserialize_global_options:\n{str(err)}')

    @classmethod
    def load_model(cls, headnum: int) -> bool:
        try:
            if not cls.load_model_throw_exception(headnum):
                return False
            cls._deserialize_global_options(headnum)
            return True
        except pkt_module().ModelLoadingException as err:
            _log.error(f'DESERIALIZE ModelLoadingException:\n{str(err)}')
        except Exception as err:
            _log.error(f'DESERIALIZE Unknown Exception:\n{str(err)}')
        return False

    @classmethod
    def reload_current_model(cls) -> bool:
        settings = fb_settings()
        headnum = settings.current_headnum
        if not settings.is_proper_headnum(headnum):
            return False
        return cls.load_model(headnum)

    @classmethod
    def place_camera(cls, headnum: int, camnum: int) -> None:
        settings = fb_settings()
        head = settings.get_head(headnum)
        camera = head.get_camera(camnum)
        camobj = camera.camobj
        headobj = head.headobj

        fb = cls.get_builder()
        keyframe = camera.get_keyframe()

        mat = calc_model_mat(fb.model_mat(keyframe), headobj.matrix_world)
        if mat is not None:
            camobj.matrix_world = mat

    @classmethod
    def solve(cls, headnum: int, camnum: int) -> bool:
        def _exception_handling(headnum, msg, license_err=True):
            _log.error(msg)
            if settings.pinmode:
                settings.force_out_pinmode = True
                settings.license_error = license_err
                cls.out_pinmode(headnum)

        _log.output('FBloader.solve called')
        settings = fb_settings()
        head = settings.get_head(headnum)
        camera = head.get_camera(camnum)
        kid = camera.get_keyframe()
        fb = cls.get_builder()

        cls.rigidity_setup()
        fb.set_use_emotions(head.should_use_emotions())

        fb.set_blinking_locked(head.lock_blinking)
        fb.set_neck_movement_locked(head.lock_neck_movement)

        configure_focal_mode_and_fixes(fb, head)
        try:
            fb.solve_for_current_pins(kid)
            update_camera_focal(camera, fb)
        except pkt_module().UnlicensedException:
            _exception_handling(headnum, 'SOLVE LICENSE EXCEPTION')
            return False
        except pkt_module().InvalidArgumentException:
            _exception_handling(headnum, 'SOLVE NO KEYFRAME EXCEPTION',
                                license_err=False)
            return False
        except Exception as err:
            _exception_handling(headnum, f'SOLVE UNKNOWN EXCEPTION: {str(err)}',
                                license_err=False
            )
            return False
        _log.output('FBloader.solve finished')
        return True

    @classmethod
    def size_from_projection(cls, keyframe_id: int) -> Tuple[float, float]:
        fb = cls.get_builder()
        proj = fb.projection_mat(keyframe_id)
        return 2 * (-proj[0][2]), 2 * (-proj[1][2])

    @classmethod
    def update_cameras_from_old_version(cls, headnum: int) -> None:
        settings = fb_settings()
        head = settings.get_head(headnum)
        if head.sensor_width == 0:
            return

        sensor_width = head.sensor_width if head.sensor_width != -1 \
            else FBConfig.default_sensor_width

        _log.output('UPDATE_OLD_MODEL')

        cls.load_model(headnum)
        fb = cls.get_builder()

        for cam in head.cameras:
            if cam.orientation % 2 == 0:
                continue
            kid = cam.get_keyframe()
            w, h = cls.size_from_projection(kid)
            _log.output(f'IMAGE_SIZE_BY_PROJECTION: {w}x{h}')
            dx = (h - w) * 0.5
            dy = (w - h) * 0.5
            for i in range(fb.pins_count(kid)):
                pin = fb.pin(kid, i)
                x, y = pin.img_pos
                fb.move_pin(kid, i, (x + dx, y + dy))
        # Save info
        head.store_serial_str_in_head_and_on_headobj(fb.serialize())

        focal = head.focal * FBConfig.default_sensor_width / sensor_width
        head.reset_sensor_size()
        for cam in head.cameras:
            cam.focal = focal
            cam.auto_focal_estimation = head.auto_focal_estimation
            cam.reset_camera_sensor()

        reload_all_camera_exif(headnum)

    @classmethod
    def create_camera_object(cls, headnum: int, camnum: int) -> Object:
        settings = fb_settings()
        head = settings.get_head(headnum)

        cam_data = bpy_create_camera_data(FBConfig.default_fb_camera_data_name)
        cam_ob = bpy_create_object(FBConfig.default_fb_camera_name, cam_data)
        cam_ob.rotation_euler = FBConfig.default_camera_rotation
        cam_ob.location = (FBConfig.camera_x_step * camnum,
                           - FBConfig.camera_y_step - headnum,
                           FBConfig.camera_z_step)

        cam_data.display_size = FBConfig.default_camera_display_size
        cam_data.lens = head.focal  # TODO: need a better choise in future
        cam_data.sensor_width = FBConfig.default_sensor_width
        cam_data.sensor_height = FBConfig.default_sensor_height
        cam_data.show_background_images = True

        headobj_collection = get_obj_collection(head.headobj)
        if headobj_collection is not None:
            headobj_collection.objects.link(cam_ob)
        else:
            _log.error('ERROR IN COLLECTIONS')
            bpy_link_to_scene(cam_ob)

        return cam_ob

    @classmethod
    def add_background_to_camera(cls, headnum: int, camnum: int,
                                 img: Optional[Any]) -> None:
        settings = fb_settings()
        head = settings.get_head(headnum)
        camera = head.get_camera(camnum)

        cam_data = camera.camobj.data
        if len(cam_data.background_images) == 0:
            b = cam_data.background_images.new()
        else:
            b = cam_data.background_images[0]

        if img is not None:
            b.image = img
            settings.get_camera(headnum, camnum).cam_image = img
        b.frame_method = 'CROP'
        b.show_on_foreground = False
        b.alpha = 1.0

        w = 0
        h = 0
        if img is not None:
            w, h = img.size

        if w == 0 and h == 0:
            w, h = bpy_render_frame()

        camera.set_image_width(w)
        camera.set_image_height(h)

    @classmethod
    def add_new_camera(cls, headnum: int, img: Optional[Any]) -> Object:
        settings = fb_settings()
        head = settings.get_head(headnum)

        camnum = len(head.cameras)
        cam_ob = cls.create_camera_object(headnum, camnum)

        camera = head.cameras.add()
        camera.camobj = cam_ob

        cls.add_background_to_camera(headnum, camnum, img)

        fb = cls.get_builder()
        kid = cls.get_next_keyframe()
        camera.set_keyframe(kid)

        fb.set_centered_geo_keyframe(kid)

        _log.output(f'KEYFRAMES {str(fb.keyframes())}')

        mark_keentools_object(camera.camobj)
        return camera

    @classmethod
    def add_new_camera_with_image(cls, headnum: int, img_path: str) -> Object:
        img = bpy.data.images.load(img_path)
        return cls.add_new_camera(headnum, img)

    @classmethod
    def _update_wireframe(cls, obj: Object, keyframe: int) -> None:
        fb = cls.get_builder()
        vp = cls.viewport()
        wf = vp.wireframer()
        wf.init_geom_data_from_fb(fb, obj, keyframe)  # TODO: Optimize it!
        wf.init_edge_indices()
        geo = fb.applied_args_model_at(keyframe)
        wf.init_geom_data_from_core(*FBLoader.get_geo_shader_data(geo))
        wf.create_batches()

    @classmethod
    def _update_points_and_residuals(cls, area: Area, obj: Object,
                                     keyframe: int) -> None:
        fb = cls.get_builder()
        vp = cls.viewport()
        vp.update_surface_points(fb, obj, keyframe)
        vp.update_residuals(fb, keyframe, area)
        vp.create_batch_2d(area)

    @classmethod
    def update_fb_viewport_shaders(cls, *, area: Area = None,
                                   headnum: Optional[int] = None,
                                   camnum: Optional[int] = None,
                                   wireframe: bool = False,
                                   wireframe_colors: bool = False,
                                   wireframe_image: bool = False,
                                   adaptive_opacity: bool = False,
                                   camera_pos: bool = False,
                                   batch_wireframe: bool = False,
                                   pins_and_residuals: bool = False) -> None:
        settings = fb_settings()
        hnum = headnum if headnum is not None else settings.current_headnum
        cnum = camnum if camnum is not None else settings.current_camnum
        head = settings.get_head(hnum)
        if not head or not head.headobj:
            return
        kid = head.get_keyframe(cnum)

        work_area = area if not area is None else cls.get_work_area()

        if adaptive_opacity:
            if settings.use_adaptive_opacity:
                settings.calc_adaptive_opacity(work_area)
        if wireframe_colors:
            vp = FBLoader.viewport()
            vp.update_wireframe_colors()
        if wireframe_image:
            wf = FBLoader.wireframer()
            wf.init_wireframe_image(settings.show_specials)
        if camera_pos:
            cam = head.get_camera(cnum)
            if cam:
                wf = FBLoader.wireframer()
                wf.set_camera_pos(cam.camobj, head.headobj)
        if wireframe:
            cls._update_wireframe(head.headobj, kid)
        if pins_and_residuals:
            cls._update_points_and_residuals(work_area, head.headobj, kid)
        if batch_wireframe:
            wf = FBLoader.wireframer()
            wf.create_batches()

    @classmethod
    def load_pins_into_viewport(cls, headnum: int, camnum: int) -> None:
        settings = fb_settings()
        kid = settings.get_keyframe(headnum, camnum)
        fb = cls.get_builder()
        vp = cls.viewport()
        vp.pins().set_pins(vp.img_points(fb, kid))
        vp.pins().reset_current_pin()

    @classmethod
    def get_work_area(cls) -> Optional[Area]:
        vp = cls.viewport()
        return vp.get_work_area()

    @classmethod
    def get_geo_shader_data(cls, geo: Any) -> Tuple:
        _log.output('get_geo_shader_data')
        mat = xy_to_xz_rotation_matrix_3x3()

        utls = pkt_module().utils
        edge_vertices = np.array(utls.get_lines(geo),
                                 dtype=np.float32) @ mat
        triangle_vertices = np.array(utls.get_independent_triangles(geo),
                                     dtype=np.float32) @ mat
        edge_vertex_normals = np.array(utls.get_normals_for_lines(geo),
                                       dtype=np.float32) @ mat

        return edge_vertices, edge_vertex_normals, triangle_vertices
