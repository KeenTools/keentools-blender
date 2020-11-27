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
from collections import Counter

import bpy

from ..fbloader import FBLoader
from ..config import Config, get_main_settings, get_operator, ErrorType
from . import cameras, attrs, coords
from .exif_reader import (read_exif_to_camera, auto_setup_camera_from_exif,
                          update_image_groups)
import keentools_facebuilder.blender_independent_packages.pykeentools_loader as pkt


def _is_keentools_object(obj):
    return Config.version_prop_name[0] in obj.keys()


def _get_serial(obj):
    return attrs.get_safe_custom_attribute(obj, Config.fb_serial_prop_name[0])


def _get_dir_name(obj):
    return attrs.get_safe_custom_attribute(obj, Config.fb_dir_prop_name[0])


def _get_image_names(obj):
    return attrs.get_safe_custom_attribute(obj, Config.fb_images_prop_name[0])


def _check_facs_available(count):
    return pkt.module().FacsExecutor.facs_available(count)


def is_it_our_mesh(obj):
    if not obj or obj.type != 'MESH':
        return False

    return _check_facs_available(len(obj.data.vertices))


# Scene States and Head number. All States are:
# RECONSTRUCT, NO_HEADS, THIS_HEAD, ONE_HEAD, MANY_HEADS, PINMODE
# ------------
def what_is_state():
    def _how_many_heads():
        settings = get_main_settings()
        unknown_headnum = -1
        heads_count = len(settings.heads)
        if heads_count == 0:
            return 'NO_HEADS', unknown_headnum
        elif heads_count == 1:
            return 'ONE_HEAD', 0
        else:
            return 'MANY_HEADS', unknown_headnum

    context = bpy.context
    settings = get_main_settings()
    unknown_headnum = -1

    if settings.pinmode:
        return 'PINMODE', settings.current_headnum

    obj = context.object

    if not obj:
        return _how_many_heads()

    if not _is_keentools_object(obj):
        if obj.type == 'MESH':
            if _check_facs_available(len(obj.data.vertices)):
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


def get_current_headnum():
    state, headnum = what_is_state()
    return headnum


def get_current_head():
    headnum = get_current_headnum()
    if headnum >= 0:
        settings = get_main_settings()
        return settings.get_head(headnum)
    return None


def has_no_blendshape(obj):
    return not obj or obj.type != 'MESH' or not obj.data or \
           not obj.data.shape_keys


def has_blendshapes_action(obj):
    if obj and obj.type == 'MESH' \
           and obj.data.shape_keys \
           and obj.data.shape_keys.animation_data \
           and obj.data.shape_keys.animation_data.action:
        return True
    return False


def get_obj_from_context(context, force_fbloader=True):
    state, headnum = what_is_state()
    if state == 'FACS_HEAD':
        return context.object, 1.0
    else:
        if headnum < 0:
            return None, 1.0

        settings = get_main_settings()
        head = settings.get_head(headnum)
        if not head:
            return None, 1.0

        if force_fbloader:
            FBLoader.load_model(headnum)
        return head.headobj, head.model_scale


def force_undo_push(msg='KeenTools operation'):
    inc_operation()
    bpy.ops.ed.undo_push(message=msg)


def push_head_in_undo_history(head, msg='KeenTools operation'):
    head.need_update = True
    force_undo_push(msg)
    head.need_update = False


def push_neutral_head_in_undo_history(head, keyframe,
                                      msg='KeenTools operation'):
    fb = FBLoader.get_builder()
    coords.update_head_mesh_neutral(fb, head.headobj)
    push_head_in_undo_history(head, msg)
    if head.should_use_emotions():
        coords.update_head_mesh_emotions(fb, head.headobj, keyframe)


def check_settings():
    settings = get_main_settings()
    if not settings.check_heads_and_cams():
        heads_deleted, cams_deleted = settings.fix_heads()
        if heads_deleted == 0:
            warn = get_operator(Config.fb_warning_idname)
            warn('INVOKE_DEFAULT', msg=ErrorType.SceneDamaged)
        return False
    return True


# --------------------
def inc_operation():
    """ Debug purpose """
    settings = get_main_settings()
    settings.opnum += 1


def get_operation():
    """ Debug purpose """
    settings = get_main_settings()
    return settings.opnum
# --------------------


