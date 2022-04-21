# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2022 KeenTools

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
from typing import Optional
import bpy
from bpy.types import Object, CameraBackgroundImage

from ..geotracker_config import GTConfig, get_gt_settings
from .gtloader import GTLoader
from ..utils.images import (np_array_from_bpy_image,
                            get_background_image_object,
                            gamma_np_image)


def is_mesh(self, obj: Optional[Object]) -> bool:
    return obj and obj.type == 'MESH'


def is_camera(self, obj: Optional[Object]) -> bool:
    return obj and obj.type == 'CAMERA'


def update_selection(self, context) -> None:
    pass


def update_wireframe_func(self, context) -> None:
    pass


def _update_preview_gamma(self, context) -> None:
    logger = logging.getLogger(__name__)
    logger.debug('Image Adj Gamma: ', self.preview_gamma)
    settings = get_gt_settings()
    if not settings.pinmode:
        return
    geotracker = settings.get_current_geotracker_item()
    bg_img = get_background_image_object(geotracker.camobj)
    bg_img.image.reload()
    np_img = np_array_from_bpy_image(bg_img.image)
    gamma_img = gamma_np_image(np_img, 1.0 / self.preview_gamma)
    bg_img.image.pixels.foreach_set(gamma_img.ravel())


class FileListItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name='File name')


class GeoTrackerItem(bpy.types.PropertyGroup):
    serial_str: bpy.props.StringProperty(name='GeoTracker Serialization string')
    geomobj: bpy.props.PointerProperty(name='Geom object',
                                       type=bpy.types.Object,
                                       poll=is_mesh, update=update_selection)
    camobj: bpy.props.PointerProperty(name='Camera object',
                                      type=bpy.types.Object,
                                      poll=is_camera, update=update_selection)
    movie_clip: bpy.props.PointerProperty(name='Movie Clip',
                                          type=bpy.types.MovieClip,
                                          update=update_selection)

    dir_name: bpy.props.StringProperty(name='Dir name')
    frames: bpy.props.CollectionProperty(type=FileListItem, name='Frame list')

    precalc_path: bpy.props.StringProperty(name='Precalc path')
    precalc_start: bpy.props.IntProperty(name='from', default=1)
    precalc_end: bpy.props.IntProperty(name='to', default=250)

    solve_for_camera: bpy.props.BoolProperty(name='Solve for camera', default=False)
    reduce_pins: bpy.props.BoolProperty(name='Reduce pins', default=False)
    spring_pins_back: bpy.props.BoolProperty(name='Spring pins back', default=True)

    focal_length_estimation: bpy.props.BoolProperty(name='Estimate focal length', default=False)
    track_focal_length: bpy.props.BoolProperty(name='Track focal length', default=False)

    preview_gamma: bpy.props.FloatProperty(name='Gamma', default=1.0, min=0.1, max=3.0,
                                           update=_update_preview_gamma)

    def get_serial_str(self) -> str:
        return self.serial_str

    def save_serial_str(self, serial: str) -> None:
        self.serial_str = serial

    def store_serial_str_on_geomobj(self) -> None:
        if self.geomobj:
            self.geomobj[GTConfig.serial_prop_name] = self.get_serial_str()

    def solve_for_camera_mode(self) -> None:
        return self.solve_for_camera

    def animatable_object(self) -> Optional[Object]:
        if self.solve_for_camera_mode():
            return self.camobj
        return self.geomobj

    def set_frames(self, arr: list) -> None:
        self.frames.clear()
        for filename in arr:
            item = self.frames.add()
            item.name = filename

    def sequence_frame(self, request_frame: int) -> Optional[str]:
        logger = logging.getLogger(__name__)
        frame = request_frame - self.precalc_start
        logger.debug('sequence_frame:', request_frame, frame)
        if 0 <= frame < len(self.frames):
            logger.debug('sequence_frame:', self.frames[frame].name)
            return self.frames[frame].name
        return None

    def get_background_image_object(self) -> Optional[CameraBackgroundImage]:
        return get_background_image_object(self.camobj)

    def reload_background_image(self) -> None:
        bg_img = self.get_background_image_object()
        if bg_img is not None:
            bg_img.image.reload()

    def reset_focal_length_estimation(self) -> None:
        self.focal_length_estimation = False


