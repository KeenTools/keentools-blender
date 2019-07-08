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
from bpy.types import Panel, Operator, Menu
import addon_utils
from . config import config, get_main_settings, ErrorType


# Test if selected object is our Mesh or Camera
def proper_object_test():
    context = bpy.context
    settings = get_main_settings()
    obj = context.active_object
    if settings.pinmode:
        return True
    if not obj:
        return False
    if config.version_prop_name in obj.keys():
        # Object has our attribute 'keentools_fb_version'
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
    bl_idname = config.fb_panel_idname
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = config.fb_panel_label
    bl_category = config.fb_tab_category

    # Panel appear only when our Mesh or Camera selected
    @classmethod
    def poll(cls, context):
        return proper_object_test()

    def draw_pins_panel(self, context):
        layout = self.layout
        box = layout.box()
        op = box.operator(config.fb_main_operator_idname, text="Center Geo")
        op.action = 'center_geo'

        op = box.operator(
            config.fb_main_operator_idname, text="Remove Pins", icon='CANCEL')
        op.action = 'remove_pins'

        op = box.operator(
            config.fb_main_operator_idname, text="Unmorph", icon='CANCEL')
        op.action = 'unmorph'

    # Face Builder Main Panel Draw
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
            # Need for reconstruction
            row = layout.row()
            row.scale_y = 3.0
            op = row.operator(
                config.fb_actor_operator_idname, text='Reconstruct!')
            op.action = 'reconstruct_by_head'
            op.headnum = -1
            op.camnum = -1
            return

        head = settings.heads[headnum]

        layout.prop(settings, 'focal')
        layout.prop(settings, 'sensor_width')

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
                config.fb_main_operator_idname, text='', icon=icon)
            op.action = 'select_camera'
            op.headnum = headnum
            op.camnum = i

            # Use in Tex Baking
            col.prop(camera, 'use_in_tex_baking', text='')

            # Camera Num / Pins / Name
            col = row.column()
            row2 = col.row()
            pc = str(camera.pins_count) if camera.pins_count > 0 else '-'

            text = "[{0}] -{1}- {2}".format(str(i), pc, camera.camobj.name)

            icon = 'ERROR'
            if not camera.cam_image:
                # No image --> Broken icon
                icon = 'LIBRARY_DATA_BROKEN'

            if camera.cam_image and not wrong_size_flag:
                # Camera has proper size background
                row2.label(text=text)
            else:
                # Background has different size
                row2.label(text=text, icon=icon)

            # Pin Icon if there are some pins
            if pc != '-':
                row2.label(text='', icon='PINNED')

            # Camera Delete button
            if not settings.pinmode:
                op = row2.operator(
                    config.fb_actor_operator_idname, text='', icon='CANCEL')
                op.action = 'delete_camera'
                op.headnum = headnum
                op.camnum = i

            col.template_ID(head.cameras[i], "cam_image", open="image.open")

        if len(head.cameras) == 0:
            layout.label(text="-- Camera List is empty --")
        else:
            row = layout.row()
            # Select All cameras for baking Button
            op = row.operator(config.fb_actor_operator_idname, text='All')
            op.action = 'select_all_cameras'
            op.headnum = headnum
            # Deselect All cameras
            op = row.operator(config.fb_actor_operator_idname, text='None')
            op.action = 'deselect_all_cameras'
            op.headnum = headnum
            row.label(text='Use in bake')

            row = layout.row()

            # Output current Frame Size
            if settings.frame_width > 0 and settings.frame_height > 0:
                row.label(text='{} x {}'.format(
                    settings.frame_width, settings.frame_height))
            else:
                row.label(text="...")

            if wrong_size_counter == 0:
                op = row.operator("wm.call_menu", text='Fix Size')
            else:
                op = row.operator("wm.call_menu", text='Fix Size', icon='ERROR')
            op.name = config.fb_fix_frame_menu_idname

        # Open sequence Button (large x2)
        row = layout.row()
        row.scale_y = 2.0
        row.operator(config.fb_filedialog_operator_idname,
                     text="Open Sequence", icon='OUTLINER_OB_IMAGE')

        # Add New Camera button
        op = layout.operator(
            config.fb_actor_operator_idname,
            text="Add New Camera", icon='PLUS')
        op.action = "add_camera"
        op.headnum = headnum

        # Camera buttons Center Geo, Remove pins, Unmorph
        if context.space_data.region_3d.view_perspective == 'CAMERA':
            if settings.pinmode:
                self.draw_pins_panel(context)


class WM_OT_FBAddonWarning(Operator):
    bl_idname = config.fb_warning_operator_idname
    bl_label = "FaceBuilder Addon WARNING!"

    msg: bpy.props.IntProperty(default=ErrorType.Unknown)

    content = []

    def set_content(self, txt_list):
        self.content = txt_list

    def draw(self, context):
        layout = self.layout

        for t in self.content:
            layout.label(text=t)

    def execute(self, context):
        if self.msg != 0:
            return {"FINISHED"}

        # Unlicensed message only
        wm = context.window_manager
        # Searching keyword in Addons tab
        wm.addon_search = config.addon_search

        try:
            addon_utils.modules_refresh()
            mod = addon_utils.addons_fake_modules.get(config.addon_name)
            info = addon_utils.module_bl_info(mod)
            info["show_expanded"] = True
            # bpy.ops.screen.userpref_show('INVOKE_DEFAULT')
        except:
            print('SOME ERROR WITH SETTINGS OPENNING')
            pass

        return {"FINISHED"}

    def invoke(self, context, event):
        if self.msg == ErrorType.NoLicense:
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
        return context.window_manager.invoke_props_dialog(self, width=300)
        # return context.window_manager.invoke_popup(self, width=300)