def select_object_only(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(state=True)
    bpy.context.view_layer.objects.active = obj


def unhide_head(headnum):
    settings = get_main_settings()
    head = settings.get_head(headnum)
    FBLoader.load_model(headnum)
    coords.update_head_mesh_neutral(FBLoader.get_builder(), head.headobj)
    head.headobj.hide_set(False)
    settings.pinmode = False


def use_camera_frame_size(headnum, camnum):
    # Camera Background --> Render size
    scene = bpy.context.scene
    settings = get_main_settings()
    camera = settings.get_camera(headnum, camnum)
    w, h = camera.get_image_size()
    settings.frame_width = w
    settings.frame_height = h
    if w > 0 and h > 0:
        scene.render.resolution_x = w
        scene.render.resolution_y = h


def use_render_frame_size():
    scene = bpy.context.scene
    settings = get_main_settings()
    settings.frame_width = scene.render.resolution_x
    settings.frame_height = scene.render.resolution_y


def auto_detect_frame_size():
    scene = bpy.context.scene
    settings = get_main_settings()
    headnum = settings.current_headnum
    sizes = []
    for c in settings.get_head(headnum).cameras:
        w, h = c.get_image_size()
        sizes.append((w, h))
    cnt = Counter(sizes)
    mc = cnt.most_common(2)
    if len(mc) == 0:
        return
    el = mc[0][0]
    # If most are undefined images
    if el == (-1, -1):
        if len(mc) > 1:
            el = mc[1][0]
    if el[0] > 0:
        scene.render.resolution_x = el[0]
        settings.frame_width = el[0]
    if el[1] > 0:
        scene.render.resolution_y = el[1]
        settings.frame_height = el[1]


def reset_model_to_neutral(headnum):
    settings = get_main_settings()
    FBLoader.load_model(headnum)
    head = settings.get_head(headnum)
    if head is None:
        return
    fb = FBLoader.get_builder()
    coords.update_head_mesh_neutral(fb, head.headobj)


def load_expressions_to_model(headnum, camnum):
    settings = get_main_settings()
    FBLoader.load_model(headnum)
    head = settings.get_head(headnum)
    if head is None:
        return
    fb = FBLoader.get_builder()
    coords.update_head_mesh_emotions(fb, head.headobj,
                                     head.get_keyframe(camnum))


def reconstruct_by_head():
    """ Reconstruct Cameras and Scene structures by serial """
    logger = logging.getLogger(__name__)
    scene = bpy.context.scene
    rx = scene.render.resolution_x
    ry = scene.render.resolution_y
    settings = get_main_settings()

    obj = bpy.context.object

    if obj.type != 'MESH':
        return

    if not _is_keentools_object(obj):
        return

    logger.debug('START RECONSTRUCT')

    params = cameras.get_camera_params(obj)
    if params is None:
        params = cameras.default_camera_params()
        logger.debug('DEFAULT CAMERA PARAMETERS GENERATED')
    logger.debug('PARAMS: {}'.format(params))

    serial_str = _get_serial(obj)
    if serial_str is None:
        serial_str = ""
    logger.debug("SERIAL")

    dir_name = _get_dir_name(obj)
    if dir_name is None:
        dir_name = ""
    logger.debug("DIR_NAME: {}".format(dir_name))

    images = _get_image_names(obj)
    if type(images) is not list:
        images = []
    logger.debug("IMAGES: {}".format(images))
    logger.debug("PARAMETERS LOADED. START HEAD CREATION")

    settings.fix_heads()
    headnum = len(settings.heads)
    head = settings.heads.add()
    head.headobj = obj

    try:
        head.set_serial_str(serial_str)
        fb = FBLoader.new_builder()
        head.sensor_width = params['sensor_width']
        head.sensor_height = params['sensor_height']
        head.focal = params['focal']
        head.use_emotions = False
        scene.render.resolution_x = params['frame_width']
        scene.render.resolution_y = params['frame_height']

        fb.deserialize(head.get_serial_str())
        logger.debug("RECONSTRUCT KEYFRAMES {}".format(str(fb.keyframes())))

        for i, kid in enumerate(fb.keyframes()):
            cam_ob = FBLoader.create_camera_object(headnum, i)
            camera = head.cameras.add()
            camera.camobj = cam_ob
            camera.set_keyframe(kid)

            filename = images[i]
            logger.debug("IMAGE {} {}".format(i, filename))
            img = bpy.data.images.new(filename, 0, 0)
            img.source = 'FILE'
            img.filepath = filename

            FBLoader.add_background_to_camera(headnum, i, img)

            read_exif_to_camera(headnum, i, filename)
            camera.orientation = camera.exif.orientation

            auto_setup_camera_from_exif(camera)

            logger.debug("CAMERA CREATED {}".format(kid))
            FBLoader.place_camera(headnum, i)
            camera.set_model_mat(fb.model_mat(kid))
            FBLoader.update_pins_count(headnum, i)

            attrs.mark_keentools_object(camera.camobj)

        update_image_groups(head)
        FBLoader.update_cameras_from_old_version(headnum)

    except Exception:
        logger.error("WRONG PARAMETERS")
        for i, c in enumerate(reversed(head.cameras)):
            if c.camobj is not None:
                bpy.data.objects.remove(c.camobj, do_unlink=True)
            head.cameras.remove(i)
        settings.heads.remove(headnum)
        scene.render.resolution_x = rx
        scene.render.resolution_y = ry
        logger.info("SCENE PARAMETERS RESTORED")
        warn = get_operator(Config.fb_warning_idname)
        warn('INVOKE_DEFAULT', msg=ErrorType.CannotReconstruct)
        return
