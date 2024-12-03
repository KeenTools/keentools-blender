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

from typing import Any, Optional, List, Tuple
import math
from contextlib import contextmanager

import numpy as np
from bpy.props import (
    BoolProperty,
    IntProperty,
    FloatProperty,
    StringProperty,
    FloatVectorProperty,
    PointerProperty,
    CollectionProperty,
    EnumProperty,
    BoolVectorProperty
)
from bpy.types import PropertyGroup, Object, Area, Image

from ..utils.kt_logging import KTLogger
from ..addon_config import (Config,
                            fb_settings,
                            get_addon_preferences,
                            ProductType)
from ..facebuilder_config import FBConfig
from .fbloader import FBLoader
from ..utils.coords import (get_camera_border,
                            projection_matrix,
                            get_image_space_coord)
from .callbacks import (update_mesh_with_dialog,
                        update_mesh_simple,
                        update_shape_rigidity,
                        update_expression_rigidity,
                        update_blinking_rigidity,
                        update_neck_movement_rigidity,
                        update_use_emotions,
                        update_lock_blinking,
                        update_lock_neck_movement,
                        update_expression_view,
                        update_wireframe_image,
                        update_wireframe_func,
                        update_pin_sensitivity,
                        update_pin_size,
                        update_model_scale,
                        update_cam_image,
                        update_head_focal,
                        update_camera_focal,
                        update_background_tone_mapping)
from .utils.manipulate import get_current_head
from ..utils.images import tone_mapping, reset_tone_mapping
from ..utils.viewport_state import ViewportStateItem
from ..utils.bpy_common import (bpy_render_frame,
                                bpy_scene,
                                bpy_remove_object,
                                bpy_abspath,
                                get_scene_camera_shift)

_log = KTLogger(__name__)


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

    orientation: IntProperty(default=0)

    # from EXIF tag ExifImageWidth, ExifImageLength
    exif_width: FloatProperty(default=-1.0)
    exif_length: FloatProperty(default=-1.0)

    # from image file
    real_width: FloatProperty(default=-1.0)
    real_length: FloatProperty(default=-1.0)

    def __str__(self):
        res = 'focal: {} \n'.format(self.focal)
        res += 'focal35mm: {} \n'.format(self.focal35mm)
        res += 'focal_x_res: {} \n'.format(self.focal_x_res)
        res += 'focal_y_res: {} \n'.format(self.focal_y_res)
        res += 'units: {} \n'.format(self.units)
        res += 'sensor_width: {} \n'.format(self.sensor_width)
        res += 'sensor_length: {} \n'.format(self.sensor_length)
        res += 'image_width: {} \n'.format(self.image_width)
        res += 'image_length: {} \n'.format(self.image_length)
        res += 'orientation: {} \n'.format(self.orientation)
        res += 'exif_width: {} \n'.format(self.exif_width)
        res += 'real_width: {} \n'.format(self.real_width)
        res += 'real_length: {} \n'.format(self.real_length)
        res += 'info_message: {} \n'.format(self.info_message)
        res += 'sizes_message: {} \n'.format(self.sizes_message)
        return res

    def calculated_image_size(self) -> Tuple[float, float]:
        if self.image_width > 0.0 and self.image_length > 0.0:
            w = self.image_width
            h = self.image_length
        else:
            w = self.exif_width
            h = self.exif_length
        return w, h


