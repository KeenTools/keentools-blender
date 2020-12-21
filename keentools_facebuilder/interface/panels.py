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

import bpy
from bpy.types import Panel

from .updater import FBUpdater
from ..config import Config, get_main_settings
from ..messages import draw_labels
import re
from ..fbloader import FBLoader
from ..utils.manipulate import (what_is_state,
                                get_current_head,
                                get_obj_from_context,
                                has_no_blendshape,
                                has_blendshapes_action,
                                is_it_our_mesh)
from ..utils.materials import find_bpy_image_by_name
import keentools_facebuilder.blender_independent_packages.pykeentools_loader as pkt


def _state_valid_to_show(state):
    # RECONSTRUCT, NO_HEADS, THIS_HEAD, ONE_HEAD, MANY_HEADS, PINMODE, FACS_HEAD
    return state in {'THIS_HEAD', 'ONE_HEAD', 'PINMODE'}


def _show_all_panels():
    if not pkt.is_installed():
        return False
    state, _ = what_is_state()
    return _state_valid_to_show(state)


def _show_all_panels_no_blendshapes():
    if not pkt.is_installed():
        return False
    state, headnum = what_is_state()
    if not _state_valid_to_show(state):
        return False
    settings = get_main_settings()
    return settings.get_head(headnum).has_no_blendshapes()


def _draw_update_blendshapes_panel(layout):
    box = layout.box()
    col = box.column()
    col.alert = True
    col.scale_y = Config.text_scale_y
    col.label(text='The shape has been changed,')
    col.label(text='blendshapes need to be updated')
    box.operator(Config.fb_update_blendshapes_idname)


class Common:
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = Config.fb_tab_category
    bl_context = 'objectmode'


class CommonClosed(Common):
    bl_options = {'DEFAULT_CLOSED'}


class AllVisible(Common):
    @classmethod
    def poll(cls, context):
        return _show_all_panels()


class AllVisibleClosed(AllVisible):
    bl_options = {'DEFAULT_CLOSED'}


class FB_PT_HeaderPanel(Common, Panel):
    bl_idname = Config.fb_header_panel_idname
    bl_label = '{} {}'.format(
            Config.addon_human_readable_name, Config.addon_version)

    def draw_header_preset(self, context):
        layout = self.layout
        row = layout.row()
        row.operator(
            Config.fb_addon_settings_idname,
            text='', icon='PREFERENCES')

    def _head_creation_offer(self, layout):
        # Test custom icons
        # FBIcons.layout_icons(layout)

        row = layout.row()
        row.scale_y = 2.0
        row.operator(
            Config.fb_add_head_operator_idname,
            text='Create a new head', icon='USER')

        box = layout.box()
        col = box.column()
        col.scale_y = Config.text_scale_y
        col.label(text="You can also create")
        col.label(text="a new head using:")
        col.label(text="Add > Mesh > FaceBuilder")


    def _pkt_install_offer(self, layout):
        col = layout.column()
        col.scale_y = Config.text_scale_y
        col.label(text="You need to install ")
        col.label(text="KeenTools Core library")
        col.label(text="before using FaceBuilder.")

        row = layout.row()
        row.scale_y = 2.0
        row.operator(
            Config.fb_addon_settings_idname,
            text='Install Core library', icon='PREFERENCES')

    def _draw_start_panel(self, layout):
        if not pkt.is_installed():
            self._pkt_install_offer(layout)
        else:
            self._head_creation_offer(layout)

    def _draw_reconstruct(self, layout):
        row = layout.row()
        row.scale_y = 3.0
        row.operator(Config.fb_reconstruct_head_idname)

    def _draw_many_heads(self, layout):
        # Output List of all heads in Scene
        settings = get_main_settings()
        state, headnum = what_is_state()

        for i, h in enumerate(settings.heads):
            box = layout.box()
            row = box.row()

            if headnum == i:
                row.prop(settings, 'blue_head_button', toggle=1,
                         text=h.headobj.name, icon='USER')
            else:
                op = row.operator(Config.fb_select_head_idname,
                                  text=h.headobj.name, icon='USER')
                op.headnum = i

            if not settings.pinmode:
                op = row.operator(
                    Config.fb_delete_head_idname,
                    text='', icon='CANCEL')
                op.headnum = i

    def draw(self, context):
        layout = self.layout

        if not pkt.is_installed():
            self._draw_start_panel(layout)
            return

        state, headnum = what_is_state()

        if headnum >= 0 and FBLoader.is_not_loaded():
            FBLoader.load_model(headnum)

        if state == 'PINMODE':
            # Unhide Button if Head is hidden in pinmode (by ex. after Undo)
            if not FBLoader.viewport().wireframer().is_working():
                row = layout.row()
                row.scale_y = 2.0
                row.alert = True
                row.operator(Config.fb_unhide_head_idname, icon='HIDE_OFF')
            return

        elif state == 'RECONSTRUCT':
            self._draw_reconstruct(layout)
            return

        elif state == 'NO_HEADS':
            self._draw_start_panel(layout)
            return

        else:
            self._draw_many_heads(layout)
            if not FBUpdater.has_response_message():
                FBUpdater.init_updater()


