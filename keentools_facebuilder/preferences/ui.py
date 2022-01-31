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

import sys
import logging

import bpy
from ..preferences.operators import (
    PREF_OT_InstallPkt,
    PREF_OT_InstallFromFilePkt,
    PREF_OT_InstallLicenseOnline,
    PREF_OT_OpenManualInstallPage,
    PREF_OT_CopyHardwareId,
    PREF_OT_InstallLicenseOffline,
    PREF_OT_DownloadsURL,
    PREF_OT_FloatingConnect,
    PREF_OT_OpenPktLicensePage)
from ..blender_independent_packages.pykeentools_loader import (
    module as pkt_module,
    is_installed as pkt_is_installed,
    is_python_supported as pkt_is_python_supported,
    installation_status as pkt_installation_status,
    loaded as pkt_loaded)
from ..config import (Config, is_blender_supported,
                      get_main_settings, get_operator)
from .formatting import split_by_br_or_newlines
from ..preferences.progress import InstallationProgress
from ..messages import (ERROR_MESSAGES, USER_MESSAGES, draw_system_info,
                        draw_warning_labels, draw_long_labels)
from ..preferences.user_preferences import UserPreferences, UpdaterPreferences
from ..interface.updater import preferences_current_active_updater_operators_info, UpdateState, \
    render_active_message, FBUpdater, CurrentStateExecutor


def _multi_line_text_to_output_labels(layout, txt):
    if txt is None:
        return

    all_lines = split_by_br_or_newlines(txt)
    non_empty_lines = filter(len, all_lines)

    col = layout.column()
    col.scale_y = Config.text_scale_y
    for text_line in non_empty_lines:
        col.label(text=text_line)


def _reset_user_preferences_parameter_to_default(name):
    UserPreferences.reset_parameter_to_default(name)


def _set_all_user_preferences_to_default():
    UserPreferences.reset_all_to_defaults()


def reset_updater_preferences_to_default():
    UpdaterPreferences.reset_all_to_defaults()


class FB_OT_UserPreferencesResetAll(bpy.types.Operator):
    bl_idname = Config.fb_user_preferences_reset_all
    bl_label = 'Reset All'
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = 'Reset All'

    def draw(self, context):
        pass

    def execute(self, context):
        logger = logging.getLogger(__name__)
        logger.debug('user_preferences_reset_all call')
        warn = get_operator(Config.fb_user_preferences_reset_all_warning_idname)
        warn('INVOKE_DEFAULT')
        return {'FINISHED'}


class FB_OT_UserPreferencesGetColors(bpy.types.Operator):
    bl_idname = Config.fb_user_preferences_get_colors
    bl_label = 'Get from scene'
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = 'Get color settings from the current scene'

    def draw(self, context):
        pass

    def execute(self, context):
        logger = logging.getLogger(__name__)
        logger.debug('user_preferences_get_colors')

        settings = get_main_settings()
        preferences = settings.preferences()
        preferences.wireframe_color = settings.wireframe_color
        preferences.wireframe_special_color = settings.wireframe_special_color
        preferences.wireframe_midline_color = settings.wireframe_midline_color
        preferences.wireframe_opacity = settings.wireframe_opacity
        return {'FINISHED'}


class FB_OT_UserPreferencesChanger(bpy.types.Operator):
    bl_idname = Config.fb_user_preferences_changer
    bl_label = 'FaceBuilder Action'
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = 'Reset'

    param_string: bpy.props.StringProperty(name='String parameter')
    action: bpy.props.StringProperty(name='Action Name')

    def draw(self, context):
        pass

    def execute(self, context):
        logger = logging.getLogger(__name__)
        logger.debug('user_preferences_changer: {}'.format(self.action))

        if self.action == 'revert_default':
            _reset_user_preferences_parameter_to_default(self.param_string)
            return {'FINISHED'}
        elif self.action == 'revert_default_colors':
            _reset_user_preferences_parameter_to_default('wireframe_color')
            _reset_user_preferences_parameter_to_default('wireframe_special_color')
            _reset_user_preferences_parameter_to_default('wireframe_midline_color')
            _reset_user_preferences_parameter_to_default('wireframe_opacity')
            return {'FINISHED'}

        return {'CANCELLED'}


