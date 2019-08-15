import bpy
import keentools_facebuilder
from keentools_facebuilder.config import Config, get_main_settings
import keentools_facebuilder.utils.coords as coords
from keentools_facebuilder.fbloader import FBLoader

# --------
def select_by_headnum(headnum):
    settings = get_main_settings()
    headobj = settings.heads[headnum].headobj
    headobj.select_set(state=True)
    bpy.context.view_layer.objects.active = headobj
    return headobj

# --------------
# Operators call
def create_head():
    # Create Head
    op = getattr(bpy.ops.mesh, Config.fb_add_head_operator_callname)
    op('EXEC_DEFAULT')


def create_empty_camera(headnum):
    # Add New Camera button
    op = getattr(bpy.ops.object, Config.fb_main_add_camera_callname)
    op('EXEC_DEFAULT', headnum=headnum)


def delete_camera(headnum, camnum):
    op = getattr(bpy.ops.object, Config.fb_main_delete_camera_callname)
    op('EXEC_DEFAULT', headnum=headnum, camnum=camnum)


def move_pin(start_x, start_y, end_x, end_y, arect, brect,
             headnum=0, camnum=0):
    # Registered Operator call
    op = getattr(
        bpy.ops.object, Config.fb_movepin_operator_callname)
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
    op = getattr(bpy.ops.object, Config.fb_main_select_camera_callname)
    op('EXEC_DEFAULT', headnum=headnum, camnum=camnum)


def deselect_all():
    bpy.ops.object.select_all(action='DESELECT')


def out_pinmode():
    settings = get_main_settings()
    FBLoader.out_pinmode(settings.current_headnum, settings.current_camnum)


def wireframe_coloring(action='wireframe_green'):
    op = getattr(
        bpy.ops.object, Config.fb_main_wireframe_color_callname)
    op('EXEC_DEFAULT', action=action)


def new_scene():
    bpy.ops.scene.new(type='NEW')
