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
import re

from bpy.types import Area, Panel, UIList, Menu, Operator
from bl_operators.presets import AddPresetBase
from bl_ui.utils import PresetPanel

from ...utils.kt_logging import KTLogger
from ...utils.version import BVersion
from ...addon_config import (Config,
                             ft_settings, fb_settings,
                             facetracker_enabled,
                             addon_pinmode,
                             ProductType,
                             common_loader)
from ...facebuilder_config import FBConfig
from ...facetracker_config import FTConfig
from ...geotracker_config import GTConfig
from ...blender_independent_packages.pykeentools_loader import is_installed as pkt_is_installed
from ...updater.panels import (KTUpdater,
                               COMMON_PT_UpdatePanel,
                               COMMON_PT_DownloadNotification,
                               COMMON_PT_DownloadingProblemPanel,
                               COMMON_PT_UpdatesInstallationPanel)
from ...utils.grace_timer import KTGraceTimer
from ..ftloader import FTLoader
from ...utils.bpy_common import bpy_timer_register, bpy_object_is_in_scene, bpy_data
from ...utils.materials import find_bpy_image_by_name
from ...utils.icons import KTIcons
from ...common.interface.panels import (COMMON_FB_PT_ViewsPanel,
                                        COMMON_FB_PT_OptionsPanel,
                                        COMMON_FB_PT_ModelPanel,
                                        COMMON_FB_PT_AppearancePanel)
from ...common.license_checker import ft_license_timer, draw_upgrade_license_box
from ...common.escapers import (fb_pinmode_escaper_check,
                                ft_pinmode_escaper_check,
                                start_ft_pinmode_escaper,
                                ft_calculating_escaper_check,
                                start_ft_calculating_escaper,
                                exit_from_localview_button)


_log = KTLogger(__name__)
_ft_grace_timer = KTGraceTimer(ProductType.FACETRACKER)


def _geomobj_delete_handler() -> None:
    settings = ft_settings()
    if settings.pinmode:
        FTLoader.out_pinmode()
    settings.fix_geotrackers()
    return None


def _start_geomobj_delete_handler() -> None:
    bpy_timer_register(_geomobj_delete_handler, first_interval=0.01)


def _fb_head_in_ft_mode_active() -> bool:
    return common_loader().ft_head_mode() != 'NONE'


