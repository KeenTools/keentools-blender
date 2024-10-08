# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2019-2022  KeenTools

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

import platform
from urllib.parse import urlencode

from bpy.types import Operator
from bpy.props import StringProperty, IntProperty, BoolProperty

from .kt_logging import KTLogger
from .version import BVersion
from ..addon_config import (Config,
                            get_settings,
                            get_operator,
                            show_user_preferences,
                            show_tool_preferences,
                            product_name,
                            ProductType,
                            common_loader,
                            license_checker_module)
from .localview import check_context_localview
from .viewport_state import force_show_ui_overlays
from ..utils.ui_redraw import (force_ui_redraw,
                               find_modules_by_name_starting_with,
                               filter_module_list_by_name_starting_with,
                               collapse_all_modules,
                               mark_old_modules)
from .bpy_common import (bpy_localview,
                         bpy_background_mode,
                         bpy_show_addon_preferences,
                         bpy_url_open,
                         bpy_window_manager,
                         bpy_ops)
from ..ui_strings import buttons
from ..common.actor import KT_OT_Actor
from ..preferences.hotkeys import viewport_native_pan_operator_activate


_log = KTLogger(__name__)


class KT_OT_AddonSettings(Operator):
    bl_idname = Config.kt_addon_settings_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER'}

    show: StringProperty(default='all')

    def draw(self, context):
        pass

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute show={self.show}')
        show_user_preferences(facebuilder=False, geotracker=False,
                              facetracker=False)
        if self.show == 'facebuilder':
            show_tool_preferences(facebuilder=True, geotracker=False,
                                  facetracker=False)
        elif self.show == 'geotracker':
            show_tool_preferences(facebuilder=False, geotracker=True,
                                  facetracker=False)
        elif self.show == 'facetracker':
            show_tool_preferences(facebuilder=False, geotracker=False,
                                  facetracker=True)
        elif self.show == 'all':
            show_tool_preferences(facebuilder=True, geotracker=True,
                                  facetracker=True)
        elif self.show == 'none':
            show_tool_preferences(facebuilder=False, geotracker=False,
                                  facetracker=False)
        bpy_show_addon_preferences()
        _log.output(f'{self.__class__.__name__} end >>>')
        return {'FINISHED'}


class KT_OT_OpenURLBase:
    bl_options = {'REGISTER', 'INTERNAL'}

    url: StringProperty(name='URL', default='')

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        bpy_url_open(url=self.url)
        _log.output(f'{self.__class__.__name__} end >>>')
        return {'FINISHED'}


class KT_OT_OpenURL(KT_OT_OpenURLBase, Operator):
    bl_idname = Config.kt_open_url_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'INTERNAL'}

    url: StringProperty(name='URL', default='')


class KT_OT_AddonSearch(Operator):
    bl_idname = Config.kt_addon_search_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER'}

    search: StringProperty(default='KeenTools')

    def draw(self, context):
        pass

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        bpy_window_manager().addon_search = self.search
        bpy_ops().screen.userpref_show()
        mods = find_modules_by_name_starting_with(self.search)
        if len(mods) > 1:
            collapse_all_modules(mods)
            keentools_fb_mods = filter_module_list_by_name_starting_with(
                mods, 'KeenTools FaceBuilder')
            mark_old_modules(keentools_fb_mods, {'category': 'Add Mesh'})
        force_ui_redraw(area_type='PREFERENCES')
        _log.output(f'{self.__class__.__name__} end >>>')
        return {'FINISHED'}


class KT_OT_ExitLocalview(Operator):
    bl_idname = Config.kt_exit_localview_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        if not check_context_localview(context):
            self.report({'ERROR', 'Cannot set proper context for operator'})
            return {'CANCELLED'}
        bpy_localview()
        force_show_ui_overlays(context.area)
        _log.output(f'{self.__class__.__name__} end >>>')
        return {'FINISHED'}


def get_machine_specs() -> str:
    txt = f'{platform.machine()} {platform.processor()}; {BVersion.gpu_backend}; '
    gpu_txt = ''
    try:
        import gpu
        gpu_txt = f'{gpu.platform.renderer_get()}'
    except Exception as err:
        _log.error(f'get_machine_specs error:\n{str(err)}')
    return txt + gpu_txt


def _fb_feedback_url() -> str:
    params = {
        'hl': 'en',
        'usp': 'pp_url',
        'entry.783336314': f'{platform.platform()}',
        'entry.1510351504': f'{get_machine_specs()}',
        'entry.1095779847': f'{BVersion.version_string}',
        'entry.1252663858': f'{Config.addon_name} {Config.addon_version}'
    }
    url = (f'https://docs.google.com/forms/d/e/'
           f'1FAIpQLSftXdcCX7YjPPBkvwGihHBXECLVswM4KuNbxOQGR2bOBPtI6w/'
           f'viewform?{urlencode(params)}')
    return url


