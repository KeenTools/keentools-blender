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
import keentools_facebuilder.blender_independent_packages.pykeentools_loader as pkt
import numpy as np

from .config import Config, get_main_settings
from .utils.coords import xy_to_xz_rotation_matrix_3x3
from .utils import attrs, coords, cameras
from .utils.exif_reader import update_image_groups, reload_all_camera_exif
from .utils.other import FBStopShaderTimer, restore_ui_elements
from .viewport import FBViewport


class FBLoader:
    _camera_input = None
    _builder_instance = None
    _viewport = FBViewport()

    @classmethod
    def viewport(cls):
        return cls._viewport

    @classmethod
    def new_builder(cls):
        from .camera_input import FaceBuilderCameraInput
        cls._camera_input = FaceBuilderCameraInput()
        cls._builder_instance = pkt.module().FaceBuilder(cls._camera_input)
        return cls._builder_instance

    @classmethod
    def get_builder(cls):
        if cls._builder_instance is not None:
            return cls._builder_instance
        return cls.new_builder()

    @classmethod
    def is_not_loaded(cls):
        return cls._builder_instance is None

    @classmethod
    def update_cam_image_size(cls, cam_item):
        cam_item.update_image_size()

    @classmethod
    def update_head_camera_focals(cls, head):
        logger = logging.getLogger(__name__)
        for i, c in enumerate(head.cameras):
            c.camobj.data.lens = c.focal
            logger.debug("camera: {} focal: {}".format(i, c.focal))

    @classmethod
    def set_keentools_attributes(cls, obj):
        attrs.mark_keentools_object(obj)

    @classmethod
    def check_mesh(cls, headobj):
        try:
            fb = cls.get_builder()
            if len(headobj.data.vertices) == len(fb.applied_args_vertices()):
                return True
        except Exception:
            pass
        return False

    @classmethod
    def in_pin_drag(cls):
        vp = cls.viewport()
        return vp.in_pin_drag()

    @classmethod
    def save_pinmode_state(cls, headnum):
        logger = logging.getLogger(__name__)

        cls.save_fb_on_headobj(headnum)

        vp = cls.viewport()
        vp.pins().reset_current_pin()

        settings = get_main_settings()
        head = settings.get_head(headnum)
        if head:
            cls.update_head_camera_focals(head)
            if head.headobj:
                coords.update_head_mesh_neutral(cls.get_builder(), head.headobj)
        logger.debug("SAVE PINMODE STATE")

    @classmethod
    def out_pinmode(cls, headnum):
        logger = logging.getLogger(__name__)

        cls.save_pinmode_state(headnum)

        vp = cls.viewport()
        vp.unregister_handlers()

        FBStopShaderTimer.stop()
        logger.debug("STOPPER STOP")

        restore_ui_elements()

        cameras.show_all_cameras(headnum)

        settings = get_main_settings()
        head = settings.get_head(headnum)
        if head and head.headobj:
            head.headobj.hide_set(False)
        settings.pinmode = False
        logger.debug("OUT PINMODE")

    @classmethod
    def save_only(cls, headnum):
        fb = cls.get_builder()
        settings = get_main_settings()
        head = settings.get_head(headnum)
        # Save block
        head.set_serial_str(fb.serialize())

    @classmethod
    def save_fb_on_headobj(cls, headnum):
        fb = cls.get_builder()
        settings = get_main_settings()
        head = settings.get_head(headnum)
        if head:
            head.set_serial_str(fb.serialize())
            head.save_images_src()
            if head.headobj:
                cls.set_keentools_attributes(head.headobj)

    @classmethod
    def fb_save(cls, headnum, camnum):
        """ Face Builder Serialize Model Info """
        fb = cls.get_builder()
        settings = get_main_settings()
        head = settings.get_head(headnum)
        cam = head.get_camera(camnum)

        if cam is not None:
            cam.set_model_mat(fb.model_mat(cam.get_keyframe()))

        cls.save_fb_on_headobj(headnum)

    @classmethod
    def update_mesh_only(cls, headnum):
        fb = cls.get_builder()
        settings = get_main_settings()
        head = settings.get_head(headnum)
        coords.update_head_mesh(settings, fb, head)

    @classmethod
    def shader_update(cls, headobj):
        cls.viewport().wireframer().init_geom_data(headobj)
        cls.viewport().wireframer().init_edge_indices(FBLoader.get_builder())
        cls.viewport().wireframer().create_batches()

    @classmethod
    def fb_redraw(cls, headnum, camnum):
        fb = cls.get_builder()
        settings = get_main_settings()
        head = settings.get_head(headnum)
        cam = head.get_camera(camnum)
        headobj = head.headobj
        kid = settings.get_keyframe(headnum, camnum)
        cls.place_camera(headnum, camnum)
        coords.update_head_mesh(settings, fb, head)
        # Load pins from model
        vp = cls.viewport()
        vp.pins().set_pins(vp.img_points(fb, kid))
        vp.update_surface_points(fb, headobj, kid)

        cls.shader_update(headobj)

    @classmethod
    def rigidity_setup(cls):
        fb = cls.get_builder()
        settings = get_main_settings()
        fb.set_shape_rigidity(settings.shape_rigidity)
        fb.set_expressions_rigidity(settings.expression_rigidity)

    @classmethod
    def update_all_camera_positions(cls, headnum):
        fb = cls.get_builder()
        settings = get_main_settings()
        head = settings.get_head(headnum)

        for camnum, camera in enumerate(head.cameras):
            if camera.has_pins():
                cls.place_camera(headnum, camnum)
                keyframe = camera.get_keyframe()
                camera.set_model_mat(fb.model_mat(keyframe))

    @classmethod
    def update_all_camera_focals(cls, headnum):
        fb = cls.get_builder()
        settings = get_main_settings()
        head = settings.get_head(headnum)

        for i, cam in enumerate(head.cameras):
            if cam.has_pins():
                kid = cam.get_keyframe()
                proj_mat = fb.projection_mat(kid)
                focal = coords.focal_by_projection_matrix(
                    proj_mat, Config.default_sensor_width)

                cam.focal = focal * cam.compensate_view_scale()

    @classmethod
    def center_geo_camera_projection(cls, headnum, camnum):
        settings = get_main_settings()
        camera = settings.get_camera(headnum, camnum)
        if camera is None:
            return
        fb = FBLoader.get_builder()
        keyframe = camera.get_keyframe()
        if not fb.is_key_at(keyframe):
            fb.set_centered_geo_keyframe(keyframe)
        else:
            fb.center_geo(keyframe)

    # --------------------
    @classmethod
    def set_camera_projection(cls, fl, sw, rx, ry,
                              near_clip=0.1, far_clip=1000.0):
        camera_w = rx  # Camera Width in pixels 1920
        camera_h = ry  # Camera Height in pixels 1080
        focal_length = fl
        sensor_width = sw

        # This works only when Camera Sensor Mode is Auto
        if camera_w < camera_h:
            sensor_width = sw * camera_w / camera_h

        projection = coords.projection_matrix(
            camera_w, camera_h, focal_length, sensor_width,
            near_clip, far_clip)

        fb = cls.get_builder()
        fb.set_projection_mat(projection)

    @classmethod
    def update_pins_count(cls, headnum, camnum):
        logger = logging.getLogger(__name__)
        settings = get_main_settings()
        head = settings.get_head(headnum)
        cam = head.get_camera(camnum)
        fb = cls.get_builder()
        kid = settings.get_keyframe(headnum, camnum)
        pins_count = fb.pins_count(kid)
        cam.pins_count = pins_count
        logger.debug("PINS_COUNT H:{} C:{} k:{} count:{}".format(
            headnum, camnum, kid, pins_count))

    @classmethod
    def get_next_keyframe(cls):
        fb = cls.get_builder()
        kfs = fb.keyframes()
        if kfs:
            return max(kfs) + 1
        return 1

    @classmethod
    def select_uv_set(cls, builder, uv_set):
        try:
            uv_num = int(uv_set[2:])
            builder.select_uv_set(uv_num)
        except ValueError:
            raise ValueError('Incompatible UV number')
        except pkt.module().InvalidArgumentException:
            raise ValueError('Invalid UV index is out of bounds')
        except TypeError:
            raise TypeError('Invalid UV index')
        except Exception:
            raise Exception('Unknown error in UV selector')

    @classmethod
    def get_builder_mesh(cls, builder, mesh_name='keentools_mesh',
                         masks=(), uv_set='uv0', keyframe=None):
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

        f_count = me.faces_count()
        faces = np.empty(f_count, dtype=np.object)

        for i in range(f_count):
            faces[i] = [me.face_point(i, j) for j in range(me.face_size(i))]

        mesh = bpy.data.meshes.new(mesh_name)
        mesh.from_pydata(vertices2, [], faces.tolist())

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
    def universal_mesh_loader(cls, mesh_name='keentools_mesh',
                              masks=(), uv_set='uv0'):
        builder = cls.new_builder()
        mesh = cls.get_builder_mesh(builder, mesh_name, masks, uv_set,
                                    keyframe=None)
        return mesh

    @classmethod
    def load_model_from_head(cls, head):
        fb = cls.get_builder()
        if not fb.deserialize(head.get_serial_str()):
            logger = logging.getLogger(__name__)
            logger.warning('DESERIALIZE ERROR: {}'.format(
                head.get_serial_str()))
            return False
        return True

    @classmethod
    def load_model(cls, headnum):
        settings = get_main_settings()
        head = settings.get_head(headnum)
        if head is None:
            return False
        return cls.load_model_from_head(head)

    @classmethod
    def load_all(cls, headnum, camnum):
        logger = logging.getLogger(__name__)
        settings = get_main_settings()
        head = settings.get_head(headnum)
        cam = head.get_camera(camnum)
        kid = cam.get_keyframe()

        cls.load_model_from_head(head)
        fb = cls.get_builder()

        cls.place_camera(headnum, camnum)
        # Load pins from model
        vp = cls.viewport()
        vp.pins().set_pins(vp.img_points(fb, kid))
        vp.pins().reset_current_pin()
        logger.debug("LOAD MODEL END")

    @classmethod
    def place_camera(cls, headnum, camnum):
        settings = get_main_settings()
        head = settings.get_head(headnum)
        camera = head.get_camera(camnum)
        camobj = camera.camobj
        headobj = head.headobj

        fb = cls.get_builder()
        keyframe = camera.get_keyframe()

        mat = coords.calc_model_mat(
            fb.model_mat(keyframe),
            headobj.matrix_world)
        if mat is not None:
            camobj.matrix_world = mat

    @classmethod
    def load_pins(cls, headnum, camnum):
        settings = get_main_settings()
        kid = settings.get_keyframe(headnum, camnum)
        fb = cls.get_builder()
        # Load pins from model
        vp = cls.viewport()
        vp.pins().set_pins(vp.img_points(fb, kid))
        vp.pins().reset_current_pin()

    @classmethod
    def get_keyframe_focal(cls, keyframe_id):
        fb = cls.get_builder()
        proj_mat = fb.projection_mat(keyframe_id)
        focal = coords.focal_by_projection_matrix(
            proj_mat, Config.default_sensor_width)

        # Fix for Vertical camera (because Blender has Auto in sensor)
        rx, ry = coords.render_frame()
        if ry > rx:
            focal = focal * rx / ry
        return focal

    @classmethod
    def solve(cls, headnum, camnum):
        def _exception_handling(headnum, msg, license_err=True):
            logger = logging.getLogger(__name__)
            logger.error(msg)
            if settings.pinmode:
                settings.force_out_pinmode = True
                settings.license_error = license_err
                cls.out_pinmode(headnum)

        def _unfix_all(fb, head):
            for cam in head.cameras:
                fb.set_focal_length_fixed_at(cam.get_keyframe(), False)

        def _fix_all_except_this(fb, head, exclude_kid):
            for cam in head.cameras:
                fb.set_focal_length_fixed_at(cam.get_keyframe(),
                                             cam.get_keyframe() != exclude_kid)

        def _unfix_not_in_groups(fb, head):
            for cam in head.cameras:
                fb.set_focal_length_fixed_at(
                    cam.get_keyframe(),
                    cam.is_in_group()
                    or not cam.auto_focal_estimation)

        def _auto_focal_estimation_mode_and_fixes():
            mode = 'FB_ESTIMATE_VARYING_FOCAL_LENGTH'
            if head.smart_mode():
                if camera.auto_focal_estimation:
                    if camera.is_in_group():
                        for cam in head.cameras:
                            fb.set_focal_length_fixed_at(
                                cam.get_keyframe(),
                                cam.image_group != camera.image_group
                                or not cam.auto_focal_estimation)
                        mode = 'FB_ESTIMATE_STATIC_FOCAL_LENGTH'
                    else:  # image_group in (-1, 0)
                        for cam in head.cameras:
                            fb.set_focal_length_fixed_at(
                                cam.get_keyframe(),
                                cam.image_group > 0
                                or not cam.auto_focal_estimation)
                        mode = 'FB_ESTIMATE_VARYING_FOCAL_LENGTH'
                else:
                    _unfix_not_in_groups(fb, head)
                    mode = 'FB_ESTIMATE_VARYING_FOCAL_LENGTH'
            else:  # Override all
                if head.manual_estimation_mode == 'all_different':
                    _unfix_all(fb, head)
                    mode = 'FB_ESTIMATE_VARYING_FOCAL_LENGTH'
                elif head.manual_estimation_mode == 'current_estimation':
                    _fix_all_except_this(fb, head, kid)
                    mode = 'FB_ESTIMATE_VARYING_FOCAL_LENGTH'
                elif head.manual_estimation_mode == 'same_focus':
                    _unfix_all(fb, head)
                    mode = 'FB_ESTIMATE_STATIC_FOCAL_LENGTH'
                elif head.manual_estimation_mode == 'force_focal':
                    mode = 'FB_FIXED_FOCAL_LENGTH_ALL_FRAMES'
                else:
                    assert False, 'Unknown mode: {}'.format(
                        head.manual_estimation_mode)
            return mode

        def _update_camera_focal_post():
            focal = cls.get_keyframe_focal(kid)
            camera.camobj.data.lens = focal
            camera.focal = focal

        settings = get_main_settings()
        head = settings.get_head(headnum)
        camera = head.get_camera(camnum)
        kid = camera.get_keyframe()
        fb = cls.get_builder()

        cls.rigidity_setup()
        fb.set_use_emotions(head.should_use_emotions())

        mode = _auto_focal_estimation_mode_and_fixes()
        fb.set_focal_length_estimation_mode(mode)

        try:
            fb.solve_for_current_pins(kid)
        except pkt.module().UnlicensedException:
            _exception_handling(headnum, 'SOLVE LICENSE EXCEPTION')
            return False
        except pkt.module().InvalidArgumentException:
            _exception_handling(headnum, 'SOLVE NO KEYFRAME EXCEPTION',
                                license_err=False)
            return False
        except Exception as err:
            _exception_handling(headnum,
                                'SOLVE UNKNOWN EXCEPTION: {}'.format(str(err)),
                                license_err=False)
            return False

        _update_camera_focal_post()
        return True

    @classmethod
    def size_from_projection(cls, keyframe_id):
        fb = cls.get_builder()
        proj = fb.projection_mat(keyframe_id)
        return 2 * (-proj[0][2]), 2 * (-proj[1][2])

    @classmethod
    def update_cameras_from_old_version(cls, headnum):
        settings = get_main_settings()
        head = settings.get_head(headnum)
        if head.sensor_width == 0:
            return

        sensor_width = head.sensor_width if head.sensor_width != -1 \
            else Config.default_sensor_width

        logger = logging.getLogger(__name__)
        logger.debug('UPDATE_OLD_MODEL')

        cls.load_model_from_head(head)
        fb = cls.get_builder()

        for cam in head.cameras:
            if cam.orientation % 2 == 0:
                continue
            kid = cam.get_keyframe()
            w, h = cls.size_from_projection(kid)
            logger.debug('IMAGE_SIZE_BY_PROJECTION: {}x{}'.format(w, h))
            dx = (h - w) * 0.5
            dy = (w - h) * 0.5
            for i in range(fb.pins_count(kid)):
                pin = fb.pin(kid, i)
                x, y = pin.img_pos
                fb.move_pin(kid, i, (x + dx, y + dy))
        # Save info
        head.set_serial_str(fb.serialize())

        focal = head.focal * Config.default_sensor_width / sensor_width
        head.reset_sensor_size()
        for cam in head.cameras:
            cam.focal = focal
            cam.auto_focal_estimation = head.auto_focal_estimation
            cam.reset_camera_sensor()
            cam.image_group = 0

        reload_all_camera_exif(headnum)
        update_image_groups(head)

    @classmethod
    def create_camera_object(cls, headnum, camnum):
        settings = get_main_settings()
        head = settings.get_head(headnum)

        cam_data = bpy.data.cameras.new(Config.default_fb_camera_data_name)
        cam_ob = bpy.data.objects.new(Config.default_fb_camera_name, cam_data)
        cam_ob.rotation_euler = Config.default_camera_rotation
        cam_ob.location = (Config.camera_x_step * camnum,
                           - Config.camera_y_step - headnum,
                           Config.camera_z_step)

        cam_data.display_size = Config.default_camera_display_size
        cam_data.lens = head.focal  # TODO: need a better choise in future
        cam_data.sensor_width = Config.default_sensor_width
        cam_data.sensor_height = Config.default_sensor_height
        cam_data.show_background_images = True

        col = attrs.get_obj_collection(head.headobj)
        if col is not None:
            col.objects.link(cam_ob)  # link to headobj collection
        else:
            logger = logging.getLogger(__name__)
            logger.error("ERROR IN COLLECTIONS")
            bpy.context.scene.collection.objects.link(cam_ob)  # Link to Scene

        return cam_ob

    @classmethod
    def add_background_to_camera(cls, headnum, camnum, img):
        settings = get_main_settings()
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
            w = bpy.context.scene.render.resolution_x
            h = bpy.context.scene.render.resolution_y

        camera.set_image_width(w)
        camera.set_image_height(h)

    @classmethod
    def add_new_camera(cls, headnum, img):
        logger = logging.getLogger(__name__)
        settings = get_main_settings()
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

        logger.debug("KEYFRAMES {}".format(str(fb.keyframes())))

        attrs.mark_keentools_object(camera.camobj)
        return camera

    @classmethod
    def add_new_camera_with_image(cls, headnum, img_path):
        img = bpy.data.images.load(img_path)
        return cls.add_new_camera(headnum, img)
