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
from bpy.types import Operator
from bpy.props import (
    StringProperty,
    IntProperty,
)

from .utils import cameras, manipulate, materials
from .utils.manipulate import check_settings
from .utils.attrs import get_obj_collection, safe_delete_collection
from .fbloader import FBLoader
from .fbdebug import FBDebug
from .config import get_main_settings, get_operators, Config
from .utils.exif_reader import (read_exif_from_camera,
                                get_sensor_size_35mm_equivalent)


class FB_OT_SelectHead(Operator):
    bl_idname = Config.fb_select_head_idname
    bl_label = "Select head"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Select head in the scene"

    headnum: IntProperty(default=0)

    def draw(self, context):
        pass

    def execute(self, context):
        if not check_settings():
            return {'CANCELLED'}

        settings = get_main_settings()
        head = settings.get_head(self.headnum)

        bpy.ops.object.select_all(action='DESELECT')
        head.headobj.select_set(state=True)
        bpy.context.view_layer.objects.active = head.headobj
        return {'FINISHED'}


class FB_OT_DeleteHead(Operator):
    bl_idname = Config.fb_delete_head_idname
    bl_label = "Delete head"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Delete the head and its cameras from the scene"

    headnum: IntProperty(default=0)

    def draw(self, context):
        pass

    def execute(self, context):
        if not check_settings():
            return {'CANCELLED'}

        settings = get_main_settings()
        head = settings.get_head(self.headnum)

        for c in head.cameras:
            try:
                # Remove camera object
                bpy.data.objects.remove(c.camobj)  # , do_unlink=True
            except Exception:
                pass

        try:
            col = get_obj_collection(head.headobj)
            # Remove head object
            bpy.data.objects.remove(
                head.headobj)  # , do_unlink=True
            safe_delete_collection(col)
        except Exception:
            pass
        settings.heads.remove(self.headnum)
        return {'FINISHED'}


class FB_OT_SelectCamera(Operator):
    bl_idname = Config.fb_select_camera_idname
    bl_label = "Pin Mode"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}
    bl_description = "Switch to Pin mode for this view"

    headnum: IntProperty(default=0)
    camnum: IntProperty(default=0)

    def draw(self, context):
        pass

    def execute(self, context):
        if not check_settings():
            return {'CANCELLED'}

        settings = get_main_settings()
        headnum = self.headnum
        camnum = self.camnum
        head = settings.get_head(headnum)

        # bpy.ops.object.select_all(action='DESELECT')
        camobj = head.get_camera(camnum).camobj

        cameras.switch_to_camera(camobj)

        # Add Background Image
        c = camobj.data
        c.lens = head.focal
        c.show_background_images = True
        if len(c.background_images) == 0:
            b = c.background_images.new()
        else:
            b = c.background_images[0]
        b.image = head.get_camera(camnum).cam_image

        headobj = head.headobj
        bpy.context.view_layer.objects.active = headobj

        # Auto Call PinMode
        draw_op = getattr(get_operators(), Config.fb_pinmode_callname)
        if not bpy.app.background:
            draw_op('INVOKE_DEFAULT', headnum=headnum, camnum=camnum)

        # === Debug only ===
        FBDebug.add_event_to_queue('SELECT_CAMERA', headnum, camnum)
        FBDebug.add_event_to_queue('FORCE_SNAPSHOT', headnum, camnum)
        FBDebug.make_snapshot()
        # === Debug only ===
        return {'FINISHED'}


class FB_OT_CenterGeo(Operator):
    bl_idname = Config.fb_center_geo_idname
    bl_label = "Reset Camera"
    bl_options = {'REGISTER', 'INTERNAL'}  # 'UNDO'
    bl_description = "Place the camera so the model will be centred " \
                     "in the view"

    headnum: IntProperty(default=0)
    camnum: IntProperty(default=0)

    def draw(self, context):
        pass

    def execute(self, context):
        if not check_settings():
            return {'CANCELLED'}

        settings = get_main_settings()
        headnum = self.headnum
        camnum = self.camnum

        fb = FBLoader.get_builder()
        kid = settings.get_keyframe(headnum, camnum)

        FBLoader.fb_save(headnum, camnum)
        manipulate.push_head_state_in_undo_history(
            settings.get_head(headnum), 'Before Reset Camera')

        fb.center_model_mat(kid)
        FBLoader.fb_save(headnum, camnum)
        FBLoader.fb_redraw(headnum, camnum)

        manipulate.push_head_state_in_undo_history(
            settings.get_head(headnum), 'After Reset Camera')
        # === Debug only ===
        FBDebug.add_event_to_queue('CENTER_GEO', 0, 0)
        FBDebug.add_event_to_queue('FORCE_SNAPSHOT', 0, 0)
        FBDebug.make_snapshot()
        return {'FINISHED'}


