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
from ...utils.viewport_state import force_show_ui_overlays
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
        if not pkt_is_installed():
            return False
        settings = get_gt_settings()
        if not settings.current_geotracker_num >= 0:
            return False
        geotracker = settings.get_current_geotracker_item()
        return geotracker.geomobj and geotracker.camobj


def _draw_calculating_indicator(layout: Any) -> None:
    settings = get_gt_settings()
    row = layout.row(align=True)
    row.prop(settings, 'user_percent', text='Calculating...')
    col = row.column(align=True)
    col.alert = True
    icon = 'CANCEL' if not settings.user_interrupts else 'X'
    col.operator(GTConfig.gt_stop_calculating_idname, text='',
                 icon=icon)


class GT_PT_GeotrackersPanel(View3DPanel):
    bl_idname = GTConfig.gt_geotrackers_panel_idname
    bl_label = '{} {}'.format(GTConfig.gt_tool_name,
                              Config.addon_version)

    def draw_header_preset(self, context: Any) -> None:
        layout = self.layout
        row = layout.row()
        op = row.operator(Config.kt_addon_settings_idname,
                          text='', icon='PREFERENCES', emboss=False)
        op.show = 'geotracker'

    def _geotracker_creation_offer(self, layout: Any) -> None:
        settings = get_gt_settings()
        row = layout.row()
        row.active = not settings.pinmode
        row.enabled = not settings.pinmode
        row.scale_y = 2.0 if len(settings.geotrackers) == 0 else Config.btn_scale_y
        row.operator(GTConfig.gt_create_geotracker_idname, icon='ADD')

    def _output_geotrackers_list(self, layout: Any) -> None:
        settings = get_gt_settings()
        geotracker_num = settings.current_geotracker_num

        for i, geotracker in enumerate(settings.geotrackers):

            row = layout.row(align=True)
            row.scale_y = Config.btn_scale_y

            name = geotracker.animatable_object_name()

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

    @classmethod
    def poll(cls, context: Any) -> bool:
        if not geotracker_enabled():
            return False
        if not pkt_is_installed():
            return False
        settings = get_gt_settings()
        if not settings.current_geotracker_num >= 0:
            return False
        return True

    def draw_header_preset(self, context: Any) -> None:
        layout = self.layout
        row = layout.row()
        row.active = False
        row.operator(GTConfig.gt_help_inputs_idname,
                     text='', icon='QUESTION', emboss=False)

    def _draw_main_inputs(self, layout, geotracker):
        factor = 0.35
        split = layout.split(factor=factor, align=True)
        split.label(text='Clip')

        row = split.row(align=True)
        row.alert = not geotracker.movie_clip
        row.prop(geotracker, 'movie_clip', text='')

        if geotracker.movie_clip:
            row.menu(GTConfig.gt_clip_menu_idname, text='', icon='COLLAPSEMENU')
        else:
            row.operator(GTConfig.gt_sequence_filebrowser_idname,
                         text='', icon='FILEBROWSER')

        split = layout.split(factor=factor, align=True)
        split.label(text='Geometry')

        row = split.row()
        row.alert = not geotracker.geomobj
        row.prop(geotracker, 'geomobj', text='')

        split = layout.split(factor=factor, align=True)
        split.label(text='Camera')

        row = split.row()
        row.alert = not geotracker.camobj
        row.prop(geotracker, 'camobj', text='')

    def _draw_precalc_switcher(self, layout, geotracker):
        row = layout.row(align=True)
        row.prop(geotracker, 'precalcless',
                 text='Use analysis cache file', invert_checkbox=True)

    def _draw_analyze_btn(self, layout, geotracker):
        no_movie_clip = not geotracker.movie_clip
        precalc_path_is_empty = geotracker.precalc_path == ''

        col = layout.column()
        txt = 'Analyse'
        if no_movie_clip or precalc_path_is_empty or not geotracker.camobj:
            col.enabled = False
        else:
            error = geotracker.precalc_message_error()
            col.alert = error
            if not error:
                txt = 'Re-analyse'
        col.operator(GTConfig.gt_analyze_call_idname, text=txt)

    def draw(self, context: Any) -> None:
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item(safe=True)
        if not geotracker:
            return

        if geotracker.geomobj and geotracker.geomobj.users == 1:
            _start_geomobj_delete_handler()

        layout = self.layout
        self._draw_main_inputs(layout, geotracker)

        col = layout.column(align=True)
        self._draw_precalc_switcher(col, geotracker)

        if geotracker.precalcless:
            return

        row = col.row(align=True)
        no_movie_clip = not geotracker.movie_clip
        precalc_path_is_empty = geotracker.precalc_path == ''

        if no_movie_clip or not geotracker.camobj:
            row.enabled = False
        else:
            if precalc_path_is_empty:
                row.alert = True
        row.prop(geotracker, 'precalc_path', text='')
        row.operator(GTConfig.gt_choose_precalc_file_idname,
                     text='', icon='FILEBROWSER')

        if not precalc_path_is_empty:
            row.operator(GTConfig.gt_precalc_info_idname,
                         text='', icon='INFO')
        else:
            if not no_movie_clip:
                row.operator(GTConfig.gt_auto_name_precalc_idname,
                             text='', icon='FILE_HIDDEN')

        if settings.is_calculating('PRECALC'):
            _draw_calculating_indicator(layout)
        else:
            self._draw_analyze_btn(col, geotracker)


