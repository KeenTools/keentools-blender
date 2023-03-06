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

import re
from typing import Tuple, Optional, Any
from functools import partial

import bpy
from bpy.types import Area, Panel

from ...addon_config import Config, geotracker_enabled, addon_pinmode
from ...geotracker_config import GTConfig, get_gt_settings
from ...blender_independent_packages.pykeentools_loader import is_installed as pkt_is_installed
from ...updater.panels import (KTUpdater,
                               KT_PT_UpdatePanel,
                               KT_PT_DownloadNotification,
                               KT_PT_DownloadingProblemPanel,
                               KT_PT_UpdatesInstallationPanel)
from ..gtloader import GTLoader
from ...utils.localview import exit_area_localview, check_context_localview
from ...utils.other import force_show_ui_overlays
from ...utils.bpy_common import bpy_timer_register
from ...utils.grace_timer import KTGraceTimer


_gt_grace_timer = KTGraceTimer('geotracker')


def _pinmode_escaper(area: Area) -> None:
    GTLoader.out_pinmode()
    exit_area_localview(area)
    force_show_ui_overlays(area)
    return None


def _start_pinmode_escaper(context: Any) -> None:
    if context.area:
        bpy_timer_register(partial(_pinmode_escaper, context.area),
                           first_interval=0.01)


def _geomobj_delete_handler() -> None:
    settings = get_gt_settings()
    if settings.pinmode:
        GTLoader.out_pinmode()
    settings.fix_geotrackers()
    return None


def _start_geomobj_delete_handler() -> None:
    bpy_timer_register(_geomobj_delete_handler, first_interval=0.01)


def _exit_from_localview_button(layout, context):
    if addon_pinmode() or not check_context_localview(context):
        return
    settings = get_gt_settings()
    if settings.is_calculating():
        return
    col = layout.column()
    col.alert = True
    col.scale_y = 2.0
    col.operator(Config.kt_exit_localview_idname)


def show_all_panels() -> bool:
    settings = get_gt_settings()
    return settings.current_geotracker_num >= 0