class FB_OT_Unmorph(Operator):
    bl_idname = Config.fb_unmorph_idname
    bl_label = "Reset"
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = "Reset shape deformations to the default state. " \
                     "It will remove all pins as well"

    headnum: IntProperty(default=0)
    camnum: IntProperty(default=0)

    def draw(self, context):
        pass

    def execute(self, context):
        if not check_settings():
            return {'CANCELLED'}
        settings = get_main_settings()
        headnum = self.headnum
        camnum = self.camnum
        head = settings.get_head(headnum)

        fb = FBLoader.get_builder()
        FBLoader.fb_save(headnum, camnum)
        manipulate.push_head_state_in_undo_history(
            settings.get_head(headnum), 'Before Reset')

        fb.unmorph()

        for i, camera in enumerate(head.cameras):
            fb.remove_pins(camera.get_keyframe())
            camera.pins_count = 0

        if settings.pinmode:
            FBLoader.fb_save(headnum, camnum)
            FBLoader.fb_redraw(headnum, camnum)
        else:
            FBLoader.save_only(headnum)
            FBLoader.update_mesh_only(headnum)

        FBLoader.fb_save(headnum, camnum)
        manipulate.push_head_state_in_undo_history(
            settings.get_head(headnum), 'After Reset')

        return {'FINISHED'}


class FB_OT_RemovePins(Operator):
    bl_idname = Config.fb_remove_pins_idname
    bl_label = "Remove pins"
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = "Remove all pins on this view"

    headnum: IntProperty(default=0)
    camnum: IntProperty(default=0)

    def draw(self, context):
        pass

    def execute(self, context):
        settings = get_main_settings()

        if not settings.pinmode:
            return {'CANCELLED'}

        headnum = self.headnum
        camnum = self.camnum

        fb = FBLoader.get_builder()
        kid = settings.get_keyframe(headnum, camnum)
        FBLoader.fb_save(headnum, camnum)
        manipulate.push_head_state_in_undo_history(
            settings.get_head(headnum), 'Before Remove pins')

        fb.remove_pins(kid)
        # Added but don't work
        fb.solve_for_current_pins(kid)
        FBLoader.fb_save(headnum, camnum)
        FBLoader.fb_redraw(headnum, camnum)
        FBLoader.update_pins_count(headnum, camnum)

        manipulate.push_head_state_in_undo_history(
            settings.get_head(headnum), 'After Remove pins')

        # === Debug only ===
        FBDebug.add_event_to_queue('REMOVE_PINS', 0, 0)
        FBDebug.add_event_to_queue('FORCE_SNAPSHOT', 0, 0)
        FBDebug.make_snapshot()
        # === Debug only ===
        return {'FINISHED'}


class FB_OT_WireframeColor(Operator):
    bl_idname = Config.fb_wireframe_color_idname
    bl_label = "Wireframe color"
    bl_options = {'REGISTER', 'INTERNAL'}  # 'UNDO'
    bl_description = "Choose the wireframe coloring scheme"

    action: StringProperty(name="Action Name")

    def draw(self, context):
        pass

    def execute(self, context):
        settings = get_main_settings()

        if self.action == "wireframe_red":
            settings.wireframe_color = Config.red_scheme1
            settings.wireframe_special_color = Config.red_scheme2
        elif self.action == "wireframe_green":
            settings.wireframe_color = Config.green_scheme1
            settings.wireframe_special_color = Config.green_scheme2
        elif self.action == "wireframe_blue":
            settings.wireframe_color = Config.blue_scheme1
            settings.wireframe_special_color = Config.blue_scheme2
        elif self.action == "wireframe_cyan":
            settings.wireframe_color = Config.cyan_scheme1
            settings.wireframe_special_color = Config.cyan_scheme2
        elif self.action == "wireframe_magenta":
            settings.wireframe_color = Config.magenta_scheme1
            settings.wireframe_special_color = Config.magenta_scheme2
        elif self.action == "wireframe_yellow":
            settings.wireframe_color = Config.yellow_scheme1
            settings.wireframe_special_color = Config.yellow_scheme2
        elif self.action == "wireframe_black":
            settings.wireframe_color = Config.black_scheme1
            settings.wireframe_special_color = Config.black_scheme2
        elif self.action == "wireframe_white":
            settings.wireframe_color = Config.white_scheme1
            settings.wireframe_special_color = Config.white_scheme2

        return {'FINISHED'}


