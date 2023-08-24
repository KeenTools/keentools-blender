import unittest
import sys
import os
import math
from typing import Any
import time

import bpy
from mathutils import Vector

from keentools.utils.kt_logging import KTLogger
from keentools.utils.materials import get_mat_by_name, assign_material_to_object, get_shader_node
from keentools.addon_config import get_operator
from keentools.geotracker_config import GTConfig
from keentools.utils.animation import create_locrot_keyframe
from keentools.utils.bpy_common import (bpy_current_frame,
                                        bpy_set_current_frame,
                                        bpy_scene,
                                        update_depsgraph)
from keentools.geotracker_config import get_gt_settings, get_current_geotracker_item
from keentools.geotracker.gtloader import GTLoader
from keentools.utils.ui_redraw import get_areas_by_type


_log = KTLogger(__name__)


class GTTestConfig:
    cube_render_filename = 'cube_render_'
    cube_render_scene_filename = 'cube_render.blend'
    cube_frames_dir = 'cube_frames'
    cube_start_frame = 1
    cube_end_frame = 14
    cube_frames_count = cube_end_frame - cube_start_frame + 1
    cube_max_precalc_time_per_frame = 5.0
    cube_precalc_time_limit = cube_frames_count * cube_max_precalc_time_per_frame
    cube_max_tracking_time_per_frame = 2.0
    cube_tracking_time_limit = cube_frames_count * cube_max_tracking_time_per_frame
    cube_precalc_filename = 'cube.precalc'
    cube_start_location = Vector((0.0, 0.0, 0.0))
    cube_start_rotation = Vector((0.0, 0.0, 0.0))
    cube_end_location = Vector((-5.0, 10.0, -3.0))
    cube_end_rotation = Vector((0.0, 0.0, math.pi / 4.0))
    cube_location_tolerance = 0.3
    cube_moving_scene_filename = 'gt1_moving_cube.blend'
    cube_precalc_scene_filename = 'gt2_precalc_calculated.blend'
    cube_tracked_scene_filename = 'gt3_cube_tracked.blend'


def add_test_utils_path() -> None:
    _dirname: str = os.path.dirname(os.path.abspath(__file__))
    _log.output(f'GT TEST DIRNAME: {_dirname}')

    if _dirname not in sys.path:
        sys.path.append(_dirname)
        _log.output(f'sys.path: {sys.path}')


add_test_utils_path()
import test_utils


def create_new_default_scene() -> None:
    bpy.ops.wm.read_homefile(app_template="")


def create_checker_material() -> Any:
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


def create_geotracker() -> None:
    op = get_operator(GTConfig.gt_create_geotracker_idname)
    op('EXEC_DEFAULT')


def new_scene() -> None:
    bpy.ops.wm.read_homefile(app_template='')


def cube_render_frames_dir() -> str:
    return os.path.join(test_utils.test_dir(), GTTestConfig.cube_frames_dir)


def create_moving_cube_scene() -> None:
    obj = bpy.data.objects['Cube']
    mat = create_checker_material()
    assign_material_to_object(obj, mat)
    bpy_set_current_frame(GTTestConfig.cube_start_frame)
    obj.location = GTTestConfig.cube_start_location
    obj.rotation_euler = GTTestConfig.cube_start_rotation
    update_depsgraph()
    create_locrot_keyframe(obj)
    bpy_set_current_frame(GTTestConfig.cube_end_frame)
    obj.location = GTTestConfig.cube_end_location
    obj.rotation_euler = GTTestConfig.cube_end_rotation
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
    _log.output(f'Rendered by {scene.render.engine}: {filepath}')


def gt_create_geotracker() -> None:
    op = get_operator(GTConfig.gt_create_geotracker_idname)
    op('EXEC_DEFAULT')


def gt_load_movieclip(dir_path: str, filename: str) -> None:
    op = get_operator(GTConfig.gt_sequence_filebrowser_idname)
    op('EXEC_DEFAULT', directory=dir_path, files=[{'name':filename}])


def fake_pinmode_on() -> None:
    settings = get_gt_settings()
    settings.pinmode = True
    settings.user_interrupts = False


def fake_viewport_work_area() -> None:
    pairs = get_areas_by_type(area_type='VIEW_3D')
    area, _ = pairs[0]
    vp = GTLoader.viewport()
    vp.set_work_area(area)


