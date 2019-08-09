import bpy
from bpy.types import Panel, Operator
from bpy.props import StringProperty

import keentools_facebuilder
from keentools_facebuilder.config import config
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
            print_work()
        elif self.action == "test_create_head_and_cameras":
            test_create_head_and_cameras()
        elif self.action == "test_create_and_move_pins":
            test_create_and_move_pins()
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

        op = layout.operator('object.keentools_fb_tests', text="print_work")
        op.action = "print_work"

        op = layout.operator('object.keentools_fb_tests', text="test_create_head_and_cameras")
        op.action = "test_create_head_and_cameras"

        op = layout.operator('object.keentools_fb_tests', text="test_create_and_move_pins")
        op.action = "test_create_and_move_pins"


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


def create_head():
    # Create Head
    op = getattr(bpy.ops.mesh, config.fb_add_head_operator_callname)
    op('EXEC_DEFAULT')


def create_empty_camera():
    # Add New Camera button
    op = getattr(bpy.ops.object, config.fb_main_add_camera_callname)
    op('EXEC_DEFAULT')

def print_work():
    print("WORK")


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


def test_create_head_and_cameras():
    create_head()
    create_empty_camera()
    create_empty_camera()
    create_empty_camera()


def test_create_and_move_pins():
    test_create_head_and_cameras()
    # Switch to PinMode
    op = getattr(bpy.ops.object, config.fb_main_select_camera_callname)
    op('EXEC_DEFAULT', headnum=0, camnum=0)

    area = get_area()
    region_3d = area.spaces[0].region_3d

    fake_context = lambda: None
    fake_context.area = area
    fake_context.space_data = lambda: None
    fake_context.space_data.region_3d = region_3d
    fake_context.scene = bpy.context.scene

    x1, y1, x2, y2 = coords.get_camera_border(fake_context)

    ax1, ay1, ax2, ay2 = 396.5,-261.9, 1189.5,1147.9

    x, y = coords.region_to_image_space(792, 422, ax1, ay1, ax2, ay2)
    px, py = coords.image_space_to_region(x, y, x1, y1, x2, y2)
    
    print("P1:", px, py)

    # Registered Operator call
    op = getattr(
        bpy.ops.object, config.fb_movepin_operator_callname)
    op('INVOKE_DEFAULT',
       headnum=0,
       camnum=0,
       pinx=px, piny=py)

    x, y = coords.region_to_image_space(655, 447, ax1, ay1, ax2, ay2)
    px, py = coords.image_space_to_region(x, y, x1, y1, x2, y2)

    print("P2:", px, py)
    
    op('INVOKE_DEFAULT',
       headnum=0,
       camnum=0,
       pinx=px, piny=py)

