# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2019-2024 KeenTools

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

from ..utils.kt_logging import KTLogger
from ..addon_config import (ActionStatus,
                            fb_settings)
from .fbloader import FBLoader
from ..utils.coords import (rotate_camera_around_model,
                            model_mat_by_bpy_model_and_camera,
                            update_head_mesh_non_neutral)


_log = KTLogger(__name__)


def solve_head(headnum: int) -> None:
    def _find_keyframe_with_more_than_three_pins(fb) -> int:
        for keyframe in fb.keyframes():
            pins_count = fb.pins_count(keyframe)
            if pins_count > 3:
                return keyframe
        return -1

    def _get_camnum_by_keyframe(head, keyframe) -> int:
        for i, camera in enumerate(head.cameras):
            if camera.get_keyframe() == keyframe:
                return i
        return -1

    _log.yellow('solve_head start')
    fb = FBLoader.get_builder()
    keyframe = _find_keyframe_with_more_than_three_pins(fb)
    if keyframe < 0:
        fb.unmorph()
        return
    settings = fb_settings()
    head = settings.get_head(headnum)
    camnum = _get_camnum_by_keyframe(head, keyframe)
    if camnum < 0:
        return
    FBLoader.solve(headnum, camnum)
    _log.output('solve_head end >>>')


def remove_pins_act(headnum: int, camnum: int, update: bool = True) -> ActionStatus:
    _log.yellow('remove_pins_act start')
    settings = fb_settings()
    head = settings.get_head(headnum)
    if not head:
        return ActionStatus(False, 'No Head in remove pins action')
    camera = head.get_camera(camnum)
    if not camera:
        return ActionStatus(False, 'No Camera in remove pins action')

    kid = settings.get_keyframe(headnum, camnum)
    if kid < 0:
        return ActionStatus(False, 'Wrong keyframe_id in remove pins action')

    fb = FBLoader.get_builder()
    fb.remove_pins(kid)
    camera.pins_count = 0

    if not update:
        _log.output('remove_pins_act early end >>>')
        return ActionStatus(True, 'ok')

    solve_head(headnum)

    FBLoader.save_fb_serial_and_image_pathes(headnum)
    FBLoader.load_pins_into_viewport(headnum, camnum)
    update_head_mesh_non_neutral(fb, head)
    FBLoader.update_fb_viewport_shaders(camera_pos=True,
                                        wireframe=True,
                                        pins_and_residuals=True,
                                        batch_wireframe=True)
    FBLoader.viewport().tag_redraw()
    _log.output('remove_pins_act end >>>')
    return ActionStatus(True, 'ok')


def rotate_head_act(headnum: int, camnum: int, angle: float) -> ActionStatus:
    _log.yellow('rotate_head_act start')
    settings = fb_settings()
    if not settings:
        return ActionStatus(False, 'No settings in rotate head action')

    head = settings.get_head(headnum)
    if not head:
        return ActionStatus(False, 'No Head in rotate head action')
    camera = head.get_camera(camnum)
    if not camera:
        return ActionStatus(False, 'No Camera in rotate head action')

    head_mat = head.headobj.matrix_world
    cam_mat = rotate_camera_around_model(head_mat,
                                         camera.camobj.matrix_world,
                                         angle=angle)
    camera.camobj.matrix_world = cam_mat.copy()
    model_mat = model_mat_by_bpy_model_and_camera(head_mat, cam_mat)

    act_status = remove_pins_act(headnum, camnum)
    if not act_status.success:
        return act_status

    fb = FBLoader.get_builder()
    fb.update_model_mat(camera.get_keyframe(), model_mat)

    FBLoader.save_fb_serial_and_image_pathes(headnum)
    FBLoader.load_pins_into_viewport(headnum, camnum)
    FBLoader.update_fb_viewport_shaders(camera_pos=True,
                                        wireframe=True,
                                        pins_and_residuals=True,
                                        batch_wireframe=True)
    FBLoader.viewport().tag_redraw()
    _log.output('rotate_head_act end >>>')
    return ActionStatus(True, 'ok')


def reset_expression_act(headnum: int, camnum: int,
                         update: bool = True) -> ActionStatus:
    _log.yellow('reset_expression_act start')
    settings = fb_settings()
    if not settings:
        return ActionStatus(False, 'No settings in reset expression')

    head = settings.get_head(headnum)
    if not head:
        return ActionStatus(False, 'No Head in reset expression')
    camera = head.get_camera(camnum)
    if not camera:
        return ActionStatus(False, 'No Camera in reset expression')

    kid = head.get_keyframe(camnum)
    if kid < 0:
        return ActionStatus(False, 'Wrong keyframe_id in reset expression')

    fb = FBLoader.get_builder()
    fb.reset_to_neutral_emotions(kid)

    if not update:
        _log.output('reset_expression_act early end >>>')
        return ActionStatus(True, 'ok')

    FBLoader.save_fb_serial_and_image_pathes(headnum)
    FBLoader.load_pins_into_viewport(headnum, camnum)
    update_head_mesh_non_neutral(fb, head)
    FBLoader.update_fb_viewport_shaders(camera_pos=True,
                                        wireframe=True,
                                        pins_and_residuals=True,
                                        batch_wireframe=True)
    FBLoader.viewport().tag_redraw()
    _log.output('reset_expression_act end >>>')
    return ActionStatus(True, 'ok')


def center_geo_act(headnum: int, camnum: int,
                   update: bool = True) -> ActionStatus:
    _log.yellow('center_geo_act start')
    settings = fb_settings()
    if not settings:
        return ActionStatus(False, 'No settings in center geo')

    head = settings.get_head(headnum)
    if not head:
        return ActionStatus(False, 'No Head in center geo')
    camera = head.get_camera(camnum)
    if not camera:
        return ActionStatus(False, 'No Camera in center geo')

    kid = head.get_keyframe(camnum)
    if kid < 0:
        return ActionStatus(False, 'Wrong keyframe_id in center geo')

    FBLoader.center_geo_camera_projection(headnum, camnum)
    FBLoader.place_camera(headnum, camnum)

    if not update:
        _log.output('center_geo_act early end >>>')
        return ActionStatus(True, 'ok')

    FBLoader.save_fb_serial_and_image_pathes(headnum)
    FBLoader.load_pins_into_viewport(headnum, camnum)
    FBLoader.update_fb_viewport_shaders(camera_pos=True,
                                        wireframe=True,
                                        pins_and_residuals=True,
                                        batch_wireframe=True)
    FBLoader.viewport().tag_redraw()
    _log.output('center_geo_act end >>>')
    return ActionStatus(True, 'ok')
