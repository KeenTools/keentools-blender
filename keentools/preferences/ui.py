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
from ..blender_independent_packages.pykeentools_loader import (
    module as pkt_module,
    is_installed as pkt_is_installed,
    is_python_supported as pkt_is_python_supported,
    installation_status as pkt_installation_status,
    loaded as pkt_loaded)
from ..addon_config import Config, get_operator, is_blender_supported
from ..facebuilder_config import FBConfig, get_fb_settings
from ..geotracker_config import GTConfig
from .formatting import split_by_br_or_newlines
from ..preferences.progress import InstallationProgress
from ..messages import (ERROR_MESSAGES, USER_MESSAGES, draw_system_info,
                        draw_warning_labels, draw_long_labels)
from ..preferences.user_preferences import UserPreferences, UpdaterPreferences
from ..updater.utils import (preferences_current_active_updater_operators_info,
                             UpdateState,
                             render_active_message,
                             KTUpdater,
                             CurrentStateExecutor)
from .operators import get_product_license_manager


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


def _expand_icon(value):
    return 'TRIA_RIGHT' if not value else 'TRIA_DOWN'


def _expandable_button(layout, data, property, text=None):
    prop_value = getattr(data, property)
    if text is None:
        layout.prop(data, property,
                    icon=_expand_icon(prop_value))
    else:
        layout.prop(data, property, text=text,
                    icon=_expand_icon(prop_value))
    return prop_value


class FB_OT_UserPreferencesResetAll(bpy.types.Operator):
    bl_idname = FBConfig.fb_user_preferences_reset_all
    bl_label = 'Reset All'
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = 'Reset All'

    def draw(self, context):
        pass

    def execute(self, context):
        logger = logging.getLogger(__name__)
        logger.debug('user_preferences_reset_all call')
        warn = get_operator(FBConfig.fb_user_preferences_reset_all_warning_idname)
        warn('INVOKE_DEFAULT')
        return {'FINISHED'}


class FB_OT_UserPreferencesGetColors(bpy.types.Operator):
    bl_idname = FBConfig.fb_user_preferences_get_colors
    bl_label = 'Get from scene'
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = 'Get color settings from the current scene'

    def draw(self, context):
        pass

    def execute(self, context):
        logger = logging.getLogger(__name__)
        logger.debug('user_preferences_get_colors')

        settings = get_fb_settings()
        preferences = settings.preferences()
        preferences.wireframe_color = settings.wireframe_color
        preferences.wireframe_special_color = settings.wireframe_special_color
        preferences.wireframe_midline_color = settings.wireframe_midline_color
        preferences.fb_wireframe_opacity = settings.wireframe_opacity
        return {'FINISHED'}


class FB_OT_UserPreferencesChanger(bpy.types.Operator):
    bl_idname = FBConfig.fb_user_preferences_changer
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
            _reset_user_preferences_parameter_to_default('fb_wireframe_color')
            _reset_user_preferences_parameter_to_default('fb_wireframe_special_color')
            _reset_user_preferences_parameter_to_default('fb_wireframe_midline_color')
            _reset_user_preferences_parameter_to_default('fb_wireframe_opacity')
            return {'FINISHED'}

        return {'CANCELLED'}


class FB_OT_UserPreferencesResetAllWarning(bpy.types.Operator):
    bl_idname = FBConfig.fb_user_preferences_reset_all_warning_idname
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
    settings = get_fb_settings()
    prefs = settings.preferences()
    settings.pin_size = self.pin_size

    if prefs.pin_sensitivity < self.pin_size:
        prefs.pin_sensitivity = self.pin_size


def _update_user_preferences_pin_sensitivity(self, context):
    settings = get_fb_settings()
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


_lic_type_items = (('ONLINE', 'Online', 'Online license management', 0),
            ('OFFLINE', 'Offline', 'Offline license management', 1),
            ('FLOATING', 'Floating', 'Floating license management', 2))


