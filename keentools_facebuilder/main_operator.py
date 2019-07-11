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
from bpy.types import Operator
from bpy.props import (
    StringProperty,
    IntProperty,
)
from . fbloader import FBLoader
from . fbdebug import FBDebug
from .config import get_main_settings, ErrorType
from . config import config


def check_settings():
    settings = get_main_settings()
    # Settings structure is broken
    if not settings.check_heads_and_cams():
        # Fix Heads and cameras
        heads_deleted, cams_deleted = settings.fix_heads()
        if heads_deleted == 0:
            warn = getattr(bpy.ops.wm, config.fb_warning_operator_callname)
            warn('INVOKE_DEFAULT', msg=ErrorType.SceneDamaged)
        return False
    return True


class OBJECT_OT_FBSelectCamera(Operator):
    bl_idname = config.fb_main_select_camera_idname
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

        if not check_settings():
            return {'CANCELLED'}

        # bpy.ops.object.select_all(action='DESELECT')
        cam = settings.heads[headnum].cameras[camnum].camobj
        cam.select_set(state=True)
        bpy.context.view_layer.objects.active = cam

        # Switch to camera
        if scene.camera != cam:
            cam.hide_viewport = False  # To allow switch
            bpy.ops.view3d.object_as_camera()
        else:
            # Toggle camera view
            bpy.ops.view3d.view_camera()  # if settings.pinmode

        # Add Background Image
        c = cam.data
        c.lens = settings.focal
        c.show_background_images = True
        if len(c.background_images) == 0:
            b = c.background_images.new()
        else:
            b = c.background_images[0]
        b.image = settings.heads[headnum].cameras[camnum].cam_image

        headobj = settings.heads[headnum].headobj
        bpy.context.view_layer.objects.active = headobj

        # Auto Call PinMode
        draw_op = getattr(bpy.ops.object, config.fb_draw_operator_callname)
        draw_op('INVOKE_DEFAULT', headnum=headnum, camnum=camnum)

        # === Debug only ===
        FBDebug.add_event_to_queue('SELECT_CAMERA', (headnum, camnum))
        FBDebug.add_event_to_queue('FORCE_SNAPSHOT', (headnum, camnum))
        FBDebug.make_snapshot()
        # === Debug only ===
        return {'FINISHED'}


class OBJECT_OT_FBCenterGeo(Operator):
    bl_idname = config.fb_main_center_geo_idname
    bl_label = "Center Geo"
    bl_options = {'REGISTER', 'UNDO'}
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
        kid = FBLoader.keyframe_by_camnum(headnum, camnum)
        fb.center_model_mat(kid)
        print('CENTERED GEO', headnum, camnum)
        FBLoader.fb_save(headnum, camnum)
        FBLoader.fb_redraw(headnum, camnum)
        # === Debug only ===
        FBDebug.add_event_to_queue('CENTER_GEO', (0, 0))
        FBDebug.add_event_to_queue('FORCE_SNAPSHOT', (0, 0))
        FBDebug.make_snapshot()
        return {'FINISHED'}


class OBJECT_OT_FBUnmorph(Operator):
    bl_idname = config.fb_main_unmorph_idname
    bl_label = "Unmorph"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Unmorph shape to default mesh. It will return back when you move any pin."

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
        kid = FBLoader.keyframe_by_camnum(headnum, camnum)
        # TODO: Unmorph method call
        fb.unmorph()
        print('UNMORPH', headnum, camnum)
        FBLoader.fb_save(headnum, camnum)
        FBLoader.fb_redraw(headnum, camnum)
        return {'FINISHED'}


class OBJECT_OT_FBRemovePins(Operator):
    bl_idname = config.fb_main_remove_pins_idname
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
        kid = FBLoader.keyframe_by_camnum(headnum, camnum)
        fb.remove_pins(kid)
        # Added but don't work
        fb.solve_for_current_pins(kid)
        print('PINS REMOVED')
        FBLoader.fb_save(headnum, camnum)
        FBLoader.fb_redraw(headnum, camnum)
        FBLoader.update_pins_count(headnum, camnum)
        # === Debug only ===
        FBDebug.add_event_to_queue('REMOVE_PINS', (0, 0))
        FBDebug.add_event_to_queue('FORCE_SNAPSHOT', (0, 0))
        FBDebug.make_snapshot()
        # === Debug only ===
        return {'FINISHED'}
