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

import re

from bpy.props import (
    StringProperty,
    IntProperty,
    BoolProperty
)
from bpy.types import Operator

from ..utils.kt_logging import KTLogger
from ..addon_config import (Config,
                            fb_settings,
                            get_operator,
                            show_user_preferences,
                            show_tool_preferences)
from ..utils.bpy_common import (bpy_background_mode,
                                bpy_show_addon_preferences,
                                bpy_view_camera,
                                bpy_remove_object,
                                bpy_call_menu)
from ..facebuilder_config import FBConfig
from .fbloader import FBLoader
from ..utils.images import remove_bpy_image_by_name
from ..utils.coords import update_head_mesh_non_neutral
from ..utils.attrs import get_obj_collection, safe_delete_collection
from ..facebuilder.utils.exif_reader import (update_exif_sizes_message,
                                             copy_exif_parameters_from_camera_to_head)
from .utils.manipulate import check_settings, push_head_in_undo_history
from ..utils.manipulate import center_viewports_on_object
from ..utils.materials import (bake_tex,
                               show_texture_in_mat,
                               assign_material_to_object,
                               toggle_mode,
                               switch_to_mode,
                               remove_mat_by_name,
                               find_bpy_image_by_name)
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
from .facebuilder_acts import (remove_pins_act,
                               rotate_head_act,
                               reset_expression_act,
                               center_geo_act)
from .prechecks import common_fb_checks
from .integration import FB_OT_ExportToCC


_log = KTLogger(__name__)


class ButtonOperator:
    bl_options = {'REGISTER', 'UNDO'}

    def draw(self, context):
        pass


class ActiveButtonOperator(ButtonOperator):
    active_button: BoolProperty(default=True)


class FB_OT_SelectHead(ButtonOperator, Operator):
    bl_idname = FBConfig.fb_select_head_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    headnum: IntProperty(default=0)

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        check_status = common_fb_checks(object_mode=True,
                                        is_calculating=True,
                                        fix_facebuilders=True,
                                        head_only=True,
                                        headnum=self.headnum)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        settings = fb_settings()
        head = settings.get_head(self.headnum)
        center_viewports_on_object(head.headobj)
        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


