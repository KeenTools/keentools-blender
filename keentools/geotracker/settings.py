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

import numpy as np
from typing import Optional, Tuple, Any, List
from contextlib import contextmanager

import bpy
from bpy.types import Object, CameraBackgroundImage, Area, Image, Mask
from mathutils import Matrix

from ..utils.kt_logging import KTLogger
from ..addon_config import Config, get_addon_preferences
from ..geotracker_config import GTConfig, get_gt_settings
from .gtloader import GTLoader
from ..utils.images import (get_background_image_object,
                            set_background_image_by_movieclip,
                            tone_mapping,
                            find_bpy_image_by_name)
from .utils.tracking import reload_precalc
from ..utils.coords import (xz_to_xy_rotation_matrix_4x4,
                            get_scale_vec_4_from_matrix_world,
                            get_image_space_coord,
                            focal_mm_to_px,
                            camera_focal_length,
                            camera_sensor_width,
                            get_polygons_in_vertex_group)
from ..utils.video import fit_render_size, fit_time_length
from ..utils.bpy_common import (bpy_render_frame,
                                bpy_start_frame,
                                bpy_end_frame,
                                bpy_current_frame,
                                bpy_render_single_frame)
from ..utils.compositing import (get_compositing_shadow_scene,
                                 create_mask_compositing_node_tree,
                                 get_mask_by_name,
                                 viewer_node_to_image,
                                 get_rendered_mask_bpy_image)
from ..preferences.user_preferences import (UserPreferences,
                                            universal_cached_getter,
                                            universal_cached_setter)


_log = KTLogger(__name__)


def object_is_in_scene(obj: Object) -> bool:
    return obj in bpy.context.scene.objects[:]


def is_mesh(self, obj: Optional[Object]) -> bool:
    return obj and obj.type == 'MESH' and object_is_in_scene(obj)


def is_camera(self, obj: Optional[Object]) -> bool:
    return obj and obj.type == 'CAMERA' and object_is_in_scene(obj)


def update_camobj(geotracker, context: Any) -> None:
    _log.output('update_camera')
    _log.output(f'self: {geotracker.camobj}')
    if not geotracker.camobj:
        settings = get_gt_settings()
        if settings.pinmode:
            GTLoader.out_pinmode()
            return
    GTLoader.update_viewport_shaders()


def update_geomobj(geotracker, context: Any) -> None:
    def _polygon_exists(vertices: List, poly_sets: List) -> bool:
        vert_set = set(vertices)
        for poly_set in poly_sets:
            if poly_set.issuperset(vert_set):
                return True
        return False

    def _check_geometry(gt: Any, geomobj: Object) -> bool:
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
        for p in mesh.polygons:
            poly_set_list.append(set(p.vertices[:]))

        wrong_pins = []
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
            if not _polygon_exists(sp.geo_point_idxs[:], poly_set_list):
                wrong_pins.append(i)

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

    _log.output(f'update_geomobj: {geotracker.geomobj}')
    settings = get_gt_settings()
    if not geotracker.geomobj:
        if settings.pinmode:
            GTLoader.out_pinmode()
        return

    GTLoader.load_geotracker()
    gt = GTLoader.kt_geotracker()
    _check_geometry(gt, geotracker.geomobj)
    GTLoader.save_geotracker()
    if settings.pinmode:
        GTLoader.update_viewport_shaders()


def update_movieclip(geotracker, context: Any) -> None:
    _log.output('update_movieclip')
    settings = get_gt_settings()
    if settings.ui_write_mode:
        return
    set_background_image_by_movieclip(geotracker.camobj, geotracker.movie_clip)
    if geotracker.movie_clip:
        fit_render_size(geotracker.movie_clip)
        fit_time_length(geotracker.movie_clip)
        geotracker.precalc_start = bpy_start_frame()
        geotracker.precalc_end = bpy_end_frame()


def update_wireframe(self, context: Any) -> None:
    GTLoader.update_viewport_wireframe()


def update_mask_2d_color(settings, context: Any) -> None:
    vp = GTLoader.viewport()
    mask = vp.mask2d()
    mask.color = (*settings.mask_2d_color, settings.mask_2d_opacity)


