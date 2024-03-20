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
from typing import Optional

from bpy.types import Panel, Area, Window, Screen

from ...utils.kt_logging import KTLogger
from ...updater.panels import (KT_PT_UpdatePanel,
                               KT_PT_DownloadNotification,
                               KT_PT_DownloadingProblemPanel,
                               KT_PT_UpdatesInstallationPanel)
from ...updater.utils import KTUpdater
from ...addon_config import (Config,
                             fb_settings,
                             facebuilder_enabled,
                             addon_pinmode,
                             ProductType)
from ...facebuilder_config import FBConfig
from ...utils.version import BVersion
from ..fbloader import FBLoader
from ...utils.manipulate import has_no_blendshape, has_blendshapes_action
from ..utils.manipulate import what_is_state, get_obj_from_context
from ...utils.materials import find_bpy_image_by_name
from ...blender_independent_packages.pykeentools_loader import is_installed as pkt_is_installed
from ...utils.localview import exit_area_localview, check_context_localview
from ...utils.bpy_common import bpy_timer_register
from ...utils.grace_timer import KTGraceTimer
from ...utils.icons import KTIcons


_log = KTLogger(__name__)


_fb_grace_timer = KTGraceTimer(ProductType.FACEBUILDER)


def _state_valid_to_show(state):
    # RECONSTRUCT, NO_HEADS, THIS_HEAD, ONE_HEAD, MANY_HEADS, PINMODE, FACS_HEAD
    return state in {'THIS_HEAD', 'ONE_HEAD', 'PINMODE'}


def _show_all_panels():
    if not pkt_is_installed():
        return False
    state, _ = what_is_state()
    return _state_valid_to_show(state)


def _show_all_panels_no_blendshapes():
    if not pkt_is_installed():
        return False
    state, headnum = what_is_state()
    if not _state_valid_to_show(state):
        return False
    settings = fb_settings()
    if settings is None:
        return False
    return settings.get_head(headnum).has_no_blendshapes()


def _draw_update_blendshapes_panel(layout):
    box = layout.box()
    col = box.column()
    col.alert = True
    col.scale_y = Config.text_scale_y
    col.label(text='Mesh shape changed.')
    col.label(text='Update blendshapes')
    box.operator(FBConfig.fb_update_blendshapes_idname)


def _pinmode_escaper(area: Area, window: Optional[Window],
                     screen: Optional[Screen]) -> None:
    settings = fb_settings()
    exit_area_localview(area, window, screen)
    settings.pinmode = False
    settings.viewport_state.show_ui_elements(area)
    return None


def _start_pinmode_escaper(context):
    _log.output(f'_start_pinmode_escaper: area={context.area}')
    bpy_timer_register(partial(_pinmode_escaper, context.area, context.window,
                               context.screen), first_interval=0.01)


def _exit_from_localview_button(layout, context):
    if not addon_pinmode() and check_context_localview(context):
        col = layout.column()
        col.alert = True
        col.scale_y = 2.0
        col.operator(Config.kt_exit_localview_idname)


def _geomobj_delete_handler() -> None:
    settings = fb_settings()
    settings.force_out_pinmode = True
    return None


def _start_geomobj_delete_handler() -> None:
    bpy_timer_register(_geomobj_delete_handler, first_interval=0.01)


def _autoloader_handler(headnum: int) -> None:
    _log.output(f'Head autoloader started: {headnum}')
    if not FBLoader.load_model(headnum):
        _log.error(f'Head autoloader failed: {headnum}')
    return None


def _start_autoloader_handler(headnum: int) -> None:
    bpy_timer_register(partial(_autoloader_handler, headnum), first_interval=0.01)


def _draw_align_button(layout, scale=2.0, depress=False):
    settings = fb_settings()
    row = layout.row(align=True)
    row.scale_y = scale
    row.operator(FBConfig.fb_rotate_head_backward_idname,
                 **KTIcons.key_value('rotate_head_backward'), text='')

    op = row.operator(FBConfig.fb_pickmode_starter_idname,
                      **KTIcons.key_value('align_face'), depress=depress,
                      text='Auto Align      ')  # 6 Extra spaces are for layout!
    op.headnum = settings.current_headnum
    op.camnum = settings.current_camnum
    op.auto_detect_single = False

    row.operator(FBConfig.fb_rotate_head_forward_idname,
                 **KTIcons.key_value('rotate_head_forward'), text='')


