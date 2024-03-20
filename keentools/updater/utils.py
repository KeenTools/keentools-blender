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

from threading import Lock
from collections import namedtuple
from enum import IntEnum
from datetime import datetime
from typing import Tuple, List, Optional, Any, Dict

import bpy
from bpy.types import Operator
from bpy.props import BoolProperty

from ..utils.kt_logging import KTLogger
from ..addon_config import Config, get_operator, get_addon_preferences, ErrorType
from ..blender_independent_packages.pykeentools_loader import (
    module as pkt_module, is_installed as pkt_is_installed,
    updates_downloaded, download_core_zip_async, download_addon_zip_async,
    install_downloaded_zips)
from ..utils.html import parse_html, skip_new_lines_and_spaces, render_main
from ..utils.ui_redraw import force_ui_redraw
from ..preferences.progress import KTUpdateProgressTimer
from ..ui_strings import buttons


_log = KTLogger(__name__)


def _mock_response(*, product: str='FaceBuilder', ver: Tuple) -> Any:
    response = lambda: None
    response.description_url = 'https://keentools.io/downloads'
    response.download_url = 'https://keentools.io/downloads'
    response.message = "<h3>What's New in KeenTools {} {}</h3>\n" \
                       "<ul>\n  " \
                       "<li>fixed performance issues in Nuke 12;</li>\n  " \
                       "<li>pintooling performance improvements;</li>\n  " \
                       "<li>fixed large frame numbers bug;</li>\n  " \
                       "<li>fixed invisible model in macOS Catalina;</li>\n " \
                       "<li>minor fixes and improvements</li>\n" \
                       "</ul>\n<br />\n".format(product,
                                                '.'.join([str(x) for x in ver]))
    response.plugin_name = 'FaceBuilder'
    try:
        response.version = pkt_module().Version(*ver)
    except Exception:
        response.version = None
    return response


def _version_to_tuple(version: Optional[Any]) -> Tuple:
    if version is None:
        return tuple([0, 0, 0])
    if type(version).__name__ == 'str':
        if version == "":
            return tuple([0, 0, 0])
        return tuple(map(int, version.split('.')))
    if type(version).__name__ == 'Version':
        return tuple([version.major, version.minor, version.patch])
    assert False


def _downloaded_version() -> str:
    prefs = get_addon_preferences()
    if not prefs:
        return ''
    return prefs.downloaded_version


def _latest_installation_skip_version() -> str:
    prefs = get_addon_preferences()
    if not prefs:
        return ''
    return prefs.latest_installation_skip_version


_PREFERENCES_DATETIME_FORMAT: str = '%d/%m/%y %H:%M:%S'


def _operator_available_time(previous_show_datetime_str: str) -> bool:
    if previous_show_datetime_str == '':
        return True
    previous_show_time = datetime.strptime(previous_show_datetime_str, _PREFERENCES_DATETIME_FORMAT)
    return (datetime.now() - previous_show_time).total_seconds() // 3600 >= 24


def render_active_message(limit: int=64) -> List[str]:
    prefs = get_addon_preferences()
    if not prefs:
        return []
    updater_state = prefs.updater_state

    if updater_state == UpdateState.UPDATES_AVAILABLE:
        return KTUpdater.render_message(product=None, limit=limit)
    elif updater_state == UpdateState.DOWNLOADING:
        return KTDownloadNotification.render_message()
    elif updater_state == UpdateState.DOWNLOADING_PROBLEM:
        return KTDownloadingProblem.render_message(limit=limit)
    elif updater_state == UpdateState.INSTALL:
        return KTInstallationReminder.render_message(limit=limit)
    return []


