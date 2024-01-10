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

from .kt_logging import KTLogger
from ..addon_config import Config, fb_settings, get_operator, ErrorType
from ..facebuilder_config import FBConfig
from .manipulate import (has_no_blendshape, select_object_only)
from ..facebuilder.utils.manipulate import (get_current_headnum,
                                            get_current_head,
                                            get_obj_from_context,
                                            reconstruct_by_head)
from .coords import update_head_mesh_non_neutral
from ..facebuilder.utils.cameras import show_all_cameras
from ..facebuilder.fbloader import FBLoader
from ..blender_independent_packages.pykeentools_loader import module as pkt_module
from .blendshapes import (create_facs_blendshapes,
                          create_facs_test_animation_on_blendshapes,
                          disconnect_blendshapes_action,
                          remove_blendshapes,
                          update_facs_blendshapes,
                          zero_all_blendshape_weights)
from .localview import exit_area_localview
from .bpy_common import bpy_context, bpy_export_fbx


_log = KTLogger(__name__)


def create_blendshapes(operator):
    _log.output('create_blendshapes call')
    obj, scale = get_obj_from_context(bpy_context())
    if not obj:
        _log.output('no object')
        return {'CANCELLED'}

    settings = fb_settings()
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
        _log.error('UnlicensedException generate_facs_blendshapes')
        warn = get_operator(Config.kt_warning_idname)
        warn('INVOKE_DEFAULT', msg=ErrorType.NoLicense)
        return {'CANCELLED'}
    except Exception:
        _log.error('UNKNOWN EXCEPTION generate_facs_blendshapes')
        operator.report({'ERROR'}, 'Unknown error (see console window)')
        return {'CANCELLED'}

    if counter >= 0:
        _log.info('Created {} blendshapes'.format(counter))
        operator.report({'INFO'}, 'Created {} blendshapes'.format(counter))
    else:
        _log.error('Cannot create blendshapes (FACS Model)')
        operator.report({'ERROR'}, 'Cannot create blendshapes')
    return {'FINISHED'}


def delete_blendshapes(operator):
    _log.output('delete_blendshapes call')
    obj, scale = get_obj_from_context(bpy_context())
    if not obj:
        _log.output('no object')
        return {'CANCELLED'}

    remove_blendshapes(obj)
    _log.output('blendshapes removed')
    operator.report({'INFO'}, 'Blendshapes have been removed')
    return {'FINISHED'}


def load_animation_from_csv(operator):
    _log.output('load_animation_from_csv call')
    obj, scale = get_obj_from_context(bpy_context())
    if not obj:
        _log.output('no object')
        return {'CANCELLED'}

    if has_no_blendshape(obj):
        _log.output('no blendshapes')
        operator.report({'ERROR'}, 'The object has no blendshapes')
    else:
        op = get_operator(FBConfig.fb_animation_filebrowser_idname)
        op('INVOKE_DEFAULT', obj_name=obj.name)
        _log.output('filebrowser called')
    return {'FINISHED'}


def create_example_animation(operator):
    _log.output('create_example_animation call')
    obj, scale = get_obj_from_context(bpy_context())
    if not obj:
        _log.output('no object')
        return {'CANCELLED'}

    counter = create_facs_test_animation_on_blendshapes(obj)
    if counter < 0:
        _log.output('no blendshapes')
        operator.report({'ERROR'}, 'The object has no blendshapes')
    elif counter > 0:
        _log.output('{} animated'.format(counter))
        operator.report({'INFO'}, 'Created animation '
                                  'for {} blendshapes'.format(counter))
    else:
        _log.output('zero animated error')
        operator.report({'ERROR'}, 'An error occured while '
                                   'creating animation')
    return {'FINISHED'}


def reset_blendshape_values(operator):
    _log.output('reset_blendshape_values call')
    obj, scale = get_obj_from_context(bpy_context())
    if not obj:
        _log.output('no object')
        return {'CANCELLED'}

    counter = zero_all_blendshape_weights(obj)
    if counter < 0:
        _log.output('no blendshapes')
        operator.report({'ERROR'}, 'The object has no blendshapes')
    else:
        _log.output('reset {} blendshapes'.format(counter))
        operator.report({'INFO'}, '{} blendshape values has been '
                                  'set to 0'.format(counter))
    return {'FINISHED'}


def clear_animation(operator):
    _log.output('clear_animation call')
    obj, scale = get_obj_from_context(bpy_context())
    if not obj:
        _log.output('no object')
        return {'CANCELLED'}

    if disconnect_blendshapes_action(obj):
        _log.output('action disconnected')
        operator.report({'INFO'}, 'Animation action has been unlinked')
        zero_all_blendshape_weights(obj)
    else:
        _log.output('action not found')
        operator.report({'INFO'}, 'Blendshape animation action '
                                  'has not been found')
    return {'FINISHED'}


def export_head_to_fbx(operator):
    _log.output('export_head_to_fbx call')
    obj, scale = get_obj_from_context(bpy_context())
    if not obj:
        _log.output('no object')
        return {'CANCELLED'}

    select_object_only(obj)
    bpy_export_fbx('INVOKE_DEFAULT',
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
    _log.output('fbx operator finished')
    return {'FINISHED'}


def update_blendshapes(operator):
    _log.output('update_blendshapes call')
    head = get_current_head()
    if head:
        FBLoader.load_model(head.get_headnum())
        try:
            update_facs_blendshapes(head.headobj, head.model_scale)
            _log.output('update_facs_blendshapes performed')
        except pkt_module().UnlicensedException:
            _log.error('UnlicensedException update_blendshapes')
            warn = get_operator(Config.kt_warning_idname)
            warn('INVOKE_DEFAULT', msg=ErrorType.NoLicense)
            return {'CANCELLED'}
        except Exception:
            _log.error('UNKNOWN EXCEPTION update_blendshapes')
            operator.report({'ERROR'}, 'Unknown error (see console window)')
            return {'CANCELLED'}
        head.clear_model_changed_status()
        return {'FINISHED'}
    else:
        _log.output('head not found')
    return {'CANCELLED'}


def unhide_head(operator, context):
    _log.output('unhide_head call')
    headnum = get_current_headnum()
    if headnum >= 0:
        settings = fb_settings()
        head = settings.get_head(headnum)
        FBLoader.load_model(headnum)
        update_head_mesh_non_neutral(FBLoader.get_builder(), head)

        if not exit_area_localview(context.area):
            show_all_cameras(headnum)  # legacy scenes only
            head.headobj.hide_set(False)

        settings.viewport_state.show_ui_elements(context.area)
        settings.pinmode = False

        _log.output('head revealed')
        return {'FINISHED'}
    _log.output('no head')
    return {'CANCELLED'}


def reconstruct_by_mesh():
    _log.output('reconstruct_by_mesh call')
    reconstruct_by_head()
    _log.output('reconstruction finished')
    return {'FINISHED'}
