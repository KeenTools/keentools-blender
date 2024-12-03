# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2019  KeenTools

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

from functools import partial
from typing import Optional, Any

from bpy.types import Panel, Area, Window, Screen, Operator, Menu
from bl_operators.presets import AddPresetBase
from bl_ui.utils import PresetPanel

from ...utils.kt_logging import KTLogger
from ...updater.panels import (COMMON_PT_UpdatePanel,
                               COMMON_PT_DownloadNotification,
                               COMMON_PT_DownloadingProblemPanel,
                               COMMON_PT_UpdatesInstallationPanel)
from ...updater.utils import KTUpdater
from ...addon_config import (Config,
                             fb_settings,
                             facebuilder_enabled,
                             ProductType)
from ...facebuilder_config import FBConfig
from ...utils.version import BVersion
from ...utils.manipulate import has_no_blendshape, has_blendshape_action
from ..utils.manipulate import what_is_state, get_obj_from_context
from ...utils.materials import find_bpy_image_by_name
from ...blender_independent_packages.pykeentools_loader import is_installed as pkt_is_installed
from ...utils.bpy_common import bpy_timer_register
from ...utils.grace_timer import KTGraceTimer
from ...utils.icons import KTIcons
from ...common.interface.panels import (COMMON_FB_PT_ViewsPanel,
                                        COMMON_FB_PT_OptionsPanel,
                                        COMMON_FB_PT_ModelPanel,
                                        COMMON_FB_PT_AppearancePanel)
from ...common.license_checker import fb_license_timer, draw_upgrade_license_box
from ...common.escapers import (start_fb_pinmode_escaper,
                                exit_from_localview_button)


_log = KTLogger(__name__)
_fb_grace_timer = KTGraceTimer(ProductType.FACEBUILDER)


def _state_valid_to_show(state: str) -> bool:
    # RECONSTRUCT, NO_HEADS, THIS_HEAD, ONE_HEAD, MANY_HEADS, PINMODE, FACS_HEAD
    return state in {'THIS_HEAD', 'ONE_HEAD', 'PINMODE'}


def _show_all_panels() -> bool:
    state, _ = what_is_state()
    return _state_valid_to_show(state)


def _show_all_panels_no_blendshapes() -> bool:
    state, headnum = what_is_state()
    if not _state_valid_to_show(state):
        return False
    settings = fb_settings()
    if settings is None:
        return False
    return settings.get_head(headnum).has_no_blendshapes()


def _draw_update_blendshapes_panel(layout: Any) -> None:
    box = layout.box()
    col = box.column()
    col.alert = True
    col.scale_y = Config.text_scale_y
    col.label(text='Mesh shape changed.')
    col.label(text='Update blendshapes')
    box.operator(FBConfig.fb_update_blendshapes_idname)


def fb_autoloader(headnum: int) -> None:
    _log.output(f'FaceBuilder autoloader started: {headnum}')
    settings = fb_settings()
    if not settings.loader().load_model(headnum):
        _log.error(f'Head autoloader failed: {headnum}')
    return None


def start_fb_autoloader(headnum: int) -> None:
    bpy_timer_register(partial(fb_autoloader, headnum), first_interval=0.01)


def poll_fb_common() -> bool:
    if not facebuilder_enabled():
        return False
    if not pkt_is_installed():
        return False
    return _show_all_panels()


class AllVisible:
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = Config.fb_tab_category
    bl_context = 'objectmode'

    @classmethod
    def poll(cls, context):
        return poll_fb_common()


class AllVisibleClosed(AllVisible):
    bl_options = {'DEFAULT_CLOSED'}


