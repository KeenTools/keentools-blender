# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2019-2022 KeenTools

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# ##### END GPL LICENSE BLOCK #####
from typing import Any, Dict, Callable, Tuple, List, Optional
from contextlib import contextmanager
import traceback

import bpy
from bpy.types import Object, Mesh, Operator, Camera, Scene, Image, Material

from .version import BVersion
from .kt_logging import KTLogger
from ..addon_config import Config


_log = KTLogger(__name__)


def bpy_app_version() -> Tuple:
    return bpy.app.version


use_gpu_instead_of_bgl: bool = not BVersion.use_old_bgl_shaders


def bpy_background_mode() -> bool:
    return bpy.app.background


def bpy_scene() -> Any:
    return bpy.context.scene


def bpy_context() -> Any:
    return bpy.context


def bpy_window_manager() -> Any:
    return bpy.context.window_manager


def bpy_objects() -> Any:
    return bpy.data.objects


def bpy_images() -> Any:
    return bpy.data.images


def bpy_scene_camera() -> Camera:
    return bpy.context.scene.camera


def bpy_is_animation_playing() -> bool:
    if not bpy.context.screen:
        return False
    return bpy.context.screen.is_animation_playing


def bpy_current_frame() -> int:
    return bpy.context.scene.frame_current


def bpy_start_frame() -> int:
    return bpy.context.scene.frame_start


def bpy_end_frame() -> int:
    return bpy.context.scene.frame_end


def bpy_set_current_frame(frame: int) -> None:
    _log.output(_log.color('green', f'bpy_set_current_frame: {frame}'))
    bpy.context.scene.frame_set(frame)


def bpy_render_frame() -> Tuple[int, int]:
    scene = bpy.context.scene
    rx = scene.render.resolution_x
    ry = scene.render.resolution_y
    w = rx if rx != 0 else 1
    h = ry if ry != 0 else 1
    return w, h


def bpy_render_aspect() -> float:
    w, h = bpy_render_frame()
    return w / h


def bpy_abspath(file_path: str) -> str:
    return bpy.path.abspath(file_path)


def bpy_set_render_frame(rx: int, ry: int) -> None:
    scene = bpy.context.scene
    scene.render.resolution_x = rx
    scene.render.resolution_y = ry


def bpy_link_to_scene(obj: Object) -> None:
    bpy.context.scene.collection.objects.link(obj)


def link_object_to_current_scene_collection(obj: Object) -> None:
    act_col = bpy.context.view_layer.active_layer_collection
    index = bpy.data.collections.find(act_col.name)
    if index >= 0:
        col = bpy.data.collections[index]
    else:
        col = bpy.context.scene.collection
    col.objects.link(obj)


def bpy_create_object(name: str, data: Any) -> Object:
    obj = bpy.data.objects.new(name, data)
    return obj


def bpy_create_empty(name:str) -> Object:
    return bpy_create_object(name, None)


def bpy_create_camera_data(name: str) -> Any:
    cam = bpy.data.cameras.new(name)
    return cam


def create_empty_object(name: str) -> Object:
    control = bpy_create_empty(name)
    link_object_to_current_scene_collection(control)
    control.empty_display_type = 'PLAIN_AXES'
    control.empty_display_size = 2.5
    control.rotation_euler = (0, 0, 0)
    control.location = (0, 0, 0)
    return control


def bpy_remove_object(obj: Object) -> bool:
    try:
        if obj:
            bpy.data.objects.remove(obj, do_unlink=True)
            return True
    except Exception as err:
        _log.error(f'bpy_remove_object Exception: {str(err)}')
    return False


def bpy_object_is_in_scene(obj: Object) -> bool:
    return obj in bpy.context.scene.objects[:]


def bpy_poll_is_mesh(self: Any, obj: Optional[Object]) -> bool:
    return obj and obj.type == 'MESH' and bpy_object_is_in_scene(obj)


def bpy_poll_is_camera(self: Any, obj: Optional[Object]) -> bool:
    return obj and obj.type == 'CAMERA' and bpy_object_is_in_scene(obj)


def _operator_with_context_old(operator: Operator,
                               context_override_dict: Dict, **kwargs) -> None:
    _log.output(f'_operator_with_context_old: {operator}')
    return operator(context_override_dict, **kwargs)


def _operator_with_context_new(operator: Operator,
                               context_override_dict: Dict, **kwargs) -> None:
    _log.output(f'_operator_with_context_new: {operator}')
    with bpy.context.temp_override(**context_override_dict):
        return operator(**kwargs)


operator_with_context: Callable = _operator_with_context_new \
    if BVersion.operator_with_context_exists else _operator_with_context_old


def extend_scene_timeline_end(keyframe_num: int, force=False) -> None:
    scene = bpy.context.scene
    if force or scene.frame_end < keyframe_num:
        scene.frame_end = keyframe_num


def extend_scene_timeline_start(keyframe_num: int) -> None:
    scene = bpy.context.scene
    if 0 <= keyframe_num < scene.frame_start:
        scene.frame_start = keyframe_num


def get_scene_camera_shift() -> Tuple[float, float]:
    cam = bpy.context.scene.camera
    if not cam:
        return 0.0, 0.0
    return cam.data.shift_x, cam.data.shift_y


def get_depsgraph() -> Any:
    return bpy.context.evaluated_depsgraph_get()


def evaluated_object(obj: Any) -> Object:
    depsgraph = get_depsgraph()
    return obj.evaluated_get(depsgraph)


def evaluated_mesh(obj: Object) -> Mesh:
    object_eval = evaluated_object(obj) if obj.mode == 'OBJECT' else obj
    return object_eval.data