class FB_OT_FilterCameras(Operator):
    bl_idname = Config.fb_filter_cameras_idname
    bl_label = "Camera Filter"
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = "Select cameras to use for texture baking"

    action: StringProperty(name="Action Name")
    headnum: IntProperty(default=0)

    def draw(self, context):
        pass

    def execute(self, context):
        settings = get_main_settings()

        if self.action == "select_all_cameras":
            for c in settings.get_head(self.headnum).cameras:
                c.use_in_tex_baking = True

        elif self.action == "deselect_all_cameras":
            for c in settings.get_head(self.headnum).cameras:
                c.use_in_tex_baking = False

        return {'FINISHED'}


class FB_OT_DeleteCamera(Operator):
    bl_idname = Config.fb_delete_camera_idname
    bl_label = "Delete View"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Delete this view and its camera from the scene"

    headnum: IntProperty(default=0)
    camnum: IntProperty(default=0)

    def draw(self, context):
        pass

    def execute(self, context):
        if not check_settings():
            return {'CANCELLED'}

        settings = get_main_settings()
        headnum = self.headnum
        camnum = self.camnum

        camera = settings.get_camera(headnum, camnum)
        if camera is None:
            return {'CANCELLED'}

        kid = camera.get_keyframe()
        fb = FBLoader.get_builder()
        fb.remove_keyframe(kid)

        head = settings.get_head(headnum)
        camera.delete_cam_image()
        camera.delete_camobj()
        head.cameras.remove(camnum)

        if settings.current_camnum > camnum:
            settings.current_camnum -= 1
        elif settings.current_camnum == camnum:
            settings.current_camnum = -1

        FBLoader.fb_save(headnum, settings.current_camnum)

        logger = logging.getLogger(__name__)
        logger.debug("CAMERA H:{} C:{} REMOVED".format(headnum, camnum))
        return {'FINISHED'}


class FB_OT_AddCamera(Operator):
    bl_idname = Config.fb_add_camera_idname
    bl_label = "Add Empty Camera"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Add new camera without image (Not recommended). \n" \
                     "Use 'Add Camera Image(s)' button instead"
    headnum: IntProperty(default=0)

    def draw(self, context):
        pass

    def execute(self, context):
        if not check_settings():
            return {'CANCELLED'}

        settings = get_main_settings()
        headnum = self.headnum

        # Warning! Loading camera may cause data loss
        if settings.get_head(headnum).cameras:
            FBLoader.load_only(headnum)

        camera = FBLoader.add_camera(headnum, None)
        FBLoader.set_keentools_version(camera.camobj)
        FBLoader.save_only(headnum)
        return {'FINISHED'}


class FB_OT_SetSensorWidth(Operator):
    bl_idname = Config.fb_set_sensor_width_idname
    bl_label = "Sensor Size"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Change Sensor Size using EXIF data from loaded images"

    headnum: IntProperty(default=0)

    def draw(self, context):
        pass

    def execute(self, context):
        settings = get_main_settings()
        settings.tmp_headnum = self.headnum
        bpy.ops.wm.call_menu(
            'INVOKE_DEFAULT', name=Config.fb_sensor_width_menu_idname)
        return {'FINISHED'}