class FB_PT_HeaderPanel(AllVisible, Panel):
    bl_idname = FBConfig.fb_header_panel_idname
    bl_label = f'{FBConfig.fb_tool_name} {Config.addon_version}'

    @classmethod
    def poll(cls, context):
        return facebuilder_enabled()

    def draw_header_preset(self, context):
        layout = self.layout
        row = layout.row()
        op = row.operator(
            Config.kt_addon_settings_idname,
            text='', icon='PREFERENCES', emboss=False)
        op.show = 'facebuilder'

    def _create_head_button(self, layout, active=True):
        settings = fb_settings()
        first_head = len(settings.heads) == 0

        row = layout.row(align=True)
        row.enabled = active
        row.scale_y = 2.0 if first_head else Config.btn_scale_y
        row.operator(
            FBConfig.fb_add_head_operator_idname,
            text='Create new Head', icon='USER' if first_head else 'ADD')

    def _pkt_install_offer(self, layout):
        col = layout.column(align=True)
        col.scale_y = Config.text_scale_y
        col.label(text='You need to install')
        col.label(text='KeenTools Core library')
        col.label(text='before using FaceBuilder.')

        row = layout.row()
        row.scale_y = 2.0
        op = row.operator(
            Config.kt_addon_settings_idname,
            text='Install Core library', icon='PREFERENCES')
        op.show = 'none'

    def _draw_start_panel(self, layout):
        if not pkt_is_installed():
            self._pkt_install_offer(layout)
        else:
            self._create_head_button(layout)

    def _draw_reconstruct(self, layout):
        row = layout.row()
        row.scale_y = 3.0
        row.operator(FBConfig.fb_reconstruct_head_idname)

    def _draw_many_heads(self, layout, active=True):
        # Output List of all heads in Scene
        settings = fb_settings()
        if settings is None:
            return
        state, headnum = what_is_state()

        for i, h in enumerate(settings.heads):
            row = layout.row(align=True)
            row.scale_y = Config.btn_scale_y
            row.enabled = active

            if headnum == i:
                op = row.operator(FBConfig.fb_select_current_head_idname,
                                  text=h.headobj.name, icon='USER',
                                  depress=True)
                op.headnum = i
            else:
                op = row.operator(FBConfig.fb_select_head_idname,
                                  text=h.headobj.name, icon='USER')
                op.headnum = i

            if not settings.pinmode:
                op = row.operator(
                    FBConfig.fb_delete_head_idname,
                    text='', icon='CANCEL')
                op.headnum = i

    def draw(self, context):
        layout = self.layout

        if not pkt_is_installed():
            self._draw_start_panel(layout)
            return

        draw_upgrade_license_box(layout, ProductType.FACEBUILDER)

        state, headnum = what_is_state()
        settings = fb_settings()
        loader = settings.loader()

        if headnum >= 0 and loader.is_not_loaded():
            start_fb_autoloader(headnum)

        if state == 'PINMODE':
            # Unhide Button if Head is hidden in pinmode (by ex. after Undo)
            if not loader.viewport().viewport_is_working():
                row = layout.row()
                row.scale_y = 2.0
                row.alert = True
                row.operator(FBConfig.fb_unhide_head_idname, icon='HIDE_OFF')
                start_fb_pinmode_escaper(context)

            col = layout.column(align=True)
            self._draw_many_heads(col, active=False)
            self._create_head_button(col, active=False)
            return

        elif state == 'RECONSTRUCT':
            self._draw_reconstruct(layout)
            exit_from_localview_button(layout, context, ProductType.FACEBUILDER)
            return

        elif state == 'NO_HEADS':
            self._draw_start_panel(layout)
            KTUpdater.call_updater(ProductType.ADDON)
            _fb_grace_timer.start()
            fb_license_timer.start_timer()
            exit_from_localview_button(layout, context, ProductType.FACEBUILDER)
            return

        else:
            col = layout.column(align=True)
            self._draw_many_heads(col)
            self._create_head_button(col)
            exit_from_localview_button(layout, context, ProductType.FACEBUILDER)
            KTUpdater.call_updater(ProductType.FACEBUILDER)
            _fb_grace_timer.start()
            fb_license_timer.start_timer()


class FB_PT_UpdatePanel(COMMON_PT_UpdatePanel):
    bl_idname = FBConfig.fb_update_panel_idname
    bl_category = Config.fb_tab_category

    @classmethod
    def poll(cls, context):
        if not facebuilder_enabled():
            return False
        return KTUpdater.updates_available_state()


class FB_PT_DownloadNotification(COMMON_PT_DownloadNotification):
    bl_idname = FBConfig.fb_download_notification_panel_idname
    bl_category = Config.fb_tab_category


class FB_PT_DownloadingProblemPanel(COMMON_PT_DownloadingProblemPanel):
    bl_idname = FBConfig.fb_downloading_problem_panel_idname
    bl_category = Config.fb_tab_category


