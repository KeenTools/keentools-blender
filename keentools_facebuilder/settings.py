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
from . config import Config, get_main_settings, get_operators
from .utils.manipulate import what_is_state


def update_wireframe(self, context):
    settings = get_main_settings()
    headnum = settings.current_headnum
    head = settings.get_head(headnum)
    FBLoader.viewport().update_wireframe(
        FBLoader.get_builder_type(), head.headobj)


def update_pin_sensitivity(self, context):
    FBLoader.viewport().update_pin_sensitivity()


def update_pin_size(self, context):
    FBLoader.viewport().update_pin_size()


def update_debug_log(self, value):
    FBDebug.set_active(value)


def update_cam_image(self, context):
    FBLoader.update_cam_image_size(self)


def update_sensor_width(self, context):
    self.sensor_height = self.sensor_width * 0.666666667
    FBLoader.update_camera_params(self)


def update_sensor_height(self, context):
    FBLoader.update_camera_params(self)


def update_focal(self, context):
    settings = get_main_settings()
    if not settings.pinmode:
        FBLoader.update_all_camera_focals(self)


def update_blue_camera_button(self, context):
    settings = get_main_settings()
    if not settings.blue_camera_button:
        op = getattr(get_operators(), Config.fb_exit_pinmode_callname)
        op('EXEC_DEFAULT')
        settings.blue_camera_button = True


def update_blue_head_button(self, context):
    settings = get_main_settings()
    if not settings.blue_head_button:
        op = getattr(get_operators(), Config.fb_select_head_callname)
        op('EXEC_DEFAULT')
        settings.blue_head_button = True


def update_mesh_parts(self, context):
    settings = get_main_settings()
    state, headnum = what_is_state()

    if headnum < 0:
        return

    head = settings.get_head(headnum)
    masks = [head.check_ears, head.check_eyes, head.check_face,
             head.check_headback, head.check_jaw, head.check_mouth,
             head.check_neck, head.check_nose]

    old_mesh = head.headobj.data
    # Create new mesh
    mesh = FBLoader.get_builder_mesh(FBLoader.get_builder(), 'FBHead_mesh',
                                     tuple(masks),
                                     uv_set=head.tex_uv_shape)
    try:
        # Copy old material
        if old_mesh.materials:
            mesh.materials.append(old_mesh.materials[0])
    except Exception:
        pass
    head.headobj.data = mesh
    if settings.pinmode:
        # Update wireframe structures
        FBLoader.viewport().wireframer().init_geom_data(head.headobj)
        FBLoader.viewport().wireframer().init_edge_indices(head.headobj)
        FBLoader.viewport().update_wireframe(
            FBLoader.get_builder_type(), head.headobj)

    mesh_name = old_mesh.name
    # Delete old mesh
    bpy.data.meshes.remove(old_mesh, do_unlink=True)
    mesh.name = mesh_name


