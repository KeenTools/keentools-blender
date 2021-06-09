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
from threading import Lock

import bpy

from ..config import get_main_settings, Config
from ..blender_independent_packages.pykeentools_loader import (
    module as pkt_module, is_installed as pkt_is_installed)
from ..blender_independent_packages.pykeentools_loader.install import (
    updates_downloaded,
    download_addon_zip_async, download_core_zip_async,
    remove_addon_zip, remove_core_zip,
    install_downloaded_addon, install_downloaded_core)

from ..utils.html import parse_html, skip_new_lines_and_spaces, render_main


def mock_response():
    response = lambda: None
    response.description_url = 'https://keentools.io/downloads'
    response.download_url = 'https://keentools.io/downloads'
    response.message = "<h3>What's New in KeenTools 2021.2.1</h3>\n" \
                       "<ul>\n  " \
                       "<li>fixed performance issues in Nuke 12;</li>\n  " \
                       "<li>pintooling performance improvements;</li>\n  " \
                       "<li>fixed large frame numbers bug;</li>\n  " \
                       "<li>fixed invisible model in macOS Catalina;</li>\n " \
                       "<li>minor fixes and improvements</li>\n" \
                       "</ul>\n<br />\n"
    response.plugin_name = 'FaceBuilder'
    response.version = pkt_module().Version(2021, 2, 1)
    return response


def _version_to_tuple(version):
    if type(version).__name__ == 'str':
        if version == "":
            return tuple([0, 0, 0])
        l = version.split('.')
        return tuple(map(int, l))
    if type(version).__name__ == 'Version':
        return tuple([version.major, version.minor, version.patch])
    return version


def _downloaded_version():
    settings = get_main_settings()
    return settings.preferences().downloaded_version


def _latest_skip_version():
    settings = get_main_settings()
    return settings.preferences().latest_skip_version


class FBUpdater:
    _response = None
    # _response = mock_response()  # Mock for testing (1/3)
    _parsed_response_content = None

    @classmethod
    def is_active(cls):
        return cls.has_response() and \
               _version_to_tuple(_downloaded_version()) < _version_to_tuple(cls.version())

    @classmethod
    def has_response(cls):
        return cls.get_response() is not None

    @classmethod
    def has_response_message(cls):
        return cls._parsed_response_content is not None

    @classmethod
    def set_response(cls, val):
        response = cls.get_response()
        cls._response = val

    @classmethod
    def get_response(cls):
        if cls._response is None:
            cls._response = mock_response()  # Mock for testing (2/3)
        return cls._response

    @classmethod
    def get_parsed(cls):
        return cls._parsed_response_content

    @classmethod
    def set_parsed(cls, val):
        cls._parsed_response_content = val

    @classmethod
    def clear_message(cls):
        cls.set_response(None)
        cls.set_parsed(None)

    @classmethod
    def render_message(cls, layout):
        parsed = cls.get_parsed()
        if parsed is not None:
            render_main(layout, parsed)

    @classmethod
    def get_update_checker(cls):
        pykeentools = pkt_module()
        platform = 'Blender'
        ver = pykeentools.Version(*bpy.app.version)
        uc = pykeentools.UpdatesChecker.instance(platform, ver)
        return uc

    @classmethod
    def version(cls):
        return cls.get_response().version

    @classmethod
    def init_updater(cls):
        if cls.has_response_message() or not pkt_is_installed():
            return

        uc = cls.get_update_checker()
        res = uc.check_for_updates('FaceBuilder')
        res = cls.get_response()  # Mock for testing (3/3)
        if res is not None:
            cls.set_response(res)
            parsed = parse_html(skip_new_lines_and_spaces(res.message))
            cls.set_parsed(parsed)


class DownloadedPartsExecutor:
    _state_mutex = Lock()

    @classmethod
    def get_downloaded_parts_count(cls):
        cls._state_mutex.acquire()
        try:
            settings = get_main_settings()
            return settings.preferences().downloaded_parts
        finally:
            cls._state_mutex.release()

    @classmethod
    def inc_downloaded_parts_count(cls):
        cls._state_mutex.acquire()
        try:
            settings = get_main_settings()
            settings.preferences().downloaded_parts += 1
        finally:
            cls._state_mutex.release()

    @classmethod
    def nullify_downloaded_parts_count(cls):
        cls._state_mutex.acquire()
        try:
            settings = get_main_settings()
            settings.preferences().downloaded_parts = 0
        finally:
            cls._state_mutex.release()


class FB_OT_DownloadTheUpdate(bpy.types.Operator):
    bl_idname = Config.fb_download_the_update_idname
    bl_label = 'Download the update'
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = 'Download the latest version of addon and core'

    def execute(self, context):
        settings = get_main_settings()
        settings.preferences().downloaded_version = str(FBUpdater.version())
        DownloadedPartsExecutor.nullify_downloaded_parts_count()
        download_core_zip_async(final_callback=DownloadedPartsExecutor.inc_downloaded_parts_count)
        download_addon_zip_async(final_callback=DownloadedPartsExecutor.inc_downloaded_parts_count)
        return {'FINISHED'}


