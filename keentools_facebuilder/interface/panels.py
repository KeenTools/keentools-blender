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
import re
from ..fbloader import FBLoader
from ..utils.manipulate import what_is_state
from ..utils.materials import find_tex_by_name
import keentools_facebuilder.blender_independent_packages.pykeentools_loader as pkt


def _show_all_panels():
    state, _ = what_is_state()
    # RECONSTRUCT, NO_HEADS, THIS_HEAD, ONE_HEAD, MANY_HEADS, PINMODE
    return state in {'THIS_HEAD', 'ONE_HEAD', 'PINMODE'}


class FB_PT_HeaderPanel(Panel):
    bl_idname = Config.fb_header_panel_idname
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "{} {}".format(
            Config.addon_human_readable_name, Config.addon_version)
    bl_category = Config.fb_tab_category
    bl_context = "objectmode"

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
        col.scale_y = 0.75
        col.label(text="You can also create")
        col.label(text="a new head using:")
        col.label(text="Add > Mesh > FaceBuilder")


    def _pkt_install_offer(self, layout):
        col = layout.column()
        col.scale_y = 0.75
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
        # Need for reconstruction
        row = layout.row()
        row.scale_y = 3.0
        op = row.operator(
            Config.fb_actor_idname, text='Reconstruct!')
        op.action = 'reconstruct_by_head'
        op.headnum = -1
        op.camnum = -1

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
        state, headnum = what_is_state()
        # layout.label(text="{} {}".format(state, headnum))

        if state == 'PINMODE':
            # Unhide Button if Head is hidden in pinmode (by ex. after Undo)
            if not FBLoader.viewport().wireframer().is_working():
                row = layout.row()
                row.scale_y = 2.0
                row.alert = True
                op = row.operator(Config.fb_actor_idname,
                                  text='Show Head', icon='HIDE_OFF')
                op.action = 'unhide_head'
                op.headnum = headnum
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


class FB_PT_UpdatePanel(Panel):
    bl_idname = Config.fb_update_panel_idname
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Update available"
    bl_category = Config.fb_tab_category
    bl_context = "objectmode"

    @classmethod
    def poll(cls, context):
        return FBUpdater.has_response_message() and _show_all_panels()

    def _draw_response(self, layout):
        col = layout.column()
        col.scale_y = 0.75
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


class FB_PT_CameraPanel(Panel):
    bl_idname = Config.fb_camera_panel_idname
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = Config.fb_camera_panel_label
    bl_category = Config.fb_tab_category
    bl_context = "objectmode"
    bl_option = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return _show_all_panels()

    def draw_header_preset(self, context):
        layout = self.layout
        row = layout.row()
        row.active = False
        row.operator(
            Config.fb_help_camera_idname,
            text='', icon='QUESTION')

    def draw(self, context):
        settings = get_main_settings()
        layout = self.layout

        state, headnum = what_is_state()

        if headnum < 0:
            return

        head = settings.get_head(headnum)

        row = layout.row()
        row.prop(head, 'sensor_width')
        row.operator(
            Config.fb_sensor_size_window_idname,
            text='', icon='SETTINGS')

        col = layout.column()
        if head.auto_focal_estimation:
            col.active = False
            col.enabled = False
        row = col.row()
        row.prop(head, 'focal')
        row.operator(
            Config.fb_focal_length_menu_exec_idname,
            text='', icon='SETTINGS')

        row = layout.row()
        row.prop(head, 'auto_focal_estimation')


