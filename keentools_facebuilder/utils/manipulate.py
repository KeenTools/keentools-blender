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

from keentools_facebuilder import Config
from keentools_facebuilder.config import get_main_settings, BuilderType, \
    ErrorType
from keentools_facebuilder.fbloader import FBLoader
from keentools_facebuilder.utils import cameras, attrs

from .. config import get_main_settings, ErrorType, Config


def force_undo_push(msg='KeenTools operation'):
    inc_operation()
    bpy.ops.ed.undo_push(message=msg)


def check_settings():
    settings = get_main_settings()
    if not settings.check_heads_and_cams():
        # Settings structure is broken
        # Fix Heads and cameras
        heads_deleted, cams_deleted = settings.fix_heads()
        if heads_deleted == 0:
            warn = getattr(bpy.ops.wm, Config.fb_warning_operator_callname)
            warn('INVOKE_DEFAULT', msg=ErrorType.SceneDamaged)
        return False
    return True


#--------------------
def inc_operation():
    """ Debug purpose """
    settings = get_main_settings()
    settings.opnum += 1


def get_operation():
    """ Debug purpose """
    settings = get_main_settings()
    return settings.opnum
#--------------------


def unhide_head(headnum):
    settings = get_main_settings()
    settings.heads[headnum].headobj.hide_set(False)
    settings.pinmode = False


def use_camera_frame_size(headnum, camnum):
    # Camera Background --> Render size
    scene = bpy.context.scene
    settings = get_main_settings()
    camera = settings.heads[headnum].cameras[camnum]
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
    for c in settings.heads[headnum].cameras:
        w, h = c.get_image_size()
        sizes.append((w, h))
    cnt = Counter(sizes)
    mc = cnt.most_common(2)
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


def use_render_frame_size_scaled():
    # Allow converts scenes pinned on default cameras
    scene = bpy.context.scene
    settings = get_main_settings()
    headnum = settings.current_headnum
    head = settings.heads[headnum]
    rw = scene.render.resolution_x
    rh = scene.render.resolution_y
    fw = settings.frame_width
    fh = settings.frame_height
    kx = rw / fw
    dy = 0.5 * (rh - fh * kx)

    FBLoader.load_only(headnum)
    fb = FBLoader.get_builder()
    for i, c in enumerate(head.cameras):
        if c.pins_count > 0:
            kid = cameras.keyframe_by_camnum(headnum, i)
            for n in range(fb.pins_count(kid)):
                p = fb.pin(kid, n)
                fb.move_pin(
                    kid, n, (kx * p.img_pos[0], kx * p.img_pos[1] + dy))
            fb.solve_for_current_pins(kid)
    FBLoader.save_only(headnum)

    settings.frame_width = rw
    settings.frame_height = rh


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

    # Has object our main attribute?
    if not attrs.has_custom_attribute(obj, Config.version_prop_name[0]):
        return  # No, it hasn't, leave

    # Object marked by our attribute, so can be reconstructed
    error_message = "===============\n" \
                    "Can't reconstruct\n" \
                    "===============\n" \
                    "Object parameters are invalid or missing:\n"

    logger.info("START RECONSTRUCT")

    obj_type = attrs.get_safe_custom_attribute(
            obj, Config.object_type_prop_name[0])
    if obj_type is None:
        obj_type = BuilderType.FaceBuilder
    logger.debug("OBJ_TYPE: {}".format(obj_type))

    if obj_type != BuilderType.FaceBuilder:
        warn = getattr(bpy.ops.wm, Config.fb_warning_operator_callname)
        warn('INVOKE_DEFAULT', msg=ErrorType.CustomMessage,
             msg_content=error_message + 'Object Type')
        return  # Problem with object type custom attribute

    # Get Mod version
    mod_ver = attrs.get_safe_custom_attribute(
            obj, Config.fb_mod_ver_prop_name[0])
    if mod_ver is None:
        mod_ver = Config.unknown_mod_ver
    logger.debug("MOD_VER {}".format(mod_ver))

    # Get all camera parameters
    params = cameras.get_camera_params(obj)
    if params is None:
        warn = getattr(bpy.ops.wm, Config.fb_warning_operator_callname)
        warn('INVOKE_DEFAULT', msg=ErrorType.CustomMessage,
             msg_content=error_message + 'camera')
        return  # One or more parameters undefined
    logger.debug("PARAMS: {}".format(params))

    # Get Serial string
    serial_str = attrs.get_safe_custom_attribute(
            obj, Config.fb_serial_prop_name[0])
    if serial_str is None:
        serial_str = ""
    logger.debug("SERIAL")

    # Get Dir Name
    dir_name = attrs.get_safe_custom_attribute(
            obj, Config.fb_dir_prop_name[0])
    if dir_name is None:
        dir_name = ""
    logger.debug("DIR_NAME: {}".format(dir_name))

    # Get Image Names
    images = attrs.get_safe_custom_attribute(
            obj, Config.fb_images_prop_name[0])
    if type(images) is not list:
        images = []
    logger.debug("IMAGES: {}".format(images))
    logger.debug("PARAMETERS LOADED. START HEAD CREATION")
    # -------------------
    # Fix our settings structure before new head add
    settings.fix_heads()

    headnum = len(settings.heads)
    # Create new head in collection
    head = settings.heads.add()
    head.headobj = obj

    try:
        # Copy serial string from object custom property
        head.set_serial_str(serial_str)
        fb = FBLoader.new_builder(obj_type, mod_ver)
        head.mod_ver = FBLoader.get_builder_version()
        settings.current_head = headnum
        settings.current_camnum = 0
        logger.debug("CREATED MOD_VER {}".format(head.mod_ver))

        head.sensor_width = params['sensor_width']
        head.sensor_height = params['sensor_height']
        head.focal = params['focal']
        scene.render.resolution_x = params['frame_width']
        scene.render.resolution_y = params['frame_height']

        # New head shape
        fb.deserialize(head.get_serial_str())
        # Now reconstruct cameras
        for i, kid in enumerate(fb.keyframes()):
            c = FBLoader.add_camera(headnum, None)
            FBLoader.set_keentools_version(c.camobj)
            c.keyframe_id = kid
            logger.debug("CAMERA CREATED {}".format(kid))
            FBLoader.place_cameraobj(kid, c.camobj, obj)
            c.set_model_mat(fb.model_mat(kid))
            FBLoader.update_pins_count(headnum, i)

        # load background images
        for i, f in enumerate(images):
            logger.debug("IM {} {}".format(i, f))
            img = bpy.data.images.new(f, 0, 0)
            img.source = 'FILE'
            img.filepath = f
            head.cameras[i].cam_image = img

        FBLoader.update_camera_params(head)

    except Exception:
        logger.error("WRONG PARAMETERS")
        for i, c in enumerate(reversed(head.cameras)):
            if c.camobj is not None:
                # Delete camera object from scene
                bpy.data.objects.remove(c.camobj, do_unlink=True)
            # Delete link from list
            head.cameras.remove(i)
        settings.heads.remove(headnum)
        scene.render.resolution_x = rx
        scene.render.resolution_y = ry
        logger.debug("SCENE PARAMETERS RESTORED")
        warn = getattr(bpy.ops.wm, Config.fb_warning_operator_callname)
        warn('INVOKE_DEFAULT', msg=ErrorType.CannotReconstruct)
        return
