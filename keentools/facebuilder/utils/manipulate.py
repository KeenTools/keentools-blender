# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2019-2022  KeenTools

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

from typing import Any, Tuple, Optional

import bpy
from bpy.types import Object

from ...utils.kt_logging import KTLogger
from ...addon_config import Config, fb_settings, get_operator, ErrorType
from ...facebuilder_config import FBConfig
from ...utils.manipulate import force_undo_push
from ...utils import attrs
from ...blender_independent_packages.pykeentools_loader import module as pkt_module
from ..utils.cameras import (get_camera_params, default_camera_params)
from .exif_reader import (read_exif_to_camera, auto_setup_camera_from_exif)
from ...utils.bpy_common import bpy_render_frame, bpy_set_render_frame


_log = KTLogger(__name__)


def push_head_in_undo_history(head: Any,
                              msg: str = 'KeenTools operation') -> None:
    head.need_update = True
    inc_fb_operation()
    force_undo_push(msg)
    head.need_update = False


def inc_fb_operation() -> None:
    settings = fb_settings()
    settings.opnum += 1


def get_fb_operation() -> int:
    settings = fb_settings()
    return settings.opnum


def check_settings() -> bool:
    settings = fb_settings()
    if not settings.check_heads_and_cams():
        heads_deleted, cams_deleted = settings.fix_heads()
        if heads_deleted == 0:
            warn = get_operator(Config.kt_warning_idname)
            warn('INVOKE_DEFAULT', msg=ErrorType.SceneDamaged)
        return False
    return True


def _is_facebuilder_object(obj: Object) -> bool:
    return FBConfig.version_prop_name in obj.keys()


def is_facebuilder_head_topology(obj: Object) -> bool:
    if not obj or obj.type != 'MESH':
        return False
    return check_facs_available(len(obj.data.vertices))


def check_facs_available(count: int) -> bool:
    try:
        return pkt_module().FacsExecutor.facs_available(count)
    except pkt_module().ModelLoadingException as err:
        _log.error(f'check_facs_available ModelLoadingException:\n{str(err)}')
    except Exception as err:
        _log.error(f'check_facs_available Unknown Exception:\n{str(err)}')
    return False


# Scene States and Head number. All States are:
# RECONSTRUCT, NO_HEADS, THIS_HEAD, ONE_HEAD, MANY_HEADS, PINMODE
# ------------
def what_is_state() -> Tuple[str, int]:
    def _how_many_heads() -> Tuple[str, int]:
        settings = fb_settings()
        unknown_headnum = -1
        heads_count = len(settings.heads)
        if heads_count == 0:
            return 'NO_HEADS', unknown_headnum
        elif heads_count == 1:
            return 'ONE_HEAD', 0
        else:
            return 'MANY_HEADS', unknown_headnum

    context = bpy.context
    settings = fb_settings()
    unknown_headnum = -1
    if settings is None:
        return 'NO_HEADS', unknown_headnum

    if settings.pinmode:
        return 'PINMODE', settings.current_headnum

    obj = context.object

    if not obj:
        return _how_many_heads()

    if not _is_facebuilder_object(obj):
        if obj.type == 'MESH':
            if check_facs_available(len(obj.data.vertices)):
                return 'FACS_HEAD', unknown_headnum
        return _how_many_heads()

    if obj.type == 'MESH':
        ind = settings.find_head_index(obj)
        if ind >= 0:
            return 'THIS_HEAD', ind
        else:
            return 'RECONSTRUCT', unknown_headnum

    elif obj.type == 'CAMERA':
        ind, _ = settings.find_cam_index(obj)
        if ind >= 0:
            return 'THIS_HEAD', ind
        else:
            return _how_many_heads()

    return _how_many_heads()


def get_current_headnum() -> int:
    state, headnum = what_is_state()
    return headnum


def get_current_head() -> Optional[Any]:
    headnum = get_current_headnum()
    if headnum >= 0:
        settings = fb_settings()
        return settings.get_head(headnum)
    return None