def preferences_current_active_updater_operators_info() -> Optional[List]:
    prefs = get_addon_preferences()
    if not prefs:
        return None
    updater_state = prefs.updater_state
    OperatorInfo = namedtuple('OperatorInfo', 'idname, text, icon')
    if updater_state == UpdateState.UPDATES_AVAILABLE:
        return [OperatorInfo(Config.kt_download_the_update_idname, 'Download the update', 'IMPORT')]
    if updater_state == UpdateState.DOWNLOADING_PROBLEM:
        return [OperatorInfo(Config.kt_retry_download_the_update_idname, 'Try again', 'FILE_REFRESH'),
                OperatorInfo(Config.kt_come_back_to_update_idname, 'Cancel', 'PANEL_CLOSE')]
    elif updater_state == UpdateState.INSTALL:
        return [OperatorInfo(Config.kt_install_updates_idname, 'Install and restart', 'FILE_REFRESH')]
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
    def set_current_panel_updater_state(cls, state: UpdateState,
            set_preferences_updater_state: bool=True) -> None:
        if cls._mutable:
            cls._panel_updater_state = state
            force_ui_redraw('VIEW_3D')
            if set_preferences_updater_state:
                prefs = get_addon_preferences()
                if not prefs:
                    return
                prefs.updater_state = state
                force_ui_redraw('PREFERENCES')

    @classmethod
    def compute_current_panel_updater_state(cls) -> UpdateState:
        downloaded_version = _version_to_tuple(_downloaded_version())
        if cls._panel_updater_state == UpdateState.INITIAL:
            if KTUpdater.is_available():
                cls.set_current_panel_updater_state(UpdateState.UPDATES_AVAILABLE)
            elif downloaded_version > _version_to_tuple(Config.addon_version) and \
                    downloaded_version != _version_to_tuple(_latest_installation_skip_version()) and \
                    updates_downloaded() and KTInstallationReminder.is_available():
                cls.set_current_panel_updater_state(UpdateState.INSTALL)
        elif cls._panel_updater_state == UpdateState.INSTALL:
            if KTUpdater.is_available():
                cls.set_current_panel_updater_state(UpdateState.UPDATES_AVAILABLE)
        return cls._panel_updater_state


