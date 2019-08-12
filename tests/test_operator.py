import bpy
from bpy.types import Panel, Operator
from bpy.props import StringProperty

import keentools_facebuilder
from keentools_facebuilder.config import config, get_main_settings
import keentools_facebuilder.utils.coords as coords

class TestsOperator(Operator):
    bl_idname = 'object.keentools_fb_tests'
    bl_label = "Run Test"
    bl_options = {'REGISTER'}  # 'UNDO'
    bl_description = "Start test"

    action: StringProperty(name="Action Name")

    def draw(self, context):
        """ No need to show panel so empty draw"""
        pass

    def execute(self, context):
        if self.action == "print_work":
            test_print_work()
        elif self.action == "test_create_head_and_cameras":
            test_create_head_and_cameras()
        elif self.action == "test_move_pins":
            test_move_pins()
        elif self.action == "test_delete_last_сamera":
            test_delete_last_camera()
        elif self.action == "test_duplicate_and_reconstruct":
            test_duplicate_and_reconstruct()
        return {'FINISHED'}


class TestsPanel(Panel):
    bl_idname = "FACEBUILDER_PT_tests_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Integration Tests"
    bl_category = "Face Builder"
    bl_context = "objectmode"

    # Face Builder Tests Panel Draw
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        obj = context.object

        op = layout.operator('object.keentools_fb_tests',
                             text="print_work")
        op.action = "print_work"

        op = layout.operator('object.keentools_fb_tests',
                             text="test_create_head_and_cameras")
        op.action = "test_create_head_and_cameras"

        op = layout.operator('object.keentools_fb_tests',
                             text="test_delete_camera")
        op.action = "test_delete_last_сamera"

        op = layout.operator('object.keentools_fb_tests',
                             text="test_move_pins")
        op.action = "test_move_pins"
        op = layout.operator('object.keentools_fb_tests',
                             text="test_duplicate_and_reconstruct")
        op.action = "test_duplicate_and_reconstruct"



_classes = (
    TestsPanel, TestsOperator
)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()

# --------
def create_head():
    # Create Head
    op = getattr(bpy.ops.mesh, config.fb_add_head_operator_callname)
    op('EXEC_DEFAULT')


def get_last_headnum():
    settings = get_main_settings()
    headnum = len(settings.heads) - 1
    return headnum


def select_by_headnum(headnum):
    settings = get_main_settings()
    headobj = settings.heads[headnum].headobj
    headobj.select_set(state=True)
    bpy.context.view_layer.objects.active = headobj
    return headobj


def get_last_camnum(headnum):
    settings = get_main_settings()
    camnum = len(settings.heads[headnum].cameras) - 1
    return camnum

def create_empty_camera():
    # Add New Camera button
    op = getattr(bpy.ops.object, config.fb_main_add_camera_callname)
    op('EXEC_DEFAULT')


def delete_camera(headnum, camnum):
    op = getattr(bpy.ops.object, config.fb_main_delete_camera_callname)
    op('EXEC_DEFAULT', headnum=headnum, camnum=camnum)


def get_override_context():
    window = bpy.context.window
    screen = window.screen
    override = bpy.context.copy()
    area = get_area()
    if area is not None:
        override['window'] = window
        override['screen'] = screen
        override['area'] = area
    return override


def get_area():
    window = bpy.context.window
    screen = window.screen
    for area in screen.areas:
        if area.type == 'VIEW_3D':
            return area
    return None


def move_pin(start_x, start_y, end_x, end_y, arect, brect, headnum=0, camnum=0):
    # Registered Operator call
    op = getattr(
        bpy.ops.object, config.fb_movepin_operator_callname)
    # Move pin
    x, y = coords.region_to_image_space(start_x, start_y, *arect)
    px, py = coords.image_space_to_region(x, y, *brect)
    print("P:", px, py)
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
    op = getattr(bpy.ops.object, config.fb_main_select_camera_callname)
    op('EXEC_DEFAULT', headnum=headnum, camnum=camnum)


# -------
# Tests
# -------
def test_print_work():
    print("WORK")


def test_create_head_and_cameras():
    create_head()
    create_empty_camera()
    create_empty_camera()
    create_empty_camera()


def test_delete_last_camera():
    headnum = get_last_headnum()
    assert(headnum >= 0)
    camnum = get_last_camnum(headnum)
    assert(camnum >= 0)
    delete_camera(headnum, camnum)


def test_move_pins():
    # test_create_head_and_cameras()
    # Switch to PinMode
    select_camera(0, 0)

    area = get_area()
    region_3d = area.spaces[0].region_3d

    fake_context = lambda: None
    fake_context.area = area
    fake_context.space_data = lambda: None
    fake_context.space_data.region_3d = region_3d
    fake_context.scene = bpy.context.scene

    brect = tuple(coords.get_camera_border(fake_context))
    arect = (396.5, -261.9, 1189.5, 1147.9)

    move_pin(793, 421, 651, 425, arect, brect)
    move_pin(732, 478, 826, 510, arect, brect)
    move_pin(542, 549, 639, 527, arect, brect)
    move_pin(912, 412, 911, 388, arect, brect)

def test_duplicate_and_reconstruct():
    headnum = get_last_headnum()
    bpy.ops.object.select_all(action='DESELECT')
    headobj = select_by_headnum(headnum)
    bpy.ops.object.duplicate_move(
        OBJECT_OT_duplicate={"linked": False, "mode": 'TRANSLATION'},
        TRANSFORM_OT_translate={"value": (-3.0, 0, 0)})
