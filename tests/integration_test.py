# -------
# KeenTools for Blender integration tests
# start it from commandline:
# blender -b -P /full_path_to/test_file.py
# -------
import unittest

import bpy
import sys
import os

# Import test functions used in unit-tests started from any location
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import test_utils
# import tests.test_utils as test_utils


from keentools_facebuilder.utils import coords, materials
from keentools_facebuilder.config import Config, get_main_settings, \
    get_operators


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
        test_utils.create_empty_camera(headnum)
        test_utils.create_empty_camera(headnum)
        test_utils.create_empty_camera(headnum)
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
        op = getattr(
            bpy.ops.object, Config.fb_main_wireframe_color_callname)
        op('EXEC_DEFAULT', action='wireframe_green')

    def test_duplicate_and_reconstruct(self):
        test_utils.new_scene()
        self._head_and_cameras()
        settings = get_main_settings()
        headnum = settings.get_last_headnum()
        test_utils.deselect_all()
        headobj = test_utils.select_by_headnum(headnum)
        bpy.ops.object.duplicate_move(
            OBJECT_OT_duplicate={"linked": False, "mode": 'TRANSLATION'},
            TRANSFORM_OT_translate={"value": (-3.0, 0, 0)})
        op = getattr(get_operators(), Config.fb_actor_callname)
        op('EXEC_DEFAULT', action='reconstruct_by_head', headnum=-1, camnum=-1)
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
        self.assertEqual(new_sensor_width, camobj.data.sensor_width)
        new_sensor_width = 20
        head.sensor_width = new_sensor_width
        self.assertEqual(new_sensor_width, camobj.data.sensor_width)

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
        # Test EXIF read
        self.assertEqual(head.exif.focal, 50.0)
        self.assertEqual(head.exif.focal35mm, 75.0)

        camnum = 2
        filename = os.path.join(dir, 'images/ana_blue_24x16.tif')
        res = test_utils.create_camera_from_image(
            headnum=headnum, camnum=camnum, filename=filename)
        self.assertEqual(res, {'FINISHED'})

        tex_name = materials.bake_tex(headnum=0, tex_name='bake_texture_name')
        self.assertTrue(tex_name is not None)


if __name__ == "__main__":
    # unittest.main()  # -- Doesn't work with Blender, so we use Suite
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(FaceBuilderTest)
    unittest.TextTestRunner().run(suite)
