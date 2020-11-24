import os
import tempfile
import shutil
import logging
import numpy as np
import random

import bpy
import keentools_facebuilder
from keentools_facebuilder.config import Config, get_main_settings, \
    get_operator
import keentools_facebuilder.utils.coords as coords
from keentools_facebuilder.fbloader import FBLoader


_TEST_DIR = os.path.join(tempfile.gettempdir(), 'keentools_tests')


def test_dir():
    global _TEST_DIR
    return _TEST_DIR


def clear_test_dir():
    shutil.rmtree(test_dir(), ignore_errors=True)


def create_test_dir():
    os.makedirs(test_dir(), exist_ok=True)


def create_image(image_name, width=1920, height=1080, color=(0, 0, 0, 1)):
    image = bpy.data.images.new(image_name, width=width, height=height,
                                alpha=True, float_buffer=False)
    rgba = np.full((height, width, len(color)), color)
    image.pixels[:] = rgba.ravel()
    return image


def save_image(image, file_format='JPEG'):
    image.filepath_raw = os.path.join(test_dir(),
                                      image.name + '.' + file_format.lower())
    image.file_format = file_format
    image.save()
    logger = logging.getLogger(__name__)
    logger.debug('SAVED IMAGE: {} {}'.format(image.file_format,
                                             image.filepath))
    return image.filepath


def random_color():
    return (*[random.random() for _ in range(0, 3)], 1)


def create_test_images(count=3, size=(1920, 1080),
                       image_name_template='hd_image'):
    images = []
    for i in range(0, count):
        image_name = '{}{}'.format(image_name_template, i)
        image = create_image(image_name, size[0], size[1], random_color())
        save_image(image, file_format='JPEG')
        images.append(image)
    return images


def create_random_size_test_images(count=3,
                                   width=(500, 3000), height=(400, 2400),
                                   image_name_template='random_image'):
    images = []
    for i in range(0, count):
        image_name = '{}{}'.format(image_name_template, i)
        image = create_image(image_name,
                             random.randint(width[0], width[1]),
                             random.randint(height[0], height[1]),
                             random_color())
        save_image(image, file_format='JPEG')
        images.append(image)
    return images


def select_by_headnum(headnum):
    settings = get_main_settings()
    headobj = settings.get_head(headnum).headobj
    headobj.select_set(state=True)
    bpy.context.view_layer.objects.active = headobj
    return headobj


def out_pinmode():
    settings = get_main_settings()
    FBLoader.out_pinmode(settings.current_headnum)


def update_pins(headnum, camnum):
    FBLoader.update_pins_count(headnum, camnum)


# --------------
# Operators call
def create_head():
    # Create Head
    op = get_operator(Config.fb_add_head_operator_idname)
    op('EXEC_DEFAULT')


def create_empty_camera(headnum):
    FBLoader.add_new_camera(headnum, None)


def create_camera_from_image(headnum, camnum, filename):
    return keentools_facebuilder.interface.filedialog.load_single_image_file(
        headnum, camnum, filename)


def create_camera(headnum, filepath):
    filename = os.path.basename(filepath)
    dir = os.path.dirname(filepath)
    op = get_operator(Config.fb_multiple_filebrowser_idname)
    op('EXEC_DEFAULT', headnum=headnum, directory=dir,
       files=({'name': filename},))


def delete_camera(headnum, camnum):
    op = get_operator(Config.fb_delete_camera_idname)
    op('EXEC_DEFAULT', headnum=headnum, camnum=camnum)


def move_pin(start_x, start_y, end_x, end_y, arect, brect,
             headnum=0, camnum=0):
    # Registered Operator call
    op = get_operator(Config.fb_movepin_idname)
    # Move pin
    x, y = coords.region_to_image_space(start_x, start_y, *arect)
    px, py = coords.image_space_to_region(x, y, *brect)
    op('EXEC_DEFAULT', headnum=headnum, camnum=camnum,
       pinx=px, piny=py, test_action="add_pin")

    x, y = coords.region_to_image_space(end_x, end_y, *arect)
    px, py = coords.image_space_to_region(x, y, *brect)
    op('EXEC_DEFAULT', headnum=headnum, camnum=camnum,
       pinx=px, piny=py, test_action="mouse_move")

    # Stop pin
    op('EXEC_DEFAULT', headnum=headnum, camnum=camnum,
       pinx=px, piny=py, test_action="mouse_release")


def select_camera(headnum=0, camnum=0):
    op = get_operator(Config.fb_select_camera_idname)
    op('EXEC_DEFAULT', headnum=headnum, camnum=camnum)


def deselect_all():
    bpy.ops.object.select_all(action='DESELECT')


def wireframe_coloring(action='wireframe_green'):
    op = get_operator(Config.fb_wireframe_color_idname)
    op('EXEC_DEFAULT', action=action)


def new_scene():
    bpy.ops.scene.new(type='NEW')


def save_scene(filename):
    filepath = os.path.join(test_dir(), filename)
    bpy.ops.wm.save_mainfile(filepath=filepath, check_existing=False)
