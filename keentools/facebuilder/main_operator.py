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
from bpy.props import (
    StringProperty,
    IntProperty,
    BoolProperty
)
from bpy.types import Operator

from ..utils.kt_logging import KTLogger
from ..addon_config import (Config,
                            get_operator,
                            show_user_preferences,
                            show_tool_preferences)
from ..utils.bpy_common import (bpy_background_mode,
                                bpy_show_addon_preferences,
                                bpy_view_camera)
from ..facebuilder_config import FBConfig, get_fb_settings
from .fbloader import FBLoader
from ..utils import manipulate, materials, coords, images
from ..utils.attrs import get_obj_collection, safe_delete_collection
from ..facebuilder.utils.exif_reader import (update_exif_sizes_message,
                                             copy_exif_parameters_from_camera_to_head)
from .utils.manipulate import check_settings
from .utils.manipulate import push_head_in_undo_history
from ..utils.operator_action import (create_blendshapes,
                                     delete_blendshapes,
                                     load_animation_from_csv,
                                     create_example_animation,
                                     reset_blendshape_values,
                                     clear_animation,
                                     export_head_to_fbx,
                                     update_blendshapes,
                                     unhide_head,
                                     reconstruct_by_mesh)
from ..utils.localview import exit_area_localview
from .ui_strings import buttons


_log = KTLogger(__name__)


class ButtonOperator:
    bl_options = {'REGISTER', 'UNDO'}

    def draw(self, context):
        pass


class ActiveButtonOperator(ButtonOperator):
    active_button: BoolProperty(default=True)


class FB_OT_SelectHead(Operator):
    bl_idname = FBConfig.fb_select_head_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'UNDO'}

    headnum: IntProperty(default=0)

    def draw(self, context):
        pass

    def execute(self, context):
        if not check_settings():
            return {'CANCELLED'}

        settings = get_fb_settings()
        head = settings.get_head(self.headnum)

        manipulate.center_viewports_on_object(head.headobj)
        return {'FINISHED'}


class FB_OT_DeleteHead(Operator):
    bl_idname = FBConfig.fb_delete_head_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'UNDO'}

    headnum: IntProperty(default=0)

    def draw(self, context):
        pass

    def execute(self, context):
        if not check_settings():
            return {'CANCELLED'}

        settings = get_fb_settings()
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
            bpy.data.objects.remove(head.headobj)  # , do_unlink=True
            safe_delete_collection(col)
        except Exception:
            pass
        settings.heads.remove(self.headnum)
        return {'FINISHED'}


class FB_OT_SelectCamera(Operator):
    bl_idname = FBConfig.fb_select_camera_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'INTERNAL'}

    headnum: IntProperty(default=0)
    camnum: IntProperty(default=0)

    def draw(self, context):
        pass

    def execute(self, context):
        if not check_settings():
            return {'CANCELLED'}

        settings = get_fb_settings()
        head = settings.get_head(self.headnum)
        camera = head.get_camera(self.camnum)

        copy_exif_parameters_from_camera_to_head(camera, head)
        update_exif_sizes_message(self.headnum, camera.cam_image)

        pinmode_op = get_operator(FBConfig.fb_pinmode_idname)
        if not bpy_background_mode():
            try:
                pinmode_op('INVOKE_DEFAULT',
                           headnum=self.headnum, camnum=self.camnum)
            except Exception as err:
                self.report({'ERROR'}, str(err))

        return {'FINISHED'}


class FB_OT_CenterGeo(Operator):
    bl_idname = FBConfig.fb_center_geo_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'INTERNAL'}

    headnum: IntProperty(default=0)
    camnum: IntProperty(default=0)

    def draw(self, context):
        pass

    def execute(self, context):
        if not check_settings():
            return {'CANCELLED'}

        settings = get_fb_settings()
        headnum = self.headnum
        camnum = self.camnum

        FBLoader.center_geo_camera_projection(headnum, camnum)
        FBLoader.save_fb_serial_and_image_pathes(headnum)
        FBLoader.place_camera(headnum, camnum)

        push_head_in_undo_history(settings.get_head(headnum), 'Reset Camera.')

        FBLoader.update_viewport_shaders(context.area, headnum, camnum)
        return {'FINISHED'}