def _gt_feedback_url() -> str:
    params = {
        'hl': 'en',
        'usp': 'pp_url',
        'entry.783336314': f'{platform.platform()}',
        'entry.1510351504': f'{get_machine_specs()}',
        'entry.1095779847': f'{BVersion.version_string}',
        'entry.1252663858': f'{Config.addon_name} {Config.addon_version}'
    }
    url = (f'https://docs.google.com/forms/d/e/'
           f'1FAIpQLSf7Up-IPtqqSVjEy_BicDHE-1p31SynJsUUXHbBiMOpqpJ_2Q/'
           f'viewform?{urlencode(params)}')
    return url


def _ft_feedback_url() -> str:
    params = {
        'hl': 'en',
        'usp': 'pp_url',
        'entry.783336314': f'{platform.platform()}',
        'entry.1510351504': f'{get_machine_specs()}',
        'entry.1095779847': f'{BVersion.version_string}',
        'entry.1252663858': f'{Config.addon_name} {Config.addon_version}'
    }
    url = (f'https://docs.google.com/forms/d/e/'
           f'1FAIpQLSdfphsWt-dVKBt8Ysq0fLBb9qarZ0QeNKThZjhhbqCmhp9dHw/'
           f'viewform?{urlencode(params)}')
    return url


class KT_OT_ShareFeedback(Operator):
    bl_idname = Config.kt_share_feedback_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER'}

    product: IntProperty(default=ProductType.UNDEFINED)

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute [{product_name(self.product)}]')

        if self.product == ProductType.FACEBUILDER:
            url = _fb_feedback_url()
        elif self.product == ProductType.GEOTRACKER:
            url = _gt_feedback_url()
        elif self.product == ProductType.FACETRACKER:
            url = _ft_feedback_url()
        else:
            self.report({'ERROR', 'Wrong Product ID'})
            url = 'https://keentools.io'

        _log.output(f'\n{url}')
        bpy_url_open(url)
        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


def _fb_report_bug_url() -> str:
    params = {
        'hl': 'en',
        'usp': 'pp_url',
        'entry.829556545': f'{platform.platform()}',
        'entry.1380547335': f'{get_machine_specs()}',
        'entry.1878956515': f'{BVersion.version_string}',
        'entry.369889899': f'{Config.addon_name} {Config.addon_version}'
    }
    url = (f'https://docs.google.com/forms/d/e/'
           f'1FAIpQLSc8KtSmpnk5P5zCaE64y0fUSYfzOQRrJk3jWfAlO2hyCMPS7g/'
           f'viewform?{urlencode(params)}')
    return url


def _gt_report_bug_url() -> str:
    params = {
        'hl': 'en',
        'usp': 'pp_url',
        'entry.829556545': f'{platform.platform()}',
        'entry.1778135883': f'{get_machine_specs()}',
        'entry.1878956515': f'{BVersion.version_string}',
        'entry.369889899': f'{Config.addon_name} {Config.addon_version}'
    }
    url = (f'https://docs.google.com/forms/d/e/'
           f'1FAIpQLScoRDBhL9prv-vVKiLwyqZduQCEC0VlxtOW3lEmO-d77p8kcQ/'
           f'viewform?{urlencode(params)}')
    return url


def _ft_report_bug_url() -> str:
    params = {
        'hl': 'en',
        'usp': 'pp_url',
        'entry.829556545': f'{platform.platform()}',
        'entry.1075934335': f'{get_machine_specs()}',
        'entry.1878956515': f'{BVersion.version_string}',
        'entry.369889899': f'{Config.addon_name} {Config.addon_version}'
    }
    url = (f'https://docs.google.com/forms/d/e/'
           f'1FAIpQLSfVRO7_ptdnHJEk4hgdjPIb_PAP1Qa7luw3ZBDpEslB8TzE9A/'
           f'viewform?{urlencode(params)}')
    return url


class KT_OT_ReportBug(Operator):
    bl_idname = Config.kt_report_bug_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER'}

    product: IntProperty(default=ProductType.UNDEFINED)

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute [{product_name(self.product)}]')

        if self.product == ProductType.FACEBUILDER:
            url = _fb_report_bug_url()
        elif self.product == ProductType.GEOTRACKER:
            url = _gt_report_bug_url()
        elif self.product == ProductType.FACETRACKER:
            url = _ft_report_bug_url()
        else:
            self.report({'ERROR', 'Wrong Product ID'})
            url = 'https://link.keentools.io/new-support-request'

        _log.output(f'\n{url}')
        bpy_url_open(url)
        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class KT_OT_UpgradeProduct(Operator):
    bl_idname = Config.kt_upgrade_product_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER'}

    product: IntProperty(default=ProductType.UNDEFINED)
    source: StringProperty(default='none')

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute '
                   f'[{product_name(self.product)}] source={self.source}')
        url = license_checker_module().get_upgrade_url(product=self.product,
                                                       source=self.source)
        _log.output(f'\n{url}')
        bpy_url_open(url)
        _log.output(f'{self.__class__.__name__} execute end >>>')
        return {'FINISHED'}