class FB_PT_UpdatePanel(Common, Panel):
    bl_idname = Config.fb_update_panel_idname
    bl_label = 'Update available'

    @classmethod
    def poll(cls, context):
        return FBUpdater.has_response_message() and _show_all_panels()

    def _draw_response(self, layout):
        col = layout.column()
        col.scale_y = Config.text_scale_y
        FBUpdater.render_message(col)

        res = FBUpdater.get_response()
        if res is None:
            return
        op = layout.operator(Config.fb_open_url_idname,
            text='Open downloads page', icon='URL')
        op.url = res.download_url
        layout.operator(Config.fb_remind_later_idname,
            text='Remind tomorrow', icon='RECOVER_LAST')
        layout.operator(Config.fb_skip_version_idname,
            text='Skip this version', icon='X')

    def draw(self, context):
        layout = self.layout
        self._draw_response(layout)


class FB_PT_CameraPanel(AllVisibleClosed, Panel):
    bl_idname = Config.fb_camera_panel_idname
    bl_label = Config.fb_camera_panel_label

    def draw_header_preset(self, context):
        state, headnum = what_is_state()

        layout = self.layout
        row = layout.row()
        row.active = False

        op = row.operator(Config.fb_camera_panel_menu_exec_idname,
                     text='', icon='COLLAPSEMENU')
        op.headnum = headnum

        row.operator(
            Config.fb_help_camera_idname,
            text='', icon='QUESTION')

    def draw(self, context):
        def _draw_default_mode(layout, settings, head):
            camera = head.get_camera(settings.current_camnum)
            box = layout.box()
            row = box.row()
            col = row.column()
            col.scale_y = Config.text_scale_y
            col.label(text='File: {}'.format(camera.get_image_name()))
            row2 = col.split(factor=0.6)
            row2.label(text='Camera Group:')

            txt = camera.image_group
            if camera.image_group == 0:
                txt = '—'
            if camera.image_group < 0:
                txt = 'Excluded'

            row2.operator(Config.fb_image_group_menu_exec_idname,
                          text='{}'.format(txt))

            box.prop(camera, 'auto_focal_estimation')
            if camera.auto_focal_estimation:
                box.label(text='Focal length: {:.2f} mm'.format(camera.focal))
            else:
                box.prop(camera, 'focal')

        def _draw_mode_comment(layout, mode):
            if mode == 'all_different':
                txt = ['The focal length of each view',
                       'will be different, but',
                       'estimation process will',
                       'happen across all pinned',
                       'views simultaneously.']
            elif mode == 'current_estimation':
                txt = ['The focal length of each view',
                       'will be different and it',
                       'will be estimated only',
                       'for current view.']
            elif mode == 'same_focus':
                txt = ['The focal length will be',
                       'the same for each view,',
                       'estimation will happen',
                       'across all pinned views',
                       'simultaneously.']
            elif mode == 'force_focal':
                txt = ['The focal length will be',
                       'the same for every view,',
                       'estimation will be turned off,',
                       'you can enter the focal',
                       'length manually.']
            else:
                txt =[]
            draw_labels(layout, txt)

        def _draw_override_mode(layout, settings, head):
            box = layout.box()
            box.label(text='Override Focal Length settings:')
            box.prop(head, 'manual_estimation_mode', text='')
            col = box.column()
            col.scale_y = Config.text_scale_y
            _draw_mode_comment(col, head.manual_estimation_mode)
            if head.manual_estimation_mode == 'force_focal':
                box.prop(head, 'focal')

            if settings.current_camnum < 0:
                return
            if head.manual_estimation_mode in {'current_estimation',
                                               'all_different',
                                               'same_focus'}:
                camera = head.get_camera(settings.current_camnum)
                box.label(text='Focal length: {:.2f} mm'.format(camera.focal))

        def _draw_exif(layout, head):
            # Show EXIF info message
            if len(head.exif.info_message) > 0:
                box = layout.box()
                arr = re.split("\r\n|\n", head.exif.info_message)
                col = box.column()
                col.scale_y = Config.text_scale_y
                for a in arr:
                    col.label(text=a)

            # Show EXIF sizes message
            if len(head.exif.sizes_message) > 0:
                box = layout.box()
                arr = re.split("\r\n|\n", head.exif.sizes_message)
                col = box.column()
                col.scale_y = Config.text_scale_y
                for a in arr:
                    col.label(text=a)

        layout = self.layout
        settings = get_main_settings()
        head = get_current_head()

        if not head:
            return

        if head.smart_mode():
            if settings.current_camnum >= 0:
                _draw_default_mode(layout, settings, head)
        else:
            _draw_override_mode(layout, settings, head)

        _draw_exif(layout, head)


