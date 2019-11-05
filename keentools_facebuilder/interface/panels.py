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
from bpy.types import Panel, Operator
from ..config import Config, get_main_settings, ErrorType
import re
from ..fbloader import FBLoader
from ..utils.manipulate import what_is_state
import keentools_facebuilder.blender_independent_packages.pykeentools_loader as pkt

from ..utils.icons import FBIcons

def _show_all_panels():
    state, _ = what_is_state()
    # RECONSTRUCT, NO_HEADS, THIS_HEAD, ONE_HEAD, MANY_HEADS, PINMODE
    return state in {'THIS_HEAD', 'ONE_HEAD', 'PINMODE'}


class OBJECT_PT_FBHeaderPanel(Panel):
    bl_idname = Config.fb_header_panel_idname
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "{} {}".format(
            Config.addon_human_readable_name, Config.addon_version)
    bl_category = Config.fb_tab_category
    bl_context = "objectmode"

    def _head_creation_offer(self, layout):
        # Test custom icons
        # FBIcons.layout_icons(layout)

        row = layout.row()
        row.scale_y = 2.0
        row.operator(
            Config.fb_add_head_operator_idname,
            text='Create a new head', icon='USER')

        # row = layout.row()
        # row.label(text='', icon='INFO')
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
            Config.fb_main_addon_settings_idname,
            text='Install Core library', icon='PREFERENCES')

    def draw_start_panel(self, layout):
        if not pkt.is_installed():
            self._pkt_install_offer(layout)
        else:
            self._head_creation_offer(layout)

    def draw_reconstruct(self, layout):
        # Need for reconstruction
        row = layout.row()
        row.scale_y = 3.0
        op = row.operator(
            Config.fb_actor_operator_idname, text='Reconstruct!')
        op.action = 'reconstruct_by_head'
        op.headnum = -1
        op.camnum = -1

    def draw_many_heads(self, layout):
        # Output List of all heads in Scene
        settings = get_main_settings()
        for i, h in enumerate(settings.heads):
            box = layout.box()
            row = box.row()
            op = row.operator(
                Config.fb_main_select_head_idname, text='', icon='USER')
            op.headnum = i

            row.label(text=h.headobj.name)

            if not settings.pinmode:
                op = row.operator(
                    Config.fb_main_delete_head_idname,
                    text='', icon='CANCEL')
                op.headnum = i

    # ----------------------
    # Blender defined draws
    # ----------------------
    def draw_header_preset(self, context):
        layout = self.layout
        row = layout.row()
        row.operator(
            Config.fb_main_addon_settings_idname,
            text='', icon='PREFERENCES')

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
                op = row.operator(Config.fb_actor_operator_idname,
                                  text='Show Head', icon='HIDE_OFF')
                op.action = 'unhide_head'
                op.headnum = headnum
            return

        elif state == 'RECONSTRUCT':
            self.draw_reconstruct(layout)
            return

        elif state == 'NO_HEADS':
            self.draw_start_panel(layout)
            return

        else:
            self.draw_many_heads(layout)


class OBJECT_PT_FBCameraPanel(Panel):
    bl_idname = Config.fb_camera_panel_idname
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = Config.fb_camera_panel_label
    bl_category = Config.fb_tab_category
    bl_context = "objectmode"
    bl_option = {'DEFAULT_CLOSED'}

    # Panel appear only when actual
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

    # Face Builder Panel Draw
    def draw(self, context):
        settings = get_main_settings()
        layout = self.layout

        state, headnum = what_is_state()

        if headnum < 0:
            return

        head = settings.heads[headnum]

        row = layout.row()
        row.prop(head, 'sensor_width')
        row.operator(
            Config.fb_main_set_sensor_width_idname,
            text='', icon='SETTINGS')

        col = layout.column()
        if head.auto_focal_estimation:
            col.active = False
            col.alert = True
            col.enabled = False
        row = col.row()
        row.prop(head, 'focal')
        row.operator(
            Config.fb_main_set_focal_length_idname,
            text='', icon='SETTINGS')

        row = layout.row()
        if head.auto_focal_estimation:
            row.alert = True
        row.prop(head, 'auto_focal_estimation')

        # Show EXIF message
        if len(head.exif.message) > 0:
            box = layout.box()
            arr = re.split("\r\n|\n", head.exif.message)
            col = box.column()
            col.scale_y = 0.75
            for a in arr:
                col.label(text=a)


