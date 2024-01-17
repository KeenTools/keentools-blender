# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2023 KeenTools

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

from typing import Any
from functools import partial

from bpy.types import Area, Panel

from ...utils.kt_logging import KTLogger
from ...addon_config import (Config,
                             ft_settings,
                             facetracker_enabled,
                             addon_pinmode,
                             ProductType)
from ...facetracker_config import FTConfig
from ...blender_independent_packages.pykeentools_loader import is_installed as pkt_is_installed
from ...updater.panels import KTUpdater
from ...utils.localview import check_context_localview, exit_area_localview
from ...utils.viewport_state import force_show_ui_overlays
from ...utils.grace_timer import KTGraceTimer
from ..ftloader import FTLoader
from ...utils.bpy_common import bpy_timer_register


_log = KTLogger(__name__)
_ft_grace_timer = KTGraceTimer(ProductType.FACETRACKER)


def _pinmode_escaper(area: Area) -> None:
    _log.error('_pinmode_escaper call')
    FTLoader.out_pinmode()
    exit_area_localview(area)
    force_show_ui_overlays(area)
    return None


def _exit_from_localview_button(layout, context):
    if addon_pinmode() or not check_context_localview(context):
        return
    settings = ft_settings()
    if settings.is_calculating():
        return
    col = layout.column()
    col.alert = True
    col.scale_y = 2.0
    col.operator(Config.kt_exit_localview_idname)


def _start_calculating_escaper() -> None:
    settings = ft_settings()
    mode = settings.calculating_mode
    if mode == 'TRACKING' or mode == 'REFINE':
        bpy_timer_register(_calculating_escaper, first_interval=0.01)


def _start_pinmode_escaper(context: Any) -> None:
    if context.area:
        bpy_timer_register(partial(_pinmode_escaper, context.area),
                           first_interval=0.01)


def _calculating_escaper() -> None:
    _log.error('_calculating_escaper call')
    settings = ft_settings()
    settings.stop_calculating()
    settings.user_interrupts = True


def _geomobj_delete_handler() -> None:
    settings = ft_settings()
    if settings.pinmode:
        FTLoader.out_pinmode()
    settings.fix_geotrackers()
    return None


def _start_geomobj_delete_handler() -> None:
    bpy_timer_register(_geomobj_delete_handler, first_interval=0.01)


