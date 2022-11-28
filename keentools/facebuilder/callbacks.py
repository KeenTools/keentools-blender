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
import numpy as np
import bpy
from typing import Any

from ..addon_config import Config, get_operator, ErrorType
from ..facebuilder_config import get_fb_settings, FBConfig
from .fbloader import FBLoader
from ..utils import coords
from ..utils.manipulate import (get_vertex_groups,
                                create_vertex_groups)
from ..utils.blendshapes import (restore_facs_blendshapes,
                                 disconnect_blendshapes_action)
from ..blender_independent_packages.pykeentools_loader import module as pkt_module
from ..preferences.user_preferences import UserPreferences


_logger: Any = logging.getLogger(__name__)


def _log_output(message: str) -> None:
    global _logger
    _logger.debug(message)


def _log_error(message: str) -> None:
    global _logger
    _logger.error(message)


def mesh_update_accepted(headnum):
    _log_output('callbacks.update_mesh_geometry')

    settings = get_fb_settings()
    head = settings.get_head(headnum)

    if not head or not head.model_changed():
        _log_output('WRONG_HEAD OR MODEL NOT CHANGED')
        return

    head.apply_model_changes()

    if not head.has_no_blendshapes():
        names = [kb.name for kb in head.headobj.data.shape_keys.key_blocks[1:]]
        action = disconnect_blendshapes_action(head.headobj)
        _log_output(f'blendshapes: {names}')
        _update_mesh_now(headnum)

        try:
            counter = restore_facs_blendshapes(head.headobj,
                                               head.model_scale, names)
            _log_output(f'blendshapes_restored: {counter}')
        except pkt_module().UnlicensedException:
            _log_error('UnlicensedException restore_facs_blendshapes')
            warn = get_operator(Config.kt_warning_idname)
            warn('INVOKE_DEFAULT', msg=ErrorType.NoLicense)
        except Exception:
            _log_error('UNKNOWN EXCEPTION restore_facs_blendshapes')

        if action:
            head.headobj.data.shape_keys.animation_data_create()
            head.headobj.data.shape_keys.animation_data.action = action
    else:
        _update_mesh_now(headnum)


def mesh_update_canceled(headnum):
    _log_output('callbacks.mesh_update_canceled')
    settings = get_fb_settings()
    head = settings.get_head(headnum)
    if not head:
        _log_output('WRONG_HEAD')
        return
    head.discard_model_changes()


def update_mesh_with_dialog(head, context):
    _log_output('update_mesh_with_dialog')

    headnum = head.get_headnum()
    FBLoader.load_model(headnum)

    _log_output(f'model_changed: {head.model_changed()}')
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


def update_mesh_simple(head, context):
    headnum = head.get_headnum()
    FBLoader.load_model(headnum)
    _update_mesh_now(headnum)


def _update_mesh_now(headnum):
    _log_output('callbacks.update_mesh')

    settings = get_fb_settings()
    head = settings.get_head(headnum)
    if not head:
        _log_output('WRONG_HEAD')
        return

    if head.should_use_emotions() and \
            head.expression_view != FBConfig.empty_expression_view_name:
        keyframe = head.get_expression_view_keyframe()
        if keyframe <= 0:
            keyframe = None
    else:
        keyframe = None

    _log_output('create_mesh_for_update')

    old_mesh = head.headobj.data
    FBLoader.load_model(headnum)

    fb = FBLoader.get_builder()
    models = [x.name for x in fb.models_list()]
    if (head.model_type in models):
        model_index = models.index(head.model_type)
    else:
        _log_error('MODEL_TYPE_NOT_FOUND (Reset to default)')
        model_index = 0
        head.model_type = models[model_index]

    try:
        fb.select_model(model_index)
    except pkt_module().ModelLoadingException:
        _log_error('CHANGE_MODEL_ERROR: ModelLoadingException')
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
        _log_error('CHANGE_MODEL_ERROR: Unknown Exception')
        _log_error(f'info: {type(err)} -- {err}')
        return False

    _log_output(f'MODEL_TYPE: [{model_index}] {head.model_type}')

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
            _log_error(f'_update_mesh_now get VG: {str(err)}')
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

    if settings.pinmode:
        # Update wireframe structures
        vp = FBLoader.viewport()
        wf = vp.wireframer()
        wf.init_geom_data_from_fb(fb, head.headobj,
                                  head.get_keyframe(settings.current_camnum))
        wf.init_edge_indices(fb)
        vp.update_wireframe_colors()

    if recreate_vertex_groups_flag:
        try:
            create_vertex_groups(head.headobj, vg_groups_dict)
        except Exception as err:
            _log_error(f'_update_mesh_now create VG: {str(err)}')

    mesh_name = old_mesh.name
    # Delete old mesh
    bpy.data.meshes.remove(old_mesh, do_unlink=True)
    mesh.name = mesh_name
    return True


def _update_expressions(head, context):
    settings = get_fb_settings()
    headnum = head.get_headnum()
    if headnum < 0:
        _log_error('WRONG HEADNUM {}'.format(headnum))
        return
    _log_output('EXPRESSIONS HEADNUM {}'.format(headnum))
    fb = FBLoader.get_builder()
    fb.set_use_emotions(head.should_use_emotions())
    _log_output(f'EXPRESSIONS: {head.should_use_emotions()}')

    coords.update_head_mesh_non_neutral(fb, head)

    FBLoader.save_fb_serial_str(headnum)

    if not settings.pinmode:
        return
    FBLoader.update_wireframe_shader_only(settings.current_headnum,
                                          settings.current_camnum)


