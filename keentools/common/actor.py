# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2022-2024 KeenTools

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

from typing import Any, Optional, Set
from copy import deepcopy

from bpy.types import Operator
from bpy.props import StringProperty, IntProperty

from ..utils.kt_logging import KTLogger
from ..addon_config import Config, fb_settings, ft_settings, get_operator
from ..facebuilder_config import FBConfig
from ..utils.localview import exit_area_localview
from ..common.loader import CommonLoader
from ..utils.bpy_common import bpy_current_frame, bpy_new_image, bpy_view_camera
from ..utils.viewport_state import force_show_ui_overlays


_log = KTLogger(__name__)


class KT_OT_Actor(Operator):
    bl_idname = Config.kt_actor_idname
    bl_label = 'Experimental Operator'
    bl_description = 'Experimental Operator description'
    bl_options = {'REGISTER', 'INTERNAL'}

    action: StringProperty(name='Action string', default='none')
    num: IntProperty(name='Numeric parameter', default=0)

    def draw(self, context):
        pass

    def execute(self, context):
        _log.output('ACTION call: {}'.format(self.action))

        if self.action == 'none':
            return {'CANCELLED'}

        elif self.action == 'ft_create_new_head':
            settings = ft_settings()
            geotracker = settings.get_current_geotracker_item()
            if not geotracker:
                return {'CANCELLED'}

            op = get_operator(FBConfig.fb_add_head_operator_idname)
            op('EXEC_DEFAULT')

            settings_fb = fb_settings()
            headnum = settings_fb.get_last_headnum()
            head = settings_fb.get_head(headnum)
            geotracker.geomobj = head.headobj
            head.use_emotions = True

            vp = CommonLoader.text_viewport()
            default_txt = deepcopy(vp.texter().get_default_text())
            default_txt[0]['text'] = 'Choose frame on timeline then press Take snapshot button'
            default_txt[0]['color'] = (1., 0., 1., 0.85)
            vp.message_to_screen(default_txt)

            op = get_operator('keentools_ft.choose_frame_mode')
            op('INVOKE_DEFAULT')
            CommonLoader.set_ft_head_mode('CHOOSE_FRAME')

        elif self.action == 'ft_take_snapshot_mode':
            vp = CommonLoader.text_viewport()
            default_txt = deepcopy(vp.texter().get_default_text())
            default_txt[0]['text'] = 'Choose frame on timeline then press Take snapshot button'
            default_txt[0]['color'] = (1., 0., 1., 0.85)
            vp.message_to_screen(default_txt)

            op = get_operator('keentools_ft.choose_frame_mode')
            op('INVOKE_DEFAULT')
            CommonLoader.set_ft_head_mode('CHOOSE_FRAME')

        elif self.action == 'ft_take_snapshot':
            settings = ft_settings()
            geotracker = settings.get_current_geotracker_item()
            if not geotracker:
                return {'CANCELLED'}

            frame = bpy_current_frame()

            movie_clip = geotracker.movie_clip
            if not movie_clip:
                self.report({'INFO'}, 'No movie clip')
                return {'CANCELLED'}

            name = movie_clip.name
            w, h = movie_clip.size[:]
            img = bpy_new_image(name, width=w, height=h, alpha=True,
                                float_buffer=False)
            img.use_view_as_render = True

            if movie_clip.source == 'MOVIE':
                img.source = 'MOVIE'
            else:
                img.source = 'SEQUENCE' if movie_clip.frame_duration > 1 else 'FILE'

            img.filepath = movie_clip.filepath

            settings_fb = fb_settings()
            loader_fb = settings_fb.loader()
            headnum = settings_fb.head_by_obj(geotracker.geomobj)
            if headnum < 0:
                _log.error('No FaceBuilder object found')
                return {'CANCELLED'}

            loader_fb.add_new_camera(headnum, img, frame)
            loader_fb.save_fb_serial_str(headnum)

            settings_fb.current_camnum = settings_fb.get_last_camnum(headnum)

            op = get_operator(Config.kt_actor_idname)
            op('EXEC_DEFAULT', action='ft_edit_head')

        elif self.action == 'ft_cancel_create_head':
            area = context.area
            exit_area_localview(area)
            force_show_ui_overlays(area)
            CommonLoader.set_ft_head_mode('NONE')

        elif self.action == 'ft_cancel_take_snapshot':
            settings = ft_settings()
            geotracker = settings.get_current_geotracker_item()
            if not geotracker:
                return {'CANCELLED'}

            area = context.area
            exit_area_localview(area)
            force_show_ui_overlays(area)

            area = CommonLoader.text_viewport().get_work_area()
            CommonLoader.text_viewport().stop_viewport()
            CommonLoader.set_ft_head_mode('NONE')
            if area:
                area.tag_redraw()

        elif self.action == 'ft_edit_head':
            settings = ft_settings()
            geotracker = settings.get_current_geotracker_item()
            if not geotracker or not geotracker.geomobj:
                return {'CANCELLED'}

            settings_fb = fb_settings()
            headnum = settings_fb.head_by_obj(geotracker.geomobj)
            if headnum < 0:
                _log.error('No FaceBuilder object found')
                return {'CANCELLED'}

            head = settings_fb.get_head(headnum)

            if len(head.cameras) == 0:
                _log.error('No Cameras found')
                op = get_operator(Config.kt_actor_idname)
                op('EXEC_DEFAULT', action='ft_take_snapshot_mode')
                return {'CANCELLED'}

            if headnum == settings_fb.current_headnum:
                camnum = settings_fb.current_camnum
            else:
                camnum = 0

            if camnum < 0 or camnum >= len(head.cameras):
                camnum = 0

            camera = head.get_camera(camnum)

            op = get_operator(FBConfig.fb_select_camera_idname)
            op('EXEC_DEFAULT', headnum=headnum, camnum=camnum,
               detect_face=not camera.has_pins())

            CommonLoader.set_ft_head_mode('EDIT_HEAD')

        self.report({'INFO'}, self.action)
        return {'FINISHED'}