def update_mask_3d_color(settings, context: Any) -> None:
    vp = GTLoader.viewport()
    wf = vp.wireframer()
    wf.selection_fill_color = (*settings.mask_3d_color, settings.mask_3d_opacity)
    if settings.pinmode:
        GTLoader.update_viewport_wireframe()


def update_wireframe_backface_culling(settings, context: Any) -> None:
    if settings.ui_write_mode:
        return
    gt = GTLoader.kt_geotracker()
    gt.set_back_face_culling(settings.wireframe_backface_culling)
    GTLoader.save_geotracker()
    if settings.pinmode:
        GTLoader.update_viewport_wireframe()


def update_lit_wireframe(settings, context: Any) -> None:
    if settings.pinmode:
        GTLoader.update_viewport_wireframe(normals=settings.lit_wireframe)


def update_background_tone_mapping(geotracker, context: Any) -> None:
    bg_img = get_background_image_object(geotracker.camobj)
    if not bg_img or not bg_img.image:
        return
    tone_mapping(bg_img.image,
                 exposure=geotracker.tone_exposure, gamma=geotracker.tone_gamma)


def update_pin_sensitivity(settings, context: Any) -> None:
    if settings.pin_size > settings.pin_sensitivity:
        settings.pin_size = settings.pin_sensitivity

    GTLoader.viewport().update_pin_sensitivity()


def update_pin_size(settings, context: Any) -> None:
    if settings.pin_sensitivity < settings.pin_size:
        settings.pin_sensitivity = settings.pin_size
    GTLoader.viewport().update_pin_size()


def update_focal_length_mode(geotracker, context: Any) -> None:
    _log.output(f'update_focal_length_mode: {geotracker.focal_length_mode}')
    if geotracker.focal_length_mode == 'STATIC_FOCAL_LENGTH':
        geotracker.static_focal_length = focal_mm_to_px(
            camera_focal_length(geotracker.camobj),
            *bpy_render_frame(), camera_sensor_width(geotracker.camobj))


def update_mask_3d(geotracker, context: Any) -> None:
    GTLoader.update_viewport_wireframe()
    settings = get_gt_settings()
    settings.reload_current_geotracker()
    settings.reload_mask_3d()


def update_mask_2d(geotracker, context: Any) -> None:
    GTLoader.update_viewport_wireframe()
    settings = get_gt_settings()
    settings.reload_current_geotracker()
    settings.reload_mask_2d()
    vp = GTLoader.viewport()
    if vp.is_working():
        vp.create_batch_2d(context.area)


def update_mask_source(geotracker, context: Any) -> None:
    if geotracker.mask_source == 'COMP_MASK':
        _log.output('switch to COMP_MASK')
        geotracker.update_compositing_mask(recreate_nodes=True)
    update_mask_2d(geotracker, context)


def update_spring_pins_back(geotracker, context: Any) -> None:
    if geotracker.spring_pins_back:
        GTLoader.load_geotracker()
        GTLoader.spring_pins_back()
        GTLoader.save_geotracker()
        settings = get_gt_settings()
        if settings.pinmode:
            GTLoader.update_viewport_shaders()
            GTLoader.viewport_area_redraw()


class FrameListItem(bpy.types.PropertyGroup):
    num: bpy.props.IntProperty(name='Frame number', default=-1)
    selected: bpy.props.BoolProperty(name='Selected', default=False)


