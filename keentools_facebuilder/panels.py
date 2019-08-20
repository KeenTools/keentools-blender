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
import logging

import bpy
from bpy.types import Panel, Operator, Menu
import addon_utils
from .config import Config, get_main_settings, ErrorType
import re
from .fbloader import FBLoader


# Test if selected object is our Mesh or Camera
def proper_object_test():
    context = bpy.context
    settings = get_main_settings()
    obj = context.active_object
    if settings.pinmode:
        return True
    if not obj:
        return False
    if Config.version_prop_name[0] in obj.keys():
        # Object has our attribute 'keentools_version'
        return True
    if obj.type == 'MESH':
        # Is this mesh in settings
        return settings.find_head_index(obj) >= 0
    if obj.type == 'CAMERA':
        # Is this camera in settings
        i, _ = settings.find_cam_index(obj)
        return i >= 0
    return False


class OBJECT_PT_FBPanel(Panel):
    bl_idname = Config.fb_panel_idname
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = Config.fb_panel_label
    bl_category = Config.fb_tab_category
    bl_context = "objectmode"

    def draw_pins_panel(self, headnum, camnum):
        layout = self.layout
        box = layout.box()
        op = box.operator(Config.fb_main_center_geo_idname, text="Center Geo")
        op.headnum = headnum
        op.camnum = camnum
        op = box.operator(
            Config.fb_main_remove_pins_idname,
            text="Remove Pins", icon='UNPINNED')
        op.headnum = headnum
        op.camnum = camnum
        op = box.operator(Config.fb_main_unmorph_idname, text="Unmorph")
        op.headnum = headnum
        op.camnum = camnum

    # Face Builder Main Panel Draw
    def draw(self, context):
        layout = self.layout
        obj = context.object
        settings = get_main_settings()
        headnum = settings.head_by_obj(obj)

        proper = proper_object_test()

        if not proper:
            # Show User Hint when no target object selected
            layout.label(text='Select FaceBuilder object:')
            layout.label(text='Head or Camera.')
            layout.label(text='You can create new via:')
            layout.label(text='Add > Mesh > Face Builder')

            row = layout.row()
            row.scale_y = 2.0
            row.operator(
                Config.fb_add_head_operator_idname,
                text='Add New Head', icon='USER')

            row = layout.row()
            row.scale_y = 2.0
            row.operator(
                Config.fb_main_addon_settings_idname,
                text='Open Addon Settings', icon='PREFERENCES')
            # and out
            return

        # No registered models in scene
        if headnum < 0:
            if not obj or obj.type != 'MESH':
                return
            # Need for reconstruction
            row = layout.row()
            row.scale_y = 3.0
            op = row.operator(
                Config.fb_actor_operator_idname, text='Reconstruct!')
            op.action = 'reconstruct_by_head'
            op.headnum = -1
            op.camnum = -1
            return

        head = settings.heads[headnum]

        # Unhide Head if there some problem with pinmode
        if settings.pinmode and not FBLoader.viewport().wireframer().is_working():
            # Show Head
            row = layout.row()
            row.scale_y = 2.0
            op = row.operator(Config.fb_actor_operator_idname,
                              text='Show Head', icon='HIDE_OFF')
            op.action = 'unhide_head'
            op.headnum = headnum

        if len(head.cameras) == 0:
            layout.label(text="1. Setup two main parameters:")

        layout.prop(head, 'focal')
        box = layout.box()
        box.prop(head, 'sensor_width')
        row = box.row()
        row.prop(head, 'sensor_height')
        row.active = False

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
            icon = 'OUTLINER_OB_CAMERA' if settings.current_camnum == i \
                else 'CAMERA_DATA'
            op = col.operator(
                Config.fb_main_select_camera_idname, text='', icon=icon)
            # op.action = 'select_camera'
            op.headnum = headnum
            op.camnum = i

            # Use in Tex Baking
            col.prop(camera, 'use_in_tex_baking', text='')

            # Camera Num / Pins / Name
            col = row.column()
            row2 = col.row()
            pc = str(camera.pins_count) if camera.pins_count > 0 else '-'

            text = "[{0}] -{1}- {2}".format(str(i), pc, camera.camobj.name)

            if wrong_size_flag:
                # Background has different size
                op = row2.operator(Config.fb_main_camera_fix_size_idname,
                                   text='', icon='ERROR')
                op.headnum = headnum
                op.camnum = i

            if not camera.cam_image:
                # No image --> Broken icon
                row2.label(text='', icon='LIBRARY_DATA_BROKEN')

            # Pin Icon if there are some pins
            if pc != '-':
                row2.label(text='', icon='PINNED')

            # Output camera info
            row2.label(text=text)

            # Camera Delete button
            if not settings.pinmode:
                op = row2.operator(
                    Config.fb_main_delete_camera_idname,
                    text='', icon='CANCEL')
                # op.action = 'delete_camera'
                op.headnum = headnum
                op.camnum = i

            col.template_ID(head.cameras[i], "cam_image", open="image.open",
                            live_icon=True)

        if len(head.cameras) == 0:
            layout.label(text="2. Select reference photos")
        else:
            row = layout.row()
            # Select All cameras for baking Button
            op = row.operator(Config.fb_main_filter_cameras_idname, text='All')
            op.action = 'select_all_cameras'
            op.headnum = headnum
            # Deselect All cameras
            op = row.operator(Config.fb_main_filter_cameras_idname,
                              text='None')
            op.action = 'deselect_all_cameras'
            op.headnum = headnum
            row.label(text='in bake')

            row = layout.row()

            # Output current Frame Size
            if settings.frame_width > 0 and settings.frame_height > 0:
                row.label(text='{} x {}'.format(
                    settings.frame_width, settings.frame_height))
            else:
                row.label(text="...")

            if wrong_size_counter == 0:
                # op = row.operator("wm.call_menu", text='Fix Size')
                row.operator(Config.fb_main_fix_size_idname, text='Fix Size')
            else:
                # op = row.operator("wm.call_menu",
                #                  text='Fix Size', icon='ERROR')
                row.operator(Config.fb_main_fix_size_idname,
                             text='Fix Size', icon='ERROR')
            # op.name = config.fb_fix_frame_menu_idname

        # Open sequence Button (large x2)
        row = layout.row()
        row.scale_y = 2.0
        row.operator(Config.fb_filedialog_operator_idname,
                     text="Open Sequence", icon='OUTLINER_OB_IMAGE')

        # Add New Camera button
        op = layout.operator(
            Config.fb_main_add_camera_idname,
            text="Add Empty Camera", icon='PLUS')
        # op.action = "add_camera"
        op.headnum = headnum

        # Camera buttons Center Geo, Remove pins, Unmorph
        if context.space_data.region_3d.view_perspective == 'CAMERA':
            if settings.pinmode:
                self.draw_pins_panel(headnum, settings.current_camnum)


