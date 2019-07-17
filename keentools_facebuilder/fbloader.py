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
import numpy as np

from . utils import (
    FBPoints2D, FBPoints3D, FBText, FBCalc, FBEdgeShader,
    FBStopTimer
)
from . builder import UniBuilder
from . fbdebug import FBDebug
from . config import config, get_main_settings, BuilderType
from pykeentools import UnlicensedException


class FBLoader:
    # Builder selection: FaceBuilder or BodyBuilder
    builder = UniBuilder(config.default_builder)

    # Current View Pins draw
    points2d = FBPoints2D()
    # Surface points draw
    points3d = FBPoints3D()
    # Text output in Modal mode
    texter = FBText()
    # Wireframe shader object
    wireframer = FBEdgeShader()
    # Update timer
    draw_timer_handler = None

    # Pins
    spins = []  # current screen pins
    current_pin = None
    current_pin_num = -1

    last_context = None

    POINT_SENSITIVITY = config.default_POINT_SENSITIVITY
    PIXEL_SIZE = 0.1  # Auto Calculated

    # Functions for Custom Attributes perform
    @classmethod
    def has_custom_attribute(cls, obj, attr_name):
        return attr_name in obj.keys()

    @classmethod
    def get_custom_attribute(cls, obj, attr_name):
        return obj[attr_name]

    @classmethod
    def get_safe_custom_attribute(cls, obj, attr_name):
        if cls.has_custom_attribute(obj, attr_name):
            return obj[attr_name]
        else:
            return None

    @classmethod
    def get_custom_attribute_variants(cls, obj, attr_names):
        for attr in attr_names:
            res = cls.get_safe_custom_attribute(obj, attr)
            if res:
                return res
        return None

    @classmethod
    def set_custom_attribute(cls, obj, attr_name, val):
        obj[attr_name] = val

    @classmethod
    def has_keentools_attributes(cls, obj):
        attr_name = config.version_prop_name[0]
        if cls.has_custom_attribute(obj, attr_name):
            return True
        return False

    @classmethod
    def set_keentools_version(cls, obj):
        attr_name = config.version_prop_name[0]
        cls.set_custom_attribute(obj, attr_name, config.addon_version)

    # -----------------
    @classmethod
    def get_fb_collection(cls):
        """ Singleton for FB objects collection """
        col_name = config.default_FB_COLLECTION_NAME
        if col_name in bpy.data.collections:
            return bpy.data.collections[col_name]
        fb_col = bpy.data.collections.new(col_name)
        bpy.context.scene.collection.children.link(fb_col)
        return fb_col

    @classmethod
    def add_to_fb_collection(cls, obj):
        fb_col = cls.get_fb_collection()
        fb_col.objects.link(obj)

    @classmethod
    def update_cam_image_size(cls, cam_item):
        cam_item.update_image_size()

    @classmethod
    def update_camera_params(cls):
        """ Update when some camera parameters changes
            Warning! Result may be unstable if some object where deleted
        """
        settings = get_main_settings()
        scene = bpy.context.scene

        # Check scene consistency
        heads_deleted, cams_deleted = settings.fix_heads()

        for headnum, head in enumerate(settings.heads):

            rx = scene.render.resolution_x
            ry = scene.render.resolution_y

            fb = cls.get_builder()
            cls.load_only(headnum)

            max_index = -1
            max_pins = -1
            for i, c in enumerate(head.cameras):
                kid = c.keyframe_id
                cls.set_camera_projection(
                    settings.focal, settings.sensor_width, rx, ry)
                # We are looking for keyframe that has maximum pins
                if c.pins_count > 0:
                    if max_pins < c.pins_count:
                        max_index = kid
                        max_pins = c.pins_count
                c.camobj.data.lens = settings.focal
                c.camobj.data.sensor_width = settings.sensor_width

            if cls.get_builder_type() == BuilderType.FaceBuilder:
                fb.set_auto_rigidity(settings.check_auto_rigidity)
                fb.set_rigidity(settings.rigidity)

            if max_index >= 0:
                try:
                    # Solver
                    fb.solve_for_current_pins(max_index)
                    print("SOLVED", max_index)

                except UnlicensedException:
                    settings.force_out_pinmode = True
                    settings.license_error = True
                    # FBLoader.out_pinmode(context, headnum, camnum)
                    cls.report({'INFO'}, "LICENSE EXCEPTION")

            # Head Mesh update
            FBCalc.update_head_mesh(fb, head.headobj)
            if settings.pinmode:
                cls.fb_redraw(headnum, camnum)
            cls.update_cameras(headnum)
            cls.save_only(headnum)

    @classmethod
    def update_pixel_size(cls, context):
        ps = FBCalc.get_pixel_relative_size(context)
        cls.PIXEL_SIZE = ps

    @classmethod
    def tolerance_dist(cls):  # distance * sensitivity
        return cls.POINT_SENSITIVITY * cls.PIXEL_SIZE

    @classmethod
    def tolerance_dist2(cls):  # squared distance
        return (cls.POINT_SENSITIVITY * cls.PIXEL_SIZE)**2

    @classmethod
    def get_builder(cls):
        return cls.builder.get_builder()

    @classmethod
    def new_builder(cls, builder_type=BuilderType.NoneBuilder):
        return cls.builder.new_builder(builder_type)

    @classmethod
    def get_builder_type(cls):
        return cls.builder.get_builder_type()

    # --- bpy dependent
    @classmethod
    def force_undo_push(cls):
        cls.inc_operation()
        bpy.ops.ed.undo_push()

    @staticmethod
    def inc_operation():
        """ Debug purpose """
        settings = get_main_settings()
        settings.opnum += 1

    @staticmethod
    def get_operation():
        """ Debug purpose """
        settings = get_main_settings()
        return settings.opnum

    @staticmethod
    def hide_other_cameras(context, headnum, camnum):
        settings = get_main_settings()
        head = settings.heads[headnum]
        for i, c in enumerate(head.cameras):
            if i != camnum:
                # Hide camera
                c.camobj.hide_viewport = True

    @staticmethod
    def show_all_cameras(context, headnum):
        settings = get_main_settings()
        head = settings.heads[headnum]
        for i, c in enumerate(head.cameras):
            # Hide camera
            c.camobj.hide_viewport = False

    @classmethod
    def out_pinmode(cls, context, headnum, camnum):
        settings = get_main_settings()
        cls.unregister_handlers()
        cls.fb_save(headnum, camnum)
        cls.wireframer.unregister_handler()
        headobj = settings.heads[headnum].headobj
        # Show geometry
        headobj.hide_viewport = False
        settings.pinmode = False

        cls.current_pin = None
        cls.show_all_cameras(context, headnum)
        # === Debug use only ===
        FBDebug.add_event_to_queue('OUT_PIN_MODE', (0, 0))
        FBDebug.output_event_queue()
        FBDebug.clear_event_queue()
        # === Debug use only ===
        FBStopTimer.stop()
        print("STOPPER STOP")

    @staticmethod
    def keyframe_by_camnum(headnum, camnum):
        settings = get_main_settings()
        if headnum >= len(settings.heads):
            return -1
        if camnum >= len(settings.heads[headnum].cameras):
            return -1
        return settings.heads[headnum].cameras[camnum].keyframe_id

    @classmethod
    def save_only(cls, headnum):
        fb = cls.get_builder()
        settings = get_main_settings()
        head = settings.heads[headnum]
        # Save block
        head.set_serial_str(fb.serialize())

    @classmethod
    def save_camera(cls, headnum, camnum):
        fb = cls.get_builder()
        scene = bpy.context.scene
        settings = get_main_settings()
        cam = heads[headnum].cameras[camnum]
        kid = cls.keyframe_by_camnum(headnum, camnum)

        cam.set_model_mat(fb.model_mat(kid))
        cam.set_frame_size(
            scene.render.resolution_x,
            scene.render.resolution_y)

    @classmethod
    def fb_save(cls, headnum, camnum):
        """ Face Builder Serialize Model Info """
        fb = cls.get_builder()
        scene = bpy.context.scene
        settings = get_main_settings()
        head = settings.heads[headnum]
        cam = head.cameras[camnum]

        # Save block
        head.set_serial_str(fb.serialize())

        kid = cls.keyframe_by_camnum(headnum, camnum)
        cam.set_model_mat(fb.model_mat(kid))
        # Save images list on headobj
        head.save_images_src()
        settings.save_cam_settings(head.headobj)

    @classmethod
    def fb_redraw(cls, headnum, camnum):
        scene = bpy.context.scene
        fb = cls.get_builder()
        settings = get_main_settings()
        head = settings.heads[headnum]
        cam = head.cameras[camnum]
        headobj = head.headobj
        camobj = cam.camobj
        kid = cls.keyframe_by_camnum(headnum, camnum)
        # Camera update
        cls.place_cameraobj(kid, camobj, headobj)
        # Head Mesh update
        FBCalc.update_head_mesh(fb, headobj)
        # Load pins from model
        cls.spins = cls.img_points(kid)
        cls.update_surface_points(headobj, kid)
        # Shader update
        cls.wireframer.init_geom_data(headobj)
        cls.wireframer.create_batches()

    @classmethod
    def create_batch_2d(cls, context=None):
        """ Main Pin Draw Batch"""
        if context is None:
            context = cls.last_context
        else:
            cls.last_context = context

        points = cls.spins.copy()
        scene = context.scene
        asp = scene.render.resolution_y / scene.render.resolution_x

        x1, y1, x2, y2 = FBCalc.get_camera_border(context)

        for i, p in enumerate(points):
            x, y = FBCalc.image_space_to_region(p[0], p[1], x1, y1, x2, y2)
            points[i] = (x, y)

        vertex_colors = [(1.0, 0.0, 0.0, 1.0) for _ in range(len(points))]

        if cls.current_pin and cls.current_pin_num < len(vertex_colors):
            vertex_colors[cls.current_pin_num] = (1.0, 0.0, 1.0, 1.0)

        # Sensitivity indicator
        points.append(
            (FBCalc.image_space_to_region(
                -0.5 - cls.PIXEL_SIZE * cls.POINT_SENSITIVITY, -asp * 0.5,
                x1, y1, x2, y2))
        )
        # Camera corners
        points.append(
            (FBCalc.image_space_to_region(
                -0.5, -asp * 0.5, x1, y1, x2, y2))
        )
        points.append(
            (FBCalc.image_space_to_region(
                0.5, asp * 0.5,
                x1, y1, x2, y2))
        )
        vertex_colors.append((0, 1, 0, 0.2))  # sensitivity indicator
        vertex_colors.append((1, 0, 1, 1))  # camera corner
        vertex_colors.append((1, 0, 1, 1))  # camera corner

        cls.points2d.set_vertices_colors(points, vertex_colors)
        cls.points2d.create_batch()

    # --------------------
    # Update functions
    # --------------------
    @classmethod
    def update_surface_points(
            cls, headobj, keyframe=-1,
            allcolor=(0, 0, 1, 0.15), selcolor=(0, 1, 0, 1)):
        # Load 3D pins
        verts, colors = cls.surface_points(
            headobj, keyframe, allcolor, selcolor)

        if len(verts) > 0:
            # Object matrix usage
            m = np.array(headobj.matrix_world, dtype=np.float32).transpose()
            vv = np.ones((len(verts), 4), dtype=np.float32)
            vv[:, :-1] = verts
            vv = vv @ m
            # Transformed vertices
            verts = vv[:, :3]

        cls.points3d.set_vertices_colors(verts, colors)
        cls.points3d.create_batch()

    @classmethod
    def update_wireframe(cls, obj):
        settings = get_main_settings()
        color = settings.wireframe_color

        cls.wireframer.init_color_data(
            (color[0], color[1], color[2], settings.wireframe_opacity)
        )
        if settings.show_specials and (
                cls.get_builder_type() == BuilderType.FaceBuilder):
            mesh = obj.data
            # Check to prevent shader problem
            if len(mesh.edges) * 2 == len(cls.wireframer.edges_colors):
                cls.wireframer.init_special_areas2(
                    obj.data,
                    (1.0 - color[0], 1.0 - color[1], 1.0 - color[2],
                     settings.wireframe_opacity)
                )
            else:
                print("COMPARE PROBLEM")
                print("EDGES", len(mesh.edges))
                print("EDGE_COLORS", len(cls.wireframer.edges_colors))
        cls.wireframer.create_batches()

    @classmethod
    def update_pin_sensitivity(cls):
        settings = get_main_settings()
        cls.POINT_SENSITIVITY = settings.pin_sensitivity

    @classmethod
    def update_pin_size(cls):
        settings = get_main_settings()
        cls.points2d.set_point_size(settings.pin_size)
        cls.points3d.set_point_size(settings.pin_size)

    @classmethod
    def update_cameras(cls, headnum):
        """ Update positions for all cameras """
        fb = cls.get_builder()
        settings = get_main_settings()
        head = settings.heads[headnum]
        headobj = head.headobj

        for i, cam in enumerate(head.cameras):
            camobj = cam.camobj
            if cam.pins_count > 0:
                # Camera update only if pins is present
                kid = cls.keyframe_by_camnum(headnum, i)
                cls.place_cameraobj(kid, camobj, headobj)
                cam.set_model_mat(fb.model_mat(kid))

    @classmethod
    def update_cam_image(cls, cam_item):
        """ Update camera background image """
        cam_data = cam_item.camobj.data
        cam_data.show_background_images = True

        if len(cam_data.background_images) == 0:
            b = cam_data.background_images.new()
        else:
            b = cam_data.background_images[0]

        b.image = cam_item.cam_image

        b.frame_method = 'CROP'
        b.show_on_foreground = False  # True
        b.alpha = 1.0  # 0.5

    # --------------------
    @classmethod
    def surface_points(
            cls, headobj, keyframe=-1,
            allcolor=(0, 0, 1, 0.15), selcolor=(0, 1, 0, 1)):
        """ Load 3D pin points """
        verts = []
        colors = []

        fb = cls.get_builder()

        for k in fb.keyframes():
            for i in range(fb.pins_count(k)):
                pin = fb.pin(k, i)
                p = FBCalc.pin_to_xyz(pin, headobj)
                verts.append(p)
                if k == keyframe:
                    colors.append(selcolor)
                else:
                    colors.append(allcolor)
        return verts, colors

    @classmethod
    def img_points(cls, keyframe):
        scene = bpy.context.scene
        w = scene.render.resolution_x
        h = scene.render.resolution_y

        fb = cls.get_builder()

        pins_count = fb.pins_count(keyframe)

        verts = []
        for i in range(pins_count):
            pin = fb.pin(keyframe, i)
            x, y = pin.img_pos
            verts.append((FBCalc.frame_to_image_space(x, y, w, h)))
        return verts

    @classmethod
    def place_cameraobj(cls, keyframe, camobj, headobj):
        fb = cls.get_builder()
        camobj.matrix_world = FBCalc.calc_model_mat(
            fb.model_mat(keyframe),
            headobj.matrix_world
        )

    @classmethod
    def set_camera_projection(cls, fl, sw, rx, ry,
                              near_clip=0.1, far_clip=1000.0):
        CAMERA_W = rx  # Camera Width in pixels 1920
        CAMERA_H = ry  # Camera Height in pixels 1080
        FOCAL_LENGTH = fl
        SENSOR_WIDTH = sw
        fb = cls.get_builder()

        # This works only when Camera Sensor Mode is Auto
        if CAMERA_W < CAMERA_H:
            SENSOR_WIDTH = sw * CAMERA_W / CAMERA_H

        PROJECTION = FBCalc.projection_matrix(
            CAMERA_W, CAMERA_H, FOCAL_LENGTH, SENSOR_WIDTH,
            near_clip, far_clip)
        fb.set_projection_mat(PROJECTION)

    @classmethod
    def register_handlers(cls, args, context):
        cls.unregister_handlers()  # Experimental

        cls.points3d.register_handler(args)
        cls.points2d.register_handler(args)
        # Draw text on screen registration
        cls.texter.register_handler(args)
        # Timer for continuous update modal view
        cls.draw_timer_handler = context.window_manager.event_timer_add(
            time_step=0.2, window=context.window
        )

    @classmethod
    def unregister_handlers(cls):
        if cls.draw_timer_handler is not None:
            bpy.context.window_manager.event_timer_remove(
                cls.draw_timer_handler
            )
        cls.draw_timer_handler = None
        cls.texter.unregister_handler()
        cls.points2d.unregister_handler()
        cls.points3d.unregister_handler()

    @classmethod
    def update_pins_count(cls, headnum, camnum):
        settings = get_main_settings()
        head = settings.heads[headnum]
        cam = head.cameras[camnum]
        fb = cls.get_builder()
        kid = cls.keyframe_by_camnum(headnum, camnum)
        pins_count = fb.pins_count(kid)
        print("HEADNUM", headnum)
        print("CAMNUM", camnum)
        print("KID", kid)
        cam.pins_count = pins_count
        print("UPDATE_PINS_COUNT", pins_count)

    @classmethod
    def get_next_keyframe(cls):
        fb = cls.get_builder()
        kfs = fb.keyframes()
        if kfs:
            return max(kfs) + 1
        return 1

    @classmethod
    def get_builder_mesh(cls, builder, mesh_name='keentools_mesh',
                               masks=()):
        for i, m in enumerate(masks):
            builder.set_mask(i, m)

        # default UV
        builder.select_uv_set(0)

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
        # mesh.auto_smooth_angle = 3.1415927410125732

        return mesh


    @classmethod
    def universal_mesh_loader(cls, builder_type,
                              mesh_name='keentools_mesh', masks=()):
        stored_builder_type = FBLoader.get_builder_type()
        builder = cls.new_builder(builder_type)

        mesh = cls.get_builder_mesh(builder, mesh_name, masks)

        # Restore builder
        cls.new_builder(stored_builder_type)
        return mesh

    @classmethod
    def load_only(cls, headnum):
        settings = get_main_settings()
        head = settings.heads[headnum]
        # Load serialized data
        fb = cls.get_builder()
        if not fb.deserialize(head.get_serial_str()):
            print('DESERIALIZE ERROR: ', head.get_serial_str())

    @classmethod
    def load_all(cls, headnum, camnum, center=False):
        scene = bpy.context.scene
        settings = get_main_settings()
        head = settings.heads[headnum]
        cam = head.cameras[camnum]
        camobj = cam.camobj
        headobj = head.headobj
        # end objects definition

        # Load serialized data
        fb = cls.get_builder()
        if not fb.deserialize(head.get_serial_str()):
            print('DESERIALIZE ERROR: ', head.get_serial_str())

        # Check Scene consistency

        # Set projection matrix
        rx = scene.render.resolution_x
        ry = scene.render.resolution_y
        cls.set_camera_projection(
            settings.focal, settings.sensor_width, rx, ry)

        # Update all cameras model_mat
        for i, c in enumerate(head.cameras):
            kid = c.keyframe_id
            pins_count = fb.pins_count(kid)
            if pins_count == 0:
                if center or c.is_model_mat_empty():
                    fb.center_model_mat(kid)  # Center if no pins on camera
            else:
                fb.set_model_mat(kid, c.get_model_mat())

        kid = cls.keyframe_by_camnum(headnum, camnum)
        # Move current camera
        cls.place_cameraobj(kid, camobj, headobj)
        # Load pins from model
        cls.spins = cls.img_points(kid)
        cls.current_pin = None
        print("LOAD MODEL END")

    @classmethod
    def add_camera(cls, headnum, img=None):
        # scene = bpy.context.scene
        settings = get_main_settings()
        fb = cls.get_builder()

        # create camera data
        cam_data = bpy.data.cameras.new("fbCam")
        # create object camera data and insert the camera data
        cam_ob = bpy.data.objects.new("fbCamObj", cam_data)

        cam_ob.rotation_euler = [3.1415927410125732 * 0.5, 0, 0]
        camnum = len(settings.heads[headnum].cameras)

        cam_ob.location = [2 * camnum, -5 - headnum, 0.5]

        # place camera object to our list
        camera = settings.heads[headnum].cameras.add()
        camera.camobj = cam_ob

        num = cls.get_next_keyframe()
        # Create new keyframe
        fb.set_keyframe(num)
        camera.keyframe_id = num

        # link camera into scene
        cls.add_to_fb_collection(cam_ob)
        # scene.collection.objects.link(cam_ob)  # Link to Scene

        # Add Background Image
        cam_data.display_size = 0.75  # Camera Size
        cam_data.lens = settings.focal  # From Interface
        cam_data.sensor_width = settings.sensor_width
        cam_data.show_background_images = True

        if len(cam_data.background_images) == 0:
            b = cam_data.background_images.new()
        else:
            b = cam_data.background_images[0]

        if img is not None:
            b.image = img
            settings.heads[headnum].cameras[camnum].cam_image = img
        # b.image = settings.heads[headnum].cameras[camnum].cam_image
        b.frame_method = 'CROP'
        b.show_on_foreground = False  # True
        b.alpha = 1.0  # 0.5

        # scene.update()  # Removed from API
        return camera

    @classmethod
    def add_camera_image(cls, headnum, img_path):
        img = bpy.data.images.load(img_path)
        cam_ob = cls.add_camera(headnum, img)
        return img