class KTAddonPreferences(bpy.types.AddonPreferences):
    bl_idname = Config.addon_name

    facebuilder_enabled: bpy.props.BoolProperty(
        name='Enable KeenTools FaceBuilder',
        default=True
    )
    facebuilder_expanded: bpy.props.BoolProperty(
        name='KeenTools FaceBuilder',
        default=False
    )

    geotracker_enabled: bpy.props.BoolProperty(
        name='Enable KeenTools GeoTracker',
        default=not Config.hide_geotracker
    )
    geotracker_expanded: bpy.props.BoolProperty(
        name='KeenTools GeoTracker',
        default=False
    )

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

    license_key: bpy.props.StringProperty(
        name="License key", default=""
    )

    fb_license_server: bpy.props.StringProperty(
        name="License Server host/IP", default="localhost"
    )
    gt_license_server: bpy.props.StringProperty(
        name="License Server host/IP", default="localhost"
    )

    fb_license_server_port: bpy.props.IntProperty(
        name="License Server port", default=7096, min=0, max=65535
    )
    gt_license_server_port: bpy.props.IntProperty(
        name="License Server port", default=7096, min=0, max=65535
    )

    fb_license_server_lock: bpy.props.BoolProperty(
        name="Variables from ENV", default=False
    )
    gt_license_server_lock: bpy.props.BoolProperty(
        name="Variables from ENV", default=False
    )

    fb_license_server_auto: bpy.props.BoolProperty(
        name="Auto settings from Environment", default=True
    )
    gt_license_server_auto: bpy.props.BoolProperty(
        name="Auto settings from Environment", default=True
    )

    hardware_id: bpy.props.StringProperty(
        name="Hardware ID", default=""
    )

    fb_lic_type: bpy.props.EnumProperty(
        name="Type",
        items=_lic_type_items,
        default='ONLINE')

    gt_lic_type: bpy.props.EnumProperty(
        name="Type",
        items=_lic_type_items,
        default='ONLINE')

    fb_lic_path: bpy.props.StringProperty(
            name="License file",
            description="absolute path to license file",
            default="",
            subtype="FILE_PATH"
    )

    gt_lic_path: bpy.props.StringProperty(
            name="License file",
            description="absolute path to license file",
            default="",
            subtype="FILE_PATH"
    )

    more_info: bpy.props.BoolProperty(
        name='More Info',
        default=False
    )

    # Common User Preferences
    pin_size: bpy.props.FloatProperty(
        description='Set pin size in pixels',
        name='Size', min=1.0, max=100.0,
        precision=1,
        get=_universal_getter('pin_size', 'float'),
        set=_universal_setter('pin_size'),
        update=_update_user_preferences_pin_size)
    pin_sensitivity: bpy.props.FloatProperty(
        description='Set active area in pixels',
        name='Active area', min=1.0, max=100.0,
        precision=1,
        get=_universal_getter('pin_sensitivity', 'float'),
        set=_universal_setter('pin_sensitivity'),
        update=_update_user_preferences_pin_sensitivity)

    # FaceBuilder User preferences
    show_fb_user_preferences: bpy.props.BoolProperty(
        name='FaceBuilder Settings',
        default=False
    )
    prevent_fb_view_rotation: bpy.props.BoolProperty(
        name='Prevent accidental exit from Pin Mode in FaceBuilder',
        get=_universal_getter('prevent_fb_view_rotation', 'bool'),
        set=_universal_setter('prevent_fb_view_rotation'),
    )
    fb_wireframe_opacity: bpy.props.FloatProperty(
        description='From 0.0 to 1.0',
        name='FaceBuilder wireframe opacity',
        default=FBConfig.wireframe_opacity, min=0.0, max=1.0,
        get=_universal_getter('fb_wireframe_opacity', 'float'),
        set=_universal_setter('fb_wireframe_opacity')
    )
    fb_wireframe_color: bpy.props.FloatVectorProperty(
        description='Color of mesh wireframe in FaceBuilder pin-mode',
        name="Wireframe Color", subtype='COLOR',
        default=FBConfig.color_schemes['default'][0],
        get=_universal_getter('fb_wireframe_color', 'color'),
        set=_universal_setter('fb_wireframe_color')
    )
    fb_wireframe_special_color: bpy.props.FloatVectorProperty(
        description='Color of special parts in FaceBuilder pin-mode',
        name='Wireframe Special Color', subtype='COLOR',
        default=FBConfig.color_schemes['default'][1],
        get=_universal_getter('fb_wireframe_special_color', 'color'),
        set=_universal_setter('fb_wireframe_special_color')
    )
    fb_wireframe_midline_color: bpy.props.FloatVectorProperty(
        description="Color of midline in pin-mode",
        name="Wireframe Midline Color", subtype='COLOR',
        default=FBConfig.midline_color,
        get=_universal_getter('fb_wireframe_midline_color', 'color'),
        set=_universal_setter('fb_wireframe_midline_color')
    )

    # GeoTracker User Preferences
    show_gt_user_preferences: bpy.props.BoolProperty(
        name='GeoTracker Settings',
        default=False
    )
    prevent_gt_view_rotation: bpy.props.BoolProperty(
        name='Prevent accidental exit from Pin Mode in GeoTracker',
        get=_universal_getter('prevent_gt_view_rotation', 'bool'),
        set=_universal_setter('prevent_gt_view_rotation'),
    )
    gt_wireframe_color: bpy.props.FloatVectorProperty(
        description='Color of GeoTracker mesh wireframe in pin-mode',
        name='Wireframe Color', subtype='COLOR',
        default=GTConfig.wireframe_color[:3],
        get=_universal_getter('gt_wireframe_color', 'color'),
        set=_universal_setter('gt_wireframe_color')
    )
    gt_wireframe_opacity: bpy.props.FloatProperty(
        description='From 0.0 to 1.0',
        name='GeoTracker wireframe opacity',
        default=GTConfig.wireframe_color[3], min=0.0, max=1.0,
        get=_universal_getter('gt_wireframe_opacity', 'float'),
        set=_universal_setter('gt_wireframe_opacity')
    )
    gt_mask_3d_color: bpy.props.FloatVectorProperty(
        description='Color of GeoTracker masked mesh excluded from tracking',
        name='Wireframe Color', subtype='COLOR',
        default=GTConfig.mask_3d_color[:3],
        get=_universal_getter('gt_mask_3d_color', 'color'),
        set=_universal_setter('gt_mask_3d_color')
    )
    gt_mask_3d_opacity: bpy.props.FloatProperty(
        description='From 0.0 to 1.0',
        name='GeoTracker masked mesh opacity',
        default=GTConfig.mask_3d_color[3], min=0.0, max=1.0,
        get=_universal_getter('gt_mask_3d_opacity', 'float'),
        set=_universal_setter('gt_mask_3d_opacity')
    )
    gt_mask_2d_color: bpy.props.FloatVectorProperty(
        description='Color of GeoTracker masked mesh excluded from tracking',
        name='Wireframe Color', subtype='COLOR',
        default=GTConfig.mask_2d_color[:3],
        get=_universal_getter('gt_mask_2d_color', 'color'),
        set=_universal_setter('gt_mask_2d_color')
    )
    gt_mask_2d_opacity: bpy.props.FloatProperty(
        description='From 0.0 to 1.0',
        name='GeoTracker masked mesh opacity',
        default=GTConfig.mask_2d_color[3], min=0.0, max=1.0,
        get=_universal_getter('gt_mask_2d_opacity', 'float'),
        set=_universal_setter('gt_mask_2d_opacity')
    )

    def _license_was_accepted(self):
        return pkt_is_installed() or self.license_accepted

    def _draw_fb_license_info(self, layout):
        layout.label(text='FaceBuilder license info:')
        box = layout.box()

        lm = get_product_license_manager('facebuilder')
        _multi_line_text_to_output_labels(box, lm.license_status_text(
            strategy=pkt_module().LicenseCheckStrategy.LAZY))

        box.row().prop(self, 'fb_lic_type', expand=True)

        if self.fb_lic_type == 'ONLINE':
            box = layout.box()
            row = box.split(factor=0.85)
            row.prop(self, 'license_key')
            install_online_op = row.operator(Config.kt_install_license_online_idname)
            install_online_op.license_key = self.license_key
            install_online_op.product = 'facebuilder'

        elif self.fb_lic_type == 'OFFLINE':
            self.hardware_id = lm.hardware_id()

            row = layout.split(factor=0.65)
            row.label(text='Get an activated license file at our site:')
            op = row.operator(Config.kt_open_manual_install_page_idname, icon='URL')
            op.product = 'facebuilder'

            box = layout.box()
            row = box.split(factor=0.85)
            row.prop(self, 'hardware_id')
            row.operator(Config.kt_copy_hardware_id_idname)

            row = box.split(factor=0.85)
            row.prop(self, 'fb_lic_path')
            install_offline_op = row.operator(Config.kt_install_license_offline_idname)
            install_offline_op.lic_path = self.fb_lic_path
            install_offline_op.product = 'facebuilder'

        elif self.fb_lic_type == 'FLOATING':
            env = pkt_module().LicenseManager.env_server_info()
            if env is not None:
                self.fb_license_server = env[0]
                self.fb_license_server_port = env[1]
                self.fb_license_server_lock = True
            else:
                self.fb_license_server_lock = False

            box = layout.box()
            row = box.split(factor=0.35)
            row.label(text='License Server host/IP')
            if self.fb_license_server_lock and self.fb_license_server_auto:
                row.label(text=self.fb_license_server)
            else:
                row.prop(self, 'fb_license_server', text='')

            row = box.split(factor=0.35)
            row.label(text='License Server port')
            if self.fb_license_server_lock and self.fb_license_server_auto:
                row.label(text=str(self.fb_license_server_port))
            else:
                row.prop(self, 'fb_license_server_port', text='')

            if self.fb_license_server_lock:
                box.prop(self, 'fb_license_server_auto',
                         text='Auto server/port settings')

            floating_install_op = row.operator(Config.kt_floating_connect_idname)
            floating_install_op.license_server = self.fb_license_server
            floating_install_op.license_server_port = self.fb_license_server_port
            floating_install_op.product = 'facebuilder'

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
            Config.kt_install_latest_pkt_idname,
            text='Install online', icon='WORLD')
        op.license_accepted = self._license_was_accepted()

        box2 = row.box()
        row2 = box2.split(factor=0.6)
        if not self.license_accepted:
            row2.active = False
            # row2.alert = True

        op = row2.operator(Config.kt_install_pkt_from_file_idname,
                           text='Install from disk', icon='FILEBROWSER')
        op.license_accepted = self._license_was_accepted()

        op = row2.operator(Config.kt_pref_downloads_url_idname,
                           text='Download', icon='URL')
        op.url = Config.core_download_website_url

    def _draw_please_accept_license(self, layout):
        box = layout.box()
        self._draw_warning_labels(box, USER_MESSAGES['WE_CANNOT_SHIP'])

        box2 = box.box()
        row = box2.split(factor=0.85)
        row.prop(self, 'license_accepted')

        row.operator(Config.kt_open_pkt_license_page_idname,
                     text='Read', icon='URL')

        self._draw_download_install_buttons(box)
        return box

    def _draw_accepted_license(self, layout):
        box = layout.box()
        row = box.split(factor=0.75)
        row.label(text='KeenTools End-User License Agreement [accepted]')
        row.operator(Config.kt_open_pkt_license_page_idname,
                     text='Read', icon='URL')
        return box

    def _draw_download_progress(self, layout):
        download_state = InstallationProgress.get_state()
        if download_state['active']:
            col = layout.column()
            col.scale_y = Config.text_scale_y
            col.label(text="Downloading: {:.1f}%".format(
                100 * download_state['progress']))
        if download_state['status'] is not None:
            col = layout.column()
            col.scale_y = Config.text_scale_y
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
            layout.operator(Config.kt_uninstall_core_idname)

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
        KTUpdater.call_updater('FaceBuilder')
        CurrentStateExecutor.compute_current_panel_updater_state()
        settings = get_fb_settings()
        if settings is None:
            return
        if settings.preferences().updater_state == UpdateState.INITIAL:
            return

        output_list = render_active_message()
        operators_info = preferences_current_active_updater_operators_info()

        if len(output_list) == 0 and operators_info is None:
            return

        layout.label(text='Update available:')
        box = layout.box()
        col = box.column()
        col.scale_y = Config.text_scale_y
        col.alert = settings.preferences().updater_state == UpdateState.DOWNLOADING_PROBLEM
        for txt in output_list:
            col.label(text=txt)

        if operators_info is not None:
            box2 = box.split(factor=1.0 / len(operators_info))
            for info in operators_info:
                box2.operator(info.idname, text=info.text, icon=info.icon)

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
            op = row.operator(Config.kt_pref_downloads_url_idname,
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

    def _draw_fb_user_preferences(self, layout):
        main_box = layout
        if not _expandable_button(main_box, self, 'show_fb_user_preferences'):
            return

        box = main_box.box()
        box.prop(self, 'prevent_fb_view_rotation')

        box = main_box.box()
        box.label(text='Default pin settings')
        row = box.split(factor=0.7)
        row.prop(self, 'pin_size', slider=True)
        op = row.operator(FBConfig.fb_user_preferences_changer, text='Reset')
        op.action = 'revert_default'
        op.param_string = 'pin_size'

        row = box.split(factor=0.7)
        row.prop(self, 'pin_sensitivity', slider=True)
        op = row.operator(FBConfig.fb_user_preferences_changer, text='Reset')
        op.action = 'revert_default'
        op.param_string = 'pin_sensitivity'

        box = main_box.box()
        split = box.split(factor=0.7)
        split.label(text='Default wireframe colors')
        split.operator(FBConfig.fb_user_preferences_get_colors)

        colors_row = box.split(factor=0.7)
        row = colors_row.row()
        row.prop(self, 'fb_wireframe_color', text='')
        row.prop(self, 'fb_wireframe_special_color', text='')
        row.prop(self, 'fb_wireframe_midline_color', text='')
        row.prop(self, 'fb_wireframe_opacity', text='', slider=True)

        op = colors_row.operator(FBConfig.fb_user_preferences_changer,
                                 text='Reset')
        op.action = 'revert_default_colors'

        main_box.operator(FBConfig.fb_user_preferences_reset_all)

    def _draw_gt_user_preferences(self, layout):
        main_box = layout
        if not _expandable_button(main_box, self, 'show_gt_user_preferences'):
            return

        box = main_box.box()
        box.prop(self, 'prevent_gt_view_rotation')

        box = main_box.box()
        box.label(text='Default pin settings')
        row = box.split(factor=0.7)
        row.prop(self, 'pin_size', slider=True)
        op = row.operator(FBConfig.fb_user_preferences_changer, text='Reset')
        op.action = 'revert_default'
        op.param_string = 'pin_size'

        row = box.split(factor=0.7)
        row.prop(self, 'pin_sensitivity', slider=True)
        op = row.operator(FBConfig.fb_user_preferences_changer, text='Reset')
        op.action = 'revert_default'
        op.param_string = 'pin_sensitivity'

        box = main_box.box()
        split = box.split(factor=0.7)
        split.label(text='Default wireframe colors')
        split.operator(FBConfig.fb_user_preferences_get_colors)

        colors_row = box.split(factor=0.7)
        row = colors_row.row()
        row.prop(self, 'gt_wireframe_color', text='')
        row.prop(self, 'gt_wireframe_opacity', text='', slider=True)

        op = colors_row.operator(FBConfig.fb_user_preferences_changer,
                                 text='Reset')
        op.action = 'revert_default_colors'

        box = main_box.box()
        colors_row = box.split(factor=0.7)
        row = colors_row.row()
        row.label(text='3d mask color')
        row.prop(self, 'gt_mask_3d_color', text='')
        row.prop(self, 'gt_mask_3d_opacity', text='', slider=True)
        op = colors_row.operator(FBConfig.fb_user_preferences_changer,
                                 text='Reset')
        op.action = 'revert_default_colors'

        colors_row = box.split(factor=0.7)
        row = colors_row.row()
        row.label(text='2d mask color')
        row.prop(self, 'gt_mask_2d_color', text='')
        row.prop(self, 'gt_mask_2d_opacity', text='', slider=True)
        op = colors_row.operator(FBConfig.fb_user_preferences_changer,
                                 text='Reset')
        op.action = 'revert_default_colors'

        main_box.operator(FBConfig.fb_user_preferences_reset_all)

    def _draw_core_python_problem(self, layout):
        if not pkt_is_python_supported():
            self._draw_unsupported_python(layout)
            draw_system_info(layout)
            return True
        return False

    def _draw_core_installation_progress(self, layout):
        cached_status = pkt_installation_status()
        if cached_status[1] == 'NOT_INSTALLED':
            if pkt_loaded():
                box = layout.box()
                draw_warning_labels(
                    box, USER_MESSAGES['RESTART_BLENDER_TO_UNLOAD_CORE'])
                self._draw_problem_library(box)
                draw_system_info(layout)
                return True

            self._draw_please_accept_license(layout)
            self._draw_download_progress(layout)
            return True
        return False

    def _draw_pykeentools_problem_report(self, layout, pykeentools_status):
        box = layout.box()
        self._draw_pkt_detail_error_report(box, pykeentools_status)
        self._draw_problem_library(box)
        draw_system_info(layout)
        self._draw_download_progress(layout)

    def _draw_pykeentools_problem(self, layout):
        cached_status = pkt_installation_status()
        if cached_status[1] != 'PYKEENTOOLS_OK':
            self._draw_pykeentools_problem_report(layout, cached_status[1])
            return True
        return False

    def _draw_core_info(self, layout):
        cached_status = pkt_installation_status()
        if cached_status[1] == 'PYKEENTOOLS_OK':
            core_txt = self._get_core_version_text()
            if core_txt is not None:
                box = layout.box()
                msg = [core_txt,
                       'The core library has been installed successfully']
                draw_warning_labels(box, msg, alert=False, icon='INFO')
                return True

        self._draw_pykeentools_problem_report(layout, 'NO_VERSION')
        return False

    def _draw_gt_license_info(self, layout):
        layout.label(text='GeoTracker license info:')
        box = layout.box()

        lm = get_product_license_manager('geotracker')
        _multi_line_text_to_output_labels(box, lm.license_status_text(
            strategy=pkt_module().LicenseCheckStrategy.LAZY))

        box.row().prop(self, 'gt_lic_type', expand=True)

        if self.gt_lic_type == 'ONLINE':
            box = layout.box()
            row = box.split(factor=0.85)
            row.prop(self, 'license_key')
            install_online_op = row.operator(Config.kt_install_license_online_idname)
            install_online_op.license_key = self.license_key
            install_online_op.product = 'geotracker'

        elif self.gt_lic_type == 'OFFLINE':
            self.hardware_id = lm.hardware_id()

            row = layout.split(factor=0.65)
            row.label(text='Get an activated license file at our site:')
            op = row.operator(
                Config.kt_open_manual_install_page_idname,
                icon='URL')
            op.product = 'geotracker'

            box = layout.box()
            row = box.split(factor=0.85)
            row.prop(self, 'hardware_id')
            row.operator(Config.kt_copy_hardware_id_idname)

            row = box.split(factor=0.85)
            row.prop(self, 'gt_lic_path')
            install_offline_op = row.operator(Config.kt_install_license_offline_idname)
            install_offline_op.lic_path = self.gt_lic_path
            install_offline_op.product = 'geotracker'

        elif self.gt_lic_type == 'FLOATING':
            env = pkt_module().LicenseManager.env_server_info()
            if env is not None:
                self.gt_license_server = env[0]
                self.gt_license_server_port = env[1]
                self.gt_license_server_lock = True
            else:
                self.gt_license_server_lock = False

            box = layout.box()
            row = box.split(factor=0.35)
            row.label(text='License Server host/IP')
            if self.gt_license_server_lock and self.gt_license_server_auto:
                row.label(text=self.gt_license_server)
            else:
                row.prop(self, 'gt_license_server', text='')

            row = box.split(factor=0.35)
            row.label(text='License Server port')
            if self.gt_license_server_lock and self.gt_license_server_auto:
                row.label(text=str(self.gt_license_server_port))
            else:
                row.prop(self, 'gt_license_server_port', text='')

            if self.gt_license_server_lock:
                box.prop(self, 'gt_license_server_auto',
                         text='Auto server/port settings')

            floating_install_op = row.operator(Config.kt_floating_connect_idname)
            floating_install_op.license_server = self.gt_license_server
            floating_install_op.license_server_port = self.gt_license_server_port
            floating_install_op.product = 'geotracker'

    def _draw_facebuilder_preferences(self, layout):
        self._draw_fb_license_info(layout)
        self._draw_fb_user_preferences(layout)

    def _draw_geotracker_preferences(self, layout):
        self._draw_gt_license_info(layout)
        self._draw_gt_user_preferences(layout)

    def draw(self, context):
        layout = self.layout

        if self._draw_core_python_problem(layout):
            return
        if self._draw_core_installation_progress(layout):
            return
        if self._draw_pykeentools_problem(layout):
            return
        if not self._draw_core_info(layout):
            return
        self._draw_updater_info(layout)

        if Config.hide_geotracker:
            self._draw_facebuilder_preferences(layout)
            return

        box = layout.box()
        row = box.row(align=True)
        row.prop(self, 'facebuilder_enabled', text='')
        if _expandable_button(row, self, 'facebuilder_expanded'):
            self._draw_facebuilder_preferences(box)

        box = layout.box()
        row = box.row(align=True)
        row.prop(self, 'geotracker_enabled', text='')
        if _expandable_button(row, self, 'geotracker_expanded'):
            self._draw_geotracker_preferences(box)