class WM_OT_FBAddonWarning(Operator):
    bl_idname = Config.fb_warning_operator_idname
    bl_label = "FaceBuilder WARNING!"

    msg: bpy.props.IntProperty(default=ErrorType.Unknown)
    msg_content: bpy.props.StringProperty(default="")

    content = []

    def set_content(self, txt_list):
        self.content = txt_list

    def draw(self, context):
        layout = self.layout

        for t in self.content:
            layout.label(text=t)

    def execute(self, context):
        logger = logging.getLogger(__name__)
        if self.msg != 0:
            return {"FINISHED"}

        # Unlicensed message only
        wm = context.window_manager
        # Searching keyword in Addons tab
        wm.addon_search = Config.addon_search

        try:
            addon_utils.modules_refresh()
            mod = addon_utils.addons_fake_modules.get(Config.addon_name)
            info = addon_utils.module_bl_info(mod)
            info["show_expanded"] = True
        except Exception:
            logger.error("SOME ERROR WITH ADDON SETTINGS OPENNING")
            pass

        return {"FINISHED"}

    def invoke(self, context, event):
        if self.msg == ErrorType.CustomMessage:
            self.set_content(re.split("\r\n|\n", self.msg_content))
            return context.window_manager.invoke_props_dialog(self, width=300)
        elif self.msg == ErrorType.NoLicense:
            self.set_content([
                "===============",
                "License is not detected",
                "===============",
                "Go to Addon preferences:",
                "Edit > Preferences --> Addons",
                "Use 'KeenTools' word in search field"
            ])
        elif self.msg == ErrorType.SceneDamaged:
            self.set_content([
                "===============",
                "Scene was damaged",
                "===============",
                "It looks like you manualy deleted",
                "some FaceBuilder cameras.",
                "It's not safe way.",
                "Please use [X] button on tab.",
                "===============",
                "The scene was fixed.",
                "Now everything is ok!"
            ])
        elif self.msg == ErrorType.BackgroundsDiffer:
            self.set_content([
                "===============",
                "Different sizes",
                "===============",
                "Cameras backgrounds",
                "has different sizes.",
                "Texture Builder can't bake"
            ])
        elif self.msg == ErrorType.IllegalIndex:
            self.set_content([
                "===============",
                "Object index is out of bounds",
                "===============",
                "Object index out of scene count"
            ])
        elif self.msg == ErrorType.CannotReconstruct:
            self.set_content([
                "===============",
                "Can't reconstruct",
                "===============",
                "Object parameters are invalid or missing."
            ])
        elif self.msg == ErrorType.CannotCreate:
            self.set_content([
                "===============",
                "Can't create Object",
                "===============",
                "Error when creating Object",
                "This addon version can't create",
                "objects of this type"
            ])
        elif self.msg == ErrorType.AboutFrameSize:
            self.set_content([
                "===============",
                "About Frame Sizes",
                "===============",
                "All frames used as a background image ",
                "must be the same size. This size should ",
                "be specified as the Render Size ",
                "in the scene.",
                "You will receive a warning if these ",
                "sizes are different. You can fix them ",
                "by choosing commands from this menu."
            ])
        return context.window_manager.invoke_props_dialog(self, width=300)


