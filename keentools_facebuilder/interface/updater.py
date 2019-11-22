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

from ..config import Config
from keentools_facebuilder.blender_independent_packages import \
    pykeentools_loader as pkt
from ..utils.html import parse_html, skip_new_lines_and_spaces, render_main


def get_update_checker():
    import pykeentools
    platform = 'Blender'
    ver = pykeentools.Version(*bpy.app.version)
    uc = pykeentools.UpdatesChecker.instance(platform, ver)
    return uc


def init_updater():
    if FBUpdater.get_state() or not pkt.is_installed():
        return

    uc = get_update_checker()
    res = uc.check_for_updates('FaceBuilder')  # production
    res = FBUpdater.get_response()  # Mock data
    if res is not None:
        FBUpdater.set_response(res)
        FBUpdater.set_state(True)


class FBUpdater:
    _state = False  # updater read status
    _response = None
    _parsed = None
    _show = True  # for force hiding after skip or remind later

    @classmethod
    def set_state(cls, val):
        cls._state = val

    @classmethod
    def get_state(cls):
        return cls._state

    @classmethod
    def set_response(cls, val):
        cls._response = val

    @classmethod
    def get_response(cls):
        return cls._response  # production code, comment it for mocking

        # Mock code
        if cls._response is not None:
            return cls._response

        # Mock object
        response = lambda: None
        response.description_url = 'https://keentools.io/downloads'
        response.download_url = 'https://keentools.io/downloads'
        response.message = "<h3>What's New in KeenTools 1.5.6</h3>\n" \
            "<ul>\n  " \
            "<li>fixed performance issues in Nuke 12;</li>\n  " \
            "<li>pintooling performance improvements;</li>\n  " \
            "<li>fixed large frame numbers bug;</li>\n  " \
            "<li>fixed invisible model in macOS Catalina;</li>\n  " \
            "<li>minor fixes and improvements</li>\n" \
            "</ul>\n<br />\n"
        response.plugin_name = 'FaceBuilder'
        response.version = pkt.module().Version(1, 5, 6)
        return response

    @classmethod
    def get_parsed(cls):
        return cls._parsed

    @classmethod
    def set_parsed(cls, val):
        cls._parsed = val

    @classmethod
    def get_show(cls):
        return cls._show

    @classmethod
    def set_show(cls, val):
        cls._show = val

    @classmethod
    def visible(cls):
        return cls.get_state() and cls.get_show()

    @classmethod
    def render_message(cls, layout):
        parsed = cls.get_parsed()
        if parsed is None:
            res = cls.get_response()
            parsed = parse_html(skip_new_lines_and_spaces(res.message))
            cls.set_parsed(parsed)
        render_main(layout, parsed)


class FB_OT_RemindLater(bpy.types.Operator):
    bl_idname = Config.fb_remind_later_idname
    bl_label = 'Remind later'
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = 'Remind about this update tomorrow'

    def execute(self, context):
        uc = get_update_checker()
        res = FBUpdater.get_response()
        uc.pause_update(res.plugin_name, res.version)
        FBUpdater.set_show(False)
        return {'FINISHED'}


class FB_OT_SkipVersion(bpy.types.Operator):
    bl_idname = Config.fb_skip_version_idname
    bl_label = 'Skip this version'
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = 'Skip this version'

    def execute(self, context):
        uc = get_update_checker()
        res = FBUpdater.get_response()
        uc.skip_update(res.plugin_name, res.version)
        FBUpdater.set_show(False)
        return {'FINISHED'}