def get_obj_from_context(context: Any,
        force_fbloader: bool = True) -> Tuple[Optional[Object], float]:

    state, headnum = what_is_state()
    if state == 'FACS_HEAD':
        return context.object, 1.0
    else:
        if headnum < 0:
            return None, 1.0

        settings = fb_settings()
        head = settings.get_head(headnum)
        if not head:
            return None, 1.0

        if force_fbloader:
            settings.loader().load_model(headnum)
        return head.headobj, head.model_scale


def _get_serial(obj: Object) -> str:
    return attrs.get_safe_custom_attribute(obj, FBConfig.fb_serial_prop_name)


def _get_dir_name(obj: Object) -> str:
    return attrs.get_safe_custom_attribute(obj, FBConfig.fb_dir_prop_name)


def _get_image_names(obj: Object) -> str:
    return attrs.get_safe_custom_attribute(obj, FBConfig.fb_images_prop_name)


def reconstruct_by_head() -> bool:
    """ Reconstruct Cameras and Scene structures by serial """
    rx, ry = bpy_render_frame()
    settings = fb_settings()
    loader = settings.loader()

    obj = bpy.context.object

    if obj.type != 'MESH':
        return False

    if not _is_facebuilder_object(obj):
        return False

    _log.output('START RECONSTRUCTION')

    params = get_camera_params(obj)
    if params is None:
        params = default_camera_params()
        _log.output('DEFAULT CAMERA PARAMETERS GENERATED')
    _log.output(f'PARAMS: {params}')

    serial_str = _get_serial(obj)
    if serial_str is None:
        serial_str = ''
    _log.output('SERIAL')

    dir_name = _get_dir_name(obj)
    if dir_name is None:
        dir_name = ''
    _log.output(f'DIR_NAME: {dir_name}')

    images = _get_image_names(obj)
    if type(images) is not list:
        images = []
    _log.output(f'IMAGES: {images}')
    _log.output('PARAMETERS LOADED. START HEAD CREATION')

    settings.fix_heads()
    headnum = len(settings.heads)
    head = settings.heads.add()
    head.headobj = obj

    try:
        head.store_serial_str_in_head_and_on_headobj(serial_str)
        fb = loader.new_builder()
        head.sensor_width = params['sensor_width']
        head.sensor_height = params['sensor_height']
        head.focal = params['focal']
        bpy_set_render_frame(params['frame_width'], params['frame_height'])

        fb.deserialize(head.get_serial_str())
        _log.output(f'RECONSTRUCT KEYFRAMES {str(fb.keyframes())}')

        for i, kid in enumerate(fb.keyframes()):
            cam_ob = loader.create_camera_object(headnum, i)
            camera = head.cameras.add()
            camera.camobj = cam_ob
            camera.set_keyframe(kid)

            filename = images[i]
            _log.output(f'IMAGE {i} {filename}')
            img = bpy.data.images.new(filename, 0, 0)
            img.source = 'FILE'
            img.filepath = filename

            loader.add_background_to_camera(headnum, i, img)

            read_exif_to_camera(headnum, i, filename)
            camera.orientation = camera.exif.orientation

            auto_setup_camera_from_exif(camera)

            _log.output(f'CAMERA CREATED {kid}')
            loader.place_camera(headnum, i)
            loader.update_camera_pins_count(headnum, i)

            attrs.mark_keentools_object(camera.camobj)

        loader.update_cameras_from_old_version(headnum)

    except Exception:
        _log.error('WRONG PARAMETERS')
        for i, c in enumerate(reversed(head.cameras)):
            if c.camobj is not None:
                bpy.data.objects.remove(c.camobj, do_unlink=True)
            head.cameras.remove(i)
        settings.heads.remove(headnum)
        bpy_set_render_frame(rx, ry)
        _log.info('SCENE PARAMETERS RESTORED')
        warn = get_operator(Config.kt_warning_idname)
        warn('INVOKE_DEFAULT', msg=ErrorType.CannotReconstruct)
        return False

    return True