class OBJECT_PT_FBViewsPanel(Panel):
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

    def draw_pins_panel(self, headnum, camnum):
        layout = self.layout
        box = layout.box()
        op = box.operator(Config.fb_main_center_geo_idname, text="Center Geo")
        op.headnum = headnum
        op.camnum = camnum
        op = box.operator(
            Config.fb_main_remove_pins_idname, text="Remove Pins")
        op.headnum = headnum
        op.camnum = camnum

    def draw_camera_list(self, headnum, layout):
        settings = get_main_settings()
        head = settings.heads[headnum]
        wrong_size_counter = 0
        fw = settings.frame_width
        fh = settings.frame_height

        # Output cameras list
        for i, camera in enumerate(head.cameras):
            box = layout.box()
            row = box.row()

            w = camera.get_image_width()
            h = camera.get_image_height()

            # Count for wrong size images
            wrong_size_flag = w != fw or h != fh

            if wrong_size_flag:
                wrong_size_counter += 1

            # Camera Icon
            col = row.column()
            view_icon = 'HIDE_OFF'  # CAMERA_DATA
            if settings.current_camnum == i:
                col.alert = True

            op = col.operator(
                Config.fb_main_select_camera_idname, text='', icon=view_icon)
            op.headnum = headnum
            op.camnum = i

            # Camera Num / Pins / Name
            col = row.column()
            row2 = col.row()

            # Pin Icon if there are some pins
            pin_icon = 'BLANK1'
            if camera.pins_count > 0:
                pin_icon = 'PINNED'

            # Filename and Context Menu button
            if camera.cam_image:
                row2.label(text="{}".format(camera.cam_image.name),
                           icon=pin_icon)
                edit_icon = 'GREASEPENCIL'  # OUTLINER_DATA_GP_LAYER
                if wrong_size_flag:
                    # Background has different size
                    edit_icon = 'ERROR'
                op = row2.operator(Config.fb_main_camera_fix_size_idname,
                                   text='', icon=edit_icon)
                op.headnum = headnum
                op.camnum = i
            else:
                # No image --> Broken icon
                row2.label(text='-- empty --', icon=pin_icon)
                row2.label(text='', icon='LIBRARY_DATA_BROKEN')

                op = row2.operator(
                    Config.fb_single_filebrowser_operator_idname,
                    text='', icon='FILEBROWSER')
                op.headnum = headnum
                op.camnum = i

            # Camera Delete
            op = row2.operator(
                Config.fb_main_delete_camera_idname,
                text='', icon='CANCEL')  #
            op.headnum = headnum
            op.camnum = i

    def draw(self, context):
        settings = get_main_settings()
        layout = self.layout

        # Output current Frame Size
        if settings.frame_width > 0 and settings.frame_height > 0:
            info = '{}x{}'.format(
                settings.frame_width, settings.frame_height)
        else:
            x = bpy.context.scene.render.resolution_x
            y = bpy.context.scene.render.resolution_y
            info = '{}x{}'.format(x, y)

        layout.label(text=info)

        state, headnum = what_is_state()

        if headnum < 0:
            return

        # Large List of cameras
        self.draw_camera_list(headnum, layout)

        # Open sequence Button (large x2)
        row = layout.row()
        row.scale_y = 2.0
        op = row.operator(Config.fb_multiple_filebrowser_operator_idname,
                          text="Add Image(s)", icon='OUTLINER_OB_IMAGE')
        op.headnum = headnum

        # Camera buttons Center Geo, Remove pins
        if settings.pinmode and \
                context.space_data.region_3d.view_perspective == 'CAMERA':
            self.draw_pins_panel(headnum, settings.current_camnum)


class OBJECT_PT_FBExifPanel(Panel):
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
        layout.label(text='EXIF info:')

