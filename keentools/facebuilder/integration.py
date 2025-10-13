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
from datetime import datetime

from bpy.types import Operator, Object, Material, Image, ShaderNode
from bpy.props import BoolProperty, StringProperty, EnumProperty

from ..utils.kt_logging import KTLogger
from ..addon_config import Config, get_operator, fb_settings, ActionStatus
from ..facebuilder_config import FBConfig
from .ui_strings import buttons
from .fbloader import FBLoader
from ..utils.manipulate import select_object_only
from ..utils.bpy_common import (bpy_create_object,
                                bpy_remove_object,
                                bpy_link_to_scene,
                                bpy_export_fbx,
                                bpy_remove_image,
                                bpy_remove_material)
from ..utils.materials import (new_material,
                               new_shader_node,
                               get_nodes_by_type,
                               get_node_from_input,
                               make_node_shader_matte)


_log = KTLogger(__name__)

_integration_subfolder_name: str = 'keentools_integration'
_cc_headobj_name: str = 'headshot_head'
_cc_headobj_mesh_name: str = 'headshot_mesh'

_CC_REGISTRY_PATH: str = r'SOFTWARE\Reallusion\Character Creator'
_CC4_VERSION_REGISTRY_PATH: str = _CC_REGISTRY_PATH + r'\4.0'
_CC5_VERSION_REGISTRY_PATH: str = _CC_REGISTRY_PATH + r'\5.0'
_CC_REGISTRY_SUBKEY: str = 'Main Program'
_HEADSHOT_FOR_CC4_REGISTRY_PATH: str = r'SOFTWARE\Reallusion\Headshot Plug-in for Character Creator 4'
_HEADSHOT2_FOR_CC4_VERSION_REGISTRY_PATH: str = _HEADSHOT_FOR_CC4_REGISTRY_PATH + r'\2.0'
_HEADSHOT_FOR_CC5_REGISTRY_PATH: str = r'SOFTWARE\Reallusion\Headshot Plug-in for Character Creator 5'
_HEADSHOT2_FOR_CC5_VERSION_REGISTRY_PATH: str = _HEADSHOT_FOR_CC5_REGISTRY_PATH + r'\2.0'
_HEADSHOT_SUBKEY: str = 'Version Code'

_headshot_minimal_supported_version: int = 200


def _get_random_num() -> str:
    return str(uuid4().hex)


def _get_current_date() -> str:
    return datetime.now().strftime('%Y-%m-%d')


def _proper_headshot_version(ver: Any) -> bool:
    try:
        ver_int = int(ver)
        return ver_int >= _headshot_minimal_supported_version
    except Exception as err:
        _log.error(f'_check_headshot_version Exception:\n{str(err)}')
    return False


def _create_material(img: Image=None) -> Material:
    mat = new_material('temp_material')
    mat.node_tree.nodes.clear()
    output_node = new_shader_node(mat, 'ShaderNodeOutputMaterial')
    principled_node = new_shader_node(mat, 'ShaderNodeBsdfPrincipled')
    image_node = new_shader_node(mat, 'ShaderNodeTexImage')

    make_node_shader_matte(principled_node)

    step = 300
    principled_node.location.x += step
    output_node.location.x += 2 * step

    mat.node_tree.links.new(
        principled_node.outputs['BSDF'],
        output_node.inputs['Surface'])

    mat.node_tree.links.new(
        image_node.outputs['Color'],
        principled_node.inputs['Base Color'])

    if img is not None:
        image_node.image = img
    return mat


def _create_head() -> Optional[Object]:
    def _revert_masks(fb, masks: List) -> None:
        for i, m in enumerate(masks):
            fb.set_mask(i, m)

    settings = fb_settings()
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
    obj = bpy_create_object(_cc_headobj_name, mesh)
    bpy_link_to_scene(obj)
    return obj


def _check_hklm_registry_key(reg_path: str) -> bool:
    _log.output(f'_check_hklm_registry_key: {reg_path}')
    try:
        from winreg import (ConnectRegistry, HKEY_LOCAL_MACHINE, OpenKeyEx,
                            QueryValueEx, CloseKey)

        hklm = ConnectRegistry(None, HKEY_LOCAL_MACHINE)
        reg_key = OpenKeyEx(hklm, reg_path)
        _log.output(f'_check_hklm_registry_key_unsafe reg_path: {reg_path}')
        CloseKey(reg_key)
    except Exception as err:
        _log.red(f'_check_hklm_registry_key_unsafe Exception:\n{str(err)}')
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


def _get_export_path() -> Optional[str]:
    try:
        temp_dir = os.path.join(tempfile.gettempdir(), _integration_subfolder_name)
        os.makedirs(temp_dir, exist_ok=True)
        num = _get_random_num()
        date = _get_current_date()
        export_path = os.path.join(temp_dir, f'head_{date}_{num}')
    except Exception as err:
        _log.error(f'_get_export_path Exception:\n{str(err)}')
        return None
    return export_path


