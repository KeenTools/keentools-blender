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

from typing import Optional, Tuple, Any, List

from bpy.types import (Object, CameraBackgroundImage, Area, Image, Mask,
                       PropertyGroup, MovieClip)
from bpy.props import (IntProperty, BoolProperty, FloatProperty,
                       StringProperty, EnumProperty, FloatVectorProperty,
                       PointerProperty, CollectionProperty, BoolVectorProperty)

from ..utils.kt_logging import KTLogger
from ..addon_config import Config, ProductType
from .ftloader import FTLoader
from ..utils.bpy_common import (bpy_poll_is_mesh,
                                bpy_poll_is_camera)
from ..preferences.user_preferences import (UserPreferences,
                                            universal_cached_getter,
                                            universal_cached_setter)
from ..utils.viewport_state import ViewportStateItem
from .callbacks import (update_camobj,
                        update_geomobj,
                        update_movieclip,
                        update_precalc_path,
                        update_wireframe,
                        update_wireframe_image,
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
from ..tracker.settings import FrameListItem, TrackerItem, TRSceneSetting


_log = KTLogger(__name__)


class FaceTrackerItem(TrackerItem):
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


class FTSceneSettings(TRSceneSetting):
    def product_type(self) -> int:
        return ProductType.FACETRACKER

    def loader(self) -> Any:
        return FTLoader

    ui_write_mode: BoolProperty(name='UI Write mode', default=False)
    viewport_state: PointerProperty(type=ViewportStateItem)

    pinmode: BoolProperty(name='Pinmode status', default=False)
    pinmode_id: StringProperty(name='Unique pinmode ID')

    facetrackers: CollectionProperty(type=FaceTrackerItem, name='FaceTrackers')
    def trackers(self) -> Any:
        return self.facetrackers

    current_facetracker_num: IntProperty(name='Current FaceTracker Number', default=-1)
    def current_tracker_num(self) -> int:
        return self.current_facetracker_num
    def set_current_tracker_num(self, value: int) -> None:
        self.current_facetracker_num = value

    adaptive_opacity: FloatProperty(
        description='From 0.0 to 1.0',
        name='GeoTracker adaptive Opacity',
        default=1.0,
        min=0.0, max=1.0)

    use_adaptive_opacity: BoolProperty(
        name='Use adaptive opacity',
        default=True,
        update=update_wireframe)

    wireframe_opacity: FloatProperty(
        name='GeoTracker wireframe Opacity',
        default=UserPreferences.get_value_safe('gt_wireframe_opacity',
                                               UserPreferences.type_float),
        min=0.0, max=1.0,
        update=update_wireframe)

    wireframe_color: FloatVectorProperty(
        description='Mesh wireframe color in Pinmode',
        name='GeoTracker wireframe Color', subtype='COLOR',
        default=UserPreferences.get_value_safe('fb_wireframe_color',
                                               UserPreferences.type_color),
        min=0.0, max=1.0,
        update=update_wireframe_image)

    wireframe_special_color: FloatVectorProperty(
        description='Color of special parts in pin-mode',
        name='Wireframe Special Color', subtype='COLOR',
        default=UserPreferences.get_value_safe('fb_wireframe_special_color',
                                               UserPreferences.type_color),
        min=0.0, max=1.0,
        update=update_wireframe_image,
        get=universal_cached_getter('fb_wireframe_special_color', 'color'),
        set=universal_cached_setter('fb_wireframe_special_color'))

    wireframe_midline_color: FloatVectorProperty(
        description='Color of midline in pin-mode',
        name='Wireframe Midline Color', subtype='COLOR',
        default=UserPreferences.get_value_safe('fb_wireframe_midline_color',
                                               UserPreferences.type_color),
        min=0.0, max=1.0,
        update=update_wireframe_image,
        get=universal_cached_getter('fb_wireframe_midline_color', 'color'),
        set=universal_cached_setter('fb_wireframe_midline_color'))

    show_specials: BoolProperty(
        description='Use different colors for important head parts '
                    'on the mesh',
        name='Special face parts', default=True, update=update_wireframe_image)

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