class FBCameraItem(PropertyGroup):
    keyframe_id: IntProperty(default=-1)
    cam_image: PointerProperty(
        name='Image', type=Image, update=update_cam_image
    )
    cam_image_frame: IntProperty(default=-1)
    image_width: IntProperty(default=-1)
    image_height: IntProperty(default=-1)

    camobj: PointerProperty(
        name='Camera', type=Object
    )
    pins_count: IntProperty(
        name='Pins in Camera', default=0)

    use_in_tex_baking: BoolProperty(name='Use In Texture Baking', default=True)

    exif: PointerProperty(type=FBExifItem)

    orientation: IntProperty(default=0)  # angle = orientation * Pi/2

    focal: FloatProperty(
        description="35mm equivalent focal length",
        name="Focal Length", default=50,
        unit="CAMERA",
        min=0.1, update=update_camera_focal)

    background_scale: FloatProperty(
        description="CAMERA background image scale",
        name="Cam BGScale", default=1.0,
        min=0.0001)

    auto_focal_estimation: BoolProperty(
        name='Estimate focal length',
        description='Automatically estimate focal length '
                    'while aligning mesh to image. '
                    'Activates from 4th pin and on',
        default=True)

    tone_exposure: FloatProperty(
        name='Exposure', description='Adjust exposure in current view',
        default=Config.default_tone_exposure,
        min=-10.0, max=10.0, soft_min=-4.0, soft_max=4.0, precision=2,
        update=update_background_tone_mapping)

    tone_gamma: FloatProperty(
        name='Gamma', description='Adjust gamma in current view',
        default=Config.default_tone_gamma, min=0.01, max=10.0, soft_max=4.0, precision=2,
        update=update_background_tone_mapping)

    def update_scene_frame_size(self) -> None:
        if self.image_width > 0 and self.image_height > 0:
            render = bpy_scene().render
            if (self.orientation % 2) == 0:
                render.resolution_x = self.image_width
                render.resolution_y = self.image_height
            else:
                render.resolution_x = self.image_height
                render.resolution_y = self.image_width

    def get_camera_background(self) -> Optional[Image]:
        c = self.camobj.data
        if len(c.background_images) == 0:
            return None
        else:
            return c.background_images[0]

    def get_background_size(self) -> Tuple[int, int]:
        img = self.get_camera_background()
        if img is not None:
            if img.image:
                return img.image.size
        return -1, -1

    def reset_background_image_rotation(self) -> None:
        background_image = self.get_camera_background()
        if background_image is None:
            return
        background_image.rotation = 0
        self.orientation = 0

    def rotate_background_image(self, delta: int = 1) -> None:
        background_image = self.get_camera_background()
        if background_image is None:
            return

        self.orientation += delta
        if self.orientation < 0:
            self.orientation += 4
        if self.orientation >= 4:
            self.orientation += -4
        background_image.rotation = self.orientation * math.pi / 2

    def show_background_image(self) -> None:
        data = self.camobj.data
        data.show_background_images = True
        if len(data.background_images) == 0:
            bim = data.background_images.new()
        else:
            bim = data.background_images[0]
        bim.image = self.cam_image
        bim.rotation = self.orientation * math.pi / 2

        if self.cam_image_frame >= 0:
            bim.image_user.frame_duration = 1
            bim.image_user.use_cyclic = True
            bim.image_user.frame_offset = self.cam_image_frame - 1

    def calculate_background_scale(self) -> float:
        if self.image_width <= 0 or self.image_height <= 0:
            return 1.0
        if (self.orientation % 2) == 0:
            return 1.0
        else:
            if self.image_width >= self.image_height:
                return self.image_height / self.image_width
            else:
                return self.image_width / self.image_height

    def update_background_image_scale(self) -> bool:
        self.background_scale = self.calculate_background_scale()
        background = self.get_camera_background()
        if background is None:
            return False
        background.scale = self.background_scale
        return True

    def compensate_view_scale(self) -> float:
        if self.image_width <= 0 or self.image_height <= 0:
            return 1.0

        if (self.orientation % 2) == 0:
            if self.image_width >= self.image_height:
                return 1.0
            else:
                return self.image_width / self.image_height

        if self.image_width >= self.image_height:
            return self.image_height / self.image_width
        else:
            return 1.0

    # Simple getters/setters
    def get_image_width(self) -> int:
        return self.image_width

    def set_image_width(self, w: int) -> None:
        self.image_width = w

    def get_image_height(self) -> int:
        return self.image_height

    def set_image_height(self, h: int) -> None:
        self.image_height = h

    # Real getter from image size
    def get_image_size(self) -> Tuple[int, int]:
        w = -1
        h = -1
        if self.cam_image:
            w, h = self.cam_image.size
            self.image_width = w
            self.image_height = h
        return w, h

    def get_oriented_image_size(self) -> Tuple[int, int]:
        if (self.orientation % 2) == 0:
            return (self.get_image_width(), self.get_image_height())
        return (self.get_image_height(), self.get_image_width())

    def update_image_size(self) -> None:
        w, h = self.get_image_size()
        self.set_image_width(w)
        self.set_image_height(h)

    def is_deleted(self) -> bool:
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

    def delete_cam_background_images(self) -> None:
        if self.camobj is None:
            return
        for im in reversed(self.camobj.data.background_images):
            self.camobj.data.background_images.remove(im)
        self.camobj.data.show_background_images = False

    def delete_cam_image(self) -> None:
        self.cam_image = None
        self.delete_cam_background_images()

    def delete_camobj(self) -> None:
        bpy_remove_object(self.camobj)

    def get_keyframe(self) -> int:
        return self.keyframe_id

    def set_keyframe(self, num: int) -> None:
        self.keyframe_id = num

    def has_pins(self) -> bool:
        return self.pins_count > 0

    def get_abspath(self) -> Optional[str]:
        if self.cam_image is not None:
            return bpy_abspath(self.cam_image.filepath)
        else:
            return None

    def get_image_name(self) -> str:
        if self.cam_image is not None:
            return self.cam_image.name
        else:
            return 'N/A'

    def reset_camera_sensor(self) -> None:
        if self.camobj:
            self.camobj.data.sensor_width = FBConfig.default_sensor_width
            self.camobj.data.sensor_height = FBConfig.default_sensor_height

    def get_custom_projection_matrix(self, focal: float) -> Any:
        w = self.image_width
        h = self.image_height

        near = 0.1
        far = 1000.0

        sc = 1.0 / self.compensate_view_scale()

        if (self.orientation % 2) == 0:
            if w >= h:
                projection = projection_matrix(
                    w, h, focal, FBConfig.default_sensor_width,
                    near, far, scale=1.0)
            else:
                projection = projection_matrix(
                    w, h, focal, FBConfig.default_sensor_width,
                    near, far, scale=sc)
        else:
            projection = projection_matrix(
                h, w, focal, FBConfig.default_sensor_width,
                near, far, scale=sc)

        return projection

    def get_projection_matrix(self) -> Any:
        return self.get_custom_projection_matrix(self.focal)

    def get_headnum_camnum(self) -> Tuple[int, int]:
        settings = fb_settings()
        for i, head in enumerate(settings.heads):
            for j, camera in enumerate(head.cameras):
                if camera == self:
                    return i, j
        return -1, -1

    def get_focal_length_in_pixels_coef(self) -> float:
        w, _ = self.get_oriented_image_size()
        sc = 1.0 / self.compensate_view_scale()
        return sc * w / FBConfig.default_sensor_width

    def reset_tone_mapping(self) -> None:
        reset_tone_mapping(self.cam_image)

    def apply_tone_mapping(self) -> None:
        if not self.cam_image:
            return
        tone_mapping(self.cam_image,
                     exposure=self.tone_exposure, gamma=self.tone_gamma)