class FB_OT_UserPreferencesResetAllWarning(bpy.types.Operator):
    bl_idname = Config.fb_user_preferences_reset_all_warning_idname
    bl_label = 'Reset All'
    bl_options = {'REGISTER', 'INTERNAL'}

    accept: bpy.props.BoolProperty(name='Yes, I really want '
                                        'to reset all settings',
                                   default=False)

    def draw(self, context):
        layout = self.layout.column()
        col = layout.column()
        col.scale_y = Config.text_scale_y
        layout.prop(self, 'accept')

    def execute(self, context):
        if (self.accept):
            logger = logging.getLogger(__name__)
            logger.debug('user_preferences_reset_all')
            _set_all_user_preferences_to_default()
        return {'FINISHED'}

    def cancel(self, context):
        return

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=400)


def _update_user_preferences_pin_size(self, context):
    settings = get_main_settings()
    prefs = settings.preferences()
    settings.pin_size = self.pin_size

    if prefs.pin_sensitivity < self.pin_size:
        prefs.pin_sensitivity = self.pin_size


def _update_user_preferences_pin_sensitivity(self, context):
    settings = get_main_settings()
    prefs = settings.preferences()
    settings.pin_sensitivity = self.pin_sensitivity

    if prefs.pin_size > self.pin_sensitivity:
        prefs.pin_size = self.pin_sensitivity


def _universal_getter(name, type):
    def _getter(self):
        return UserPreferences.get_value_safe(name, type)
    return _getter


def _universal_setter(name):
    def _setter(self, value):
        UserPreferences.set_value(name, value)
    return _setter


def _universal_updater_getter(name, type):
    def _getter(self):
        return UpdaterPreferences.get_value_safe(name, type)
    return _getter


def _universal_updater_setter(name):
    def _setter(self, value):
        UpdaterPreferences.set_value(name, value)
    return _setter


