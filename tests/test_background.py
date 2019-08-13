# Test for context override
# Direct call test in background mode:
# blender -b -P test_background.py
import bpy

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

bpy.ops.object.select_all(action='DESELECT')
bpy.ops.object.camera_add(location=(0, -5, 0), rotation=(1.57, 0, 0))
override = get_override_context()
bpy.ops.view3d.object_as_camera(override)