def uv_items_callback(self, context) -> List[Tuple]:
    fb = FBLoader.get_builder()
    res: List[Tuple] = []
    for i, name in enumerate(fb.uv_sets_list()):
        res.append(('uv{}'.format(i), name, '', 'UV', i))
    return res


def _get_icon_by_lod(level_of_detail: str) -> str:
    icons = {'HIGH_POLY': 'SHADING_WIRE',
             'MID_POLY': 'MESH_UVSPHERE',
             'LOW_POLY': 'META_BALL'}
    if level_of_detail in icons.keys():
        return icons[level_of_detail]
    return 'BLANK1'


def model_type_callback(self, context) -> List[Tuple]:
    res = [(x.name, x.name, '', _get_icon_by_lod(x.level_of_detail), i)
           for i, x in enumerate(FBLoader.get_builder().models_list())]
    if len(res) == 0 or (len(res) == 1 and res[0][0] == ''):
        return [('', 'old topology', '', _get_icon_by_lod('HIGH_POLY'), 0)]
    return res


def expression_views_callback(self, context) -> List[Tuple]:
    res = [(FBConfig.neutral_expression_view_name, 'Neutral', '', 'USER', 0), ]
    for i, camera in enumerate(self.cameras):
        kid = camera.get_keyframe()
        res.append(('{}'.format(kid), camera.get_image_name(),
                    '', 'PINNED' if camera.has_pins() else 'HIDE_OFF', kid))
    return res