class FB_OT_SensorSizeWindow(Operator):
    bl_idname = Config.fb_sensor_size_window_idname
    bl_label = "Sensor Size"
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = "Change Sensor Size using EXIF data from loaded images"

    headnum: IntProperty(default=0)

    def draw(self, context):
        settings = get_main_settings()
        layout = self.layout
        head = settings.get_head(self.headnum)

        split_factor = 0.37

        # Auto Sensor & Focal via EXIF
        if head.exif.sensor_width > 0.0 and head.exif.sensor_length > 0.0 \
                and head.exif.focal > 0.0:
            w = head.exif.sensor_width
            h = head.exif.sensor_length
            f = head.exif.focal
            txt = "{:.2f} x {:.2f} mm [{:.2f}]   ".format(w, h, f)

            row = layout.split(factor=split_factor)
            op = row.operator(Config.fb_camera_actor_idname,
                              text=txt,
                              icon='OBJECT_DATAMODE')
            op.headnum = settings.tmp_headnum
            op.action = 'exif_sensor_and_focal'
            row.label(text='EXIF Sensor & [EXIF Focal Length]')

        # EXIF Focal and Sensor via 35mm equiv.
        if head.exif.focal > 0.0 and head.exif.focal35mm > 0.0:
            f = head.exif.focal
            w, h = get_sensor_size_35mm_equivalent(head)
            txt = "{:.2f} x {:.2f} mm [{:.2f}]   ".format(w, h, f)

            row = layout.split(factor=split_factor)
            op = row.operator(Config.fb_camera_actor_idname,
                              text=txt,
                              icon='OBJECT_HIDDEN')
            op.headnum = settings.tmp_headnum
            op.action = 'exif_focal_and_sensor_via_35mm'
            row.label(text='Sensor via 35mm equiv. & [EXIF Focal Length]')

        layout.separator()

        # Sensor Size (only) via EXIF
        if head.exif.sensor_width > 0.0 and head.exif.sensor_length > 0.0:
            w = head.exif.sensor_width
            h = head.exif.sensor_length
            txt = "{:.2f} x {:.2f} mm   ".format(w, h)

            row = layout.split(factor=split_factor)
            op = row.operator(Config.fb_camera_actor_idname,
                              text=txt,
                              icon='OBJECT_DATAMODE')
            op.headnum = settings.tmp_headnum
            op.action = 'exif_sensor'
            row.label(text='EXIF Sensor Size')

        # Sensor Size (only) via EXIF 35mm equivalent
        if head.exif.focal > 0.0 and head.exif.focal35mm > 0.0:
            w, h = get_sensor_size_35mm_equivalent(head)
            txt = "{:.2f} x {:.2f} mm   ".format(w, h)

            row = layout.split(factor=split_factor)
            op = row.operator(Config.fb_camera_actor_idname,
                              text=txt,
                              icon='OBJECT_HIDDEN')
            op.headnum = settings.tmp_headnum
            op.action = 'exif_sensor_via_35mm'
            row.label(text='Sensor Size 35mm equivalent')

        # ----------------
        layout.separator()

        row = layout.split(factor=split_factor)
        op = row.operator(Config.fb_camera_actor_idname,
                          text="36 x 24 mm",
                          icon='FULLSCREEN_ENTER')
        op.headnum = settings.tmp_headnum
        op.action = 'sensor_36x24mm'
        row.label(text='35mm Full-frame (default)')

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=480)

    def execute(self, context):
        return {'FINISHED'}


class FB_OT_FocalLengthMenuExec(Operator):
    bl_idname = Config.fb_focal_length_menu_exec_idname
    bl_label = "Focal Length"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Change Focal Length using EXIF data from loaded images"

    headnum: IntProperty(default=0)

    def draw(self, context):
        pass

    def execute(self, context):
        settings = get_main_settings()
        settings.tmp_headnum = self.headnum
        bpy.ops.wm.call_menu(
            'INVOKE_DEFAULT', name=Config.fb_focal_length_menu_idname)
        return {'FINISHED'}


class FB_OT_AllViewsMenuExec(Operator):
    bl_idname = Config.fb_fix_size_menu_exec_idname
    bl_label = "Change Frame size"
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = "Set Frame size based on images or scene render size"

    headnum: IntProperty(default=0)

    def draw(self, context):
        pass

    def execute(self, context):
        settings = get_main_settings()
        settings.tmp_headnum = self.headnum
        bpy.ops.wm.call_menu(
            'INVOKE_DEFAULT', name=Config.fb_fix_frame_size_menu_idname)
        return {'FINISHED'}