class FB_PT_ExifPanel(Panel):
    bl_idname = Config.fb_exif_panel_idname
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "EXIF"
    bl_category = Config.fb_tab_category
    bl_context = "objectmode"

    @classmethod
    def poll(cls, context):
        return _show_all_panels()

    def draw_header_preset(self, context):
        layout = self.layout
        row = layout.row()
        row.active = False
        row.operator(
            Config.fb_help_exif_idname,
            text='', icon='QUESTION')

    def draw(self, context):
        settings = get_main_settings()
        layout = self.layout
        state, headnum = what_is_state()

        head = settings.get_head(headnum)

        if head is None:
            return

        op = layout.operator(Config.fb_read_exif_menu_exec_idname,
                             text='Read EXIF')
        op.headnum = headnum

        # Show EXIF info message
        if len(head.exif.info_message) > 0:
            box = layout.box()
            arr = re.split("\r\n|\n", head.exif.info_message)
            col = box.column()
            col.scale_y = 0.75
            for a in arr:
                col.label(text=a)

        # Show EXIF sizes message
        if len(head.exif.sizes_message) > 0:
            box = layout.box()
            arr = re.split("\r\n|\n", head.exif.sizes_message)
            col = box.column()
            col.scale_y = 0.75
            for a in arr:
                col.label(text=a)


class FB_PT_ViewsPanel(Panel):
    bl_idname = Config.fb_views_panel_idname
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = Config.fb_views_panel_label
    bl_category = Config.fb_tab_category
    bl_context = "objectmode"

    @classmethod
    def poll(cls, context):
        return _show_all_panels()

    def draw_header_preset(self, context):
        layout = self.layout
        row = layout.row()
        row.active = False
        row.operator(
            Config.fb_help_views_idname,
            text='', icon='QUESTION')

    def _draw_pins_panel(self, headnum, camnum):
        layout = self.layout
        box = layout.box()
        op = box.operator(Config.fb_center_geo_idname,
                          text="Reset camera")
        op.headnum = headnum
        op.camnum = camnum
        op = box.operator(
            Config.fb_remove_pins_idname, text="Remove pins")
        op.headnum = headnum
        op.camnum = camnum

    def _draw_camera_list(self, headnum, layout):
        settings = get_main_settings()
        head = settings.get_head(headnum)
        wrong_size_counter = 0
        fw = settings.frame_width
        fh = settings.frame_height

        for i, camera in enumerate(head.cameras):
            box = layout.box()
            row = box.row()

            w = camera.get_image_width()
            h = camera.get_image_height()
            wrong_size_flag = w != fw or h != fh

            if wrong_size_flag:
                wrong_size_counter += 1

            view_icon = 'PINNED' if camera.has_pins() else 'HIDE_OFF'

            col = row.column()
            cam_name = camera.get_image_name()
            if settings.current_camnum == i and settings.pinmode:
                col.prop(settings, 'blue_camera_button', toggle=1,
                         text=cam_name, icon=view_icon)
            else:
                op = col.operator(
                    Config.fb_select_camera_idname,
                    text=cam_name, icon=view_icon)
                op.headnum = headnum
                op.camnum = i

            col = row.column()
            if not camera.cam_image:
                op = col.operator(
                    Config.fb_improper_view_menu_exec_idname,
                    text='', icon='COLLAPSEMENU')
            elif wrong_size_flag:
                col.alert = True
                op = col.operator(
                    Config.fb_improper_view_menu_exec_idname,
                    text='', icon='ERROR')
            else:
                col.active = False
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
            col.scale_y = 0.75
            col.label(text='Press a view button with',icon='INFO')
            col.label(text='a picture file name below', icon='BLANK1')
            col.label(text='to switch to Pin mode', icon='BLANK1')

    def _draw_exit_pinmode(self, layout):
        settings = get_main_settings()
        if settings.pinmode:
            col = layout.column()
            col.scale_y = 2.0
            op = col.operator(Config.fb_exit_pinmode_idname,
                              text="Exit Pin mode", icon='LOOP_BACK')

    def draw(self, context):
        settings = get_main_settings()
        layout = self.layout

        # Output current Frame Size
        if settings.frame_width > 0 and settings.frame_height > 0:
            info = 'Frame size: {}x{}px'.format(
                settings.frame_width, settings.frame_height)
        else:
            x = bpy.context.scene.render.resolution_x
            y = bpy.context.scene.render.resolution_y
            info = 'Frame size: {}x{}px'.format(x, y)

        state, headnum = what_is_state()

        if headnum < 0:
            return

        box = layout.box()
        box.scale_y = 1.5
        row = box.row()
        row.label(text=info)
        op = row.operator(Config.fb_fix_size_menu_exec_idname,
                          text='', icon='SETTINGS')
        op.headnum = headnum

        self._draw_camera_hint(layout, headnum)

        self._draw_exit_pinmode(layout)

        # Large List of cameras
        self._draw_camera_list(headnum, layout)

        # Open sequence Button (large x2)
        col = layout.column()
        col.scale_y = 2.0

        op = col.operator(Config.fb_multiple_filebrowser_exec_idname,
                          text="Add Images", icon='OUTLINER_OB_IMAGE')
        op.headnum = headnum
        op.auto_update_frame_size = settings.get_last_camnum(headnum) < 0

        # Camera buttons Reset camera, Remove pins
        if settings.pinmode and \
                context.space_data.region_3d.view_perspective == 'CAMERA':
            self._draw_pins_panel(headnum, settings.current_camnum)


