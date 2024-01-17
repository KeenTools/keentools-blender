from typing import Any, Tuple, List, Set
import os
import tempfile
import shutil
import numpy as np
import random
import math

import bpy

from keentools.utils.kt_logging import KTLogger
from keentools.addon_config import fb_settings, get_operator
from keentools.facebuilder_config import FBConfig
import keentools.utils.coords as coords
from keentools.facebuilder.fbloader import FBLoader
from keentools.facebuilder.interface.filedialog import load_single_image_file
from keentools.utils.images import assign_pixels_data
from keentools.utils.manipulate import deselect_all


_log = KTLogger(__name__)


_TEST_DIR: str = os.path.join(tempfile.gettempdir(), 'keentools_tests')
_log.output(f'_TEST_DIR: {_TEST_DIR}')


def test_dir() -> str:
    global _TEST_DIR
    return _TEST_DIR


def clear_test_dir() -> None:
    shutil.rmtree(test_dir(), ignore_errors=True)


def create_test_dir() -> str:
    dir_path = test_dir()
    os.makedirs(dir_path, exist_ok=True)
    return dir_path


def create_image(image_name: str, width: int = 1920, height: int = 1080,
                 color: Tuple = (0, 0, 0, 1)) -> Any:
    image = bpy.data.images.new(image_name, width=width, height=height,
                                alpha=True, float_buffer=False)
    rgba = np.full((height, width, len(color)), color, dtype=np.float32)
    assign_pixels_data(image.pixels, rgba.ravel())
    return image


def save_image(image: Any, file_format: str = 'JPEG') -> str:
    image.filepath_raw = os.path.join(test_dir(),
                                      image.name + '.' + file_format.lower())
    image.file_format = file_format
    image.save()
    _log.output(f'SAVED IMAGE: {image.file_format} {image.filepath}')
    return image.filepath


def random_color() -> Tuple:
    return (*[random.random() for _ in range(0, 3)], 1)


def create_test_images(count: int = 3, size: Tuple[int, int] = (1920, 1080),
                       image_name_template: str = 'hd_image') -> List:
    images = []
    for i in range(0, count):
        image_name = '{}{}'.format(image_name_template, i)
        image = create_image(image_name, size[0], size[1], random_color())
        save_image(image, file_format='JPEG')
        images.append(image)
    return images


def create_random_size_test_images(
        count: int = 3, width: Tuple[int, int] = (500, 3000),
        height: Tuple[int, int]=(400, 2400),
        image_name_template: str = 'random_image') -> List:
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


def select_by_headnum(headnum: int) -> Any:
    settings = fb_settings()
    headobj = settings.get_head(headnum).headobj
    headobj.select_set(state=True)
    bpy.context.view_layer.objects.active = headobj
    return headobj


def out_pinmode() -> None:
    settings = fb_settings()
    FBLoader.out_pinmode(settings.current_headnum)


def update_pins(headnum: int, camnum: int) -> None:
    FBLoader.update_camera_pins_count(headnum, camnum)


# --------------
# Operators call
def create_head() -> None:
    # Create Head
    op = get_operator(FBConfig.fb_add_head_operator_idname)
    op('EXEC_DEFAULT')


def create_empty_camera(headnum: int) -> None:
    FBLoader.add_new_camera(headnum, None)


def create_camera_from_image(headnum: int, camnum: int, filename: str) -> bool:
    return load_single_image_file(headnum, camnum, filename)


def create_camera(headnum: int, filepath: str) -> None:
    filename = os.path.basename(filepath)
    dir = os.path.dirname(filepath)
    op = get_operator(FBConfig.fb_multiple_filebrowser_idname)
    op('EXEC_DEFAULT', headnum=headnum, directory=dir,
       files=({'name': filename},))


def delete_camera(headnum: int, camnum: int) -> None:
    op = get_operator(FBConfig.fb_delete_camera_idname)
    op('EXEC_DEFAULT', headnum=headnum, camnum=camnum)


def move_pin(start_x: int, start_y: int, end_x: int, end_y: int,
             arect: Tuple, brect: Tuple,
             headnum: int = 0, camnum: int = 0) -> None:
    # Registered Operator call
    op = get_operator(FBConfig.fb_movepin_idname)
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