class FB_OT_ProperViewMenuExec(Operator):
    bl_idname = Config.fb_proper_view_menu_exec_idname
    bl_label = "View operations"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Delete the view or modify the image file path"

    headnum: IntProperty(default=0)
    camnum: IntProperty(default=0)

    def draw(self, context):
        pass

    def execute(self, context):
        settings = get_main_settings()
        settings.tmp_headnum = self.headnum
        settings.tmp_camnum = self.camnum
        bpy.ops.wm.call_menu(
            'INVOKE_DEFAULT', name=Config.fb_proper_view_menu_idname)
        return {'FINISHED'}


class FB_OT_ImproperViewMenuExec(Operator):
    bl_idname = Config.fb_improper_view_menu_exec_idname
    bl_label = "Possible Frame size issue detected"
    bl_options = {'REGISTER', 'INTERNAL'}  # UNDO
    bl_description = "Size of this image is different from the Frame size"

    headnum: IntProperty(default=0)
    camnum: IntProperty(default=0)

    def draw(self, context):
        pass

    def execute(self, context):
        settings = get_main_settings()
        settings.tmp_headnum = self.headnum
        settings.tmp_camnum = self.camnum
        bpy.ops.wm.call_menu(
            'INVOKE_DEFAULT', name=Config.fb_improper_view_menu_idname)
        return {'FINISHED'}


class FB_OT_ViewToFrameSize(Operator):
    bl_idname = Config.fb_view_to_frame_size_idname
    bl_label = "Set the Frame size using this view"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Set the Frame size using this view"

    headnum: IntProperty(default=0)
    camnum: IntProperty(default=0)

    def draw(self, context):
        pass

    def execute(self, context):
        # Current camera Background --> Render size
        manipulate.use_camera_frame_size(self.headnum, self.camnum)
        return {'FINISHED'}


class FB_OT_MostFrequentFrameSize(Operator):
    bl_idname = Config.fb_most_frequent_frame_size_idname
    bl_label = "Most frequent frame size"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Use most frequent image size"

    def draw(self, context):
        pass

    def execute(self, context):
        manipulate.auto_detect_frame_size()
        return {'FINISHED'}


class FB_OT_RenderSizeToFrameSize(Operator):
    bl_idname = Config.fb_render_size_to_frame_size_idname
    bl_label = "Scene Render size"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Use Scene render size"

    def draw(self, context):
        pass

    def execute(self, context):
        manipulate.use_render_frame_size()
        return {'FINISHED'}


class FB_OT_ReadExif(Operator):
    bl_idname = Config.fb_read_exif_idname
    bl_label = "Read EXIF"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Read EXIF"

    headnum: IntProperty(default=0)
    camnum: IntProperty(default=0)

    def draw(self, context):
        pass

    def execute(self, context):
        status = read_exif_from_camera(self.headnum, self.camnum)

        if status:
            self.report({'INFO'}, 'EXIF read success')
        else:
            self.report({'ERROR'},
                        'EXIF read failed. File is damaged or missing')
        return {'FINISHED'}


class FB_OT_ReadExifMenuExec(Operator):
    bl_idname = Config.fb_read_exif_menu_exec_idname
    bl_label = "Read EXIF"
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = "Select image to read EXIF"

    headnum: IntProperty(default=0)

    def draw(self, context):
        pass

    def execute(self, context):
        settings = get_main_settings()
        settings.tmp_headnum = self.headnum
        bpy.ops.wm.call_menu(
            'INVOKE_DEFAULT', name=Config.fb_read_exif_menu_idname)
        return {'FINISHED'}


class FB_OT_AddonSettings(Operator):
    bl_idname = Config.fb_addon_settings_idname
    bl_label = "Addon Settings"
    bl_options = {'REGISTER'}
    bl_description = "Open Addon Settings in Preferences window"

    def draw(self, context):
        pass

    def execute(self, context):
        bpy.ops.preferences.addon_show(module=Config.addon_name)
        return {'FINISHED'}


class FB_OT_BakeTexture(Operator):
    bl_idname = Config.fb_bake_tex_idname
    bl_label = "Bake Texture"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Bake the texture using all selected cameras. " \
                     "It can take a lot of time, be patient"

    headnum: IntProperty(default=0)

    def draw(self, context):
        pass

    def execute(self, context):
        settings = get_main_settings()
        tex_name = materials.bake_tex(
            self.headnum, Config.tex_builder_filename)

        if tex_name is None:
            return {'CANCELLED'}

        if settings.tex_auto_preview:
            mat = materials.show_texture_in_mat(
                tex_name, Config.tex_builder_matname)
            # Assign Material to Head Object
            materials.assign_mat(
                settings.get_head(self.headnum).headobj, mat)
            # Switch to Material Mode or Back
            materials.toggle_mode(('MATERIAL',))

        return {'FINISHED'}