class GT_PT_MasksPanel(AllVisible):
    bl_idname = GTConfig.gt_masks_panel_idname
    bl_label = 'Masks'
    bl_options = {'DEFAULT_CLOSED'}

    def _mask_3d_block(self, layout: Any, geotracker: Any) -> None:
        if not geotracker.geomobj:
            return

        col = layout.column(align=True)
        col.label(text='Surface mask')
        row = col.row(align=True)
        row.prop_search(geotracker, 'mask_3d',
                        geotracker.geomobj, 'vertex_groups', text='')
        row.prop(geotracker, 'mask_3d_inverted',
                 text='', icon='ARROW_LEFTRIGHT')

    def _mask_2d_block(self, layout: Any, geotracker: Any) -> None:
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

        if geotracker.mask_2d_info == '':
            return

        arr = re.split('\r\n|\n', geotracker.mask_2d_info)
        for txt in arr:
            col = layout.column(align=True)
            col.scale_y = Config.text_scale_y
            col.label(text=txt)

    def _mask_compositing_block(self, layout: Any, geotracker: Any) -> None:
        col = layout.column(align=True)
        col.label(text='Compositing mask')
        row = col.row(align=True)
        row.prop_search(geotracker, 'compositing_mask',
                        bpy.data, 'masks', text='')
        row.prop(geotracker, 'compositing_mask_inverted',
                 text='', icon='ARROW_LEFTRIGHT')

        if not GTConfig.hidden_feature:
            row = col.row(align=True)
            row.prop(geotracker, 'compositing_mask_threshold', slider=True)

    def _mask_3d_enabled(self, geotracker: Any) -> bool:
        return geotracker and geotracker.geomobj and geotracker.mask_3d != ''

    def _mask_2d_enabled(self, geotracker: Any) -> bool:
        return geotracker and geotracker.get_mask_source() != 'NONE'

    def draw_header_preset(self, context: Any) -> None:
        layout = self.layout
        row = layout.row()
        row.active = False
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item(safe=True)
        if self._mask_3d_enabled(geotracker):
            if self._mask_2d_enabled(geotracker):
                row.label(text='2D / 3D')
            else:
                row.label(text='3D')
        else:
            if self._mask_2d_enabled(geotracker):
                row.label(text='2D')
        row.operator(GTConfig.gt_help_masks_idname,
                     text='', icon='QUESTION', emboss=False)

    def draw(self, context: Any) -> None:
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item(safe=True)
        if not geotracker:
            return

        layout = self.layout
        self._mask_3d_block(layout, geotracker)

        if not GTConfig.hidden_feature:
            self._mask_2d_block(layout, geotracker)
        self._mask_compositing_block(layout, geotracker)