class View3DPanel(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    # bl_options = {'DEFAULT_CLOSED'}
    bl_category = FTConfig.ft_tab_category

    @classmethod
    def poll(cls, context: Any) -> bool:
        return facetracker_enabled()


class AllVisible(View3DPanel):
    @classmethod
    def poll(cls, context: Any) -> bool:
        if not facetracker_enabled():
            return False
        if not pkt_is_installed():
            return False
        settings = ft_settings()
        if not settings.current_tracker_num() >= 0:
            return False
        facetracker = settings.get_current_geotracker_item()
        return facetracker.geomobj and facetracker.camobj


class FT_PT_FacetrackersPanel(View3DPanel):
    bl_idname = FTConfig.ft_facetrackers_panel_idname
    bl_label = '{} {}'.format(FTConfig.ft_tool_name,
                              Config.addon_version)

    def draw_header_preset(self, context: Any) -> None:
        layout = self.layout
        row = layout.row()
        op = row.operator(Config.kt_addon_settings_idname,
                          text='', icon='PREFERENCES', emboss=False)
        op.show = 'facetracker'

    def _facetracker_creation_offer(self, layout: Any) -> None:
        settings = ft_settings()
        row = layout.row()
        if settings.is_calculating():
            row.scale_y = Config.btn_scale_y
            row.operator(FTConfig.ft_stop_calculating_idname, icon='X')
        else:
            row.active = not settings.pinmode
            row.enabled = not settings.pinmode
            row.scale_y = 2.0 if len(settings.trackers()) == 0 else Config.btn_scale_y
            row.operator(FTConfig.ft_create_facetracker_idname, icon='ADD')

    def _output_geotrackers_list(self, layout: Any) -> None:
        settings = ft_settings()
        facetracker_num = settings.current_tracker_num()

        for i, facetracker in enumerate(settings.trackers()):

            row = layout.row(align=True)
            row.scale_y = Config.btn_scale_y

            name = facetracker.animatable_object_name()

            if settings.pinmode and facetracker_num == i:
                row.operator(FTConfig.ft_exit_pinmode_idname,
                             text='', icon='HIDE_OFF', depress=True)
            else:
                op = row.operator(FTConfig.ft_pinmode_idname,
                                  text='', icon='HIDE_OFF', depress=False)
                op.geotracker_num = i

            if not settings.pinmode:
                op = row.operator(
                    FTConfig.ft_select_facetracker_objects_idname, text=name,
                    depress=facetracker_num == i,
                    icon='CAMERA_DATA' if facetracker.camera_mode()
                    else 'USER')
                op.geotracker_num = i
            else:
                if facetracker_num == i:
                    row.operator(FTConfig.ft_exit_pinmode_idname,
                                 text=name, depress=True,
                                 icon='CAMERA_DATA' if facetracker.camera_mode()
                                 else 'USER')
                else:
                    op = row.operator(FTConfig.ft_pinmode_idname,
                                      text=name, depress=False,
                                      icon='CAMERA_DATA' if facetracker.camera_mode()
                                      else 'USER')
                    op.geotracker_num = i

            if not settings.pinmode:
                op = row.operator(FTConfig.ft_delete_facetracker_idname,
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
        self._facetracker_creation_offer(layout)
        _exit_from_localview_button(layout, context)
        KTUpdater.call_updater('FaceTracker')
        _ft_grace_timer.start()


class FT_PT_InputsPanel(AllVisible):
    bl_idname = FTConfig.ft_input_panel_idname
    bl_label = 'Inputs'

    @classmethod
    def poll(cls, context: Any) -> bool:
        if not facetracker_enabled():
            return False
        if not pkt_is_installed():
            return False
        settings = ft_settings()
        if not settings.current_tracker_num() >= 0:
            return False
        return True

    def draw_header_preset(self, context: Any) -> None:
        layout = self.layout
        row = layout.row()
        row.active = False
        row.operator(FTConfig.ft_help_inputs_idname,
                     text='', icon='QUESTION', emboss=False)

    def _draw_main_inputs(self, layout, geotracker):
        factor = 0.35
        split = layout.split(factor=factor, align=True)
        split.label(text='Clip')

        col = split.column(align=True)
        row = col.row(align=True)
        row.alert = not geotracker.movie_clip
        row.prop(geotracker, 'movie_clip', text='')

        if geotracker.movie_clip:
            row.menu(FTConfig.ft_clip_menu_idname, text='', icon='COLLAPSEMENU')
            col2 = col.column(align=True)
            col2.active = False
            col2.prop(geotracker.movie_clip.colorspace_settings, 'name',
                      text='')
        else:
            op = row.operator(FTConfig.ft_sequence_filebrowser_idname,
                              text='', icon='FILEBROWSER')
            op.product = ProductType.FACETRACKER

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
        op = col.operator(FTConfig.ft_analyze_call_idname, text=txt)
        op.product = ProductType.FACETRACKER

    def draw(self, context: Any) -> None:
        settings = ft_settings()
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
        op = row.operator(FTConfig.ft_choose_precalc_file_idname,
                          text='', icon='FILEBROWSER')
        op.product = ProductType.FACETRACKER

        if not precalc_path_is_empty:
            op = row.operator(FTConfig.ft_precalc_info_idname,
                              text='', icon='INFO')
            op.product = ProductType.FACETRACKER
        else:
            if not no_movie_clip:
                row.operator(FTConfig.ft_auto_name_precalc_idname,
                             text='', icon='FILE_HIDDEN')

        if settings.is_calculating('PRECALC'):
            col2 = col.column()
            col2.operator(FTConfig.ft_stop_calculating_idname,
                          text='Cancel', icon='X')
        else:
            self._draw_analyze_btn(col, geotracker)


class FT_PT_TrackingPanel(AllVisible):
    bl_idname = FTConfig.ft_tracking_panel_idname
    bl_label = 'Tracking'

    def draw_header_preset(self, context: Any) -> None:
        layout = self.layout
        row = layout.row()
        row.active = False
        settings = ft_settings()
        geotracker = settings.get_current_geotracker_item(safe=True)
        if geotracker:
            row.label(text='Camera' if geotracker.camera_mode() else 'Geometry')
        row.operator(
            FTConfig.ft_help_tracking_idname,
            text='', icon='QUESTION', emboss=False)

    def _tracking_mode_selector(self, settings: Any, layout: Any,
                                geotracker: Any) -> None:
        col = layout.column(align=True)
        row = col.row(align=True)
        row.operator(FTConfig.ft_switch_to_geometry_mode_idname,
                     icon='MESH_ICOSPHERE',
                     depress=not geotracker.solve_for_camera)
        row.operator(FTConfig.ft_switch_to_camera_mode_idname,
                     icon='CAMERA_DATA',
                     depress=geotracker.solve_for_camera)

    def _tracking_pinmode_button(self, settings: Any, layout: Any,
                                 context: Any) -> None:
        row = layout.row()
        row.scale_y = 2.0
        if settings.pinmode:
            row.operator(FTConfig.ft_exit_pinmode_idname,
                         icon='LOOP_BACK',
                         depress=settings.pinmode)
            if not FTLoader.viewport().is_working():
                _start_pinmode_escaper(context)
        else:
            op = row.operator(FTConfig.ft_pinmode_idname,
                              text='Start Pinmode', icon='HIDE_OFF',
                              depress=settings.pinmode)
            op.geotracker_num = -1

    def _tracking_center_block(self, settings: Any, layout: Any) -> None:
        col = layout.column(align=True)

        col.prop(settings, 'stabilize_viewport_enabled',
                 icon='LOCKED' if settings.stabilize_viewport_enabled else 'UNLOCKED')

        row = col.row(align=True)
        row.operator(FTConfig.ft_toggle_pins_idname, icon='UNPINNED')
        row.operator(FTConfig.ft_remove_pins_idname)
        col.operator(FTConfig.ft_center_geo_idname, icon='PIVOT_BOUNDBOX')

    def _tracking_track_row(self, settings: Any, layout: Any) -> None:
        row = layout.row(align=True)
        row.active = settings.pinmode
        row.scale_y = 1.2

        if settings.is_calculating('TRACKING'):
            split = row.split(factor=0.24, align=True)
            split.operator(FTConfig.ft_track_prev_idname, text='',
                           icon='TRACKING_BACKWARDS_SINGLE')

            split2 = split.split(factor=0.6666, align=True)
            split2.operator(FTConfig.ft_stop_calculating_idname, text='',
                            icon='PAUSE')

            split2.operator(FTConfig.ft_track_next_idname, text='',
                            icon='TRACKING_FORWARDS_SINGLE')
        else:
            split = row.split(factor=0.5, align=True)
            split.operator(FTConfig.ft_track_prev_idname, text='',
                           icon='TRACKING_BACKWARDS_SINGLE')

            split.operator(FTConfig.ft_track_to_start_idname, text='',
                           icon='TRACKING_BACKWARDS')

            split = row.split(factor=0.5, align=True)
            split.operator(FTConfig.ft_track_to_end_idname, text='',
                           icon='TRACKING_FORWARDS')
            split.operator(FTConfig.ft_track_next_idname, text='',
                           icon='TRACKING_FORWARDS_SINGLE')

    def _tracking_refine_row(self, settings: Any, layout: Any) -> None:
        row = layout.row(align=True)
        row.active = settings.pinmode
        row.scale_y = 1.5
        if settings.is_calculating('REFINE'):
            row.operator(FTConfig.ft_stop_calculating_idname,
                         text='Cancel', icon='X')
        else:
            row.operator(FTConfig.ft_refine_idname)
            row.operator(FTConfig.ft_refine_all_idname)

    def _tracking_keyframes_row(self, settings: Any, layout: Any) -> None:
        row = layout.row(align=True)
        split = row.split(factor=0.5, align=True)
        split.operator(FTConfig.ft_prev_keyframe_idname, text='',
                       icon='PREV_KEYFRAME')
        split.operator(FTConfig.ft_next_keyframe_idname, text='',
                       icon='NEXT_KEYFRAME')

        split = row.split(factor=0.5, align=True)
        split.active = settings.pinmode
        split.operator(FTConfig.ft_add_keyframe_idname, text='',
                       icon='KEY_HLT')
        split.operator(FTConfig.ft_remove_keyframe_idname, text='',
                       icon='KEY_DEHLT')

    def _tracking_remove_keys_row(self, settings: Any, layout: Any) -> None:
        active = settings.pinmode
        row = layout.row(align=True)
        part = row.split(factor=0.5, align=True)
        row = part.split(factor=0.5, align=True)
        row.active = active
        row.operator(FTConfig.ft_clear_tracking_backward_idname,
                     icon='TRACKING_CLEAR_BACKWARDS', text='')
        row.operator(FTConfig.ft_clear_tracking_between_idname, text='| Xk |')

        part = part.row(align=True)
        row = part.split(factor=0.5, align=True)
        btn = row.column(align=True)
        btn.active = active
        btn.operator(FTConfig.ft_clear_tracking_forward_idname,
                     icon='TRACKING_CLEAR_FORWARDS', text='')

        btn = row.column(align=True)
        btn.active = active
        btn.operator(FTConfig.ft_clear_tracking_menu_exec_idname,
                     text='', icon='X')

    def draw(self, context: Any) -> None:
        settings = ft_settings()
        geotracker = settings.get_current_geotracker_item(safe=True)
        if not geotracker:
            return

        layout = self.layout

        self._tracking_mode_selector(settings, layout, geotracker)
        self._tracking_pinmode_button(settings, layout, context)

        if settings.pinmode:
            col = layout.column(align=True)
            self._tracking_track_row(settings, col)
            self._tracking_refine_row(settings, col)
        else:
            if settings.is_calculating():
                _start_calculating_escaper()

        col = layout.column(align=True)
        self._tracking_keyframes_row(settings, col)

        if settings.pinmode:
            self._tracking_remove_keys_row(settings, col)
            self._tracking_center_block(settings, layout)