class FBHeadItem(PropertyGroup):
    use_emotions: BoolProperty(name='Allow facial expressions',
                               default=False, update=update_use_emotions)
    lock_blinking: BoolProperty(name='Lock eyelids',
                                default=False, update=update_lock_blinking)
    lock_neck_movement: BoolProperty(name='Lock neck',
                                     default=False,
                                     update=update_lock_neck_movement)
    headobj: PointerProperty(name='Head', type=Object)

    blendshapes_control_panel: PointerProperty(name='Blendshapes Control Panel',
                                               type=Object)
    cameras: CollectionProperty(name='Cameras', type=FBCameraItem)

    sensor_width: FloatProperty(
        description="The length of the longest side "
                    "of the camera sensor in millimetres",
        name="Sensor Width (mm)", default=-1)
    sensor_height: FloatProperty(
        description="Secondary parameter. "
                    "Set it according to the real camera specification."
                    "This parameter is not used if Sensor Width is greater",
        name="Sensor Height (mm)", default=-1)
    focal: FloatProperty(
        description="Focal length in millimetres",
        name="Focal Length (mm)", default=50,
        min=0.01, update=update_head_focal)

    auto_focal_estimation: BoolProperty(
        name="Estimate focal length",
        description="When turned on, FaceBuilder will try to estimate "
                    "focal length based on the position of the model "
                    "in the frame",
        default=False)

    masks: BoolVectorProperty(name='Masks',
                              description='Turn model parts on and off',
                              size=12, subtype='NONE',
                              default=(True,) * 12,
                              update=update_mesh_simple)

    serial_str: StringProperty(name="Serialization string", default="")
    need_update: BoolProperty(name="Mesh need update", default=False)

    tex_uv_shape: EnumProperty(name="UV", items=uv_items_callback,
                               description="UV Layout",
                               update=update_mesh_simple)

    exif: PointerProperty(type=FBExifItem)

    model_scale: FloatProperty(
        description="Adjust absolute size of 3D head",
        name="Scale", default=1.0, min=0.01, max=100.0,
        update=update_model_scale)

    model_changed_by_scale: BoolProperty(default=False)

    model_type: EnumProperty(name='Topology', items=model_type_callback,
                             description='Selected topology',
                             update=update_mesh_with_dialog)

    model_type_previous: EnumProperty(name='Current Topology',
                                      items=model_type_callback,
                                      description='Invisible Model selector')

    expression_view: EnumProperty(name='Expression View Selector',
                                  items=expression_views_callback,
                                  description='Use expression from',
                                  update=update_expression_view)

    def blenshapes_are_relevant(self) -> bool:
        if self.has_no_blendshapes():
            return True
        return not self.model_changed_by_scale

    def clear_model_changed_status(self) -> None:
        self.model_changed_by_scale = False

    def mark_model_changed_by_scale(self) -> None:
        if not self.has_no_blendshapes():
            self.model_changed_by_scale = True

    def model_type_changed(self) -> bool:
        return self.model_type != self.model_type_previous

    def model_changed(self) -> bool:
        return self.model_type_changed()

    def discard_model_changes(self) -> None:
        if self.model_type_changed():
            self.model_type = self.model_type_previous

    def apply_model_changes(self) -> None:
        self.model_type_previous = self.model_type

    def has_no_blendshapes(self) -> bool:
        return not self.headobj or not self.headobj.data or \
               not self.headobj.data.shape_keys

    def has_blendshape_action(self) -> bool:
        if self.headobj and self.headobj.data.shape_keys \
               and self.headobj.data.shape_keys.animation_data \
               and self.headobj.data.shape_keys.animation_data.action:
            return True
        return False

    def get_camera(self, camnum: int) -> Optional[Any]:
        if camnum < 0 and len(self.cameras) + camnum >= 0:
            return self.cameras[len(self.cameras) + camnum]
        if 0 <= camnum < len(self.cameras):
            return self.cameras[camnum]
        else:
            return None

    def get_camera_by_keyframe(self, keyframe: int) -> Optional[Any]:
        for camera in self.cameras:
            if camera.get_keyframe() == keyframe:
                return camera
        return None

    def get_last_camera(self) -> Optional[Any]:
        return self.get_camera(self.get_last_camnum())

    def store_serial_str_on_headobj(self) -> None:
        if self.headobj:
            self.headobj[FBConfig.fb_serial_prop_name] = self.serial_str

    def set_serial_str(self, value: str) -> None:
        self.serial_str = value

    def get_serial_str(self) -> str:
        return self.serial_str

    def store_serial_str_in_head_and_on_headobj(self, value: str) -> None:
        self.set_serial_str(value)
        self.store_serial_str_on_headobj()

    def is_deleted(self) -> bool:
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

    def control_panel_exists(self) -> bool:
        if self.blendshapes_control_panel is None:
            return False
        try:
            if not hasattr(self.blendshapes_control_panel, 'users_scene') or \
                    len(self.blendshapes_control_panel.users_scene) == 0:
                return False
            return True
        except AttributeError:
            return False

    def get_last_camnum(self) -> int:
        return len(self.cameras) - 1

    def get_keyframe(self, camnum: int) -> int:
        camera = self.get_camera(camnum)
        if camera is not None:
            return camera.get_keyframe()
        else:
            return -1

    def has_camera(self, camnum: int) -> bool:
        return 0 <= camnum < len(self.cameras)

    def has_cameras(self) -> bool:
        return len(self.cameras) > 0

    def has_pins(self) -> bool:
        for c in self.cameras:
            if c.has_pins():
                return True
        return False

    def save_images_src_on_headobj(self) -> None:
        res: List[str] = []
        for c in self.cameras:
            if c.cam_image:
                res.append(c.cam_image.filepath)
            else:
                res.append('')
        if not self.headobj:
            return
        self.headobj[FBConfig.fb_images_prop_name] = res
        # Dir name of current scene
        self.headobj[FBConfig.fb_dir_prop_name] = bpy_abspath("//")

    def should_use_emotions(self) -> bool:
        return self.use_emotions

    def get_masks(self) -> List[bool]:
        fb = FBLoader.get_builder()
        return self.masks[:len(fb.masks())]

    def reset_sensor_size(self) -> None:
        self.sensor_width = 0
        self.sensor_height = 0

    def get_headnum(self) -> int:
        settings = fb_settings()
        for i, head in enumerate(settings.heads):
            if head == self:
                return i
        return -1

    def get_expression_view_keyframe(self) -> int:
        if self.expression_view == FBConfig.empty_expression_view_name:
            return 0  # Neutral
        kid = int(self.expression_view)
        return kid

    def set_neutral_expression_view(self) -> None:
        self.expression_view = FBConfig.neutral_expression_view_name

    def has_vertex_groups(self) -> bool:
        return len(self.headobj.vertex_groups) != 0

    def get_headobj_name(self) -> str:
        if self.headobj:
            return self.headobj.name
        return 'none'

    def preview_material_name(self) -> str:
        return FBConfig.tex_builder_matname_template.format(self.get_headobj_name())

    def preview_texture_name(self) -> str:
        return FBConfig.tex_builder_filename_template.format(self.get_headobj_name())