class FB_PT_ViewsPanel(AllVisible, Panel):
    bl_idname = Config.fb_views_panel_idname
    bl_label = Config.fb_views_panel_label

    def draw_header_preset(self, context):
        layout = self.layout
        row = layout.row()
        row.active = False
        row.operator(
            Config.fb_help_views_idname,
            text='', icon='QUESTION')

    def _draw_pins_panel(self, headnum, camnum):
        settings = get_main_settings()
        layout = self.layout
        box = layout.box()

        if settings.get_head(headnum).should_use_emotions():
            op = box.operator(Config.fb_reset_expression_idname)
            op.headnum = headnum

        op = box.operator(Config.fb_center_geo_idname,
                          text="Reset camera")
        op.headnum = headnum
        op.camnum = camnum
        op = box.operator(
            Config.fb_remove_pins_idname, text="Remove all pins")
        op.headnum = headnum
        op.camnum = camnum

    def _draw_camera_list(self, headnum, layout):
        settings = get_main_settings()
        head = settings.get_head(headnum)

        if not head.has_cameras():
            return

        box = layout.box()
        box.prop(settings.get_head(headnum), 'use_emotions')

        box = layout.box()
        for i, camera in enumerate(head.cameras):
            row = box.row()
            view_icon = 'PINNED' if camera.has_pins() else 'HIDE_OFF'

            col = row.column()
            cam_name = '{}{}'.format(
                camera.get_image_name(),
                ' [{}]'.format(camera.image_group)
                if head.is_image_group_visible(i) else ''
            )

            if settings.current_camnum == i and settings.pinmode:
                col.prop(settings, 'blue_camera_button', toggle=1,
                         text=cam_name, icon=view_icon)
            else:
                split = col
                op = split.operator(
                    Config.fb_select_camera_idname,
                    text=cam_name, icon=view_icon)
                op.headnum = headnum
                op.camnum = i

            col = row.column()
            col.active = not camera.cam_image
            op = col.operator(
                Config.fb_proper_view_menu_exec_idname,
                text='', icon='COLLAPSEMENU')
            op.headnum = headnum
            op.camnum = i

    def _draw_camera_hint(self, layout, headnum):
        settings = get_main_settings()
        head = settings.get_head(headnum)

        if not head.has_pins() \
                and head.get_last_camnum() >= 0 \
                and not settings.pinmode:
            col = layout.column()
            col.alert = True
            col.scale_y = Config.text_scale_y
            col.label(text='Press a view button with',icon='INFO')
            col.label(text='a picture file name below', icon='BLANK1')
            col.label(text='to switch to Pin mode', icon='BLANK1')

    def _draw_exit_pinmode(self, layout):
        settings = get_main_settings()
        if settings.pinmode:
            col = layout.column()
            col.scale_y = 2.0
            col.operator(Config.fb_exit_pinmode_idname,
                         text="Exit Pin mode", icon='LOOP_BACK')

    def draw(self, context):
        settings = get_main_settings()
        layout = self.layout

        state, headnum = what_is_state()
        if headnum < 0:
            return

        self._draw_exit_pinmode(layout)
        self._draw_camera_hint(layout, headnum)

        head = settings.get_head(headnum)
        if not head.blenshapes_are_relevant() and head.model_changed_by_pinmode:
            _draw_update_blendshapes_panel(layout)
        self._draw_camera_list(headnum, layout)

        # Open sequence Button (large x2)
        col = layout.column()
        col.scale_y = 2.0
        op = col.operator(Config.fb_multiple_filebrowser_exec_idname,
                          text="Add Images", icon='OUTLINER_OB_IMAGE')
        op.headnum = headnum

        # Camera buttons Reset camera, Remove pins
        if settings.pinmode and \
                context.space_data.region_3d.view_perspective == 'CAMERA':
            self._draw_pins_panel(headnum, settings.current_camnum)


