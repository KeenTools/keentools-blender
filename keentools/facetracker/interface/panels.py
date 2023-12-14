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

from bpy.types import Area, Panel

from ...utils.kt_logging import KTLogger
from ...addon_config import Config, facetracker_enabled
from ...facetracker_config import FTConfig, get_ft_settings
from ...blender_independent_packages.pykeentools_loader import is_installed as pkt_is_installed


_log = KTLogger(__name__)


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
        settings = get_ft_settings()
        if not settings.current_geotracker_num >= 0:
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
        settings = get_ft_settings()
        row = layout.row()
        if settings.is_calculating():
            row.scale_y = Config.btn_scale_y
            row.operator(FTConfig.ft_stop_calculating_idname, icon='X')
        else:
            row.active = not settings.pinmode
            row.enabled = not settings.pinmode
            row.scale_y = 2.0 if len(settings.geotrackers) == 0 else Config.btn_scale_y
            row.operator(FTConfig.ft_create_facetracker_idname, icon='ADD')

    def _output_geotrackers_list(self, layout: Any) -> None:
        settings = get_ft_settings()
        facetracker_num = settings.current_geotracker_num

        for i, facetracker in enumerate(settings.geotrackers):

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
        # _exit_from_localview_button(layout, context)
        # KTUpdater.call_updater('GeoTracker')
        # _gt_grace_timer.start()