class FB_OT_Unmorph(Operator):
    bl_idname = FBConfig.fb_unmorph_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'INTERNAL'}

    headnum: IntProperty(default=0)
    camnum: IntProperty(default=0)

    def draw(self, context):
        pass

    def execute(self, context):
        if not check_settings():
            return {'CANCELLED'}
        settings = get_fb_settings()
        headnum = self.headnum
        camnum = self.camnum
        head = settings.get_head(headnum)

        fb = FBLoader.get_builder()
        fb.unmorph()

        for i, camera in enumerate(head.cameras):
            fb.remove_pins(camera.get_keyframe())
            camera.pins_count = 0

        coords.update_head_mesh_non_neutral(fb, head)
        FBLoader.save_fb_serial_and_image_pathes(headnum)

        if settings.pinmode:
            FBLoader.load_pins_into_viewport(headnum, camnum)
            FBLoader.update_viewport_shaders(context.area, headnum, camnum)

        push_head_in_undo_history(settings.get_head(headnum), 'After Reset')

        return {'FINISHED'}


class FB_OT_RemovePins(Operator):
    bl_idname = FBConfig.fb_remove_pins_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'INTERNAL'}

    headnum: IntProperty(default=0)
    camnum: IntProperty(default=0)

    def draw(self, context):
        pass

    def execute(self, context):
        settings = get_fb_settings()

        if not settings.pinmode:
            return {'CANCELLED'}

        headnum = self.headnum
        camnum = self.camnum

        fb = FBLoader.get_builder()
        kid = settings.get_keyframe(headnum, camnum)

        fb.remove_pins(kid)
        FBLoader.solve(headnum, camnum)

        FBLoader.save_fb_serial_and_image_pathes(headnum)
        FBLoader.update_camera_pins_count(headnum, camnum)
        FBLoader.load_pins_into_viewport(headnum, camnum)
        FBLoader.update_viewport_shaders(context.area, headnum, camnum)

        push_head_in_undo_history(settings.get_head(headnum), 'Remove pins')

        return {'FINISHED'}


class FB_OT_WireframeColor(Operator):
    bl_idname = FBConfig.fb_wireframe_color_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    action: StringProperty(name="Action Name")

    def draw(self, context):
        pass

    def execute(self, context):
        def _setup_colors_from_scheme(name):
            settings = get_fb_settings()
            settings.wireframe_color = FBConfig.color_schemes[name][0]
            settings.wireframe_special_color = FBConfig.color_schemes[name][1]

        if self.action == 'wireframe_red':
            _setup_colors_from_scheme('red')
        elif self.action == 'wireframe_green':
            _setup_colors_from_scheme('green')
        elif self.action == 'wireframe_blue':
            _setup_colors_from_scheme('blue')
        elif self.action == 'wireframe_cyan':
            _setup_colors_from_scheme('cyan')
        elif self.action == 'wireframe_magenta':
            _setup_colors_from_scheme('magenta')
        elif self.action == 'wireframe_yellow':
            _setup_colors_from_scheme('yellow')
        elif self.action == 'wireframe_black':
            _setup_colors_from_scheme('black')
        elif self.action == 'wireframe_white':
            _setup_colors_from_scheme('white')

        return {'FINISHED'}


class FB_OT_FilterCameras(Operator):
    bl_idname = FBConfig.fb_filter_cameras_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    action: StringProperty(name="Action Name")
    headnum: IntProperty(default=0)

    def draw(self, context):
        pass

    def execute(self, context):
        settings = get_fb_settings()

        if self.action == 'select_all_cameras':
            for c in settings.get_head(self.headnum).cameras:
                c.use_in_tex_baking = True

        elif self.action == 'deselect_all_cameras':
            for c in settings.get_head(self.headnum).cameras:
                c.use_in_tex_baking = False

        return {'FINISHED'}


class FB_OT_DeleteCamera(Operator):
    bl_idname = FBConfig.fb_delete_camera_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'UNDO'}

    headnum: IntProperty(default=0)
    camnum: IntProperty(default=0)

    def draw(self, context):
        pass

    def execute(self, context):
        if not check_settings():
            return {'CANCELLED'}

        settings = get_fb_settings()
        headnum = self.headnum
        camnum = self.camnum

        head = settings.get_head(headnum)
        if head is None:
            return {'CANCELLED'}
        camera = head.get_camera(camnum)
        if camera is None:
            return {'CANCELLED'}

        kid = camera.get_keyframe()
        if head.get_expression_view_keyframe() == kid:
            head.set_neutral_expression_view()

        fb = FBLoader.get_builder()
        fb.remove_keyframe(kid)

        camera.delete_cam_image()
        camera.delete_camobj()
        head.cameras.remove(camnum)

        if settings.current_camnum > camnum:
            settings.current_camnum -= 1
        elif settings.current_camnum == camnum:
            settings.current_camnum = -1

        FBLoader.save_fb_serial_and_image_pathes(headnum)

        _log.output(f'CAMERA H:{headnum} C:{camnum} REMOVED')
        return {'FINISHED'}


