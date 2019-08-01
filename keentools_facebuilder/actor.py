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


from collections import Counter

import bpy
import numpy as np
from bpy.props import (
    StringProperty,
    IntProperty,
)
from bpy.types import Operator

from .config import config, ErrorType
from . fbloader import FBLoader
from . licmanager import FBLicManager
from . config import get_main_settings


class OBJECT_OT_FBActor(Operator):
    """ Face Builder Action
    """
    bl_idname = config.fb_actor_operator_idname
    bl_label = "FaceBuilder in Action"
    bl_options = {'REGISTER'}
    bl_description = "Face Builder"

    action: StringProperty(name="Action Name")
    headnum: IntProperty(default=0)
    camnum: IntProperty(default=0)

    tex_name = config.tex_builder_filename
    mat_name = config.tex_builder_matname

    def get_headnum(self):
        return self.headnum

    def get_camnum(self):
        return self.camnum

    @staticmethod
    def get_mesh_uvmap(mesh):
        # if no UVtex - create it
        if not len(mesh.uv_layers) > 0:
            uvtex = mesh.uv_layers.new()
        else:
            uvtex = mesh.uv_layers.active
        return uvtex.data

    def bake_tex(self):
        scene = bpy.context.scene
        settings = get_main_settings()
        headnum = settings.current_headnum
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

        print("UV_TYPE", uv_shape)

        geo = fb.applied_args_model()
        me = geo.mesh(0)

        # Fill uvs in uvmap
        uvs_count = me.uvs_count()
        for i in range(uvs_count):
            uvmap[i].uv = me.uv(i)

        # There no cameras on object
        if len(head.cameras) == 0:
            return

        W = -1
        H = -1
        changes = 0
        for i, c in enumerate(head.cameras):
            if c.use_in_tex_baking:
                # Image marked to use in baking
                img = c.cam_image
                if img:
                    size = img.size
                    if size[0] != W or size[1] != H:
                        changes += 1
                    W = size[0]
                    H = size[1]

        # We have no background images
        if W <= 0 or H <= 0:
            return

        # Back images has different sizes
        if changes > 1:
            warn = getattr(bpy.ops.wm, config.fb_warning_operator_callname)
            warn('INVOKE_DEFAULT', msg=ErrorType.BackgroundsDiffer)
            return

        print("IMAGE SIZE", W, H, changes)

        TW = settings.tex_width
        TH = settings.tex_height

        # Change Camera Matrix for Image aspect
        # Camera aspect vs Image aspect

        rx = scene.render.resolution_x
        ry = scene.render.resolution_y
        kx = 1.0
        ky = 1.0
        # This is needed because of Image and Render size difference
        FBLoader.set_camera_projection(
            settings.focal,
            settings.sensor_width,
            kx * W, ky * H
        )

        imgs = []
        keyframes = []
        wm = bpy.context.window_manager
        wm.progress_begin(0, len(head.cameras) + 1.0)
        for i, cam in enumerate(head.cameras):
            wm.progress_update(i + 1.0)
            # Bake only if 1) Marked 2) Image is exists 3) Some pins added
            if cam.use_in_tex_baking and cam.cam_image and cam.pins_count > 0:
                pix = cam.cam_image.pixels[:]
                imgs.append(np.asarray(pix).reshape((H, W, 4)))
                keyframes.append(cam.keyframe_id)
        wm.progress_end()

        # API info: build_texture(
        # rgba_imgs_list: List[img],
        # keyframes: List[int],11
        # texture_h: int, texture_w: int,
        # face_angles_affection: float,
        # uv_expand_percents: float,
        # back_face_culling: bool,
        # equalize_brightness: bool, equalize_colour: bool) -> img
        tfaa = settings.tex_face_angles_affection
        tuep = settings.tex_uv_expand_percents
        tbfc = settings.tex_back_face_culling
        teb = settings.tex_equalize_brightness
        tec = settings.tex_equalize_colour
        # Texture Creation
        if len(keyframes) > 0:
            texture = fb.build_texture(
                imgs, keyframes, TH, TW, tfaa, tuep, tbfc, teb, tec)

            print('TEXTURE', texture.shape)

            tex_num = bpy.data.images.find(self.tex_name)

            if tex_num > 0:
                tex = bpy.data.images[tex_num]
                bpy.data.images.remove(tex)

            tex = bpy.data.images.new(
                    self.tex_name, width=TW, height=TH,
                    alpha=True, float_buffer=False)
            # Store Baked Texture into blender
            tex.pixels[:] = texture.ravel()
            # Pack image to store in blend-file
            tex.pack()

    @staticmethod
    def switch_to_mode(context, mode='MATERIAL'):
        # Switch to Mode
        areas = context.workspace.screens[0].areas
        for area in areas:
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.shading.type = mode

    @staticmethod
    def toggle_mode(context, modes=('SOLID', 'MATERIAL')):
        # Switch to Mode
        areas = context.workspace.screens[0].areas
        for area in areas:
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    cur_mode = space.shading.type
                    ind = 0
                    if cur_mode in modes:
                        ind = modes.index(cur_mode)
                        ind += 1
                        if ind >= len(modes):
                            ind = 0
                    space.shading.type = modes[ind]

    def show_texture_in_mat(self, context):
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
            nod.location = config.image_node_layout_coord

            mat.node_tree.links.new(
                nod.outputs['Color'],
                sh.inputs['Base Color'])

        # Assign Material to Head Object
        headobj = settings.heads[settings.current_headnum].headobj
        if headobj.data.materials:
            headobj.data.materials[0] = mat
        else:
            headobj.data.materials.append(mat)


    def get_attr_variant_named(self, data, attr_names):
        for attr in attr_names:
            if attr in data.keys():
                return data[attr]
        return None

    def get_camera_params(self, obj):
        # Init camera parameters
        data = FBLoader.get_safe_custom_attribute(
            obj, config.fb_camera_prop_name[0])
        if not data:
            return None

        try:
            params = {}
            print("CAMERA_PARAMS", config.reconstruct_focal_param)
            params['focal'] = self.get_attr_variant_named(
                data, config.reconstruct_focal_param)
            params['sensor_width'] = self.get_attr_variant_named(
                data, config.reconstruct_sensor_width_param)
            params['sensor_height'] = self.get_attr_variant_named(
                data, config.reconstruct_sensor_width_param)
            params['frame_width'] = self.get_attr_variant_named(
                data, config.reconstruct_frame_width_param)
            params['frame_height'] = self.get_attr_variant_named(
                data, config.reconstruct_frame_height_param)
            print("LOADED PARAMS", params)
            if None in params.values():
                return None
        except:
            return None
        return params


    def reconstruct_by_head(self, context):
        """ Reconstruct Cameras and Scene structures by serial """
        scene = context.scene
        rx = scene.render.resolution_x
        ry = scene.render.resolution_y
        settings = get_main_settings()

        # Some backup
        old_sensor_width = settings.sensor_width
        old_sensor_height = settings.sensor_height
        old_focal = settings.focal

        obj = context.object

        if obj.type != 'MESH':
            return

        # Has object our main attribute?
        if not FBLoader.has_custom_attribute(obj, config.version_prop_name[0]):
            return  # No, it hasn't, leave

        # Object marked by our attribute, so can be reconstructed


        error_message = "===============\n" \
                        "Can't reconstruct\n" \
                        "===============\n" \
                        "Object parameters are invalid or missing:\n"
        print("START RECONSTRUCT")
        print("PARAMS")
        # Get all camera parameters
        params = self.get_camera_params(obj)
        if params is None:
            warn = getattr(bpy.ops.wm, config.fb_warning_operator_callname)
            warn('INVOKE_DEFAULT', msg=ErrorType.CustomMessage,
                 msg_content=error_message + 'camera')
            return  # One or more parameters undefined

        print("SERIAL")
        # Get Serial string
        serial_str = FBLoader.get_safe_custom_attribute(
                obj, config.fb_serial_prop_name[0])
        if not serial_str:
            warn = getattr(bpy.ops.wm, config.fb_warning_operator_callname)
            warn('INVOKE_DEFAULT', msg=ErrorType.CustomMessage,
                 msg_content=error_message + 'serial')
            return  # No serial string custom attribute

        print("DIRNAME")
        # Get Dir Name
        dir_name = FBLoader.get_safe_custom_attribute(
                obj, config.fb_dir_prop_name[0])
        if dir_name is None:
            warn = getattr(bpy.ops.wm, config.fb_warning_operator_callname)
            warn('INVOKE_DEFAULT', msg=ErrorType.CustomMessage,
                 msg_content=error_message + 'dir')
            return  # No dir_name custom attribute

        print("IMAGES")
        # Get Image Names
        images = FBLoader.get_safe_custom_attribute(
                obj, config.fb_images_prop_name[0])
        if (not images) or not (type(images) is list):
            warn = getattr(bpy.ops.wm, config.fb_warning_operator_callname)
            warn('INVOKE_DEFAULT', msg=ErrorType.CustomMessage,
                 msg_content=error_message + 'images')
            return  # Problem with images custom attribute


        print("HEAD CREATION")
        # -------------------
        # Start Creation
        # Fix our settings structure before new head add
        settings.fix_heads()

        headnum = len(settings.heads)
        # Create new head in collection
        head = settings.heads.add()
        head.headobj = obj

        try:
            # Copy serial string from object custom property
            head.set_serial_str(serial_str)
            fb = FBLoader.new_builder()

            settings.sensor_width = params['sensor_width']
            settings.sensor_height = params['sensor_height']
            settings.focal = params['focal']
            scene.render.resolution_x = params['frame_width']
            scene.render.resolution_y = params['frame_height']

            # New head shape
            fb.deserialize(head.get_serial_str())
            # Now reconstruct cameras
            for i, kid in enumerate(fb.keyframes()):
                c = FBLoader.add_camera(headnum, None)
                FBLoader.set_keentools_version(c.camobj)
                c.keyframe_id = kid
                print("CAMERA CREATED", kid)
                FBLoader.place_cameraobj(kid, c.camobj, obj)
                c.set_model_mat(fb.model_mat(kid))
                FBLoader.update_pins_count(headnum, i)

            # load background images
            for i, f in enumerate(images):
                img = bpy.data.images.new(f, 0, 0)
                img.source = 'FILE'
                img.filepath = f
                head.cameras[i].cam_image = img

        except:
            print("WRONG PARAMETERS")
            settings.sensor_width = old_sensor_width
            settings.sensor_height = old_sensor_height
            settings.focal = old_focal
            scene.render.resolution_x = rx
            scene.render.resolution_y = ry
            print("SCENE PARAMETERS RESTORED")
            warn = getattr(bpy.ops.wm, config.fb_warning_operator_callname)
            warn('INVOKE_DEFAULT', msg=ErrorType.CannotReconstruct)
            return


    def draw(self, context):
        """ No need to show panel so empty draw"""
        pass

    def execute(self, context):
        scene = context.scene
        settings = get_main_settings()

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

        elif self.action == 'show_tex':
            self.show_texture_in_mat(context)
            # Switch to Material Mode or Back
            self.toggle_mode(context, ('SOLID', 'MATERIAL'))

        elif self.action == 'bake_tex':
            self.bake_tex()
            self.show_texture_in_mat(context)

        elif self.action == "visit_site":
            bpy.ops.wm.url_open(url="https://keentools.io/manual-installation")

        elif self.action == "unhide_head":
            # settings.heads[self.headnum].headobj.hide_viewport = False
            settings.heads[self.headnum].headobj.hide_set(False)
            settings.pinmode = False

        elif self.action == "about_fix_frame_warning":
            warn = getattr(bpy.ops.wm, config.fb_warning_operator_callname)
            warn('INVOKE_DEFAULT', msg=ErrorType.AboutFrameSize)

        elif self.action == "auto_detect_frame_size":
            headnum = settings.current_headnum
            sizes = []
            for c in settings.heads[headnum].cameras:
                # w = c.get_image_width()
                # h = c.get_image_height()
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
            print('COUNTER', mc)

        elif self.action == 'use_render_frame_size':
            settings.frame_width = scene.render.resolution_x
            settings.frame_height = scene.render.resolution_y

        elif self.action == 'use_camera_frame_size':
            # Current camera Background --> Render size
            headnum = settings.current_headnum
            camnum = settings.current_camnum
            camera = settings.heads[headnum].cameras[camnum]
            w, h = camera.get_image_size()
            settings.frame_width = w
            settings.frame_height = h
            if w > 0 and h > 0:
                scene.render.resolution_x = w
                scene.render.resolution_y = h

        elif self.action == 'use_this_camera_frame_size':
            # Current camera Background --> Render size
            headnum = settings.tmp_headnum
            camnum = settings.tmp_camnum
            camera = settings.heads[headnum].cameras[camnum]
            w, h = camera.get_image_size()
            settings.frame_width = w
            settings.frame_height = h
            if w > 0 and h > 0:
                scene.render.resolution_x = w
                scene.render.resolution_y = h

        elif self.action == 'use_render_frame_size_scaled':
            # Allow converts scenes pinned on default cameras
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
                    kid = FBLoader.keyframe_by_camnum(headnum, i)
                    for n in range(fb.pins_count(kid)):
                        p = fb.pin(kid, n)
                        fb.move_pin(
                            kid, n, (kx * p.img_pos[0], kx * p.img_pos[1] + dy))
                    fb.solve_for_current_pins(kid)
            FBLoader.save_only(headnum)

            settings.frame_width = rw
            settings.frame_height = rh

        self.report({'INFO'}, "Actor: {}".format(self.action))

        return {'FINISHED'}