# Duplicate FB_OT_SelectHead operator but with different tooltip
class FB_OT_SelectCurrentHead(ButtonOperator, Operator):
    bl_idname = FBConfig.fb_select_current_head_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    headnum: IntProperty(default=0)

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        check_status = common_fb_checks(object_mode=True,
                                        is_calculating=True,
                                        fix_facebuilders=True,
                                        head_only=True,
                                        headnum=self.headnum)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        settings = fb_settings()
        head = settings.get_head(self.headnum)
        center_viewports_on_object(head.headobj)
        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FB_OT_DeleteHead(ButtonOperator, Operator):
    bl_idname = FBConfig.fb_delete_head_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    headnum: IntProperty(default=0)

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        check_status = common_fb_checks(object_mode=True,
                                        pinmode_out=True,
                                        is_calculating=True,
                                        fix_facebuilders=True,
                                        head_only=True,
                                        headnum=self.headnum)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        settings = fb_settings()
        head = settings.get_head(self.headnum)

        for c in head.cameras:
            try:
                bpy_remove_object(c.camobj)
            except Exception:
                pass

        try:
            col = get_obj_collection(head.headobj)
            bpy_remove_object(head.headobj)
            safe_delete_collection(col)
        except Exception:
            pass
        settings.heads.remove(self.headnum)
        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FB_OT_SelectCamera(ButtonOperator, Operator):
    bl_idname = FBConfig.fb_select_camera_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    headnum: IntProperty(default=0)
    camnum: IntProperty(default=0)

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        check_status = common_fb_checks(object_mode=True,
                                        is_calculating=True,
                                        fix_facebuilders=True,
                                        head_and_camera=True,
                                        headnum=self.headnum,
                                        camnum=self.camnum)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        settings = fb_settings()
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
                msg = f'{str(err)}'
                self.report({'ERROR'}, msg)
                _log.error(f'{type(err)}\n{msg}')

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FB_OT_CenterGeo(ButtonOperator, Operator):
    bl_idname = FBConfig.fb_center_geo_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    headnum: IntProperty(default=0)
    camnum: IntProperty(default=0)

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        check_status = common_fb_checks(object_mode=True,
                                        pinmode=True,
                                        is_calculating=True,
                                        reload_facebuilder=True,
                                        head_and_camera=True,
                                        headnum=self.headnum,
                                        camnum=self.camnum)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        act_status = center_geo_act(self.headnum, self.camnum, update=True)
        if not act_status.success:
            msg = act_status.error_message
            self.report({'ERROR'}, msg)
            _log.error(f'{msg}')
            return {'CANCELLED'}

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FB_OT_Unmorph(ButtonOperator, Operator):
    bl_idname = FBConfig.fb_unmorph_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    headnum: IntProperty(default=0)
    camnum: IntProperty(default=0)

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        check_status = common_fb_checks(object_mode=True,
                                        pinmode=True,
                                        is_calculating=True,
                                        reload_facebuilder=True,
                                        head_and_camera=True,
                                        headnum=self.headnum,
                                        camnum=self.camnum)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        settings = fb_settings()
        headnum = self.headnum
        camnum = self.camnum
        head = settings.get_head(headnum)

        fb = FBLoader.get_builder()
        fb.unmorph()

        for i, camera in enumerate(head.cameras):
            fb.remove_pins(camera.get_keyframe())
            camera.pins_count = 0

        update_head_mesh_non_neutral(fb, head)
        FBLoader.save_fb_serial_and_image_pathes(headnum)

        if settings.pinmode:
            FBLoader.load_pins_into_viewport(headnum, camnum)
            FBLoader.update_fb_viewport_shaders(area=context.area,
                                                headnum=headnum, camnum=camnum,
                                                wireframe=True,
                                                pins_and_residuals=True)

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FB_OT_RemovePins(ButtonOperator, Operator):
    bl_idname = FBConfig.fb_remove_pins_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    headnum: IntProperty(default=0)
    camnum: IntProperty(default=0)

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        check_status = common_fb_checks(object_mode=True,
                                        pinmode=True,
                                        is_calculating=True,
                                        reload_facebuilder=True,
                                        head_and_camera=True,
                                        headnum=self.headnum,
                                        camnum=self.camnum)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        act_status = remove_pins_act(self.headnum, self.camnum, update=True)
        if not act_status.success:
            msg = act_status.error_message
            self.report({'ERROR'}, msg)
            _log.error(f'{msg}')
            return {'CANCELLED'}

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FB_OT_WireframeColor(ButtonOperator, Operator):
    bl_idname = FBConfig.fb_wireframe_color_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    action: StringProperty(name="Action Name")

    def execute(self, context):
        def _setup_colors_from_scheme(name):
            settings = fb_settings()
            settings.wireframe_color = Config.fb_color_schemes[name][0]
            settings.wireframe_special_color = Config.fb_color_schemes[name][1]

        _log.green(f'{self.__class__.__name__} execute')
        check_status = common_fb_checks(is_calculating=True)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

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

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FB_OT_FilterCameras(ButtonOperator, Operator):
    bl_idname = FBConfig.fb_filter_cameras_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    action: StringProperty(name='Action Name')
    headnum: IntProperty(default=0)

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute action={self.action}')
        check_status = common_fb_checks(is_calculating=True,
                                        head_only=True,
                                        headnum=self.headnum)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        settings = fb_settings()
        if self.action == 'select_all_cameras':
            for c in settings.get_head(self.headnum).cameras:
                c.use_in_tex_baking = True

        elif self.action == 'deselect_all_cameras':
            for c in settings.get_head(self.headnum).cameras:
                c.use_in_tex_baking = False

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FB_OT_DeleteCamera(ButtonOperator, Operator):
    bl_idname = FBConfig.fb_delete_camera_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    headnum: IntProperty(default=0)
    camnum: IntProperty(default=0)

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        check_status = common_fb_checks(object_mode=True,
                                        is_calculating=True,
                                        fix_facebuilders=True,
                                        reload_facebuilder=True,
                                        head_and_camera=True,
                                        headnum=self.headnum,
                                        camnum=self.camnum)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        settings = fb_settings()
        headnum = self.headnum
        camnum = self.camnum

        head = settings.get_head(headnum)
        camera = head.get_camera(camnum)
        kid = camera.get_keyframe()
        if head.get_expression_view_keyframe() == kid:
            head.set_neutral_expression_view()

        fb = FBLoader.get_builder()
        fb.remove_keyframe(kid)

        camera.delete_cam_image()
        camera.delete_camobj()
        head.cameras.remove(camnum)

        FBLoader.save_fb_serial_and_image_pathes(headnum)

        if settings.current_camnum > camnum:
            settings.current_camnum -= 1
        elif settings.current_camnum == camnum:
            settings.current_camnum = -1
            settings.reset_pinmode_id()

        _log.output(f'CAMERA H:{headnum} C:{camnum} REMOVED')
        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FB_OT_ProperViewMenuExec(ButtonOperator, Operator):
    bl_idname = FBConfig.fb_proper_view_menu_exec_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    headnum: IntProperty(default=0)
    camnum: IntProperty(default=0)

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        check_status = common_fb_checks(is_calculating=True,
                                        fix_facebuilders=True,
                                        head_and_camera=True,
                                        headnum=self.headnum,
                                        camnum=self.camnum)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        settings = fb_settings()
        settings.tmp_headnum = self.headnum
        settings.tmp_camnum = self.camnum
        bpy_call_menu('INVOKE_DEFAULT',
                      name=FBConfig.fb_proper_view_menu_idname)
        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FB_OT_AddonSetupDefaults(Operator):
    bl_idname = FBConfig.fb_addon_setup_defaults_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER'}

    def draw(self, context):
        pass

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        show_user_preferences(facebuilder=True, geotracker=False)
        show_tool_preferences(facebuilder=True, geotracker=False)
        bpy_show_addon_preferences()
        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FB_OT_BakeTexture(ButtonOperator, Operator):
    bl_idname = FBConfig.fb_bake_tex_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    headnum: IntProperty(default=0)

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        check_status = common_fb_checks(object_mode=True,
                                        is_calculating=True,
                                        fix_facebuilders=True,
                                        reload_facebuilder=True,
                                        head_only=True,
                                        headnum=self.headnum)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        settings = fb_settings()
        head = settings.get_head(self.headnum)
        bake_status = bake_tex(self.headnum, head.preview_texture_name())

        if not bake_status.success:
            _log.error('Texture has not been baked')
            self.report({'ERROR'}, bake_status.error_message)
            return {'CANCELLED'}

        if settings.tex_auto_preview:
            mat = show_texture_in_mat(head.preview_texture_name(),
                                      head.preview_material_name())
            assign_material_to_object(head.headobj, mat)
            toggle_mode(('MATERIAL',))

            if settings.pinmode:
                settings.force_out_pinmode = True
                if head.should_use_emotions():
                    bpy_view_camera()

        self.report({'INFO'}, 'Texture has been created')
        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FB_OT_DeleteTexture(ButtonOperator, Operator):
    bl_idname = FBConfig.fb_delete_texture_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    headnum: IntProperty(default=0)

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        check_status = common_fb_checks(is_calculating=True,
                                        fix_facebuilders=True,
                                        reload_facebuilder=True,
                                        head_only=True,
                                        headnum=self.headnum)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        settings = fb_settings()
        head = settings.get_head(self.headnum)
        remove_bpy_image_by_name(head.preview_texture_name())
        remove_mat_by_name(head.preview_material_name())
        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FB_OT_RotateImageCW(ButtonOperator, Operator):
    bl_idname = FBConfig.fb_rotate_image_cw_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    headnum: IntProperty(default=0)
    camnum: IntProperty(default=0)

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        check_status = common_fb_checks(object_mode=True,
                                        is_calculating=True,
                                        fix_facebuilders=True,
                                        reload_facebuilder=True,
                                        head_and_camera=True,
                                        headnum=self.headnum,
                                        camnum=self.camnum)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        settings = fb_settings()
        camera = settings.get_camera(self.headnum, self.camnum)
        camera.rotate_background_image(1)
        camera.update_scene_frame_size()
        camera.update_background_image_scale()
        FBLoader.save_fb_serial_and_image_pathes(self.headnum)
        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FB_OT_RotateImageCCW(ButtonOperator, Operator):
    bl_idname = FBConfig.fb_rotate_image_ccw_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    headnum: IntProperty(default=0)
    camnum: IntProperty(default=0)

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        check_status = common_fb_checks(object_mode=True,
                                        is_calculating=True,
                                        fix_facebuilders=True,
                                        reload_facebuilder=True,
                                        head_and_camera=True,
                                        headnum=self.headnum,
                                        camnum=self.camnum)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        settings = fb_settings()
        camera = settings.get_camera(self.headnum, self.camnum)
        camera.rotate_background_image(-1)
        camera.update_scene_frame_size()
        camera.update_background_image_scale()
        FBLoader.save_fb_serial_and_image_pathes(self.headnum)
        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FB_OT_ResetImageRotation(ButtonOperator, Operator):
    bl_idname = FBConfig.fb_reset_image_rotation_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    headnum: IntProperty(default=0)
    camnum: IntProperty(default=0)

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        check_status = common_fb_checks(object_mode=True,
                                        is_calculating=True,
                                        fix_facebuilders=True,
                                        reload_facebuilder=True,
                                        head_and_camera=True,
                                        headnum=self.headnum,
                                        camnum=self.camnum)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        settings = fb_settings()
        camera = settings.get_camera(self.headnum, self.camnum)
        camera.reset_background_image_rotation()
        camera.update_scene_frame_size()
        camera.update_background_image_scale()
        FBLoader.save_fb_serial_and_image_pathes(self.headnum)
        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FB_OT_ResetExpression(ButtonOperator, Operator):
    bl_idname = FBConfig.fb_reset_expression_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    headnum: IntProperty(default=0)
    camnum: IntProperty(default=0)

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        check_status = common_fb_checks(object_mode=True,
                                        is_calculating=True,
                                        fix_facebuilders=True,
                                        reload_facebuilder=True,
                                        head_and_camera=True,
                                        headnum=self.headnum,
                                        camnum=self.camnum)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        act_status = reset_expression_act(self.headnum, self.camnum,
                                          update=True)
        if not act_status.success:
            msg = act_status.error_message
            self.report({'ERROR'}, msg)
            _log.error(f'{msg}')
            return {'CANCELLED'}

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FB_OT_ShowTexture(ButtonOperator, Operator):
    bl_idname = FBConfig.fb_show_tex_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        check_status = common_fb_checks(object_mode=True,
                                        is_calculating=True,
                                        fix_facebuilders=True,
                                        reload_facebuilder=True,
                                        head_only=True)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        settings = fb_settings()
        head = settings.get_head(settings.current_headnum)

        tex = find_bpy_image_by_name(head.preview_texture_name())
        if tex is None:
            return {'CANCELLED'}

        if settings.pinmode:
            FBLoader.out_pinmode(settings.current_headnum)
            exit_area_localview(context.area)

        mat = show_texture_in_mat(head.preview_texture_name(),
                                  head.preview_material_name())
        assign_material_to_object(head.headobj, mat)
        switch_to_mode('MATERIAL')

        _log.output('SWITCH TO MATERIAL MODE WITH TEXTURE')
        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FB_OT_ShowSolid(ButtonOperator, Operator):
    bl_idname = FBConfig.fb_show_solid_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        check_status = common_fb_checks(object_mode=True,
                                        is_calculating=True,
                                        fix_facebuilders=True,
                                        reload_facebuilder=True,
                                        head_only=True)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        settings = fb_settings()
        if settings.pinmode:
            FBLoader.out_pinmode(settings.current_headnum)
            exit_area_localview(context.area)
        switch_to_mode('SOLID')
        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FB_OT_ExitPinmode(ButtonOperator, Operator):
    bl_idname = FBConfig.fb_exit_pinmode_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        check_status = common_fb_checks(is_calculating=True,
                                        fix_facebuilders=True)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        settings = fb_settings()
        if settings.pinmode:
            settings.force_out_pinmode = True

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FB_OT_CreateBlendshapes(ButtonOperator, Operator):
    bl_idname = FBConfig.fb_create_blendshapes_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        check_status = common_fb_checks(object_mode=True,
                                        is_calculating=True)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}
        return create_blendshapes(self)


