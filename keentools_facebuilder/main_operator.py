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

from . utils.manipulate import check_settings
from . utils import manipulate
from . fbloader import FBLoader
from . fbdebug import FBDebug
from . config import get_main_settings, Config


class OBJECT_OT_FBSelectCamera(Operator):
    bl_idname = Config.fb_main_select_camera_idname
    bl_label = "Pin Mode"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Switch to pin-mode for this camera"

    headnum: IntProperty(default=0)
    camnum: IntProperty(default=0)

    # This draw overrides standard operator panel
    def draw(self, context):
        pass

    def execute(self, context):
        scene = context.scene
        settings = get_main_settings()
        headnum = self.headnum
        camnum = self.camnum
        head = settings.heads[headnum]

        if not check_settings():
            return {'CANCELLED'}

        # bpy.ops.object.select_all(action='DESELECT')
        cam = head.cameras[camnum].camobj
        cam.select_set(state=True)
        bpy.context.view_layer.objects.active = cam

        # Switch to camera
        if (scene.camera == cam) and settings.pinmode:
            bpy.ops.view3d.view_camera()
        else:
            cam.hide_set(False)  # To allow switch
            if not bpy.app.background:
                bpy.ops.view3d.object_as_camera()

        # Add Background Image
        c = cam.data
        c.lens = head.focal
        c.show_background_images = True
        if len(c.background_images) == 0:
            b = c.background_images.new()
        else:
            b = c.background_images[0]
        b.image = head.cameras[camnum].cam_image

        headobj = head.headobj
        bpy.context.view_layer.objects.active = headobj

        # Auto Call PinMode
        draw_op = getattr(bpy.ops.object, Config.fb_draw_operator_callname)
        draw_op('INVOKE_DEFAULT', headnum=headnum, camnum=camnum)

        # === Debug only ===
        FBDebug.add_event_to_queue('SELECT_CAMERA', (headnum, camnum))
        FBDebug.add_event_to_queue('FORCE_SNAPSHOT', (headnum, camnum))
        FBDebug.make_snapshot()
        # === Debug only ===
        return {'FINISHED'}


class OBJECT_OT_FBCenterGeo(Operator):
    bl_idname = Config.fb_main_center_geo_idname
    bl_label = "Center Geo"
    bl_options = {'REGISTER'}  # 'UNDO'
    bl_description = "Place model geometry central in camera view"

    headnum: IntProperty(default=0)
    camnum: IntProperty(default=0)

    # This draw overrides standard operator panel
    def draw(self, context):
        pass

    def execute(self, context):
        settings = get_main_settings()
        headnum = self.headnum
        camnum = self.camnum

        if not settings.pinmode:
            return {'CANCELLED'}

        if not check_settings():
            return {'CANCELLED'}

        fb = FBLoader.get_builder()
        kid = manipulate.keyframe_by_camnum(headnum, camnum)
        fb.center_model_mat(kid)
        FBLoader.fb_save(headnum, camnum)
        FBLoader.fb_redraw(headnum, camnum)
        # === Debug only ===
        FBDebug.add_event_to_queue('CENTER_GEO', (0, 0))
        FBDebug.add_event_to_queue('FORCE_SNAPSHOT', (0, 0))
        FBDebug.make_snapshot()
        return {'FINISHED'}


class OBJECT_OT_FBUnmorph(Operator):
    bl_idname = Config.fb_main_unmorph_idname
    bl_label = "Unmorph"
    bl_options = {'REGISTER'}  # 'UNDO'
    bl_description = "Unmorph shape to default mesh. It will return back " \
                     "when you move any pin."

    headnum: IntProperty(default=0)
    camnum: IntProperty(default=0)

    # This draw overrides standard operator panel
    def draw(self, context):
        pass

    def execute(self, context):
        scene = context.scene
        settings = get_main_settings()
        headnum = self.headnum
        camnum = self.camnum

        if not settings.pinmode:
            return {'CANCELLED'}

        if not check_settings():
            return {'CANCELLED'}

        fb = FBLoader.get_builder()
        kid = manipulate.keyframe_by_camnum(headnum, camnum)
        fb.unmorph()
        FBLoader.fb_save(headnum, camnum)
        FBLoader.fb_redraw(headnum, camnum)
        return {'FINISHED'}


