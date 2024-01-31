# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2022-2023 KeenTools

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

import numpy as np
from typing import Optional, Tuple, Any, List
from contextlib import contextmanager

from bpy.types import (Object, CameraBackgroundImage, Area, Image, Mask,
                       PropertyGroup, MovieClip)
from bpy.props import IntProperty

from ..utils.kt_logging import KTLogger
from ..addon_config import Config, get_addon_preferences, ProductType
from ..geotracker_config import GTConfig
from ..utils.images import (get_background_image_object,
                            get_background_image_strict,
                            set_background_image_by_movieclip)
from ..geotracker.utils.tracking import reload_precalc
from ..utils.coords import (xz_to_xy_rotation_matrix_4x4,
                            get_scale_vec_4_from_matrix_world,
                            get_image_space_coord,
                            get_camera_border,
                            get_polygons_in_vertex_group,
                            LocRotScale)
from ..utils.bpy_common import (bpy_render_frame,
                                bpy_current_frame,
                                bpy_render_single_frame,
                                get_scene_camera_shift)
from ..utils.compositing import (get_compositing_shadow_scene,
                                 create_mask_compositing_node_tree,
                                 viewer_node_to_image,
                                 get_rendered_mask_bpy_image)
from ..geotracker.ui_strings import PrecalcStatusMessage
from ..blender_independent_packages.pykeentools_loader import module as pkt_module


_log = KTLogger(__name__)


class FrameListItem(PropertyGroup):
    num: IntProperty(name='Frame number', default=-1)


class TrackerItem(PropertyGroup):
    def precalc_message_error(self):
        return self.precalc_message in [
            PrecalcStatusMessage.empty,
            PrecalcStatusMessage.broken_file,
            PrecalcStatusMessage.missing_file]

    def get_mask_2d_channels(self) -> Tuple[bool, bool, bool, bool]:
        return self.mask_2d_channel_r, self.mask_2d_channel_g, \
               self.mask_2d_channel_b, self.mask_2d_channel_a

    def get_mask_2d_channel_bitmask(self) -> int:
        ''' Bitmask value in ABGR format
            0 - R (1)
            1 - G (2)
            2 - B (4)
            3 - Alpha (8)
        '''
        return int(self.mask_2d_channel_r) + 2 * int(self.mask_2d_channel_g) + \
               4 * int(self.mask_2d_channel_b) + 8 * int(self.mask_2d_channel_a)

    def get_2d_mask_source(self) -> str:
        if self.mask_2d_mode == 'COMP_MASK':
            return 'COMP_MASK' if self.compositing_mask != '' else 'NONE'
        elif self.mask_2d_mode == 'MASK_2D':
            return 'MASK_2D' if self.mask_2d else 'NONE'
        return 'NONE'

    def update_compositing_mask(self, *, frame: Optional[int]=None,
                                recreate_nodes: bool=False) -> Image:
        _log.output(f'update_compositing_mask enter. '
                    f'recreate_nodes={recreate_nodes}')
        shadow_scene = get_compositing_shadow_scene(
            GTConfig.gt_shadow_compositing_scene_name)
        if recreate_nodes:
            create_mask_compositing_node_tree(shadow_scene,
                                              self.compositing_mask,
                                              clear_nodes=True)
        frame_at = frame if frame is not None else bpy_current_frame()
        if recreate_nodes or self.compositing_mask != '':
            bpy_render_single_frame(shadow_scene, frame_at)
        mask_image = get_rendered_mask_bpy_image(
            GTConfig.gt_rendered_mask_image_name)
        viewer_node_to_image(mask_image)
        _log.output('update_compositing_mask exit')
        return mask_image

    def get_serial_str(self) -> str:
        return self.serial_str

    def save_serial_str(self, serial: str) -> None:
        self.serial_str = serial

    def camera_mode(self) -> None:
        return self.solve_for_camera

    def animatable_object(self) -> Optional[Object]:
        if self.camera_mode():
            return self.camobj
        return self.geomobj

    def non_animatable_object(self) -> Optional[Object]:
        if self.camera_mode():
            return self.geomobj
        return self.camobj

    def object_pair(self) -> Tuple[Object, Object]:
        if self.camera_mode():
            return self.camobj, self.geomobj
        return self.geomobj, self.camobj

    def animatable_object_name(self) -> str:
        obj = self.animatable_object()
        if not obj:
            return 'N/A'
        return obj.name

    def get_background_image_object(self) -> Optional[CameraBackgroundImage]:
        return get_background_image_object(self.camobj)

    def reload_background_image(self) -> None:
        bg_img = self.get_background_image_object()
        if bg_img is not None and bg_img.image:
            bg_img.image.reload()

    def setup_background_image(self) -> None:
        set_background_image_by_movieclip(self.camobj,
                                          self.movie_clip,
                                          name=GTConfig.gt_background_name,
                                          index=0)

    def setup_background_mask(self) -> None:
        set_background_image_by_movieclip(self.camobj,
                                          self.mask_2d,
                                          name=GTConfig.gt_background_mask_name,
                                          index=1)

    def reset_focal_length_estimation(self) -> None:
        self.focal_length_estimation = False

    def reload_precalc(self) -> Tuple[bool, str, Any]:
        return reload_precalc(self)

    def calc_model_matrix(self) -> Any:
        if not self.camobj or not self.geomobj:
            return np.eye(4)

        rot_mat = xz_to_xy_rotation_matrix_4x4()

        t, r, s = self.camobj.matrix_world.decompose()
        cam_mat = LocRotScale(t, r, (1, 1, 1))

        geom_mw = self.geomobj.matrix_world
        geom_scale_vec = get_scale_vec_4_from_matrix_world(geom_mw)
        if not geom_scale_vec.all():
            return np.eye(4)
        geom_scale_inv = np.diag(1.0 / geom_scale_vec)
        geom_mat = np.array(geom_mw, dtype=np.float32) @ geom_scale_inv

        nm = np.array(cam_mat.inverted_safe(),
                      dtype=np.float32) @ geom_mat @ rot_mat
        return nm

    def check_pins_on_geometry(self, gt: Any, deep_analyze: bool=False) -> bool:
        def _polygon_exists(vertices: List, poly_sets: List) -> bool:
            vert_set = set(vertices)
            for poly_set in poly_sets:
                if poly_set.issuperset(vert_set):
                    return True
            return False

        geomobj = self.geomobj
        if not geomobj or not geomobj.type == 'MESH':
            gt.remove_pins()
            return False

        verts_count = len(geomobj.data.vertices)

        keyframes = gt.keyframes()
        if len(keyframes) == 0:
            gt.remove_pins()
            return False

        mesh = geomobj.data
        poly_set_list = []

        if deep_analyze:
            for p in mesh.polygons:
                poly_set_list.append(set(p.vertices[:]))

        wrong_pins = []
        try:
            for i in range(gt.pins_count()):
                pin = gt.pin(keyframes[0], i)
                if not pin:
                    wrong_pins.append(i)
                    continue
                sp = pin.surface_point
                gp = sp.geo_point_idxs
                if len(gp) < 3 or gp[0] >= verts_count or \
                        gp[1] >= verts_count or gp[2] >= verts_count:
                    wrong_pins.append(i)
                    continue
                if deep_analyze and not _polygon_exists(sp.geo_point_idxs[:],
                                                        poly_set_list):
                    wrong_pins.append(i)
        except pkt_module().FaceGeoInputException as err:
            _log.red(f'check_pins_on_geometry FaceGeoInputException:\n{str(err)}')
            gt.remove_pins()
            return False

        if len(wrong_pins) > 0:
            _log.output(f'WRONG PINS: {wrong_pins}')
            for i in reversed(wrong_pins):
                gt.remove_pin(i)
            current_keyframe = bpy_current_frame()
            if gt.is_key_at(current_keyframe):
                gt.spring_pins_back(current_keyframe)
            else:
                gt.spring_pins_back(keyframes[0])

        return True

    def get_geomobj_name(self):
        if self.geomobj:
            return self.geomobj.name
        return 'none'

    def preview_material_name(self):
        return GTConfig.tex_builder_matname_template.format(self.get_geomobj_name())

    def preview_texture_name(self):
        return GTConfig.tex_builder_filename_template.format(self.get_geomobj_name())