class FB_OT_DeleteTexture(Operator):
    bl_idname = Config.fb_delete_texture_idname
    bl_label = "Delete texture"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Delete the created texture from the scene"

    def draw(self, context):
        pass

    def execute(self, context):
        materials.remove_tex_by_name(Config.tex_builder_filename)
        materials.remove_mat_by_name(Config.tex_builder_matname)
        op = getattr(get_operators(), Config.fb_show_solid_callname)
        op('EXEC_DEFAULT')
        return {'FINISHED'}


class FB_OT_ShowTexture(Operator):
    bl_idname = Config.fb_show_tex_idname
    bl_label = "Show Texture"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Create a material from the generated texture " \
                     "and apply it to the model"

    def draw(self, context):
        pass

    def execute(self, context):
        tex = materials.find_tex_by_name(Config.tex_builder_filename)
        if tex is None:
            return {'CANCELLED'}

        settings = get_main_settings()
        if settings.pinmode:
            FBLoader.out_pinmode(settings.current_headnum,
                                 settings.current_camnum)

        mat = materials.show_texture_in_mat(
            Config.tex_builder_filename, Config.tex_builder_matname)
        materials.assign_mat(
            settings.get_head(settings.current_headnum).headobj, mat)
        materials.switch_to_mode('MATERIAL')

        logger = logging.getLogger(__name__)
        logger.debug("SWITCH TO MATERIAL MODE WITH TEXTURE")
        return {'FINISHED'}


class FB_OT_ShowSolid(Operator):
    bl_idname = Config.fb_show_solid_idname
    bl_label = "Show Solid"
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = "Hide texture and go back to Solid mode"

    def draw(self, context):
        pass

    def execute(self, context):
        logger = logging.getLogger(__name__)
        logger.debug("SWITCH TO SOLID MODE")
        settings = get_main_settings()
        if settings.pinmode:
            FBLoader.out_pinmode(settings.current_headnum,
                                 settings.current_camnum)
        materials.switch_to_mode('SOLID')
        return {'FINISHED'}


class FB_OT_ExitPinmode(Operator):
    bl_idname = Config.fb_exit_pinmode_idname
    bl_label = "Exit Pin mode"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Exit Pin mode"

    def draw(self, context):
        pass

    def execute(self, context):
        settings = get_main_settings()
        if settings.pinmode:
            FBLoader.out_pinmode(settings.current_headnum,
                                 settings.current_camnum)
            bpy.ops.view3d.view_camera()
        return {'FINISHED'}


class FB_OT_OpenURL(bpy.types.Operator):
    bl_idname = Config.fb_open_url_idname
    bl_label = 'Open URL'
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = 'Open URL in web browser'

    url: bpy.props.StringProperty(name='URL', default='')

    def execute(self, context):
        bpy.ops.wm.url_open(url=self.url)
        return {'FINISHED'}


CLASSES_TO_REGISTER = (FB_OT_SelectHead,
                       FB_OT_DeleteHead,
                       FB_OT_SelectCamera,
                       FB_OT_CenterGeo,
                       FB_OT_Unmorph,
                       FB_OT_RemovePins,
                       FB_OT_WireframeColor,
                       FB_OT_FilterCameras,
                       FB_OT_AllViewsMenuExec,
                       FB_OT_ProperViewMenuExec,
                       FB_OT_ImproperViewMenuExec,
                       FB_OT_ViewToFrameSize,
                       FB_OT_MostFrequentFrameSize,
                       FB_OT_RenderSizeToFrameSize,
                       FB_OT_ReadExif,
                       FB_OT_ReadExifMenuExec,
                       FB_OT_DeleteCamera,
                       FB_OT_AddCamera,
                       FB_OT_AddonSettings,
                       FB_OT_BakeTexture,
                       FB_OT_DeleteTexture,
                       FB_OT_ShowTexture,
                       FB_OT_ShowSolid,
                       FB_OT_ExitPinmode,
                       FB_OT_OpenURL,
                       FB_OT_SetSensorWidth,
                       FB_OT_SensorSizeWindow,
                       FB_OT_FocalLengthMenuExec)