class OBJECT_PT_FBFaceParts(Panel):
    bl_idname = Config.fb_parts_panel_idname
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Mesh parts & UV"
    bl_category = Config.fb_tab_category
    bl_options = {'DEFAULT_CLOSED'}
    bl_context = "objectmode"

    # Panel appear only when our Mesh or Camera selected
    @classmethod
    def poll(cls, context):
        return proper_object_test()

    # Panel Draw
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        obj = context.object
        settings = get_main_settings()
        headnum = settings.head_by_obj(obj)

        # No registered models in scene
        if headnum < 0:
            if obj.type != 'MESH':
                return
        head = settings.heads[headnum]

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
        box.prop(head, 'tex_uv_shape')


class OBJECT_PT_TBPanel(Panel):
    bl_idname = Config.fb_tb_panel_idname
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Texture Builder"
    bl_category = Config.fb_tab_category
    bl_options = {'DEFAULT_CLOSED'}
    bl_context = "objectmode"

    # Panel appear only when our Mesh or Camera selected
    @classmethod
    def poll(cls, context):
        return proper_object_test()

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
        row.scale_y = 3.0

        op = row.operator(Config.fb_main_bake_tex_idname, text="Bake Texture")
        op.headnum = headnum

        mode = self.get_area_mode(context)
        if mode == 'MATERIAL':
            row.operator(Config.fb_main_show_tex_idname, text="Show Mesh")
        else:
            row.operator(Config.fb_main_show_tex_idname, text="Show Texture")

        layout.prop(settings, 'tex_back_face_culling')
        layout.prop(settings, 'tex_equalize_brightness')
        layout.prop(settings, 'tex_equalize_colour')
        layout.prop(settings, 'tex_face_angles_affection')
        layout.prop(settings, 'tex_uv_expand_percents')

    def draw_header(self, context):
        pass


class OBJECT_PT_FBColorsPanel(Panel):
    bl_idname = Config.fb_colors_panel_idname
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Wireframe Colors"
    bl_category = Config.fb_tab_category
    bl_context = "objectmode"

    # Panel appear only when our Mesh or Camera selected
    @classmethod
    def poll(cls, context):
        return proper_object_test()

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

    def draw_header(self, context):
        pass


class OBJECT_PT_FBSettingsPanel(Panel):
    bl_idname = Config.fb_settings_panel_idname
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Settings"
    bl_category = Config.fb_tab_category
    bl_context = "objectmode"

    # Panel appear only when our Mesh or Camera selected
    @classmethod
    def poll(cls, context):
        return proper_object_test()

    # Right Panel Draw
    def draw(self, context):
        layout = self.layout
        settings = get_main_settings()

        box = layout.box()
        box.prop(settings, 'pin_size', slider=True)
        box.prop(settings, 'pin_sensitivity', slider=True)

        layout.prop(settings, 'check_auto_rigidity')
        row = layout.row()
        row.prop(settings, 'rigidity')
        row.active = not settings.check_auto_rigidity

        row = layout.row()
        row.scale_y = 2.0
        row.operator(
            Config.fb_main_addon_settings_idname,
            text="Open Addon Settings", icon="PREFERENCES")
        # layout.prop(settings, 'debug_active', text="Debug Log Active")


class OBJECT_MT_FBFixCameraMenu(Menu):
    bl_label = "Fix Frame Size"
    bl_idname = Config.fb_fix_camera_frame_menu_idname
    bl_description = "Fix frame Width and Height parameters for camera"

    def draw(self, context):
        layout = self.layout

        op = layout.operator(
            Config.fb_actor_operator_idname, text="Info about this warning")
        op.action = 'about_fix_frame_warning'

        op = layout.operator(
            Config.fb_actor_operator_idname,
            text="Auto-Detect most frequent Size")
        op.action = 'auto_detect_frame_size'

        op = layout.operator(
            Config.fb_actor_operator_idname, text="Use Scene Render Size")
        op.action = 'use_render_frame_size'

        op = layout.operator(
            Config.fb_actor_operator_idname, text="Use This Camera Size")
        op.action = 'use_this_camera_frame_size'


class OBJECT_MT_FBFixMenu(Menu):
    bl_label = "Select Frame Size"
    bl_idname = Config.fb_fix_frame_menu_idname
    bl_description = "Fix frame Width and Height parameters for all cameras"

    def draw(self, context):
        layout = self.layout

        op = layout.operator(
            Config.fb_actor_operator_idname, text="Info about Size warning")
        op.action = 'about_fix_frame_warning'

        op = layout.operator(
            Config.fb_actor_operator_idname,
            text="Auto-Detect most frequent Size")
        op.action = 'auto_detect_frame_size'

        op = layout.operator(
            Config.fb_actor_operator_idname, text="Use Scene Render Size")
        op.action = 'use_render_frame_size'

        op = layout.operator(
            Config.fb_actor_operator_idname, text="Use Current Camera Size")
        op.action = 'use_camera_frame_size'

        # Disabled to avoid problems with users (but usefull for internal use)
        # frame_width & frame_height should be sets before rescale call
        # op = layout.operator(
        #    config.fb_actor_operator_idname,
        #    text="Experimental Rescale to Render Size")
        # op.action = 'use_render_frame_size_scaled'
