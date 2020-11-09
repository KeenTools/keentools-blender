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

from .config import get_main_settings
from .fbloader import FBLoader
from .utils.manipulate import get_current_headnum


def update_mesh_geometry(accepted):
    logger = logging.getLogger(__name__)
    logger.debug('callbacks.update_mesh_geometry')
    headnum = get_current_headnum()
    if headnum < 0:
        return

    settings = get_main_settings()
    head = settings.get_head(headnum)

    if not head.model_changed():
        return

    if not accepted:
        logger.debug('discard_model_changes')
        head.discard_model_changes()
        return

    head.apply_model_changes()
    update_mesh_now()


def update_mesh_now():
    logger = logging.getLogger(__name__)
    logger.debug('callbacks.update_mesh')
    headnum = get_current_headnum()
    if headnum < 0:
        return

    settings = get_main_settings()
    head = settings.get_head(headnum)
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

    if old_mesh.shape_keys:
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