class FBExifItem(PropertyGroup):
    info_message: StringProperty(name="EXIF Info Message", default="")
    sizes_message: StringProperty(name="EXIF Sizes Message", default="")

    focal: FloatProperty(default=-1.0)
    focal35mm: FloatProperty(default=-1.0)
    focal_x_res: FloatProperty(default=-1.0)
    focal_y_res: FloatProperty(default=-1.0)
    units: StringProperty(default="inch")  # or cm
    sensor_width: FloatProperty(default=-1.0)
    sensor_length: FloatProperty(default=-1.0)

    # from EXIF tags Image_ImageWidth, Image_ImageLength
    image_width: FloatProperty(default=-1.0)
    image_length: FloatProperty(default=-1.0)

    # from EXIF tag ExifImageWidth, ExifImageLength
    exif_width: FloatProperty(default=-1.0)
    exif_length: FloatProperty(default=-1.0)

    # from image file
    real_width: FloatProperty(default=-1.0)
    real_length: FloatProperty(default=-1.0)

    def calculated_image_size(self):
        if self.image_width > 0.0 and self.image_length > 0.0:
            w = self.image_width
            h = self.image_length
        else:
            w = self.exif_width
            h = self.exif_length
        return w, h


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
    tmp_model_mat: StringProperty(
        name="Temporary Model Matrix", default=""
    )
    pins_count: IntProperty(
        name="Pins in Camera", default=0)

    use_in_tex_baking: BoolProperty(name="Use In Texture Baking", default=True)

    @staticmethod
    def convert_matrix_to_str(arr):
        b = arr.tobytes()
        return b.hex()

    @staticmethod
    def convert_str_to_matrix(mat):
        if len(mat) == 0:
            return np.eye(4)
        b = bytes.fromhex(mat)
        return np.frombuffer(b, dtype=np.float32).reshape((4, 4))

    def set_model_mat(self, arr):
        self.model_mat = self.convert_matrix_to_str(arr)

    def get_model_mat(self):
        return self.convert_str_to_matrix(self.model_mat)

    def set_tmp_model_mat(self, arr):
        self.tmp_model_mat = self.convert_matrix_to_str(arr)

    def get_tmp_model_mat(self):
        return self.convert_str_to_matrix(self.tmp_model_mat)

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

    def delete_cam_background_images(self):
        if self.camobj is None:
            return
        for im in reversed(self.camobj.data.background_images):
            self.camobj.data.background_images.remove(im)
        self.camobj.data.show_background_images = False

    def delete_cam_image(self):
        self.cam_image = None
        self.delete_cam_background_images()

    def delete_camobj(self):
        bpy.data.objects.remove(self.camobj, do_unlink=True)

    def get_keyframe(self):
        return self.keyframe_id

    def set_keyframe(self, num):
        self.keyframe_id = num

    def has_pins(self):
        return self.pins_count > 0

    def get_abspath(self):
        if self.cam_image is not None:
            return bpy.path.abspath(self.cam_image.filepath)
        else:
            return None

    def get_image_name(self):
        if self.cam_image is not None:
            return self.cam_image.name
        else:
            return 'N/A'