class FB_PT_Model(AllVisibleClosed, Panel):
    bl_idname = Config.fb_model_panel_idname
    bl_label = 'Model'

    def draw_header_preset(self, context):
        layout = self.layout
        row = layout.row()
        row.active = False
        row.operator(
            Config.fb_help_model_idname,
            text='', icon='QUESTION')

    def draw(self, context):
        layout = self.layout
        settings = get_main_settings()

        state, headnum = what_is_state()
        # No registered models in scene
        if headnum < 0:
            return
        head = settings.get_head(headnum)

        op = layout.operator(Config.fb_unmorph_idname, text='Reset')
        op.headnum = headnum
        op.camnum = settings.current_camnum

        box = layout.box()
        box.prop(settings, 'shape_rigidity')
        expression_rigidity_row = box.row()
        expression_rigidity_row.prop(settings, 'expression_rigidity')  
        expression_rigidity_row.active = head.should_use_emotions()

        box = layout.box()
        box.prop(head, 'model_scale')

        if not head.blenshapes_are_relevant() and head.model_changed_by_scale:
            _draw_update_blendshapes_panel(box)

        row = box.split(factor=0.35)
        row.label(text='Topology')
        row.prop(head, 'model_type', text='')

        if FBLoader.is_not_loaded():
            return
        fb = FBLoader.get_builder()
        box = layout.box()
        box.label(text='Model parts:')
        names = fb.mask_names()
        for i, mask in enumerate(fb.masks()):
            if i % 2 == 0:
                row = box.row()
            row.prop(head, 'masks', index=i, text=names[i])


class FB_PT_TexturePanel(AllVisibleClosed, Panel):
    bl_idname = Config.fb_texture_panel_idname
    bl_label = 'Texture'

    def draw_header_preset(self, context):
        layout = self.layout
        row = layout.row()
        row.active = False
        row.operator(
            Config.fb_help_texture_idname,
            text='', icon='QUESTION')

    @classmethod
    def get_area_mode(cls, context):
        # Get Mode
        area = context.area
        for space in area.spaces:
            if space.type == 'VIEW_3D':
                return space.shading.type
        return 'NONE'

    def draw(self, context):
        layout = self.layout
        obj = context.object
        settings = get_main_settings()
        headnum = settings.head_by_obj(obj)
        if headnum < 0:
            headnum = settings.current_headnum
        head = settings.get_head(headnum)

        box = layout.box()
        box.label(text='Resolution (in pixels):')
        row = box.row()
        row.prop(settings, 'tex_width', text='W')
        row.prop(settings, 'tex_height', text='H')

        box = layout.box()
        box.prop(head, 'tex_uv_shape')

        row = layout.row()
        row.scale_y = 2.0
        op = row.operator(Config.fb_tex_selector_idname,
                          text="Create texture", icon='IMAGE')
        op.headnum = headnum

        texture_exists = find_bpy_image_by_name(Config.tex_builder_filename)
        row = layout.row()
        if not texture_exists:
            row.active = False

        mode = self.get_area_mode(context)
        if mode == 'MATERIAL':
            row.operator(Config.fb_show_solid_idname,
                         text="Hide texture", icon='SHADING_SOLID')
        else:
            row.operator(Config.fb_show_tex_idname,
                         text="Apply texture", icon='MATERIAL')

        row = layout.row()
        if not texture_exists:
            row.active = False
        row.operator(Config.fb_texture_file_export_idname,
                     text="Export", icon='EXPORT')
        row.operator(Config.fb_delete_texture_idname,
                     text="Delete", icon='X')

        box = layout.box()
        box.label(text='Advanced:')
        # layout.prop(settings, 'tex_back_face_culling')
        box.prop(settings, 'tex_face_angles_affection')
        box.prop(settings, 'tex_uv_expand_percents')
        box.prop(settings, 'tex_equalize_brightness')
        box.prop(settings, 'tex_equalize_colour')
        box.prop(settings, 'tex_fill_gaps')