class GT_PT_CameraPanel(AllVisible):
    bl_idname = GTConfig.gt_camera_panel_idname
    bl_label = 'Camera'
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context: Any) -> bool:
        if not geotracker_enabled():
            return False
        if not pkt_is_installed():
            return False
        settings = get_gt_settings()
        if not settings.current_geotracker_num >= 0:
            return False
        geotracker = settings.get_current_geotracker_item()
        return not not geotracker.camobj

    def _camera_lens_row(self, layout: Any, cam_data: Any) -> None:
        row = layout.row(align=True)
        row.prop(cam_data, 'lens')
        row.operator(GTConfig.gt_remove_focal_keyframe_idname,
                     text='', icon='KEY_DEHLT')
        row.operator(GTConfig.gt_remove_focal_keyframes_idname,
                     text='', icon='CANCEL')

    def _camera_sensor_size(self, layout: Any, cam_data: Any) -> None:
        col = layout.column(align=True)
        col.prop(cam_data, 'sensor_width')
        col.prop(cam_data, 'sensor_height')

    def _camera_header_lens_info(self, layout: Any, geotracker: Any) -> None:
        col = layout.column()
        if geotracker and geotracker.camobj:
            col.active = False
            col.label(text=f'{geotracker.camobj.data.lens:.2f}mm')
        else:
            col.alert = True
            col.label(text='', icon='ERROR')

    def _camera_header_help_button(self, layout: Any) -> None:
        col = layout.column()
        col.active = False
        col.operator(GTConfig.gt_help_camera_idname,
                     text='', icon='QUESTION', emboss=False)

    def draw_header_preset(self, context: Any) -> None:
        layout = self.layout

        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item(safe=True)

        self._camera_header_lens_info(layout, geotracker)
        self._camera_header_help_button(layout)

    def draw(self, context: Any) -> None:
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item(safe=True)
        if not geotracker or not geotracker.camobj:
            return

        layout = self.layout
        cam_data = geotracker.camobj.data

        col = layout.column()
        col.prop(geotracker, 'lens_mode')
        row = col.row()
        row.prop(geotracker, 'focal_length_estimation')
        if geotracker.lens_mode == 'ZOOM':
            row = col.row()
            row.prop(geotracker, 'track_focal_length')

        self._camera_lens_row(layout, cam_data)
        self._camera_sensor_size(layout, cam_data)


class GT_PT_TrackingPanel(AllVisible):
    bl_idname = GTConfig.gt_tracking_panel_idname
    bl_label = 'Tracking'

    def _tracking_mode_selector(self, settings: Any, layout: Any,
                                geotracker: Any) -> None:
        col = layout.column(align=True)
        row = col.row(align=True)
        row.operator(GTConfig.gt_switch_to_geometry_mode_idname,
                     icon='MESH_ICOSPHERE',
                     depress=not geotracker.solve_for_camera)
        row.operator(GTConfig.gt_switch_to_camera_mode_idname,
                     icon='CAMERA_DATA',
                     depress=geotracker.solve_for_camera)

    def _tracking_pinmode_button(self, settings: Any, layout: Any,
                                 context: Any) -> None:
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

    def _tracking_center_block(self, settings: Any, layout: Any) -> None:
        col = layout.column(align=True)
        row = col.row(align=True)
        row.active = settings.pinmode
        row.operator(GTConfig.gt_center_geo_idname, icon='PIVOT_BOUNDBOX')
        row = col.row(align=True)
        row.active = settings.pinmode
        row.operator(GTConfig.gt_toggle_pins_idname, icon='UNPINNED')
        row.operator(GTConfig.gt_remove_pins_idname, icon='X')

    def _tracking_track_row(self, settings: Any, layout: Any) -> None:
        row = layout.row(align=True)
        row.active = settings.pinmode
        row.scale_y = 1.2
        split = row.split(factor=0.5, align=True)
        split.operator(GTConfig.gt_track_prev_idname, text='',
                       icon='TRACKING_BACKWARDS_SINGLE')
        split.operator(GTConfig.gt_track_to_start_idname, text='',
                       icon='TRACKING_BACKWARDS')

        split = row.split(factor=0.5, align=True)
        split.operator(GTConfig.gt_track_to_end_idname, text='',
                       icon='TRACKING_FORWARDS')
        split.operator(GTConfig.gt_track_next_idname, text='',
                       icon='TRACKING_FORWARDS_SINGLE')

    def _tracking_refine_row(self, settings: Any, layout: Any) -> None:
        row = layout.row(align=True)
        row.active = settings.pinmode
        row.scale_y = 1.5
        row.operator(GTConfig.gt_refine_idname)
        row.operator(GTConfig.gt_refine_all_idname)

    def _tracking_keyframes_row(self, settings: Any, layout: Any) -> None:
        row = layout.row(align=True)
        split = row.split(factor=0.5, align=True)
        split.operator(GTConfig.gt_prev_keyframe_idname, text='',
                       icon='PREV_KEYFRAME')
        split.operator(GTConfig.gt_next_keyframe_idname, text='',
                       icon='NEXT_KEYFRAME')

        split = row.split(factor=0.5, align=True)
        split.active = settings.pinmode
        split.operator(GTConfig.gt_add_keyframe_idname, text='',
                       icon='KEY_HLT')
        split.operator(GTConfig.gt_remove_keyframe_idname, text='',
                       icon='KEY_DEHLT')

    def _tracking_remove_keys_row(self, settings: Any, layout: Any) -> None:
        active = settings.pinmode
        row = layout.row(align=True)
        part = row.split(factor=0.5, align=True)
        row = part.split(factor=0.5, align=True)
        row.active = active
        row.operator(GTConfig.gt_clear_tracking_backward_idname,
                     icon='TRACKING_CLEAR_BACKWARDS', text='')
        row.operator(GTConfig.gt_clear_tracking_between_idname, text='| Xk |')

        part = part.row(align=True)
        row = part.split(factor=0.5, align=True)
        btn = row.column(align=True)
        btn.active = active
        btn.operator(GTConfig.gt_clear_tracking_forward_idname,
                     icon='TRACKING_CLEAR_FORWARDS', text='')

        btn = row.column(align=True)
        btn.active = active
        btn.operator(GTConfig.gt_clear_tracking_menu_exec_idname,
                     text='', icon='X')

    def draw_header_preset(self, context: Any) -> None:
        layout = self.layout
        row = layout.row()
        row.active = False
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item(safe=True)
        if geotracker:
            row.label(text='Camera' if geotracker.camera_mode() else 'Geometry')
        row.operator(
            GTConfig.gt_help_tracking_idname,
            text='', icon='QUESTION', emboss=False)

    def draw(self, context: Any) -> None:
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item(safe=True)
        if not geotracker:
            return

        layout = self.layout

        self._tracking_mode_selector(settings, layout, geotracker)
        self._tracking_pinmode_button(settings, layout, context)

        if settings.pinmode:
            self._tracking_center_block(settings, layout)
            col = layout.column(align=True)
            self._tracking_track_row(settings, col)
            self._tracking_refine_row(settings, col)

        col = layout.column(align=True)
        self._tracking_keyframes_row(settings, col)
        if settings.pinmode:
            self._tracking_remove_keys_row(settings, col)

        if settings.is_calculating('TRACKING') or settings.is_calculating('REFINE'):
            _draw_calculating_indicator(layout)