class FBHeadItem(PropertyGroup):
    mod_ver: IntProperty(name="Modifier Version", default=-1)
    headobj: PointerProperty(name="Head", type=bpy.types.Object)
    cameras: CollectionProperty(name="Cameras", type=FBCameraItem)

    sensor_width: FloatProperty(
        description="The length of the longest side "
                    "of the camera sensor in millimetres",
        name="Sensor Width (mm)", default=36,
        min=0.1, update=update_sensor_width)
    sensor_height: FloatProperty(
        description="Secondary parameter. "
                    "Set it according to the real camera specification."
                    "This parameter is not used if Sensor Width is greater",
        name="Sensor Height (mm)", default=24,
        min=0.1, update=update_sensor_height)
    focal: FloatProperty(
        description="Focal length in millimetres",
        name="Focal Length (mm)", default=50,
        min=0.1, update=update_focal)

    auto_focal_estimation: BoolProperty(
        name="Focal Length Estimation",
        description="When turned on, FaceBuilder will try to estimate "
                    "focal length based on the position of the model "
                    "in the frame",
        default=False)

    check_ears: BoolProperty(name="Ears", default=True,
                             update=update_mesh_parts)
    check_eyes: BoolProperty(name="Eyes", default=True,
                             update=update_mesh_parts)
    check_face: BoolProperty(name="Face", default=True,
                             update=update_mesh_parts)
    check_headback: BoolProperty(name="Headback", default=True,
                                 update=update_mesh_parts)
    check_jaw: BoolProperty(name="Jaw", default=True,
                            update=update_mesh_parts)
    check_mouth: BoolProperty(name="Mouth", default=True,
                              update=update_mesh_parts)
    check_neck: BoolProperty(name="Neck", default=True,
                             update=update_mesh_parts)
    check_nose: BoolProperty(name="Nose", default=True,
                             update=update_mesh_parts)

    serial_str: StringProperty(name="Serialization string", default="")
    tmp_serial_str: StringProperty(name="Temporary Serialization", default="")
    need_update: BoolProperty(name="Mesh need update", default=False)

    tex_uv_shape: EnumProperty(name="UV", items=[
                ('uv0', 'Butterfly', 'A one-seam layout for common use',
                 'UV', 0),
                ('uv1', 'Legacy',
                 'A layout with minimal distortions but many seams', 'UV', 1),
                ('uv2', 'Spherical', 'A wrap-around layout', 'UV', 2),
                ('uv3', 'Maxface',
                 'Maximum face resolution, low uniformness', 'UV', 3),
                ], description="UV Layout", update=update_mesh_parts)

    use_exif: BoolProperty(
        name="Use EXIF if available in file",
        description="Automatically detects Focal Length & Sensor Size "
                    "from EXIF data in image file if available",
        default=True)

    exif: PointerProperty(type=FBExifItem)

    def get_camera(self, camnum):
        if camnum < 0 and len(self.cameras) + camnum >= 0:
            return self.cameras[len(self.cameras) + camnum]
        if 0 <= camnum <= len(self.cameras):
            return self.cameras[camnum]
        else:
            return None

    def set_serial_str(self, value):
        self.serial_str = value
        self.headobj[Config.fb_serial_prop_name[0]] = value

    def get_serial_str(self):
        return self.serial_str

    def get_tmp_serial_str(self):
        return self.tmp_serial_str

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

    def get_last_camnum(self):
        return len(self.cameras) - 1

    def get_keyframe(self, camnum):
        camera = self.get_camera(camnum)
        if camera is not None:
            return camera.get_keyframe()
        else:
            return -1

    def has_cameras(self):
        return len(self.cameras) > 0

    def has_pins(self):
        for c in self.cameras:
            if c.has_pins():
                return True
        return False

    def save_images_src(self):
        res = []
        for c in self.cameras:
            if c.cam_image:
                res.append(c.cam_image.filepath)
        self.headobj[Config.fb_images_prop_name[0]] = res
        # Dir name of current scene
        self.headobj[Config.fb_dir_prop_name[0]] = bpy.path.abspath("//")

    def save_cam_settings(self):
        render = bpy.context.scene.render
        d = {
                Config.reconstruct_sensor_width_param[0]: self.sensor_width,
                Config.reconstruct_sensor_height_param[0]: self.sensor_height,
                Config.reconstruct_focal_param[0]: self.focal,
                Config.reconstruct_frame_width_param[0]: render.resolution_x,
                Config.reconstruct_frame_height_param[0]: render.resolution_y}
        self.headobj[Config.fb_camera_prop_name[0]] = d