class FB_OT_ProperViewMenuExec(Operator):
    bl_idname = FBConfig.fb_proper_view_menu_exec_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'UNDO'}

    headnum: IntProperty(default=0)
    camnum: IntProperty(default=0)

    def draw(self, context):
        pass

    def execute(self, context):
        settings = get_fb_settings()
        settings.tmp_headnum = self.headnum
        settings.tmp_camnum = self.camnum
        bpy.ops.wm.call_menu(
            'INVOKE_DEFAULT', name=FBConfig.fb_proper_view_menu_idname)
        return {'FINISHED'}


class FB_OT_AddonSetupDefaults(Operator):
    bl_idname = FBConfig.fb_addon_setup_defaults_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER'}

    def draw(self, context):
        pass

    def execute(self, context):
        show_user_preferences(facebuilder=True, geotracker=False)
        show_tool_preferences(facebuilder=True, geotracker=False)
        bpy_show_addon_preferences()
        return {'FINISHED'}


class FB_OT_BakeTexture(Operator):
    bl_idname = FBConfig.fb_bake_tex_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'UNDO'}

    headnum: IntProperty(default=0)

    def draw(self, context):
        pass

    def execute(self, context):
        settings = get_fb_settings()
        head = settings.get_head(self.headnum)
        texture_baked = materials.bake_tex(
            self.headnum, head.preview_texture_name())

        if not texture_baked:
            return {'CANCELLED'}

        if settings.tex_auto_preview:
            mat = materials.show_texture_in_mat(
                head.preview_texture_name(),
                head.preview_material_name())
            materials.assign_material_to_object(head.headobj, mat)
            materials.toggle_mode(('MATERIAL',))

            if settings.pinmode:
                settings.force_out_pinmode = True
                if head.should_use_emotions():
                    bpy_view_camera()

        return {'FINISHED'}


class FB_OT_DeleteTexture(Operator):
    bl_idname = FBConfig.fb_delete_texture_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'UNDO'}

    headnum: IntProperty(default=0)

    def draw(self, context):
        pass

    def execute(self, context):
        settings = get_fb_settings()
        head = settings.get_head(self.headnum)
        if head is None:
            return {'CANCELLED'}
        images.remove_bpy_image_by_name(head.preview_texture_name())
        materials.remove_mat_by_name(head.preview_material_name())
        return {'FINISHED'}


class FB_OT_RotateImageCW(Operator):
    bl_idname = FBConfig.fb_rotate_image_cw_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'UNDO'}

    headnum: IntProperty(default=0)
    camnum: IntProperty(default=0)

    def draw(self, context):
        pass

    def execute(self, context):
        settings = get_fb_settings()
        camera = settings.get_camera(self.headnum, self.camnum)
        camera.rotate_background_image(1)
        camera.update_scene_frame_size()
        camera.update_background_image_scale()
        FBLoader.save_fb_serial_and_image_pathes(self.headnum)
        return {'FINISHED'}


class FB_OT_RotateImageCCW(Operator):
    bl_idname = FBConfig.fb_rotate_image_ccw_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'UNDO'}

    headnum: IntProperty(default=0)
    camnum: IntProperty(default=0)

    def draw(self, context):
        pass

    def execute(self, context):
        settings = get_fb_settings()
        camera = settings.get_camera(self.headnum, self.camnum)
        camera.rotate_background_image(-1)
        camera.update_scene_frame_size()
        camera.update_background_image_scale()
        FBLoader.save_fb_serial_and_image_pathes(self.headnum)
        return {'FINISHED'}


class FB_OT_ResetImageRotation(Operator):
    bl_idname = FBConfig.fb_reset_image_rotation_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'UNDO'}

    headnum: IntProperty(default=0)
    camnum: IntProperty(default=0)

    def draw(self, context):
        pass

    def execute(self, context):
        settings = get_fb_settings()
        camera = settings.get_camera(self.headnum, self.camnum)
        camera.reset_background_image_rotation()
        camera.update_scene_frame_size()
        camera.update_background_image_scale()
        FBLoader.save_fb_serial_and_image_pathes(self.headnum)
        return {'FINISHED'}


