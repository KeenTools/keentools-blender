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
from . fbloader import FBLoader
from bpy.props import (
    BoolProperty,
    IntProperty,
    FloatProperty,
    StringProperty,
    FloatVectorProperty,
    PointerProperty,
    CollectionProperty,
    EnumProperty
)
from bpy.types import PropertyGroup
from . fbdebug import FBDebug
from . config import config


def update_wireframe(self, context):
    FBLoader.update_wireframe()


def update_pin_sensitivity(self, context):
    FBLoader.update_pin_sensitivity()


def update_pin_size(self, context):
    FBLoader.update_pin_size()


def update_debug_log(self, value):
    print("SET: ", value)
    FBDebug.set_active(value)


def update_cam_image(self, context):
    print("SELF", self.keys())
    FBLoader.update_cam_image_size(self)


def update_camera_params(self, contex):
    print("CAMERA CHANGES", self.keys())
    FBLoader.update_camera_params()


class FBCameraItem(PropertyGroup):
    keyframe_id: IntProperty(default=0)
    cam_image: PointerProperty(
        name="Image", type=bpy.types.Image, update=update_cam_image
    )
    image_width: IntProperty(default=-1)
    image_height: IntProperty(default=-1)

    camobj: PointerProperty(
        name="Camera", type=bpy.types.Object
    )
    model_mat: StringProperty(
        name="Model Matrix", default=""
    )
    pins_count: IntProperty(
        name="Pins in Camera", default=0)

    use_in_tex_baking: BoolProperty(name="Use In Texture Baking", default=True)

    def set_model_mat(self, arr):
        b = arr.tobytes()
        self.model_mat = b.hex()

    def get_model_mat(self):
        if len(self.model_mat) == 0:
            return np.eye(4)

        b = bytes.fromhex(self.model_mat)
        return np.frombuffer(b, dtype=np.float32).reshape((4, 4))

    # Simple getters/setters
    def get_image_width(self):
        return self.image_width

    def set_image_width(self, w):
        self.image_width = w

    def get_image_height(self):
        return self.image_height

    def set_image_height(self, h):
        self.image_height = h

    # Real getter from image size
    def get_image_size(self):
        w = -1
        h = -1
        if self.cam_image:
            w, h = self.cam_image.size
            self.image_width = w
            self.image_height = h
        return w, h

    def update_image_size(self):
        w, h = self.get_image_size()
        self.set_image_width(w)
        self.set_image_height(h)

    def is_model_mat_empty(self):
        return self.model_mat == ''

    def is_deleted(self):
        """ Checks that the list item references a non-existent object """
        if self.camobj is None:
            return True
        try:
            res = hasattr(self.camobj, 'users_scene')
            # Object is deleted and not used by the scene
            if len(self.camobj.users_scene) == 0:
                return True
            return False
        except AttributeError:
            return True


class FBHeadItem(PropertyGroup):
    headobj: PointerProperty(name="Head", type=bpy.types.Object)
    cameras: CollectionProperty(name="Cameras", type=FBCameraItem)

    serial_str: StringProperty(name="Serialization string", default="")
    need_update: BoolProperty(name="Mesh need update", default=False)

    def set_serial_str(self, value):
        self.serial_str = value
        self.headobj[config.fb_serial_prop_name[0]] = value

    def get_serial_str(self):
        return self.serial_str

    def is_deleted(self):
        """ Checks that the list item references a non-existent object """
        if self.headobj is None:
            return True
        try:
            res = hasattr(self.headobj, 'users_scene')
            # Object is deleted and not used by the scene
            if len(self.headobj.users_scene) == 0:
                return True
            return False
        except AttributeError:
            return True

    def save_images_src(self):
        res = []
        for c in self.cameras:
            if c.cam_image:
                res.append(c.cam_image.filepath)
        self.headobj[config.fb_images_prop_name[0]] = res
        # Dir name of current scene
        self.headobj[config.fb_dir_prop_name[0]] = bpy.path.abspath("//")