class KTUpdater:
    _response: Dict = {'FaceBuilder': None, 'GeoTracker': None,
                       'FaceTracker': None, 'KeenTools': None}
    _parsed_response_content: Dict = {'FaceBuilder': None, 'GeoTracker': None,
                                      'FaceTracker': None, 'KeenTools': None}
    _max_log_counter: int = 25
    _log_counter: Dict = {'FaceBuilder': _max_log_counter,
                          'GeoTracker': _max_log_counter,
                          'FaceTracker': _max_log_counter,
                          'KeenTools': _max_log_counter}

    @classmethod
    def is_available(cls) -> bool:
        prefs = get_addon_preferences()
        if not prefs:
            return False
        if not _operator_available_time(prefs.latest_show_datetime_update_reminder) or not cls.has_response():
            return False
        ver_tuple = _version_to_tuple(cls.version())
        return _version_to_tuple(Config.addon_version) < ver_tuple and \
               _version_to_tuple(_downloaded_version()) < ver_tuple and \
               _version_to_tuple(prefs.latest_update_skip_version) != ver_tuple

    @classmethod
    def is_active(cls) -> bool:
        return CurrentStateExecutor.compute_current_panel_updater_state() == UpdateState.UPDATES_AVAILABLE

    @classmethod
    def has_response(cls) -> bool:
        return any([cls._response[key] is not None for key in cls._response])

    @classmethod
    def product_is_checked(cls, product: str) -> bool:
        return cls._parsed_response_content[product] is not None

    @classmethod
    def has_response_message(cls, product: str) -> bool:
        return cls._parsed_response_content[product] is not None

    @classmethod
    def set_response(cls, product: str, val: Optional[Any]) -> None:
        _log.green(f'set_response:\n{product}\n{val}')
        cls._response[product] = val
        _log.yellow(f'response:\n{cls._response}')

    @classmethod
    def get_response(cls, *, product: Optional[str]=None) -> Optional[Any]:
        if product is not None:
            return cls._response[product]
        for key in cls._response:
            response = cls._response[key]
            if response is not None:
                return response
        return None

    @classmethod
    def get_parsed(cls, *, product: Optional[str]=None) -> Optional[Any]:
        if product is not None:
            return cls._parsed_response_content[product]
        for key in cls._parsed_response_content:
            parsed = cls._parsed_response_content[key]
            if parsed is not None:
                return parsed
        return None

    @classmethod
    def set_parsed(cls, product: str, val: Optional[Any]) -> None:
        _log.green(f'set_parsed:\n{product}\n{val}')
        cls._parsed_response_content[product] = val

    @classmethod
    def render_message(cls, *, product: Optional[str]=None, limit: int=32) -> List[str]:
        parsed = cls.get_parsed(product=product)
        if parsed is not None:
            return render_main(parsed, limit)
        return []

    @classmethod
    def get_update_checker(cls) -> Any:
        pykeentools = pkt_module()
        platform = 'Blender'
        ver = pykeentools.Version(*bpy.app.version)
        uc = pykeentools.UpdatesChecker.instance(platform, ver)
        return uc

    @classmethod
    def remind_later(cls) -> None:
        prefs = get_addon_preferences()
        if not prefs:
            return
        prefs.latest_show_datetime_update_reminder = \
            datetime.now().strftime(_PREFERENCES_DATETIME_FORMAT)

    @classmethod
    def version(cls) -> Any:
        response = cls.get_response(product=None)
        if response is not None:
            return response.version
        return ''

    @classmethod
    def call_updater(cls, product: str) -> None:
        if product not in cls._log_counter.keys():
            _log.error(f'call_updater: {product}')
            return
        cls._log_counter[product] += 1
        if cls._log_counter[product] >= cls._max_log_counter:
            cls._log_counter[product] = 0
            _log.cyan(f'call_updater [{product}] x{cls._max_log_counter}')

        if cls.has_response_message(product) or not pkt_is_installed():
            return
        uc = cls.get_update_checker()
        res = uc.check_for_updates(product)
        if Config.mock_update_for_testing_flag and not cls.product_is_checked(product):
            if Config.mock_product is None or Config.mock_product == product:
                res = _mock_response(product=product,
                                     ver=Config.mock_update_version)
        if res is not None:
            cls.set_response(product, res)
            parsed = parse_html(skip_new_lines_and_spaces(res.message))
            cls.set_parsed(product, parsed)


def _set_installing() -> None:
    prefs = get_addon_preferences()
    if not prefs:
        return
    prefs.downloaded_version = str(KTUpdater.version())
    CurrentStateExecutor.set_current_panel_updater_state(UpdateState.INSTALL)
    KTDownloadNotification.init_progress(None)
    KTUpdateProgressTimer.stop()


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


class KT_OT_DownloadTheUpdate(Operator):
    bl_idname = Config.kt_download_the_update_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        CurrentStateExecutor.set_current_panel_updater_state(UpdateState.DOWNLOADING)
        KTUpdateProgressTimer.start(redraw_view3d=True)
        KTDownloadNotification.init_progress(_download_update())
        return {'FINISHED'}


class KT_OT_RemindLater(Operator):
    bl_idname = Config.kt_remind_later_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        CurrentStateExecutor.set_current_panel_updater_state(UpdateState.INITIAL,
                                                             set_preferences_updater_state=False)
        _log.output('REMIND LATER')
        KTUpdater.remind_later()
        return {'FINISHED'}


class KT_OT_SkipVersion(Operator):
    bl_idname = Config.kt_skip_version_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        CurrentStateExecutor.set_current_panel_updater_state(UpdateState.INITIAL,
                                                             set_preferences_updater_state=False)
        _log.output('SKIP THIS VERSION')
        prefs = get_addon_preferences()
        if not prefs:
            return {'CANCELLED'}
        prefs.latest_update_skip_version = str(KTUpdater.version())
        return {'FINISHED'}


