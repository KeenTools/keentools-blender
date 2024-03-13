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

from bpy.props import IntProperty, BoolProperty
from bpy.types import Operator

from ...utils.kt_logging import KTLogger
from ...addon_config import Config, fb_settings, get_operator
from ...facebuilder_config import FBConfig
from ..callbacks import mesh_update_accepted, mesh_update_canceled
from ..ui_strings import buttons, warnings
from ..prechecks import common_fb_checks


_log = KTLogger(__name__)


class FB_OT_BlendshapesWarning(Operator):
    bl_idname = FBConfig.fb_blendshapes_warning_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'INTERNAL'}

    headnum: IntProperty(default=0)
    accept: BoolProperty(name='Proceed with topology change '
                              'and recreate blendshapes',
                         default=False)
    content_red = []
    content_white = []

    def output_text(self, layout, content, red=False):
        for txt in content:
            row = layout.row()
            row.alert = red
            row.label(text=txt)

    def draw(self, context):
        layout = self.layout.column()

        col = layout.column()
        col.scale_y = Config.text_scale_y

        self.output_text(col, self.content_red, red=True)
        self.output_text(col, self.content_white, red=False)

        layout.prop(self, 'accept')

    def execute(self, context):
        if (self.accept):
            mesh_update_accepted(self.headnum)
        else:
            mesh_update_canceled(self.headnum)
        return {'FINISHED'}

    def cancel(self, context):
        mesh_update_canceled(self.headnum)

    def invoke(self, context, event):
        self.content_red = warnings[FBConfig.fb_blendshapes_warning_idname].content_red
        self.content_white = warnings[FBConfig.fb_blendshapes_warning_idname].content_white
        return context.window_manager.invoke_props_dialog(self, width=400)


class FB_OT_NoBlendshapesUntilExpressionWarning(Operator):
    bl_idname = FBConfig.fb_noblenshapes_until_expression_warning_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'INTERNAL'}

    headnum: IntProperty(default=0)
    accept: BoolProperty(name='Set neutral expression', default=False)
    content_red = []

    def output_text(self, layout, content, red=False):
        for txt in content:
            row = layout.row()
            row.alert = red
            row.label(text=txt)

    def draw(self, context):
        layout = self.layout.column()
        col = layout.column()
        col.scale_y = Config.text_scale_y
        self.output_text(col, self.content_red, red=True)
        layout.prop(self, 'accept')

    def execute(self, context):
        if (self.accept):
            settings = fb_settings()
            head = settings.get_head(self.headnum)
            if head is None:
                return {'CANCELLED'}

            head.set_neutral_expression_view()
            op = get_operator(FBConfig.fb_create_blendshapes_idname)
            op('EXEC_DEFAULT')

        return {'FINISHED'}

    def cancel(self, context):
        pass

    def invoke(self, context, event):
        self.content_red = warnings[FBConfig.fb_noblenshapes_until_expression_warning_idname].content_red

        return context.window_manager.invoke_props_dialog(self, width=400)


def _tex_file_filter_buttons(layout, headnum):
    row = layout.row(align=True)
    row.alignment = 'LEFT'
    op = row.operator(FBConfig.fb_filter_cameras_idname, text='Select All')
    op.action = 'select_all_cameras'
    op.headnum = headnum

    op = row.operator(FBConfig.fb_filter_cameras_idname, text='Clear All')
    op.action = 'deselect_all_cameras'
    op.headnum = headnum


def _tex_selector(layout, headnum):
    settings = fb_settings()
    head = settings.get_head(headnum)
    if not head:
        return

    if not head.has_cameras():
        layout.label(text='You need at least one image to create texture.',
                     icon='ERROR')
        return

    layout.label(text='Source images:')

    checked_views = False
    for camera in head.cameras:
        row = layout.row()
        if not camera.has_pins():
            continue

        row.prop(camera, 'use_in_tex_baking', text='')
        if camera.use_in_tex_baking:
            checked_views = True

        image_icon = 'PINNED' if camera.has_pins() else 'FILE_IMAGE'
        if camera.cam_image:
            row.label(text=camera.get_image_name(), icon=image_icon)
        else:
            row.label(text='-- empty --', icon='LIBRARY_DATA_BROKEN')

    if not checked_views:
        col = layout.column()
        col.scale_y = Config.text_scale_y
        col.alert = True
        col.label(text='You need to select at least one image')
        col.label(text='to create texture.')