class FBSceneSettings(PropertyGroup):
    # ---------------------
    # Main settings
    # ---------------------
    heads: CollectionProperty(type=FBHeadItem, name="Heads")
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
        description="From 0.0 to 1.0",
        name="Wireframe opacity",
        default=0.35, min=0.0, max=1.0,
        update=update_wireframe)
    wireframe_color: FloatVectorProperty(
        description="Color of mesh wireframe in pin-mode",
        name="Wireframe Color", subtype='COLOR',
        default=Config.default_scheme1, min=0.0, max=1.0,
        update=update_wireframe)
    wireframe_special_color: FloatVectorProperty(
        description="Color of special parts in pin-mode",
        name="Wireframe Special Color", subtype='COLOR',
        default=Config.default_scheme2, min=0.0, max=1.0,
        update=update_wireframe)
    show_specials: BoolProperty(
        description="Use different colors for important head parts "
                    "on the mesh",
        name="Special face parts", default=True, update=update_wireframe)
    overall_opacity: FloatProperty(
        description="Overall opacity in pin-mode.",
        name="Overall opacity",
        default=1.00, min=0.0, max=1.0)

    # Initial pin_size state in FBShaderPoints class
    pin_size: FloatProperty(
        description="Set pin size in pixels",
        name="Pin size",
        default=Config.default_pin_size, min=1.0, max=100.0,
        update=update_pin_size)
    pin_sensitivity: FloatProperty(
        description="Set pin handle radius in pixels",
        name="Pin handle radius",
        default=Config.default_POINT_SENSITIVITY, min=1.0, max=100.0,
        update=update_pin_sensitivity)

    # Other settings
    rigidity: FloatProperty(
        description="Change how much pins affect the model shape",
        name="Rigidity", default=1.0, min=0.001, max=1000.0)
    check_auto_rigidity: BoolProperty(
        description="Automatic Rigidity calculation",
        name="Auto rigidity", default=True)

    # Internal use only
    current_headnum: IntProperty(name="Current Head Number", default=-1)
    current_camnum: IntProperty(name="Current Camera Number", default=-1)

    tmp_headnum: IntProperty(name="Temporary Head Number", default=-1)
    tmp_camnum: IntProperty(name="Temporary Camera Number", default=-1)

    # -------------------------
    # Texture Baking parameters
    # -------------------------
    tex_width: IntProperty(
        description="Width size of output texture",
        name="Width", default=2048)
    tex_height: IntProperty(
        description="Height size of output texture",
        name="Height", default=2048)

    tex_face_angles_affection: FloatProperty(
        description="Choose how much a polygon view angle affects "
                    "a pixel color: with 0 you will get an average "
                    "color from all views; with 100 you'll get color "
                    "information only from the polygons at which a camera "
                    "is looking at 90 degrees",
        name="Angle strictness", default=10.0, min=0.0, max=100.0)
    tex_uv_expand_percents: FloatProperty(
        description="Expand texture edges",
        name="Expand edges (%)", default=0.0)
    tex_back_face_culling: BoolProperty(
        description="Exclude backfacing polygons from the created texture",
        name="Back face culling", default=True)
    tex_equalize_brightness: BoolProperty(
        description="Experimental. Automatically equalize "
                    "brightness across images",
        name="Equalize brightness", default=False)
    tex_equalize_colour: BoolProperty(
        description="Experimental. Automatically equalize "
                    "colors across images",
        name="Equalize color", default=False)

    tex_auto_preview: BoolProperty(
        description="Automatically apply the created texture",
        name="Automatically apply the created texture", default=True)

    # Workaround to get blue button for selected camera
    blue_camera_button: BoolProperty(
        description="Current camera",
        name="Blue camera button", default=True,
        update=update_blue_camera_button)

    blue_head_button: BoolProperty(
        description="Current head",
        name="Blue head button", default=True,
        update=update_blue_head_button)

    def get_head(self, headnum):
        if headnum < 0 and len(self.heads) + headnum >= 0:
            return self.heads[len(self.heads) + headnum]
        if 0 <= headnum <= len(self.heads):
            return self.heads[headnum]
        else:
            return None

    def get_camera(self, headnum, camnum):
        head = self.get_head(headnum)
        if head is None:
            return None
        return head.get_camera(camnum)

    def get_keyframe(self, headnum, camnum):
        head = self.get_head(headnum)
        if head is None:
            return -1
        camera = head.get_camera(camnum)
        if camera is None:
            return -1
        return camera.get_keyframe()

    def head_has_pins(self, headnum):
        head = self.get_head(headnum)
        if head is None:
            return False
        return head.has_pins()

    def head_has_cameras(self, headnum):
        head = self.get_head(headnum)
        if head is None:
            return False
        return head.has_cameras()

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
                    except Exception:
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

    def get_last_headnum(self):
        return len(self.heads) - 1

    def get_last_camnum(self, headnum):
        head = self.get_head(headnum)
        if head is None:
            return -1
        return head.get_last_camnum()