def update_use_emotions(head, context):
    settings = get_fb_settings()
    if settings.ui_write_mode:
        return
    _update_expressions(head, context)


def _update_head_shape_with_expressions(head, context):
    settings = get_fb_settings()
    headnum = head.get_headnum()
    camnum = settings.current_camnum
    if headnum < 0 or camnum < 0:
        _log_error(f'WRONG HEADNUM: {headnum} CAMNUM: {camnum}')
        return
    _log_output(f'EXPRESSIONS HEADNUM: {headnum} {head.should_use_emotions()}')
    fb = FBLoader.get_builder()
    FBLoader.solve(headnum, camnum)

    FBLoader.update_all_camera_positions(headnum)
    FBLoader.save_fb_serial_str(headnum)

    coords.update_head_mesh_non_neutral(fb, head)
    if not settings.pinmode:
        return

    FBLoader.update_viewport_shaders(context.area,
                                     settings.current_headnum,
                                     settings.current_camnum)


def update_lock_blinking(head, context):
    settings = get_fb_settings()
    if settings.ui_write_mode:
        return
    _update_head_shape_with_expressions(head, context)


def update_lock_neck_movement(head, context):
    settings = get_fb_settings()
    if settings.ui_write_mode:
        return
    _update_head_shape_with_expressions(head, context)


def update_expression_view(head, context):
    exp_view = head.expression_view
    if exp_view == FBConfig.empty_expression_view_name:
        head.set_neutral_expression_view()
        return
    if exp_view != FBConfig.neutral_expression_view_name \
            and not head.has_no_blendshapes():
        _log_error('Object has blendshapes so expression view cannot be used')
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


def update_wireframe_image(self, context):
    settings = get_fb_settings()
    vp = FBLoader.viewport()
    wf = vp.wireframer()
    wf.init_colors((settings.wireframe_color,
                    settings.wireframe_special_color,
                    settings.wireframe_midline_color),
                    settings.wireframe_opacity * settings.get_adaptive_opacity())
    wf.init_wireframe_image(FBLoader.get_builder(), settings.show_specials)
    vp.update_wireframe_colors()


def update_wireframe_func(self, context):
    FBLoader.viewport().update_wireframe_colors()


def update_pin_sensitivity(settings, context):
    if settings.pin_size > settings.pin_sensitivity:
        settings.pin_size = settings.pin_sensitivity

    FBLoader.viewport().update_pin_sensitivity()


def update_pin_size(settings, context):
    if settings.pin_sensitivity < settings.pin_size:
        settings.pin_sensitivity = settings.pin_size
    FBLoader.viewport().update_pin_size()


def update_model_scale(head, context):
    headnum = head.get_headnum()
    FBLoader.load_model(headnum)

    fb = FBLoader.get_builder()
    fb.set_scale(head.model_scale)

    head.mark_model_changed_by_scale()

    coords.update_head_mesh_non_neutral(fb, head)
    FBLoader.update_all_camera_positions(headnum)
    FBLoader.update_all_camera_focals(headnum)
    FBLoader.save_fb_serial_str(headnum)
    settings = get_fb_settings()
    if settings.pinmode:
        head.need_update = True


def update_cam_image(camera, context):
    FBLoader.update_cam_image_size(camera)


def update_head_focal(head, context):
    _log_output(f'UPDATE_HEAD_FOCAL: {head.focal}')
    for cam in head.cameras:
        cam.focal = head.focal


def update_camera_focal(camera, context):
    def _check_current_selection_is_not_actual(headnum, camnum):
        settings = get_fb_settings()
        return headnum < 0 or headnum != settings.current_headnum \
                or camnum != settings.current_camnum

    kid = camera.get_keyframe()
    camera.camobj.data.lens = camera.focal
    _log_output(f'UPDATE_CAMERA_FOCAL: K:{kid} F:{camera.focal}')

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


def update_background_tone_mapping(camera, context):
    settings = get_fb_settings()
    if not settings.pinmode:
        return
    camera.apply_tone_mapping()


def update_shape_rigidity(settings, context):
    if settings.ui_write_mode:
        return
    fb = FBLoader.get_builder()
    fb.set_shape_rigidity(settings.shape_rigidity)
    if settings.pinmode:
        _update_head_shape_with_expressions(
            settings.get_head(settings.current_headnum), context)


def update_expression_rigidity(settings, context):
    if settings.ui_write_mode:
        return
    fb = FBLoader.get_builder()
    fb.set_expressions_rigidity(settings.expression_rigidity)
    if settings.pinmode:
        _update_head_shape_with_expressions(
            settings.get_head(settings.current_headnum), context)


def update_blinking_rigidity(settings, context):
    if settings.ui_write_mode:
        return
    fb = FBLoader.get_builder()
    fb.set_blinking_rigidity(settings.blinking_rigidity)
    if settings.pinmode:
        _update_head_shape_with_expressions(
            settings.get_head(settings.current_headnum), context)


def update_neck_movement_rigidity(settings, context):
    if settings.ui_write_mode:
        return
    fb = FBLoader.get_builder()
    fb.set_neck_movement_rigidity(settings.neck_movement_rigidity)
    if settings.pinmode:
        _update_head_shape_with_expressions(
            settings.get_head(settings.current_headnum), context)