class GeoTrackerItem(bpy.types.PropertyGroup):
    serial_str: bpy.props.StringProperty(name='GeoTracker Serialization string')
    geomobj: bpy.props.PointerProperty(name='Geometry',
                                       description='Geometry object in scene',
                                       type=bpy.types.Object,
                                       poll=is_mesh,
                                       update=update_geomobj)
    camobj: bpy.props.PointerProperty(name='Camera',
                                      description='Camera object in scene',
                                      type=bpy.types.Object,
                                      poll=is_camera,
                                      update=update_camobj)
    movie_clip: bpy.props.PointerProperty(name='Movie Clip',
                                          description='Footage for tracking',
                                          type=bpy.types.MovieClip,
                                          update=update_movieclip)

    dir_name: bpy.props.StringProperty(name='Dir name')

    precalc_path: bpy.props.StringProperty(name='Precalc path')
    precalc_start: bpy.props.IntProperty(name='from', default=1)
    precalc_end: bpy.props.IntProperty(name='to', default=250)
    precalc_message: bpy.props.StringProperty(name='Precalc info')

    solve_for_camera: bpy.props.BoolProperty(
        name='Track for Camera or Geometry',
        description='Which object will be tracked Geometry or Camera',
        default=False)
    reduce_pins: bpy.props.BoolProperty(name='Reduce pins', default=False)
    spring_pins_back: bpy.props.BoolProperty(
        name='Spring pins back', default=True,
        update=update_spring_pins_back)

    focal_length_estimation: bpy.props.BoolProperty(
        name='Estimate focal length',
        description='To enable this you need choose STATIC FOCAL as mode',
        default=False)
    track_focal_length: bpy.props.BoolProperty(
        name='Track focal length',
        description='This can be enabled only in ZOOM FOCAL LENGTH as mode',
        default=False)

    tone_exposure: bpy.props.FloatProperty(
        name='Exposure', description='Tone gain',
        default=Config.default_tone_exposure,
        min=-10.0, max=10.0, soft_min=-4.0, soft_max=4.0, precision=2,
        update=update_background_tone_mapping)
    tone_gamma: bpy.props.FloatProperty(
        name='Gamma correction', description='Tone gamma correction',
        default=Config.default_tone_gamma, min=0.01, max=10.0, soft_max=4.0, precision=2,
        update=update_background_tone_mapping)
    default_zoom_focal_length: bpy.props.FloatProperty(
        name='Default Zoom FL',
        default=50.0 / 36.0 * 1920,
        min=0.01, max=15000.0 / 36.0 * 1920)
    static_focal_length: bpy.props.FloatProperty(name='Static FL',
                                                 default=50.0 / 36.0 * 1920,
                                                 min=0.01, max=15000.0 / 36.0 * 1920)
    focal_length_mode: bpy.props.EnumProperty(name='Focal length mode',
        items=[
            ('CAMERA_FOCAL_LENGTH', 'CAMERA FOCAL LENGTH',
            'Use camera object focal length', 0),
            ('STATIC_FOCAL_LENGTH', 'STATIC FOCAL LENGTH',
            'Use the same static focal length in tracking', 1),
            ('ZOOM_FOCAL_LENGTH', 'ZOOM FOCAL LENGTH',
            'Use zooming focal length in tracking', 2)],
        description='Focal length calculation mode',
        update=update_focal_length_mode)

    precalcless: bpy.props.BoolProperty(
        name='Precalcless tracking',
        description='Using analysis (.precalc) file makes a tracking faster. '
                    'Precalcless tracking can help in difficult situations',
        default=True)

    selected_frames: bpy.props.CollectionProperty(type=FrameListItem,
                                                  name='Selected frames')
    mask_3d: bpy.props.StringProperty(
        name='3d mask',
        description='The polygons in selected Vertex Group '
                    'will be excluded from tracking',
        update=update_mask_3d)
    mask_3d_inverted: bpy.props.BoolProperty(
        name='Invert Mask 3D',
        description='Invert Mask 3D Vertex Group',
        default=False,
        update=update_mask_3d)
    mask_2d: bpy.props.StringProperty(
        name='2d mask',
        description='The masked areas will be excluded from tracking '
                    '(It does not work yet)',
        update=update_mask_2d)
    mask_2d_inverted: bpy.props.BoolProperty(
        name='Invert Mask 2D',
        description='Invert Mask 2D area',
        default=False,
        update=update_mask_2d)
    mask_2d_threshold: bpy.props.FloatProperty(
        default=0.002, soft_min=0.0, soft_max=1.0, min=-0.1, max=1.1,
        precision=4,
        name='2d mask threshold',
        description='Cutout threshold',
        update=update_mask_2d)
    mask_2d_info: bpy.props.StringProperty(
        default='',
        name='2d mask info',
        description='About 2d mask')
    compositing_mask: bpy.props.StringProperty(
        default='',
        name='Compositing 2D mask',
        description='Compositing 2D mask for tracking',
        update=update_mask_source)
    compositing_mask_inverted: bpy.props.BoolProperty(
        name='Invert Compositing Mask 2D',
        description='Invert Compositing Mask',
        default=False,
        update=update_mask_source)
    compositing_mask_threshold: bpy.props.FloatProperty(
        default=0.5, soft_min=0.0, soft_max=1.0, min=-0.1, max=1.1,
        precision=4,
        name='Compositing mask threshold',
        description='Compositing mask cutout threshold',
        update=update_mask_source)
    mask_source: bpy.props.EnumProperty(name='2D mask source',
        items=[
            ('NONE', 'No mask', 'Don\'t use mask', 0),
            ('MASK_2D', '2D image', 'Use 2D mask image', 1),
            ('COMP_MASK', 'Compositing', 'Use compositing mask', 2)],
        description='2D mask source',
        update=update_mask_source)

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

    def store_serial_str_on_geomobj(self) -> None:
        if self.geomobj:
            self.geomobj[GTConfig.serial_prop_name] = self.get_serial_str()

    def camera_mode(self) -> None:
        return self.solve_for_camera

    def animatable_object(self) -> Optional[Object]:
        if self.camera_mode():
            return self.camobj
        return self.geomobj

    def secondary_object(self) -> Optional[Object]:
        if not self.camera_mode():
            return self.camobj
        return self.geomobj

    def get_background_image_object(self) -> Optional[CameraBackgroundImage]:
        return get_background_image_object(self.camobj)

    def reload_background_image(self) -> None:
        bg_img = self.get_background_image_object()
        if bg_img is not None and bg_img.image:
            bg_img.image.reload()

    def reset_focal_length_estimation(self) -> None:
        self.focal_length_estimation = False

    def reload_precalc(self) -> Tuple[bool, str, Any]:
        return reload_precalc(self)

    def calc_model_matrix(self) -> Any:
        if not self.camobj or not self.geomobj:
            return np.eye(4)

        rot_mat = xz_to_xy_rotation_matrix_4x4()

        t, r, s = self.camobj.matrix_world.decompose()
        cam_mat = Matrix.LocRotScale(t, r, (1, 1, 1))

        geom_mw = self.geomobj.matrix_world
        geom_scale_vec = get_scale_vec_4_from_matrix_world(geom_mw)
        geom_scale_inv = np.diag(1.0 / geom_scale_vec)
        geom_mat = np.array(geom_mw, dtype=np.float32) @ geom_scale_inv

        nm = np.array(cam_mat.inverted_safe(),
                      dtype=np.float32) @ geom_mat @ rot_mat
        return nm


