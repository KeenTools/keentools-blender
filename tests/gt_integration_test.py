import unittest
import sys
import os
import logging
import math
from typing import Any

import bpy

from keentools.utils.materials import get_mat_by_name, assign_material_to_object, get_shader_node
from keentools.addon_config import get_operator
from keentools.geotracker_config import GTConfig
from keentools.utils.animation import create_locrot_keyframe
from keentools.utils.bpy_common import bpy_current_frame, bpy_set_current_frame, bpy_scene
from keentools.utils.coords import update_depsgraph
from keentools.geotracker_config import get_gt_settings, get_current_geotracker_item


_logger: Any = logging.getLogger(__name__)


def _log_output(message: str) -> None:
    global _logger
    _logger.info(message)


def _log_error(message: str) -> None:
    global _logger
    _logger.error(message)


class GTTestConfig:
    cube_render_filename = 'cube_render_'
    cube_render_scene_filename = 'cube_render.blend'
    cube_frames_dir = 'cube_frames'
    cube_start_frame = 1
    cube_end_frame = 10
    cube_precalc_filename = 'cube.precalc'


_dirname: str = os.path.dirname(os.path.abspath(__file__))
_log_output(f'GT TEST DIRNAME: {_dirname}')

if _dirname not in sys.path:
    sys.path.append(_dirname)
sys.path.append(_dirname)

import test_utils


def create_new_default_scene():
    bpy.ops.wm.read_homefile(app_template="")


def create_checker_material():
    tex_size = 2048
    mat = get_mat_by_name('checker_material')
    tex = bpy.data.images.new('ch', tex_size, tex_size)
    tex.generated_type = 'UV_GRID'
    principled_node = get_shader_node(
        mat, 'BSDF_PRINCIPLED', 'ShaderNodeBsdfPrincipled')
    image_node = get_shader_node(
        mat, 'TEX_IMAGE', 'ShaderNodeTexImage')
    image_node.image = tex
    image_node.location = (-350, 0)
    principled_node.inputs['Specular'].default_value = 0.0
    mat.node_tree.links.new(
        image_node.outputs['Color'],
        principled_node.inputs['Base Color'])
    return mat


def create_geotracker():
    op = get_operator(GTConfig.gt_create_geotracker_idname)
    op('EXEC_DEFAULT')


def new_scene():
    bpy.ops.wm.read_homefile(app_template='')


def cube_render_frames_dir():
    return os.path.join(test_utils.test_dir(), GTTestConfig.cube_frames_dir)


def create_moving_cube_scene():
    obj = bpy.data.objects['Cube']
    mat = create_checker_material()
    assign_material_to_object(obj, mat)
    bpy_set_current_frame(GTTestConfig.cube_start_frame)
    create_locrot_keyframe(obj)
    bpy_set_current_frame(GTTestConfig.cube_end_frame)
    obj.location = (-5, 10, -3)
    obj.rotation_euler = (0, 0, math.pi / 4)
    update_depsgraph()
    create_locrot_keyframe(obj)
    scene = bpy_scene()
    scene.frame_end = GTTestConfig.cube_end_frame

    scene.render.image_settings.file_format = 'JPEG'
    scene.world = bpy.data.worlds['World']
    scene.world.color = (0.9, 0.9, 0.9)

    filepath = os.path.join(cube_render_frames_dir(),
                            GTTestConfig.cube_render_filename)
    scene.render.filepath = filepath
    bpy.ops.render.render(animation=True, write_still=True)
    _log_output(f'Rendered by {scene.render.engine}: {filepath}')


def gt_create_geotracker():
    op = get_operator(GTConfig.gt_create_geotracker_idname)
    op('EXEC_DEFAULT')


def gt_load_movieclip(dir_path, filename):
    op = get_operator(GTConfig.gt_multiple_filebrowser_idname)
    op('EXEC_DEFAULT', directory=dir_path, files=[{'name':filename}], num=0)


def prepare_gt_test_environment():
    global _timer_var
    test_utils.clear_test_dir()
    dir_path = test_utils.create_test_dir()
    _log_output(f'test_dir: {test_utils.test_dir()}')
    new_scene()
    create_moving_cube_scene()
    test_utils.save_scene(filename=GTTestConfig.cube_render_scene_filename)

    new_scene()
    bpy.data.objects['Cube'].select_set(True)
    bpy.data.objects['Camera'].select_set(True)
    gt_create_geotracker()
    gt_load_movieclip(cube_render_frames_dir(),
                      f'{GTTestConfig.cube_render_filename}0001.jpg')

    try:
        op = get_operator(GTConfig.gt_choose_precalc_file_idname)
        op('EXEC_DEFAULT',
           filepath=os.path.join(dir_path, GTTestConfig.cube_precalc_filename))
    except Exception as err:
        _log_error(f'Choose precalc: {str(err)}')

    geotracker = get_current_geotracker_item()
    geotracker.precalc_start = GTTestConfig.cube_start_frame
    geotracker.precalc_end = GTTestConfig.cube_end_frame

    test_utils.save_scene(filename='geotracker1.blend')

    op = get_operator(GTConfig.gt_actor_idname)
    op('EXEC_DEFAULT', action='create_precalc')

    settings = get_gt_settings()
    while settings.precalc_mode:
        pass

    test_utils.save_scene(filename='geotracker2.blend')


class GeoTrackerTest(unittest.TestCase):
    pass


if __name__ == '__main__':
    try:
        from teamcity import is_running_under_teamcity
        from teamcity.unittestpy import TeamcityTestRunner
        runner = TeamcityTestRunner()
        _log_output('Teamcity TeamcityTestRunner is active')
    except ImportError:
        _log_error('ImportError: Teamcity is not installed')
        runner = unittest.TextTestRunner()
        _log_error('Unittest TextTestRunner is active')
    except Exception:
        _log_error('Unhandled error with Teamcity')
        runner = unittest.TextTestRunner()
        _log_error('Unittest TextTestRunner is active')

    prepare_gt_test_environment()

    # unittest.main()  # -- Doesn't work with Blender, so we use Suite
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(GeoTrackerTest)
    result = runner.run(suite)

    _log_output('Results: {}'.format(result))
    if len(result.errors) != 0 or len(result.failures) != 0:
        # For non-zero blender exit code in conjuction with command line option
        # --python-exit-code <code>
        raise Exception(f'GeoTracker Test errors: {result.errors} '
                        f'failures: {result.failures}')
