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

from typing import Any
import numpy as np

import bpy

from ..utils.kt_logging import KTLogger
from ..addon_config import Config, fb_settings, get_operator, ErrorType
from ..facebuilder_config import FBConfig
from .fbloader import FBLoader
from ..utils import coords
from ..utils.manipulate import (get_vertex_groups,
                                create_vertex_groups)
from ..utils.blendshapes import (restore_facs_blendshapes,
                                 disconnect_blendshapes_action)
from ..blender_independent_packages.pykeentools_loader import module as pkt_module


_log = KTLogger(__name__)


def mesh_update_accepted(headnum: int) -> None:
    _log.output('callbacks.update_mesh_geometry')

    settings = fb_settings()
    head = settings.get_head(headnum)

    if not head or not head.model_changed():
        _log.output('WRONG_HEAD OR MODEL NOT CHANGED')
        return

    head.apply_model_changes()

    if not head.has_no_blendshapes():
        names = [kb.name for kb in head.headobj.data.shape_keys.key_blocks[1:]]
        action = disconnect_blendshapes_action(head.headobj)
        _log.output(f'blendshapes: {names}')
        _update_mesh_now(headnum)

        try:
            counter = restore_facs_blendshapes(head.headobj,
                                               head.model_scale, names)
            _log.output(f'blendshapes_restored: {counter}')
        except pkt_module().UnlicensedException:
            _log.error('UnlicensedException restore_facs_blendshapes')
            warn = get_operator(Config.kt_warning_idname)
            warn('INVOKE_DEFAULT', msg=ErrorType.NoLicense)
        except Exception:
            _log.error('UNKNOWN EXCEPTION restore_facs_blendshapes')

        if action:
            head.headobj.data.shape_keys.animation_data_create()
            head.headobj.data.shape_keys.animation_data.action = action
    else:
        _update_mesh_now(headnum)


def mesh_update_canceled(headnum: int) -> None:
    _log.output('callbacks.mesh_update_canceled')
    settings = fb_settings()
    head = settings.get_head(headnum)
    if not head:
        _log.output('WRONG_HEAD')
        return
    head.discard_model_changes()


def update_mesh_with_dialog(head: Any, context: Any) -> None:
    _log.output('update_mesh_with_dialog')

    headnum = head.get_headnum()
    FBLoader.load_model(headnum)

    _log.output(f'model_changed: {head.model_changed()}')
    if not head.model_changed():
        return

    if head.has_no_blendshapes():
        if _update_mesh_now(headnum):
            head.apply_model_changes()
        else:
            head.discard_model_changes()
    else:
        warn = get_operator(FBConfig.fb_blendshapes_warning_idname)
        warn('INVOKE_DEFAULT', headnum=headnum)


def update_mesh_simple(head: Any, context: Any) -> None:
    headnum = head.get_headnum()
    FBLoader.load_model(headnum)
    _update_mesh_now(headnum)