def wait_for_precalc_end(time_limit: float=GTTestConfig.cube_precalc_time_limit) -> None:
    settings = get_gt_settings()
    start_time = time.time()
    prev_time = start_time
    overall_time = 0.0
    output_status_delta_time = 2.0

    while settings.is_calculating():
        current_time = time.time()
        overall_time = current_time - start_time
        if current_time - prev_time > output_status_delta_time:
            _log.output(f'precalc calculating... {overall_time:.2f} sec.')
            prev_time = current_time
        if overall_time > time_limit:
            settings.user_interrupts = True  # Stop background process
            raise Exception('Too long precalc calculation')
    _log.output(f'precalc time: {overall_time}')


def wait_for_tracking_end(time_limit: float=GTTestConfig.cube_tracking_time_limit) -> None:
    settings = get_gt_settings()
    start_time = time.time()
    prev_time = start_time
    overall_time = 0.0
    output_status_delta_time = 0.5

    while settings.is_calculating():
        current_time = time.time()
        overall_time = current_time - start_time
        if current_time - prev_time > output_status_delta_time:
            _log.output(f'Tracking calculating... {overall_time:.2f} sec.')
            prev_time = current_time
        if overall_time > time_limit:
            settings.user_interrupts = True  # Stop background process
            raise Exception('Too long tracking calculation')
    _log.output(f'tracking time: {overall_time}')


def prepare_gt_test_environment() -> None:
    test_utils.clear_test_dir()
    dir_path = test_utils.create_test_dir()
    _log.output(f'test_dir: {test_utils.test_dir()}')
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
        _log.error(f'Choose precalc: {str(err)}')

    geotracker = get_current_geotracker_item()
    geotracker.precalc_start = GTTestConfig.cube_start_frame
    geotracker.precalc_end = GTTestConfig.cube_end_frame
    geotracker.precalcless = False

    test_utils.save_scene(filename=GTTestConfig.cube_moving_scene_filename)

    _log.output('Start precalc')
    op = get_operator(GTConfig.gt_create_precalc_idname)
    op('EXEC_DEFAULT')
    wait_for_precalc_end()
    test_utils.save_scene(filename=GTTestConfig.cube_precalc_scene_filename)

    _log.output('Start tracking')
    fake_pinmode_on()
    fake_viewport_work_area()
    op = get_operator(GTConfig.gt_add_keyframe_idname)
    op('EXEC_DEFAULT')

    op = get_operator(GTConfig.gt_track_to_end_idname)
    op('EXEC_DEFAULT')
    wait_for_tracking_end()
    test_utils.save_scene(filename=GTTestConfig.cube_tracked_scene_filename)


class GeoTrackerTest(unittest.TestCase):
    def test_addon_on(self) -> None:
        new_scene()
        settings = get_gt_settings()
        self.assertEqual(0, len(settings.geotrackers))

    def test_tracked_cube(self) -> None:
        new_scene()
        test_utils.load_scene(GTTestConfig.cube_tracked_scene_filename)
        obj = bpy.data.objects['Cube']

        bpy_set_current_frame(GTTestConfig.cube_start_frame)
        _log.output(f'Cube location: {obj.location}')
        loc_diff = (obj.location - GTTestConfig.cube_start_location).length
        _log.output(f'Cube location diff: {loc_diff}')
        assert loc_diff < GTTestConfig.cube_location_tolerance

        bpy_set_current_frame(GTTestConfig.cube_end_frame)
        _log.output(f'Cube location: {obj.location}')
        loc_diff = (obj.location - GTTestConfig.cube_end_location).length
        _log.output(f'Cube location diff: {loc_diff}')
        assert loc_diff < GTTestConfig.cube_location_tolerance


if __name__ == '__main__':
    try:
        from teamcity import is_running_under_teamcity
        from teamcity.unittestpy import TeamcityTestRunner
        runner = TeamcityTestRunner()
        _log.output('Teamcity TeamcityTestRunner is active')
    except ImportError:
        _log.error('ImportError: Teamcity is not installed')
        runner = unittest.TextTestRunner()
        _log.error('Unittest TextTestRunner is active')
    except Exception:
        _log.error('Unhandled error with Teamcity')
        runner = unittest.TextTestRunner()
        _log.error('Unittest TextTestRunner is active')

    try:
        prepare_gt_test_environment()
    except Exception as err:
        _log.error(f'Preparing environment exception: \n{str(err)}')
        raise Exception('GeoTracker Test failed on scene preparing')

    # unittest.main()  # -- Doesn't work with Blender, so we use Suite
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(GeoTrackerTest)
    result = runner.run(suite)

    _log.output('Results: {}'.format(result))
    if len(result.errors) != 0 or len(result.failures) != 0:
        # For non-zero blender exit code in conjuction with command line option
        # --python-exit-code <code>
        raise Exception(f'GeoTracker Test errors: {result.errors} '
                        f'failures: {result.failures}')
