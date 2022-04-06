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
from collections import namedtuple
from enum import IntEnum
from datetime import datetime
from typing import Tuple

import bpy

from ..config import get_operator, get_main_settings, Config, ErrorType
from ..blender_independent_packages.pykeentools_loader import (
    module as pkt_module, is_installed as pkt_is_installed,
    updates_downloaded, download_core_zip_async, download_addon_zip_async,
    install_downloaded_zips)

from ..utils.html import parse_html, skip_new_lines_and_spaces, render_main
from ..utils.other import force_ui_redraw

from ..preferences.progress import FBUpdateProgressTimer


def _mock_response(ver: Tuple):
    response = lambda: None
    response.description_url = 'https://keentools.io/downloads'
    response.download_url = 'https://keentools.io/downloads'
    response.message = "<h3>What's New in KeenTools {}</h3>\n" \
                       "<ul>\n  " \
                       "<li>fixed performance issues in Nuke 12;</li>\n  " \
                       "<li>pintooling performance improvements;</li>\n  " \
                       "<li>fixed large frame numbers bug;</li>\n  " \
                       "<li>fixed invisible model in macOS Catalina;</li>\n " \
                       "<li>minor fixes and improvements</li>\n" \
                       "</ul>\n<br />\n".format('.'.join([str(x) for x in ver]))
    response.plugin_name = 'FaceBuilder'
    try:
        response.version = pkt_module().Version(*ver)
    except Exception:
        response.version = None
    return response


def _version_to_tuple(version):
    if version is None:
        return tuple([0, 0, 0])
    if type(version).__name__ == 'str':
        if version == "":
            return tuple([0, 0, 0])
        return tuple(map(int, version.split('.')))
    if type(version).__name__ == 'Version':
        return tuple([version.major, version.minor, version.patch])
    assert False


def _downloaded_version():
    settings = get_main_settings()
    return settings.preferences().downloaded_version


def _latest_installation_skip_version():
    settings = get_main_settings()
    return settings.preferences().latest_installation_skip_version


_PREFERENCES_DATETIME_FORMAT = '%d/%m/%y %H:%M:%S'


def _operator_available_time(previous_show_datetime_str):
    if previous_show_datetime_str == '':
        return True
    previous_show_time = datetime.strptime(previous_show_datetime_str, _PREFERENCES_DATETIME_FORMAT)
    return (datetime.now() - previous_show_time).total_seconds() // 3600 >= 24


def render_active_message(layout):
    settings = get_main_settings()
    updater_state = settings.preferences().updater_state
    limit = 64
    layout.scale_y = Config.text_scale_y
    if updater_state == UpdateState.UPDATES_AVAILABLE:
        FBUpdater.render_message(layout, limit=limit)
    elif updater_state == UpdateState.DOWNLOADING:
        FBDownloadNotification.render_message(layout)
    elif updater_state == UpdateState.DOWNLOADING_PROBLEM:
        FBDownloadingProblem.render_message(layout, limit=limit)
    elif updater_state == UpdateState.INSTALL:
        FBInstallationReminder.render_message(layout, limit=limit)


def preferences_current_active_updater_operators_info():
    settings = get_main_settings()
    updater_state = settings.preferences().updater_state
    OperatorInfo = namedtuple('OperatorInfo', 'idname, text, icon')
    if updater_state == UpdateState.UPDATES_AVAILABLE:
        return [OperatorInfo(Config.fb_download_the_update_idname, 'Download the update', 'IMPORT')]
    if updater_state == UpdateState.DOWNLOADING_PROBLEM:
        return [OperatorInfo(Config.fb_retry_download_the_update_idname, 'Try again', 'FILE_REFRESH'),
                OperatorInfo(Config.fb_come_back_to_update_idname, 'Cancel', 'PANEL_CLOSE')]
    elif updater_state == UpdateState.INSTALL:
        return [OperatorInfo(Config.fb_install_updates_idname, 'Install and restart', 'FILE_REFRESH')]
    else:
        return None


class UpdateState(IntEnum):
    INITIAL = 1
    UPDATES_AVAILABLE = 2
    DOWNLOADING = 3
    DOWNLOADING_PROBLEM = 4
    INSTALL = 5