def _draw_pins_panel(layout):
    settings = fb_settings()
    if settings is None:
        return
    headnum, camnum = settings.current_headnum, settings.current_camnum
    col = layout.column(align=True)
    col.scale_y = Config.btn_scale_y

    if settings.get_head(headnum).should_use_emotions():
        op = col.operator(FBConfig.fb_reset_expression_idname)
        op.headnum = headnum
        op.camnum = camnum

    op = col.operator(FBConfig.fb_center_geo_idname)
    op.headnum = headnum
    op.camnum = camnum

    op = col.operator(FBConfig.fb_remove_pins_idname)
    op.headnum = headnum
    op.camnum = camnum


def _draw_camera_info(layout):
    settings = fb_settings()
    camera = settings.get_camera(settings.current_headnum,
                                 settings.current_camnum)
    if camera is None:
        return

    row = layout.row(align=True)
    row.prop(camera, 'auto_focal_estimation')

    row = layout.row(align=True)
    row.active = not camera.auto_focal_estimation
    row.prop(camera, 'focal')
    row.operator(FBConfig.fb_image_info_idname, text='', icon='INFO')


def _draw_expression_settings(layout, head):
    if not head.should_use_emotions():
        return
    row = layout.row(align=True)
    row.label(text='', icon='BLANK1')
    col = row.column(align=True)
    col.prop(head, 'lock_blinking')
    col.prop(head, 'lock_neck_movement')


class Common:
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = Config.fb_tab_category
    bl_context = 'objectmode'

    @classmethod
    def poll(cls, context):
        return facebuilder_enabled()


class CommonClosed(Common):
    bl_options = {'DEFAULT_CLOSED'}


class AllVisible(Common):
    @classmethod
    def poll(cls, context):
        if not facebuilder_enabled():
            return False
        return _show_all_panels()


class AllVisibleClosed(AllVisible):
    bl_options = {'DEFAULT_CLOSED'}


class FB_PT_HeaderPanel(Common, Panel):
    bl_idname = FBConfig.fb_header_panel_idname
    bl_label = '{} {}'.format(
            FBConfig.fb_tool_name, Config.addon_version)

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

        state, headnum = what_is_state()

        if headnum >= 0 and FBLoader.is_not_loaded():
            _start_autoloader_handler(headnum)

        if state == 'PINMODE':
            # Unhide Button if Head is hidden in pinmode (by ex. after Undo)
            if not FBLoader.viewport().wireframer().is_working():
                row = layout.row()
                row.scale_y = 2.0
                row.alert = True
                row.operator(FBConfig.fb_unhide_head_idname, icon='HIDE_OFF')
                _start_pinmode_escaper(context)

            col = layout.column(align=True)
            self._draw_many_heads(col, active=False)
            self._create_head_button(col, active=False)
            return

        elif state == 'RECONSTRUCT':
            self._draw_reconstruct(layout)
            _exit_from_localview_button(layout, context)
            return

        elif state == 'NO_HEADS':
            self._draw_start_panel(layout)
            KTUpdater.call_updater('FaceBuilder')
            _fb_grace_timer.start()
            _exit_from_localview_button(layout, context)
            return

        else:
            col = layout.column(align=True)
            self._draw_many_heads(col)
            self._create_head_button(col)
            _exit_from_localview_button(layout, context)
            KTUpdater.call_updater('FaceBuilder')
            _fb_grace_timer.start()


class FB_PT_UpdatePanel(KT_PT_UpdatePanel):
    bl_idname = FBConfig.fb_update_panel_idname
    bl_category = Config.fb_tab_category

    @classmethod
    def poll(cls, context):
        if not facebuilder_enabled():
            return False
        return KTUpdater.is_active()