class TRSceneSetting(PropertyGroup):
    def product_type(self) -> int:
        return ProductType.UNDEFINED

    def loader(self) -> Any:
        assert False, 'TRSceneSetting: loader'

    def get_adaptive_opacity(self):
        return self.adaptive_opacity if self.use_adaptive_opacity else 1.0

    def calc_adaptive_opacity(self, area: Area) -> None:
        if not area:
            return
        aw = area.width
        rx, ry = bpy_render_frame()
        denom = aw if 1 <= aw < rx else rx
        x1, y1, x2, y2 = get_camera_border(area)
        self.adaptive_opacity = (x2 - x1) / denom

    @contextmanager
    def ui_write_mode_context(self):
        self.ui_write_mode = True
        yield
        self.ui_write_mode = False

    def reset_pinmode_id(self) -> None:
        self.pinmode_id = 'stop'

    def wrong_pinmode_id(self) -> bool:
        return self.pinmode_id in {'', 'stop'}

    def get_last_geotracker_num(self) -> int:
        return len(self.trackers()) - 1

    def is_proper_geotracker_number(self, num: int) -> bool:
        return 0 <= num < len(self.trackers())

    def get_current_geotracker_item(self, safe=False) -> Optional[Any]:  # TrackerItem
        if self.is_proper_geotracker_number(self.current_tracker_num()):
            return self.trackers()[self.current_tracker_num()]
        elif not safe:
            self.set_current_tracker_num(-1)
        return None

    def get_geotracker_item(self, num:int) -> Any:  # TrackerItem
        return self.trackers()[num]

    def get_geotracker_item_safe(self, num: int) -> Optional[Any]:  # TrackerItem
        if self.is_proper_geotracker_number(num):
            return self.get_geotracker_item(num)
        return None

    def change_current_geotracker(self, num: int) -> None:
        self.fix_geotrackers()
        self.set_current_tracker_num(num)
        if not self.loader().load_geotracker():
            self.loader().new_kt_geotracker()

    def change_current_geotracker_safe(self, num: int) -> bool:
        if self.is_proper_geotracker_number(num):
            self.change_current_geotracker(num)
            return True
        return False

    def reload_current_geotracker(self) -> bool:
        self.fix_geotrackers()
        return self.change_current_geotracker_safe(self.current_tracker_num())

    def reload_mask_3d(self) -> None:
        geotracker = self.get_current_geotracker_item()
        if not geotracker:
            return
        gt = self.loader().kt_geotracker()
        if not geotracker.geomobj:
            return
        polys = get_polygons_in_vertex_group(geotracker.geomobj,
                                             geotracker.mask_3d,
                                             geotracker.mask_3d_inverted)
        gt.set_ignored_faces(polys)
        self.loader().save_geotracker()

    def reload_mask_2d(self) -> None:
        _log.output(_log.color('yellow', 'reload_mask_2d start'))
        geotracker = self.get_current_geotracker_item()
        if not geotracker:
            return
        vp = self.loader().viewport()
        mask = vp.mask2d()
        mask_source = geotracker.get_2d_mask_source()
        _log.output(f'mask mode: {mask_source}')
        if mask_source == 'MASK_2D':
            _log.output(f'RELOAD 2D MASK: {geotracker.mask_2d}')
            mask.image = get_background_image_strict(geotracker.camobj, index=1)
            mask.inverted = geotracker.mask_2d_inverted
            mask.mask_threshold = geotracker.mask_2d_threshold
            mask.channel = geotracker.get_mask_2d_channel_bitmask()
        elif mask_source == 'COMP_MASK':
            mask_image = geotracker.update_compositing_mask()
            _log.output('RELOAD 2D COMP_MASK')
            mask.image = mask_image
            mask.inverted = geotracker.compositing_mask_inverted
            mask.mask_threshold = geotracker.compositing_mask_threshold
            mask.channel = 7  # RGB bitmask (without Alpha)
        else:
            mask.image = None

        if mask.image:
            rw, rh = bpy_render_frame()
            size = mask.image.size[:]
            if rw == size[0] or rh == size[1]:
                geotracker.mask_2d_info = ''
            else:
                geotracker.mask_2d_info = f'Wrong size: {size[0]} x {size[1]} px'
                _log.output(f'size differs:\n{geotracker.mask_2d_info}')
        else:
            geotracker.mask_2d_info = ''
        _log.output('reload_mask_2d end')

    def add_geotracker_item(self) -> int:
        self.fix_geotrackers()
        self.trackers().add()
        return self.get_last_geotracker_num()

    def remove_geotracker_item(self, num: int) -> bool:
        self.fix_geotrackers()
        if self.is_proper_geotracker_number(num):
            self.trackers().remove(num)
            if self.current_tracker_num() >= num:
                self.set_current_tracker_num(self.current_tracker_num() - 1)
                if self.current_tracker_num() < 0:
                    if self.is_proper_geotracker_number(0):
                        self.set_current_tracker_num(0)
                    else:
                        self.set_current_tracker_num(-1)
            return True
        return False

    def start_selection(self, mouse_x: int, mouse_y: int) -> None:
        self.selection_x = mouse_x
        self.selection_y = mouse_y
        self.selection_mode = True
        self.do_selection(mouse_x, mouse_y)

    def do_selection(self, mouse_x: int=0, mouse_y: int=0) -> None:
        _log.output('DO SELECTION: {}'.format(self.selection_mode))
        vp = self.loader().viewport()
        selector = vp.selector()
        if not self.selection_mode:
            selector.clear_rectangle()
            selector.create_batch()
            return
        selector.add_rectangle(self.selection_x, self.selection_y,
                               mouse_x, mouse_y)
        selector.create_batch()

    def cancel_selection(self) -> None:
        self.selection_mode = False
        self.do_selection()

    def end_selection(self, area: Area, mouse_x: int, mouse_y: int) -> None:
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
        self.stabilize_viewport(reset=True)

    def stabilize_viewport(self, reset: bool = False) -> None:
        _log.output('settings.stabilize_viewport')
        vp = self.loader().viewport()
        if reset:
            vp.clear_stabilization_point()
        if not self.stabilize_viewport_enabled:
            return
        geotracker = self.get_current_geotracker_item()
        if not geotracker:
            return
        vp.stabilize(geotracker.geomobj)

    def stop_calculating(self) -> None:
        self.calculating_mode = 'NONE'

    def is_calculating(self, mode=None) -> bool:
        if mode is None:
            return self.calculating_mode != 'NONE'
        return self.calculating_mode == mode

    def fix_geotrackers(self) -> bool:
        def _object_is_not_in_use(obj: Optional[Object]):
            if obj is None:
                return False
            return obj.users <= 1

        flag = False
        for geotracker in self.trackers():
            if _object_is_not_in_use(geotracker.geomobj):
                geotracker.geomobj = None
                flag = True
            if _object_is_not_in_use(geotracker.camobj):
                geotracker.camobj = None
                flag = True
        return flag

    def preferences(self) -> Any:
        return get_addon_preferences()
