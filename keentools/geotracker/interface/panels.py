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
from typing import Tuple

import bpy

from ...addon_config import Config, geotracker_enabled
from ...geotracker_config import GTConfig, get_gt_settings
from ...blender_independent_packages.pykeentools_loader import is_installed as pkt_is_installed
from ...updater.panels import (KTUpdater,
                               KT_PT_UpdatePanel,
                               KT_PT_DownloadNotification,
                               KT_PT_DownloadingProblemPanel,
                               KT_PT_UpdatesInstallationPanel)


def _is_keentools_object(obj) -> bool:
    return GTConfig.version_prop_name in obj.keys()


def what_is_state() -> Tuple[str, int]:
    def _how_many_geotrackers():
        settings = get_gt_settings()
        unknown_geotracker = -1
        geotrackers_count = len(settings.geotrackers)
        if geotrackers_count == 0:
            return 'NO_GEOTRACKERS', unknown_geotracker
        elif geotrackers_count == 1:
            return 'ONE_GEOTRACKER', 0
        else:
            return 'MANY_GEOTRACKERS', unknown_geotracker

    context = bpy.context
    settings = get_gt_settings()
    unknown_geotracker = -1

    if settings.pinmode:
        return 'PINMODE', settings.current_geotracker_num

    obj = context.object

    if not obj:
        return _how_many_geotrackers()

    if not _is_keentools_object(obj):
        return _how_many_geotrackers()

    if obj.type == 'MESH':
        ind = settings.find_geotracker_index(obj)
        if ind >= 0:
            return 'THIS_GEOTRACKER', ind
        else:
            return 'RECONSTRUCT', unknown_geotracker

    elif obj.type == 'CAMERA':
        ind, _ = settings.find_cam_index(obj)
        if ind >= 0:
            return 'THIS_GEOTRACKER', ind
        else:
            return _how_many_geotrackers()

    return _how_many_geotrackers()


def show_all_panels() -> bool:
    settings = get_gt_settings()
    return settings.current_geotracker_num >= 0