class FBAddonPreferences(bpy.types.AddonPreferences):
    bl_idname = Config.addon_name

    latest_show_datetime_update_reminder: bpy.props.StringProperty(
        name='Latest show update reminder', default='',
        get=_universal_updater_getter('latest_show_datetime_update_reminder', 'string'),
        set=_universal_updater_setter('latest_show_datetime_update_reminder')
    )

    latest_update_skip_version: bpy.props.StringProperty(
        name='Latest update skip version', default='',
        get=_universal_updater_getter('latest_update_skip_version', 'string'),
        set=_universal_updater_setter('latest_update_skip_version')
    )

    updater_state: bpy.props.IntProperty(
        name='Updater state', default=1,
        get=_universal_updater_getter('updater_state', 'int'),
        set=_universal_updater_setter('updater_state')
    )

    downloaded_version: bpy.props.StringProperty(
        name='Downloaded version', default='',
        get=_universal_updater_getter('downloaded_version', 'string'),
        set=_universal_updater_setter('downloaded_version')
    )

    latest_installation_skip_version: bpy.props.StringProperty(
        name='Latest installation skip version', default='',
        get=_universal_updater_getter('latest_installation_skip_version', 'string'),
        set=_universal_updater_setter('latest_installation_skip_version')
    )

    latest_show_datetime_installation_reminder: bpy.props.StringProperty(
        name='Latest show installation reminder', default='',
        get=_universal_updater_getter('latest_show_datetime_installation_reminder', 'string'),
        set=_universal_updater_setter('latest_show_datetime_installation_reminder')
    )

    license_accepted: bpy.props.BoolProperty(
        name='I have read and I agree to KeenTools End-user License Agreement',
        default=False
    )

    license_id: bpy.props.StringProperty(
        name="License key", default=""
    )

    license_server: bpy.props.StringProperty(
        name="License Server host/IP", default="localhost"
    )

    license_server_port: bpy.props.IntProperty(
        name="License Server port", default=7096, min=0, max=65535
    )

    license_server_lock: bpy.props.BoolProperty(
        name="Variables from ENV", default=False
    )

    license_server_auto: bpy.props.BoolProperty(
        name="Auto settings from Environment", default=True
    )

    hardware_id: bpy.props.StringProperty(
        name="Hardware ID", default=""
    )

    lic_type: bpy.props.EnumProperty(
        name="Type",
        items=(
            ('ONLINE', "Online", "Online license management", 0),
            ('OFFLINE', "Offline", "Offline license management", 1),
            ('FLOATING', "Floating", "Floating license management", 2)),
        default='ONLINE')

    install_type: bpy.props.EnumProperty(
        name="Type",
        items=(
            ('ONLINE', "Online", "Online installation", 0),
            ('OFFLINE', "Offline", "Offline installation", 1)),
        default='ONLINE')

    lic_status: bpy.props.StringProperty(
        name="license status", default=""
    )

    lic_path: bpy.props.StringProperty(
            name="License file",
            description="absolute path to license file",
            default="",
            subtype="FILE_PATH"
    )

    more_info: bpy.props.BoolProperty(
        name='More Info',
        default=False
    )

    # User preferences
    show_user_preferences: bpy.props.BoolProperty(
        name='Addon Settings',
        default=False
    )
    pin_size: bpy.props.FloatProperty(
        description="Set pin size in pixels",
        name="Size", min=1.0, max=100.0,
        precision=1,
        get=_universal_getter('pin_size', 'float'),
        set=_universal_setter('pin_size'),
        update=_update_user_preferences_pin_size)
    pin_sensitivity: bpy.props.FloatProperty(
        description="Set active area in pixels",
        name="Active area", min=1.0, max=100.0,
        precision=1,
        get=_universal_getter('pin_sensitivity', 'float'),
        set=_universal_setter('pin_sensitivity'),
        update=_update_user_preferences_pin_sensitivity)
    prevent_view_rotation: bpy.props.BoolProperty(
        name='Prevent accidental exit from Pin Mode',
        get=_universal_getter('prevent_view_rotation', 'bool'),
        set=_universal_setter('prevent_view_rotation'),
    )
    wireframe_opacity: bpy.props.FloatProperty(
        description="From 0.0 to 1.0",
        name="Wireframe opacity",
        default=Config.wireframe_opacity, min=0.0, max=1.0,
        get=_universal_getter('wireframe_opacity', 'float'),
        set=_universal_setter('wireframe_opacity')
    )
    wireframe_color: bpy.props.FloatVectorProperty(
        description="Color of mesh wireframe in pin-mode",
        name="Wireframe Color", subtype='COLOR',
        default=Config.color_schemes['default'][0],
        get=_universal_getter('wireframe_color', 'color'),
        set=_universal_setter('wireframe_color')
    )
    wireframe_special_color: bpy.props.FloatVectorProperty(
        description="Color of special parts in pin-mode",
        name="Wireframe Special Color", subtype='COLOR',
        default=Config.color_schemes['default'][1],
        get=_universal_getter('wireframe_special_color', 'color'),
        set=_universal_setter('wireframe_special_color')
    )
    wireframe_midline_color: bpy.props.FloatVectorProperty(
        description="Color of midline in pin-mode",
        name="Wireframe Midline Color", subtype='COLOR',
        default=Config.midline_color,
        get=_universal_getter('wireframe_midline_color', 'color'),
        set=_universal_setter('wireframe_midline_color')
    )

    def _license_was_accepted(self):
        return pkt_is_installed() or self.license_accepted

    def _draw_license_info(self, layout):
        layout.label(text='License info:')
        box = layout.box()

        lm = pkt_module().FaceBuilder.license_manager()

        _multi_line_text_to_output_labels(box, lm.license_status_text(strategy=pkt_module().LicenseCheckStrategy.LAZY))

        box.row().prop(self, "lic_type", expand=True)

        if self.lic_type == 'ONLINE':
            box = layout.box()
            row = box.split(factor=0.85)
            row.prop(self, "license_id")
            install_online_op = row.operator(PREF_OT_InstallLicenseOnline.bl_idname)
            install_online_op.license_id = self.license_id

        elif self.lic_type == 'OFFLINE':
            self.hardware_id = lm.hardware_id()

            row = layout.split(factor=0.65)
            row.label(text="Get an activated license file at our site:")
            row.operator(
                PREF_OT_OpenManualInstallPage.bl_idname,
                icon='URL')

            box = layout.box()
            row = box.split(factor=0.85)
            row.prop(self, "hardware_id")
            row.operator(PREF_OT_CopyHardwareId.bl_idname)

            row = box.split(factor=0.85)
            row.prop(self, "lic_path")
            install_offline_op = row.operator(PREF_OT_InstallLicenseOffline.bl_idname)
            install_offline_op.lic_path = self.lic_path

        elif self.lic_type == 'FLOATING':
            env = pkt_module().LicenseManager.env_server_info()
            if env is not None:
                self.license_server = env[0]
                self.license_server_port = env[1]
                self.license_server_lock = True
            else:
                self.license_server_lock = False

            box = layout.box()
            row = box.split(factor=0.35)
            row.label(text="License Server host/IP")
            if self.license_server_lock and self.license_server_auto:
                row.label(text=self.license_server)
            else:
                row.prop(self, "license_server", text="")

            row = box.split(factor=0.35)
            row.label(text="License Server port")
            if self.license_server_lock and self.license_server_auto:
                row.label(text=str(self.license_server_port))
            else:
                row.prop(self, "license_server_port", text="")

            if self.license_server_lock:
                box.prop(self, "license_server_auto",
                         text="Auto server/port settings")

            floating_install_op = row.operator(PREF_OT_FloatingConnect.bl_idname)
            floating_install_op.license_server = self.license_server
            floating_install_op.license_server_port = self.license_server_port

    def _draw_warning_labels(self, layout, content, alert=True, icon='INFO'):
        col = layout.column()
        col.alert = alert
        col.scale_y = Config.text_scale_y
        for i, c in enumerate(content):
            icon_first = icon if i == 0 else 'BLANK1'
            col.label(text=c, icon=icon_first)
        return col

    def _draw_download_install_buttons(self, layout):
        # Install online / Install from disk / Download
        row = layout.split(factor=0.35)
        box2 = row.box()
        row2 = box2.row()
        if not self.license_accepted:
            row2.active = False
            # row2.alert = True

        op = row2.operator(
            PREF_OT_InstallPkt.bl_idname,
            text='Install online', icon='WORLD')
        op.license_accepted = self._license_was_accepted()

        box2 = row.box()
        row2 = box2.split(factor=0.6)
        if not self.license_accepted:
            row2.active = False
            # row2.alert = True

        op = row2.operator(
            PREF_OT_InstallFromFilePkt.bl_idname,
            text='Install from disk', icon='FILEBROWSER')
        op.license_accepted = self._license_was_accepted()

        op = row2.operator(
            PREF_OT_DownloadsURL.bl_idname,
            text='Download', icon='URL')
        op.url = Config.core_download_website_url

    def _draw_please_accept_license(self, layout):
        box = layout.box()
        self._draw_warning_labels(box, USER_MESSAGES['WE_CANNOT_SHIP'])

        box2 = box.box()
        row = box2.split(factor=0.85)
        row.prop(self, 'license_accepted')

        row.operator(
            PREF_OT_OpenPktLicensePage.bl_idname,
            text='Read', icon='URL'
        )

        self._draw_download_install_buttons(box)
        return box

    def _draw_accepted_license(self, layout):
        box = layout.box()
        row = box.split(factor=0.75)
        row.label(text='KeenTools End-User License Agreement [accepted]')
        row.operator(
            PREF_OT_OpenPktLicensePage.bl_idname,
            text='Read', icon='URL')
        return box

    def _draw_download_progress(self, layout):
        col = layout.column()
        col.scale_y = Config.text_scale_y
        download_state = InstallationProgress.get_state()
        if download_state['active']:
            col.label(text="Downloading: {:.1f}%".format(
                100 * download_state['progress']))
        if download_state['status'] is not None:
            col.label(text="{}".format(download_state['status']))

    def _draw_pkt_detail_error_report(self, layout, status):
        status_to_errors = {
            'NOT_INSTALLED': 'CORE_NOT_INSTALLED',
            'INSTALLED_WRONG': 'INSTALLED_WRONG_INSTEAD_CORE',
            'CANNOT_IMPORT': 'CORE_CANNOT_IMPORT',
            'NO_VERSION': 'CORE_HAS_NO_VERSION',
            'VERSION_PROBLEM': 'CORE_VERSION_PROBLEM',
            'PYKEENTOOLS_OK': 'PYKEENTOOLS_OK'
        }

        assert(status in status_to_errors.keys())
        error = status_to_errors[status]
        assert(error in ERROR_MESSAGES.keys())

        draw_warning_labels(
            layout, ERROR_MESSAGES[error], alert=True, icon='ERROR')

        if status in ('INSTALLED_WRONG', 'CANNOT_IMPORT',
                      'NO_VERSION', 'VERSION_PROBLEM'):
            # Core Uninstall button
            layout.operator(Config.fb_uninstall_core_idname)

    def _get_core_version_text(self):
        try:
            txt = "Version {}, built {}".format(pkt_module().__version__,
                                                pkt_module().build_time)
            return txt
        except Exception as err:
            logger = logging.getLogger(__name__)
            logger.error('_get_core_version_text: {}'.format(str(err)))
            return None

    def _draw_updater_info(self, layout):
        FBUpdater.init_updater()
        CurrentStateExecutor.compute_current_panel_updater_state()
        settings = get_main_settings()
        if settings.preferences().updater_state != UpdateState.INITIAL:
            layout.label(text='Update available:')
            box = layout.box()
            col = box.column()
            render_active_message(col)
            operators_info = preferences_current_active_updater_operators_info()
            if operators_info is not None:
                box = box.split(factor=1 / len(operators_info))
                for info in operators_info:
                    box.operator(info.idname, text=info.text, icon=info.icon)

    def _draw_old_addon(self, layout):
        box = layout.box()
        draw_warning_labels(box, ERROR_MESSAGES['OLD_ADDON'])
        return box

    def _draw_blender_with_unsupported_python(self, layout):
        box = layout.box()
        draw_warning_labels(
            box, ERROR_MESSAGES['BLENDER_WITH_UNSUPPORTED_PYTHON'])
        return box

    def _draw_unsupported_python(self, layout):
        if is_blender_supported():
            self._draw_blender_with_unsupported_python(layout)
        else:
            self._draw_old_addon(layout)
            row = layout.split(factor=0.35)
            op = row.operator(
                PREF_OT_DownloadsURL.bl_idname,
                text='Download', icon='URL')
            op.url = Config.core_download_website_url

    def _get_problem_info(self):
        info = []
        if 'pykeentools' in sys.modules:
            try:
                import importlib
                sp = importlib.util.find_spec('pykeentools')
                if sp is not None:
                    info.append(sp.origin)
                    [info.append(x) for x in sp.submodule_search_locations]
            except Exception:
                info.append('Cannot detect pykeentools spec.')
        else:
            info.append('No pykeentools in modules.')
        return info

    def _draw_problem_library(self, layout):
        info = self._get_problem_info()
        if len(info) == 0:
            return
        icon = 'TRIA_RIGHT' if not self.more_info else 'TRIA_DOWN'
        layout.prop(self, 'more_info', toggle=1, icon=icon)
        if not self.more_info:
            return
        col = layout.column()
        col.scale_y = Config.text_scale_y
        draw_long_labels(col, info, 120)

    def _draw_user_preferences(self, layout):
        icon = 'TRIA_RIGHT' if not self.show_user_preferences else 'TRIA_DOWN'
        main_box = layout.box()
        if not self.show_user_preferences:
            main_box.prop(self, 'show_user_preferences', icon=icon)
            return
        main_box.prop(self, 'show_user_preferences', icon=icon,
                      invert_checkbox=True)  # emboss=False

        box = main_box.box()
        box.prop(self, 'prevent_view_rotation')

        box = main_box.box()
        box.label(text='Default pin settings')
        row = box.split(factor=0.7)
        row.prop(self, 'pin_size', slider=True)
        op = row.operator(Config.fb_user_preferences_changer, text='Reset')
        op.action = 'revert_default'
        op.param_string = 'pin_size'

        row = box.split(factor=0.7)
        row.prop(self, 'pin_sensitivity', slider=True)
        op = row.operator(Config.fb_user_preferences_changer, text='Reset')
        op.action = 'revert_default'
        op.param_string = 'pin_sensitivity'

        box = main_box.box()
        split = box.split(factor=0.7)
        split.label(text='Default wireframe colors')
        split.operator(Config.fb_user_preferences_get_colors)

        colors_row = box.split(factor=0.7)
        row = colors_row.row()
        row.prop(self, 'wireframe_color', text='')
        row.prop(self, 'wireframe_special_color', text='')
        row.prop(self, 'wireframe_midline_color', text='')
        row.prop(self, 'wireframe_opacity', text='', slider=True)

        op = colors_row.operator(Config.fb_user_preferences_changer,
                                 text='Reset')
        op.action = 'revert_default_colors'

        main_box.operator(Config.fb_user_preferences_reset_all)

    def draw(self, context):
        layout = self.layout

        if not pkt_is_python_supported():
            self._draw_unsupported_python(layout)
            draw_system_info(layout)
            return

        cached_status = pkt_installation_status()
        assert(cached_status is not None)

        if cached_status[1] == 'NOT_INSTALLED':
            if pkt_loaded():
                box = layout.box()
                draw_warning_labels(
                    box, USER_MESSAGES['RESTART_BLENDER_TO_UNLOAD_CORE'])
                self._draw_problem_library(box)
                draw_system_info(layout)
                return

            self._draw_please_accept_license(layout)
            self._draw_download_progress(layout)
            return

        if cached_status[1] == 'PYKEENTOOLS_OK':
            core_txt = self._get_core_version_text()
            if core_txt is not None:
                box = layout.box()
                msg = [core_txt,
                       'The core library has been installed successfully']
                draw_warning_labels(box, msg, alert=False, icon='INFO')
                self._draw_updater_info(layout)
                self._draw_license_info(layout)
                self._draw_user_preferences(layout)
                return

            cached_status = (False, 'NO_VERSION')

        box = layout.box()
        self._draw_pkt_detail_error_report(box, cached_status[1])
        self._draw_problem_library(box)
        draw_system_info(layout)

        self._draw_download_progress(layout)