class FB_PT_UpdatesInstallationPanel(COMMON_PT_UpdatesInstallationPanel):
    bl_idname = FBConfig.fb_updates_installation_panel_idname
    bl_category = Config.fb_tab_category


class FB_PT_OptionsPanel(COMMON_FB_PT_OptionsPanel, Panel):
    bl_idname = FBConfig.fb_options_panel_idname
    bl_label = 'Options'
    bl_parent_id = FBConfig.fb_views_panel_idname

    @classmethod
    def poll(cls, context):
        settings = fb_settings()
        if settings is None:
            return False
        if not settings.pinmode:
            return False
        return True


class FB_PT_ViewsPanel(COMMON_FB_PT_ViewsPanel, Panel):
    bl_category = Config.fb_tab_category
    bl_idname = FBConfig.fb_views_panel_idname
    bl_label = 'Views'

    @classmethod
    def poll(cls, context):
        return poll_fb_common()


class FB_PT_ModelPanel(COMMON_FB_PT_ModelPanel, Panel):
    bl_category = Config.fb_tab_category
    bl_idname = FBConfig.fb_model_panel_idname
    bl_label = 'Model'
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return poll_fb_common()


class FB_PT_TexturePanel(AllVisibleClosed, Panel):
    bl_idname = FBConfig.fb_texture_panel_idname
    bl_label = 'Texture'

    def draw_header_preset(self, context):
        layout = self.layout
        row = layout.row()
        row.active = False
        row.operator(
            FBConfig.fb_help_texture_idname,
            text='', icon='QUESTION', emboss=False)

    @classmethod
    def get_area_mode(cls, context):  # TODO: Remove as unused
        area = context.area
        for space in area.spaces:
            if space.type == 'VIEW_3D':
                return space.shading.type
        return 'NONE'

    def draw(self, context):
        layout = self.layout
        obj = context.object
        settings = fb_settings()
        if settings is None:
            return
        headnum = settings.head_by_obj(obj)
        if headnum < 0:
            headnum = settings.current_headnum
        head = settings.get_head(headnum)

        layout.prop(head, 'tex_uv_shape')

        col = layout.column(align=True)
        row = col.row(align=True)
        row.scale_y = 2.0
        op = row.operator(FBConfig.fb_bake_tex_idname, icon='IMAGE')
        op.headnum = headnum

        op = row.operator(FBConfig.fb_texture_bake_options_idname,
                          text='', icon='PREFERENCES')
        op.headnum = headnum

        texture_exists = find_bpy_image_by_name(head.preview_texture_name())
        if texture_exists:
            row = col.row(align=True)
            row.scale_y = Config.btn_scale_y
            if not texture_exists:
                row.active = False
            op = row.operator(FBConfig.fb_texture_file_export_idname,
                              icon='EXPORT')
            op.headnum = headnum
            op = row.operator(FBConfig.fb_delete_texture_idname,
                              icon='X')
            op.headnum = headnum


class FB_PT_AppearancePresetPanel(PresetPanel, Panel):
    bl_idname = FBConfig.fb_appearance_preset_panel_idname
    bl_label = 'Display Appearance Presets'
    preset_subdir = 'keentools/facebuilder/appearance'
    preset_operator = 'script.execute_preset'
    preset_add_operator = FBConfig.fb_appearance_preset_add_idname
    draw = Menu.draw_preset


class FB_OT_AppearanceAddPreset(AddPresetBase, Operator):
    bl_idname = FBConfig.fb_appearance_preset_add_idname
    bl_label = 'Add Appearance Preset'
    preset_menu = FBConfig.fb_appearance_preset_panel_idname

    preset_defines = [
        f'settings = bpy.context.scene.{Config.fb_global_var_name}'
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
    ]
    preset_subdir = 'keentools/facebuilder/appearance'


class FB_PT_AppearancePanel(COMMON_FB_PT_AppearancePanel, Panel):
    bl_category = Config.fb_tab_category
    bl_idname = FBConfig.fb_appearance_panel_idname
    bl_label = 'Appearance'
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return poll_fb_common()