class CurrentStateExecutor:
    _panel_updater_state = UpdateState.INITIAL
    _mutable = True

    @classmethod
    def make_immutable(cls):
        cls._mutable = False


    @classmethod
    def set_current_panel_updater_state(cls, state, set_preferences_updater_state=True):
        if cls._mutable:
            cls._panel_updater_state = state
            force_ui_redraw('VIEW_3D')
            if set_preferences_updater_state:
                settings = get_main_settings()
                settings.preferences().updater_state = state
                force_ui_redraw('PREFERENCES')

    @classmethod
    def compute_current_panel_updater_state(cls):
        downloaded_version = _version_to_tuple(_downloaded_version())
        if cls._panel_updater_state == UpdateState.INITIAL:
            if FBUpdater.is_available():
                cls.set_current_panel_updater_state(UpdateState.UPDATES_AVAILABLE)
            elif downloaded_version > _version_to_tuple(Config.addon_version) and \
                    downloaded_version != _version_to_tuple(_latest_installation_skip_version()) and \
                    updates_downloaded() and FBInstallationReminder.is_available():
                cls.set_current_panel_updater_state(UpdateState.INSTALL)
        elif cls._panel_updater_state == UpdateState.INSTALL:
            if FBUpdater.is_available():
                cls.set_current_panel_updater_state(UpdateState.UPDATES_AVAILABLE)
        return cls._panel_updater_state


class FBUpdater:
    _response = None
    _parsed_response_content = None

    @classmethod
    def is_available(cls):
        settings = get_main_settings()
        previous_show_time_str = settings.preferences().latest_show_datetime_update_reminder
        latest_skip_version = settings.preferences().latest_update_skip_version
        return _operator_available_time(previous_show_time_str) and cls.has_response() and \
               _version_to_tuple(Config.addon_version) < _version_to_tuple(cls.version()) and \
               _version_to_tuple(_downloaded_version()) < _version_to_tuple(cls.version()) and \
               _version_to_tuple(latest_skip_version) != _version_to_tuple(cls.version())

    @classmethod
    def is_active(cls):
        return CurrentStateExecutor.compute_current_panel_updater_state() == UpdateState.UPDATES_AVAILABLE

    @classmethod
    def has_response(cls):
        return cls.get_response() is not None

    @classmethod
    def has_response_message(cls):
        return cls._parsed_response_content is not None

    @classmethod
    def set_response(cls, val):
        cls._response = val

    @classmethod
    def get_response(cls):
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
    def render_message(cls, layout, limit=32):
        parsed = cls.get_parsed()
        if parsed is not None:
            render_main(layout, parsed, limit)

    @classmethod
    def get_update_checker(cls):
        pykeentools = pkt_module()
        platform = 'Blender'
        ver = pykeentools.Version(*bpy.app.version)
        uc = pykeentools.UpdatesChecker.instance(platform, ver)
        return uc

    @classmethod
    def remind_later(cls):
        settings = get_main_settings()
        settings.preferences().latest_show_datetime_update_reminder = \
            datetime.now().strftime(_PREFERENCES_DATETIME_FORMAT)

    @classmethod
    def version(cls):
        return cls.get_response().version

    @classmethod
    def init_updater(cls):
        if cls.has_response_message() or not pkt_is_installed():
            return

        uc = cls.get_update_checker()
        res = uc.check_for_updates('FaceBuilder')
        if Config.mock_update_for_testing_flag and cls.get_response() is None:
            res = _mock_response(ver=Config.mock_update_version)
        if res is not None:
            cls.set_response(res)
            parsed = parse_html(skip_new_lines_and_spaces(res.message))
            cls.set_parsed(parsed)


def _set_installing():
    settings = get_main_settings()
    settings.preferences().downloaded_version = str(FBUpdater.version())
    CurrentStateExecutor.set_current_panel_updater_state(UpdateState.INSTALL)
    FBDownloadNotification.init_progress(None)
    FBUpdateProgressTimer.stop()