def _export_fbx(fbx_export_path: str) -> ActionStatus:
    try:
        bpy_export_fbx('EXEC_DEFAULT',
                       filepath=fbx_export_path,
                       use_selection=True,
                       bake_anim_use_all_actions=False,
                       bake_anim_use_nla_strips=False,
                       add_leaf_bones=False,
                       mesh_smooth_type='FACE',
                       axis_forward='Y',
                       axis_up='Z',
                       bake_space_transform=False,
                       path_mode='COPY',
                       embed_textures=True)
    except Exception as err:
        msg = f'FBX Export problem: {str(err)}'
        _log.error(f'_export_fbx Exception:\n{msg}')
        return ActionStatus(False, msg)

    return ActionStatus(True, 'ok')


def _call_cc(cc_path: str, fbx_export_path: str) -> ActionStatus:
    args = [cc_path, '-headshot', fbx_export_path,
            '-app', 'FaceBuilder for Blender',
            '-ver', Config.addon_version]
    _log.info(f'CC call:\n{" ".join([str(x) for x in args])}')
    try:
        output = subprocess.Popen(args)
        _log.output(f'_call_cc\n{output}')
    except FileNotFoundError as err:
        msg = f'{str(err)}'
        _log.error(f'_call_cc FileNotFoundError: {cc_path}\n{msg}')
        return ActionStatus(False, msg)
    except Exception as err:
        msg = f'{str(err)}'
        _log.error(f'_call_cc Exception:\n{msg}')
        return ActionStatus(False, msg)

    return ActionStatus(True, 'ok')


def _find_base_texture(obj: Object) -> Optional[ShaderNode]:
    if not obj.data.materials:
        return None
    if len(obj.data.materials) == 0:
        return None
    mat = obj.data.materials[0]
    if not mat.use_nodes:
        _log.error('Head material does not use nodes')
        return None
    tex_nodes = get_nodes_by_type(mat.node_tree.nodes, 'TEX_IMAGE')
    if len(tex_nodes) < 1:
        _log.error('No texture node in head material')
        return None
    if len(tex_nodes) == 1:
        return tex_nodes[0]

    output_nodes = get_nodes_by_type(mat.node_tree.nodes, 'OUTPUT_MATERIAL')
    if len(output_nodes) < 1:
        _log.error('Material does not have output node')
        return None
    if len(output_nodes) > 1:
        _log.error('Material has more than one output node')

    node = get_node_from_input(output_nodes[0], 0)
    if node is None:
        _log.error('Problem with Output node in material')
        return None

    node_list = [node]
    _log.magenta('start material tree walking')
    base_color_input_index = 0
    while len(node_list) > 0:
        node = node_list.pop(0)
        _log.output(f'node: {node.type} {node}')
        if node.type == 'TEX_IMAGE':
            return node
        elif node.type == 'BSDF_PRINCIPLED':
            node = get_node_from_input(node, base_color_input_index)
            node_list.insert(0, node)
        else:
            _log.output('check node inputs')
            for x in range(len(node.inputs)):
                input = node.inputs[x]
                color_data_flag = input.type in ['SHADER', 'RGBA']
                _log.output(f'input: {"+" if color_data_flag else "-"} '
                            f'{input.name} {input.type}')
                if color_data_flag:
                    node = get_node_from_input(node, x)
                    if node is not None:
                        node_list.append(node)
        _log.output(f'node_list:\n{node_list}')
    return None