class FBSceneSettings(PropertyGroup):
    # ---------------------
    # Main settings
    # ---------------------
    heads: CollectionProperty(type=FBHeadItem, name="Heads")
    sensor_width: FloatProperty(
        description="The most important parameter. "
                    "Set it according to the photo-camera specification",
        name="Sensor Width (mm)", default=36,
        min=0.1, update=update_camera_params)
    sensor_height: FloatProperty(
        description="Secondary parameter. "
                    "Set it according to the photo-camera specification",
        name="Sensor Height (mm)", default=24,
        min=0.1, update=update_camera_params)
    focal: FloatProperty(
        description="Camera focal length. "
                    "You can found it in photo-camera settings or snapshot EXIF",
        name="Focal Length (mm)", default=50,
        min=0.1, update=update_camera_params)

    frame_width: IntProperty(default=-1)
    frame_height: IntProperty(default=-1)
    # ---------------------
    # Operational settings
    # ---------------------
    opnum: IntProperty(name="Operation Number", default=0)  # Test purpose
    debug_active: BoolProperty(
        description="Not recommended. "
                    "Can extremely enlarge your scene file size",
        name="Debug Log active", default=False, update=update_debug_log)

    pinmode: BoolProperty(name="Pin Mode", default=False)
    force_out_pinmode: BoolProperty(name="Pin Mode", default=False)
    license_error: BoolProperty(name="License Error", default=False)

    # ---------------------
    # Model View parameters
    # ---------------------
    wireframe_opacity: FloatProperty(
        description="Wireframe visual density in pin-mode.",
        name="Wireframe opacity",
        default=0.2, min=0.0, max=1.0,
        update=update_wireframe)
    wireframe_color: FloatVectorProperty(
        description="Color of wireframe mesh in pin-mode",
        name="Wireframe color", subtype='COLOR',
        default=[0.0, 0.0, 0.3], min=0.0, max=1.0, update=update_wireframe)
    show_specials: BoolProperty(
        description="Show guide contours for individual parts of the face",
        name="Special face parts", default=True, update=update_wireframe)

    # Initial pin_size state in FBShaderPoints class
    pin_size: FloatProperty(
        description="Size of visual markers (pins) in pin-mode",
        name="Pin Size",
        default=6.0, min=1.0, max=100.0, update=update_pin_size)
    pin_sensitivity: FloatProperty(
        description="Increase if it is difficult for you to get a pin. "
        "Decrease it if instead of a new pin, you capture the old one",
        name="Pin Sensitivity",
        default=12.0, min=1.0, max=100.0, update=update_pin_sensitivity)

    # Other settings
    rigidity: FloatProperty(
        description="Model deformation sensitivity adjustment. "
        "You can use it in experimental purpose only. Autorigidity is recomended",
        name="Rigidity", default=1.0, min=0.001, max=1000.0)
    check_auto_rigidity: BoolProperty(
        description="Auto Model Rigidity detection. Highly recommended",
        name="auto rigidity", default=True)
    check_ears: BoolProperty(name="Ears", default=True)
    check_eyes: BoolProperty(name="Eyes", default=True)
    check_face: BoolProperty(name="Face", default=True)
    check_headback: BoolProperty(name="Headback", default=True)
    check_jaw: BoolProperty(name="Jaw", default=True)
    check_mouth: BoolProperty(name="Mouth", default=True)
    check_neck: BoolProperty(name="Neck", default=True)

    # Internal use only
    current_headnum: IntProperty(name="Current Head Number", default=-1)
    current_camnum: IntProperty(name="Current Camera Number", default=-1)

    # -------------------------
    # Texture Baking parameters
    # -------------------------
    tex_uv_shape: EnumProperty(name="UV", items=[
                ('uv1', 'Butterfly', 'Pretty standard one-seem Layout', 0),
                ('uv2', 'Legacy', 'Uniform tex scale but many seems', 1),
                ('uv3', 'Spherical', 'Standard wrap-around Layout', 2),
                ('uv4', 'Maxface', 'Maximum face area, non-uniform', 3),
                ], description="UV Layout scheme")
    tex_width: IntProperty(
        description="Width size of output texture",
        name="Texture Width", default=2048)
    tex_height: IntProperty(
        description="Height size of output texture",
        name="Texture Height", default=2048)

    tex_face_angles_affection: FloatProperty(
        description="Deviation angle of normal direction affects "
                    "the choice of camera for baking.",
        name="Face Angles Affection", default=10.0)
    tex_uv_expand_percents: FloatProperty(
        description="Expand texture out of bounds to prevent seams "
                    "visibility. Only if it's greate then zero",
        name="UV Expand Percent", default=0.0)
    tex_back_face_culling: BoolProperty(
        description="Exclude backfacing polygons from baking (Recommended)",
        name="Back Face Culling", default=True)
    tex_equalize_brightness: BoolProperty(
        description="Equalizes the brightness in case of "
                    "a big difference in lightness",
        name="Equalize Brightness", default=False)
    tex_equalize_colour: BoolProperty(
        description="Equalizes colors used from different frames",
        name="Equalize color", default=False)

    # Find Head by Blender object (Head Mesh)
    def find_head_index(self, obj):
        """ Find head index by blender object """
        for i, h in enumerate(self.heads):
            if h.headobj is obj:
                return i  # Found Head index
        return -1  # head object not found

    # Find Camera by Blender object
    def find_cam_index(self, obj):
        for i, h in enumerate(self.heads):
            for j, c in enumerate(h.cameras):
                if c.camobj is obj:
                    return i, j  # Head & Camera indices
        return -1, -1  # camera not found

    # Verify the existence of all this head cameras
    @staticmethod
    def check_head_cams(head):
        for i, c in enumerate(head.cameras):
            if c.is_deleted():
                return False  # Wrong camera in list
        return True  # All head cameras is ok

    # Verify the existence of all heads
    def check_heads(self):
        for i, h in enumerate(self.heads):
            if h.is_deleted():
                return False  # Wrong head object in list
        return True  # All heads is ok

    # Full check heads and cameras existence
    def check_heads_and_cams(self):
        for i, h in enumerate(self.heads):
            if h.is_deleted():
                return False  # Wrong head object in list'
            if not self.check_head_cams(h):
                return False  # Wrong camera
        return True  # All is ok

    # Remove non-existent cameras in list of this head
    @staticmethod
    def fix_head_cams(head):
        status = False  # no changes
        err = []
        for i, c in enumerate(head.cameras):
            if c.is_deleted():
                status = True
                err.append(i)  # Wrong camera in list
        for i in reversed(err):  # Delete in backward order
            head.cameras.remove(i)
        return status  # True if there was any changes

    def fix_heads(self):
        heads_deleted = 0  # no changes
        cams_deleted = 0  # no changes
        err = []
        for i, h in enumerate(self.heads):
            if h.is_deleted():
                heads_deleted += 1  # some changes!
                # Head object is deleted by user
                for c in h.cameras:
                    try:
                        # Remove camera object
                        bpy.data.objects.remove(c.camobj)  # , do_unlink=True
                        cams_deleted += 1
                    except:
                        pass
                err.append(i)  # Wrong head in list
            else:
                if self.fix_head_cams(h):
                    cams_deleted += 1  # At least one camera is deleted
        for i in reversed(err):
            self.heads.remove(i)
        return heads_deleted, cams_deleted

    def head_by_obj(self, obj):
        i = self.find_head_index(obj)
        j, _ = self.find_cam_index(obj)
        return max(i, j)

    def save_cam_settings(self, obj):
        render = bpy.context.scene.render
        d = {
                config.reconstruct_sensor_width_param[0]: self.sensor_width,
                config.reconstruct_focal_param[0]: self.focal,
                config.reconstruct_frame_width_param[0]: render.resolution_x,
                config.reconstruct_frame_height_param[0]: render.resolution_y}
        obj[config.fb_camera_prop_name[0]] = d
