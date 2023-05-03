# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2023  KeenTools

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

from typing import Optional, List, Any
import subprocess
import os
import tempfile
from uuid import uuid4

import bpy
from bpy.types import Operator, Object

from ..utils.kt_logging import KTLogger
from ..addon_config import Config, ActionStatus
from ..facebuilder_config import FBConfig, get_fb_settings
from .ui_strings import buttons
from .fbloader import FBLoader
from ..utils.manipulate import select_object_only
from ..utils.bpy_common import bpy_remove_object


_log = KTLogger(__name__)
_integration_subfolder_name: str = 'keentools_integration'
_cc_headobj_name: str = 'headshot_head'
_cc_headobj_mesh_name: str = 'headshot_mesh'
_cc_registry_path: str = r'SOFTWARE\Reallusion\Character Creator'
_cc_versioned_registry_path: str = _cc_registry_path + r'\4.0'
_cc_registry_subkey: str = 'Main Program'
_headshot_registry_path: str = r'SOFTWARE\Reallusion\Headshot Plug-in for Character Creator 4'
_headshot_versioned_registry_path: str = _headshot_registry_path + r'\2.0'
_headshot_subkey: str = 'Version Code'
_headshot_minimal_supported_version: int = 200


def _get_random_num() -> str:
    return str(uuid4().hex)


def _proper_headshot_version(ver: Any) -> bool:
    try:
        ver_int = int(ver)
        return ver_int >= _headshot_minimal_supported_version
    except Exception as err:
        _log.error(f'_check_headshot_version Exception:\n{str(err)}')
    return False


def _create_head() -> Optional[Object]:
    def _revert_masks(fb, masks: List) -> None:
        for i, m in enumerate(masks):
            fb.set_mask(i, m)

    settings = get_fb_settings()
    settings.check_heads_and_cams()
    _log.output(f'_create_head current_headnum: {settings.current_headnum}')
    head = settings.get_current_head()
    if not head or not head.headobj:
        return None
    fb = FBLoader.get_builder()
    masks = head.get_masks()
    mesh = FBLoader.get_builder_mesh(fb, _cc_headobj_mesh_name,
                                     [True] * len(masks),
                                     uv_set=head.tex_uv_shape,
                                     keyframe=None)
    _revert_masks(fb, masks)
    obj = bpy.data.objects.new(_cc_headobj_name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def _check_hklm_registry_key(reg_path: str) -> bool:
    from winreg import (ConnectRegistry, HKEY_LOCAL_MACHINE, OpenKeyEx,
                        QueryValueEx, CloseKey)
    try:
        hklm = ConnectRegistry(None, HKEY_LOCAL_MACHINE)
        reg_key = OpenKeyEx(hklm, reg_path)
        _log.output(f'_check_hklm_registry_key_unsafe reg_path: {reg_path}')
        CloseKey(reg_key)
    except Exception as err:
        _log.error(f'_check_hklm_registry_key_unsafe Exception: {str(err)}')
        return False
    return True


def _get_hklm_registry_value_unsafe(reg_path: str, sub_key: str) -> str:
    from winreg import (ConnectRegistry, HKEY_LOCAL_MACHINE, OpenKeyEx,
                        QueryValueEx, CloseKey)
    hklm = ConnectRegistry(None, HKEY_LOCAL_MACHINE)
    reg_key = OpenKeyEx(hklm, reg_path)
    _log.output(f'_get_hklm_registry_value_unsafe reg_path: {reg_path}')
    value, regtype = QueryValueEx(reg_key, sub_key)
    CloseKey(reg_key)
    return value


def _call_cc(cc_path: str) -> ActionStatus:
    head_obj = _create_head()
    if head_obj is None:
        msg = 'FB cannot find head and head-mesh'
        _log.error(msg)
        return ActionStatus(False, msg)

    select_object_only(head_obj)

    temp_dir = os.path.join(tempfile.gettempdir(), _integration_subfolder_name)
    os.makedirs(temp_dir, exist_ok=True)

    num = _get_random_num()
    modelpath = os.path.join(temp_dir, f'head_{num}.fbx')

    try:
        bpy.ops.export_scene.fbx('EXEC_DEFAULT',
                                 filepath=modelpath,
                                 use_selection=True,
                                 bake_anim_use_all_actions=False,
                                 bake_anim_use_nla_strips=False,
                                 add_leaf_bones=False,
                                 mesh_smooth_type='FACE',
                                 axis_forward='Y',
                                 axis_up='Z',
                                 bake_space_transform=False)

        output = subprocess.Popen([cc_path, '-headshot', modelpath,
                                   '-app', 'FaceBuilder for Blender',
                                   '-ver', Config.addon_version])
        _log.output(f'_call_cc\n{output}')
    except FileNotFoundError as err:
        msg = f'{str(err)}'
        _log.error(f'_call_cc FileNotFoundError: {cc_path}\n{msg}')
        return ActionStatus(False, msg)
    except Exception as err:
        msg = f'{str(err)}'
        _log.error(f'_call_cc Exception:\n{msg}')
        return ActionStatus(False, msg)
    finally:
        bpy_remove_object(head_obj)
    return ActionStatus(True, 'ok')


class FB_OT_ExportToCC(Operator):
    bl_idname = FBConfig.fb_export_to_cc_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER'}

    def execute(self, context):
        if not _check_hklm_registry_key(_cc_registry_path):
            msg = 'Cannot find Character Creator 4 on this computer'
            self.report({'ERROR'}, msg)
            _log.error(f'{msg}')
            _log.output(f'key: {_cc_registry_path}\n')
            return {'CANCELLED'}

        try:
            cc_path = _get_hklm_registry_value_unsafe(
                _cc_versioned_registry_path, _cc_registry_subkey)
        except Exception as err:
            msg = 'Installed incompatible version of Character Creator'
            self.report({'ERROR'}, msg)
            _log.error(f'{msg}\n{str(err)}')
            _log.output(f'key: {_cc_versioned_registry_path}\n'
                        f'subkey: {_cc_registry_subkey}\n')
            return {'CANCELLED'}

        _log.output(f'Character Creator path: {cc_path}')

        if not _check_hklm_registry_key(_headshot_registry_path):
            msg = 'Cannot find Headshot add-on on this computer'
            self.report({'ERROR'}, msg)
            _log.error(f'{msg}')
            _log.output(f'key: {_headshot_registry_path}\n')
            return {'CANCELLED'}

        try:
            headshot_version = _get_hklm_registry_value_unsafe(
                _headshot_versioned_registry_path, _headshot_subkey)
        except Exception as err:
            msg = 'Headshot plugin has incompatible version'
            self.report({'ERROR'}, msg)
            _log.error(f'{msg}\n{str(err)}')
            _log.output(f'key: {_headshot_versioned_registry_path}\n'
                        f'subkey: {_headshot_subkey}\n')
            return {'CANCELLED'}

        _log.output(f'Headshot version: {headshot_version} '
                    f'[{type(headshot_version)}]')

        if not _proper_headshot_version(headshot_version):
            msg = f'Incompatible Headshot version [{headshot_version}]'
            self.report({'ERROR'}, msg)
            _log.error(f'{msg}')
            return {'CANCELLED'}

        act_status = _call_cc(cc_path)
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        self.report({'INFO'}, 'Success!')
        return {'FINISHED'}
