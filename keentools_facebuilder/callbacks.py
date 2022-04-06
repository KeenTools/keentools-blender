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

from .config import get_main_settings, get_operator, Config, ErrorType
from .fbloader import FBLoader
from .utils import coords
from .utils.manipulate import (get_current_headnum,
                               get_vertex_groups,
                               create_vertex_groups)
from .utils.blendshapes import (restore_facs_blendshapes,
                                disconnect_blendshapes_action)
from .blender_independent_packages.pykeentools_loader import module as pkt_module
from .preferences.user_preferences import UserPreferences


def mesh_update_accepted(headnum):
    logger = logging.getLogger(__name__)
    logger.debug('callbacks.update_mesh_geometry')

    settings = get_main_settings()
    head = settings.get_head(headnum)

    if not head or not head.model_changed():
        logger.debug('WRONG_HEAD OR MODEL NOT CHANGED')
        return

    head.apply_model_changes()

    if not head.has_no_blendshapes():
        names = [kb.name for kb in head.headobj.data.shape_keys.key_blocks[1:]]
        action = disconnect_blendshapes_action(head.headobj)
        logger.debug('blendshapes: {}'.format(names))
        _update_mesh_now(headnum)

        try:
            counter = restore_facs_blendshapes(head.headobj,
                                               head.model_scale, names)
            logger.debug('blendshapes_restored: {}'.format(counter))
        except pkt_module().UnlicensedException:
            logger.error('UnlicensedException restore_facs_blendshapes')
            warn = get_operator(Config.fb_warning_idname)
            warn('INVOKE_DEFAULT', msg=ErrorType.NoLicense)
        except Exception:
            logger.error('UNKNOWN EXCEPTION restore_facs_blendshapes')

        if action:
            head.headobj.data.shape_keys.animation_data_create()
            head.headobj.data.shape_keys.animation_data.action = action
    else:
        _update_mesh_now(headnum)


def mesh_update_canceled(headnum):
    logger = logging.getLogger(__name__)
    logger.debug('callbacks.mesh_update_canceled')
    settings = get_main_settings()
    head = settings.get_head(headnum)
    if not head:
        logger.debug('WRONG_HEAD')
        return
    head.discard_model_changes()


def update_mesh_with_dialog(self, context):
    logger = logging.getLogger(__name__)
    logger.debug('update_mesh_with_dialog')

    headnum = self.get_headnum()
    FBLoader.load_model(headnum)

    logger.debug('model_changed: {}'.format(self.model_changed()))
    if not self.model_changed():
        return

    if self.has_no_blendshapes():
        if _update_mesh_now(headnum):
            self.apply_model_changes()
        else:
            self.discard_model_changes()
    else:
        warn = get_operator(Config.fb_blendshapes_warning_idname)
        warn('INVOKE_DEFAULT', headnum=headnum)


def update_mesh_simple(self, context):
    headnum = self.get_headnum()
    FBLoader.load_model(headnum)
    _update_mesh_now(headnum)


def _update_mesh_now(headnum):
    logger = logging.getLogger(__name__)
    logger.debug('callbacks.update_mesh')

    settings = get_main_settings()
    head = settings.get_head(headnum)
    if not head:
        logger.debug('WRONG_HEAD')
        return

    if head.should_use_emotions() and \
            head.expression_view != Config.empty_expression_view_idname:
        keyframe = head.get_expression_view_keyframe()
        if keyframe <= 0:
            keyframe = None
    else:
        keyframe = None

    logger.debug('create_mesh_for_update')

    old_mesh = head.headobj.data
    FBLoader.load_model(headnum)

    fb = FBLoader.get_builder()
    models = [x.name for x in fb.models_list()]
    if (head.model_type in models):
        model_index = models.index(head.model_type)
    else:
        logger.error('MODEL_TYPE_NOT_FOUND (Reset to default)')
        model_index = 0
        head.model_type = models[model_index]

    try:
        fb.select_model(model_index)
    except pkt_module().ModelLoadingException:
        logger.error('CHANGE_MODEL_ERROR: ModelLoadingException')
        error_message = 'Can\'t access face model data\n\n' \
                        'Face model data is locked by another ' \
                        'process or corrupted.\n' \
                        'Please check if there are no other processes\n' \
                        'using face data at the moment.\n' \
                        'If that doesn\'t help, please reinstall the add-on.'
        warn = get_operator(Config.fb_warning_idname)
        warn('INVOKE_DEFAULT', msg=ErrorType.CustomMessage,
             msg_content=error_message)
        return False
    except Exception as err:
        logger.error('CHANGE_MODEL_ERROR: Unknown Exception')
        logger.error('info: {} -- {}'.format(type(err), err))
        return False

    logger.debug('MODEL_TYPE: [{}] {}'.format(model_index, head.model_type))

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

    recreate_vertex_groups_flag = Config.recreate_vertex_groups and \
                                  len(old_mesh.vertices) == len(mesh.vertices)
    if recreate_vertex_groups_flag:
        try:
            vg_groups_dict = get_vertex_groups(head.headobj)
        except Exception as err:
            logger.error('_update_mesh_now get VG: {}'.format(str(err)))
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
        wf.init_geom_data_from_fb(fb, head.headobj, keyframe)
        wf.init_edge_indices(fb)
        vp.update_wireframe_colors()

    if recreate_vertex_groups_flag:
        try:
            create_vertex_groups(head.headobj, vg_groups_dict)
        except Exception as err:
            logger.error('_update_mesh_now create VG: {}'.format(str(err)))

    mesh_name = old_mesh.name
    # Delete old mesh
    bpy.data.meshes.remove(old_mesh, do_unlink=True)
    mesh.name = mesh_name
    return True