class Progress:
    def __init__(self, interval=(0.0, 1.0), parent=None):
        self._interval = interval
        self._parent = parent
        self._progress = interval[0]
        self._state_mutex = Lock()

    def create_subprogress(self, interval):
        return Progress(interval, self)

    def progress_callback(self, progress):
        self._state_mutex.acquire()

        try:
            next_progress = self._interval[0] + (self._interval[1] - self._interval[0]) * progress
            self._progress = next_progress
            if self._parent is not None:
                self._parent.progress_callback(next_progress)
        finally:
            self._state_mutex.release()

    def get_current_progress(self):
        self._state_mutex.acquire()
        try:
            return self._progress
        finally:
            self._state_mutex.release()


def _download_update():
    common_progress = Progress()

    core_download_progress = common_progress.create_subprogress((0.0, 0.98))
    addon_download_progress = common_progress.create_subprogress((0.98, 1.0))

    _TIMEOUT = 10

    def core_download_callback():
        download_addon_zip_async(timeout=_TIMEOUT,
                                 final_callback=_set_installing,
                                 progress_callback=addon_download_progress.progress_callback,
                                 error_callback=on_downloading_problem)

    download_core_zip_async(timeout=_TIMEOUT,
                            final_callback=core_download_callback,
                            progress_callback=core_download_progress.progress_callback,
                            error_callback=on_downloading_problem)

    return common_progress


class FB_OT_DownloadTheUpdate(bpy.types.Operator):
    bl_idname = Config.fb_download_the_update_idname
    bl_label = 'Download the update'
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = 'Download and install the latest version of FaceBuilder'

    def execute(self, context):
        CurrentStateExecutor.set_current_panel_updater_state(UpdateState.DOWNLOADING)
        FBUpdateProgressTimer.start(redraw_view3d=True)
        FBDownloadNotification.init_progress(_download_update())
        return {'FINISHED'}


class FB_OT_RemindLater(bpy.types.Operator):
    bl_idname = Config.fb_remind_later_idname
    bl_label = 'Remind later'
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = 'Remind about this update tomorrow'

    def execute(self, context):
        CurrentStateExecutor.set_current_panel_updater_state(UpdateState.INITIAL,
                                                             set_preferences_updater_state=False)
        logger = logging.getLogger(__name__)
        logger.debug('REMIND LATER')
        FBUpdater.remind_later()
        return {'FINISHED'}


class FB_OT_SkipVersion(bpy.types.Operator):
    bl_idname = Config.fb_skip_version_idname
    bl_label = 'Skip this version'
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = 'Skip this version'

    def execute(self, context):
        CurrentStateExecutor.set_current_panel_updater_state(UpdateState.INITIAL,
                                                             set_preferences_updater_state=False)
        logger = logging.getLogger(__name__)
        logger.debug('SKIP THIS VERSION')
        settings = get_main_settings()
        settings.preferences().latest_update_skip_version = str(FBUpdater.version())
        return {'FINISHED'}


def on_downloading_problem(error):
    CurrentStateExecutor.set_current_panel_updater_state(UpdateState.DOWNLOADING_PROBLEM)
    FBDownloadNotification.init_progress(None)
    FBUpdateProgressTimer.stop()


class FBDownloadNotification:
    _download_update_progress = None

    @classmethod
    def init_progress(cls, progress):
        cls._download_update_progress = progress

    @classmethod
    def get_current_progress(cls):
        return cls._download_update_progress.get_current_progress()

    @classmethod
    def is_active(cls):
        return CurrentStateExecutor.compute_current_panel_updater_state() == UpdateState.DOWNLOADING

    @classmethod
    def render_message(cls, layout):
        if cls.is_active():
            col = layout.column()
            col.label(text="Downloading the update: {:.0f}%".format(100 * FBDownloadNotification.get_current_progress()))


class FBDownloadingProblem:
    @classmethod
    def is_active(cls):
        return CurrentStateExecutor.compute_current_panel_updater_state() == UpdateState.DOWNLOADING_PROBLEM

    @classmethod
    def render_message(cls, layout, limit=32):
        if cls.is_active():
            layout.alert = True
            _message_text = 'Sorry, an unexpected network error happened. Please check your network connection.'
            render_main(layout, parse_html(_message_text), limit)


class FB_OT_RetryDownloadUpdate(bpy.types.Operator):
    bl_idname = Config.fb_retry_download_the_update_idname
    bl_label = 'Retry download'
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = 'Try downloading again'

    def execute(self, context):
        CurrentStateExecutor.set_current_panel_updater_state(UpdateState.DOWNLOADING)
        FBUpdateProgressTimer.start(redraw_view3d=True)
        FBDownloadNotification.init_progress(_download_update())
        return {'FINISHED'}