class View3DPanel(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    # bl_options = {'DEFAULT_CLOSED'}
    bl_category = GTConfig.gt_tab_category

    @classmethod
    def poll(cls, context):
        return geotracker_enabled()


class AllVisible(View3DPanel):
    @classmethod
    def poll(cls, context):
        if not geotracker_enabled():
            return False
        return show_all_panels()


class GT_PT_GeotrackersPanel(View3DPanel):
    bl_idname = GTConfig.gt_geotrackers_panel_idname
    bl_label = '{} {}'.format(GTConfig.gt_tool_name,
                              Config.addon_version)

    def draw_header_preset(self, context):
        layout = self.layout
        row = layout.row()
        row.operator(
            Config.kt_addon_settings_idname,
            text='', icon='PREFERENCES')

    def _geotracker_creation_offer(self, layout):
        settings = get_gt_settings()
        if settings.pinmode:
            return
        row = layout.row()
        row.scale_y = 2.0
        row.operator(GTConfig.gt_create_geotracker_idname,
                     text='Create a new GeoTracker', icon='ADD')

    def _output_geotrackers_list(self, layout):
        settings = get_gt_settings()
        state, geotracker_num = what_is_state()

        if geotracker_num < 0:
            geotracker_num = settings.current_geotracker_num
        for i, geotracker in enumerate(settings.geotrackers):

            row = layout.row(align=True)

            if geotracker.geomobj:
                name = geotracker.geomobj.name
            else:
                name = '# Undefined'

            op = row.operator(GTConfig.gt_pinmode_idname,
                              text='', icon='HIDE_OFF')
            op.geotracker_num = i

            op = row.operator(GTConfig.gt_actor_idname, text=name,
                              depress=geotracker_num == i,
                              icon='CAMERA_DATA' if geotracker.camera_mode() else 'MESH_ICOSPHERE')
            op.action = 'select_geotracker'
            op.num = i

            if not settings.pinmode:
                op = row.operator(
                    GTConfig.gt_delete_geotracker_idname,
                    text='', icon='CANCEL')
                op.geotracker_num = i

    def _pkt_install_offer(self, layout):
        col = layout.column(align=True)
        col.scale_y = Config.text_scale_y
        col.label(text='You need to install')
        col.label(text='KeenTools Core library')
        col.label(text='before using GeoTracker.')

        row = layout.row()
        row.scale_y = 2.0
        row.operator(
            Config.kt_addon_settings_idname,
            text='Install Core library', icon='PREFERENCES')

    def draw(self, context):
        layout = self.layout
        if not pkt_is_installed():
            self._pkt_install_offer(layout)
            return

        self._output_geotrackers_list(layout)
        self._geotracker_creation_offer(layout)
        KTUpdater.call_updater('GeoTracker')


class GT_PT_UpdatePanel(KT_PT_UpdatePanel):
    bl_idname = GTConfig.gt_update_panel_idname
    bl_category = Config.gt_tab_category

    @classmethod
    def poll(cls, context):
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


class GT_PT_InputPanel(AllVisible):
    bl_idname = GTConfig.gt_input_panel_idname
    bl_label = 'Input Geometry'

    def draw(self, context):
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return

        layout = self.layout

        row = layout.row()
        row.alert = not geotracker.camobj
        row.prop(geotracker, 'camobj')

        row = layout.row()
        row.alert = not geotracker.geomobj
        row.prop(geotracker, 'geomobj')

        row = layout.row()
        row.alert = not geotracker.movie_clip
        row.prop(geotracker, 'movie_clip')

        row = layout.row(align=True)
        row.operator(GTConfig.gt_sequence_filebrowser_idname,
                     text='Open Sequence')

        if geotracker.movie_clip and geotracker.movie_clip.source == 'MOVIE':
            row.operator(GTConfig.gt_split_video_to_frames_exec_idname,
                         text='', icon='RENDER_RESULT')


class GT_PT_AnalyzePanel(AllVisible):
    bl_idname = GTConfig.gt_analyze_panel_idname
    bl_label = 'Analyze input'

    def draw(self, context):
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return

        layout = self.layout
        block = layout.column(align=True)
        block.operator(GTConfig.gt_choose_precalc_file_idname,
                        text='Set precalc file')
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
            if settings.precalc_mode:
                row = layout.row(align=True)
                row.prop(settings, 'user_percent', text='Calculation...')
                col = row.column(align=True)
                col.alert = True
                col.operator(GTConfig.gt_stop_precalc_idname, text='',
                             icon='CANCEL')
            else:
                col = layout.column(align=True)
                icon = 'ERROR' if not geotracker.movie_clip or \
                       geotracker.movie_clip.source == 'MOVIE' else 'NONE'

                op = col.operator(GTConfig.gt_actor_idname,
                                  text='Create precalc', icon=icon)
                op.action = 'create_precalc'

                row = layout.row()
                row.prop(geotracker, 'precalc_start')
                row.prop(geotracker, 'precalc_end')

class GT_PT_CameraPanel(AllVisible):
    bl_idname = GTConfig.gt_camera_panel_idname
    bl_label = 'Camera'

    def draw(self, context):
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return

        if not geotracker.camobj:
            return

        layout = self.layout

        cam_data = geotracker.camobj.data
        col = layout.column(align=True)
        col.enabled = False
        col.prop(geotracker, 'default_zoom_focal_length')
        col.prop(geotracker, 'static_focal_length')

        col = layout.column()
        col.prop(geotracker, 'focal_length_mode', text='Mode')
        row = col.row()
        row.enabled = geotracker.focal_length_mode != 'CAMERA_FOCAL_LENGTH'
        row.prop(geotracker, 'focal_length_estimation')

        row = col.row(align=True)
        row.prop(cam_data, 'lens')
        op = row.operator(GTConfig.gt_actor_idname, text='', icon='KEY_DEHLT')
        op.action = 'remove_focal_keyframe'
        op = row.operator(GTConfig.gt_actor_idname, text='', icon='CANCEL')
        op.action = 'remove_focal_keyframes'

        col = layout.column(align=True)
        col.prop(cam_data, 'sensor_width')
        col.prop(cam_data, 'sensor_height')


        col = layout.column(align=True)
        col.label(text='Track object:')
        row = col.row(align=True)
        row.prop(geotracker, 'solve_for_camera', text='Geometry', toggle=1, invert_checkbox=True)
        row.prop(geotracker, 'solve_for_camera', text='Camera', toggle=1)

        row = layout.row()
        row.scale_y = 2.0

        if settings.pinmode:
            row.operator(GTConfig.gt_exit_pinmode_idname,
                         icon='LOOP_BACK',
                         depress=settings.pinmode)
        else:
            op = row.operator(GTConfig.gt_pinmode_idname,
                              text='View', icon='HIDE_OFF',
                              depress=settings.pinmode)
            op.geotracker_num = -1


class GT_PT_TrackingPanel(AllVisible):
    bl_idname = GTConfig.gt_tracking_panel_idname
    bl_label = 'Tracking'

    def draw(self, context):
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return

        layout = self.layout
        box = layout.box()
        col = box.column()

        row = col.row()
        row.enabled = geotracker.focal_length_mode == 'ZOOM_FOCAL_LENGTH'
        row.prop(geotracker, 'track_focal_length')

        row = box.row(align=True)
        row.operator(GTConfig.gt_track_prev_idname, text=' ',
                     icon='TRACKING_BACKWARDS_SINGLE')
        row.operator(GTConfig.gt_track_to_start_idname, text=' ',
                     icon='TRACKING_BACKWARDS')
        row.operator(GTConfig.gt_track_to_end_idname, text=' ',
                     icon='TRACKING_FORWARDS')
        row.operator(GTConfig.gt_track_next_idname, text=' ',
                     icon='TRACKING_FORWARDS_SINGLE')

        row = box.row()
        row.operator(GTConfig.gt_refine_idname)
        row.operator(GTConfig.gt_refine_all_idname)

        row = box.row(align=True)
        row.operator(GTConfig.gt_clear_tracking_between_idname, text='Xk')
        row.operator(GTConfig.gt_clear_tracking_backward_idname, text='<X')
        row.operator(GTConfig.gt_clear_all_tracking_idname, text='X')
        row.operator(GTConfig.gt_clear_tracking_forward_idname, text='X>')

        layout.label(text='Keyframes')

        box = layout.box()
        row = box.row()
        row.operator(GTConfig.gt_magic_keyframe_idname)
        row.operator(GTConfig.gt_center_geo_idname)

        row = box.row()
        row.operator(GTConfig.gt_remove_pins_idname)

        col = row.column()
        col.active = False
        op = col.operator(GTConfig.gt_actor_idname,
                          text='pin/unpin')
        op.action = 'pin_unpin'

        row = box.row()
        row.operator(GTConfig.gt_toggle_pins_idname)

        box = layout.box()
        box.prop(geotracker, 'spring_pins_back')

        col = box.column()
        col.active = False
        op = col.operator(GTConfig.gt_actor_idname,
                          text='stabilize view')
        op.action = 'stabilize_view'

        row = box.row(align=True)
        row.operator(GTConfig.gt_prev_keyframe_idname, text=' ',
                     icon='PREV_KEYFRAME')
        row.operator(GTConfig.gt_next_keyframe_idname, text=' ',
                     icon='NEXT_KEYFRAME')
        row.operator(GTConfig.gt_add_keyframe_idname, text=' ',
                     icon='KEY_HLT')
        row.operator(GTConfig.gt_remove_keyframe_idname, text=' ',
                     icon='KEY_DEHLT')


class GT_PT_WireframeSettingsPanel(AllVisible):
    bl_idname = GTConfig.gt_colors_panel_idname
    bl_label = 'Appearance'

    def draw(self, context):
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

        geotracker = settings.get_current_geotracker_item()
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
        btn.operator(
            GTConfig.gt_reset_tone_mapping_idname,
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


class GT_PT_AnimationPanel(AllVisible):
    bl_idname = GTConfig.gt_animation_panel_idname
    bl_label = 'Animation'

    def draw(self, context):
        layout = self.layout
        layout.operator(GTConfig.gt_create_animated_empty_idname)