class FB_PT_WireframeSettingsPanel(AllVisible, Panel):
    bl_idname = Config.fb_colors_panel_idname
    bl_label = 'Wireframe'

    def draw_header_preset(self, context):
        layout = self.layout
        row = layout.row()
        row.active = False
        row.operator(
            Config.fb_help_wireframe_settings_idname,
            text='', icon='QUESTION')

    def draw(self, context):
        layout = self.layout
        settings = get_main_settings()

        box = layout.box()
        split = box.split(factor=0.625)
        row = split.row()
        row.prop(settings, 'wireframe_color', text='')
        row.prop(settings, 'wireframe_special_color', text='')
        row.prop(settings, 'wireframe_midline_color', text='')
        split.prop(settings, 'wireframe_opacity', text='', slider=True)

        row = box.row()
        op = row.operator(Config.fb_wireframe_color_idname, text="R")
        op.action = 'wireframe_red'
        op = row.operator(Config.fb_wireframe_color_idname, text="G")
        op.action = 'wireframe_green'
        op = row.operator(Config.fb_wireframe_color_idname, text="B")
        op.action = 'wireframe_blue'
        op = row.operator(Config.fb_wireframe_color_idname, text="C")
        op.action = 'wireframe_cyan'
        op = row.operator(Config.fb_wireframe_color_idname, text="M")
        op.action = 'wireframe_magenta'
        op = row.operator(Config.fb_wireframe_color_idname, text="Y")
        op.action = 'wireframe_yellow'
        op = row.operator(Config.fb_wireframe_color_idname, text="K")
        op.action = 'wireframe_black'
        op = row.operator(Config.fb_wireframe_color_idname, text="W")
        op.action = 'wireframe_white'

        layout.prop(settings, 'show_specials', text='Highlight head parts')


class FB_PT_PinSettingsPanel(AllVisible, Panel):
    bl_idname = Config.fb_pin_settings_panel_idname
    bl_label = 'Pins'

    def draw_header_preset(self, context):
        layout = self.layout
        row = layout.row()
        row.active = False
        row.operator(
            Config.fb_help_pin_settings_idname,
            text='', icon='QUESTION')

    def draw(self, context):
        layout = self.layout
        settings = get_main_settings()

        box = layout.box()
        box.prop(settings, 'pin_size', slider=True)
        box.prop(settings, 'pin_sensitivity', slider=True)


class FB_PT_BlendShapesPanel(AllVisible, Panel):
    bl_idname = Config.fb_blendshapes_panel_idname
    bl_label = 'Blendshapes'

    @classmethod
    def poll(cls, context):
        if not pkt.is_installed():
            return False
        state, _ = what_is_state()
        return _state_valid_to_show(state) or state == 'FACS_HEAD'

    def draw_header_preset(self, context):
        layout = self.layout
        row = layout.row()
        row.active = False
        row.operator(
            Config.fb_help_blendshapes_idname,
            text='', icon='QUESTION')

    def draw(self, context):
        layout = self.layout

        obj, scale = get_obj_from_context(context, force_fbloader=False)
        if not obj:
            return

        no_blendshapes = has_no_blendshape(obj)
        has_blendshapes_act = has_blendshapes_action(obj)

        box = layout.box()
        box.operator(Config.fb_create_blendshapes_idname)

        row = box.row()
        if no_blendshapes:
            row.active = False
        op = row.operator(Config.fb_delete_blendshapes_idname)
        op.active_button = not no_blendshapes

        if not no_blendshapes:
            box.operator(Config.fb_reset_blendshape_values_idname)

        if not no_blendshapes:
            box = layout.box()
            box.label(text='Animation')

            box.operator(Config.fb_load_animation_from_csv_idname)

            row = box.row()
            if has_blendshapes_act:
                row.active = False
            op = row.operator(Config.fb_create_example_animation_idname)
            op.active_button = not has_blendshapes_act

            row = box.row()
            if not has_blendshapes_act:
                row.active = False
            op = row.operator(Config.fb_clear_animation_idname)
            op.active_button = has_blendshapes_act

        box = layout.box()
        box.operator(Config.fb_export_head_to_fbx_idname)

        return

        # Functions for future Animation Control Panel
        box = layout.box()
        box.label(text='Control Panel')

        op = box.operator(
            Config.fb_history_actor_idname,
            text='Generate Control Panel')
        op.action = 'generate_control_panel'

        op = box.operator(
            Config.fb_history_actor_idname,
            text='Delete Control Panel')
        op.action = 'delete_control_panel'

        op = box.operator(
            Config.fb_history_actor_idname,
            text='Select sliders')
        op.action = 'select_control_panel_sliders'

        op = box.operator(
            Config.fb_history_actor_idname,
            text='Sliders -> Blendshapes')
        op.action = 'convert_controls_to_blendshapes'