class OBJECT_PT_TBPanel(Panel):
    bl_idname = config.fb_tb_panel_idname
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Texture Builder"
    bl_category = config.fb_tab_category
    bl_options = {'DEFAULT_CLOSED'}

    # Panel appear only when our Mesh or Camera selected
    @classmethod
    def poll(cls, context):
        return proper_object_test()

    # Face Builder Main Panel Draw
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        obj = context.object
        settings = get_main_settings()

        box = layout.box()
        box.prop(settings, 'tex_width')
        box.prop(settings, 'tex_height')
        box.prop(settings, 'tex_uv_shape')

        row = layout.row()
        row.scale_y = 3.0
        op = row.operator(config.fb_actor_operator_idname, text="Bake Texture")
        op.action = 'bake_tex'
        op = row.operator(
            config.fb_actor_operator_idname, text="Show on Object")
        op.action = 'show_tex'
        layout.prop(settings, 'tex_back_face_culling')
        layout.prop(settings, 'tex_equalize_brightness')
        layout.prop(settings, 'tex_equalize_colour')
        layout.prop(settings, 'tex_face_angles_affection')
        layout.prop(settings, 'tex_uv_expand_percents')

        # layout.prop_menu_enum(settings, 'tex_uv_shape', text='', icon='UV')

    def draw_header(self, context):
        layout = self.layout
        pass


class OBJECT_PT_FBColorsPanel(Panel):
    bl_idname = config.fb_colors_panel_idname
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Wireframe Colors"
    bl_category = config.fb_tab_category

    # Panel appear only when our Mesh or Camera selected
    @classmethod
    def poll(cls, context):
        return proper_object_test()

    # Face Builder Main Panel Draw
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        obj = context.object
        settings = get_main_settings()

        # layout.label(text='Wireframe Settings')
        box = layout.box()
        row = box.row()
        row.prop(settings, 'wireframe_color', text='')
        row.prop(settings, 'wireframe_opacity', text='', slider=True)

        row = box.row()
        op = row.operator(config.fb_actor_operator_idname, text="R")
        op.action = 'wireframe_red'
        op = row.operator(config.fb_actor_operator_idname, text="G")
        op.action = 'wireframe_green'
        op = row.operator(config.fb_actor_operator_idname, text="B")
        op.action = 'wireframe_blue'
        op = row.operator(config.fb_actor_operator_idname, text="C")
        op.action = 'wireframe_cyan'
        op = row.operator(config.fb_actor_operator_idname, text="M")
        op.action = 'wireframe_magenta'
        op = row.operator(config.fb_actor_operator_idname, text="Y")
        op.action = 'wireframe_yellow'
        op = row.operator(config.fb_actor_operator_idname, text="K")
        op.action = 'wireframe_black'
        op = row.operator(config.fb_actor_operator_idname, text="W")
        op.action = 'wireframe_white'

        layout.prop(settings, 'show_specials', text='Highlight Parts')

    def draw_header(self, context):
        layout = self.layout
        pass


class OBJECT_PT_FBSettingsPanel(Panel):
    bl_idname = config.fb_settings_panel_idname
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Face Builder Settings"
    # bl_context = "objectmode"
    bl_category = config.fb_tab_category

    # bl_options = {'DEFAULT_CLOSED'}

    # Panel appear only when our Mesh or Camera selected
    @classmethod
    def poll(cls, context):
        return proper_object_test()

    # Right Panel Draw
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        obj = context.object
        settings = get_main_settings()

        # layout.label(text='Pin Sensitivity')
        box = layout.box()
        box.prop(settings, 'pin_sensitivity', slider=True)
        row = box.row()
        row.operator(
            config.fb_actor_operator_idname, text="-2").action = 'sens_dec'
        row.operator(
            config.fb_actor_operator_idname, text="+4").action = 'sens_inc'

        box = layout.box()
        box.prop(settings, 'pin_size', slider=True)
        row = box.row()
        row.operator(
            config.fb_actor_operator_idname, text="-1").action = 'psize_dec'
        row.operator(
            config.fb_actor_operator_idname, text="+2").action = 'psize_inc'

        # layout.label(text='FaceBuilder Settings')
        layout.prop(settings, 'check_auto_rigidity')
        layout.prop(settings, 'rigidity')
        '''
        box = layout.box()
        row = box.row()
        row.prop(settings, 'check_ears')
        row.prop(settings, 'check_eyes')
        row = box.row()
        row.prop(settings, 'check_face')
        row.prop(settings, 'check_headback')
        row = box.row()
        row.prop(settings, 'check_jaw')
        row.prop(settings, 'check_mouth')
        row.prop(settings, 'check_neck')
        '''

        row = layout.row()
        row.scale_y = 2.0
        op = row.operator(
            config.fb_actor_operator_idname,
            text="Open Addon Settings", icon="PREFERENCES")
        op.action = 'addon_settings'
        layout.prop(settings, 'debug_active', text="Debug Log Active")


class FBFixMenu(Menu):
    bl_label = "Select Frame Size"
    bl_idname = config.fb_fix_frame_menu_idname

    def draw(self, context):
        layout = self.layout

        op = layout.operator(
            config.fb_actor_operator_idname,
            text="Auto-Detect most frequent Size")
        op.action = 'auto_detect_frame_size'

        op = layout.operator(
            config.fb_actor_operator_idname, text="Use Scene Render Size")
        op.action = 'use_render_frame_size'

        op = layout.operator(
            config.fb_actor_operator_idname, text="Use Current Camera Size")
        op.action = 'use_camera_frame_size'

        # Disabled to avoid problems with users (but usefull for internal use)
        # op = layout.operator(
        #    config.fb_actor_operator_idname, text="Experimental Rescale to Render Size")
        # op.action = 'use_render_frame_size_scaled'
