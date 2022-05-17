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

from ..addon_config import Config, get_operator, ErrorType
from ..facebuilder_config import FBConfig, get_fb_settings
from .manipulate import (has_no_blendshape, select_object_only)
from ..facebuilder.utils.manipulate import (get_current_headnum,
                                            get_current_head,
                                            get_obj_from_context,
                                            reconstruct_by_head)
from .coords import update_head_mesh_non_neutral
from ..facebuilder.utils.cameras import show_all_cameras
from .other import unhide_viewport_ui_elements_from_object
from ..facebuilder.fbloader import FBLoader
from ..blender_independent_packages.pykeentools_loader import module as pkt_module
from .blendshapes import (create_facs_blendshapes,
                          create_facs_test_animation_on_blendshapes,
                          disconnect_blendshapes_action,
                          remove_blendshapes,
                          update_facs_blendshapes,
                          zero_all_blendshape_weights)
from .localview import exit_area_localview


def create_blendshapes(operator):
    logger = logging.getLogger(__name__)
    logger.debug('create_blendshapes call')
    obj, scale = get_obj_from_context(bpy.context)
    if not obj:
        logger.debug('no object')
        return {'CANCELLED'}

    settings = get_fb_settings()
    headnum = settings.head_by_obj(obj)
    if headnum >= 0:
        head = settings.get_head(headnum)
        if head.should_use_emotions() and \
                head.expression_view != FBConfig.neutral_expression_view_name:
            warn = get_operator(FBConfig.fb_noblenshapes_until_expression_warning_idname)
            warn('INVOKE_DEFAULT', headnum=headnum)
            return {'CANCELLED'}
        # Forced change before creating blendshapes
        # It's not visible to user since expressions are switched off
        head.set_neutral_expression_view()

    try:
        counter = create_facs_blendshapes(obj, scale)
    except pkt_module().UnlicensedException:
        logger.error('UnlicensedException generate_facs_blendshapes')
        warn = get_operator(Config.kt_warning_idname)
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
    logger = logging.getLogger(__name__)
    logger.debug('delete_blendshapes call')
    obj, scale = get_obj_from_context(bpy.context)
    if not obj:
        logger.debug('no object')
        return {'CANCELLED'}

    remove_blendshapes(obj)
    logger.debug('blendshapes removed')
    operator.report({'INFO'}, 'Blendshapes have been removed')
    return {'FINISHED'}


def load_animation_from_csv(operator):
    logger = logging.getLogger(__name__)
    logger.debug('load_animation_from_csv call')
    obj, scale = get_obj_from_context(bpy.context)
    if not obj:
        logger.debug('no object')
        return {'CANCELLED'}

    if has_no_blendshape(obj):
        logger.debug('no blendshapes')
        operator.report({'ERROR'}, 'The object has no blendshapes')
    else:
        op = get_operator(FBConfig.fb_animation_filebrowser_idname)
        op('INVOKE_DEFAULT', obj_name=obj.name)
        logger.debug('filebrowser called')
    return {'FINISHED'}


def create_example_animation(operator):
    logger = logging.getLogger(__name__)
    logger.debug('create_example_animation call')
    obj, scale = get_obj_from_context(bpy.context)
    if not obj:
        logger.debug('no object')
        return {'CANCELLED'}

    counter = create_facs_test_animation_on_blendshapes(obj)
    if counter < 0:
        logger.debug('no blendshapes')
        operator.report({'ERROR'}, 'The object has no blendshapes')
    elif counter > 0:
        logger.debug('{} animated'.format(counter))
        operator.report({'INFO'}, 'Created animation '
                                  'for {} blendshapes'.format(counter))
    else:
        logger.debug('zero animated error')
        operator.report({'ERROR'}, 'An error occured while '
                                   'creating animation')
    return {'FINISHED'}