class OBJECT_PT_FBModel(Panel):
    bl_idname = Config.fb_model_panel_idname
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Model"
    bl_category = Config.fb_tab_category
    bl_options = {'DEFAULT_CLOSED'}
    bl_context = "objectmode"

    # Panel appear only when actual
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

    # Panel Draw
    def draw(self, context):
        layout = self.layout
        obj = context.object
        settings = get_main_settings()

        state, headnum = what_is_state()
        # No registered models in scene
        if headnum < 0:
            return

        head = settings.heads[headnum]

        op = layout.operator(Config.fb_main_unmorph_idname, text="Unmorph")
        op.headnum = headnum
        op.camnum = settings.current_camnum

        row = layout.split(factor=0.7)
        col = row.column()
        col.prop(settings, 'rigidity')
        col.active = not settings.check_auto_rigidity
        row.prop(settings, 'check_auto_rigidity', text="Auto")

        box = layout.box()
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

class OBJECT_PT_TexturePanel(Panel):
    bl_idname = Config.fb_texture_panel_idname
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Texture"
    bl_category = Config.fb_tab_category
    bl_options = {'DEFAULT_CLOSED'}
    bl_context = "objectmode"

    # Panel appear only when actual
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

    # Face Builder Main Panel Draw
    def draw(self, context):
        layout = self.layout
        obj = context.object
        settings = get_main_settings()
        headnum = settings.head_by_obj(obj)
        if headnum < 0:
            headnum = settings.current_headnum
        head = settings.heads[headnum]

        box = layout.box()
        box.prop(settings, 'tex_width')
        box.prop(settings, 'tex_height')
        box.prop(head, 'tex_uv_shape')

        row = layout.row()
        row.scale_y = 2.0
        op = row.operator(Config.fb_tex_selector_operator_idname,
                          text="Bake Texture", icon='RENDER_STILL')
        op.headnum = headnum

        row = layout.row()
        mode = self.get_area_mode(context)
        if mode == 'MATERIAL':
            row.operator(Config.fb_main_show_tex_idname, text="Show Mesh",
                         icon='SHADING_SOLID')
        else:
            row.operator(Config.fb_main_show_tex_idname,
                         text="Create Material", icon='MATERIAL')

        # layout.prop(settings, 'tex_back_face_culling')
        layout.prop(settings, 'tex_equalize_brightness')
        layout.prop(settings, 'tex_equalize_colour')
        layout.prop(settings, 'tex_face_angles_affection')
        layout.prop(settings, 'tex_uv_expand_percents')


class OBJECT_PT_FBColorsPanel(Panel):
    bl_idname = Config.fb_colors_panel_idname
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Wireframe Colors"
    bl_category = Config.fb_tab_category
    bl_context = "objectmode"

    # Panel appear only when actual
    @classmethod
    def poll(cls, context):
        return _show_all_panels()

    # Face Builder Main Panel Draw
    def draw(self, context):
        layout = self.layout
        settings = get_main_settings()

        box = layout.box()
        row = box.row()
        row.prop(settings, 'wireframe_color', text='')
        row.prop(settings, 'wireframe_special_color', text='')
        row.prop(settings, 'wireframe_opacity', text='', slider=True)

        row = box.row()
        op = row.operator(Config.fb_main_wireframe_color_idname, text="R")
        op.action = 'wireframe_red'
        op = row.operator(Config.fb_main_wireframe_color_idname, text="G")
        op.action = 'wireframe_green'
        op = row.operator(Config.fb_main_wireframe_color_idname, text="B")
        op.action = 'wireframe_blue'
        op = row.operator(Config.fb_main_wireframe_color_idname, text="C")
        op.action = 'wireframe_cyan'
        op = row.operator(Config.fb_main_wireframe_color_idname, text="M")
        op.action = 'wireframe_magenta'
        op = row.operator(Config.fb_main_wireframe_color_idname, text="Y")
        op.action = 'wireframe_yellow'
        op = row.operator(Config.fb_main_wireframe_color_idname, text="K")
        op.action = 'wireframe_black'
        op = row.operator(Config.fb_main_wireframe_color_idname, text="W")
        op.action = 'wireframe_white'

        layout.prop(settings, 'show_specials', text='Highlight Parts')


class OBJECT_PT_FBPinSettingsPanel(Panel):
    bl_idname = Config.fb_pin_settings_panel_idname
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Pin Settings"
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

        # layout.prop(settings, 'debug_active', text="Debug Log Active")