class CheckCCStatus:
    def __init__(self, mode: str = 'AUTO'):
        self.cc5_path: Optional[str] = None
        self.cc4_path: Optional[str] = None
        self.headshot_for_cc5_version: Optional[str] = None
        self.headshot_for_cc4_version: Optional[str] = None
        self.set_mode(mode)

    def set_mode(self, mode: str):
        if mode == 'CC5':
            self.ignore_cc5 = False
            self.ignore_cc4 = True
        elif mode == 'CC4':
            self.ignore_cc5 = True
            self.ignore_cc4 = False
        else:
            self.ignore_cc5 = False
            self.ignore_cc4 = False

    def check_cc5_installed(self) -> bool:
        if self.ignore_cc5:
            return False
        try:
            cc_path = _get_hklm_registry_value_unsafe(
                _CC5_VERSION_REGISTRY_PATH, _CC_REGISTRY_SUBKEY)
            _log.info(f'Character Creator 5 found:\n{cc_path}')
            self.cc5_path = cc_path
            return True
        except Exception as err:
            _log.info('No Character Creator 5 found')
            _log.output(f'key: {_CC5_VERSION_REGISTRY_PATH}\n'
                        f'subkey: {_CC_REGISTRY_SUBKEY}\n')
            _log.output(f'CC5 Exception: {err}')
            return False

    def check_cc4_installed(self) -> bool:
        if self.ignore_cc4:
            return False
        try:
            cc_path = _get_hklm_registry_value_unsafe(
                _CC4_VERSION_REGISTRY_PATH, _CC_REGISTRY_SUBKEY)
            _log.info(f'\nCharacter Creator 4 found:\n{cc_path}')
            self.cc4_path = cc_path
            return True
        except Exception as err:
            _log.info('No Character Creator 4 found')
            _log.output(f'key: {_CC5_VERSION_REGISTRY_PATH}\n'
                        f'subkey: {_CC_REGISTRY_SUBKEY}\n')
            _log.output(f'CC4 Exception: {err}')
            return False

    def check_cc4_headshot(self) -> bool:
        if self.ignore_cc4:
            return False

        if not _check_hklm_registry_key(_HEADSHOT_FOR_CC4_REGISTRY_PATH):
            return False
        try:
            headshot_version = _get_hklm_registry_value_unsafe(
                _HEADSHOT2_FOR_CC4_VERSION_REGISTRY_PATH, _HEADSHOT_SUBKEY)
            if not _proper_headshot_version(headshot_version):
                msg = f'You have Headshot [{headshot_version}] for CC4. ' \
                      f'Need Headshot 2 or higher'
                _log.error(f'{msg}')
                return False
            self.headshot_for_cc4_version = headshot_version
            return True
        except Exception as err:
            msg = 'Failed to identify Headshot version'
            _log.output(f'key: {_HEADSHOT2_FOR_CC4_VERSION_REGISTRY_PATH}\n'
                        f'subkey: {_HEADSHOT_SUBKEY}\n')
            _log.error(f'{msg}\n{str(err)}')
            return False

    def check_cc5_headshot(self) -> bool:
        if self.ignore_cc5:
            return False

        if not _check_hklm_registry_key(_HEADSHOT_FOR_CC5_REGISTRY_PATH):
            return False
        try:
            headshot_version = _get_hklm_registry_value_unsafe(
                _HEADSHOT2_FOR_CC5_VERSION_REGISTRY_PATH, _HEADSHOT_SUBKEY)
            if not _proper_headshot_version(headshot_version):
                msg = f'You have Headshot [{headshot_version}] for CC5. ' \
                      f'Need Headshot 2 or higher'
                _log.error(f'{msg}')
                return False
            self.headshot_for_cc5_version = headshot_version
            return True
        except Exception as err:
            msg = 'Failed to identify Headshot version'
            _log.output(f'key: {_HEADSHOT2_FOR_CC4_VERSION_REGISTRY_PATH}\n'
                        f'subkey: {_HEADSHOT_SUBKEY}\n')
            _log.error(f'{msg}\n{str(err)}')
            return False

    def cc5_found(self) -> bool:
        if self.ignore_cc5:
            return False
        return not self.cc5_path is None

    def cc4_found(self) -> bool:
        if self.ignore_cc4:
            return False
        return not self.cc4_path is None

    def cc_found(self) -> bool:
        return self.cc5_found() or self.cc4_found()

    def get_cc5_path(self) -> Optional[str]:
        if self.ignore_cc5:
            return None
        if self.cc5_path and self.headshot_for_cc5_version:
            return self.cc5_path
        return None

    def get_cc4_path(self) -> Optional[str]:
        if self.ignore_cc4:
            return None
        if self.cc4_path and self.headshot_for_cc4_version:
            return self.cc4_path
        return None

    def get_cc_path(self) -> Optional[str]:
        cc5_path = self.get_cc5_path()
        if cc5_path is not None:
            return cc5_path
        return self.get_cc4_path()

    def multiple_version_available(self) -> bool:
        return self.get_cc5_path() is not None and self.get_cc4_path() is not None


class FB_OT_ExportToCCExec(Operator):
    bl_idname = FBConfig.fb_export_to_cc_exec_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    done: BoolProperty(default=False)

    def cancel(self, context):
        _log.output(f'{self.__class__.__name__} cancel')
        self.done = True

    def draw(self, context):
        layout = self.layout
        if self.done:
            layout.label(text='Operation has been done')
            return

        col = layout.column(align=True)
        col.scale_y = Config.text_scale_y
        col.label(text='Do you want to continue without head texture?')

    def invoke(self, context, event):
        _log.output(f'{self.__class__.__name__} execute')
        self.done = False

        settings = fb_settings()
        head = settings.get_current_head()
        if not head or not head.headobj:
            msg = 'Head not found'
            self.report({'ERROR'}, msg)
            _log.error(f'{msg}')
            return {'CANCELLED'}

        tex_node = _find_base_texture(head.headobj)
        if tex_node is None:
            return context.window_manager.invoke_props_dialog(self, width=400)
        return self.execute(context)

    def execute(self, context):
        self.done = True
        op = get_operator(FBConfig.fb_export_to_cc_idname)
        op('INVOKE_DEFAULT')
        return {'FINISHED'}