def _update_mesh_now(headnum: int) -> bool:
    _log.output('callbacks.update_mesh')

    settings = fb_settings()
    head = settings.get_head(headnum)
    if not head:
        _log.output('WRONG_HEAD')
        return False

    if head.should_use_emotions() and \
            head.expression_view != FBConfig.empty_expression_view_name:
        keyframe = head.get_expression_view_keyframe()
        if keyframe <= 0:
            keyframe = None
    else:
        keyframe = None

    _log.output('create_mesh_for_update')

    old_mesh = head.headobj.data
    FBLoader.load_model(headnum)

    fb = FBLoader.get_builder()
    models = [x.name for x in fb.models_list()]
    if (head.model_type in models):
        model_index = models.index(head.model_type)
    else:
        _log.error('MODEL_TYPE_NOT_FOUND (Reset to default)')
        model_index = 0
        head.model_type = models[model_index]

    try:
        fb.select_model(model_index)
    except pkt_module().ModelLoadingException:
        _log.error('CHANGE_MODEL_ERROR: ModelLoadingException')
        error_message = 'Can\'t access face model data\n\n' \
                        'Face model data is locked by another ' \
                        'process or corrupted.\n' \
                        'Please check if there are no other processes\n' \
                        'using face data at the moment.\n' \
                        'If that doesn\'t help, please reinstall the add-on.'
        warn = get_operator(Config.kt_warning_idname)
        warn('INVOKE_DEFAULT', msg=ErrorType.CustomMessage,
             msg_content=error_message)
        return False
    except Exception as err:
        _log.error('CHANGE_MODEL_ERROR: Unknown Exception')
        _log.error(f'info: {type(err)} -- {err}')
        return False

    _log.output(f'MODEL_TYPE: [{model_index}] {head.model_type}')

    # Create new mesh
    mesh = FBLoader.get_builder_mesh(fb, 'FBHead_tmp_mesh',
                                     head.get_masks(),
                                     uv_set=head.tex_uv_shape,
                                     keyframe=keyframe)
    try:
        # Copy old material
        if old_mesh.materials:
            mesh.materials.append(old_mesh.materials[0])
    except Exception:
        pass

    recreate_vertex_groups_flag = FBConfig.recreate_vertex_groups and \
                                  len(old_mesh.vertices) == len(mesh.vertices)
    if recreate_vertex_groups_flag:
        try:
            vg_groups_dict = get_vertex_groups(head.headobj)
        except Exception as err:
            _log.error(f'_update_mesh_now get VG: {str(err)}')
            recreate_vertex_groups_flag = False

    head.headobj.data = mesh
    FBLoader.save_fb_serial_str(headnum)

    # Copy blendshapes and animation
    if old_mesh.shape_keys and len(old_mesh.vertices) == len(mesh.vertices):
        for kb in old_mesh.shape_keys.key_blocks:
            shape = head.headobj.shape_key_add(name=kb.name)
            count = len(kb.data)
            verts = np.empty((count, 3), dtype=np.float32)
            kb.data.foreach_get('co', np.reshape(verts, count * 3))
            shape.data.foreach_set('co', verts.ravel())
            shape.value = kb.value
        if old_mesh.shape_keys.animation_data and old_mesh.shape_keys.animation_data.action:
            mesh.shape_keys.animation_data_create()
            mesh.shape_keys.animation_data.action = old_mesh.shape_keys.animation_data.action

    if recreate_vertex_groups_flag:
        try:
            create_vertex_groups(head.headobj, vg_groups_dict)
        except Exception as err:
            _log.error(f'_update_mesh_now create VG: {str(err)}')

    mesh_name = old_mesh.name
    # Delete old mesh
    bpy.data.meshes.remove(old_mesh, do_unlink=True)
    mesh.name = mesh_name

    if settings.pinmode:
        FBLoader.update_fb_viewport_shaders(wireframe=True,
                                            pins_and_residuals=True)
    return True


def _update_expressions(head: Any, context: Any) -> None:
    settings = fb_settings()
    headnum = head.get_headnum()
    if headnum < 0:
        _log.error('WRONG HEADNUM {}'.format(headnum))
        return
    _log.output('EXPRESSIONS HEADNUM {}'.format(headnum))
    fb = FBLoader.get_builder()
    fb.set_use_emotions(head.should_use_emotions())
    _log.output(f'EXPRESSIONS: {head.should_use_emotions()}')

    coords.update_head_mesh_non_neutral(fb, head)

    FBLoader.save_fb_serial_str(headnum)

    if not settings.pinmode:
        return
    FBLoader.update_fb_viewport_shaders(wireframe=True, pins_and_residuals=True)


def update_use_emotions(head: Any, context: Any) -> None:
    settings = fb_settings()
    if settings.ui_write_mode:
        return
    _update_expressions(head, context)


def _update_head_shape_with_expressions(head: Any, context: Any) -> None:
    settings = fb_settings()
    headnum = head.get_headnum()
    camnum = settings.current_camnum
    if headnum < 0 or camnum < 0:
        _log.error(f'WRONG HEADNUM: {headnum} CAMNUM: {camnum}')
        return
    _log.output(f'EXPRESSIONS HEADNUM: {headnum} {head.should_use_emotions()}')
    fb = FBLoader.get_builder()
    FBLoader.solve(headnum, camnum)

    FBLoader.update_all_camera_positions(headnum)
    FBLoader.save_fb_serial_str(headnum)

    coords.update_head_mesh_non_neutral(fb, head)
    if not settings.pinmode:
        return

    FBLoader.update_fb_viewport_shaders(area=context.area,
                                        wireframe=True, pins_and_residuals=True)


def update_lock_blinking(head: Any, context: Any) -> None:
    settings = fb_settings()
    if settings.ui_write_mode:
        return
    _update_head_shape_with_expressions(head, context)


def update_lock_neck_movement(head: Any, context: Any) -> None:
    settings = fb_settings()
    if settings.ui_write_mode:
        return
    _update_head_shape_with_expressions(head, context)


