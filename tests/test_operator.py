import os
import bpy
from bpy.types import Panel, Operator
from bpy.props import StringProperty, IntProperty

import keentools_facebuilder
from keentools.facebuilder.config import FBConfig, get_fb_settings, \
    get_operator, ErrorType
import keentools.utils.coords as coords
from keentools.utils.fake_context import get_fake_context
from keentools.facebuilder.fbloader import FBLoader


class TestsOperator(Operator):
    bl_idname = 'object.keentools_fb_tests'
    bl_label = "Run Test"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Start test"

    action: StringProperty(name="Action Name")
    error_type: IntProperty(name="Error Type")

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
        elif self.action == "test_error_message":
            warn = get_operator(FBConfig.fb_warning_idname)
            warn('INVOKE_DEFAULT', msg=self.error_type)
        return {'FINISHED'}


class TestsPanel(Panel):
    bl_idname = "FACEBUILDER_PT_tests_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Integration Tests"
    bl_category = FBConfig.fb_tab_category
    bl_context = "objectmode"


    def _draw_error_buttons(self, layout):
        layout.label(text='Error Messages')
        for err in dir(ErrorType):
            if not callable(getattr(ErrorType, err)) and \
                    not err.startswith('__'):
                name = "{}".format(err)
                value = getattr(ErrorType, err)
                op = layout.operator('object.keentools_fb_tests',
                                     text="{}: {}".format(value, name))
                op.action = "test_error_message"
                op.error_type = getattr(ErrorType, name)


    # Face Builder Tests Panel Draw
    def draw(self, context):
        layout = self.layout

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

        box = layout.box()
        self._draw_error_buttons(box)


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
    op = get_operator(FBConfig.fb_add_head_operator_idname)
    op('EXEC_DEFAULT')


def get_last_headnum():
    settings = get_fb_settings()
    headnum = len(settings.heads) - 1
    return headnum


def select_by_headnum(headnum):
    settings = get_fb_settings()
    headobj = settings.get_head(headnum).headobj
    headobj.select_set(state=True)
    bpy.context.view_layer.objects.active = headobj
    return headobj


def get_last_camnum(headnum):
    settings = get_fb_settings()
    camnum = len(settings.get_head(headnum).cameras) - 1
    return camnum


def create_empty_camera(headnum):
    FBLoader.add_new_camera(headnum, None)


def create_camera(dir, filename):
    headnum = get_last_headnum()
    op = get_operator(FBConfig.fb_multiple_filebrowser_idname)
    op('EXEC_DEFAULT', headnum=headnum, directory=dir,
       files=({'name': filename},))


def delete_camera(headnum, camnum):
    op = get_operator(FBConfig.fb_delete_camera_idname)
    op('EXEC_DEFAULT', headnum=headnum, camnum=camnum)


def move_pin(start_x, start_y, end_x, end_y, arect, brect,
             headnum=0, camnum=0):
    # Registered Operator call
    op = get_operator(FBConfig.fb_movepin_idname)
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
    op = get_operator(FBConfig.fb_select_camera_idname)
    op('EXEC_DEFAULT', headnum=headnum, camnum=camnum)


# -------
# Tests
# -------
def test_print_work():
    print("WORK")


def test_create_head_and_cameras():
    create_head()
    headnum = get_last_headnum()
    create_empty_camera(headnum)
    create_empty_camera(headnum)
    create_empty_camera(headnum)


def test_delete_last_camera():
    headnum = get_last_headnum()
    print("HN", headnum)
    assert(headnum >= 0)
    camnum = get_last_camnum(headnum)
    print("CN", camnum)
    assert(camnum >= 0)
    delete_camera(headnum, camnum)


def test_move_pins():
    # test_create_head_and_cameras()
    # Switch to PinMode
    select_camera(0, 0)

    fake_context = get_fake_context()

    brect = tuple(coords.get_camera_border(fake_context))
    arect = (396.5, -261.9, 1189.5, 1147.9)

    move_pin(793, 421, 651, 425, arect, brect)
    move_pin(732, 478, 826, 510, arect, brect)
    move_pin(542, 549, 639, 527, arect, brect)
    move_pin(912, 412, 911, 388, arect, brect)

    # Coloring wireframe
    op = get_operator(FBConfig.fb_wireframe_color_idname)
    op('EXEC_DEFAULT', action='wireframe_green')


def test_duplicate_and_reconstruct():
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.object.duplicate_move(
        OBJECT_OT_duplicate={"linked": False, "mode": 'TRANSLATION'},
        TRANSFORM_OT_translate={"value": (-3.0, 0, 0)})

    op = get_operator(FBConfig.fb_history_actor_idname)
    op('EXEC_DEFAULT', action='reconstruct_by_head')
