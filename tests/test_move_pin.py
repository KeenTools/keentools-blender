import bpy
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import test_funcs

from keentools_facebuilder.utils import manipulate, coords
from keentools_facebuilder.config import Config

# -------
# Tests
# -------
def test_print_work():
    print("WORK")


def test_create_head_and_cameras():
    test_funcs.create_head()
    headnum = test_funcs.get_last_headnum()
    test_funcs.create_empty_camera(headnum)
    test_funcs.create_empty_camera(headnum)
    test_funcs.create_empty_camera(headnum)


def test_delete_last_camera():
    headnum = test_funcs.get_last_headnum()
    print("HN", headnum)
    assert(headnum >= 0)
    camnum = test_funcs.get_last_camnum(headnum)
    print("CN", camnum)
    assert(camnum >= 0)
    test_funcs.delete_camera(headnum, camnum)


def test_move_pins():
    # test_create_head_and_cameras()
    # Switch to PinMode
    test_funcs.select_camera(0, 0)

    area = manipulate.get_area()
    region_3d = area.spaces[0].region_3d

    fake_context = lambda: None
    fake_context.area = area
    fake_context.space_data = lambda: None
    fake_context.space_data.region_3d = region_3d
    fake_context.scene = bpy.context.scene

    brect = tuple(coords.get_camera_border(bpy.context))
    arect = (396.5, -261.9, 1189.5, 1147.9)

    test_funcs.move_pin(793, 421, 651, 425, arect, brect)
    test_funcs.move_pin(732, 478, 826, 510, arect, brect)
    test_funcs.move_pin(542, 549, 639, 527, arect, brect)
    test_funcs.move_pin(912, 412, 911, 388, arect, brect)

    # Coloring wireframe
    op = getattr(
        bpy.ops.object, Config.fb_main_wireframe_color_callname)
    op('EXEC_DEFAULT', action='wireframe_green')


def test_duplicate_and_reconstruct():
    headnum = test_funcs.get_last_headnum()
    test_funcs.deselect_all()
    headobj = test_funcs.select_by_headnum(headnum)
    bpy.ops.object.duplicate_move(
        OBJECT_OT_duplicate={"linked": False, "mode": 'TRANSLATION'},
        TRANSFORM_OT_translate={"value": (-3.0, 0, 0)})

    op = getattr(
        bpy.ops.object, Config.fb_actor_operator_callname)
    op('EXEC_DEFAULT', action='reconstruct_by_head', headnum=-1, camnum=-1)


if __name__ == "__main__":
    print("test_create_head_and_cameras")
    test_create_head_and_cameras()
    print("test_delete_last_camera")
    test_delete_last_camera()
    print("test_move_pins")
    test_move_pins()
    test_funcs.out_pinmode()
    print("test_duplicate_and_reconstruct")
    test_duplicate_and_reconstruct()