class FB_OT_DeleteBlendshapes(ActiveButtonOperator, Operator):
    bl_idname = FBConfig.fb_delete_blendshapes_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        check_status = common_fb_checks(object_mode=True,
                                        is_calculating=True)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        if not self.active_button:
            return {'CANCELLED'}
        return delete_blendshapes(self)


class FB_OT_LoadAnimationFromCSV(ButtonOperator, Operator):
    bl_idname = FBConfig.fb_load_animation_from_csv_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        check_status = common_fb_checks(object_mode=True,
                                        is_calculating=True)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}
        return load_animation_from_csv(self)


class FB_OT_CreateExampleAnimation(ActiveButtonOperator, Operator):
    bl_idname = FBConfig.fb_create_example_animation_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        check_status = common_fb_checks(object_mode=True,
                                        is_calculating=True)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        if not self.active_button:
            return {'CANCELLED'}
        return create_example_animation(self)


class FB_OT_ResetBlendshapeValues(ButtonOperator, Operator):
    bl_idname = FBConfig.fb_reset_blendshape_values_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        check_status = common_fb_checks(object_mode=True,
                                        is_calculating=True)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}
        return reset_blendshape_values(self)


class FB_OT_ClearAnimation(ActiveButtonOperator, Operator):
    bl_idname = FBConfig.fb_clear_animation_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        check_status = common_fb_checks(object_mode=True,
                                        is_calculating=True)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        if not self.active_button:
            return {'CANCELLED'}
        return clear_animation(self)