def update_depsgraph() -> Any:
    depsgraph = get_depsgraph()
    depsgraph.update()
    return depsgraph


def reset_unsaved_animation_changes_in_frame() -> int:
    current_frame = bpy_current_frame()
    bpy_set_current_frame(current_frame + 1)
    update_depsgraph()
    bpy_set_current_frame(current_frame)
    update_depsgraph()
    return current_frame


def bpy_scene_selected_objects() -> List:
    if not hasattr(bpy.context, 'selected_objects'):
        return []
    return bpy.context.selected_objects


def bpy_active_object(obj: Optional[Object] = None) -> Optional[Any]:
    if obj is not None:
        bpy.context.view_layer.objects.active = obj
    return bpy.context.view_layer.objects.active


def bpy_all_scene_objects() -> List:
    return bpy.data.objects


def bpy_show_addon_preferences():
    bpy.ops.preferences.addon_show(module=Config.addon_name)


def bpy_view_camera():
    bpy.ops.view3d.view_camera()


def bpy_url_open(url):
    bpy.ops.wm.url_open(url=url)


def bpy_localview() -> None:
    bpy.ops.view3d.localview()


def bpy_timer_register(func: Callable, *, first_interval: float=0.01,
                       persistent: bool=False) -> None:
    bpy.app.timers.register(func, first_interval=first_interval,
                            persistent=persistent)


def bpy_timer_unregister(func: Callable) -> bool:
    if bpy.app.timers.is_registered(func):
        bpy.app.timers.unregister(func)
        return True
    return False


def bpy_new_scene(name: str) -> Scene:
    return bpy.data.scenes.new(name)


def bpy_new_image(name: str, **kwargs) -> Image:
    return bpy.data.images.new(name, **kwargs)


def bpy_remove_image(img: Optional[Image]) -> None:
    if img is None:
        return
    if img.name in bpy.data.images:
        bpy.data.images.remove(img)


def bpy_remove_material(mat: Optional[Material]) -> None:
    if mat is None:
        return
    if mat.name in bpy.data.materials:
        bpy.data.materials.remove(mat)


def bpy_render_single_frame(scene: Scene, frame: Optional[int]=None) -> None:
    if frame is not None:
        scene.frame_current = frame
    _log.output(_log.color('yellow', f'bpy_render_single_frame: {frame}'))
    operator_with_context(bpy.ops.render.render,
                          {'scene': scene}, animation=False)


def get_scene_by_name(scene_name: str) -> Optional[Scene]:
    scene_num = bpy.data.scenes.find(scene_name)
    if scene_num >= 0:
        return bpy.data.scenes[scene_num]
    return None


def bpy_transform_resize(*args, **kwargs) -> None:
    bpy.ops.transform.resize(*args, **kwargs)


def bpy_call_menu(*args, **kwargs) -> None:
    bpy.ops.wm.call_menu(*args, **kwargs)


def bpy_export_fbx(*args, **kwargs) -> None:
    bpy.ops.export_scene.fbx(*args, **kwargs)


def bpy_progress_begin(start_val: float=0, end_val: float=1) -> None:
    bpy.context.window_manager.progress_begin(start_val, end_val)


def bpy_progress_end() -> None:
    bpy.context.window_manager.progress_end()


def bpy_progress_update(progress: float) -> None:
    bpy.context.window_manager.progress_update(progress)


def bpy_image_settings() -> Any:
    return bpy.context.scene.render.image_settings


def bpy_jpeg_quality(value: Optional[int]= None) -> int:
    old = bpy.context.scene.render.image_settings.quality
    if value is not None:
        bpy.context.scene.render.image_settings.quality = value
    return old


@contextmanager
def bpy_jpeg_quality_context(value: int):
    old = bpy_jpeg_quality(value)
    yield
    bpy_jpeg_quality(old)


def bpy_msgbus_subscribe_rna(*args, **kwargs) -> None:
    bpy.msgbus.subscribe_rna(*args, **kwargs)


def bpy_msgbus_clear_by_owner(owner: object) -> None:
    bpy.msgbus.clear_by_owner(owner)


def get_traceback(skip_last=1) -> str:
    return ''.join(traceback.format_stack()[:-skip_last])


def bpy_object_is_valid(obj: Object) -> bool:
    if obj is None:
        return False
    try:
        if not hasattr(obj, 'users_scene'):
            _log.output(f'invalid object: {obj}')
            return False

        return True

    except Exception as err:
        _log.output(f'bpy_object_is_valid Exception:\n{str(err)}')

    return False


def bpy_object_name(obj: Object, default_name: str = 'Undefined') -> str:
    try:
        name = obj.name
        return name
    except Exception as err:
        _log.output(f'bpy_object_name Exception:\n{str(err)}')
    return default_name


def bpy_new_action(name: str) -> Any:
    return bpy.data.actions.new(name)


def bpy_remove_action(action: Any) -> None:
    if not action:
        return
    bpy.data.actions.remove(action)


def bpy_shape_key_move(obj: Object, type_direction: str = 'UP') -> None:
    operator_with_context(bpy.ops.object.shape_key_move,
                          {'object': obj}, type=type_direction)


def bpy_shape_key_move_top(obj: Object) -> None:
    bpy_shape_key_move(obj, 'TOP')


def bpy_shape_key_move_up(obj: Object) -> None:
    bpy_shape_key_move(obj, 'UP')


def bpy_shape_key_move_down(obj: Object) -> None:
    bpy_shape_key_move(obj, 'DOWN')


def bpy_shape_key_move_bottom(obj: Object) -> None:
    bpy_shape_key_move(obj, 'BOTTOM')