class FB_PT_BlendShapesPanel(AllVisibleClosed, Panel):
    bl_idname = FBConfig.fb_blendshapes_panel_idname
    bl_label = 'ARKit Blendshapes'

    @classmethod
    def poll(cls, context):
        if not facebuilder_enabled():
            return False
        if not pkt_is_installed():
            return False
        state, _ = what_is_state()
        return _state_valid_to_show(state) or state == 'FACS_HEAD'

    def draw_header_preset(self, context):
        layout = self.layout
        row = layout.row()
        row.active = False
        row.operator(
            FBConfig.fb_help_blendshapes_idname,
            text='', icon='QUESTION', emboss=False)

    def draw(self, context):
        layout = self.layout

        obj, scale = get_obj_from_context(context, force_fbloader=False)
        if not obj:
            return

        no_blendshapes = has_no_blendshape(obj)
        has_blendshapes_act = has_blendshape_action(obj)

        col = layout.column(align=True)
        col.scale_y = Config.btn_scale_y
        col.operator(FBConfig.fb_create_blendshapes_idname)

        if not no_blendshapes:
            row = col.row(align=True)
            op = row.operator(FBConfig.fb_delete_blendshapes_idname)
            op.active_button = not no_blendshapes

        if not no_blendshapes:
            col.operator(FBConfig.fb_reset_blendshape_values_idname)

        if not no_blendshapes:
            col = layout.column(align=True)
            col.scale_y = Config.btn_scale_y
            col.label(text='Animation')
            col.separator(factor=0.4)

            col.operator(FBConfig.fb_load_animation_from_csv_idname)

            if not has_blendshapes_act:
                row = col.row(align=True)
                op = row.operator(FBConfig.fb_create_example_animation_idname)
                op.active_button = not has_blendshapes_act

            if has_blendshapes_act:
                row = col.row(align=True)
                op = row.operator(FBConfig.fb_clear_animation_idname)
                op.active_button = has_blendshapes_act


class FB_PT_ExportPanel(AllVisibleClosed, Panel):
    bl_idname = FBConfig.fb_export_panel_idname
    bl_label = 'Export'

    @classmethod
    def poll(cls, context):
        if not facebuilder_enabled():
            return False
        if not pkt_is_installed():
            return False
        state, _ = what_is_state()
        return _state_valid_to_show(state) or state == 'FACS_HEAD'

    def draw_header_preset(self, context):
        layout = self.layout
        row = layout.row()
        row.active = False
        row.operator(
            FBConfig.fb_help_export_idname,
            text='', icon='QUESTION', emboss=False)

    def draw(self, context):
        layout = self.layout

        col = layout.column(align=True)
        col.scale_y = Config.btn_scale_y
        col.operator(FBConfig.fb_export_head_to_fbx_idname)

        if BVersion.demo_mode or (Config.integration_enabled and BVersion.os_name == 'windows'):
            col.operator(FBConfig.fb_export_to_cc_idname)


class FB_PT_SupportPanel(AllVisible, Panel):
    bl_idname = FBConfig.fb_support_panel_idname
    bl_label = 'Support'

    @classmethod
    def poll(cls, context):
        if not facebuilder_enabled():
            return False
        if not pkt_is_installed():
            return False
        return _show_all_panels()

    def draw(self, context):
        layout = self.layout

        col = layout.column(align=True)
        col.scale_y = Config.btn_scale_y
        op = col.operator(Config.kt_report_bug_idname, icon='ERROR')
        op.product = ProductType.FACEBUILDER
        op = col.operator(Config.kt_share_feedback_idname,
                          icon='OUTLINER_OB_LIGHT')
        op.product = ProductType.FACEBUILDER


fb_license_timer.start_timer()


CLASSES_TO_REGISTER = (FB_PT_HeaderPanel,
                       FB_PT_UpdatePanel,
                       FB_PT_DownloadNotification,
                       FB_PT_DownloadingProblemPanel,
                       FB_PT_UpdatesInstallationPanel,
                       FB_PT_ViewsPanel,
                       FB_PT_OptionsPanel,
                       FB_PT_ModelPanel,
                       FB_OT_AppearanceAddPreset,
                       FB_PT_AppearancePresetPanel,
                       FB_PT_AppearancePanel,
                       FB_PT_TexturePanel,
                       FB_PT_BlendShapesPanel,
                       FB_PT_ExportPanel,
                       FB_PT_SupportPanel)