def on_downloading_problem(error):
    CurrentStateExecutor.set_current_panel_updater_state(UpdateState.DOWNLOADING_PROBLEM)
    KTDownloadNotification.init_progress(None)
    KTUpdateProgressTimer.stop()


class KTDownloadNotification:
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
    def render_message(cls) -> List[str]:
        if cls.is_active():
            return ["Downloading the update: {:.0f}%".format(100 * KTDownloadNotification.get_current_progress())]
        return []


class KTDownloadingProblem:
    @classmethod
    def is_active(cls):
        return CurrentStateExecutor.compute_current_panel_updater_state() == UpdateState.DOWNLOADING_PROBLEM

    @classmethod
    def render_message(cls, limit: int=32) -> List[str]:
        if cls.is_active():
            _message_text: str = 'Sorry, an unexpected network error happened. Please check your network connection.'
            return render_main(parse_html(_message_text), limit)
        return []

class KT_OT_RetryDownloadUpdate(Operator):
    bl_idname = Config.kt_retry_download_the_update_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        CurrentStateExecutor.set_current_panel_updater_state(UpdateState.DOWNLOADING)
        KTUpdateProgressTimer.start(redraw_view3d=True)
        KTDownloadNotification.init_progress(_download_update())
        return {'FINISHED'}


class KT_OT_ComeBackToUpdate(Operator):
    bl_idname = Config.kt_come_back_to_update_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        _clear_updater_info()
        CurrentStateExecutor.set_current_panel_updater_state(UpdateState.INITIAL)
        return {'FINISHED'}


class KTInstallationReminder:
    @classmethod
    def is_active(cls) -> bool:
        return CurrentStateExecutor.compute_current_panel_updater_state() == UpdateState.INSTALL

    @classmethod
    def is_available(cls) -> bool:
        prefs = get_addon_preferences()
        if not prefs:
            return False
        previous_show_time_str = prefs.latest_show_datetime_installation_reminder
        return _operator_available_time(previous_show_time_str)

    @classmethod
    def render_message(cls, limit: int=32) -> List[str]:
        _message_text: str = \
            'New version of KeenTools add-on is ready to be installed. ' \
            'Make sure all changes are saved before you continue. ' \
            'Blender will be relaunched automatically.'
        return render_main(parse_html(_message_text), limit)

    @classmethod
    def remind_later(cls):
        prefs = get_addon_preferences()
        if not prefs:
            return
        prefs.latest_show_datetime_installation_reminder = \
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


class KT_OT_InstallUpdates(Operator):
    bl_idname = Config.kt_install_updates_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'INTERNAL'}

    not_save_changes: BoolProperty(
        description="Discard changes, install the update and restart Blender",
        name="Discard changes, install the update and restart Blender", default=False
    )

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

        col = layout.column()
        col.prop(self, 'not_save_changes')

    def execute(self, context):
        if not bpy.data.is_dirty or self.not_save_changes:
            _clear_updater_info()
            if not updates_downloaded():
                warn = get_operator(Config.kt_warning_idname)
                warn('INVOKE_DEFAULT', msg=ErrorType.DownloadingProblem)
                _clear_updater_info()
                CurrentStateExecutor.set_current_panel_updater_state(UpdateState.UPDATES_AVAILABLE)
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


class KT_OT_RemindInstallLater(Operator):
    bl_idname = Config.kt_remind_install_later_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        CurrentStateExecutor.set_current_panel_updater_state(UpdateState.INITIAL,
                                                             set_preferences_updater_state=False)
        KTInstallationReminder.remind_later()
        return {'FINISHED'}


class KT_OT_SkipInstallation(Operator):
    bl_idname = Config.kt_skip_installation_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        CurrentStateExecutor.set_current_panel_updater_state(UpdateState.INITIAL,
                                                             set_preferences_updater_state=False)
        prefs = get_addon_preferences()
        if not prefs:
            return {'CANCELLED'}
        prefs.latest_installation_skip_version = prefs.downloaded_version
        return {'FINISHED'}
