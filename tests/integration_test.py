# -------
# KeenTools for Blender integration tests
# start it from commandline:
# blender -b -P /full_path_to/test_file.py
# -------
import unittest
import sys
import os
import logging

import bpy

# Import test functions used in unit-tests started from any location
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import test_utils

import keentools_facebuilder
from keentools_facebuilder.utils import coords, materials
from keentools_facebuilder.config import Config, get_main_settings, \
    get_operator


class DataHolder:
    image_files = []
    @classmethod
    def get_image_file_names(cls):
        return cls.image_files

    @classmethod
    def set_image_file_names(cls, image_files):
        cls.image_files = image_files


class FaceBuilderTest(unittest.TestCase):

    def _head_and_cameras(self):
        settings = get_main_settings()
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
        self.assertEqual(3, len(settings.get_head(headnum).cameras))

    def _head_cams_and_pins(self):
        self._head_and_cameras()
        settings = get_main_settings()
        headnum = settings.get_last_headnum()
        camnum = settings.get_last_camnum(headnum)
        test_utils.select_camera(headnum, camnum)

        brect = tuple(coords.get_camera_border(bpy.context))
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
        settings = get_main_settings()
        self.assertEqual(0, len(settings.heads))

    def test_create_head_and_cameras(self):
        test_utils.new_scene()
        self._head_and_cameras()

    def test_delete_cameras(self):
        test_utils.new_scene()
        self._head_and_cameras()
        settings = get_main_settings()
        headnum = settings.get_last_headnum()
        test_utils.create_empty_camera(headnum)
        self.assertEqual(4, len(settings.get_head(headnum).cameras))
        test_utils.delete_camera(headnum, 2)
        self.assertEqual(3, len(settings.get_head(headnum).cameras))
        test_utils.delete_camera(headnum, 2)
        self.assertEqual(2, len(settings.get_head(headnum).cameras))

    def test_move_pins(self):
        test_utils.new_scene()
        self._head_cams_and_pins()

    def test_wireframe_coloring(self):
        test_utils.new_scene()
        self._head_and_cameras()
        op = get_operator(Config.fb_wireframe_color_idname)
        op('EXEC_DEFAULT', action='wireframe_green')

    def test_duplicate_and_reconstruct(self):
        test_utils.new_scene()
        self._head_and_cameras()
        settings = get_main_settings()
        headnum = settings.get_last_headnum()
        test_utils.deselect_all()
        test_utils.select_camera(headnum, 0)
        test_utils.out_pinmode()

        headobj = test_utils.select_by_headnum(headnum)
        bpy.ops.object.duplicate_move(
            OBJECT_OT_duplicate={"linked": False, "mode": 'TRANSLATION'},
            TRANSFORM_OT_translate={"value": (-4.0, 0, 0)})
        test_utils.save_scene(filename='before.blend')

        op = get_operator(Config.fb_reconstruct_head_idname)
        op('EXEC_DEFAULT')
        headnum2 = settings.get_last_headnum()
        head_new = settings.get_head(headnum2)
        # Two heads in scene
        self.assertEqual(1, settings.get_last_headnum())
        # Three cameras created
        self.assertEqual(2, head_new.get_last_camnum())

    def test_change_camera_params(self):
        test_utils.new_scene()
        self._head_cams_and_pins()
        settings = get_main_settings()
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
        self.assertEqual(Config.default_sensor_width, camobj.data.sensor_width)
        new_sensor_width = 20
        head.sensor_width = new_sensor_width
        self.assertEqual(Config.default_sensor_width, camobj.data.sensor_width)

    def test_load_images_and_bake_texture(self):
        test_utils.new_scene()
        self._head_cams_and_pins()
        settings = get_main_settings()

        dir = os.path.dirname(os.path.abspath(__file__))
        filename = os.path.join(dir, 'images/ale_white_24x16.jpg')
        headnum = 0
        camnum = 1
        res = test_utils.create_camera_from_image(
            headnum=headnum, camnum=camnum, filename=filename)
        self.assertEqual(res, {'FINISHED'})
        head = settings.get_head(headnum)
        camera = head.get_camera(camnum)
        # Test EXIF read
        self.assertEqual(camera.exif.focal, 50.0)
        self.assertEqual(camera.exif.focal35mm, 75.0)

        camnum = 2
        filename = os.path.join(dir, 'images/ana_blue_24x16.tif')
        res = test_utils.create_camera_from_image(
            headnum=headnum, camnum=camnum, filename=filename)
        self.assertEqual(res, {'FINISHED'})

        tex_name = materials.bake_tex(headnum=0, tex_name='bake_texture_name')
        self.assertTrue(tex_name is not None)

    def test_models_and_parts(self):
        def _get_models():
            return [x[0] for x in keentools_facebuilder.settings.model_type_callback(None, None)]

        def _check_models(head):
            previous_polycount = 1.0e+6
            for level_of_detail in _get_models():
                head.model_type = level_of_detail
                poly_count = len(head.headobj.data.polygons)
                logger.debug('Model_count mask {}: {}'.format(level_of_detail,
                                                              poly_count))
                self.assertTrue(previous_polycount > poly_count)
                previous_polycount = poly_count

        def _check_masks(head, fb_masks_count):
            max_poly_count = len(head.headobj.data.polygons)
            logger.debug('Max_poly_count: {}'.format(max_poly_count))

            for i in range(len(head.masks)):
                head.masks[i] = False
                poly_count = len(head.headobj.data.polygons)
                logger.debug('Poly_count mask {}: {}'.format(i, poly_count))
                if i < FB_MASKS_COUNT:
                    self.assertTrue(max_poly_count > poly_count)
                else:
                    self.assertTrue(max_poly_count == poly_count)
                head.masks[i] = True
                poly_count = len(head.headobj.data.polygons)
                self.assertTrue(max_poly_count == poly_count)

        logger = logging.getLogger(__name__)
        test_utils.new_scene()
        self._head_cams_and_pins()
        settings = get_main_settings()
        headnum = settings.get_last_headnum()
        head = settings.get_head(headnum)

        _check_models(head)

        FB_MASKS_COUNT = 8
        for level_of_detail in _get_models():
            head.model_type = level_of_detail
            _check_masks(head, FB_MASKS_COUNT)

    def test_create_blendshapes_and_animation(self):
        test_utils.new_scene()
        self._head_cams_and_pins()
        settings = get_main_settings()
        headnum = settings.get_last_headnum()
        head = settings.get_head(headnum)
        headobj = head.headobj

        test_utils.create_blendshapes()
        self.assertTrue(headobj.data.shape_keys is not None)
        blendshapes = headobj.data.shape_keys.key_blocks
        self.assertEqual(len(blendshapes), 52)  # 51 FACS + Basic

        test_utils.create_example_animation()
        self.assertTrue(headobj.data.shape_keys and
                        headobj.data.shape_keys.animation_data and \
                        headobj.data.shape_keys.animation_data.action)

        test_utils.delete_blendshapes()
        self.assertTrue(headobj.data.shape_keys is None)


def prepare_test_environment():
    test_utils.clear_test_dir()
    test_utils.create_test_dir()
    images = test_utils.create_test_images()
    DataHolder.set_image_file_names([image.filepath for image in images])


if __name__ == "__main__":
    prepare_test_environment()

    # unittest.main()  # -- Doesn't work with Blender, so we use Suite
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(FaceBuilderTest)
    unittest.TextTestRunner().run(suite)
