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
from collections import Counter

import bpy
import numpy as np
from bpy.props import (
    StringProperty,
    IntProperty,
)
from bpy.types import Operator

from . utils import manipulate
from . utils import attrs
from . config import Config, ErrorType, BuilderType, get_main_settings
from . fbloader import FBLoader
from . licmanager import FBLicManager
import keentools_facebuilder.blender_independent_packages.pykeentools_loader as pkt


class OBJECT_OT_FBActor(Operator):
    """ Face Builder Action
    """
    bl_idname = Config.fb_actor_operator_idname
    bl_label = "FaceBuilder in Action"
    bl_options = {'REGISTER'}
    bl_description = "Face Builder"

    action: StringProperty(name="Action Name")
    headnum: IntProperty(default=0)
    camnum: IntProperty(default=0)

    tex_name = Config.tex_builder_filename
    mat_name = Config.tex_builder_matname


    @staticmethod
    def get_mesh_uvmap(mesh):
        # if no UVtex - create it
        if not len(mesh.uv_layers) > 0:
            uvtex = mesh.uv_layers.new()
        else:
            uvtex = mesh.uv_layers.active
        return uvtex.data

    def bake_tex(self, headnum):
        logger = logging.getLogger(__name__)
        settings = get_main_settings()
        # headnum = settings.current_headnum
        head = settings.heads[headnum]
        # Add UV
        mesh = head.headobj.data

        # Load FB Object if scene loaded by example
        FBLoader.load_only(headnum)
        fb = FBLoader.get_builder()

        uvmap = self.get_mesh_uvmap(mesh)

        # Generate UVs
        uv_shape = head.tex_uv_shape
        fb.select_uv_set(0)
        if uv_shape == 'uv1':
            fb.select_uv_set(1)
        elif uv_shape == 'uv2':
            fb.select_uv_set(2)
        elif uv_shape == 'uv3':
            fb.select_uv_set(3)

        logger.debug("UV_TYPE: {}".format(uv_shape))

        geo = fb.applied_args_model()
        me = geo.mesh(0)

        # Fill uvs in uvmap
        uvs_count = me.uvs_count()
        for i in range(uvs_count):
            uvmap[i].uv = me.uv(i)

        # There no cameras on object
        if len(head.cameras) == 0:
            return

        w = -1
        h = -1
        changes = 0
        for i, c in enumerate(head.cameras):
            if c.use_in_tex_baking:
                # Image marked to use in baking
                img = c.cam_image
                if img:
                    size = img.size
                    if size[0] != w or size[1] != h:
                        changes += 1
                    w = size[0]
                    h = size[1]

        # We have no background images
        if w <= 0 or h <= 0:
            return

        # Back images has different sizes
        if changes > 1:
            warn = getattr(bpy.ops.wm, Config.fb_warning_operator_callname)
            warn('INVOKE_DEFAULT', msg=ErrorType.BackgroundsDiffer)
            return

        logger.debug("IMAGE SIZE {} {} {}".format(w, h, changes))

        tw = settings.tex_width
        th = settings.tex_height

        # Set camera projection matrix
        FBLoader.set_camera_projection(head.focal, head.sensor_width, w, h)

        imgs = []
        keyframes = []
        wm = bpy.context.window_manager
        wm.progress_begin(0, len(head.cameras) + 1.0)
        for i, cam in enumerate(head.cameras):
            wm.progress_update(i + 1.0)
            # Bake only if 1) Marked 2) Image is exists 3) Some pins added
            if cam.use_in_tex_baking and cam.cam_image and cam.pins_count > 0:
                pix = cam.cam_image.pixels[:]
                imgs.append(np.asarray(pix).reshape((h, w, 4)))
                keyframes.append(cam.keyframe_id)
        wm.progress_end()

        tfaa = settings.tex_face_angles_affection
        tuep = settings.tex_uv_expand_percents
        tbfc = settings.tex_back_face_culling
        teb = settings.tex_equalize_brightness
        tec = settings.tex_equalize_colour
        # Texture Creation
        if len(keyframes) > 0:
            texture = fb.build_texture(
                imgs, keyframes, th, tw, tfaa, tuep, tbfc, teb, tec)

            tex_num = bpy.data.images.find(self.tex_name)

            if tex_num > 0:
                tex = bpy.data.images[tex_num]
                bpy.data.images.remove(tex)

            tex = bpy.data.images.new(
                    self.tex_name, width=tw, height=th,
                    alpha=True, float_buffer=False)
            # Store Baked Texture into blender
            tex.pixels[:] = texture.ravel()
            # Pack image to store in blend-file
            tex.pack()


    def show_texture_in_mat(self):
        settings = get_main_settings()
        tex_num = bpy.data.images.find(self.tex_name)

        if tex_num > 0:
            tex = bpy.data.images[tex_num]
        else:
            tex = None

        if bpy.data.materials.find(self.mat_name) > 0:
            # Material exists
            mat = bpy.data.materials[self.mat_name]

            # Looking for main shader node
            shnum = mat.node_tree.nodes.find('Principled BSDF')
            sh = mat.node_tree.nodes[shnum]

            # Looking for Image Texture node (only one?)
            nodnum = mat.node_tree.nodes.find('Image Texture')
            nod = mat.node_tree.nodes[nodnum]
            nod.image = tex
        else:
            # Create new material
            mat = bpy.data.materials.new(self.mat_name)
            mat.use_nodes = True

            shnum = mat.node_tree.nodes.find('Principled BSDF')
            sh = mat.node_tree.nodes[shnum]
            sh.inputs['Specular'].default_value = 0.0

            nod = mat.node_tree.nodes.new('ShaderNodeTexImage')
            nod.image = tex
            nod.location = Config.image_node_layout_coord

            mat.node_tree.links.new(
                nod.outputs['Color'],
                sh.inputs['Base Color'])

        # Assign Material to Head Object
        headobj = settings.heads[settings.current_headnum].headobj
        if headobj.data.materials:
            headobj.data.materials[0] = mat
        else:
            headobj.data.materials.append(mat)

    @staticmethod
    def get_camera_params(obj):
        logger = logging.getLogger(__name__)
        # Init camera parameters
        data = attrs.get_safe_custom_attribute(
            obj, Config.fb_camera_prop_name[0])
        if not data:
            return None

        try:
            params = {'focal': attrs.get_attr_variant_named(
                data, Config.reconstruct_focal_param),
                'sensor_width': attrs.get_attr_variant_named(
                    data, Config.reconstruct_sensor_width_param),
                'sensor_height': attrs.get_attr_variant_named(
                    data, Config.reconstruct_sensor_width_param),
                'frame_width': attrs.get_attr_variant_named(
                    data, Config.reconstruct_frame_width_param),
                'frame_height': attrs.get_attr_variant_named(
                    data, Config.reconstruct_frame_height_param)}
            logger.debug("LOADED PARAMS {}".format(params))
            if None in params.values():
                return None
        except Exception:
            return None
        return params

    def reconstruct_by_head(self, context):
        """ Reconstruct Cameras and Scene structures by serial """
        logger = logging.getLogger(__name__)
        scene = context.scene
        rx = scene.render.resolution_x
        ry = scene.render.resolution_y
        settings = get_main_settings()

        obj = context.object

        if obj.type != 'MESH':
            return

        # Has object our main attribute?
        if not attrs.has_custom_attribute(obj, Config.version_prop_name[0]):
            return  # No, it hasn't, leave

        # Object marked by our attribute, so can be reconstructed
        error_message = "===============\n" \
                        "Can't reconstruct\n" \
                        "===============\n" \
                        "Object parameters are invalid or missing:\n"

        logger.info("START RECONSTRUCT")

        obj_type = attrs.get_safe_custom_attribute(
                obj, Config.object_type_prop_name[0])
        if obj_type is None:
            obj_type = BuilderType.FaceBuilder
        logger.debug("OBJ_TYPE: {}".format(obj_type))

        if obj_type != BuilderType.FaceBuilder:
            warn = getattr(bpy.ops.wm, Config.fb_warning_operator_callname)
            warn('INVOKE_DEFAULT', msg=ErrorType.CustomMessage,
                 msg_content=error_message + 'Object Type')
            return  # Problem with object type custom attribute

        # Get Mod version
        mod_ver = attrs.get_safe_custom_attribute(
                obj, Config.fb_mod_ver_prop_name[0])
        if mod_ver is None:
            mod_ver = Config.unknown_mod_ver
        logger.debug("MOD_VER {}".format(mod_ver))

        # Get all camera parameters
        params = self.get_camera_params(obj)
        if params is None:
            warn = getattr(bpy.ops.wm, Config.fb_warning_operator_callname)
            warn('INVOKE_DEFAULT', msg=ErrorType.CustomMessage,
                 msg_content=error_message + 'camera')
            return  # One or more parameters undefined
        logger.debug("PARAMS: {}".format(params))

        # Get Serial string
        serial_str = attrs.get_safe_custom_attribute(
                obj, Config.fb_serial_prop_name[0])
        if serial_str is None:
            serial_str = ""
        logger.debug("SERIAL")

        # Get Dir Name
        dir_name = attrs.get_safe_custom_attribute(
                obj, Config.fb_dir_prop_name[0])
        if dir_name is None:
            dir_name = ""
        logger.debug("DIR_NAME: {}".format(dir_name))

        # Get Image Names
        images = attrs.get_safe_custom_attribute(
                obj, Config.fb_images_prop_name[0])
        if type(images) is not list:
            images = []
        logger.debug("IMAGES: {}".format(images))
        logger.debug("PARAMETERS LOADED. START HEAD CREATION")
        # -------------------
        # Fix our settings structure before new head add
        settings.fix_heads()

        headnum = len(settings.heads)
        # Create new head in collection
        head = settings.heads.add()
        head.headobj = obj

        try:
            # Copy serial string from object custom property
            head.set_serial_str(serial_str)
            fb = FBLoader.new_builder(obj_type, mod_ver)
            head.mod_ver = FBLoader.get_builder_version()
            settings.current_head = headnum
            settings.current_camnum = 0
            logger.debug("CREATED MOD_VER {}".format(head.mod_ver))

            head.sensor_width = params['sensor_width']
            head.sensor_height = params['sensor_height']
            head.focal = params['focal']
            scene.render.resolution_x = params['frame_width']
            scene.render.resolution_y = params['frame_height']

            # New head shape
            fb.deserialize(head.get_serial_str())
            # Now reconstruct cameras
            for i, kid in enumerate(fb.keyframes()):
                c = FBLoader.add_camera(headnum, None)
                FBLoader.set_keentools_version(c.camobj)
                c.keyframe_id = kid
                logger.debug("CAMERA CREATED {}".format(kid))
                FBLoader.place_cameraobj(kid, c.camobj, obj)
                c.set_model_mat(fb.model_mat(kid))
                FBLoader.update_pins_count(headnum, i)

            # load background images
            for i, f in enumerate(images):
                logger.debug("IM {} {}".format(i, f))
                img = bpy.data.images.new(f, 0, 0)
                img.source = 'FILE'
                img.filepath = f
                head.cameras[i].cam_image = img

            FBLoader.update_camera_params(head)

        except Exception:
            logger.error("WRONG PARAMETERS")
            for i, c in enumerate(reversed(head.cameras)):
                if c.camobj is not None:
                    # Delete camera object from scene
                    bpy.data.objects.remove(c.camobj, do_unlink=True)
                # Delete link from list
                head.cameras.remove(i)
            settings.heads.remove(headnum)
            scene.render.resolution_x = rx
            scene.render.resolution_y = ry
            logger.debug("SCENE PARAMETERS RESTORED")
            warn = getattr(bpy.ops.wm, Config.fb_warning_operator_callname)
            warn('INVOKE_DEFAULT', msg=ErrorType.CannotReconstruct)
            return

    def unhide_head(self):
        settings = get_main_settings()
        settings.heads[self.headnum].headobj.hide_set(False)
        settings.pinmode = False

    @staticmethod
    def use_this_camera_frame_size():
        # Current camera Background --> Render size
        scene = bpy.context.scene
        settings = get_main_settings()
        headnum = settings.tmp_headnum
        camnum = settings.tmp_camnum
        camera = settings.heads[headnum].cameras[camnum]
        w, h = camera.get_image_size()
        settings.frame_width = w
        settings.frame_height = h
        if w > 0 and h > 0:
            scene.render.resolution_x = w
            scene.render.resolution_y = h

    @staticmethod
    def use_camera_frame_size():
        # Current camera Background --> Render size
        scene = bpy.context.scene
        settings = get_main_settings()
        headnum = settings.current_headnum
        camnum = settings.current_camnum
        camera = settings.heads[headnum].cameras[camnum]
        w, h = camera.get_image_size()
        settings.frame_width = w
        settings.frame_height = h
        if w > 0 and h > 0:
            scene.render.resolution_x = w
            scene.render.resolution_y = h

    @staticmethod
    def use_render_frame_size():
        scene = bpy.context.scene
        settings = get_main_settings()
        settings.frame_width = scene.render.resolution_x
        settings.frame_height = scene.render.resolution_y

    @staticmethod
    def auto_detect_frame_size():
        scene = bpy.context.scene
        settings = get_main_settings()
        headnum = settings.current_headnum
        sizes = []
        for c in settings.heads[headnum].cameras:
            w, h = c.get_image_size()
            sizes.append((w, h))
        cnt = Counter(sizes)
        mc = cnt.most_common(2)
        el = mc[0][0]
        # If most are undefined images
        if el == (-1, -1):
            if len(mc) > 1:
                el = mc[1][0]
        if el[0] > 0:
            scene.render.resolution_x = el[0]
            settings.frame_width = el[0]
        if el[1] > 0:
            scene.render.resolution_y = el[1]
            settings.frame_height = el[1]

    @staticmethod
    def use_render_frame_size_scaled():
        # Allow converts scenes pinned on default cameras
        scene = bpy.context.scene
        settings = get_main_settings()
        headnum = settings.current_headnum
        head = settings.heads[headnum]
        rw = scene.render.resolution_x
        rh = scene.render.resolution_y
        fw = settings.frame_width
        fh = settings.frame_height
        kx = rw / fw
        dy = 0.5 * (rh - fh * kx)

        FBLoader.load_only(headnum)
        fb = FBLoader.get_builder()
        for i, c in enumerate(head.cameras):
            if c.pins_count > 0:
                kid = manipulate.keyframe_by_camnum(headnum, i)
                for n in range(fb.pins_count(kid)):
                    p = fb.pin(kid, n)
                    fb.move_pin(
                        kid, n, (kx * p.img_pos[0], kx * p.img_pos[1] + dy))
                fb.solve_for_current_pins(kid)
        FBLoader.save_only(headnum)

        settings.frame_width = rw
        settings.frame_height = rh

    def draw(self, context):
        """ No need to show panel so empty draw"""
        pass

    def execute(self, context):
        logger = logging.getLogger(__name__)
        if self.action == "reconstruct_by_head":
            self.reconstruct_by_head(context)

        elif self.action == "lic_hardware_id_copy":
            FBLicManager.copy_hardware_id()

        elif self.action == "lic_online_install":
            FBLicManager.install_online_lic()

        elif self.action == 'lic_offline_install':
            FBLicManager.install_offline_lic()

        elif self.action == 'lic_floating_connect':
            FBLicManager.connect_floating_lic()

        elif self.action == 'load_pykeentools':
            pkt.module()

        elif self.action == 'install_latest_nightly_pykeentools':
            pkt.install_from_download(nightly=True)

        elif self.action == 'uninstall_pykeentools':
            pkt.uninstall()

        elif self.action == 'show_tex':
            self.show_texture_in_mat(context)
            # Switch to Material Mode or Back
            manipulate.toggle_mode(('SOLID', 'MATERIAL'))

        elif self.action == 'bake_tex':
            self.bake_tex(self.headnum)
            self.show_texture_in_mat(context)

        elif self.action == "visit_site":
            bpy.ops.wm.url_open(url="https://keentools.io/manual-installation")

        elif self.action == "unhide_head":
            self.unhide_head()

        elif self.action == "about_fix_frame_warning":
            warn = getattr(bpy.ops.wm, Config.fb_warning_operator_callname)
            warn('INVOKE_DEFAULT', msg=ErrorType.AboutFrameSize)

        elif self.action == "auto_detect_frame_size":
            self.auto_detect_frame_size()

        elif self.action == 'use_render_frame_size':
            self.use_render_frame_size()

        elif self.action == 'use_camera_frame_size':
            # Current camera Background --> Render size (by Fix button)
            self.use_camera_frame_size()

        elif self.action == 'use_this_camera_frame_size':
            # Current camera Background --> Render size (by mini-button)
            self.use_this_camera_frame_size()

        elif self.action == 'use_render_frame_size_scaled':
            # Allow converts scenes pinned on default cameras
            self.use_render_frame_size_scaled()  # disabled in interface

        logger.debug("Actor: {}".format(self.action))

        return {'FINISHED'}