class GT_PT_AppearanceSettingsPanel(AllVisible):
    bl_idname = GTConfig.gt_appearance_panel_idname
    bl_label = 'Appearance'
    bl_options = {'DEFAULT_CLOSED'}

    def _appearance_wireframe_settings(self, settings: Any, layout: Any) -> None:
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

    def _appearance_pin_settings(self, settings: Any, layout: Any) -> None:
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

    def _appearance_image_adjustment(self, settings: Any, layout: Any) -> None:
        geotracker = settings.get_current_geotracker_item(safe=True)
        if not geotracker:
            return

        box = layout.box()
        col = box.column(align=True)
        row = col.row(align=True)
        row.label(text='Background')
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

    def draw_header_preset(self, context: Any) -> None:
        layout = self.layout
        row = layout.row(align=True)
        row.active = False
        row.operator(GTConfig.gt_addon_setup_defaults_idname,
                     text='', icon='PREFERENCES', emboss=False)
        row.operator(GTConfig.gt_help_appearance_idname,
                     text='', icon='QUESTION', emboss=False)

    def draw(self, context: Any) -> None:
        layout = self.layout
        settings = get_gt_settings()
        self._appearance_wireframe_settings(settings, layout)
        self._appearance_pin_settings(settings, layout)
        self._appearance_image_adjustment(settings, layout)


class GT_PT_TexturePanel(AllVisible):
    bl_idname = GTConfig.gt_texture_panel_idname
    bl_label = 'Texture'
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header_preset(self, context: Any) -> None:
        layout = self.layout
        row = layout.row()
        row.active = False
        row.operator(GTConfig.gt_help_texture_idname,
                     text='', icon='QUESTION', emboss=False)

    def _draw_buttons(self, layout, active=True):
        settings = get_gt_settings()
        layout.label(text='Project from')
        col = layout.column(align=True)
        col.active = active
        col.scale_y = Config.btn_scale_y
        col.operator(GTConfig.gt_reproject_frame_idname)
        col.operator(GTConfig.gt_select_frames_for_bake_idname)
        col.operator(GTConfig.gt_reproject_tex_sequence_idname)

        col = layout.column(align=True)
        col.scale_y = Config.btn_scale_y
        col.label(text='UV Map')
        col.operator(GTConfig.gt_check_uv_overlapping_idname)

        col = layout.column(align=True)
        col.scale_y = Config.btn_scale_y
        col.active = not settings.pinmode
        col.operator(GTConfig.gt_repack_overlapping_uv_idname)
        col.operator(GTConfig.gt_create_non_overlapping_uv_idname)

    def _draw_no_uv_warning(self, layout):
        box = layout.box()
        box.alert = True
        row = box.split(factor=0.15, align=True)
        row.label(text='', icon='ERROR')
        col = row.column(align=True)
        col.scale_y = Config.text_scale_y
        for i, txt in enumerate(['Geometry object','has no UV map!']):
            col.label(text=txt)
        layout.operator(GTConfig.gt_create_non_overlapping_uv_idname)

    def draw(self, context: Any) -> None:
        layout = self.layout
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()

        if not geotracker or not geotracker.geomobj or \
                not geotracker.geomobj.data.uv_layers.active:
            self._draw_no_uv_warning(layout)
            return

        self._draw_buttons(layout, not not geotracker.movie_clip)

        if settings.is_calculating('REPROJECT'):
            _draw_calculating_indicator(layout)