class FB_OT_ComeBackToUpdate(bpy.types.Operator):
    bl_idname = Config.fb_come_back_to_update_idname
    bl_label = 'Cancel'
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = 'Cancel updating'

    def execute(self, context):
        _clear_updater_info()
        CurrentStateExecutor.set_current_panel_updater_state(UpdateState.INITIAL)
        return {'FINISHED'}


class FBInstallationReminder:

    @classmethod
    def is_active(cls):
        return CurrentStateExecutor.compute_current_panel_updater_state() == UpdateState.INSTALL

    @classmethod
    def is_available(cls):
        settings = get_main_settings()
        previous_show_time_str = settings.preferences().latest_show_datetime_installation_reminder
        return _operator_available_time(previous_show_time_str)

    @classmethod
    def render_message(cls, layout, limit=32):
        _message_text = 'The new version of FaceBuilder is ready to be installed. ' \
                        'Blender will be relaunched automatically. ' \
                        'Please save your project before proceeding.'
        render_main(layout, parse_html(_message_text), limit)

    @classmethod
    def remind_later(cls):
        settings = get_main_settings()
        settings.preferences().latest_show_datetime_installation_reminder = \
            datetime.now().strftime(_PREFERENCES_DATETIME_FORMAT)


def _start_new_blender(cmd_line):
    import platform
    import os
    import subprocess
    install_downloaded_zips(True)
    if platform.system() == 'Linux':
        new_ref = os.fork()
        if new_ref == 0:
            subprocess.call([cmd_line])
    else:
        subprocess.call([cmd_line])


def _clear_updater_info():
    from ..preferences import reset_updater_preferences_to_default
    reset_updater_preferences_to_default()


class FB_OT_InstallUpdates(bpy.types.Operator):
    bl_idname = Config.fb_install_updates_idname
    bl_label = ''
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = 'Press to install the update and relaunch Blender'

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.scale_y = Config.text_scale_y

        content = ['The project has some unsaved changes. '
                   'Please save the project and then try installing the update again.',
                   'Please note that selecting something in the scene is considered a change in Blender.',
                   ' ']
        for t in content:
            col.label(text=t)

        settings = get_main_settings()
        col = layout.column()
        col.prop(settings, 'not_save_changes')

    def execute(self, context):
        settings = get_main_settings()
        if not bpy.data.is_dirty or settings.not_save_changes:
            _clear_updater_info()
            if not updates_downloaded():
                warn = get_operator(Config.fb_warning_idname)
                warn('INVOKE_DEFAULT', msg=ErrorType.DownloadingProblem)
                _clear_updater_info()
                CurrentStateExecutor.compute_current_panel_updater_state()
                return {'CANCELLED'}
            CurrentStateExecutor.make_immutable()
            import sys
            import atexit
            atexit.register(_start_new_blender, sys.argv[0])
            bpy.ops.wm.quit_blender()
        return {'FINISHED'}

    def invoke(self, context, event):
        if bpy.data.is_dirty:
            return context.window_manager.invoke_props_dialog(self, width=550)
        return self.execute(context)


class FB_OT_RemindInstallLater(bpy.types.Operator):
    bl_idname = Config.fb_remind_install_later_idname
    bl_label = 'Remind install tommorow'
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = 'Remind install tommorow'

    def execute(self, context):
        CurrentStateExecutor.set_current_panel_updater_state(UpdateState.INITIAL,
                                                             set_preferences_updater_state=False)
        FBInstallationReminder.remind_later()
        return {'FINISHED'}


class FB_OT_SkipInstallation(bpy.types.Operator):
    bl_idname = Config.fb_skip_installation_idname
    bl_label = 'Skip installation'
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = 'Skip installation'

    def execute(self, context):
        CurrentStateExecutor.set_current_panel_updater_state(UpdateState.INITIAL,
                                                             set_preferences_updater_state=False)
        settings = get_main_settings()
        settings.preferences().latest_installation_skip_version = settings.preferences().downloaded_version
        return {'FINISHED'}