class OBJECT_OT_FBRemovePins(Operator):
    bl_idname = Config.fb_main_remove_pins_idname
    bl_label = "Remove Pins"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Place model geometry central in camera view"

    headnum: IntProperty(default=0)
    camnum: IntProperty(default=0)

    # This draw overrides standard operator panel
    def draw(self, context):
        pass

    def execute(self, context):
        scene = context.scene
        settings = get_main_settings()
        headnum = self.headnum
        camnum = self.camnum

        if not settings.pinmode:
            return {'CANCELLED'}

        if not check_settings():
            return {'CANCELLED'}

        fb = FBLoader.get_builder()
        kid = manipulate.keyframe_by_camnum(headnum, camnum)
        fb.remove_pins(kid)
        # Added but don't work
        fb.solve_for_current_pins(kid)
        FBLoader.fb_save(headnum, camnum)
        FBLoader.fb_redraw(headnum, camnum)
        FBLoader.update_pins_count(headnum, camnum)
        # === Debug only ===
        FBDebug.add_event_to_queue('REMOVE_PINS', (0, 0))
        FBDebug.add_event_to_queue('FORCE_SNAPSHOT', (0, 0))
        FBDebug.make_snapshot()
        # === Debug only ===
        return {'FINISHED'}


class OBJECT_OT_FBWireframeColor(Operator):
    bl_idname = Config.fb_main_wireframe_color_idname
    bl_label = "Wireframe Color"
    bl_options = {'REGISTER'}  # 'UNDO'
    bl_description = "Change wireframe color according to scheme"

    action: StringProperty(name="Action Name")

    # This draw overrides standard operator panel
    def draw(self, context):
        pass

    def execute(self, context):
        settings = get_main_settings()

        if self.action == "wireframe_red":
            # settings.wireframe_color = config.red_color
            settings.wireframe_color = Config.red_scheme1
            settings.wireframe_special_color = Config.red_scheme2
        elif self.action == "wireframe_green":
            # settings.wireframe_color = config.green_color
            settings.wireframe_color = Config.green_scheme1
            settings.wireframe_special_color = Config.green_scheme2
        elif self.action == "wireframe_blue":
            # settings.wireframe_color = config.blue_color
            settings.wireframe_color = Config.blue_scheme1
            settings.wireframe_special_color = Config.blue_scheme2
        elif self.action == "wireframe_cyan":
            # settings.wireframe_color = config.cyan_color
            settings.wireframe_color = Config.cyan_scheme1
            settings.wireframe_special_color = Config.cyan_scheme2
        elif self.action == "wireframe_magenta":
            # settings.wireframe_color = config.magenta_color
            settings.wireframe_color = Config.magenta_scheme1
            settings.wireframe_special_color = Config.magenta_scheme2
        elif self.action == "wireframe_yellow":
            # settings.wireframe_color = config.yellow_color
            settings.wireframe_color = Config.yellow_scheme1
            settings.wireframe_special_color = Config.yellow_scheme2
        elif self.action == "wireframe_black":
            # settings.wireframe_color = config.black_color
            settings.wireframe_color = Config.black_scheme1
            settings.wireframe_special_color = Config.black_scheme2
        elif self.action == "wireframe_white":
            # settings.wireframe_color = config.white_color
            settings.wireframe_color = Config.white_scheme1
            settings.wireframe_special_color = Config.white_scheme2

        return {'FINISHED'}


class OBJECT_OT_FBFilterCameras(Operator):
    bl_idname = Config.fb_main_filter_cameras_idname
    bl_label = "Camera Filter"
    bl_options = {'REGISTER'}  # 'UNDO'
    bl_description = "Select cameras to use for texture baking"

    action: StringProperty(name="Action Name")
    headnum: IntProperty(default=0)

    # This draw overrides standard operator panel
    def draw(self, context):
        pass

    def execute(self, context):
        settings = get_main_settings()

        if self.action == "select_all_cameras":
            for c in settings.heads[self.headnum].cameras:
                c.use_in_tex_baking = True

        elif self.action == "deselect_all_cameras":
            for c in settings.heads[self.headnum].cameras:
                c.use_in_tex_baking = False

        return {'FINISHED'}