def update_expressions(self, context):
    logger = logging.getLogger(__name__)
    settings = get_main_settings()
    headnum = self.get_headnum()
    if headnum < 0:
        logger.debug('WRONG HEADNUM {}'.format(headnum))
        return
    logger.debug('EXPRESSIONS HEADNUM {}'.format(headnum))
    fb = FBLoader.get_builder()
    fb.set_use_emotions(self.should_use_emotions())
    logger.debug('EXPRESSIONS: {}'.format(self.should_use_emotions()))

    coords.update_head_mesh_non_neutral(fb, self)
    if not settings.pinmode:
        return

    FBLoader.update_wireframe_shader_only(settings.current_headnum,
                                          settings.current_camnum)


def update_expression_options(self, context):
    logger = logging.getLogger(__name__)
    settings = get_main_settings()
    headnum = self.get_headnum()
    camnum = settings.current_camnum
    if headnum < 0 or camnum < 0:
        logger.error('WRONG HEADNUM: {} CAMNUM: {}'.format(headnum, camnum))
        return
    logger.debug('EXPRESSIONS HEADNUM: '
                 '{} {}'.format(headnum, self.should_use_emotions()))
    fb = FBLoader.get_builder()
    FBLoader.solve(headnum, camnum)

    FBLoader.update_all_camera_positions(headnum)
    FBLoader.save_fb_serial_str(headnum)

    coords.update_head_mesh_non_neutral(fb, self)
    if not settings.pinmode:
        return

    FBLoader.update_viewport_shaders(context,
                                     settings.current_headnum,
                                     settings.current_camnum)


def update_expression_view(self, context):
    exp_view = self.expression_view
    if exp_view == Config.empty_expression_view_idname:
        self.set_neutral_expression_view()
        return
    if exp_view != Config.neutral_expression_view_idname \
            and not self.has_no_blendshapes():
        logger = logging.getLogger(__name__)
        logger.error('Object has blendshapes so expression view cannot be used')
        self.set_neutral_expression_view()
        error_message = \
            'Expressions can\'t be used with blendshapes\n' \
            '\n' \
            'Unfortunately, using expressions for a model\n' \
            'that has FACS blendshapes is impossible. \n' \
            'Please remove blendshapes before choosing an expression.'
        warn = get_operator(Config.fb_warning_idname)
        warn('INVOKE_DEFAULT', msg=ErrorType.CustomMessage,
             msg_content=error_message)
        return
    update_expressions(self, context)


def update_wireframe_image(self, context):
    settings = get_main_settings()
    vp = FBLoader.viewport()
    wf = vp.wireframer()
    wf.init_colors((settings.wireframe_color,
                    settings.wireframe_special_color,
                    settings.wireframe_midline_color),
                    settings.wireframe_opacity)
    wf.init_wireframe_image(FBLoader.get_builder(), settings.show_specials)
    vp.update_wireframe_colors()


def update_wireframe_func(self, context):
    FBLoader.viewport().update_wireframe_colors()


def update_pin_sensitivity(self, context):
    if self.pin_size > self.pin_sensitivity:
        self.pin_size = self.pin_sensitivity

    FBLoader.viewport().update_pin_sensitivity()


def universal_getter(name, type):
    def _getter(self):
        if name in self.keys():
            return self[name]
        else:
            return UserPreferences.get_value_safe(name, type)
    return _getter


def universal_setter(name):
    def _setter(self, value):
        self[name] = value
    return _setter


def update_pin_size(self, context):
    if self.pin_sensitivity < self.pin_size:
        self.pin_sensitivity = self.pin_size
    FBLoader.viewport().update_pin_size()


def update_model_scale(self, context):
    headnum = self.get_headnum()
    FBLoader.load_model(headnum)

    settings = get_main_settings()
    head = settings.get_head(headnum)
    fb = FBLoader.get_builder()
    fb.set_scale(head.model_scale)

    head.mark_model_changed_by_scale()

    coords.update_head_mesh_non_neutral(fb, head)
    FBLoader.update_all_camera_positions(headnum)
    FBLoader.update_all_camera_focals(headnum)
    FBLoader.save_fb_serial_str(headnum)
    if settings.pinmode:
        head.need_update = True


def update_cam_image(self, context):
    FBLoader.update_cam_image_size(self)


def update_head_focal(self, context):
    logger = logging.getLogger(__name__)
    logger.debug('UPDATE_HEAD_FOCAL: {}'.format(self.focal))

    for c in self.cameras:
        c.focal = self.focal


def update_camera_focal(self, context):
    def _check_current_selection_is_not_actual(headnum, camnum):
        settings = get_main_settings()
        return headnum < 0 or headnum != settings.current_headnum \
                or camnum != settings.current_camnum

    logger = logging.getLogger(__name__)
    kid = self.get_keyframe()
    self.camobj.data.lens = self.focal
    logger.debug('UPDATE_CAMERA_FOCAL: K:{} F:{}'.format(kid, self.focal))

    if FBLoader.in_pin_drag():
        return

    headnum, camnum = self.get_headnum_camnum()
    if _check_current_selection_is_not_actual(headnum, camnum):
        return

    fb = FBLoader.get_builder()
    if fb.is_key_at(kid):
        fb.set_varying_focal_length_estimation()
        fb.set_focal_length_at(
            kid, self.get_focal_length_in_pixels_coef() * self.focal)
        FBLoader.save_fb_serial_str(headnum)


def update_background_tone_mapping(self, context):
    settings = get_main_settings()
    if not settings.pinmode:
        return
    self.apply_tone_mapping()