def _texture_bake_options(layout):
    settings = fb_settings()
    col = layout.column(align=True)
    row = col.row()
    row.label(text='Size in pixels:')
    btn = row.column(align=True)
    btn.active = False
    btn.operator(FBConfig.fb_reset_texture_resolution_idname,
                 text='', icon='LOOP_BACK', emboss=False, depress=False)

    col.separator(factor=0.4)
    row = col.row(align=True)
    row.prop(settings, 'tex_width', text='W')
    row.prop(settings, 'tex_height', text='H')

    col = layout.column(align=True)
    row = col.row()
    row.label(text='Advanced')
    btn = row.column(align=True)
    btn.active = False
    btn.operator(FBConfig.fb_reset_advanced_settings_idname,
                 text='', icon='LOOP_BACK', emboss=False, depress=False)

    col.separator(factor=0.4)
    col.prop(settings, 'tex_face_angles_affection')
    col.prop(settings, 'tex_uv_expand_percents')
    col.separator(factor=0.8)
    col.prop(settings, 'tex_equalize_brightness')
    col.prop(settings, 'tex_equalize_colour')
    col.prop(settings, 'tex_fill_gaps')

    layout.prop(settings, 'tex_auto_preview')


class FB_OT_TextureBakeOptions(Operator):
    bl_idname = FBConfig.fb_texture_bake_options_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'INTERNAL'}

    headnum: IntProperty(default=0)

    def draw(self, context):
        layout = self.layout
        row = layout.split(factor=0.5)
        col = row.column()
        _tex_selector(col, self.headnum)
        col = row.column()
        _texture_bake_options(col)

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        return {'FINISHED'}

    def cancel(self, context):
        _log.green(f'{self.__class__.__name__} cancel')

    def invoke(self, context, event):
        _log.green(f'{self.__class__.__name__} invoke')
        check_status = common_fb_checks(is_calculating=True)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}
        return context.window_manager.invoke_props_dialog(self, width=600)


class FB_OT_ResetTextureResolution(Operator):
    bl_idname = FBConfig.fb_reset_texture_resolution_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        check_status = common_fb_checks(is_calculating=True)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        settings = fb_settings()
        settings.tex_width = Config.default_tex_width
        settings.tex_height = Config.default_tex_height
        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class FB_OT_ResetTextureSettings(Operator):
    bl_idname = FBConfig.fb_reset_advanced_settings_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        check_status = common_fb_checks(is_calculating=True)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        settings = fb_settings()
        settings.tex_face_angles_affection = Config.default_tex_face_angles_affection
        settings.tex_uv_expand_percents = Config.default_tex_uv_expand_percents
        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


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


class FB_OT_ImageInfo(Operator):
    bl_idname = FBConfig.fb_image_info_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'INTERNAL'}

    def draw(self, context):
        layout = self.layout
        settings = fb_settings()
        head = settings.get_head(settings.current_headnum)
        if not head:
            return
        camera = head.get_camera(settings.current_camnum)
        if camera is None:
            return
        col = layout.column()
        col.label(text='Image properties based on EXIF data:')
        col.label(text=f'{camera.get_image_name()}')
        _draw_exif(layout, head)

    def cancel(self, context):
        _log.green(f'{self.__class__.__name__} cancel')

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        return {'FINISHED'}

    def invoke(self, context, event):
        _log.green(f'{self.__class__.__name__} invoke')
        check_status = common_fb_checks(is_calculating=True,
                                        fix_facebuilders=True,
                                        head_and_camera=True)
        if not check_status.success:
            self.report({'ERROR'}, check_status.error_message)
            return {'CANCELLED'}

        return context.window_manager.invoke_popup(self, width=400)


CLASSES_TO_REGISTER = (FB_OT_BlendshapesWarning,
                       FB_OT_NoBlendshapesUntilExpressionWarning,
                       FB_OT_TextureBakeOptions,
                       FB_OT_ResetTextureResolution,
                       FB_OT_ResetTextureSettings,
                       FB_OT_ImageInfo)