class FBSceneSettings(PropertyGroup):
    def product_type(self) -> int:
        return ProductType.FACEBUILDER

    def loader(self) -> Any:
        return FBLoader

    heads: CollectionProperty(type=FBHeadItem, name="Heads")
    frame_width: IntProperty(default=-1)
    frame_height: IntProperty(default=-1)

    opnum: IntProperty(name="Operation Number", default=0)
    pinmode: BoolProperty(name="Pin Mode", default=False)
    pinmode_id: StringProperty(name="Unique pinmode ID")
    force_out_pinmode: BoolProperty(name="Pin Mode Out", default=False)
    license_error: BoolProperty(name="License Error", default=False)

    ui_write_mode: BoolProperty(name='UI Write mode', default=False)
    viewport_state: PointerProperty(type=ViewportStateItem)

    adaptive_opacity: FloatProperty(
        description='From 0.0 to 1.0',
        name='FaceBuilder Adaptive Opacity',
        default=1.0,
        min=0.0, max=1.0)

    use_adaptive_opacity: BoolProperty(
        name='Use adaptive opacity',
        default=True,
        update=update_wireframe_func)

    def get_adaptive_opacity(self) -> float:
        return self.adaptive_opacity if self.use_adaptive_opacity else 1.0

    def calc_adaptive_opacity(self, area: Area) -> None:
        _log.yellow('fb calc_adaptive_opacity')
        if not area:
            _log.red('fb calc_adaptive_opacity wrong area >>>')
            return
        aw = area.width
        rx, ry = bpy_render_frame()
        denom = aw if 1 <= aw < rx else rx
        x1, y1, x2, y2 = get_camera_border(area)
        self.adaptive_opacity = (x2 - x1) / denom
        _log.output(f'fb calc_adaptive_opacity: {self.adaptive_opacity} >>>')

    wireframe_opacity: FloatProperty(
        description='',
        name='Wireframe opacity',
        default=Config.fb_wireframe_opacity,
        min=0.0, max=1.0,
        update=update_wireframe_func)
    wireframe_color: FloatVectorProperty(
        description='',
        name='Base mesh colour', subtype='COLOR',
        default=Config.fb_color_schemes['default'][0],
        min=0.0, max=1.0,
        update=update_wireframe_image)
    wireframe_special_color: FloatVectorProperty(
        description='',
        name='Facial features colour', subtype='COLOR',
        default=Config.fb_color_schemes['default'][1],
        min=0.0, max=1.0,
        update=update_wireframe_image)
    wireframe_midline_color: FloatVectorProperty(
        description='',
        name='Midlines colour', subtype='COLOR',
        default=Config.fb_midline_color,
        min=0.0, max=1.0,
        update=update_wireframe_image)
    show_specials: BoolProperty(
        description='',
        name='Highlight facial features', default=True, update=update_wireframe_image)
    wireframe_backface_culling: BoolProperty(
        name='Backface culling',
        default=True,
        update=update_wireframe_func)
    pin_size: FloatProperty(
        description='Set pin size in pixels',
        name='Size',
        default=Config.pin_size,
        min=1.0, max=100.0,
        precision=1,
        update=update_pin_size)
    pin_sensitivity: FloatProperty(
        name='Sensitivity', description='Active area in pixels',
        default=Config.pin_sensitivity,
        min=1.0, max=100.0,
        precision=1,
        update=update_pin_sensitivity
    )

    # Other settings
    shape_rigidity: FloatProperty(
        description='Adjust overall mesh rigidity: '
                    '0 - most flexible, 10 - most rigid, default = 1',
        name='Shape', default=1.0, min=0.001, max=1000.0,
        update=update_shape_rigidity)
    expression_rigidity: FloatProperty(
        description='Change how much pins affect the model expressions. '
                    'Accessible in Pinmode only',
        name='Expressions', default=2.0, min=0.001, max=1000.0,
        update=update_expression_rigidity)
    blinking_rigidity: FloatProperty(
        description='Change how much pins affect blinking. '
                    'Accessible in Pinmode only',
        name='Eyelids', default=2.0, min=0.001, max=1000.0,
        update=update_blinking_rigidity)
    neck_movement_rigidity: FloatProperty(
        description='Change how much pins affect neck movement. '
                    'Accessible in Pinmode only',
        name='Neck', default=2.0, min=0.001, max=1000.0,
        update=update_neck_movement_rigidity)

    # Warning! current_headnum and current_camnum work only in Pinmode!
    current_headnum: IntProperty(name='Current Head Number', default=-1)
    current_camnum: IntProperty(name='Current Camera Number', default=-1)

    tmp_headnum: IntProperty(name='Temporary Head Number', default=-1)
    tmp_camnum: IntProperty(name='Temporary Camera Number', default=-1)

    calculating_mode: EnumProperty(name='Calculating mode', items=[
        ('NONE', 'NONE', 'No calculation mode', 0),
        ('TEXTURE_BAKING', 'TEXTURE_BAKING', 'Project and bake texture is calculating', 1),
    ])

    selection_mode: BoolProperty(name='Selection mode', default=False)
    selection_x: FloatProperty(name='Selection X', default=0.0)
    selection_y: FloatProperty(name='Selection Y', default=0.0)

    def start_selection(self, mouse_x: int, mouse_y: int) -> None:
        _log.green('start_selection start')
        self.selection_x = mouse_x
        self.selection_y = mouse_y
        self.selection_mode = True
        self.do_selection(mouse_x, mouse_y)
        _log.output('start_selection end >>>')

    def do_selection(self, mouse_x: int=0, mouse_y: int=0) -> None:
        _log.yellow(f'do_selection: selection_mode={self.selection_mode}')
        vp = self.loader().viewport()
        selector = vp.selector()
        if not self.selection_mode:
            selector.clear_rectangle()
            selector.create_batch()
            return
        selector.add_rectangle(self.selection_x, self.selection_y,
                               mouse_x, mouse_y)
        selector.create_batch()
        _log.output('do_selection end >>>')

    def cancel_selection(self) -> None:
        _log.yellow('cancel_selection start')
        self.selection_mode = False
        self.do_selection()
        _log.output('cancel_selection end >>>')

    def end_selection(self, area: Area, mouse_x: int, mouse_y: int) -> None:
        _log.green('end_selection start')
        shift_x, shift_y = get_scene_camera_shift()
        x1, y1 = get_image_space_coord(self.selection_x, self.selection_y, area,
                                       shift_x, shift_y)
        x2, y2 = get_image_space_coord(mouse_x, mouse_y, area, shift_x, shift_y)
        vp = self.loader().viewport()
        pins = vp.pins()
        found_pins = pins.pins_inside_rectangle(x1, y1, x2, y2)
        if pins.get_add_selection_mode():
            pins.toggle_selected_pins(found_pins)
        else:
            pins.set_selected_pins(found_pins)
        self.cancel_selection()
        _log.output('end_selection end >>>')

    tex_width: IntProperty(
        description="Width in pixels",
        name="Width", default=Config.default_tex_width)
    tex_height: IntProperty(
        description="Height in pixels",
        name="Height", default=Config.default_tex_height)

    tex_face_angles_affection: FloatProperty(
        description="Blending of colours between different cameras: "
                    "0 - average colour from all views, "
                    "100 - colour from 90 degree views only",
        name="Angle strictness",
        default=Config.default_tex_face_angles_affection, min=0.0, max=100.0)
    tex_uv_expand_percents: FloatProperty(
        description="Extrapolate texture to fill gaps",
        name="Expand edges (%)", default=Config.default_tex_uv_expand_percents)
    tex_back_face_culling: BoolProperty(
        description="Exclude backfacing polygons from the created texture",
        name="Back face culling", default=True)
    tex_equalize_brightness: BoolProperty(
        description="Equalize brightness",
        name="Equalize brightness", default=False)
    tex_equalize_colour: BoolProperty(
        description="Equalize color",
        name="Equalize color", default=False)
    tex_fill_gaps: BoolProperty(
        description="Automatically fill the gaps with nearby colour",
        name="Autofill", default=False)

    tex_auto_preview: BoolProperty(
        description="Make texture visible in viewport after baking",
        name="Automatically apply texture to 3D head", default=True)

    @contextmanager
    def ui_write_mode_context(self):
        self.ui_write_mode = True
        yield
        self.ui_write_mode = False

    def reset_pinmode_id(self) -> None:
        self.pinmode_id = 'stop'

    def wrong_pinmode_id(self) -> bool:
        return self.pinmode_id in {'', 'stop'}

    def start_calculating(self, mode: str) -> None:
        self.calculating_mode = mode

    def stop_calculating(self) -> None:
        self.calculating_mode = 'NONE'

    def is_calculating(self, mode: Optional[str] = None) -> bool:
        if mode is None:
            return self.calculating_mode != 'NONE'
        return self.calculating_mode == mode

    def get_head(self, headnum: int) -> Optional[Any]:
        if headnum < 0 and len(self.heads) + headnum >= 0:
            return self.heads[len(self.heads) + headnum]
        if 0 <= headnum < len(self.heads):
            return self.heads[headnum]
        else:
            return None

    def get_current_head(self) -> Optional[Any]:
        if self.pinmode:
            assert self.current_headnum >= 0
            head = self.get_head(self.current_headnum)
        else:
            head = get_current_head()
        return head

    def get_camera(self, headnum: int, camnum: int) -> Optional[Any]:
        head = self.get_head(headnum)
        if head is None:
            return None
        return head.get_camera(camnum)

    def get_keyframe(self, headnum: int, camnum: int) -> int:
        head = self.get_head(headnum)
        if head is None:
            return -1
        camera = head.get_camera(camnum)
        if camera is None:
            return -1
        return camera.get_keyframe()

    def head_has_pins(self, headnum: int) -> bool:
        head = self.get_head(headnum)
        if head is None:
            return False
        return head.has_pins()

    def head_has_cameras(self, headnum: int) -> bool:
        head = self.get_head(headnum)
        if head is None:
            return False
        return head.has_cameras()

    # Find Head by Blender object (Head Mesh)
    def find_head_index(self, obj: Object) -> int:
        """ Find head index by blender object """
        for i, h in enumerate(self.heads):
            if h.headobj is obj:
                return i  # Found Head index
        return -1  # head object not found

    # Find Camera by Blender object
    def find_cam_index(self, obj: Object) -> Tuple[int, int]:
        for i, h in enumerate(self.heads):
            for j, c in enumerate(h.cameras):
                if c.camobj is obj:
                    return i, j  # Head & Camera indices
        return -1, -1  # camera not found

    # Verify the existence of all this head cameras
    @staticmethod
    def check_head_cams(head: Any) -> bool:
        for i, c in enumerate(head.cameras):
            if c.is_deleted():
                return False  # Wrong camera in list
        return True  # All head cameras is ok

    # Verify the existence of all heads
    def check_heads(self) -> bool:
        for i, h in enumerate(self.heads):
            if h.is_deleted():
                return False  # Wrong head object in list
        return True  # All heads are ok

    # Full check heads and cameras existence
    def check_heads_and_cams(self) -> bool:
        for i, h in enumerate(self.heads):
            if h.is_deleted():
                return False  # Wrong head object in list'
            if not self.check_head_cams(h):
                return False  # Wrong camera
        return True  # All is ok

    # Remove non-existent cameras in list of this head
    @staticmethod
    def fix_head_cams(head: Any) -> bool:
        status = False  # no changes
        err: List[int] = []
        for i, c in enumerate(head.cameras):
            if c.is_deleted():
                status = True
                headnum = head.get_headnum()
                FBLoader.load_model(headnum)
                fb = FBLoader.get_builder()
                kid = c.get_keyframe()
                if fb.is_key_at(kid):
                    fb.remove_keyframe(kid)
                err.append(i)  # Wrong camera in list
        for i in reversed(err):  # Delete in backward order
            head.cameras.remove(i)
        if status:
            FBLoader.save_fb_serial_and_image_pathes(headnum)
        return status  # True if there were any changes

    def fix_heads(self) -> Tuple[int, int]:
        heads_deleted = 0  # no changes
        cams_deleted = 0  # no changes
        err: List[int] = []
        for i, h in enumerate(self.heads):
            if h.is_deleted():
                heads_deleted += 1  # some changes!
                # Head object is deleted by user
                for c in h.cameras:
                    try:
                        # Remove camera object
                        bpy_remove_object(c.camobj)
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

    def head_by_obj(self, obj: Object) -> int:
        i = self.find_head_index(obj)
        j, _ = self.find_cam_index(obj)
        return max(i, j)

    def get_last_headnum(self) -> int:
        return len(self.heads) - 1

    def get_last_camnum(self, headnum: int) -> int:
        head = self.get_head(headnum)
        if head is None:
            return -1
        return head.get_last_camnum()

    def is_proper_headnum(self, headnum: int) -> bool:
        return 0 <= headnum <= self.get_last_headnum()

    def get_next_head_position(self) -> Any:
        zero_position = (0., 0., 0)
        headnum = self.get_last_headnum()
        head = self.get_head(headnum)
        if head is None or not head.headobj:
            return zero_position
        return np.array(head.headobj.location) + FBConfig.next_head_step

    def get_all_camobj(self) -> List[Object]:
        return [cam.camobj for head in self.heads
                for cam in head.cameras if cam.camobj]

    def preferences(self) -> Any:
        return get_addon_preferences()
