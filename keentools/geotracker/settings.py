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

from bpy.types import (Object, CameraBackgroundImage, Area, Image, Mask,
                       PropertyGroup, MovieClip)
from bpy.props import (IntProperty, BoolProperty, FloatProperty,
                       StringProperty, EnumProperty, FloatVectorProperty,
                       PointerProperty, CollectionProperty, BoolVectorProperty)

from ..utils.kt_logging import KTLogger
from ..addon_config import Config, get_addon_preferences
from ..geotracker_config import GTConfig
from .gtloader import GTLoader
from ..utils.images import (get_background_image_object,
                            get_background_image_strict,
                            set_background_image_by_movieclip)
from .utils.tracking import reload_precalc
from ..utils.coords import (xz_to_xy_rotation_matrix_4x4,
                            get_scale_vec_4_from_matrix_world,
                            get_image_space_coord,
                            get_camera_border,
                            get_polygons_in_vertex_group,
                            LocRotScale)
from ..utils.bpy_common import (bpy_render_frame,
                                bpy_current_frame,
                                bpy_render_single_frame,
                                bpy_poll_is_mesh,
                                bpy_poll_is_camera,
                                get_scene_camera_shift)
from ..utils.compositing import (get_compositing_shadow_scene,
                                 create_mask_compositing_node_tree,
                                 viewer_node_to_image,
                                 get_rendered_mask_bpy_image)
from ..preferences.user_preferences import (UserPreferences,
                                            universal_cached_getter,
                                            universal_cached_setter)
from ..utils.viewport_state import ViewportStateItem
from .ui_strings import PrecalcStatusMessage
from .callbacks import (update_camobj,
                        update_geomobj,
                        update_movieclip,
                        update_precalc_path,
                        update_wireframe,
                        update_mask_2d_color,
                        update_mask_3d_color,
                        update_wireframe_backface_culling,
                        update_background_tone_mapping,
                        update_pin_sensitivity,
                        update_pin_size,
                        update_focal_length_mode,
                        update_lens_mode,
                        update_track_focal_length,
                        update_mask_3d,
                        update_mask_2d,
                        update_mask_source,
                        update_spring_pins_back,
                        update_solve_for_camera,
                        update_smoothing,
                        update_stabilize_viewport_enabled,
                        update_locks)


_log = KTLogger(__name__)


class FrameListItem(PropertyGroup):
    num: IntProperty(name='Frame number', default=-1)