class FB_OT_ResetExpression(Operator):
    bl_idname = FBConfig.fb_reset_expression_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'UNDO'}

    headnum: IntProperty(default=0)
    camnum: IntProperty(default=0)

    def draw(self, context):
        pass

    def execute(self, context):
        settings = get_fb_settings()
        head = settings.get_head(self.headnum)

        if not settings.pinmode:
            return {'CANCELLED'}
        if head is None:
            return {'CANCELLED'}
        if not head.has_camera(settings.current_camnum):
            return {'CANCELLED'}

        FBLoader.load_model(self.headnum)
        fb = FBLoader.get_builder()
        fb.reset_to_neutral_emotions(head.get_keyframe(self.camnum))

        FBLoader.save_fb_serial_and_image_pathes(self.headnum)
        coords.update_head_mesh_non_neutral(fb, head)
        FBLoader.update_viewport_shaders(context.area, self.headnum, self.camnum)

        push_head_in_undo_history(head, 'Reset Expression.')

        return {'FINISHED'}


class FB_OT_ShowTexture(Operator):
    bl_idname = FBConfig.fb_show_tex_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'UNDO'}

    def draw(self, context):
        pass

    def execute(self, context):
        settings = get_fb_settings()
        head = settings.get_head(settings.current_headnum)
        if head is None:
            return {'CANCELLED'}

        tex = materials.find_bpy_image_by_name(head.preview_texture_name())
        if tex is None:
            return {'CANCELLED'}

        if settings.pinmode:
            FBLoader.out_pinmode(settings.current_headnum)
            exit_area_localview(context.area)

        mat = materials.show_texture_in_mat(
            head.preview_texture_name(), head.preview_material_name())
        materials.assign_material_to_object(head.headobj, mat)
        materials.switch_to_mode('MATERIAL')

        _log.output('SWITCH TO MATERIAL MODE WITH TEXTURE')
        return {'FINISHED'}


class FB_OT_ShowSolid(Operator):
    bl_idname = FBConfig.fb_show_solid_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'INTERNAL'}

    def draw(self, context):
        pass

    def execute(self, context):
        _log.output('SWITCH TO SOLID MODE')
        settings = get_fb_settings()
        if settings.pinmode:
            FBLoader.out_pinmode(settings.current_headnum)
            exit_area_localview(context.area)
        materials.switch_to_mode('SOLID')
        return {'FINISHED'}


class FB_OT_ExitPinmode(Operator):
    bl_idname = FBConfig.fb_exit_pinmode_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'UNDO'}

    def draw(self, context):
        pass

    def execute(self, context):
        settings = get_fb_settings()
        if settings.pinmode:
            settings.force_out_pinmode = True
        return {'FINISHED'}


class FB_OT_CreateBlendshapes(ButtonOperator, Operator):
    bl_idname = FBConfig.fb_create_blendshapes_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        return create_blendshapes(self)


class FB_OT_DeleteBlendshapes(ActiveButtonOperator, Operator):
    bl_idname = FBConfig.fb_delete_blendshapes_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        if not self.active_button:
            return {'CANCELLED'}
        return delete_blendshapes(self)


class FB_OT_LoadAnimationFromCSV(ButtonOperator, Operator):
    bl_idname = FBConfig.fb_load_animation_from_csv_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        return load_animation_from_csv(self)


class FB_OT_CreateExampleAnimation(ActiveButtonOperator, Operator):
    bl_idname = FBConfig.fb_create_example_animation_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        if not self.active_button:
            return {'CANCELLED'}
        return create_example_animation(self)


class FB_OT_ResetBlendshapeValues(ButtonOperator, Operator):
    bl_idname = FBConfig.fb_reset_blendshape_values_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        return reset_blendshape_values(self)


class FB_OT_ClearAnimation(ActiveButtonOperator, Operator):
    bl_idname = FBConfig.fb_clear_animation_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        if not self.active_button:
            return {'CANCELLED'}
        return clear_animation(self)


class FB_OT_ExportHeadToFBX(ButtonOperator, Operator):
    bl_idname = FBConfig.fb_export_head_to_fbx_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        settings = get_fb_settings()
        if settings.pinmode:
            FBLoader.out_pinmode(settings.current_headnum)
            exit_area_localview(context.area)

        return export_head_to_fbx(self)


