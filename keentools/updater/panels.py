# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2019-2022  KeenTools

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

from bpy.types import Panel

from ..addon_config import Config, facebuilder_enabled, geotracker_enabled
from .utils import (KTUpdater, KTDownloadNotification, KTDownloadingProblem, KTInstallationReminder)


class Common:
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_context = 'objectmode'
    bl_category = Config.fb_tab_category

    @classmethod
    def check_tool_enabled(cls) -> bool:
        if cls.bl_category == Config.fb_tab_category:
            return facebuilder_enabled()
        elif cls.bl_category == Config.gt_tab_category:
            return geotracker_enabled()
        return False


class KT_PT_UpdatePanel(Common, Panel):
    bl_idname = Config.kt_update_panel_idname
    bl_label = 'Update available'

    @classmethod
    def poll(cls, context):
        return cls.check_tool_enabled()

    def _draw_response(self, layout):
        col = layout.column()
        col.scale_y = Config.text_scale_y

        product = self.bl_category

        for txt in KTUpdater.render_message(product=product, limit=32):
            col.label(text=txt)

        layout.operator(Config.kt_download_the_update_idname,
                        text='Download the update', icon='IMPORT')

        res = KTUpdater.get_response(product=product)
        if res is None:
            return
        layout.operator(Config.kt_remind_later_idname,
                        text='Remind tomorrow', icon='RECOVER_LAST')
        layout.operator(Config.kt_skip_version_idname,
                        text='Skip this version', icon='X')

    def draw(self, context):
        layout = self.layout
        self._draw_response(layout)


class KT_PT_DownloadNotification(Common, Panel):
    bl_idname = Config.kt_download_notification_panel_idname
    bl_label = 'Update available'

    @classmethod
    def poll(cls, context):
        if not cls.check_tool_enabled():
            return False
        return KTDownloadNotification.is_active()

    def _draw_response(self, layout):
        for txt in KTDownloadNotification.render_message():
            layout.label(text=txt)

    def draw(self, context):
        layout = self.layout
        self._draw_response(layout)


class KT_PT_DownloadingProblemPanel(Common, Panel):
    bl_idname = Config.kt_downloading_problem_panel_idname
    bl_label = 'Downloading problem'

    @classmethod
    def poll(cls, context):
        if not cls.check_tool_enabled():
            return False
        return KTDownloadingProblem.is_active()

    def _draw_response(self, layout):
        col = layout.column()
        col.scale_y = Config.text_scale_y

        for txt in KTDownloadingProblem.render_message(limit=32):
            col.label(text=txt)

        layout.operator(Config.kt_retry_download_the_update_idname,
                        text='Try again', icon='FILE_REFRESH')
        layout.operator(Config.kt_come_back_to_update_idname,
                        text='Cancel', icon='PANEL_CLOSE')

    def draw(self, context):
        layout = self.layout
        self._draw_response(layout)


class KT_PT_UpdatesInstallationPanel(Common, Panel):
    bl_idname = Config.kt_updates_installation_panel_idname
    bl_label = 'Update available'

    @classmethod
    def poll(cls, context):
        if not cls.check_tool_enabled():
            return False
        return KTInstallationReminder.is_active()

    def _draw_response(self, layout):
        col = layout.column()
        col.scale_y = Config.text_scale_y

        for txt in KTInstallationReminder.render_message():
            col.label(text=txt)

        layout.operator(Config.kt_install_updates_idname,
                        text='Install and restart', icon='FILE_REFRESH')
        layout.operator(Config.kt_remind_install_later_idname,
                        icon='RECOVER_LAST')
        layout.operator(Config.kt_skip_installation_idname,
                        text='Skip this version', icon='X')

    def draw(self, context):
        layout = self.layout
        self._draw_response(layout)