class FB_OT_ExportHeadToFBX(ButtonOperator, Operator):
    bl_idname = FBConfig.fb_export_head_to_fbx_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        check_status = common_fb_checks(object_mode=True,
                                        is_calculating=True)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        settings = fb_settings()
        if settings.pinmode:
            FBLoader.out_pinmode(settings.current_headnum)
            exit_area_localview(context.area)

        return export_head_to_fbx(self)


class FB_OT_UpdateBlendshapes(ButtonOperator, Operator):
    bl_idname = FBConfig.fb_update_blendshapes_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        check_status = common_fb_checks(object_mode=True,
                                        is_calculating=True)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}
        return update_blendshapes(self)


class FB_OT_UnhideHead(ButtonOperator, Operator):
    bl_idname = FBConfig.fb_unhide_head_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        check_status = common_fb_checks(object_mode=True,
                                        is_calculating=True)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}
        return unhide_head(self, context)


class FB_OT_ReconstructHead(ButtonOperator, Operator):
    bl_idname = FBConfig.fb_reconstruct_head_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        check_status = common_fb_checks(object_mode=True,
                                        is_calculating=True)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}
        return reconstruct_by_mesh()


class FB_OT_DefaultPinSettings(ButtonOperator, Operator):
    bl_idname = FBConfig.fb_default_pin_settings_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        settings = fb_settings()
        prefs = settings.preferences()
        settings.pin_size = prefs.pin_size
        settings.pin_sensitivity = prefs.pin_sensitivity
        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FB_OT_DefaultWireframeSettings(ButtonOperator, Operator):
    bl_idname = FBConfig.fb_default_wireframe_settings_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        settings = fb_settings()
        prefs = settings.preferences()
        settings.wireframe_color = prefs.fb_wireframe_color
        settings.wireframe_special_color = prefs.fb_wireframe_special_color
        settings.wireframe_midline_color = prefs.fb_wireframe_midline_color
        settings.wireframe_opacity = prefs.fb_wireframe_opacity
        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FB_OT_SelectCurrentCamera(ButtonOperator, Operator):
    bl_idname = FBConfig.fb_select_current_camera_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        check_status = common_fb_checks(object_mode=True,
                                        is_calculating=True)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        op = get_operator(FBConfig.fb_exit_pinmode_idname)
        op('EXEC_DEFAULT')
        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FB_OT_ResetToneGain(ButtonOperator, Operator):
    bl_idname = FBConfig.fb_reset_tone_exposure_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        check_status = common_fb_checks(is_calculating=True,
                                        head_and_camera=True)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        settings = fb_settings()
        cam = settings.get_camera(settings.current_headnum,
                                  settings.current_camnum)
        if not cam:
            return {'CANCELLED'}

        cam.tone_exposure = Config.default_tone_exposure
        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FB_OT_ResetToneGamma(ButtonOperator, Operator):
    bl_idname = FBConfig.fb_reset_tone_gamma_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        check_status = common_fb_checks(is_calculating=True,
                                        head_and_camera=True)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        settings = fb_settings()
        cam = settings.get_camera(settings.current_headnum,
                                  settings.current_camnum)
        if not cam:
            return {'CANCELLED'}

        cam.tone_gamma = Config.default_tone_gamma
        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FB_OT_ResetToneMapping(ButtonOperator, Operator):
    bl_idname = FBConfig.fb_reset_tone_mapping_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        check_status = common_fb_checks(is_calculating=True,
                                        head_and_camera=True)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        settings = fb_settings()
        cam = settings.get_camera(settings.current_headnum,
                                  settings.current_camnum)
        if not cam:
            return {'CANCELLED'}

        cam.tone_exposure = Config.default_tone_exposure
        cam.tone_gamma = Config.default_tone_gamma
        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FB_OT_RotateHeadForward(ButtonOperator, Operator):
    bl_idname = FBConfig.fb_rotate_head_forward_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        check_status = common_fb_checks(object_mode=True,
                                        is_calculating=True,
                                        reload_facebuilder=True,
                                        head_and_camera=True)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        settings = fb_settings()
        act_status = rotate_head_act(settings.current_headnum,
                                     settings.current_camnum, -45.0)
        if not act_status.success:
            msg = act_status.error_message
            self.report({'ERROR'}, msg)
            _log.error(f'{msg}')
            return {'CANCELLED'}

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FB_OT_RotateHeadBackward(ButtonOperator, Operator):
    bl_idname = FBConfig.fb_rotate_head_backward_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        check_status = common_fb_checks(object_mode=True,
                                        is_calculating=True,
                                        reload_facebuilder=True,
                                        head_and_camera=True)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        settings = fb_settings()
        act_status = rotate_head_act(settings.current_headnum,
                                     settings.current_camnum, 45.0)
        if not act_status.success:
            msg = act_status.error_message
            self.report({'ERROR'}, msg)
            _log.error(f'{msg}')
            return {'CANCELLED'}

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FB_OT_ResetView(ButtonOperator, Operator):
    bl_idname = FBConfig.fb_reset_view_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        check_status = common_fb_checks(object_mode=True,
                                        pinmode=True,
                                        is_calculating=True,
                                        reload_facebuilder=True,
                                        head_and_camera=True)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        settings = fb_settings()
        headnum = settings.current_headnum
        camnum = settings.current_camnum

        act_status = reset_expression_act(headnum, camnum, update=False)
        if not act_status.success:
            msg = act_status.error_message
            self.report({'ERROR'}, msg)
            _log.error(f'{msg}')
            return {'CANCELLED'}

        act_status = center_geo_act(headnum, camnum, update=False)
        if not act_status.success:
            msg = act_status.error_message
            self.report({'ERROR'}, msg)
            _log.error(f'{msg}')
            return {'CANCELLED'}

        act_status = remove_pins_act(headnum, camnum, update=True)
        if not act_status.success:
            msg = act_status.error_message
            self.report({'ERROR'}, msg)
            _log.error(f'{msg}')
            return {'CANCELLED'}

        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FB_OT_MoveWrapper(ButtonOperator, Operator):
    bl_idname = 'keentools_fb.move_wrapper'
    bl_label = 'move wrapper'
    bl_description = 'KeenTools move wrapper operator'

    use_cursor_init: BoolProperty(name='Use Mouse Position', default=True)

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute '
                   f'use_cursor_init={self.use_cursor_init}')
        settings = fb_settings()
        if not settings:
            return {'CANCELLED'}

        op = get_operator('view3d.move')
        return op('EXEC_DEFAULT', use_cursor_init=self.use_cursor_init)

    def invoke(self, context, event):
        _log.green(f'{self.__class__.__name__} invoke '
                   f'use_cursor_init={self.use_cursor_init}')
        settings = fb_settings()
        if not settings:
            return {'CANCELLED'}

        work_area = FBLoader.get_work_area()
        if work_area != context.area:
            return {'PASS_THROUGH'}

        op = get_operator('view3d.move')
        return op('INVOKE_DEFAULT', use_cursor_init=self.use_cursor_init)


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
                       FB_OT_ExportToCC,  # Integration
                       FB_OT_UpdateBlendshapes,
                       FB_OT_UnhideHead,
                       FB_OT_ReconstructHead,
                       FB_OT_DefaultPinSettings,
                       FB_OT_DefaultWireframeSettings,
                       FB_OT_ResetToneGain,
                       FB_OT_ResetToneGamma,
                       FB_OT_ResetToneMapping,
                       FB_OT_RotateHeadForward,
                       FB_OT_RotateHeadBackward,
                       FB_OT_ResetView,
                       FB_OT_MoveWrapper)