class FB_PT_DownloadNotification(KT_PT_DownloadNotification):
    bl_idname = FBConfig.fb_download_notification_panel_idname
    bl_category = Config.fb_tab_category


class FB_PT_DownloadingProblemPanel(KT_PT_DownloadingProblemPanel):
    bl_idname = FBConfig.fb_downloading_problem_panel_idname
    bl_category = Config.fb_tab_category


class FB_PT_UpdatesInstallationPanel(KT_PT_UpdatesInstallationPanel):
    bl_idname = FBConfig.fb_updates_installation_panel_idname
    bl_category = Config.fb_tab_category


class FB_PT_OptionsPanel(AllVisible, Panel):
    bl_idname = FBConfig.fb_options_panel_idname
    bl_label = 'Options'
    bl_options = {'DEFAULT_CLOSED'}
    bl_parent_id = FBConfig.fb_views_panel_idname

    @classmethod
    def poll(cls, context):
        settings = fb_settings()
        if settings is None:
            return False
        if not settings.pinmode:
            return False
        return True

    def draw(self, context):
        settings = fb_settings()
        if settings is None:
            return
        layout = self.layout

        if not settings.pinmode:
            return

        head = settings.get_head(settings.current_headnum)
        if not head:
            return

        if settings.pinmode:
            _draw_camera_info(layout)

        col = layout.column(align=True)
        col.label(text='Mesh rigidity')

        row = col.row(align=True)
        row.enabled = settings.pinmode
        row.prop(settings, 'shape_rigidity', text='Shape')

        if head.should_use_emotions():
            row = col.row(align=True)
            row.prop(settings, 'expression_rigidity', text='Expressions')
            row.enabled = head.should_use_emotions()

        if not head.lock_blinking and head.should_use_emotions():
            row = col.row(align=True)
            row.prop(settings, 'blinking_rigidity', text='Eyelids')
            row.enabled = not head.lock_blinking and head.should_use_emotions()

        if not head.lock_neck_movement and head.should_use_emotions():
            row =  col.row(align=True)
            row.prop(settings, 'neck_movement_rigidity', text='Neck')
            row.enabled = not head.lock_neck_movement and head.should_use_emotions()


class FB_PT_ViewsPanel(AllVisible, Panel):
    bl_idname = FBConfig.fb_views_panel_idname
    bl_label = 'Views'

    def draw_header_preset(self, context):
        layout = self.layout
        row = layout.row()
        row.active = False
        row.operator(
            FBConfig.fb_help_views_idname,
            text='', icon='QUESTION', emboss=False)

    def _draw_camera_list(self, headnum, layout):
        settings = fb_settings()
        if settings is None:
            return
        head = settings.get_head(headnum)

        if head is not None and not head.has_cameras():
            self._draw_add_images_button(headnum, layout, scale=2.0)
            return

        col = layout.column(align=True)
        col.prop(head, 'use_emotions')
        _draw_expression_settings(col, head)

        common_col = layout.column(align=True)
        for i, camera in enumerate(head.cameras):
            row = common_col.row(align=True)
            row.scale_y = Config.btn_scale_y
            view_icon = 'PINNED' if camera.has_pins() else 'HIDE_OFF'

            if settings.current_camnum == i and settings.pinmode:
                row.operator(FBConfig.fb_select_current_camera_idname,
                             text='Back to 3D', icon='LOOP_BACK',
                             depress=True)
            else:
                op = row.operator(
                    FBConfig.fb_select_camera_idname,
                    text=camera.get_image_name(), icon=view_icon)
                op.headnum = headnum
                op.camnum = i

            col = row.column(align=True)
            op = col.operator(
                FBConfig.fb_proper_view_menu_exec_idname,
                text='', icon='COLLAPSEMENU')
            op.headnum = headnum
            op.camnum = i

        self._draw_add_images_button(headnum, common_col,
                                     scale=Config.btn_scale_y, icon='ADD')

    def _draw_add_images_button(self, headnum, layout, scale=2.0,
                                icon='OUTLINER_OB_IMAGE'):
        col = layout.column(align=True)
        col.scale_y = scale
        op = col.operator(FBConfig.fb_multiple_filebrowser_exec_idname,
                          text='Add Images' if icon != 'ADD' else '', icon=icon)
        op.headnum = headnum

    def draw(self, context):
        settings = fb_settings()
        if settings is None:
            return
        layout = self.layout

        state, headnum = what_is_state()
        if headnum < 0:
            return

        head = settings.get_head(headnum)
        if not head.blenshapes_are_relevant() and head.model_changed_by_pinmode:
            _draw_update_blendshapes_panel(layout)
        self._draw_camera_list(headnum, layout)

        if settings.pinmode:
            col = layout.column(align=True)
            _draw_align_button(col, scale=2.0, depress=False)
            col.operator(FBConfig.fb_reset_view_idname)

        if head.headobj and head.headobj.users == 1:
            _start_geomobj_delete_handler()