class View3DPanel(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
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
        if common_loader().ft_head_mode() != 'NONE':
            return False
        settings = ft_settings()
        if not settings.current_tracker_num() >= 0:
            return False
        facetracker = settings.get_current_geotracker_item()
        return facetracker.geomobj and facetracker.camobj


class FT_PT_FacetrackersPanel(View3DPanel):
    bl_idname = FTConfig.ft_facetrackers_panel_idname
    bl_label = f'{FTConfig.ft_tool_name} {Config.addon_version}'

    def draw_header_preset(self, context: Any) -> None:
        layout = self.layout
        row = layout.row()
        op = row.operator(Config.kt_addon_settings_idname,
                          text='', icon='PREFERENCES', emboss=False)
        op.show = 'facetracker'

    def _facetracker_creation_button(self, layout: Any,
                                     active: bool =True) -> None:
        settings = ft_settings()
        row = layout.row(align=True)
        row.scale_y = 2.0 if len(settings.trackers()) == 0 else Config.btn_scale_y
        if settings.is_calculating():
            row.operator(FTConfig.ft_stop_calculating_idname, icon='X')
        else:
            row.enabled = active
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

        draw_upgrade_license_box(layout, ProductType.FACETRACKER)

        col = layout.column(align=True)
        col.enabled = common_loader().ft_head_mode() == 'NONE'
        self._output_geotrackers_list(col)
        self._facetracker_creation_button(col)

        exit_from_localview_button(layout, context, ProductType.FACETRACKER)
        KTUpdater.call_updater(ProductType.FACETRACKER
                               if len(ft_settings().trackers()) > 0
                               else ProductType.ADDON)
        _ft_grace_timer.start()
        ft_license_timer.start_timer()


class FT_PT_UpdatePanel(COMMON_PT_UpdatePanel):
    bl_idname = FTConfig.ft_update_panel_idname
    bl_category = Config.ft_tab_category

    @classmethod
    def poll(cls, context: Any) -> bool:
        if not facetracker_enabled():
            return False
        return KTUpdater.updates_available_state()


class FT_PT_DownloadNotification(COMMON_PT_DownloadNotification):
    bl_idname = FTConfig.ft_download_notification_panel_idname
    bl_category = Config.ft_tab_category


class FT_PT_DownloadingProblemPanel(COMMON_PT_DownloadingProblemPanel):
    bl_idname = FTConfig.ft_downloading_problem_panel_idname
    bl_category = Config.ft_tab_category


class FT_PT_UpdatesInstallationPanel(COMMON_PT_UpdatesInstallationPanel):
    bl_idname = FTConfig.ft_updates_installation_panel_idname
    bl_category = Config.ft_tab_category


def _fb_view_panel_active() -> bool:
    return common_loader().ft_head_mode() == 'EDIT_HEAD'


class FTFB_PT_ViewsPanel(COMMON_FB_PT_ViewsPanel, Panel):
    bl_category = Config.ft_tab_category
    bl_idname = FTConfig.ft_fb_views_panel_idname
    bl_label = 'FaceBuilder'

    @classmethod
    def poll(cls, context: Any) -> bool:
        if not facetracker_enabled():
            return False
        if not pkt_is_installed():
            return False
        settings = ft_settings()
        if not _fb_view_panel_active():
            return False
        if not settings.current_tracker_num() >= 0:
            return False
        facetracker = settings.get_current_geotracker_item()
        return facetracker.geomobj and facetracker.camobj

    def _back_to_button_title(self) -> str:
        return 'Back to FaceTracker'

    def _draw_add_images_button(self, headnum, layout, scale=2.0,
                                icon='OUTLINER_OB_IMAGE'):
        col = layout.column(align=True)
        col.scale_y = scale
        row = col.row(align=True)
        row.operator(FTConfig.ft_choose_frame_mode_idname,
                     text='+ snapshot', icon='FILE_MOVIE')
        op = row.operator(FBConfig.fb_multiple_filebrowser_exec_idname,
                          text='+ img file', icon='FILE_IMAGE')
        op.headnum = headnum

    def _draw_fb_trial_info(self, layout) -> None:
        draw_upgrade_license_box(layout, ProductType.FACEBUILDER)

    def call_escaper(self, context) -> None:
        if fb_pinmode_escaper_check():
            start_ft_pinmode_escaper(context)


class FTFB_PT_OptionsPanel(COMMON_FB_PT_OptionsPanel, Panel):
    bl_idname = FTConfig.ft_fb_options_panel_idname
    bl_label = 'Options'
    bl_options = {'DEFAULT_CLOSED'}
    bl_parent_id = FTConfig.ft_fb_views_panel_idname

    @classmethod
    def poll(cls, context):
        settings = fb_settings()
        if settings is None:
            return False
        if not settings.pinmode:
            return False
        return True


class FTFB_PT_ModelPanel(COMMON_FB_PT_ModelPanel, Panel):
    bl_idname = FTConfig.ft_fb_model_panel_idname
    bl_label = 'Model'
    bl_options = {'DEFAULT_CLOSED'}
    bl_parent_id = FTConfig.ft_fb_views_panel_idname

    @classmethod
    def poll(cls, context):
        return True

    def _draw_topology_enabled(self) -> bool:
        return False

    def _draw_resulting_expression_enabled(self) -> bool:
        return False


class FTFB_PT_AppearancePanel(COMMON_FB_PT_AppearancePanel, Panel):
    bl_idname = FTConfig.ft_fb_appearance_panel_idname
    bl_label = 'Appearance'
    bl_options = {'DEFAULT_CLOSED'}
    bl_parent_id = FTConfig.ft_fb_views_panel_idname

    @classmethod
    def poll(cls, context):
        return True


class FTFB_PT_ChooseSnapshotFramePanel(View3DPanel):
    bl_idname = FTConfig.ft_choose_snapshot_frame_idname
    bl_label = 'FaceBuilder'

    @classmethod
    def poll(cls, context: Any) -> bool:
        if not facetracker_enabled():
            return False
        if not pkt_is_installed():
            return False
        settings = ft_settings()
        if not settings.current_tracker_num() >= 0:
            return False
        return common_loader().ft_head_mode() == 'CHOOSE_FRAME'

    def draw(self, context: Any) -> None:
        settings = ft_settings()
        geotracker = settings.get_current_geotracker_item(safe=True)
        if not geotracker:
            return

        layout = self.layout
        col = layout.column(align=True)
        row = col.row(align=True)
        row.scale_y = 2.0
        row.operator(FTConfig.ft_add_chosen_frame_idname, icon='FILE_MOVIE')
        col.operator(FTConfig.ft_cancel_choose_frame_idname, icon='X')


class FT_PT_InputsPanel(View3DPanel):
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
        return not _fb_head_in_ft_mode_active()

    def draw_header_preset(self, context: Any) -> None:
        layout = self.layout
        row = layout.row()
        row.active = False
        row.operator(FTConfig.ft_help_inputs_idname,
                     text='', icon='QUESTION', emboss=False)

    def _draw_main_inputs(self, layout, geotracker):
        factor = 0.3
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
        split.label(text='Head')

        col = split.column(align=True)
        row = col.row(align=True)
        row.alert = not geotracker.geomobj

        split2 = row.split(factor=0.7, align=True)
        split2.prop(geotracker, 'geomobj', text='')

        if not geotracker.geomobj:
            split2.operator(FTConfig.ft_create_new_head_idname)
        else:
            split2.operator(FTConfig.ft_edit_head_idname)

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
        op = col.operator(GTConfig.gt_analyze_call_idname, text=txt)
        op.product = ProductType.FACETRACKER

    def draw(self, context: Any) -> None:
        settings = ft_settings()
        geotracker = settings.get_current_geotracker_item(safe=True)
        if not geotracker:
            return

        if geotracker.geomobj:
            if geotracker.geomobj.users == 1 or (geotracker.geomobj.users == 2
                    and not bpy_object_is_in_scene(geotracker.geomobj)):
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
            op = row.operator(GTConfig.gt_precalc_info_idname,
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


class FT_PT_CameraPanel(View3DPanel):
    bl_idname = FTConfig.ft_camera_panel_idname
    bl_label = 'Camera'
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context: Any) -> bool:
        if not facetracker_enabled():
            return False
        if not pkt_is_installed():
            return False
        settings = ft_settings()
        if not settings.current_tracker_num() >= 0:
            return False
        geotracker = settings.get_current_geotracker_item()
        return not not geotracker.camobj and not _fb_head_in_ft_mode_active()

    def _camera_lens_row(self, layout: Any, cam_data: Any) -> None:
        row = layout.row(align=True)
        row.prop(cam_data, 'lens')
        row.operator(FTConfig.ft_remove_focal_keyframe_idname,
                     text='', icon='KEY_DEHLT')
        row.operator(FTConfig.ft_remove_focal_keyframes_idname,
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
        col.operator(FTConfig.ft_help_camera_idname,
                     text='', icon='QUESTION', emboss=False)

    def draw_header_preset(self, context: Any) -> None:
        layout = self.layout

        settings = ft_settings()
        geotracker = settings.get_current_geotracker_item(safe=True)

        self._camera_header_lens_info(layout, geotracker)
        self._camera_header_help_button(layout)

    def draw(self, context: Any) -> None:
        settings = ft_settings()
        geotracker = settings.get_current_geotracker_item(safe=True)
        if not geotracker or not geotracker.camobj:
            return

        layout = self.layout
        cam_data = geotracker.camobj.data

        layout.prop(geotracker, 'focal_length_estimation')

        self._camera_lens_row(layout, cam_data)
        self._camera_sensor_size(layout, cam_data)


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
            row.label(text='Camera' if geotracker.camera_mode() else 'Head')
        row.operator(
            FTConfig.ft_help_tracking_idname,
            text='', icon='QUESTION', emboss=False)

    def _tracking_mode_selector(self, settings: Any, layout: Any,
                                geotracker: Any) -> None:
        col = layout.column(align=True)
        row = col.row(align=True)
        row.operator(FTConfig.ft_switch_to_geometry_mode_idname,
                     icon='USER',
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
            if ft_pinmode_escaper_check():
                start_ft_pinmode_escaper(context)
        else:
            op = row.operator(FTConfig.ft_pinmode_idname,
                              text='Start Pinmode', icon='HIDE_OFF',
                              depress=settings.pinmode)
            op.geotracker_num = -1

        if fb_pinmode_escaper_check():
            start_ft_pinmode_escaper(context)

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
            row = layout.row(align=True)
            row.scale_y = 1.5
            row.operator(FTConfig.ft_pickmode_starter_idname,
                         **KTIcons.key_value('align_face'))

            col = layout.column(align=True)
            self._tracking_track_row(settings, col)
            self._tracking_refine_row(settings, col)

        col = layout.column(align=True)
        self._tracking_keyframes_row(settings, col)

        if settings.pinmode:
            self._tracking_remove_keys_row(settings, col)
            self._tracking_center_block(settings, layout)

        if ft_calculating_escaper_check():
            start_ft_calculating_escaper()


class FT_PT_OptionsPanel(View3DPanel):
    bl_idname = FTConfig.ft_options_panel_idname
    bl_label = 'Options'
    bl_options = {'DEFAULT_CLOSED'}
    bl_parent_id = FTConfig.ft_tracking_panel_idname

    @classmethod
    def poll(cls, context):
        settings = ft_settings()
        if settings is None:
            return False
        if not settings.pinmode:
            return False
        return True

    def draw(self, context):
        settings = ft_settings()
        if settings is None:
            return
        layout = self.layout

        if not settings.pinmode:
            return

        geotracker = settings.get_current_geotracker_item(safe=True)
        if not geotracker:
            return

        col = layout.column(align=True)
        col.label(text='Lock movements')
        row = col.row(align=True)
        row.label(text='', icon='BLANK1')
        col2 = row.column(align=True)
        col2.prop(geotracker, 'lock_blinking')
        col2.prop(geotracker, 'lock_neck_movement')

        col = layout.column(align=True)
        col.label(text='Mesh rigidity')

        row = col.row(align=True)
        row.prop(geotracker, 'rigidity')

        if not geotracker.lock_blinking:
            row = col.row(align=True)
            row.prop(geotracker, 'blinking_rigidity')

        if not geotracker.lock_neck_movement:
            row = col.row(align=True)
            row.prop(geotracker, 'neck_movement_rigidity')


class FT_PT_MasksPanel(AllVisible):
    bl_idname = FTConfig.ft_masks_panel_idname
    bl_label = 'Masks'
    bl_options = {'DEFAULT_CLOSED'}

    def _mask_3d_block(self, layout: Any, geotracker: Any) -> None:
        if not geotracker.geomobj:
            return

        col = layout.column(align=True)
        col.label(text='Surface Mask')
        row = col.row(align=True)
        row.prop_search(geotracker, 'mask_3d',
                        geotracker.geomobj, 'vertex_groups', text='')
        row.prop(geotracker, 'mask_3d_inverted',
                 text='', icon='ARROW_LEFTRIGHT')

    def _mask_2d_block(self, layout: Any, geotracker: Any,
                       show_threshold: bool = False) -> None:
        row = layout.row(align=True)
        row.prop_search(geotracker, 'mask_2d',
                        bpy_data(), 'movieclips', text='')
        op = row.operator(GTConfig.gt_mask_sequence_filebrowser_idname,
                          text='', icon='FILEBROWSER')
        op.product = ProductType.FACETRACKER
        row.prop(geotracker, 'mask_2d_inverted',
                 text='', icon='ARROW_LEFTRIGHT')

        row = layout.row(align=True)
        row.prop(geotracker, 'mask_2d_channel_r', toggle=1)
        row.prop(geotracker, 'mask_2d_channel_g', toggle=1)
        row.prop(geotracker, 'mask_2d_channel_b', toggle=1)
        row.prop(geotracker, 'mask_2d_channel_a', toggle=1)

        if show_threshold:
            row = layout.row(align=True)
            row.prop(geotracker, 'mask_2d_threshold', slider=True)

        if geotracker.mask_2d_info == '':
            return

        arr = re.split('\r\n|\n', geotracker.mask_2d_info)
        for txt in arr:
            col = layout.column(align=True)
            col.scale_y = Config.text_scale_y
            col.label(text=txt)

    def _mask_compositing_block(self, layout: Any, geotracker: Any,
                                show_threshold: bool = False) -> None:
        col = layout.column(align=True)
        row = col.row(align=True)
        row.prop_search(geotracker, 'compositing_mask',
                        bpy_data(), 'masks', text='')
        row.prop(geotracker, 'compositing_mask_inverted',
                 text='', icon='ARROW_LEFTRIGHT')

        if show_threshold:
            row = col.row(align=True)
            row.prop(geotracker, 'compositing_mask_threshold', slider=True)

    def _mask_3d_enabled(self, geotracker: Any) -> bool:
        return geotracker and geotracker.geomobj and geotracker.mask_3d != ''

    def _mask_2d_enabled(self, geotracker: Any) -> bool:
        return geotracker and geotracker.get_2d_mask_source() != 'NONE'

    def draw_header_preset(self, context: Any) -> None:
        layout = self.layout
        row = layout.row()
        row.active = False
        settings = ft_settings()
        geotracker = settings.get_current_geotracker_item(safe=True)
        if self._mask_3d_enabled(geotracker):
            if self._mask_2d_enabled(geotracker):
                row.label(text='2D / 3D')
            else:
                row.label(text='3D')
        else:
            if self._mask_2d_enabled(geotracker):
                row.label(text='2D')
        row.operator(FTConfig.ft_help_masks_idname,
                     text='', icon='QUESTION', emboss=False)

    def draw(self, context: Any) -> None:
        settings = ft_settings()
        geotracker = settings.get_current_geotracker_item(safe=True)
        if not geotracker:
            return

        layout = self.layout
        self._mask_3d_block(layout, geotracker)

        col = layout.column(align=True)
        col.label(text='2D Mask')
        row = col.row(align=True)
        row.prop(geotracker, 'mask_2d_mode', expand=True)
        if geotracker.mask_2d_mode == 'MASK_2D':
            self._mask_2d_block(layout, geotracker)
        elif geotracker.mask_2d_mode == 'COMP_MASK':
            self._mask_compositing_block(layout, geotracker)


class FT_PT_AppearancePresetPanel(PresetPanel, Panel):
    bl_idname = FTConfig.ft_appearance_preset_panel_idname
    bl_label = 'Display Appearance Presets'
    preset_subdir = 'keentools/facetracker/appearance'
    preset_operator = 'script.execute_preset'
    preset_add_operator = FTConfig.ft_appearance_preset_add_idname
    draw = Menu.draw_preset


class FT_OT_AppearanceAddPreset(AddPresetBase, Operator):
    bl_idname = FTConfig.ft_appearance_preset_add_idname
    bl_label = 'Add Appearance Preset'
    preset_menu = FTConfig.ft_appearance_preset_panel_idname

    preset_defines = [
        f'settings = bpy.context.scene.{Config.ft_global_var_name}'
    ]
    preset_values = [
        'settings.wireframe_color',
        'settings.wireframe_midline_color',
        'settings.wireframe_special_color',
        'settings.wireframe_opacity',
        'settings.show_specials',
        'settings.wireframe_backface_culling',
        'settings.use_adaptive_opacity',
        'settings.pin_size',
        'settings.pin_sensitivity',
        'settings.mask_3d_color',
        'settings.mask_3d_opacity',
        'settings.mask_2d_color',
        'settings.mask_2d_opacity',
    ]
    preset_subdir = 'keentools/facetracker/appearance'


class FT_PT_AppearancePanel(AllVisible):
    bl_idname = FTConfig.ft_appearance_panel_idname
    bl_label = 'Appearance'
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header_preset(self, context):
        layout = self.layout
        row = layout.row(align=True)
        row.emboss = 'NONE'
        row.popover(text='', icon='PRESET',
                    panel=FTConfig.ft_appearance_preset_panel_idname)
        col = row.column(align=True)
        col.active = False
        col.operator(
            FTConfig.ft_help_appearance_idname,
            text='', icon='QUESTION', emboss=False)

    def _appearance_pin_settings(self, settings, layout) -> None:
        col = layout.column(align=True)
        row = col.row(align=True)
        row.label(text='Pins')
        btn = row.column(align=True)
        btn.active = False
        btn.operator(FTConfig.ft_default_pin_settings_idname, text='',
                     icon='LOOP_BACK', emboss=False, depress=False)
        col.separator(factor=0.4)
        col.prop(settings, 'pin_size', slider=True)
        col.prop(settings, 'pin_sensitivity', slider=True)

    def _appearance_wireframe_settings(self, settings, layout) -> None:
        col = layout.column(align=True)
        row = col.row(align=True)
        row.label(text='Wireframe')
        btn = row.column(align=True)
        btn.active = False
        btn.operator(
            FTConfig.ft_default_wireframe_settings_idname,
            text='', icon='LOOP_BACK', emboss=False, depress=False)
        col.separator(factor=0.4)
        split = col.split(factor=0.375, align=True)
        split2 = split.split(factor=0.34, align=True)
        split2.prop(settings, 'wireframe_color', text='')
        split3 = split2.split(factor=0.5, align=True)
        split3.prop(settings, 'wireframe_special_color', text='')
        split3.prop(settings, 'wireframe_midline_color', text='')
        split.prop(settings, 'wireframe_opacity', text='', slider=True)

        row = layout.row(align=True)
        op = row.operator(FTConfig.ft_wireframe_color_idname, text='R')
        op.action = 'wireframe_red'
        op = row.operator(FTConfig.ft_wireframe_color_idname, text='G')
        op.action = 'wireframe_green'
        op = row.operator(FTConfig.ft_wireframe_color_idname, text='B')
        op.action = 'wireframe_blue'
        op = row.operator(FTConfig.ft_wireframe_color_idname, text='C')
        op.action = 'wireframe_cyan'
        op = row.operator(FTConfig.ft_wireframe_color_idname, text='M')
        op.action = 'wireframe_magenta'
        op = row.operator(FTConfig.ft_wireframe_color_idname, text='Y')
        op.action = 'wireframe_yellow'
        op = row.operator(FTConfig.ft_wireframe_color_idname, text='K')
        op.action = 'wireframe_black'
        op = row.operator(FTConfig.ft_wireframe_color_idname, text='W')
        op.action = 'wireframe_white'

        col = layout.column(align=True)
        col.prop(settings, 'show_specials')
        col.prop(settings, 'wireframe_backface_culling')
        col.prop(settings, 'use_adaptive_opacity')

    def _appearance_image_adjustment(self, settings: Any, layout: Any) -> None:
        geotracker = settings.get_current_geotracker_item(safe=True)
        if not geotracker:
            return

        col = layout.column(align=True)
        row = col.row(align=True)
        row.label(text='Background')
        btn = row.column(align=True)
        btn.active = False
        op = btn.operator(GTConfig.gt_reset_tone_mapping_idname,
                          text='', icon='LOOP_BACK',
                          emboss=False, depress=False)
        op.product = ProductType.FACETRACKER
        col.separator(factor=0.4)
        col.prop(geotracker, 'tone_exposure', slider=True)
        col.prop(geotracker, 'tone_gamma', slider=True)

    def _mask_colors(self, settings: Any, layout: Any) -> None:
        factor1 = 0.3
        factor2 = 0.22
        col = layout.column(align=True)
        row = col.row(align=True)
        row.label(text='Mask color')
        btn = row.column(align=True)
        btn.active = False
        op = btn.operator(Config.kt_user_preferences_changer,
                          text='', icon='LOOP_BACK', emboss=False)
        op.action = 'revert_ft_default_mask_colors'
        col.separator(factor=0.4)

        split = col.split(factor=factor1, align=True)
        split.label(text='Surface')
        row = split.row(align=True)
        split2 = row.split(factor=factor2, align=True)
        split2.prop(settings, 'mask_3d_color', text='')
        split2.prop(settings, 'mask_3d_opacity', text='', slider=True)

        split = col.split(factor=factor1, align=True)
        split.label(text='2D')
        row = split.row(align=True)
        split2 = row.split(factor=factor2, align=True)
        split2.prop(settings, 'mask_2d_color', text='')
        split2.prop(settings, 'mask_2d_opacity', text='', slider=True)

    def draw(self, context):
        layout = self.layout
        settings = ft_settings()
        if settings is None:
            return

        self._appearance_wireframe_settings(settings, layout)
        self._appearance_pin_settings(settings, layout)
        self._mask_colors(settings, layout)
        if settings.pinmode:
            self._appearance_image_adjustment(settings, layout)


class FT_PT_SmoothingPanel(AllVisible):
    bl_idname = FTConfig.ft_smoothing_panel_idname
    bl_label = 'Smoothing'
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header_preset(self, context: Any) -> None:
        layout = self.layout
        row = layout.row()
        row.active = False

        settings = ft_settings()
        geotracker = settings.get_current_geotracker_item(safe=True)
        if geotracker and \
                (geotracker.smoothing_depth_coeff != 0 or
                 geotracker.smoothing_xy_translations_coeff != 0 or
                 geotracker.smoothing_rotations_coeff !=0 or
                 geotracker.smoothing_face_args_coeff != 0):
            row.label(text='On')

        row.operator(
            FTConfig.ft_help_smoothing_idname,
            text='', icon='QUESTION', emboss=False)

    def draw(self, context: Any) -> None:
        settings = ft_settings()
        geotracker = settings.get_current_geotracker_item(safe=True)
        if not geotracker:
            return

        layout = self.layout
        col = layout.column(align=True)
        col.label(text='Smoothing')
        col.prop(geotracker, 'smoothing_depth_coeff')
        col.prop(geotracker, 'smoothing_xy_translations_coeff')
        col.prop(geotracker, 'smoothing_rotations_coeff')
        col.prop(geotracker, 'smoothing_face_args_coeff')


def _draw_calculating_indicator(layout: Any) -> None:
    settings = ft_settings()
    row = layout.row(align=True)
    row.prop(settings, 'user_percent', text='Calculating...')
    col = row.column(align=True)
    col.alert = True
    icon = 'CANCEL' if not settings.user_interrupts else 'X'
    col.operator(FTConfig.ft_stop_calculating_idname, text='',
                 icon=icon)


class FT_PT_ScenePanel(AllVisible):
    bl_idname = FTConfig.ft_scene_panel_idname
    bl_label = 'Scene'
    bl_options = {'DEFAULT_CLOSED'}

    def _draw_dist_between_camera_and_object(self, layout):
        settings = ft_settings()
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

        row.operator(FTConfig.ft_help_animation_idname,
                     text='', icon='QUESTION', emboss=False)

    def draw(self, context: Any) -> None:
        layout = self.layout
        settings = ft_settings()
        geotracker = settings.get_current_geotracker_item()

        layout.label(text='Transform')

        col = layout.row(align=True)
        op = col.operator(GTConfig.gt_rescale_window_idname)
        op.product = ProductType.FACETRACKER

        op = col.operator(GTConfig.gt_move_window_idname)
        op.product = ProductType.FACETRACKER

        op = layout.operator(GTConfig.gt_rig_window_idname)
        op.product = ProductType.FACETRACKER

        layout.label(text='Animation')

        col = layout.column(align=True)
        col.prop(settings, 'transfer_animation_selector', text='')
        op = col.operator(GTConfig.gt_transfer_tracking_idname)
        op.product = ProductType.FACETRACKER

        layout.separator()

        op = layout.operator(GTConfig.gt_unbreak_rotation_idname)
        op.product = ProductType.FACETRACKER

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
        op = btn.operator(GTConfig.gt_bake_animation_to_world_idname,
                          text='Bake')
        op.product = ProductType.FACETRACKER


class FT_UL_selected_frame_list(UIList):
    bl_idname = FTConfig.ft_selected_frame_list_item_idname

    def draw_item(self, context, layout, data, item, icon, active_data,
                  active_propname, index):
        layout.label(text=f'frame {item.num}')
        op = layout.operator(GTConfig.gt_go_to_bake_frame_idname, text='',
                             icon='HIDE_OFF', emboss=False)
        op.num = index
        op.product = ProductType.FACETRACKER


class FT_PT_TexturePanel(AllVisible):
    bl_idname = FTConfig.ft_texture_panel_idname
    bl_label = 'Texture'
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header_preset(self, context: Any) -> None:
        layout = self.layout
        row = layout.row()
        row.active = False
        row.operator(FTConfig.ft_help_texture_idname,
                     text='', icon='QUESTION', emboss=False)

    def _draw_buttons(self, layout, active=True):
        col = layout.column(align=True)
        col.active = active
        col.scale_y = Config.btn_scale_y

        col = layout.column(align=True)
        row = col.row(align=True)
        row.scale_y = 2.0
        op = row.operator(GTConfig.gt_bake_from_selected_frames_idname,
                          icon='IMAGE')
        op.product = ProductType.FACETRACKER

        settings = ft_settings()
        geotracker = settings.get_current_geotracker_item()
        texture_exists = find_bpy_image_by_name(
            geotracker.preview_texture_name())

        if texture_exists:
            row = col.row(align=True)
            op = row.operator(GTConfig.gt_texture_file_export_idname,
                              text='Export', icon='EXPORT')
            op.product = ProductType.FACETRACKER
            op = row.operator(GTConfig.gt_delete_texture_idname,
                              text='Delete', icon='X')
            op.product = ProductType.FACETRACKER

        layout.separator()
        col = layout.column(align=True)
        col.scale_y = Config.btn_scale_y
        op = col.operator(GTConfig.gt_reproject_tex_sequence_idname)
        op.product = ProductType.FACETRACKER

    def _draw_no_uv_warning(self, layout):
        box = layout.box()
        col = box.column()
        col.alert = True
        row = col.split(factor=0.15, align=True)
        row.label(text='', icon='ERROR')
        row.label(text='Missing UVs')
        op = box.operator(GTConfig.gt_create_non_overlapping_uv_idname)
        op.product = ProductType.FACETRACKER

    def _draw_overlapping_detected(self, layout):
        box = layout.box()
        col = box.column()
        col.alert = True
        row = col.split(factor=0.15, align=True)
        row.label(text='', icon='ERROR')
        col = row.column(align=True)
        col.scale_y = Config.text_scale_y
        for i, txt in enumerate(['Overlapping UVs','detected!']):
            col.label(text=txt)

        col = box.column(align=True)
        op = col.operator(GTConfig.gt_repack_overlapping_uv_idname)
        op.product = ProductType.FACETRACKER
        op = col.operator(GTConfig.gt_create_non_overlapping_uv_idname)
        op.product = ProductType.FACETRACKER
        op = col.operator(GTConfig.gt_check_uv_overlapping_idname, text='Re-check')
        op.product = ProductType.FACETRACKER

    def draw(self, context: Any) -> None:
        layout = self.layout
        settings = ft_settings()
        geotracker = settings.get_current_geotracker_item()

        if not geotracker or not geotracker.geomobj or \
                not geotracker.geomobj.data.uv_layers.active:
            self._draw_no_uv_warning(layout)
            return

        if geotracker.overlapping_detected:
            self._draw_overlapping_detected(layout)

        col = layout.column(align=True)
        col.label(text='Add frames')
        row = col.row()
        row.template_list(
            FTConfig.ft_selected_frame_list_item_idname,
            'selected_frame_list',
            geotracker,
            'selected_frames',
            geotracker,
            'selected_frame_index',
            type='DEFAULT',
            rows=4
        )

        col2 = row.column(align=True)
        op = col2.operator(GTConfig.gt_add_bake_frame_idname,
                           text='', icon='ADD')
        op.product = ProductType.FACETRACKER
        op = col2.operator(GTConfig.gt_remove_bake_frame_idname,
                           text='', icon='REMOVE')
        op.product = ProductType.FACETRACKER
        col2.separator()
        op = col2.operator(GTConfig.gt_texture_bake_options_idname,
                           text='', icon='PREFERENCES')
        op.product = ProductType.FACETRACKER

        col.separator()
        self._draw_buttons(col, not not geotracker.movie_clip)

        if settings.is_calculating('REPROJECT'):
            _draw_calculating_indicator(layout)


class FT_PT_ExportPanel(View3DPanel):
    bl_idname = FTConfig.ft_export_panel_idname
    bl_label = 'Export'
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context: Any) -> bool:
        if not facetracker_enabled():
            return False
        if not pkt_is_installed():
            return False
        settings = ft_settings()
        if not settings.current_tracker_num() >= 0:
            return False
        if _fb_head_in_ft_mode_active():
            return False
        facetracker = settings.get_current_geotracker_item()
        if not facetracker.geomobj:
            return False
        return True

    def draw(self, context):
        layout = self.layout
        settings = ft_settings()

        layout.label(text='Facial Animation')
        col = layout.column(align=True)
        row = col.row(align=True)
        row.prop(settings, 'transfer_facial_animation_selector', expand=True)
        if settings.transfer_facial_animation_selector == 'ARKIT':
            col = layout.column(align=True)
            row = col.split(factor=0.25, align=True)
            row.label(text='Target')
            row.prop(settings, 'transfer_facial_animation_mesh', text='')
            row = col.row(align=True)
            row.enabled = not not settings.transfer_facial_animation_mesh
            row.operator(FTConfig.ft_transfer_facs_animation_idname)

            layout.operator(FTConfig.ft_save_facs_idname)
        else:
            col = layout.column(align=True)
            row = col.split(factor=0.25, align=True)
            row.label(text='Target')
            row.prop(settings, 'transfer_facial_animation_armature', text='')
            row = col.row(align=True)
            row.enabled = not not settings.transfer_facial_animation_armature
            row.operator(FTConfig.ft_transfer_animation_to_rig_idname)
            row.operator(FTConfig.ft_transfer_animation_to_rig_options_idname,
                         text='', icon='PREFERENCES')

        layout.separator(factor=0.4)
        layout.label(text='Empty')

        col = layout.column(align=True)
        col.prop(settings, 'export_locator_selector', text='')
        if settings.export_locator_selector == 'SELECTED_PINS':
            row = col.split(factor=0.4, align=True)
            row.label(text='Orientation')
            row.prop(settings, 'export_locator_orientation', text='')

        row = col.split(factor=0.4, align=True)
        row.prop(settings, 'export_linked_locator')
        op = row.operator(FTConfig.ft_export_animated_empty_idname)
        op.product = ProductType.FACETRACKER

        if BVersion.debug_logging_mode:
            layout.separator(factor=0.4)
            layout.label(text='Render wireframe')
            col = layout.column(align=True)
            op = col.operator(Config.kt_bake_wireframe_sequence_idname)
            op.product = ProductType.FACETRACKER


class FT_PT_SupportPanel(View3DPanel):
    bl_idname = FTConfig.ft_support_panel_idname
    bl_label = 'Support'

    @classmethod
    def poll(cls, context: Any) -> bool:
        if not facetracker_enabled():
            return False
        if not pkt_is_installed():
            return False
        settings = ft_settings()
        if not settings.current_tracker_num() >= 0:
            return False
        return not _fb_head_in_ft_mode_active()

    def draw(self, context):
        layout = self.layout

        col = layout.column(align=True)
        col.scale_y = Config.btn_scale_y
        op = col.operator(Config.kt_report_bug_idname, icon='ERROR')
        op.product = ProductType.FACETRACKER
        op = col.operator(Config.kt_share_feedback_idname,
                          icon='OUTLINER_OB_LIGHT')
        op.product = ProductType.FACETRACKER


ft_license_timer.start_timer()