class GT_PT_AnimationPanel(AllVisible):
    bl_idname = GTConfig.gt_animation_panel_idname
    bl_label = 'Scene'
    bl_options = {'DEFAULT_CLOSED'}

    def _draw_dist_between_camera_and_object(self, layout):
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item(safe=True)
        if geotracker and geotracker.geomobj and geotracker.camobj:
            geom_loc = geotracker.geomobj.matrix_world.to_translation()
            cam_loc = geotracker.camobj.matrix_world.to_translation()
            dist = (geom_loc - cam_loc).length
            layout.label(text=f'Dist: {dist:.3f}')

    def draw_header_preset(self, context: Any) -> None:
        layout = self.layout
        row = layout.row(align=True)
        row.active = False

        row.operator(GTConfig.gt_help_animation_idname,
                     text='', icon='QUESTION', emboss=False)

    def draw(self, context: Any) -> None:
        layout = self.layout
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()

        layout.label(text='Transform')

        col = layout.row(align=True)
        col.operator(GTConfig.gt_rescale_window_idname)

        col.operator(GTConfig.gt_move_window_idname)

        layout.operator(GTConfig.gt_rig_window_idname)

        layout.label(text='Animation')

        col = layout.column(align=True)
        col.prop(settings, 'transfer_animation_selector', text='')
        col.operator(GTConfig.gt_transfer_tracking_idname)

        layout.separator()

        col = layout.column(align=True)
        col.prop(settings, 'bake_animation_selector', text='')
        btn = col.row()
        if settings.bake_animation_selector == 'CAMERA' \
                and geotracker.camobj and geotracker.camobj.parent:
            btn.enabled = True
        elif settings.bake_animation_selector == 'GEOMETRY' \
                and geotracker.geomobj and geotracker.geomobj.parent:
            btn.enabled = True
        elif settings.bake_animation_selector == 'GEOMETRY_AND_CAMERA' \
                and geotracker.geomobj and geotracker.camobj \
                and (geotracker.geomobj.parent or geotracker.camobj.parent):
            btn.enabled = True
        else:
            btn.enabled = False
        btn.operator(GTConfig.gt_bake_animation_to_world_idname, text='Bake')

        layout.separator()

        col = layout.column(align=True)
        col.prop(settings, 'export_locator_selector', text='')
        row = col.split(factor=0.4, align=True)
        row.prop(settings, 'export_linked_locator')
        row.operator(GTConfig.gt_export_animated_empty_idname)


class GT_PT_RenderingPanel(AllVisible):
    bl_idname = GTConfig.gt_rendering_panel_idname
    bl_label = 'Rendering'
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context: Any) -> bool:
        if GTConfig.hidden_feature:
            return False
        return super().poll(context)

    def draw_header_preset(self, context: Any) -> None:
        layout = self.layout
        row = layout.row()
        row.active = False
        row.operator(
            GTConfig.gt_help_rendering_idname,
            text='', icon='QUESTION', emboss=False)

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


class GT_PT_SmoothingPanel(AllVisible):
    bl_idname = GTConfig.gt_smoothing_panel_idname
    bl_label = 'Smoothing'
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header_preset(self, context: Any) -> None:
        layout = self.layout
        row = layout.row()
        row.active = False

        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item(safe=True)
        if geotracker and \
                (geotracker.smoothing_depth_coeff != 0 or
                 geotracker.smoothing_xy_translations_coeff != 0 or
                 geotracker.smoothing_focal_length_coeff != 0 or
                 geotracker.smoothing_rotations_coeff !=0):
            row.label(text='On')

        row.operator(
            GTConfig.gt_help_smoothing_idname,
            text='', icon='QUESTION', emboss=False)

    def draw(self, context: Any) -> None:
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item(safe=True)
        if not geotracker:
            return

        layout = self.layout
        col = layout.column(align=True)
        col.prop(geotracker, 'smoothing_depth_coeff')
        col.prop(geotracker, 'smoothing_xy_translations_coeff')
        col.prop(geotracker, 'smoothing_rotations_coeff')
        col.prop(geotracker, 'smoothing_focal_length_coeff')
