# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2024 KeenTools

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

from bpy.types import Panel, TIME_MT_editor_menus

from ...utils.kt_logging import KTLogger
from ...addon_config import (Config,
                             gt_pinmode,
                             ft_pinmode,
                             fb_settings,
                             gt_settings,
                             ft_settings)
from ...facebuilder_config import FBConfig
from ...geotracker_config import GTConfig
from ...facetracker_config import FTConfig
from ...utils.icons import KTIcons
from ...facebuilder.utils.manipulate import what_is_state
from ...utils.bpy_common import bpy_timer_register


_log = KTLogger(__name__)


def add_timeline_panel() -> None:
    TIME_MT_editor_menus.append(tracker_timeline_panel)


def remove_timeline_panel() -> None:
    TIME_MT_editor_menus.remove(tracker_timeline_panel)


def tracker_timeline_panel(self, context: Any) -> None:
    if gt_pinmode():
        return geotracker_timeline_panel(self, context)
    elif ft_pinmode():
        return facetracker_timeline_panel(self, context)


def geotracker_timeline_panel(self, context: Any) -> None:
    layout = self.layout
    row = layout.row(align=True)
    row.separator()
    row.operator(GTConfig.gt_prev_keyframe_idname, text='',
                 icon='PREV_KEYFRAME')
    row.operator(GTConfig.gt_next_keyframe_idname, text='',
                 icon='NEXT_KEYFRAME')

    settings = gt_settings()

    row2 = row.row(align=True)
    row2.operator(GTConfig.gt_add_keyframe_idname, text='',
                  icon='KEY_HLT')
    row2.operator(GTConfig.gt_remove_keyframe_idname, text='',
                  icon='KEY_DEHLT')

    row2.separator()
    row2.prop(settings, 'stabilize_viewport_enabled',
              icon='LOCKED' if settings.stabilize_viewport_enabled else 'UNLOCKED')


def facetracker_timeline_panel(self, context: Any) -> None:
    layout = self.layout
    row = layout.row(align=True)
    row.separator()
    row.operator(FTConfig.ft_prev_keyframe_idname, text='',
                 icon='PREV_KEYFRAME')
    row.operator(FTConfig.ft_next_keyframe_idname, text='',
                 icon='NEXT_KEYFRAME')

    settings = ft_settings()

    row2 = row.row(align=True)
    row2.active = settings.pinmode
    row2.operator(FTConfig.ft_add_keyframe_idname, text='',
                  icon='KEY_HLT')
    row2.operator(FTConfig.ft_remove_keyframe_idname, text='',
                  icon='KEY_DEHLT')

    row2.separator()
    row2.prop(settings, 'stabilize_viewport_enabled',
              icon='LOCKED' if settings.stabilize_viewport_enabled else 'UNLOCKED')


def _draw_expression_settings(layout, head):
    if not head.should_use_emotions():
        return
    row = layout.row(align=True)
    row.label(text='', icon='BLANK1')
    col = row.column(align=True)
    col.prop(head, 'lock_blinking')
    col.prop(head, 'lock_neck_movement')


def _draw_update_blendshapes_panel(layout):
    box = layout.box()
    col = box.column()
    col.alert = True
    col.scale_y = Config.text_scale_y
    col.label(text='Mesh shape changed.')
    col.label(text='Update blendshapes')
    box.operator(FBConfig.fb_update_blendshapes_idname)


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


def _geomobj_delete_handler() -> None:
    settings = fb_settings()
    settings.force_out_pinmode = True
    return None


def _start_geomobj_delete_handler() -> None:
    bpy_timer_register(_geomobj_delete_handler, first_interval=0.01)


class COMMON_FB_PT_ViewsPanel:
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_context = 'objectmode'
    bl_label = 'Views'

    def draw_header_preset(self, context):
        layout = self.layout
        row = layout.row()
        row.active = False
        row.operator(
            FBConfig.fb_help_views_idname,
            text='', icon='QUESTION', emboss=False)

    def _back_to_button_title(self) -> str:
        return 'Back to 3D'

    def _draw_fb_trial_info(self, layout) -> None:
        pass

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
                             text=self._back_to_button_title(),
                             icon='LOOP_BACK', depress=True)
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

        self._draw_fb_trial_info(layout)

        head = settings.get_head(headnum)
        if not head.blenshapes_are_relevant():
            _draw_update_blendshapes_panel(layout)
        self._draw_camera_list(headnum, layout)

        if settings.pinmode:
            col = layout.column(align=True)
            _draw_align_button(col, scale=2.0, depress=False)
            col.operator(FBConfig.fb_reset_view_idname)

        if head.headobj and head.headobj.users == 1:
            _start_geomobj_delete_handler()


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


class COMMON_FB_PT_OptionsPanel:
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_context = 'objectmode'
    bl_options = {'DEFAULT_CLOSED'}
    bl_label = 'Options'

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
        row.prop(settings, 'shape_rigidity')

        if head.should_use_emotions():
            row = col.row(align=True)
            row.prop(settings, 'expression_rigidity')
            row.enabled = head.should_use_emotions()

        if not head.lock_blinking and head.should_use_emotions():
            row = col.row(align=True)
            row.prop(settings, 'blinking_rigidity')
            row.enabled = not head.lock_blinking and head.should_use_emotions()

        if not head.lock_neck_movement and head.should_use_emotions():
            row =  col.row(align=True)
            row.prop(settings, 'neck_movement_rigidity')
            row.enabled = not head.lock_neck_movement and head.should_use_emotions()


class COMMON_FB_PT_Model:
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_context = 'objectmode'
    bl_label = 'Model'

    def draw_header_preset(self, context):
        layout = self.layout
        row = layout.row()
        row.active = False
        row.operator(
            FBConfig.fb_help_model_idname,
            text='', icon='QUESTION', emboss=False)

    def _draw_topology_enabled(self) -> bool:
        return True

    def _draw_resulting_expression_enabled(self) -> bool:
        return True

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

        if self._draw_topology_enabled():
            row = layout.split(factor=0.35)
            row.label(text='Topology')
            row.prop(head, 'model_type', text='')

        layout.prop(head, 'tex_uv_shape')

        if not head.blenshapes_are_relevant() and head.model_changed_by_scale:
            _draw_update_blendshapes_panel(layout)

        if self._draw_resulting_expression_enabled() and head.should_use_emotions():
            col = layout.column(align=True)
            col.label(text='Resulting expression in 3D:')
            col.prop(head, 'expression_view', text='')

        loader = settings.loader()
        if loader.is_not_loaded():
            return
        fb = loader.get_builder()
        col = layout.column(align=True)
        col.label(text='Model parts')
        col.separator(factor=0.4)
        names = fb.mask_names()
        for i, mask in enumerate(fb.masks()):
            if i % 2 == 0:
                row = col.row(align=True)
            row.prop(head, 'masks', index=i, text=names[i])

        layout.prop(head, 'model_scale')