class GeoTrackerItem(PropertyGroup):
    serial_str: StringProperty(name='GeoTracker Serialization string')
    geomobj: PointerProperty(
        name='Geometry',
        description='Select target geometry from the list '
                    'of objects in your Scene',
        type=Object,
        poll=bpy_poll_is_mesh,
        update=update_geomobj)
    camobj: PointerProperty(
        name='Camera',
        description='Choose which camera will be your viewpoint',
        type=Object,
        poll=bpy_poll_is_camera,
        update=update_camobj)
    movie_clip: PointerProperty(name='Movie Clip',
                                description='Select Footage from list',
                                type=MovieClip,
                                update=update_movieclip)

    dir_name: StringProperty(name='Dir name')

    precalc_path: StringProperty(
        name='Analysis cache file path',
        description='The path for the analysis file. '
                    'The .precalc extension will be added automatically',
        update=update_precalc_path)
    precalc_start: IntProperty(name='from', default=1, min=0)
    precalc_end: IntProperty(name='to', default=250, min=0)
    precalc_message: StringProperty(name='Precalc info')

    def precalc_message_error(self):
        return self.precalc_message in [
            PrecalcStatusMessage.empty,
            PrecalcStatusMessage.broken_file,
            PrecalcStatusMessage.missing_file]

    solve_for_camera: BoolProperty(
        name='Track for Camera or Geometry',
        description='Which object will be tracked Geometry or Camera',
        default=False, update=update_solve_for_camera)
    reduce_pins: BoolProperty(name='Reduce pins', default=False)
    spring_pins_back: BoolProperty(
        name='Spring pins back', default=True,
        update=update_spring_pins_back)

    focal_length_estimation: BoolProperty(
        name='Estimate focal length',
        description='This will automatically calculate focal length '
                    'value while pinning. Estimation will be disabled '
                    'when you move on to another frame',
        default=False,
        update=update_lens_mode)
    track_focal_length: BoolProperty(
        name='Track focal length',
        description='Track focal length change',
        default=False,
        update=update_track_focal_length)

    tone_exposure: FloatProperty(
        name='Exposure', description='Adjust exposure in current frame',
        default=Config.default_tone_exposure,
        min=-10.0, max=10.0, soft_min=-4.0, soft_max=4.0, precision=2,
        update=update_background_tone_mapping)
    tone_gamma: FloatProperty(
        name='Gamma', description='Adjust gamma in current frame',
        default=Config.default_tone_gamma, min=0.01, max=10.0,
        soft_max=4.0, precision=2,
        update=update_background_tone_mapping)
    default_zoom_focal_length: FloatProperty(
        name='Default Zoom FL',
        default=50.0 / 36.0 * 1920,
        min=0.01, max=15000.0 / 36.0 * 1920)
    static_focal_length: FloatProperty(name='Static FL',
                                       default=50.0 / 36.0 * 1920,
                                       min=0.01, max=15000.0 / 36.0 * 1920)
    focal_length_mode: EnumProperty(name='Focal length mode',
        items=[
            ('CAMERA_FOCAL_LENGTH', 'CAMERA FOCAL LENGTH',
            'Use camera object focal length', 0),
            ('STATIC_FOCAL_LENGTH', 'STATIC FOCAL LENGTH',
            'Use the same static focal length in tracking', 1),
            ('ZOOM_FOCAL_LENGTH', 'ZOOM FOCAL LENGTH',
            'Use zooming focal length in tracking', 2)],
        description='Focal length calculation mode',
        update=update_focal_length_mode)

    lens_mode: EnumProperty(name='Lens',
        items=[
            ('FIXED', 'Fixed',
            'Fixed focal length', 0),
            ('ZOOM', 'Zoom',
            'Variable focal length', 1)],
        description='Selected lens type',
        update=update_lens_mode)

    precalcless: BoolProperty(
        name='Precalcless tracking',
        description='This will analyze the clip and create a .precalc '
                    'cache file to make tracking faster',
        default=False)

    selected_frames: CollectionProperty(type=FrameListItem,
                                        name='Selected frames')
    selected_frame_index: IntProperty(name='', default=0)

    mask_3d: StringProperty(
        name='Surface mask',
        description='Exclude polygons of selected Vertex Group from tracking',
        update=update_mask_3d)
    mask_3d_inverted: BoolProperty(
        name='Invert',
        description='Invert Surface mask',
        default=False,
        update=update_mask_3d)
    mask_2d_mode: EnumProperty(
        name='2D Mask mode',
        items=[
            ('COMP_MASK', 'Compositing', 'Use Blender Compositing mask', 0),
            ('MASK_2D', 'Sequence', 'Use 2d image sequence as a mask', 1),
        ],
        update=update_mask_2d)
    mask_2d: PointerProperty(
        type=MovieClip,
        name='2d mask',
        description='The masked areas will be excluded from tracking',
        update=update_mask_2d)
    mask_2d_inverted: BoolProperty(
        name='Invert Mask 2D',
        description='Invert Mask 2D area',
        default=False,
        update=update_mask_2d)
    mask_2d_threshold: FloatProperty(
        default=0.003, soft_min=0.0, soft_max=1.0, min=-0.1, max=1.1,
        precision=4,
        name='2d mask threshold',
        description='Cutout threshold',
        update=update_mask_2d)
    mask_2d_info: StringProperty(
        default='',
        name='2d mask info',
        description='About 2d mask')

    mask_2d_channel_r: BoolProperty(
        name='R',
        default=True,
        update=update_mask_2d
    )
    mask_2d_channel_g: BoolProperty(
        name='G',
        default=True,
        update=update_mask_2d
    )
    mask_2d_channel_b: BoolProperty(
        name='B',
        default=True,
        update=update_mask_2d
    )
    mask_2d_channel_a: BoolProperty(
        name='A',
        default=False,
        update=update_mask_2d
    )

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

    compositing_mask: StringProperty(
        default='',
        name='Compositing mask',
        description='Exclude area within selected Compositing mask from tracking',
        update=update_mask_source)
    compositing_mask_inverted: BoolProperty(
        name='Invert',
        description='Invert Compositing mask',
        default=False,
        update=update_mask_source)
    compositing_mask_threshold: FloatProperty(
        default=0.5, soft_min=0.0, soft_max=1.0, min=-0.1, max=1.1,
        precision=4,
        name='Compositing mask threshold',
        description='Compositing mask cutout threshold',
        update=update_mask_source)

    def get_2d_mask_source(self) -> str:
        if self.mask_2d_mode == 'COMP_MASK':
            return 'COMP_MASK' if self.compositing_mask != '' else 'NONE'
        elif self.mask_2d_mode == 'MASK_2D':
            return 'MASK_2D' if self.mask_2d else 'NONE'
        return 'NONE'

    smoothing_depth_coeff: FloatProperty(
        default=0.0, min=0.0, max=1.0,
        precision=2,
        name='Z Translation',
        description='Z-axis (camera view) translation smoothing',
        update=update_smoothing)
    smoothing_focal_length_coeff: FloatProperty(
        default=0.0, min=0.0, max=1.0,
        precision=2,
        name='Focal Length',
        description='Smoothing of focal length estimation',
        update=update_smoothing)
    smoothing_rotations_coeff: FloatProperty(
        default=0.0, min=0.0, max=1.0,
        precision=2,
        name='Rotations',
        description='Rotation smoothing', update=update_smoothing)
    smoothing_xy_translations_coeff: FloatProperty(
        default=0.0, min=0.0, max=1.0,
        precision=2,
        name='XY Translations',
        description='XY translation smoothing', update=update_smoothing)

    overlapping_detected: BoolProperty(default=False)

    locks: BoolVectorProperty(name='Locks', description='Fixes',
                              size=6, subtype='NONE',
                              default=(False,) * 6,
                              update=update_locks)

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