class OBJECT_OT_FBDeleteCamera(Operator):
    bl_idname = Config.fb_main_delete_camera_idname
    bl_label = "Delete Camera"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Delete this camera object from scene"

    headnum: IntProperty(default=0)
    camnum: IntProperty(default=0)

    # This draw overrides standard operator panel
    def draw(self, context):
        pass

    def execute(self, context):
        logger = logging.getLogger(__name__)
        settings = get_main_settings()
        headnum = self.headnum
        camnum = self.camnum
        if not settings.pinmode:
            fb = FBLoader.get_builder()
            head = settings.heads[headnum]
            kid = manipulate.keyframe_by_camnum(headnum, camnum)
            camobj = head.cameras[camnum].camobj
            fb.remove_keyframe(kid)
            FBLoader.fb_save(headnum, camnum)
            # Delete camera object from scene
            bpy.data.objects.remove(camobj, do_unlink=True)
            # Delete link from list
            head.cameras.remove(camnum)
            logger.debug("CAMERA REMOVED")
        return {'FINISHED'}


class OBJECT_OT_FBAddCamera(Operator):
    bl_idname = Config.fb_main_add_camera_idname
    bl_label = "Add Camera"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Add new camera without image (Not recommended). \n" \
                     "Use 'Open Sequence' button instead."
    headnum: IntProperty(default=0)

    # This draw overrides standard operator panel
    def draw(self, context):
        pass

    def execute(self, context):
        settings = get_main_settings()
        headnum = self.headnum
        if settings.heads[headnum].cameras:
            FBLoader.load_only(headnum)
        camera = FBLoader.add_camera(headnum, None)
        FBLoader.set_keentools_version(camera.camobj)
        FBLoader.save_only(headnum)
        return {'FINISHED'}


class OBJECT_OT_FBFixSize(Operator):
    bl_idname = Config.fb_main_fix_size_idname
    bl_label = "Fix Size"
    bl_options = {'REGISTER'}
    bl_description = "Fix frame Width and High parameters for all cameras"
    headnum: IntProperty(default=0)

    # This draw overrides standard operator panel
    def draw(self, context):
        pass

    def execute(self, context):
        bpy.ops.wm.call_menu(
            'INVOKE_DEFAULT', name=Config.fb_fix_frame_menu_idname)
        return {'FINISHED'}


class OBJECT_OT_FBCameraFixSize(Operator):
    bl_idname = Config.fb_main_camera_fix_size_idname
    bl_label = "Fix Size by Camera"
    bl_options = {'REGISTER'}
    bl_description = "Fix frame Width and High parameters for all cameras"

    headnum: IntProperty(default=0)
    camnum: IntProperty(default=0)

    # This draw overrides standard operator panel
    def draw(self, context):
        pass

    def execute(self, context):
        settings = get_main_settings()
        settings.tmp_headnum = self.headnum
        settings.tmp_camnum = self.camnum
        bpy.ops.wm.call_menu(
            'INVOKE_DEFAULT', name=Config.fb_fix_camera_frame_menu_idname)
        return {'FINISHED'}


class OBJECT_OT_FBAddonSettings(Operator):
    bl_idname = Config.fb_main_addon_settings_idname
    bl_label = "Addon Settings"
    bl_options = {'REGISTER'}
    bl_description = "Open Addon Settings in Preferences window"

    # This draw overrides standard operator panel
    def draw(self, context):
        pass

    def execute(self, context):
        bpy.ops.preferences.addon_show(module=Config.addon_name)
        return {'FINISHED'}


class OBJECT_OT_FBBakeTexture(Operator):
    bl_idname = Config.fb_main_bake_tex_idname
    bl_label = "Bake Texture"
    bl_options = {'REGISTER'}
    bl_description = "Bake the texture using all selected cameras. " \
                     "It can take a lot of time, be patient"

    # This draw overrides standard operator panel
    def draw(self, context):
        pass

    def execute(self, context):
        settings = get_main_settings()
        op = getattr(bpy.ops.object, Config.fb_actor_operator_callname)
        op('INVOKE_DEFAULT', action="bake_tex",
           headnum=settings.current_headnum)
        return {'FINISHED'}


class OBJECT_OT_FBShowTexture(Operator):
    bl_idname = Config.fb_main_show_tex_idname
    bl_label = "Show Texture"
    bl_options = {'REGISTER'}
    bl_description = "Switch to Material Mode and creates demo-shader " \
                     "using Baked Texture. Second call reverts back to Solid"

    # This draw overrides standard operator panel
    def draw(self, context):
        pass

    def execute(self, context):
        settings = get_main_settings()
        if settings.pinmode:
            FBLoader.out_pinmode(settings.current_headnum,
                                 settings.current_camnum)
        op = getattr(bpy.ops.object, Config.fb_actor_operator_callname)
        op('INVOKE_DEFAULT', action='show_tex',
           headnum=settings.current_headnum)
        return {'FINISHED'}