class FB_OT_UpdateBlendshapes(ButtonOperator, Operator):
    bl_idname = FBConfig.fb_update_blendshapes_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        return update_blendshapes(self)


class FB_OT_UnhideHead(ButtonOperator, Operator):
    bl_idname = FBConfig.fb_unhide_head_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        return unhide_head(self, context)


class FB_OT_ReconstructHead(ButtonOperator, Operator):
    bl_idname = FBConfig.fb_reconstruct_head_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        return reconstruct_by_mesh()


class FB_OT_DefaultPinSettings(ButtonOperator, Operator):
    bl_idname = FBConfig.fb_default_pin_settings_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        settings = get_fb_settings()
        prefs = settings.preferences()
        settings.pin_size = prefs.pin_size
        settings.pin_sensitivity = prefs.pin_sensitivity
        return {'FINISHED'}


class FB_OT_DefaultWireframeSettings(ButtonOperator, Operator):
    bl_idname = FBConfig.fb_default_wireframe_settings_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        settings = get_fb_settings()
        prefs = settings.preferences()
        settings.wireframe_color = prefs.fb_wireframe_color
        settings.wireframe_special_color = prefs.fb_wireframe_special_color
        settings.wireframe_midline_color = prefs.fb_wireframe_midline_color
        settings.wireframe_opacity = prefs.fb_wireframe_opacity
        return {'FINISHED'}


class FB_OT_SelectCurrentHead(ButtonOperator, Operator):
    bl_idname = FBConfig.fb_select_current_head_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    headnum: IntProperty(default=0)

    def execute(self, context):
        op = get_operator(FBConfig.fb_select_head_idname)
        op('EXEC_DEFAULT', headnum=self.headnum)
        return {'FINISHED'}


class FB_OT_SelectCurrentCamera(ButtonOperator, Operator):
    bl_idname = FBConfig.fb_select_current_camera_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        op = get_operator(FBConfig.fb_exit_pinmode_idname)
        op('EXEC_DEFAULT')
        return {'FINISHED'}


class FB_OT_ResetToneGain(ButtonOperator, Operator):
    bl_idname = FBConfig.fb_reset_tone_exposure_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    headnum: IntProperty(default=0)
    camnum: IntProperty(default=0)

    def execute(self, context):
        settings = get_fb_settings()
        cam = settings.get_camera(self.headnum, self.camnum)
        cam.tone_exposure = Config.default_tone_exposure
        return {'FINISHED'}


class FB_OT_ResetToneGamma(ButtonOperator, Operator):
    bl_idname = FBConfig.fb_reset_tone_gamma_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    headnum: IntProperty(default=0)
    camnum: IntProperty(default=0)

    def execute(self, context):
        settings = get_fb_settings()
        cam = settings.get_camera(self.headnum, self.camnum)
        cam.tone_gamma = Config.default_tone_gamma
        return {'FINISHED'}


CLASSES_TO_REGISTER = (FB_OT_SelectHead,
                       FB_OT_SelectCurrentHead,
                       FB_OT_DeleteHead,
                       FB_OT_SelectCamera,
                       FB_OT_SelectCurrentCamera,
                       FB_OT_CenterGeo,
                       FB_OT_Unmorph,
                       FB_OT_RemovePins,
                       FB_OT_WireframeColor,
                       FB_OT_FilterCameras,
                       FB_OT_ProperViewMenuExec,
                       FB_OT_DeleteCamera,
                       FB_OT_AddonSetupDefaults,
                       FB_OT_BakeTexture,
                       FB_OT_DeleteTexture,
                       FB_OT_RotateImageCW,
                       FB_OT_RotateImageCCW,
                       FB_OT_ResetImageRotation,
                       FB_OT_ResetExpression,
                       FB_OT_ShowTexture,
                       FB_OT_ShowSolid,
                       FB_OT_ExitPinmode,
                       FB_OT_CreateBlendshapes,
                       FB_OT_DeleteBlendshapes,
                       FB_OT_LoadAnimationFromCSV,
                       FB_OT_CreateExampleAnimation,
                       FB_OT_ResetBlendshapeValues,
                       FB_OT_ClearAnimation,
                       FB_OT_ExportHeadToFBX,
                       FB_OT_UpdateBlendshapes,
                       FB_OT_UnhideHead,
                       FB_OT_ReconstructHead,
                       FB_OT_DefaultPinSettings,
                       FB_OT_DefaultWireframeSettings,
                       FB_OT_ResetToneGain,
                       FB_OT_ResetToneGamma)