class GTSceneSettings(PropertyGroup):
    ui_write_mode: BoolProperty(name='UI Write mode', default=False)
    viewport_state: PointerProperty(type=ViewportStateItem)

    pinmode: BoolProperty(name='Pinmode status', default=False)
    pinmode_id: StringProperty(name='Unique pinmode ID')

    geotrackers: CollectionProperty(type=GeoTrackerItem, name='GeoTrackers')
    current_geotracker_num: IntProperty(name='Current Geotracker Number', default=-1)

    adaptive_opacity: FloatProperty(
        description='From 0.0 to 1.0',
        name='GeoTracker adaptive Opacity',
        default=1.0,
        min=0.0, max=1.0)

    use_adaptive_opacity: BoolProperty(
        name='Use adaptive opacity',
        default=True,
        update=update_wireframe)

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

    wireframe_opacity: FloatProperty(
        name='GeoTracker wireframe Opacity',
        default=UserPreferences.get_value_safe('gt_wireframe_opacity',
                                               UserPreferences.type_float),
        min=0.0, max=1.0,
        update=update_wireframe)

    wireframe_color: FloatVectorProperty(
        description='Mesh wireframe color in Pinmode',
        name='GeoTracker wireframe Color', subtype='COLOR',
        default=UserPreferences.get_value_safe('gt_wireframe_color',
                                               UserPreferences.type_color),
        min=0.0, max=1.0,
        update=update_wireframe)

    wireframe_backface_culling: BoolProperty(
        name='Backface culling',
        default=True,
        update=update_wireframe_backface_culling)

    lit_wireframe: BoolProperty(
        name='Lit wireframe',
        default=True,
        update=update_wireframe)

    pin_size: FloatProperty(
        name='Size', description='Pin size in pixels',
        default=UserPreferences.get_value_safe('pin_size',
                                               UserPreferences.type_float),
        min=1.0, max=100.0,
        precision=1,
        update=update_pin_size,
        get=universal_cached_getter('pin_size', 'float'),
        set=universal_cached_setter('pin_size')
    )
    pin_sensitivity: FloatProperty(
        name='Sensitivity', description='Active area in pixels',
        default=UserPreferences.get_value_safe('pin_sensitivity',
                                               UserPreferences.type_float),
        min=1.0, max=100.0,
        precision=1,
        update=update_pin_sensitivity,
        get=universal_cached_getter('pin_sensitivity', 'float'),
        set=universal_cached_setter('pin_sensitivity')
    )

    anim_start: IntProperty(name='from', default=1)
    anim_end: IntProperty(name='to', default=250)

    user_interrupts: BoolProperty(name='Interrupted by user',
                                  default = False)
    user_percent: FloatProperty(name='Percentage',
                                subtype='PERCENTAGE',
                                default=0.0, min=0.0, max=100.0,
                                precision=1)

    calculating_mode: EnumProperty(name='Calculating mode', items=[
        ('NONE', 'NONE', 'No calculation mode', 0),
        ('PRECALC', 'PRECALC', 'Precalc is calculating', 1),
        ('TRACKING', 'TRACKING', 'Tracking is calculating', 2),
        ('REFINE', 'REFINE', 'Refine is calculating', 3),
        ('REPROJECT', 'REPROJECT', 'Project and bake texture is calculating', 4),
        ('ESTIMATE_FL', 'ESTIMATE_FL', 'Focal length estimation is calculating', 5),
        ('JUMP', 'JUMP', 'Jump to frame', 6)
    ])

    selection_mode: BoolProperty(name='Selection mode', default=False)
    selection_x: FloatProperty(name='Selection X', default=0.0)
    selection_y: FloatProperty(name='Selection Y', default=0.0)

    mask_3d_color: FloatVectorProperty(
        description='Color of masked polygons',
        name='Mask 3D Color', subtype='COLOR',
        default=Config.default_user_preferences['gt_mask_3d_color']['value'],
        min=0.0, max=1.0,
        update=update_mask_3d_color)

    mask_3d_opacity: FloatProperty(
        description='From 0.0 to 1.0',
        name='Mask 3D opacity',
        default=Config.default_user_preferences['gt_mask_3d_opacity']['value'],
        min=0.0, max=1.0,
        update=update_mask_3d_color)

    mask_2d_color: FloatVectorProperty(
        description='Color of masked areas',
        name='Mask 2D Color', subtype='COLOR',
        default=Config.default_user_preferences['gt_mask_2d_color']['value'],
        min=0.0, max=1.0,
        update=update_mask_2d_color)

    mask_2d_opacity: FloatProperty(
        description='From 0.0 to 1.0',
        name='Mask 3D opacity',
        default=Config.default_user_preferences['gt_mask_3d_opacity']['value'],
        min=0.0, max=1.0,
        update=update_mask_2d_color)

    transfer_animation_selector: EnumProperty(
        name='Select direction',
        items=[
            ('GEOMETRY_TO_CAMERA', 'Geometry to Camera', '', 0),
            ('CAMERA_TO_GEOMETRY', 'Camera to Geometry', '', 1),],
        description='All animation will be converted from')

    bake_animation_selector: EnumProperty(name='Bake selector',
        items=[
            ('GEOMETRY_AND_CAMERA', 'Geometry & Camera',
             'Both objects will be baked to World space', 0),
            ('GEOMETRY', 'Geometry',
             'Geometry animation will be baked to World space', 1),
            ('CAMERA', 'Camera',
             'Camera animation will be baked to World space', 2),],
        description='Convert animation to World space')

    export_locator_selector: EnumProperty(name='Select source',
        items=[
            ('GEOMETRY', 'Geometry',
            'Use Geometry as animation source', 0),
            ('CAMERA', 'Camera',
             'Use Camera as animation source', 1),
            ('SELECTED_PINS', 'Selected pins',
             'Use selected pins as animation source', 2),],
        description='Create an animated Empty from')

    export_linked_locator: BoolProperty(
        name='Linked',
        description='Use shared animation Action or duplicate '
                    'animation data to use it independently',
        default=False)

    export_locator_orientation: EnumProperty(name='Empty Orientation', items=[
        ('NORMAL', 'Normal', 'Use normal direction of polygons', 0),
        ('OBJECT', 'Object', 'Use orientation aligned with Object Pivot', 1),
        ('WORLD', 'World', 'World aligned at start position', 2),
    ])

    tex_width: IntProperty(
        description='Width size of output texture',
        name='Width', default=Config.default_tex_width)
    tex_height: IntProperty(
        description='Height size of output texture',
        name='Height', default=Config.default_tex_height)

    tex_face_angles_affection: FloatProperty(
        description='Choose how much a polygon view angle affects '
                    'a pixel color: with 0 you will get an average '
                    'color from all views; with 100 you\'ll get color '
                    'information only from the polygons at which a camera '
                    'is looking at 90 degrees',
        name='Angle strictness',
        default=Config.default_tex_face_angles_affection, min=0.0, max=100.0)
    tex_uv_expand_percents: FloatProperty(
        description='Expand texture edges',
        name='Expand edges (%)', default=Config.default_tex_uv_expand_percents)
    tex_back_face_culling: BoolProperty(
        description='Exclude backfacing polygons from the created texture',
        name='Back face culling', default=True)
    tex_equalize_brightness: BoolProperty(
        description='Experimental. Automatically equalize '
                    'brightness across images',
        name='Equalize brightness', default=False)
    tex_equalize_colour: BoolProperty(
        description='Experimental. Automatically equalize '
                    'colors across images',
        name='Equalize color', default=False)
    tex_fill_gaps: BoolProperty(
        description='Experimental. Tries automatically fill '
                    'holes in face texture with appropriate '
                    'color',
        name='Autofill', default=False)

    tex_auto_preview: BoolProperty(
        description='Automatically apply the created texture',
        name='Automatically apply the created texture', default=True)

    stabilize_viewport_enabled: BoolProperty(
        description='Snap view to geometry or selected pin(s). Hotkey: L',
        name='Lock View', default=False,
        update=update_stabilize_viewport_enabled)

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
        _log.output(_log.color('yellow', 'reload_mask_2d start'))
        geotracker = self.get_current_geotracker_item()
        if not geotracker:
            return
        vp = GTLoader.viewport()
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

    def do_selection(self, mouse_x: int=0, mouse_y: int=0) -> None:
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
        shift_x, shift_y = get_scene_camera_shift()
        x1, y1 = get_image_space_coord(self.selection_x, self.selection_y, area,
                                       shift_x, shift_y)
        x2, y2 = get_image_space_coord(mouse_x, mouse_y, area, shift_x, shift_y)
        vp = GTLoader.viewport()
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
        vp = GTLoader.viewport()
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
        for geotracker in self.geotrackers:
            if _object_is_not_in_use(geotracker.geomobj):
                geotracker.geomobj = None
                flag = True
            if _object_is_not_in_use(geotracker.camobj):
                geotracker.camobj = None
                flag = True
        return flag

    def preferences(self) -> Any:
        return get_addon_preferences()
