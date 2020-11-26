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
import bpy

from ..config import Config, get_main_settings, get_operator, ErrorType
from . import manipulate
from ..fbloader import FBLoader
import keentools_facebuilder.blender_independent_packages.pykeentools_loader as pkt
from .blendshapes import (create_facs_blendshapes,
                          create_facs_test_animation_on_blendshapes,
                          disconnect_blendshapes_action,
                          remove_blendshapes,
                          update_facs_blendshapes,
                          zero_all_blendshape_weights)


def _get_obj_from_context():
    state, headnum = manipulate.what_is_state()
    if state == 'FACS_HEAD':
        return bpy.context.object, 1.0
    else:
        if headnum < 0:
            return None, 1.0

        settings = get_main_settings()
        head = settings.get_head(headnum)
        if not head:
            return None, 1.0

        FBLoader.load_model(headnum)
        return head.headobj, head.model_scale


def create_blendshapes(operator):
    logger = logging.getLogger(__name__)
    obj, scale = _get_obj_from_context()
    if not obj:
        return {'CANCELLED'}

    try:
        counter = create_facs_blendshapes(obj, scale)
    except pkt.module().UnlicensedException:
        logger.error('UnlicensedException generate_facs_blendshapes')
        warn = get_operator(Config.fb_warning_idname)
        warn('INVOKE_DEFAULT', msg=ErrorType.NoLicense)
        return {'CANCELLED'}
    except Exception:
        logger.error('UNKNOWN EXCEPTION generate_facs_blendshapes')
        operator.report({'ERROR'}, 'Unknown error (see console window)')
        return {'CANCELLED'}

    if counter >= 0:
        logger.info('Created {} blendshapes'.format(counter))
        operator.report({'INFO'}, 'Created {} blendshapes'.format(counter))
    else:
        logger.error('Cannot create blendshapes (FACS Model)')
        operator.report({'ERROR'}, 'Cannot create blendshapes')
    return {'FINISHED'}


def delete_blendshapes(operator):
    obj, scale = _get_obj_from_context()
    if not obj:
        return {'CANCELLED'}

    remove_blendshapes(obj)
    operator.report({'INFO'}, 'Blendshapes have been removed')
    return {'FINISHED'}


def load_animation_from_csv(operator):
    obj, scale = _get_obj_from_context()
    if not obj:
        return {'CANCELLED'}

    if manipulate.has_no_blendshape(obj):
        operator.report({'ERROR'}, 'The object has no blendshapes')
    else:
        op = get_operator(Config.fb_animation_filebrowser_idname)
        op('INVOKE_DEFAULT', obj_name=obj.name)
    return {'FINISHED'}


def create_example_animation(operator):
    obj, scale = _get_obj_from_context()
    if not obj:
        return {'CANCELLED'}

    counter = create_facs_test_animation_on_blendshapes(obj)
    if counter < 0:
        operator.report({'ERROR'}, 'The object has no blendshapes')
    elif counter > 0:
        operator.report({'INFO'}, 'Created animation '
                                  'for {} blendshapes'.format(counter))
    else:
        operator.report({'ERROR'}, 'An error occured while '
                                   'creating animation')
    return {'FINISHED'}


def reset_blendshape_values(operator):
    obj, scale = _get_obj_from_context()
    if not obj:
        return {'CANCELLED'}

    counter = zero_all_blendshape_weights(obj)
    if counter < 0:
        operator.report({'ERROR'}, 'The object has no blendshapes')
    else:
        operator.report({'INFO'}, '{} blendshape values has been '
                                  'set to 0'.format(counter))
    return {'FINISHED'}


def clear_animation(operator):
    obj, scale = _get_obj_from_context()
    if not obj:
        return {'CANCELLED'}

    if disconnect_blendshapes_action(obj):
        operator.report({'INFO'}, 'Animation action has been unlinked')
        zero_all_blendshape_weights(obj)
    else:
        operator.report({'INFO'}, 'Blendshape animation action '
                                  'has not been found')
    return {'FINISHED'}


def export_head_to_fbx(operator):
    obj, scale = _get_obj_from_context()
    if not obj:
        return {'CANCELLED'}

    manipulate.select_object_only(obj)
    bpy.ops.export_scene.fbx('INVOKE_DEFAULT',
                             use_selection=True,
                             bake_anim_use_all_actions=False,
                             bake_anim_use_nla_strips=False,
                             add_leaf_bones=False,
                             mesh_smooth_type='FACE')
    return {'FINISHED'}


def update_blendshapes(operator):
    head = manipulate.get_current_head()
    if head:
        FBLoader.load_model(head.get_headnum())
        try:
            update_facs_blendshapes(head.headobj, head.model_scale)
        except pkt.module().UnlicensedException:
            logger = logging.getLogger(__name__)
            logger.error('UnlicensedException update_blendshapes')
            warn = get_operator(Config.fb_warning_idname)
            warn('INVOKE_DEFAULT', msg=ErrorType.NoLicense)
            return {'CANCELLED'}
        except Exception:
            logger = logging.getLogger(__name__)
            logger.error('UNKNOWN EXCEPTION update_blendshapes')
            operator.report({'ERROR'}, 'Unknown error (see console window)')
            return {'CANCELLED'}
        head.clear_model_changed_status()
        return {'FINISHED'}
    return {'CANCELLED'}


def unhide_head(operator):
    headnum = manipulate.get_current_headnum()
    if headnum >= 0:
        manipulate.unhide_head(headnum)
        return {'FINISHED'}
    return {'CANCELLED'}


def reconstruct_by_mesh(operator):
    manipulate.reconstruct_by_head()
    return {'FINISHED'}