class FB_OT_RemindLater(bpy.types.Operator):
    bl_idname = Config.fb_remind_later_idname
    bl_label = 'Remind later'
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = 'Remind about this update tomorrow'

    def execute(self, context):
        logger = logging.getLogger(__name__)
        logger.debug('REMIND LATER')

        uc = FBUpdater.get_update_checker()
        res = FBUpdater.get_response()
        uc.pause_update(res.plugin_name, res.version)
        FBUpdater.clear_message()
        return {'FINISHED'}


class FB_OT_SkipVersion(bpy.types.Operator):
    bl_idname = Config.fb_skip_version_idname
    bl_label = 'Skip this version'
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = 'Skip this version'

    def execute(self, context):
        logger = logging.getLogger(__name__)
        logger.debug('SKIP THIS VERSION')

        uc = FBUpdater.get_update_checker()
        res = FBUpdater.get_response()
        uc.skip_update(res.plugin_name, res.version)
        FBUpdater.clear_message()
        return {'FINISHED'}


class FBDownloadNotification:
    @classmethod
    def is_active(cls):
        return _version_to_tuple(_downloaded_version()) > _version_to_tuple(Config.addon_version) and \
               _version_to_tuple(_downloaded_version()) != _version_to_tuple(_latest_skip_version()) and \
               DownloadedPartsExecutor.get_downloaded_parts_count() < 2

    @classmethod
    def render_message(cls, layout):
        if cls.is_active():
            _message_text = 'Updates are downloading. ' \
                            'We will let you know when they are ready for installation.'
            render_main(layout, parse_html(_message_text))


_MIN_TIME_BETWEEN_REMINDERS = 86400  # 24 hours in seconds


class FBInstallationReminder:
    _last_reminder_time = None

    @classmethod
    def is_active(cls):
        import time
        return _version_to_tuple(_downloaded_version()) > _version_to_tuple(Config.addon_version) and \
               _version_to_tuple(_downloaded_version()) != _version_to_tuple(_latest_skip_version()) and \
               DownloadedPartsExecutor.get_downloaded_parts_count() == 2 and \
               (cls._last_reminder_time is None or
                time.time() - cls._last_reminder_time > _MIN_TIME_BETWEEN_REMINDERS)

    @classmethod
    def render_message(cls, layout):
        if cls.is_active():
            _message_text = 'The update {} is ready to be installed. ' \
                            'Blender will be relaunched after installing the update automatically. ' \
                            'Please save your project before continuing. Proceed?'.\
                format(_downloaded_version())
            render_main(layout, parse_html(_message_text))

    @classmethod
    def remind_later(cls):
        import time
        cls._last_reminder_time = time.time()


def _start_new_blender(cmd_line):
    import platform
    import os
    import subprocess
    install_downloaded_addon(True)
    install_downloaded_core(True)
    if platform.system() == 'Linux':
        new_ref = os.fork()
        if new_ref == 0:
            subprocess.call([cmd_line])
    else:
        subprocess.call([cmd_line])


_START_NEW_BLENDER_REGISTER = False


class FB_OT_InstallUpdates(bpy.types.Operator):
    bl_idname = Config.fb_install_updates_idname
    bl_label = 'The blender will restart, save your changes before'
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = 'Install updates and restart blender'

    def execute(self, context):
        global _START_NEW_BLENDER_REGISTER
        if _START_NEW_BLENDER_REGISTER is False:
            _START_NEW_BLENDER_REGISTER = True
            if updates_downloaded():
                import sys
                import atexit
                atexit.register(_start_new_blender, sys.argv[0])
                bpy.ops.wm.quit_blender('INVOKE_DEFAULT')
        return {'FINISHED'}


class FB_OT_RemindInstallLater(bpy.types.Operator):
    bl_idname = Config.fb_remind_install_later_idname
    bl_label = 'Remind install tommorow'
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = 'Remind install tommorow'

    def execute(self, context):
        global _START_NEW_BLENDER_REGISTER
        if _START_NEW_BLENDER_REGISTER is True:
            import atexit
            atexit.unregister(_start_new_blender)
            _START_NEW_BLENDER_REGISTER = False
        FBInstallationReminder.remind_later()
        return {'FINISHED'}


class FB_OT_SkipInstallation(bpy.types.Operator):
    bl_idname = Config.fb_skip_installation_idname
    bl_label = 'Skip installation'
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = 'Skip installation'

    def execute(self, context):
        global _START_NEW_BLENDER_REGISTER
        if _START_NEW_BLENDER_REGISTER is True:
            import atexit
            atexit.unregister(_start_new_blender)
            _START_NEW_BLENDER_REGISTER = False
        settings = get_main_settings()
        settings.preferences().latest_skip_version = settings.preferences().downloaded_version
        remove_addon_zip()
        remove_core_zip()
        DownloadedPartsExecutor.nullify_downloaded_parts_count()
        return {'FINISHED'}