def select_camera(headnum: int = 0, camnum: int = 0) -> None:
    op = get_operator(FBConfig.fb_select_camera_idname)
    op('EXEC_DEFAULT', headnum=headnum, camnum=camnum)


def change_scene_camera(headnum: int, camnum: int) -> None:
    settings = fb_settings()
    camera = settings.get_camera(headnum, camnum)
    bpy.context.scene.camera = camera.camobj


def wireframe_coloring(action: str = 'wireframe_green') -> None:
    op = get_operator(FBConfig.fb_wireframe_color_idname)
    op('EXEC_DEFAULT', action=action)


def new_scene() -> None:
    bpy.ops.scene.new(type='NEW')


def save_scene(filename: str) -> None:
    filepath = os.path.join(test_dir(), filename)
    bpy.ops.wm.save_mainfile(filepath=filepath, check_existing=False)


def load_scene(filename: str) -> None:
    filepath = os.path.join(test_dir(), filename)
    bpy.ops.wm.open_mainfile(filepath=filepath)


def create_blendshapes() -> None:
    op = get_operator(FBConfig.fb_create_blendshapes_idname)
    op('EXEC_DEFAULT')


def delete_blendshapes() -> None:
    op = get_operator(FBConfig.fb_delete_blendshapes_idname)
    op('EXEC_DEFAULT')


def create_example_animation() -> None:
    op = get_operator(FBConfig.fb_create_example_animation_idname)
    op('EXEC_DEFAULT')


def pickmode_start(headnum: int, camnum: int) -> None:
    op = get_operator(FBConfig.fb_pickmode_starter_idname)
    op('EXEC_DEFAULT', headnum=headnum, camnum=camnum)


def pickmode_select(headnum: int, camnum: int, selected: int) -> None:
    op = get_operator(FBConfig.fb_pickmode_idname)
    op('EXEC_DEFAULT', headnum=headnum, camnum=camnum, selected=selected)


def pinmode_execute(headnum: int, camnum: int) -> None:
    op = get_operator(FBConfig.fb_pinmode_idname)
    op('EXEC_DEFAULT', headnum=headnum, camnum=camnum)


def create_head_images() -> List:
    new_scene()
    create_head()
    settings = fb_settings()
    headnum = settings.get_last_headnum()
    head = settings.get_head(headnum)
    headobj = head.headobj
    create_empty_camera(headnum)
    camnum = head.get_last_camnum()

    change_scene_camera(headnum, camnum)

    headobj.rotation_euler = (math.pi * 0.1, 0, math.pi * 0.1)
    headobj.location = (0, 10, 0)

    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 32  # low quality
    scene.render.image_settings.file_format = 'JPEG'
    scene.world = bpy.data.worlds['World']
    scene.world.color = (0.9, 0.9, 0.9)
    bpy.ops.object.light_add(type='SUN', align='WORLD', location=(0, 0, 0),
                             rotation=(math.pi * 0.45, 0.0, math.pi * 0.3),
                             scale=(1, 1, 1))
    deselect_all()

    filename1 = 'head_render1.jpg'
    filepath1 = os.path.join(test_dir(), filename1)
    scene.render.filepath = filepath1
    bpy.ops.render.render(write_still=True)
    _log.info(f'Rendered by {scene.render.engine}: {filepath1}')

    headobj = select_by_headnum(headnum)
    bpy.ops.object.duplicate_move(
        OBJECT_OT_duplicate={'linked': False, 'mode': 'TRANSLATION'},
        TRANSFORM_OT_translate={'value': (-4.0, 0, 0)})

    bpy.ops.object.duplicate_move(
        OBJECT_OT_duplicate={'linked': False, 'mode': 'TRANSLATION'},
        TRANSFORM_OT_translate={'value': (6.0, 0, 0)})

    filename2 = 'head_render2.jpg'
    filepath2 = os.path.join(test_dir(), filename2)
    scene.render.filepath = filepath2
    bpy.ops.render.render(write_still=True)
    _log.info(f'Rendered by {scene.render.engine}: {filepath2}')
    return [filepath1, filepath2]