def reset_blendshape_values(operator):
    logger = logging.getLogger(__name__)
    logger.debug('reset_blendshape_values call')
    obj, scale = get_obj_from_context(bpy.context)
    if not obj:
        logger.debug('no object')
        return {'CANCELLED'}

    counter = zero_all_blendshape_weights(obj)
    if counter < 0:
        logger.debug('no blendshapes')
        operator.report({'ERROR'}, 'The object has no blendshapes')
    else:
        logger.debug('reset {} blendshapes'.format(counter))
        operator.report({'INFO'}, '{} blendshape values has been '
                                  'set to 0'.format(counter))
    return {'FINISHED'}


def clear_animation(operator):
    logger = logging.getLogger(__name__)
    logger.debug('clear_animation call')
    obj, scale = get_obj_from_context(bpy.context)
    if not obj:
        logger.debug('no object')
        return {'CANCELLED'}

    if disconnect_blendshapes_action(obj):
        logger.debug('action disconnected')
        operator.report({'INFO'}, 'Animation action has been unlinked')
        zero_all_blendshape_weights(obj)
    else:
        logger.debug('action not found')
        operator.report({'INFO'}, 'Blendshape animation action '
                                  'has not been found')
    return {'FINISHED'}


def export_head_to_fbx(operator):
    logger = logging.getLogger(__name__)
    logger.debug('export_head_to_fbx call')
    obj, scale = get_obj_from_context(bpy.context)
    if not obj:
        logger.debug('no object')
        return {'CANCELLED'}

    select_object_only(obj)
    bpy.ops.export_scene.fbx('INVOKE_DEFAULT',
                             use_selection=True,
                             bake_anim_use_all_actions=False,
                             bake_anim_use_nla_strips=False,
                             add_leaf_bones=False,
                             mesh_smooth_type='FACE',
                             # Default directions for axes in FBX
                             axis_forward='-Z',
                             axis_up='Y',
                             # Warning! Option marked as experimental in docs
                             # but we need it for same UX in UE4/Unity imports
                             bake_space_transform=True)
    logger.debug('fbx operator called')
    return {'FINISHED'}


def update_blendshapes(operator):
    logger = logging.getLogger(__name__)
    logger.debug('update_blendshapes call')
    head = get_current_head()
    if head:
        FBLoader.load_model(head.get_headnum())
        try:
            update_facs_blendshapes(head.headobj, head.model_scale)
            logger.debug('update_facs_blendshapes performed')
        except pkt_module().UnlicensedException:
            logger = logging.getLogger(__name__)
            logger.error('UnlicensedException update_blendshapes')
            warn = get_operator(Config.kt_warning_idname)
            warn('INVOKE_DEFAULT', msg=ErrorType.NoLicense)
            return {'CANCELLED'}
        except Exception:
            logger = logging.getLogger(__name__)
            logger.error('UNKNOWN EXCEPTION update_blendshapes')
            operator.report({'ERROR'}, 'Unknown error (see console window)')
            return {'CANCELLED'}
        head.clear_model_changed_status()
        return {'FINISHED'}
    else:
        logger.debug('head not found')
    return {'CANCELLED'}


def unhide_head(operator, context):
    logger = logging.getLogger(__name__)
    logger.debug('unhide_head call')
    headnum = get_current_headnum()
    if headnum >= 0:
        settings = get_fb_settings()
        head = settings.get_head(headnum)
        FBLoader.load_model(headnum)
        update_head_mesh_non_neutral(FBLoader.get_builder(), head)

        if not exit_area_localview(context.area):
            show_all_cameras(headnum)  # legacy scenes only
            head.headobj.hide_set(False)

        if head.headobj:
            unhide_viewport_ui_elements_from_object(context.area, head.headobj)
        settings.pinmode = False

        logger.debug('head revealed')
        return {'FINISHED'}
    logger.debug('no head')
    return {'CANCELLED'}


def reconstruct_by_mesh():
    logger = logging.getLogger(__name__)
    logger.debug('reconstruct_by_mesh call')
    reconstruct_by_head()
    logger.debug('reconstruction finished')
    return {'FINISHED'}