class FB_PT_Model(Panel):
    bl_idname = Config.fb_model_panel_idname
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Model"
    bl_category = Config.fb_tab_category
    bl_options = {'DEFAULT_CLOSED'}
    bl_context = "objectmode"

    @classmethod
    def poll(cls, context):
        return _show_all_panels()

    def draw_header_preset(self, context):
        layout = self.layout
        row = layout.row()
        row.active = False
        row.operator(
            Config.fb_help_model_idname,
            text='', icon='QUESTION')

    def draw(self, context):
        layout = self.layout
        obj = context.object
        settings = get_main_settings()

        state, headnum = what_is_state()
        # No registered models in scene
        if headnum < 0:
            return

        head = settings.get_head(headnum)

        op = layout.operator(Config.fb_unmorph_idname, text="Reset")
        op.headnum = headnum
        op.camnum = settings.current_camnum

        box = layout.box()
        row = box.split(factor=0.65)
        col = row.column()
        col.prop(settings, 'rigidity')
        col.active = not settings.check_auto_rigidity
        row.prop(settings, 'check_auto_rigidity', text="Auto")

        box = layout.box()
        box.label(text='Model parts:')
        row = box.row()
        row.prop(head, 'check_ears')
        row.prop(head, 'check_eyes')
        row = box.row()
        row.prop(head, 'check_face')
        row.prop(head, 'check_headback')
        row = box.row()
        row.prop(head, 'check_jaw')
        row.prop(head, 'check_mouth')
        row = box.row()
        row.prop(head, 'check_neck')
        row.prop(head, 'check_nose')


class FB_PT_TexturePanel(Panel):
    bl_idname = Config.fb_texture_panel_idname
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Texture"
    bl_category = Config.fb_tab_category
    bl_options = {'DEFAULT_CLOSED'}
    bl_context = "objectmode"

    @classmethod
    def poll(cls, context):
        return _show_all_panels()

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
        box.label(text='Dimensions (in pixels):')
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

        texture_exists = find_tex_by_name(Config.tex_builder_filename)
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


class FB_PT_WireframeSettingsPanel(Panel):
    bl_idname = Config.fb_colors_panel_idname
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Wireframe"
    bl_category = Config.fb_tab_category
    bl_context = "objectmode"

    @classmethod
    def poll(cls, context):
        return _show_all_panels()

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
        row = box.row()
        row.prop(settings, 'wireframe_color', text='')
        row.prop(settings, 'wireframe_special_color', text='')
        row.prop(settings, 'wireframe_opacity', text='', slider=True)

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


class FB_PT_PinSettingsPanel(Panel):
    bl_idname = Config.fb_pin_settings_panel_idname
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Pins"
    bl_category = Config.fb_tab_category
    bl_context = "objectmode"

    @classmethod
    def poll(cls, context):
        return _show_all_panels()

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

        # layout.prop(settings, 'debug_active', text="Debug Log Active", toggle=1)