def update_expression_view(head: Any, context: Any) -> None:
    exp_view = head.expression_view
    if exp_view == FBConfig.empty_expression_view_name:
        head.set_neutral_expression_view()
        return
    if exp_view != FBConfig.neutral_expression_view_name \
            and not head.has_no_blendshapes():
        _log.error('Object has blendshapes so expression view cannot be used')
        head.set_neutral_expression_view()
        error_message = \
            'Expressions can\'t be used with blendshapes\n' \
            '\n' \
            'Unfortunately, using expressions for a model\n' \
            'that has FACS blendshapes is impossible. \n' \
            'Please remove blendshapes before choosing an expression.'
        warn = get_operator(Config.kt_warning_idname)
        warn('INVOKE_DEFAULT', msg=ErrorType.CustomMessage,
             msg_content=error_message)
        return
    _update_expressions(head, context)


def update_wireframe_image(settings: Any, context: Any) -> None:
    FBLoader.update_fb_viewport_shaders(wireframe_colors=True,
                                        wireframe_image=True)


def update_wireframe_func(settings: Any, context: Any) -> None:
    FBLoader.update_fb_viewport_shaders(adaptive_opacity=True,
                                        wireframe_colors=True,
                                        batch_wireframe=True)


def update_pin_sensitivity(settings: Any, context: Any) -> None:
    if settings.pin_size > settings.pin_sensitivity:
        settings.pin_size = settings.pin_sensitivity

    FBLoader.viewport().update_pin_sensitivity()


def update_pin_size(settings: Any, context: Any) -> None:
    if settings.pin_sensitivity < settings.pin_size:
        settings.pin_sensitivity = settings.pin_size
    FBLoader.viewport().update_pin_size()


def update_model_scale(head: Any, context: Any) -> None:
    headnum = head.get_headnum()
    FBLoader.load_model(headnum)

    fb = FBLoader.get_builder()
    fb.set_scale(head.model_scale)

    head.mark_model_changed_by_scale()

    coords.update_head_mesh_non_neutral(fb, head)
    FBLoader.update_all_camera_positions(headnum)
    FBLoader.update_all_camera_focals(headnum)
    FBLoader.save_fb_serial_str(headnum)
    settings = fb_settings()
    if settings.pinmode:
        head.need_update = True


def update_cam_image(camera: Any, context: Any) -> None:
    FBLoader.update_cam_image_size(camera)


def update_head_focal(head: Any, context: Any) -> None:
    _log.output(f'UPDATE_HEAD_FOCAL: {head.focal}')
    for cam in head.cameras:
        cam.focal = head.focal


def update_camera_focal(camera: Any, context: Any) -> None:
    def _check_current_selection_is_not_actual(headnum, camnum):
        settings = fb_settings()
        return headnum < 0 or headnum != settings.current_headnum \
                or camnum != settings.current_camnum

    kid = camera.get_keyframe()
    camera.camobj.data.lens = camera.focal
    _log.output(f'UPDATED_CAMERA_FOCAL: K:{kid} F:{camera.focal}')

    if FBLoader.in_pin_drag():
        return

    headnum, camnum = camera.get_headnum_camnum()
    if _check_current_selection_is_not_actual(headnum, camnum):
        return

    fb = FBLoader.get_builder()
    if fb.is_key_at(kid):
        fb.set_varying_focal_length_estimation()
        fb.set_focal_length_at(
            kid, camera.get_focal_length_in_pixels_coef() * camera.focal)
        FBLoader.save_fb_serial_str(headnum)


def update_background_tone_mapping(camera: Any, context: Any) -> None:
    settings = fb_settings()
    if not settings.pinmode:
        return
    camera.apply_tone_mapping()


def update_shape_rigidity(settings: Any, context: Any) -> None:
    if settings.ui_write_mode:
        return
    fb = FBLoader.get_builder()
    fb.set_shape_rigidity(settings.shape_rigidity)
    if settings.pinmode:
        _update_head_shape_with_expressions(
            settings.get_head(settings.current_headnum), context)


def update_expression_rigidity(settings: Any, context: Any) -> None:
    if settings.ui_write_mode:
        return
    fb = FBLoader.get_builder()
    fb.set_expressions_rigidity(settings.expression_rigidity)
    if settings.pinmode:
        _update_head_shape_with_expressions(
            settings.get_head(settings.current_headnum), context)


def update_blinking_rigidity(settings: Any, context: Any) -> None:
    if settings.ui_write_mode:
        return
    fb = FBLoader.get_builder()
    fb.set_blinking_rigidity(settings.blinking_rigidity)
    if settings.pinmode:
        _update_head_shape_with_expressions(
            settings.get_head(settings.current_headnum), context)


def update_neck_movement_rigidity(settings: Any, context: Any) -> None:
    if settings.ui_write_mode:
        return
    fb = FBLoader.get_builder()
    fb.set_neck_movement_rigidity(settings.neck_movement_rigidity)
    if settings.pinmode:
        _update_head_shape_with_expressions(
            settings.get_head(settings.current_headnum), context)
