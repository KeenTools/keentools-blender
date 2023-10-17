# -------
# KeenTools for Blender integration tests
# start it from commandline:
# blender -b -P /full_path_to/test_file.py
# -------
import unittest
import sys
import os
import numpy as np

import bpy

# Import test functions used in unit-tests started from any location
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import test_utils

from keentools.utils.kt_logging import KTLogger
from keentools.facebuilder.settings import model_type_callback, uv_items_callback
from keentools.utils import coords, materials
from keentools.addon_config import get_operator
from keentools.facebuilder_config import FBConfig, get_fb_settings
from keentools.facebuilder.fbloader import FBLoader
from keentools.facebuilder.pick_operator import reset_detected_faces, get_detected_faces


_log = KTLogger(__name__)


class TestConfig:
    facs_blendshapes_count = 51
    fb_mask_count = 9
    faces_on_test_render = 3
    skip_heavy_tests_flag = False
    heavy_tests = ('test_uv_switch', 'test_models_and_parts')

    @classmethod
    def skip_this_test(cls, name):
        return cls.skip_heavy_tests_flag and name in cls.heavy_tests


class DataHolder:
    image_files = []
    @classmethod
    def get_image_file_names(cls):
        return cls.image_files

    @classmethod
    def set_image_file_names(cls, image_files):
        cls.image_files = image_files


def _get_models():
    return [x[0] for x in model_type_callback(None, None)]


