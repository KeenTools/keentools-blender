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
from .utils.blendshapes import (restore_facs_blendshapes,
                                disconnect_blendshapes_action)
import keentools_facebuilder.blender_independent_packages.pykeentools_loader as pkt


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
        except pkt.module().UnlicensedException:
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
        _update_mesh_now(headnum)
        self.apply_model_changes()
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

    if settings.pinmode and head.should_use_emotions():
        keyframe = head.get_keyframe(settings.current_camnum)
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

    fb.select_model(model_index)
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
    head.headobj.data = mesh
    FBLoader.save_only(headnum)

    # Copy blendshapes and animation
    if old_mesh.shape_keys and len(old_mesh.vertices) == len(mesh.vertices):
        for kb in old_mesh.shape_keys.key_blocks:
            shape = head.headobj.shape_key_add(name=kb.name)
            count = len(kb.data)
            verts = np.empty((count, 3), 'f')
            kb.data.foreach_get('co', np.reshape(verts, count * 3))
            shape.data.foreach_set('co', verts.ravel())
            shape.value = kb.value
        if old_mesh.shape_keys.animation_data and old_mesh.shape_keys.animation_data.action:
            mesh.shape_keys.animation_data_create()
            mesh.shape_keys.animation_data.action = old_mesh.shape_keys.animation_data.action

    if settings.pinmode:
        # Update wireframe structures
        FBLoader.viewport().wireframer().init_geom_data(head.headobj)
        FBLoader.viewport().wireframer().init_edge_indices(FBLoader.get_builder())
        FBLoader.viewport().update_wireframe()

    mesh_name = old_mesh.name
    # Delete old mesh
    bpy.data.meshes.remove(old_mesh, do_unlink=True)
    mesh.name = mesh_name


def update_expressions(self, context):
    settings = get_main_settings()
    if not settings.pinmode:
        return
    fb = FBLoader.get_builder()
    head = settings.get_head(settings.current_headnum)
    if head is not None:
        head.need_update = True
        coords.update_head_mesh(settings, fb, head)
        FBLoader.fb_redraw(settings.current_headnum, settings.current_camnum)


def update_wireframe_image(self, context):
    settings = get_main_settings()
    vp = FBLoader.viewport()
    wf = vp.wireframer()
    wf.init_colors((settings.wireframe_color,
                    settings.wireframe_special_color,
                    settings.wireframe_midline_color),
                    settings.wireframe_opacity)
    wf.init_wireframe_image(FBLoader.get_builder(), settings.show_specials)
    vp.update_wireframe()


def update_wireframe(self, context):
    FBLoader.viewport().update_wireframe()


def update_pin_sensitivity(self, context):
    FBLoader.viewport().update_pin_sensitivity()


def update_pin_size(self, context):
    FBLoader.viewport().update_pin_size()


def update_model_scale(self, context):
    headnum = self.get_headnum()
    FBLoader.load_model(headnum)

    settings = get_main_settings()
    head = settings.get_head(headnum)
    fb = FBLoader.get_builder()
    fb.set_scale(head.model_scale)

    head.mark_model_changed_by_scale()

    coords.update_head_mesh(settings, fb, head)
    FBLoader.update_all_camera_positions(headnum)
    FBLoader.update_all_camera_focals(headnum)
    FBLoader.save_only(headnum)

    if settings.pinmode and FBLoader.viewport().wireframer().is_working():
        FBLoader.fb_redraw(settings.current_headnum, settings.current_camnum)


def update_cam_image(self, context):
    FBLoader.update_cam_image_size(self)


def update_head_focal(self, context):
    logger = logging.getLogger(__name__)
    logger.debug('UPDATE_HEAD_FOCAL: {}'.format(self.focal))

    for c in self.cameras:
        c.focal = self.focal


def update_camera_focal(self, context):
    logger = logging.getLogger(__name__)
    settings = get_main_settings()
    kid = self.get_keyframe()
    self.camobj.data.lens = self.focal
    logger.debug('UPDATE_CAMERA_FOCAL: K:{} F:{}'.format(kid, self.focal))

    fb = FBLoader.get_builder()
    if fb.is_key_at(kid):
        FBLoader.save_only(settings.current_headnum)

    if FBLoader.in_pin_drag() or self.auto_focal_estimation or \
            self.image_group <= 0 or \
            settings.current_headnum < 0 or settings.current_camnum < 0:
        return

    head = settings.get_head(settings.current_headnum)
    current_camera = head.get_camera(settings.current_camnum)
    if current_camera.get_keyframe() != kid:
        return

    for cam in head.cameras:
        if cam.get_keyframe() != kid and not cam.auto_focal_estimation and \
                cam.image_group == self.image_group:
            cam.focal = self.focal


def update_blue_camera_button(self, context):
    settings = get_main_settings()
    if not settings.blue_camera_button:
        op = get_operator(Config.fb_exit_pinmode_idname)
        op('EXEC_DEFAULT')
        settings.blue_camera_button = True


def update_blue_head_button(self, context):
    settings = get_main_settings()
    if not settings.blue_head_button:
        op = get_operator(Config.fb_select_head_idname)
        op('EXEC_DEFAULT')
        settings.blue_head_button = True