class FB_PT_Model(AllVisibleClosed, Panel):
    bl_idname = FBConfig.fb_model_panel_idname
    bl_label = 'Model'

    def draw_header_preset(self, context):
        layout = self.layout
        row = layout.row()
        row.active = False
        row.operator(
            FBConfig.fb_help_model_idname,
            text='', icon='QUESTION', emboss=False)

    def draw(self, context):
        layout = self.layout
        settings = fb_settings()
        if settings is None:
            return

        state, headnum = what_is_state()
        if headnum < 0:
            return

        head = settings.get_head(headnum)
        if not head:
            return

        row = layout.split(factor=0.35)
        row.label(text='Topology')
        row.prop(head, 'model_type', text='')
        layout.prop(head, 'tex_uv_shape')

        if not head.blenshapes_are_relevant() and head.model_changed_by_scale:
            _draw_update_blendshapes_panel(layout)

        if head.should_use_emotions():
            col = layout.column(align=True)
            col.label(text='Resulting expression in 3D:')
            col.prop(head, 'expression_view', text='')

        if FBLoader.is_not_loaded():
            return
        fb = FBLoader.get_builder()
        col = layout.column(align=True)
        col.label(text='Model parts')
        col.separator(factor=0.4)
        names = fb.mask_names()
        for i, mask in enumerate(fb.masks()):
            if i % 2 == 0:
                row = col.row(align=True)
            row.prop(head, 'masks', index=i, text=names[i])

        layout.prop(head, 'model_scale')


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
    def get_area_mode(cls, context):
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