class FaceBuilderTest(unittest.TestCase):

    def _head_and_cameras(self):
        settings = get_fb_settings()
        self.assertEqual(0, len(settings.heads))
        test_utils.create_head()
        self.assertEqual(1, len(settings.heads))
        headnum = settings.get_last_headnum()
        # No cameras
        head = settings.get_head(headnum)
        self.assertTrue(head is not None)
        files = DataHolder.get_image_file_names()
        for filepath in files:
            test_utils.create_camera(headnum, filepath)
        # Cameras counter
        self.assertEqual(len(files), len(settings.get_head(headnum).cameras))

    def _head_cams_and_pins(self):
        self._head_and_cameras()
        settings = get_fb_settings()
        headnum = settings.get_last_headnum()
        camnum = settings.get_last_camnum(headnum)
        test_utils.select_camera(headnum, camnum)

        test_utils.pinmode_execute(headnum, camnum)

        brect = tuple(coords.get_camera_border(bpy.context.area))
        arect = (396.5, -261.9, 1189.5, 1147.9)
        test_utils.move_pin(793, 421, 651, 425, arect, brect, headnum, camnum)
        test_utils.move_pin(732, 478, 826, 510, arect, brect, headnum, camnum)
        test_utils.move_pin(542, 549, 639, 527, arect, brect, headnum, camnum)
        test_utils.move_pin(912, 412, 911, 388, arect, brect, headnum, camnum)
        test_utils.update_pins(headnum, camnum)
        test_utils.out_pinmode()
        # Pins count
        self.assertEqual(4, settings.get_camera(headnum, camnum).pins_count)

    def test_addon_on(self):
        test_utils.new_scene()
        settings = get_fb_settings()
        self.assertEqual(0, len(settings.heads))

    def test_create_head_and_cameras(self):
        test_utils.new_scene()
        self._head_and_cameras()

    def test_delete_cameras(self):
        test_utils.new_scene()
        self._head_and_cameras()
        settings = get_fb_settings()
        headnum = settings.get_last_headnum()

        filenames = DataHolder.get_image_file_names()
        self.assertEqual(len(filenames), len(settings.get_head(headnum).cameras))
        test_utils.delete_camera(headnum, 2)
        self.assertEqual(len(filenames) - 1, len(settings.get_head(headnum).cameras))
        test_utils.delete_camera(headnum, 2)
        self.assertEqual(len(filenames) - 2, len(settings.get_head(headnum).cameras))

    def test_move_pins(self):
        test_utils.new_scene()
        self._head_cams_and_pins()

    def test_wireframe_coloring(self):
        test_utils.new_scene()
        self._head_and_cameras()
        op = get_operator(FBConfig.fb_wireframe_color_idname)
        op('EXEC_DEFAULT', action='wireframe_green')

    def test_duplicate_and_reconstruct(self):
        test_utils.new_scene()
        self._head_and_cameras()
        settings = get_fb_settings()
        headnum = settings.get_last_headnum()
        head1 = settings.get_head(headnum)
        test_utils.deselect_all()
        test_utils.select_camera(headnum, 0)
        test_utils.out_pinmode()

        headobj = test_utils.select_by_headnum(headnum)
        bpy.ops.object.duplicate_move(
            OBJECT_OT_duplicate={"linked": False, "mode": 'TRANSLATION'},
            TRANSFORM_OT_translate={"value": (-4.0, 0, 0)})
        test_utils.save_scene(filename='before.blend')

        op = get_operator(FBConfig.fb_reconstruct_head_idname)
        op('EXEC_DEFAULT')
        headnum2 = settings.get_last_headnum()
        head2 = settings.get_head(headnum2)
        # Two heads in scene
        self.assertEqual(2, len(settings.heads))
        self.assertEqual(len(head1.cameras), len(head2.cameras))

    def test_change_camera_params(self):
        test_utils.new_scene()
        self._head_cams_and_pins()
        settings = get_fb_settings()
        headnum = settings.get_last_headnum()
        head = settings.get_head(headnum)
        camnum = head.get_last_camnum()
        camobj = head.get_camera(camnum).camobj

        new_focal = 35.0
        head.focal = new_focal
        self.assertEqual(new_focal, camobj.data.lens)
        new_focal = 18.0
        head.focal = new_focal
        self.assertEqual(new_focal, camobj.data.lens)
        new_sensor_width = 15
        head.sensor_width = new_sensor_width
        # Config.default_sensor_width instead cutom new_sensor_width!
        self.assertEqual(FBConfig.default_sensor_width, camobj.data.sensor_width)
        new_sensor_width = 20
        head.sensor_width = new_sensor_width
        self.assertEqual(FBConfig.default_sensor_width, camobj.data.sensor_width)

    def test_load_images_and_bake_texture(self):
        test_utils.new_scene()
        self._head_cams_and_pins()
        settings = get_fb_settings()

        dir = os.path.dirname(os.path.abspath(__file__))
        filename = os.path.join(dir, 'images/ale_white_24x16.jpg')
        headnum = 0
        camnum = 1
        res = test_utils.create_camera_from_image(
            headnum=headnum, camnum=camnum, filename=filename)
        self.assertEqual(res, True)
        head = settings.get_head(headnum)
        camera = head.get_camera(camnum)
        # Test EXIF read
        self.assertEqual(camera.exif.focal, 50.0)
        self.assertEqual(camera.exif.focal35mm, 75.0)

        camnum = 2
        filename = os.path.join(dir, 'images/ana_blue_24x16.tif')
        res = test_utils.create_camera_from_image(
            headnum=headnum, camnum=camnum, filename=filename)
        self.assertEqual(res, True)

        tex_name = materials.bake_tex(headnum=0, tex_name='bake_texture_name')
        self.assertTrue(tex_name is not None)

    def test_models_and_parts(self):
        if TestConfig.skip_this_test('test_models_and_parts'):
            return
        def _check_models(head):
            previous_polycount = 1.0e+6
            for level_of_detail in _get_models():
                head.model_type = level_of_detail
                poly_count = len(head.headobj.data.polygons)
                _log.output(f'Model_count mask {level_of_detail}: {poly_count}')
                self.assertTrue(previous_polycount > poly_count)
                previous_polycount = poly_count

        def _check_masks(head, fb_masks_count):
            max_poly_count = len(head.headobj.data.polygons)
            _log.output(f'Max_poly_count: {max_poly_count}')

            for i in range(len(head.masks)):
                head.masks[i] = False
                poly_count = len(head.headobj.data.polygons)
                _log.output(f'Poly_count mask {i}: {poly_count}')
                if i < TestConfig.fb_mask_count:
                    self.assertTrue(max_poly_count > poly_count)
                else:
                    self.assertTrue(max_poly_count == poly_count)
                head.masks[i] = True
                poly_count = len(head.headobj.data.polygons)
                self.assertTrue(max_poly_count == poly_count)

        test_utils.new_scene()
        self._head_cams_and_pins()
        settings = get_fb_settings()
        headnum = settings.get_last_headnum()
        head = settings.get_head(headnum)

        _check_models(head)

        for level_of_detail in _get_models():
            head.model_type = level_of_detail
            _check_masks(head, TestConfig.fb_mask_count)

    def test_create_blendshapes_and_animation(self):
        test_utils.new_scene()
        self._head_cams_and_pins()
        settings = get_fb_settings()
        headnum = settings.get_last_headnum()
        head = settings.get_head(headnum)
        headobj = head.headobj

        test_utils.create_blendshapes()
        self.assertTrue(headobj.data.shape_keys is not None)
        blendshapes = headobj.data.shape_keys.key_blocks
        self.assertEqual(len(blendshapes),
                         TestConfig.facs_blendshapes_count + 1)  # FACS + Basic

        test_utils.create_example_animation()
        self.assertTrue(headobj.data.shape_keys and
                        headobj.data.shape_keys.animation_data and \
                        headobj.data.shape_keys.animation_data.action)

        test_utils.delete_blendshapes()
        self.assertTrue(headobj.data.shape_keys is None)

    def test_uv_switch(self):
        if TestConfig.skip_this_test('test_uv_switch'):
            return
        def _get_uv_names():
            return [x[0] for x in uv_items_callback(None, None)]
        def _get_uvs_in_np_array(obj):
            uv_map = obj.data.uv_layers.active
            uv_count = len(uv_map.data)
            np_uvs = np.empty((uv_count, 2), dtype=np.float32)
            uv_map.data.foreach_get('uv', np.reshape(np_uvs, uv_count * 2))
            return np_uvs

        test_utils.new_scene()
        self._head_cams_and_pins()
        settings = get_fb_settings()
        headnum = settings.get_last_headnum()
        head = settings.get_head(headnum)
        headobj = head.headobj

        for level_of_detail in _get_models():
            head.model_type = level_of_detail

            previous = []
            for uv_name in _get_uv_names():
                head.tex_uv_shape = uv_name
                np_uvs = _get_uvs_in_np_array(headobj)
                for member in previous:
                    self.assertFalse(np.array_equal(np_uvs, member))
                previous.append(np_uvs)

    def test_detect_faces(self):
        test_utils.new_scene()
        self._head_and_cameras()
        fb = FBLoader.get_builder()
        self.assertTrue(fb.is_face_detector_available())
        settings = get_fb_settings()
        headnum = settings.get_last_headnum()
        head = settings.get_head(headnum)
        camnum = head.get_last_camnum()

        test_utils.select_camera(headnum, camnum - 1)
        reset_detected_faces()
        test_utils.pickmode_start(headnum=headnum, camnum=camnum - 1)
        faces = get_detected_faces()
        self.assertEqual(1, len(faces))

        test_utils.select_camera(headnum, camnum)
        reset_detected_faces()
        test_utils.pickmode_start(headnum=headnum, camnum=camnum)
        faces = get_detected_faces()
        self.assertEqual(TestConfig.faces_on_test_render, len(faces))
        for i in range(len(faces)):
            test_utils.pickmode_select(headnum=headnum, camnum=camnum,
                                       selected=i)
        test_utils.out_pinmode()