class View3DPanel(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    # bl_options = {'DEFAULT_CLOSED'}
    bl_category = GTConfig.gt_tab_category

    @classmethod
    def poll(cls, context: Any) -> bool:
        return geotracker_enabled()


class AllVisible(View3DPanel):
    @classmethod
    def poll(cls, context: Any) -> bool:
        if not geotracker_enabled():
            return False
        return show_all_panels()


def _draw_calculating_indicator(layout: Any) -> None:
    settings = get_gt_settings()
    row = layout.row(align=True)
    row.prop(settings, 'user_percent', text='Calculating...')
    col = row.column(align=True)
    col.alert = True
    col.operator(GTConfig.gt_stop_calculating_idname, text='',
                 icon='CANCEL')


class GT_PT_GeotrackersPanel(View3DPanel):
    bl_idname = GTConfig.gt_geotrackers_panel_idname
    bl_label = '{} {}'.format(GTConfig.gt_tool_name,
                              Config.addon_version)

    def draw_header_preset(self, context: Any) -> None:
        layout = self.layout
        row = layout.row()
        op = row.operator(
            Config.kt_addon_settings_idname,
            text='', icon='PREFERENCES')
        op.show = 'geotracker'

    def _geotracker_creation_offer(self, layout: Any) -> None:
        settings = get_gt_settings()
        if settings.pinmode:
            return
        row = layout.row()
        row.scale_y = 2.0
        row.operator(GTConfig.gt_create_geotracker_idname,
                     text='Create a new GeoTracker', icon='ADD')

    def _output_geotrackers_list(self, layout: Any) -> None:
        settings = get_gt_settings()
        geotracker_num = settings.current_geotracker_num

        for i, geotracker in enumerate(settings.geotrackers):

            row = layout.row(align=True)
            row.scale_y = Config.btn_scale_y

            if geotracker.geomobj:
                name = geotracker.geomobj.name
            else:
                name = '# Undefined'

            if settings.pinmode and geotracker_num == i:
                row.operator(GTConfig.gt_exit_pinmode_idname,
                             text='', icon='HIDE_OFF', depress=True)
            else:
                op = row.operator(GTConfig.gt_pinmode_idname,
                                  text='', icon='HIDE_OFF', depress=False)
                op.geotracker_num = i

            if not settings.pinmode:
                op = row.operator(
                    GTConfig.gt_select_geotracker_objects_idname, text=name,
                    depress=geotracker_num == i,
                    icon='CAMERA_DATA' if geotracker.camera_mode()
                    else 'MESH_ICOSPHERE')
                op.geotracker_num = i
            else:
                if geotracker_num == i:
                    row.operator(GTConfig.gt_exit_pinmode_idname,
                                 text=name, depress=True,
                                 icon='CAMERA_DATA' if geotracker.camera_mode()
                                 else 'MESH_ICOSPHERE')
                else:
                    op = row.operator(GTConfig.gt_pinmode_idname,
                                      text=name, depress=False,
                                      icon='CAMERA_DATA' if geotracker.camera_mode()
                                      else 'MESH_ICOSPHERE')
                    op.geotracker_num = i

            if not settings.pinmode:
                op = row.operator(GTConfig.gt_delete_geotracker_idname,
                                  text='', icon='CANCEL')
                op.geotracker_num = i

    def _pkt_install_offer(self, layout: Any) -> None:
        col = layout.column(align=True)
        col.scale_y = Config.text_scale_y
        col.label(text='You need to install')
        col.label(text='KeenTools Core library')
        col.label(text='before using GeoTracker.')

        row = layout.row()
        row.scale_y = 2.0
        op = row.operator(
            Config.kt_addon_settings_idname,
            text='Install Core library', icon='PREFERENCES')
        op.show = 'none'

    def draw(self, context: Any) -> None:
        layout = self.layout
        if not pkt_is_installed():
            self._pkt_install_offer(layout)
            return

        self._output_geotrackers_list(layout)
        self._geotracker_creation_offer(layout)
        _exit_from_localview_button(layout, context)
        KTUpdater.call_updater('GeoTracker')
        _gt_grace_timer.start()


class GT_PT_UpdatePanel(KT_PT_UpdatePanel):
    bl_idname = GTConfig.gt_update_panel_idname
    bl_category = Config.gt_tab_category

    @classmethod
    def poll(cls, context: Any) -> bool:
        if not geotracker_enabled():
            return False
        return KTUpdater.is_active()


class GT_PT_DownloadNotification(KT_PT_DownloadNotification):
    bl_idname = GTConfig.gt_download_notification_panel_idname
    bl_category = Config.gt_tab_category


class GT_PT_DownloadingProblemPanel(KT_PT_DownloadingProblemPanel):
    bl_idname = GTConfig.gt_downloading_problem_panel_idname
    bl_category = Config.gt_tab_category


class GT_PT_UpdatesInstallationPanel(KT_PT_UpdatesInstallationPanel):
    bl_idname = GTConfig.gt_updates_installation_panel_idname
    bl_category = Config.gt_tab_category


class GT_PT_InputsPanel(AllVisible):
    bl_idname = GTConfig.gt_input_panel_idname
    bl_label = 'Inputs'

    def draw_header_preset(self, context: Any) -> None:
        layout = self.layout
        row = layout.row()
        row.active = False
        row.operator(
            GTConfig.gt_help_inputs_idname,
            text='', icon='QUESTION')

    def draw(self, context: Any) -> None:
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item(safe=True)
        if not geotracker:
            return

        layout = self.layout

        row = layout.row()
        row.alert = not geotracker.camobj
        row.prop(geotracker, 'camobj', text='Camera')

        row = layout.row()
        row.alert = not geotracker.geomobj
        row.prop(geotracker, 'geomobj', text='Geometry')

        if geotracker.geomobj and geotracker.geomobj.users == 1:
            _start_geomobj_delete_handler()

        row = layout.row(align=True)
        col = row.column(align=True)
        col.alert = not geotracker.movie_clip
        col.prop(geotracker, 'movie_clip', text='Clip')

        if geotracker.movie_clip and geotracker.movie_clip.source == 'MOVIE':
            row.operator(GTConfig.gt_split_video_to_frames_exec_idname,
                         text='', icon='RENDER_RESULT')
        row.operator(GTConfig.gt_sequence_filebrowser_idname,
                     text='', icon='FILEBROWSER')

        col = layout.column(align=True)
        if not settings.pinmode:
            col.label(text='Tracked object:')
        row = col.row(align=True)
        row.prop(geotracker, 'solve_for_camera',
                 text='Geometry', icon='MESH_ICOSPHERE',
                 toggle=1, invert_checkbox=True)
        row.prop(geotracker, 'solve_for_camera',
                 text='Camera', icon='CAMERA_DATA',
                 toggle=1)

        col = layout.column(align=True)
        if not settings.pinmode:
            col.label(text='Cached data usage:')
        row = col.row(align=True)
        row.prop(geotracker, 'precalcless', text='Precalcless', toggle=1)
        row.prop(geotracker, 'precalcless', text='Use precalc', toggle=1,
                 invert_checkbox=True)


class GT_PT_MasksPanel(AllVisible):
    bl_idname = GTConfig.gt_masks_panel_idname
    bl_label = 'Masks'
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header_preset(self, context: Any) -> None:
        layout = self.layout
        row = layout.row()
        row.active = False
        row.operator(
            GTConfig.gt_help_masks_idname,
            text='', icon='QUESTION')

    def draw(self, context: Any) -> None:
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item(safe=True)
        if not geotracker:
            return

        layout = self.layout
        if geotracker.geomobj:
            row = layout.row(align=True)
            row.prop_search(geotracker, 'mask_3d',
                            geotracker.geomobj, 'vertex_groups')
            row.prop(geotracker, 'mask_3d_inverted',
                     text='', icon='ARROW_LEFTRIGHT')

        if not GTConfig.hide_2d_mask:
            row = layout.row(align=True)
            row.prop(geotracker, 'mask_source', expand=True)

            box = layout.box()
            row = box.row(align=True)
            row.prop_search(geotracker, 'mask_2d',
                            bpy.data, 'images')
            row.prop(geotracker, 'mask_2d_inverted',
                     text='', icon='ARROW_LEFTRIGHT')
            row.operator(GTConfig.gt_mask_sequence_filebrowser_idname,
                         text='', icon='FILEBROWSER')
            row = box.row(align=True)
            row.prop(geotracker, 'mask_2d_threshold', slider=True)

            if geotracker.mask_2d_info != '':
                arr = re.split('\r\n|\n', geotracker.mask_2d_info)
                for txt in arr:
                    col = layout.column(align=True)
                    col.scale_y = Config.text_scale_y
                    col.label(text=txt)

            box = layout.box()
            row = box.row(align=True)
            row.prop_search(geotracker, 'compositing_mask',
                            bpy.data, 'masks')
            row.prop(geotracker, 'compositing_mask_inverted',
                     text='', icon='ARROW_LEFTRIGHT')
            row = box.row(align=True)
            row.prop(geotracker, 'compositing_mask_threshold', slider=True)


class GT_PT_AnalyzePanel(AllVisible):
    bl_idname = GTConfig.gt_analyze_panel_idname
    bl_label = 'Analyze input'

    @classmethod
    def poll(cls, context: Any) -> bool:
        if not geotracker_enabled():
            return False
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item(safe=True)
        if not geotracker:
            return False
        return not geotracker.precalcless

    def draw_header_preset(self, context: Any) -> None:
        layout = self.layout
        row = layout.row()
        row.active = False
        row.operator(
            GTConfig.gt_help_analyze_idname,
            text='', icon='QUESTION')

    def draw(self, context: Any) -> None:
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item(safe=True)
        if not geotracker:
            return

        layout = self.layout
        block = layout.column(align=True)
        block.operator(GTConfig.gt_choose_precalc_file_idname,
                       text='Create / Load precalc file')
        if geotracker.precalc_path != '':
            box = block.box()
            col = box.column()
            col.scale_y = Config.text_scale_y
            col.label(text=geotracker.precalc_path)

            if geotracker.precalc_message != '':
                arr = re.split('\r\n|\n', geotracker.precalc_message)
                for txt in arr:
                    col.label(text=txt)

        if geotracker.precalc_path != '':
            if settings.is_calculating('PRECALC'):
                _draw_calculating_indicator(layout)
            else:
                col = layout.column(align=True)
                icon = 'ERROR' if not geotracker.movie_clip else 'NONE'
                col.operator(GTConfig.gt_create_precalc_idname,
                             text='Create precalc', icon=icon)

                row = layout.row()
                row.prop(geotracker, 'precalc_start')
                row.prop(geotracker, 'precalc_end')


class GT_PT_CameraPanel(AllVisible):
    bl_idname = GTConfig.gt_camera_panel_idname
    bl_label = 'Camera'
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header_preset(self, context: Any) -> None:
        layout = self.layout
        row = layout.row()

        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item(safe=True)
        if geotracker and geotracker.camobj:
            col = row.column()
            col.active = False
            row.label(text=f'{geotracker.camobj.data.lens:.2f}mm')
        else:
            col = row.column()
            col.alert = True
            col.label(text='', icon='ERROR')
        col = row.column()
        col.active = False
        col.operator(
            GTConfig.gt_help_camera_idname,
            text='', icon='QUESTION')

    def draw(self, context: Any) -> None:
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item(safe=True)
        if not geotracker:
            return

        if not geotracker.camobj:
            return

        layout = self.layout
        cam_data = geotracker.camobj.data

        col = layout.column()
        col.prop(geotracker, 'focal_length_mode', text='Mode')
        row = col.row()
        row.enabled = geotracker.focal_length_mode != 'CAMERA_FOCAL_LENGTH'
        row.prop(geotracker, 'focal_length_estimation')

        row = col.row(align=True)
        row.prop(cam_data, 'lens')

        row.operator(GTConfig.gt_remove_focal_keyframe_idname,
                     text='', icon='KEY_DEHLT')
        row.operator(GTConfig.gt_remove_focal_keyframes_idname,
                     text='', icon='CANCEL')

        col = layout.column(align=True)
        col.prop(cam_data, 'sensor_width')
        col.prop(cam_data, 'sensor_height')


class GT_PT_TrackingPanel(AllVisible):
    bl_idname = GTConfig.gt_tracking_panel_idname
    bl_label = 'Tracking'

    def draw_header_preset(self, context: Any) -> None:
        layout = self.layout
        row = layout.row()
        row.active = False
        row.operator(
            GTConfig.gt_help_tracking_idname,
            text='', icon='QUESTION')

    def draw(self, context: Any) -> None:
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item(safe=True)
        if not geotracker:
            return

        layout = self.layout

        row = layout.row()
        row.scale_y = 2.0
        if settings.pinmode:
            row.operator(GTConfig.gt_exit_pinmode_idname,
                         icon='LOOP_BACK',
                         depress=settings.pinmode)
            if not GTLoader.viewport().is_working():
                _start_pinmode_escaper(context)
        else:
            op = row.operator(GTConfig.gt_pinmode_idname,
                              text='Start Pinmode', icon='HIDE_OFF',
                              depress=settings.pinmode)
            op.geotracker_num = -1

        box = layout.box()

        row = box.row(align=True)
        row.operator(GTConfig.gt_prev_keyframe_idname, text=' ',
                     icon='PREV_KEYFRAME')
        row.operator(GTConfig.gt_next_keyframe_idname, text=' ',
                     icon='NEXT_KEYFRAME')
        row2 = row.row(align=True)
        row2.active = settings.pinmode
        row2.operator(GTConfig.gt_add_keyframe_idname, text=' ',
                     icon='KEY_HLT')
        row2.operator(GTConfig.gt_remove_keyframe_idname, text=' ',
                     icon='KEY_DEHLT')

        box = layout.box()
        col = box.column()

        row = col.row()
        row.enabled = geotracker.focal_length_mode == 'ZOOM_FOCAL_LENGTH'
        row.prop(geotracker, 'track_focal_length')

        row = box.row(align=True)
        row.active = settings.pinmode
        row.operator(GTConfig.gt_track_prev_idname, text=' ',
                     icon='TRACKING_BACKWARDS_SINGLE')
        row.operator(GTConfig.gt_track_to_start_idname, text=' ',
                     icon='TRACKING_BACKWARDS')
        row.operator(GTConfig.gt_track_to_end_idname, text=' ',
                     icon='TRACKING_FORWARDS')
        row.operator(GTConfig.gt_track_next_idname, text=' ',
                     icon='TRACKING_FORWARDS_SINGLE')

        row = box.row()
        row.active = settings.pinmode
        row.scale_y = 1.5
        row.operator(GTConfig.gt_refine_idname)
        row.operator(GTConfig.gt_refine_all_idname)

        row = box.row(align=True)
        row.active = settings.pinmode
        part = row.split(factor=0.5, align=True)
        row = part.split(factor=0.5, align=True)
        row.operator(GTConfig.gt_clear_tracking_backward_idname,
                     icon='TRACKING_CLEAR_BACKWARDS', text='')
        row.operator(GTConfig.gt_clear_tracking_between_idname, text='| Xk |')
        part = part.row(align=True)
        row = part.split(factor=0.5, align=True)
        row.operator(GTConfig.gt_clear_tracking_forward_idname,
                     icon='TRACKING_CLEAR_FORWARDS', text='')
        row.operator(GTConfig.gt_clear_all_tracking_idname, text='X')

        if settings.is_calculating('TRACKING') or settings.is_calculating('REFINE'):
            _draw_calculating_indicator(layout)

        box = layout.box()
        row = box.row(align=True)
        row.active = settings.pinmode
        row.operator(GTConfig.gt_remove_pins_idname, icon='X')
        row.operator(GTConfig.gt_toggle_pins_idname, icon='UNPINNED')

        row = box.row(align=True)
        row.active = settings.pinmode
        row.operator(GTConfig.gt_center_geo_idname)
        col = row.column()
        col.active = False
        col.operator(GTConfig.gt_magic_keyframe_idname)

        box = layout.box()
        box.prop(geotracker, 'spring_pins_back')

        col = box.column()
        col.active = False
        op = col.operator(GTConfig.gt_actor_idname,
                          text='stabilize view')
        op.action = 'stabilize_view'


class GT_PT_AppearanceSettingsPanel(AllVisible):
    bl_idname = GTConfig.gt_appearance_panel_idname
    bl_label = 'Appearance'

    def draw_header_preset(self, context: Any) -> None:
        layout = self.layout
        row = layout.row(align=True)
        row.active = False
        row.operator(
            GTConfig.gt_addon_setup_defaults_idname,
            text='', icon='PREFERENCES')
        row.operator(
            GTConfig.gt_help_appearance_idname,
            text='', icon='QUESTION')

    def draw(self, context: Any) -> None:
        layout = self.layout
        settings = get_gt_settings()

        box = layout.box()
        col = box.column(align=True)
        row = col.row(align=True)
        row.label(text='Wireframe')
        col.separator(factor=0.4)
        btn = row.column(align=True)
        btn.active = False
        btn.scale_y = 0.75
        btn.operator(
            GTConfig.gt_default_wireframe_settings_idname,
            text='', icon='LOOP_BACK', emboss=False, depress=False)

        split = col.split(factor=0.25, align=True)
        split.prop(settings, 'wireframe_color', text='')
        split.prop(settings, 'wireframe_opacity', text='', slider=True)
        col.prop(settings, 'wireframe_backface_culling')
        col.prop(settings, 'lit_wireframe')
        col.prop(settings, 'use_adaptive_opacity')

        box = layout.box()
        col = box.column(align=True)
        row = col.row(align=True)
        row.label(text='Pins')
        col.separator(factor=0.4)
        btn = row.column(align=True)
        btn.active = False
        btn.scale_y = 0.75
        btn.operator(
            GTConfig.gt_default_pin_settings_idname,
            text='', icon='LOOP_BACK', emboss=False, depress=False)
        col.prop(settings, 'pin_size', slider=True)
        col.prop(settings, 'pin_sensitivity', slider=True)

        geotracker = settings.get_current_geotracker_item(safe=True)
        if not geotracker:
            return

        box = layout.box()
        col = box.column(align=True)
        row = col.row(align=True)
        row.label(text='Background adjustment')
        col.separator(factor=0.4)
        btn = row.column(align=True)
        btn.active = False
        btn.scale_y = 0.75
        btn.operator(GTConfig.gt_reset_tone_mapping_idname,
                     text='', icon='LOOP_BACK', emboss=False, depress=False)
        col2 = col.column(align=True)
        row = col2.row(align=True)
        row.prop(geotracker, 'tone_exposure', slider=True)
        row.operator(GTConfig.gt_reset_tone_exposure_idname,
                     text='', icon='LOOP_BACK')
        row = col.row(align=True)
        row.prop(geotracker, 'tone_gamma', slider=True)
        row.operator(GTConfig.gt_reset_tone_gamma_idname,
                     text='', icon='LOOP_BACK')


class GT_PT_TexturePanel(AllVisible):
    bl_idname = GTConfig.gt_texture_panel_idname
    bl_label = 'Texture'
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header_preset(self, context: Any) -> None:
        layout = self.layout
        row = layout.row()
        row.active = False
        row.operator(
            GTConfig.gt_help_texture_idname,
            text='', icon='QUESTION')

    def draw(self, context: Any) -> None:
        layout = self.layout
        col = layout.column(align=True)
        col.scale_y = Config.btn_scale_y
        col.operator(GTConfig.gt_reproject_frame_idname,
                     text='Reproject current frame')
        col.operator(GTConfig.gt_select_frames_for_bake_idname,
                        text='Reproject from keyframes')
        col.operator(GTConfig.gt_reproject_tex_sequence_idname,
                        text='Reproject to sequence')

        settings = get_gt_settings()
        if settings.is_calculating('REPROJECT'):
            _draw_calculating_indicator(layout)


class GT_PT_AnimationPanel(AllVisible):
    bl_idname = GTConfig.gt_animation_panel_idname
    bl_label = 'Animation'
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header_preset(self, context: Any) -> None:
        layout = self.layout
        row = layout.row()
        row.active = False
        row.operator(
            GTConfig.gt_help_animation_idname,
            text='', icon='QUESTION')

    def draw(self, context: Any) -> None:
        layout = self.layout
        layout.label(text='Create helpers')
        col = layout.column(align=True)
        col.scale_y = Config.btn_scale_y
        col.operator(GTConfig.gt_create_animated_empty_idname)
        layout.label(text='Move to default position')
        col = layout.column(align=True)
        col.scale_y = Config.btn_scale_y
        col.operator(GTConfig.gt_relative_to_camera_idname,
                     text='Camera to default')
        col.operator(GTConfig.gt_relative_to_geometry_idname,
                     text='Object to default')

        layout.label(text='Repositioning of animated')
        col = layout.column(align=True)
        col.scale_y = Config.btn_scale_y
        col.operator(GTConfig.gt_geometry_repositioning_idname,
                     text='Reorient Geometry')
        col.operator(GTConfig.gt_camera_repositioning_idname,
                     text='Reorient Camera')

        layout.label(text='Convert tracked keys')
        col = layout.column(align=True)
        col.scale_y = Config.btn_scale_y
        col.operator(GTConfig.gt_move_tracking_to_camera_idname,
                     text='Geom. tracking -> Camera')
        col.operator(GTConfig.gt_move_tracking_to_geometry_idname,
                     text='Cam. tracking -> Geom.')


class GT_PT_RenderingPanel(AllVisible):
    bl_idname = GTConfig.gt_rendering_panel_idname
    bl_label = 'Rendering'
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header_preset(self, context: Any) -> None:
        layout = self.layout
        row = layout.row()
        row.active = False
        row.operator(
            GTConfig.gt_help_rendering_idname,
            text='', icon='QUESTION')

    def draw(self, context: Any) -> None:
        layout = self.layout
        col = layout.column(align=True)
        col.scale_y = Config.btn_scale_y
        col.operator(GTConfig.gt_render_with_background_idname)
        col.operator(GTConfig.gt_revert_default_render_idname)

        box = layout.box()
        col = box.column(align=True)
        col.prop(bpy.context.scene.render, 'film_transparent',
                 text='Transparent background')
        col.prop(bpy.context.scene, 'use_nodes',
                 text='Use compositing nodes')