class GTSceneSettings(bpy.types.PropertyGroup):
    pinmode: bpy.props.BoolProperty(name='Pinmode status', default=False)
    pin_move_mode: bpy.props.BoolProperty(name='Pin move mode status', default=False)
    pinmode_id: bpy.props.StringProperty(name='Unique pinmode ID')

    geotrackers: bpy.props.CollectionProperty(type=GeoTrackerItem, name='GeoTrackers')
    current_geotracker_num: bpy.props.IntProperty(name='Current Geotracker Number', default=-1)

    wireframe_opacity: bpy.props.FloatProperty(
        description='From 0.0 to 1.0',
        name='Wireframe opacity',
        default=GTConfig.wireframe_opacity, min=0.0, max=1.0,
        update=update_wireframe_func)

    wireframe_color: bpy.props.FloatVectorProperty(
        description='Color of mesh wireframe in pin-mode',
        name='Wireframe Color', subtype='COLOR',
        default=GTConfig.wireframe_color, min=0.0, max=1.0,
        update=update_wireframe_func)

    anim_start: bpy.props.IntProperty(name='from', default=1)
    anim_end: bpy.props.IntProperty(name='to', default=250)

    user_interrupts: bpy.props.BoolProperty(name='Interrupted by user',
                                            default = False)
    user_percent: bpy.props.FloatProperty(name='Percentage',
                                          subtype='PERCENTAGE',
                                          default=0.0, min=0.0, max=100.0,
                                          precision=1)
    precalc_mode: bpy.props.BoolProperty(name='Precalc mode status',
                                         default = False)

    selection_mode: bpy.props.BoolProperty(name='Selection mode',
                                           default=False)
    selection_x: bpy.props.FloatProperty(name='Selection X',
                                         default=0.0)
    selection_y: bpy.props.FloatProperty(name='Selection Y',
                                         default=0.0)

    def reset_pinmode_id(self) -> None:
        self.pinmode_id = 'stop'

    def wrong_pinmode_id(self) -> bool:
        return self.pinmode_id in {'', 'stop'}

    def current_frame(self) -> int:
        return bpy.context.scene.frame_current

    def end_frame(self) -> int:
        return bpy.context.scene.frame_end

    def start_frame(self) -> int:
        return bpy.context.scene.frame_start

    def set_current_frame(self, frame: int) -> None:
        bpy.context.scene.frame_set(frame)

    def get_last_geotracker_num(self) -> int:
        return len(self.geotrackers) - 1

    def is_proper_geotracker_number(self, num: int) -> bool:
        return 0 <= num < len(self.geotrackers)

    def get_current_geotracker_item(self) -> Optional[GeoTrackerItem]:
        if self.is_proper_geotracker_number(self.current_geotracker_num):
            return self.geotrackers[self.current_geotracker_num]
        else:
            self.current_geotracker_num = -1
        return None

    def change_current_geotracker(self, num: int) -> bool:
        if self.is_proper_geotracker_number(num):
            self.current_geotracker_num = num
            if not GTLoader.load_geotracker():
                GTLoader.new_kt_geotracker()
            return True
        return False

    def reload_current_geotracker(self) -> bool:
        return self.change_currrent_geotracker(self.current_geotracker_num)

    def add_geotracker_item(self) -> int:
        self.geotrackers.add()
        return self.get_last_geotracker_num()

    def remove_geotracker_item(self, num: int) -> int:
        if self.is_proper_geotracker_number(num):
            self.geotrackers.remove(num)
            if self.current_geotracker_num >= num:
                self.current_geotracker_num -= 1
                if self.current_geotracker_num < 0:
                    if self.is_proper_geotracker_number(0):
                        self.current_geotracker_num = 0
                    else:
                        self.current_geotracker_num = -1
        return self.current_geotracker_num

    def get_frame_image_path(self, frame: int) -> Optional[str]:
        geotracker = self.get_current_geotracker_item()
        if not geotracker:
            return None
        return geotracker.sequence_frame(frame)

    def start_selection(self, mouse_x: int, mouse_y: int) -> None:
        self.selection_x = mouse_x
        self.selection_y = mouse_y
        self.selection_mode = True
        self.do_selection(mouse_x, mouse_y)

    def do_selection(self, mouse_x: int=0, mouse_y: int=0):
        logger = logging.getLogger(__name__)
        logger.debug('DO SELECTION: {}'.format(self.selection_mode))
        vp = GTLoader.viewport()
        selector = vp.selector()
        if not self.selection_mode:
            selector.clear_rectangle()
            selector.create_batch()
            return
        selector.add_rectangle(self.selection_x, self.selection_y,
                               mouse_x, mouse_y)
        selector.create_batch()

    def end_selection(self) -> None:
        self.selection_mode = False
        self.do_selection()