class GTSceneSettings(bpy.types.PropertyGroup):
    ui_write_mode: bpy.props.BoolProperty(name='UI Write mode', default=False)
    pinmode: bpy.props.BoolProperty(name='Pinmode status', default=False)
    pinmode_id: bpy.props.StringProperty(name='Unique pinmode ID')

    geotrackers: bpy.props.CollectionProperty(type=GeoTrackerItem, name='GeoTrackers')
    current_geotracker_num: bpy.props.IntProperty(name='Current Geotracker Number', default=-1)

    adaptive_opacity: bpy.props.FloatProperty(
        description='From 0.0 to 1.0',
        name='GeoTracker adaptive Opacity',
        default=1.0,
        min=0.0, max=1.0)

    use_adaptive_opacity: bpy.props.BoolProperty(
        name='Use adaptive opacity',
        default=True,
        update=update_wireframe)

    def get_adaptive_opacity(self):
        return self.adaptive_opacity if self.use_adaptive_opacity else 1.0

    wireframe_opacity: bpy.props.FloatProperty(
        description='From 0.0 to 1.0',
        name='GeoTracker wireframe Opacity',
        default=UserPreferences.get_value_safe('gt_wireframe_opacity',
                                               UserPreferences.type_float),
        min=0.0, max=1.0,
        update=update_wireframe)

    wireframe_color: bpy.props.FloatVectorProperty(
        description='Color of mesh wireframe in pin-mode',
        name='GeoTracker wireframe Color', subtype='COLOR',
        default=UserPreferences.get_value_safe('gt_wireframe_color',
                                               UserPreferences.type_color),
        min=0.0, max=1.0,
        update=update_wireframe)

    wireframe_backface_culling: bpy.props.BoolProperty(
        name='Backface culling',
        default=True,
        update=update_wireframe_backface_culling)

    lit_wireframe: bpy.props.BoolProperty(
        name='Lit wireframe',
        default=False,
        update=update_lit_wireframe)

    pin_size: bpy.props.FloatProperty(
        description='Set pin size in pixels',
        name='Size',
        default=UserPreferences.get_value_safe('pin_size',
                                               UserPreferences.type_float),
        min=1.0, max=100.0,
        precision=1,
        update=update_pin_size,
        get=universal_cached_getter('pin_size', 'float'),
        set=universal_cached_setter('pin_size')
    )
    pin_sensitivity: bpy.props.FloatProperty(
        description='Set active area in pixels',
        name='Active area',
        default=UserPreferences.get_value_safe('pin_sensitivity',
                                               UserPreferences.type_float),
        min=1.0, max=100.0,
        precision=1,
        update=update_pin_sensitivity,
        get=universal_cached_getter('pin_sensitivity', 'float'),
        set=universal_cached_setter('pin_sensitivity')
    )

    anim_start: bpy.props.IntProperty(name='from', default=1)
    anim_end: bpy.props.IntProperty(name='to', default=250)

    user_interrupts: bpy.props.BoolProperty(name='Interrupted by user',
                                            default = False)
    user_percent: bpy.props.FloatProperty(name='Percentage',
                                          subtype='PERCENTAGE',
                                          default=0.0, min=0.0, max=100.0,
                                          precision=1)

    calculating_mode: bpy.props.EnumProperty(name='Calculating mode', items=[
        ('NONE', 'NONE', 'No calculation mode', 0),
        ('PRECALC', 'PRECALC', 'Precalc is calculating', 1),
        ('TRACKING', 'TRACKING', 'Tracking is calculating', 2),
        ('REFINE', 'REFINE', 'Refine is calculating', 3),
        ('REPROJECT', 'REPROJECT', 'Reproject is calculating', 4),
        ('ESTIMATE_FL', 'ESTIMATE_FL', 'Focal length estimation is calculating', 5)
    ])

    selection_mode: bpy.props.BoolProperty(name='Selection mode',
                                           default=False)
    selection_x: bpy.props.FloatProperty(name='Selection X',
                                         default=0.0)
    selection_y: bpy.props.FloatProperty(name='Selection Y',
                                         default=0.0)

    mask_3d_color: bpy.props.FloatVectorProperty(
        description='Color of masked polygons',
        name='Mask 3D Color', subtype='COLOR',
        default=Config.default_user_preferences['gt_mask_3d_color']['value'],
        min=0.0, max=1.0,
        update=update_mask_3d_color)

    mask_3d_opacity: bpy.props.FloatProperty(
        description='From 0.0 to 1.0',
        name='Mask 3D opacity',
        default=Config.default_user_preferences['gt_mask_3d_opacity']['value'],
        min=0.0, max=1.0,
        update=update_mask_3d_color)

    mask_2d_color: bpy.props.FloatVectorProperty(
        description='Color of masked areas',
        name='Mask 2D Color', subtype='COLOR',
        default=Config.default_user_preferences['gt_mask_2d_color']['value'],
        min=0.0, max=1.0,
        update=update_mask_2d_color)

    mask_2d_opacity: bpy.props.FloatProperty(
        description='From 0.0 to 1.0',
        name='Mask 3D opacity',
        default=Config.default_user_preferences['gt_mask_3d_opacity']['value'],
        min=0.0, max=1.0,
        update=update_mask_2d_color)

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
        return len(self.geotrackers) - 1

    def is_proper_geotracker_number(self, num: int) -> bool:
        return 0 <= num < len(self.geotrackers)

    def get_current_geotracker_item(self, safe=False) -> Optional[GeoTrackerItem]:
        if self.is_proper_geotracker_number(self.current_geotracker_num):
            return self.geotrackers[self.current_geotracker_num]
        elif not safe:
            self.current_geotracker_num = -1
        return None

    def get_geotracker_item(self, num:int) -> GeoTrackerItem:
        return self.geotrackers[num]

    def get_geotracker_item_safe(self, num: int) -> Optional[GeoTrackerItem]:
        if self.is_proper_geotracker_number(num):
            return self.get_geotracker_item(num)
        return None

    def change_current_geotracker(self, num: int) -> None:
        self.fix_geotrackers()
        self.current_geotracker_num = num
        if not GTLoader.load_geotracker():
            GTLoader.new_kt_geotracker()

    def change_current_geotracker_safe(self, num: int) -> bool:
        if self.is_proper_geotracker_number(num):
            self.change_current_geotracker(num)
            return True
        return False

    def reload_current_geotracker(self) -> bool:
        self.fix_geotrackers()
        return self.change_current_geotracker_safe(self.current_geotracker_num)

    def reload_mask_3d(self) -> None:
        geotracker = self.get_current_geotracker_item()
        if not geotracker:
            return
        gt = GTLoader.kt_geotracker()
        if not geotracker.geomobj:
            return
        polys = get_polygons_in_vertex_group(geotracker.geomobj,
                                             geotracker.mask_3d,
                                             geotracker.mask_3d_inverted)
        gt.set_ignored_faces(polys)
        GTLoader.save_geotracker()

    def reload_mask_2d(self) -> None:
        geotracker = self.get_current_geotracker_item()
        if not geotracker:
            return
        vp = GTLoader.viewport()
        mask = vp.mask2d()
        if geotracker.mask_source == 'MASK_2D':
            _log.output(f'RELOAD 2D MASK: {geotracker.mask_2d}')
            mask.image = find_bpy_image_by_name(geotracker.mask_2d)
            mask.inverted = geotracker.mask_2d_inverted
            mask.mask_threshold = geotracker.mask_2d_threshold
        elif geotracker.mask_source == 'COMP_MASK':
            mask_image = geotracker.update_compositing_mask()
            _log.output('RELOAD 2D COMP_MASK')
            mask.image = mask_image
            mask.inverted = geotracker.compositing_mask_inverted
            mask.mask_threshold = geotracker.compositing_mask_threshold
        else:
            mask.image = None

        if mask.image:
            rw, rh = bpy_render_frame()
            size = mask.image.size[:]
            if rw == size[0] or rh == size[1]:
                geotracker.mask_2d_info = ''
            else:
                geotracker.mask_2d_info = f'Wrong size: {size[0]} x {size[1]} px'
        else:
            geotracker.mask_2d_info = ''

    def add_geotracker_item(self) -> int:
        self.fix_geotrackers()
        self.geotrackers.add()
        return self.get_last_geotracker_num()

    def remove_geotracker_item(self, num: int) -> bool:
        self.fix_geotrackers()
        if self.is_proper_geotracker_number(num):
            self.geotrackers.remove(num)
            if self.current_geotracker_num >= num:
                self.current_geotracker_num -= 1
                if self.current_geotracker_num < 0:
                    if self.is_proper_geotracker_number(0):
                        self.current_geotracker_num = 0
                    else:
                        self.current_geotracker_num = -1
            return True
        return False

    def start_selection(self, mouse_x: int, mouse_y: int) -> None:
        self.selection_x = mouse_x
        self.selection_y = mouse_y
        self.selection_mode = True
        self.do_selection(mouse_x, mouse_y)

    def do_selection(self, mouse_x: int=0, mouse_y: int=0):
        _log.output('DO SELECTION: {}'.format(self.selection_mode))
        vp = GTLoader.viewport()
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
        x1, y1 = get_image_space_coord(self.selection_x, self.selection_y, area)
        x2, y2 = get_image_space_coord(mouse_x, mouse_y, area)
        vp = GTLoader.viewport()
        pins = vp.pins()
        found_pins = pins.pins_inside_rectangle(x1, y1, x2, y2)
        if pins.get_add_selection_mode():
            pins.toggle_selected_pins(found_pins)
        else:
            pins.set_selected_pins(found_pins)
        self.cancel_selection()

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
        for geotracker in self.geotrackers:
            if _object_is_not_in_use(geotracker.geomobj):
                geotracker.geomobj = None
                flag = True
            if _object_is_not_in_use(geotracker.camobj):
                geotracker.camobj = None
                flag = True
        return flag

    def preferences(self):
        return get_addon_preferences()