class KT_OT_InterruptModal(Operator):
    bl_idname = Config.kt_interrupt_modal_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'INTERNAL'}

    product: IntProperty(default=ProductType.UNDEFINED)
    bus_id: IntProperty(default=-1)

    def init_bus(self) -> None:
        message_bus = common_loader().message_bus()
        self.bus_id = message_bus.register_item(
            Config.kt_interrupt_modal_idname, product=self.product)
        _log.output(f'{self.__class__.__name__} bus_id={self.bus_id}')

    def release_bus(self) -> None:
        message_bus = common_loader().message_bus()
        item = message_bus.remove_by_id(self.bus_id)
        _log.output(f'release_bus: {self.bus_id} -> {item}')

    def cancel(self, context):
        _log.magenta(f'{self.__class__.__name__} cancel ***')
        self.release_bus()

    def execute(self, context):
        _log.magenta(f'{self.__class__.__name__} execute ***')
        self.release_bus()
        return {'FINISHED'}

    def invoke(self, context, event):
        _log.green(f'{self.__class__.__name__} invoke')
        if self.product == ProductType.UNDEFINED:
            _log.error(f'{self.__class__.__name__}: '
                       f'Wrong product type {self.product}')
            return {'CANCELLED'}

        settings = get_settings(self.product)
        settings.user_interrupts = False

        if not bpy_background_mode():
            self.init_bus()
            context.window_manager.modal_handler_add(self)
            _log.output(f'{product_name(self.product)} INTERRUPTOR START')
        else:
            _log.info(f'{product_name(self.product)} Interruptor '
                      f'skipped by background mode')
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        message_bus = common_loader().message_bus()
        if not message_bus.check_id(self.bus_id):
            _log.red(f'{product_name(self.product)} Interruptor '
                     f'has been stopped by message bus')
            _log.output(f'{self.__class__.__name__} modal end >>>')
            return {'FINISHED'}

        settings = get_settings(self.product)

        if settings.user_interrupts:
            _log.red(f'{product_name(self.product)} Interruptor '
                        f'has been stopped by value')
            self.release_bus()
            _log.output(f'{self.__class__.__name__} modal end >>>')
            return {'FINISHED'}

        if event.type == 'ESC' and event.value == 'PRESS':
            settings.user_interrupts = True
            self.release_bus()
            _log.red(f'Exit {product_name(self.product)} Interruptor by ESC')
            _log.output(f'{self.__class__.__name__} modal end >>>')
            return {'FINISHED'}

        return {'PASS_THROUGH'}


class KT_OT_MoveWrapper(Operator):
    bl_idname = Config.kt_move_wrapper_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'INTERNAL'}

    use_cursor_init: BoolProperty(name='Use Mouse Position', default=True)

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute '
                   f'use_cursor_init={self.use_cursor_init}')

        op = get_operator('view3d.move')
        return op('EXEC_DEFAULT', use_cursor_init=self.use_cursor_init)

    def invoke(self, context, event):
        _log.green(f'{self.__class__.__name__} invoke '
                   f'use_cursor_init={self.use_cursor_init}')

        work_area = common_loader().get_current_viewport_area()
        if work_area != context.area:
            return {'PASS_THROUGH'}

        op = get_operator('view3d.move')
        return op('INVOKE_DEFAULT', use_cursor_init=self.use_cursor_init)


class KT_OT_PanDetector(Operator):
    bl_idname = Config.kt_pan_detector_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        return {'FINISHED'}

    def invoke(self, context, event):
        _log.green(f'{self.__class__.__name__} invoke')

        work_area = common_loader().get_current_viewport_area()
        if viewport_native_pan_operator_activate(work_area == context.area):
            return {'CANCELLED'}
        return {'PASS_THROUGH'}


CLASSES_TO_REGISTER = (KT_OT_AddonSettings,
                       KT_OT_OpenURL,
                       KT_OT_AddonSearch,
                       KT_OT_ExitLocalview,
                       KT_OT_ShareFeedback,
                       KT_OT_ReportBug,
                       KT_OT_UpgradeProduct,
                       KT_OT_Actor,
                       KT_OT_InterruptModal,
                       KT_OT_MoveWrapper,
                       KT_OT_PanDetector)