_check_cc_status: Optional[CheckCCStatus] = None
def _get_check_cc_status() -> Optional[CheckCCStatus]:
    global _check_cc_status
    return _check_cc_status


def _set_check_cc_status(value: Optional[CheckCCStatus]) -> None:
    global _check_cc_status
    _check_cc_status = value


class FB_OT_ExportToCC(Operator):
    bl_idname = FBConfig.fb_export_to_cc_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description

    done: BoolProperty(default=False)
    version: EnumProperty(name='Choose Version', items=[
        ('CC5', 'Character Creator 5',
         'Execute Character Creator 5', 0),
        ('CC4', 'Character Creator 4',
         'Execute Character Creator 4', 1),
    ], default='CC5')

    test_mode: BoolProperty(default=False)

    def cancel(self, context):
        _log.output(f'{self.__class__.__name__} cancel')
        self.done = True

    def draw(self, context):
        layout = self.layout
        if self.done:
            layout.label(text='Operation has been done')
            return

        col = layout.column(align=True)
        col.prop(self, 'version')

    def invoke(self, context, event):
        _log.output(f'{self.__class__.__name__} execute')
        self.done = False

        if not FBLoader.reload_current_model():
            msg = 'Cannot reload current model before start'
            self.report({'ERROR'}, msg)
            _log.error(f'{msg}')
            return {'CANCELLED'}

        if not _check_hklm_registry_key(_CC_REGISTRY_PATH):
            msg = 'Character Creator 4 or 5 not found'
            self.report({'ERROR'}, msg)
            _log.error(f'{msg}')
            _log.output(f'key: {_CC_REGISTRY_PATH}\n')

            if not self.test_mode:
                return {'CANCELLED'}

        check_status = CheckCCStatus()
        _set_check_cc_status(check_status)

        check_status.check_cc5_installed()
        check_status.check_cc4_installed()
        if not check_status.cc_found():
            msg = 'Need Character Creator 4 or higher'
            self.report({'ERROR'}, msg)

            if not self.test_mode:
                return {'CANCELLED'}

        check_status.check_cc5_headshot()
        check_status.check_cc4_headshot()
        if check_status.get_cc_path() is None:
            msg = 'Need Character Creator 4 or higher with Headshot 2'
            self.report({'ERROR'}, msg)

            if not self.test_mode:
                return {'CANCELLED'}

        if check_status.multiple_version_available():
            return context.window_manager.invoke_props_dialog(self, width=400)

        return self.execute(context)

    def execute(self, context):
        self.done = True

        export_path = _get_export_path()
        _log.info(f'Export path: {export_path}')
        if export_path is None:
            msg = 'Cannot create export path'
            self.report({'ERROR'}, msg)
            _log.error(f'{msg}')
            return {'CANCELLED'}

        settings = fb_settings()
        head = settings.get_current_head()
        if not head or not head.headobj:
            msg = 'Head not found'
            self.report({'ERROR'}, msg)
            _log.error(f'{msg}')
            return {'CANCELLED'}

        head_obj = _create_head()
        if head_obj is None:
            msg = 'Cannot create head-mesh for export'
            self.report({'ERROR'}, msg)
            _log.error(msg)
            return {'CANCELLED'}

        select_object_only(head_obj)

        img = None
        duplicate_img = None
        tex_node = _find_base_texture(head.headobj)
        if tex_node is not None:
            img = tex_node.image
            if img and img.packed_file:
                duplicate_img = img.copy()
                duplicate_img.filepath = f'{export_path}.png'
                duplicate_img.save()
        mat = _create_material(duplicate_img if duplicate_img is not None
                               else img)

        head_obj.data.materials.clear()
        head_obj.data.materials.append(mat)

        act_status = _export_fbx(f'{export_path}.fbx')
        if not act_status.success:
            bpy_remove_object(head_obj)
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}

        bpy_remove_image(duplicate_img)
        bpy_remove_material(mat)
        bpy_remove_object(head_obj)

        check_status = _get_check_cc_status()
        if check_status.multiple_version_available():
            check_status.set_mode(self.version)
        _log.red(f'SELECTED VERSION: {self.version}')
        act_status = _call_cc(check_status.get_cc_path(), f'{export_path}.fbx')
        if not act_status.success:
            self.report({'ERROR'}, act_status.error_message)
            return {'CANCELLED'}
        self.report({'INFO'}, 'Launching Character Creator. Please wait...')
        return {'FINISHED'}