def prepare_test_environment():
    test_utils.clear_test_dir()
    test_utils.create_test_dir()
    images = test_utils.create_test_images()
    render_images = test_utils.create_head_images()
    test_utils.save_scene(filename='render.blend')
    DataHolder.set_image_file_names([image.filepath for image
                                     in images] + render_images)


if __name__ == "__main__":
    try:
        from teamcity import is_running_under_teamcity
        from teamcity.unittestpy import TeamcityTestRunner
        runner = TeamcityTestRunner()
        _log.info('Teamcity TeamcityTestRunner is active')
    except ImportError:
        _log.error('ImportError: Teamcity is not installed')
        runner = unittest.TextTestRunner()
        _log.error('Unittest TextTestRunner is active')
    except Exception:
        _log.error('Unhandled error with Teamcity')
        runner = unittest.TextTestRunner()
        _log.error('Unittest TextTestRunner is active')

    prepare_test_environment()

    # unittest.main()  # -- Doesn't work with Blender, so we use Suite
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(FaceBuilderTest)
    result = runner.run(suite)

    _log.info('Results: {}'.format(result))
    if len(result.errors) != 0 or len(result.failures) != 0:
        # For non-zero blender exit code in conjuction with command line option
        # --python-exit-code <code>
        raise Exception('Test errors: {} failures: {}'.format(result.errors,
                                                              result.failures))
