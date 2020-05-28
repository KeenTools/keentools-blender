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
import logging
import math

import numpy as np

from .viewport import FBViewport
from .utils import attrs, coords, cameras
from .utils.other import FBStopShaderTimer, restore_ui_elements
from .utils.exif_reader import update_image_groups

from .builder import UniBuilder
from .config import (Config, get_main_settings, get_operators,
                     BuilderType, ErrorType)
import keentools_facebuilder.blender_independent_packages.pykeentools_loader as pkt


class FBLoader:
    # Builder selection: FaceBuilder or BodyBuilder
    builder_instance = None
    _viewport = FBViewport()

    @classmethod
    def viewport(cls):
        return cls._viewport

    @classmethod
    def builder(cls):
        if cls.builder_instance is None:
            cls.builder_instance = UniBuilder(Config.default_builder)
        return cls.builder_instance

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
    def update_camera_params(cls, head):
        """ Update when some camera parameters changes """
        logger = logging.getLogger(__name__)
        logger.debug("UPDATE CAMERA PARAMETERS")

        settings = get_main_settings()
        scene = bpy.context.scene

        # Check scene consistency
        heads_deleted, cams_deleted = settings.fix_heads()

        headnum = -1
        for i, h in enumerate(settings.heads):
            if head == h:
                headnum = i

        if headnum < 0:
            return

        # NoneBuilder for auto-select builder class
        fb = cls.new_builder(BuilderType.NoneBuilder, head.mod_ver)
        cls.load_model(headnum)

        max_index = -1
        max_pins = -1
        for i, c in enumerate(head.cameras):
            kid = c.get_keyframe()
            # We are looking for keyframe that has maximum pins
            if c.has_pins():
                if max_pins < c.pins_count:
                    max_index = kid
                    max_pins = c.pins_count
            c.camobj.data.lens = c.focal  # fix
            c.camobj.data.sensor_width = Config.default_sensor_width
            c.camobj.data.sensor_height = Config.default_sensor_height

        FBLoader.rigidity_setup()
        fb.set_use_emotions(head.should_use_emotions())

        if max_index >= 0:
            try:
                fb.solve_for_current_pins(max_index)
                logger.debug("SOLVED {}".format(max_index))

            except pkt.module().UnlicensedException:
                logger.error("LICENSE PROBLEM")

                if not settings.pinmode and not settings.license_error:
                    warn = getattr(get_operators(), Config.fb_warning_callname)
                    warn('INVOKE_DEFAULT', msg=ErrorType.NoLicense)

                settings.force_out_pinmode = True
                settings.license_error = True
            except Exception:
                logger.error("SOLVER PROBLEM")
                settings.force_out_pinmode = True

        coords.update_head_mesh(settings, fb, head)

        if settings.pinmode:
            cls.fb_redraw(headnum, settings.current_camnum)
        cls.update_all_camera_positions(headnum)
        cls.save_only(headnum)

    @classmethod
    def get_builder(cls):
        return cls.builder().get_builder()

    @classmethod
    def new_builder(cls, builder_type=BuilderType.NoneBuilder,
                    ver=Config.unknown_mod_ver):
        return cls.builder().new_builder(builder_type, ver)

    @classmethod
    def get_builder_type(cls):
        return cls.builder().get_builder_type()

    @classmethod
    def get_builder_version(cls):
        return cls.builder().get_version()

    @classmethod
    def set_keentools_version(cls, obj):
        attrs.set_keentools_version(obj, cls.get_builder_type(),
                                    cls.get_builder_version())

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
    def save_pinmode_state(cls, headnum):
        logger = logging.getLogger(__name__)
        settings = get_main_settings()
        head = settings.get_head(headnum)
        headobj = head.headobj

        cls.save_fb_on_headobj(headnum)

        vp = cls.viewport()
        vp.pins().reset_current_pin()

        cls.update_head_camera_focals(head)
        coords.update_head_mesh_neutral(cls.get_builder(), headobj)
        logger.debug("SAVE PINMODE STATE")

    @classmethod
    def out_pinmode(cls, headnum):
        logger = logging.getLogger(__name__)
        settings = get_main_settings()
        head = settings.get_head(headnum)
        headobj = head.headobj

        cls.save_pinmode_state(headnum)

        vp = cls.viewport()
        vp.unregister_handlers()

        FBStopShaderTimer.stop()
        logger.debug("STOPPER STOP")

        restore_ui_elements()

        cameras.show_all_cameras(headnum)
        headobj.hide_set(False)
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

        head.set_serial_str(fb.serialize())

        head.save_images_src()
        head.save_cam_settings()
        cls.set_keentools_version(head.headobj)

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
        cls.viewport().wireframer().init_edge_indices(headobj)
        cls.viewport().wireframer().create_batches()

    @classmethod
    def fb_redraw(cls, headnum, camnum):
        fb = cls.get_builder()
        settings = get_main_settings()
        head = settings.get_head(headnum)
        cam = head.get_camera(camnum)
        headobj = head.headobj
        camobj = cam.camobj
        kid = settings.get_keyframe(headnum, camnum)
        cls.place_cameraobj(kid, camobj, headobj)
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
        if FBLoader.get_builder_type() == BuilderType.FaceBuilder:
            fb.set_auto_rigidity(settings.check_auto_rigidity)
            fb.set_rigidity(settings.rigidity)

    @classmethod
    def rigidity_post(cls):
        fb = cls.get_builder()
        settings = get_main_settings()
        if settings.check_auto_rigidity and (
                FBLoader.get_builder_type() == BuilderType.FaceBuilder):
            rg = fb.current_rigidity()
            settings.rigidity = rg

    @classmethod
    def update_all_camera_positions(cls, headnum):
        fb = cls.get_builder()
        settings = get_main_settings()
        head = settings.get_head(headnum)
        headobj = head.headobj

        for i, cam in enumerate(head.cameras):
            if cam.has_pins():
                kid = cam.get_keyframe()
                cls.place_cameraobj(kid, cam.camobj, headobj)
                cam.set_model_mat(fb.model_mat(kid))

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
    def update_camera_projection(cls, headnum, camnum):
        settings = get_main_settings()
        camera = settings.get_camera(headnum, camnum)
        if camera is None:
            return
        fb = FBLoader.get_builder()
        projection = camera.get_projection_matrix()
        fb.update_projection_mat(camera.get_keyframe(), projection)

    @classmethod
    def center_geo_camera_projection(cls, headnum, camnum):
        settings = get_main_settings()
        camera = settings.get_camera(headnum, camnum)
        if camera is None:
            return
        fb = FBLoader.get_builder()
        projection = camera.get_projection_matrix()
        fb.set_centered_geo_keyframe(camera.get_keyframe(), projection)

    # --------------------
    @classmethod
    def place_cameraobj(cls, keyframe, camobj, headobj):
        fb = cls.get_builder()
        mat = coords.calc_model_mat(
            fb.model_mat(keyframe),
            headobj.matrix_world
        )
        if mat is not None:
            camobj.matrix_world = mat

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
    def get_builder_mesh(cls, builder, mesh_name='keentools_mesh',
                         masks=(), uv_set='uv0', keyframe=None):
        for i, m in enumerate(masks):
            builder.set_mask(i, m)

        # change UV in accordance to selected UV set
        # Blender can't use integer as key in enum property
        builder.select_uv_set(0)
        if uv_set == 'uv1':
            builder.select_uv_set(1)
        if uv_set == 'uv2':
            builder.select_uv_set(2)
        if uv_set == 'uv3':
            builder.select_uv_set(3)

        if keyframe is not None:
            geo = builder.applied_args_model_at(keyframe)
        else:
            geo = builder.applied_args_model()
        me = geo.mesh(0)

        v_count = me.points_count()
        vertices = []
        for i in range(0, v_count):
            vertices.append(me.point(i))

        rot = np.array([[1., 0., 0.], [0., 0., 1.], [0., -1., 0]])
        vertices2 = vertices @ rot
        # vertices2 = vertices

        f_count = me.faces_count()
        faces = []

        # Normals are not in use yet
        normals = []
        n = 0
        for i in range(0, f_count):
            row = []
            for j in range(0, me.face_size(i)):
                row.append(me.face_point(i, j))
                normal = me.normal(i, j) @ rot
                normals.append(tuple(normal))
                n += 1
            faces.append(tuple(row))

        mesh = bpy.data.meshes.new(mesh_name)
        mesh.from_pydata(vertices2, [], faces)

        # Init Custom Normals (work on Shading Flat!)
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
    def universal_mesh_loader(cls, builder_type, mesh_name='keentools_mesh',
                              masks=(), uv_set='uv0'):
        stored_builder_type = FBLoader.get_builder_type()
        stored_builder_version = FBLoader.get_builder_version()
        builder = cls.new_builder(builder_type, Config.unknown_mod_ver)

        mesh = cls.get_builder_mesh(builder, mesh_name, masks, uv_set,
                                    keyframe=None)
        # Restore builder
        cls.new_builder(stored_builder_type, stored_builder_version)
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
        camobj = cam.camobj
        headobj = head.headobj

        cls.load_model_from_head(head)
        fb = cls.get_builder()

        cls.place_cameraobj(kid, camobj, headobj)
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
        kid = settings.get_keyframe(headnum, camnum)
        cls.place_cameraobj(kid, camobj, headobj)

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
        def _exception_handling(headnum, msg):
            logger = logging.getLogger(__name__)
            logger.error(msg)
            if settings.pinmode:
                settings.force_out_pinmode = True
                settings.license_error = True
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
                    for cam in head.cameras:
                        fb.update_projection_mat(cam.get_keyframe(),
                            cam.get_custom_projection_matrix(head.focal))
                    mode = 'FB_FIXED_FOCAL_LENGTH_ALL_FRAMES'
                else:
                    assert(False), 'Unknown mode: {}'.format(
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
            _exception_handling(headnum, "SOLVE LICENSE EXCEPTION")
            return False
        except Exception:
            _exception_handling(headnum, "SOLVE EXCEPTION")
            return False

        _update_camera_focal_post()
        return True

    @classmethod
    def size_from_projection(cls, keyframe_id):
        fb = cls.get_builder()
        proj = fb.projection_mat(keyframe_id)
        return 2 * (-proj[0][2]), 2 * (-proj[1][2])

    @classmethod
    def update_cameras_from_old_version(cls, head):
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

        update_image_groups(head)

    @classmethod
    def add_camera(cls, headnum, img=None):
        logger = logging.getLogger(__name__)
        settings = get_main_settings()
        head = settings.get_head(headnum)
        fb = cls.get_builder()

        # create camera data
        cam_data = bpy.data.cameras.new("fbCam")
        # create object camera data and insert the camera data
        cam_ob = bpy.data.objects.new("fbCamObj", cam_data)

        cam_ob.rotation_euler = Config.default_camera_rotation
        camnum = len(head.cameras)

        cam_ob.location = (Config.camera_x_step * camnum,
                           - Config.camera_y_step - headnum,
                           Config.camera_z_step)

        # place camera object to our list
        camera = head.cameras.add()
        camera.camobj = cam_ob

        # link camera into scene
        col = attrs.get_obj_collection(head.headobj)
        if col is not None:
            col.objects.link(cam_ob)
        else:
            logger.error("ERROR IN COLLECTIONS")
            bpy.context.scene.collection.objects.link(cam_ob)  # Link to Scene

        # Add Background Image
        cam_data.display_size = Config.default_camera_display_size
        cam_data.lens = head.focal  # From Interface
        cam_data.sensor_width = Config.default_sensor_width
        cam_data.sensor_height = Config.default_sensor_height
        cam_data.show_background_images = True

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

        if img is not None:
            w, h = img.size
        else:
            w = bpy.context.scene.render.resolution_x
            h = bpy.context.scene.render.resolution_y

        camera.set_image_width(w)
        camera.set_image_height(h)

        num = cls.get_next_keyframe()
        camera.set_keyframe(num)

        # Create new keyframe
        projection = coords.projection_matrix(
            w, h, head.focal, Config.default_sensor_width, 0.1, 1000.0)
        fb.set_centered_geo_keyframe(num, projection)
        logger.debug("KEYFRAMES {}".format(str(fb.keyframes())))

        FBLoader.save_only(headnum)
        return camera

    @classmethod
    def add_camera_image(cls, headnum, img_path):
        img = bpy.data.images.load(img_path)
        camera = cls.add_camera(headnum, img)
        return img, camera