class FB_PT_AppearancePanel(AllVisibleClosed, Panel):
    bl_idname = FBConfig.fb_appearance_panel_idname
    bl_label = 'Appearance'

    def draw_header_preset(self, context):
        layout = self.layout
        row = layout.row(align=True)
        row.active = False
        row.operator(
            FBConfig.fb_addon_setup_defaults_idname,
            text='', icon='PREFERENCES', emboss=False)
        row.operator(
            FBConfig.fb_help_appearance_idname,
            text='', icon='QUESTION', emboss=False)

    def _appearance_pin_settings(self, settings, layout) -> None:
        col = layout.column(align=True)
        row = col.row(align=True)
        row.label(text='Pins')
        col.separator(factor=0.4)
        btn = row.column(align=True)
        btn.active = False
        btn.scale_y = 0.75
        btn.operator(FBConfig.fb_default_pin_settings_idname, text='',
                     icon='LOOP_BACK', emboss=False, depress=False)
        col.prop(settings, 'pin_size', slider=True)
        col.prop(settings, 'pin_sensitivity', slider=True)

    def _appearance_wireframe_settings(self, settings, layout) -> None:
        col = layout.column(align=True)
        row = col.row(align=True)
        row.label(text='Wireframe')
        col.separator(factor=0.4)
        btn = row.column(align=True)
        btn.active = False
        btn.scale_y = 0.75
        btn.operator(
            FBConfig.fb_default_wireframe_settings_idname,
            text='', icon='LOOP_BACK', emboss=False, depress=False)

        split = col.split(factor=0.375, align=True)
        split2 = split.split(factor=0.34, align=True)
        split2.prop(settings, 'wireframe_color', text='')
        split3 = split2.split(factor=0.5, align=True)
        split3.prop(settings, 'wireframe_special_color', text='')
        split3.prop(settings, 'wireframe_midline_color', text='')
        split.prop(settings, 'wireframe_opacity', text='', slider=True)

        row = layout.row(align=True)
        op = row.operator(FBConfig.fb_wireframe_color_idname, text='R')
        op.action = 'wireframe_red'
        op = row.operator(FBConfig.fb_wireframe_color_idname, text='G')
        op.action = 'wireframe_green'
        op = row.operator(FBConfig.fb_wireframe_color_idname, text='B')
        op.action = 'wireframe_blue'
        op = row.operator(FBConfig.fb_wireframe_color_idname, text='C')
        op.action = 'wireframe_cyan'
        op = row.operator(FBConfig.fb_wireframe_color_idname, text='M')
        op.action = 'wireframe_magenta'
        op = row.operator(FBConfig.fb_wireframe_color_idname, text='Y')
        op.action = 'wireframe_yellow'
        op = row.operator(FBConfig.fb_wireframe_color_idname, text='K')
        op.action = 'wireframe_black'
        op = row.operator(FBConfig.fb_wireframe_color_idname, text='W')
        op.action = 'wireframe_white'

        col = layout.column(align=True)
        col.prop(settings, 'show_specials')
        col.prop(settings, 'wireframe_backface_culling')
        col.prop(settings, 'use_adaptive_opacity')

    def _appearance_image_adjustment(self, settings, layout) -> None:
        camera = settings.get_camera(settings.current_headnum,
                                     settings.current_camnum)
        if not camera:
            return

        col = layout.column(align=True)
        row = col.row(align=True)
        row.label(text='Background')
        col.separator(factor=0.4)
        btn = row.column(align=True)
        btn.active = False
        btn.scale_y = 0.75
        btn.operator(FBConfig.fb_reset_tone_mapping_idname,
                     text='', icon='LOOP_BACK', emboss=False, depress=False)
        col2 = col.column(align=True)
        row = col2.row(align=True)
        row.prop(camera, 'tone_exposure', slider=True)
        row.operator(FBConfig.fb_reset_tone_exposure_idname,
                     text='', icon='LOOP_BACK')
        row = col.row(align=True)
        row.prop(camera, 'tone_gamma', slider=True)
        row.operator(FBConfig.fb_reset_tone_gamma_idname,
                     text='', icon='LOOP_BACK')

    def draw(self, context):
        layout = self.layout
        settings = fb_settings()
        if settings is None:
            return

        self._appearance_wireframe_settings(settings, layout)
        self._appearance_pin_settings(settings, layout)
        if settings.pinmode:
            self._appearance_image_adjustment(settings, layout)


class FB_PT_BlendShapesPanel(AllVisibleClosed, Panel):
    bl_idname = FBConfig.fb_blendshapes_panel_idname
    bl_label = 'FACS Blendshapes'

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
        has_blendshapes_act = has_blendshapes_action(obj)

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

    def draw(self, context):
        layout = self.layout

        col = layout.column(align=True)
        col.scale_y = Config.btn_scale_y
        op = col.operator(Config.kt_report_bug_idname, icon='ERROR')
        op.product = ProductType.FACEBUILDER
        op = col.operator(Config.kt_share_feedback_idname,
                          icon='OUTLINER_OB_LIGHT')
        op.product = ProductType.FACEBUILDER


CLASSES_TO_REGISTER = (FB_PT_HeaderPanel,
                       FB_PT_UpdatePanel,
                       FB_PT_DownloadNotification,
                       FB_PT_DownloadingProblemPanel,
                       FB_PT_UpdatesInstallationPanel,
                       FB_PT_ViewsPanel,
                       FB_PT_OptionsPanel,
                       FB_PT_Model,
                       FB_PT_AppearancePanel,
                       FB_PT_TexturePanel,
                       FB_PT_BlendShapesPanel,
                       FB_PT_ExportPanel,
                       FB_PT_SupportPanel)
