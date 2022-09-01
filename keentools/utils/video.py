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
import os
import logging
from typing import Any, Tuple, List, Optional

import bpy
from bpy.types import MovieClip

from ..addon_config import ActionStatus
from .bpy_common import (operator_with_context,
                         extend_scene_timeline_start,
                         extend_scene_timeline_end)
from .ui_redraw import get_all_areas


_logger: Any = logging.getLogger(__name__)


def _log_output(message: str) -> None:
    global _logger
    _logger.debug(message)


def _log_error(message: str) -> None:
    global _logger
    _logger.error(message)


def get_movieclip_size(movie_clip: Optional[MovieClip]) -> Tuple[int, int]:
    if not movie_clip:
        return -1, -1
    size = movie_clip.size[:]
    if len(size) != 2:
        return -1, -1
    return size[0], size[1]


def get_movieclip_duration(movie_clip: Optional[MovieClip]) -> int:
    if not movie_clip:
        return -1
    return movie_clip.frame_duration


def make_movieclip_proxy(movie_clip: Optional[MovieClip],
                         dir_path: str) -> bool:
    if not movie_clip:
        return False

    areas = get_all_areas()
    area = areas[-1]
    area_type_old = area.type

    movie_clip.use_proxy = True
    movie_clip.proxy.build_25 = False
    movie_clip.proxy.build_undistorted_100 = True
    movie_clip.proxy.quality = 100
    movie_clip.proxy.directory = dir_path
    movie_clip.use_proxy_custom_directory = True
    area.type = 'CLIP_EDITOR'
    area.spaces.active.clip = movie_clip
    bpy.ops.clip.rebuild_proxy({'area': area})
    area.type = area_type_old
    _log_output(f'make_proxy success')
    return True


def get_new_movieclip(old_movieclips: List) -> Optional[MovieClip]:
    for movieclip in bpy.data.movieclips:
        if movieclip not in old_movieclips:
            return movieclip
    return None


def find_movieclip(filepath: str) -> Optional[MovieClip]:
    if not os.path.exists(filepath):
        return None
    for movieclip in bpy.data.movieclips:
        try:
            if os.path.samefile(movieclip.filepath, filepath):
                return movieclip
        except FileNotFoundError as err:
            _log_error(f'find_movieclip FILE NOT FOUND:\n{str(err)}')
        except Exception as err:
            _log_error(f'find_movieclip error:\n{str(err)}')
    return None


def load_movieclip(directory: str, file_names: List[str]) -> Optional[MovieClip]:
    if len(file_names) == 0:
        _log_error('NO FILES HAVE BEEN SELECTED')
        return None

    file_names.sort()
    frame_files = [{'name': name} for name in file_names]
    _log_output(f'DIR: {directory}')

    old_movieclips = bpy.data.movieclips[:]
    try:
        res = bpy.ops.clip.open('EXEC_DEFAULT', files=frame_files,
                                directory=directory)
        _log_output(f'Operator result: {res}')
    except RuntimeError as err:
        _log_error('MOVIECLIP OPEN ERROR: {}'.format(str(err)))
        return None

    new_movieclip = get_new_movieclip(old_movieclips)
    if new_movieclip is not None:
        return new_movieclip

    _log_error('NO NEW MOVIECLIP HAS BEEN CREATED')

    new_movieclip = find_movieclip(os.path.join(directory, file_names[0]))
    if new_movieclip is None:
        _log_error('NO NEW MOVIECLIP IN EXISTING')
        return None

    _log_output(f'EXISTING MOVICLIP HAS BEEN FOUND: {new_movieclip}')
    return new_movieclip


def convert_movieclip_to_frames(movie_clip: Optional[MovieClip],
                                filepath: str, *,
                                file_format: str='PNG',
                                quality: float=100.0,
                                start_frame: int=1,
                                end_frame: int=-1,
                                opengl_render: bool=True) -> Optional[str]:
    def _cleanup_scene() -> None:
        sequence_editor.sequences.remove(strip)
        scene.sequence_editor_clear()
        bpy.data.objects.remove(cam_ob, do_unlink=True)
        bpy.data.scenes.remove(scene)

    w, h = get_movieclip_size(movie_clip)
    if w <= 0 or h <= 0:
        _cleanup_scene()
        return None

    scene = bpy.data.scenes.new('convert_video_to_frames')
    sequence_editor = scene.sequence_editor_create()
    strip = sequence_editor.sequences.new_clip('video', movie_clip, 1, 1)

    cam_data = bpy.data.cameras.new('output_cam_data')
    cam_data.show_background_images = True
    cam_ob = bpy.data.objects.new('output_camera', cam_data)
    scene.collection.objects.link(cam_ob)

    scene.render.resolution_x = w
    scene.render.resolution_y = h
    scene.render.filepath = filepath
    scene.render.use_overwrite = True
    scene.render.use_file_extension = True
    scene.render.image_settings.file_format = file_format
    if file_format == 'JPEG':
        scene.render.image_settings.image_settings.quality = quality
    scene.frame_start = start_frame
    scene.frame_end = end_frame if end_frame >= 0 else movie_clip.frame_duration
    output_filepath = scene.render.frame_path(frame=start_frame)
    try:
        if opengl_render:
            operator_with_context(bpy.ops.render.opengl,
                                  {'scene': scene}, animation=True,
                                  sequencer=True, view_context=False)
        else:
            # Much slower but works everywhere
            operator_with_context(bpy.ops.render.render,
                                  {'scene': scene}, animation=True)
    except Exception as err:
        output_filepath = None
        _log_error(f'convert_movieclip_to_frames Exception:\n{str(err)}')
    finally:
        _cleanup_scene()
    return output_filepath


def fit_render_size(movie_clip: Optional[MovieClip]) -> ActionStatus:
    w, h = get_movieclip_size(movie_clip)
    if w <= 0 or h <= 0:
        msg = f'Wrong precalc frame size {w} x {h}'
        _log_error(msg)
        return ActionStatus(False, msg)

    scene = bpy.context.scene
    scene.render.resolution_x = w
    scene.render.resolution_y = h
    return ActionStatus(True, f'Render size {w} x {h}')


def fit_time_length(movie_clip: Optional[MovieClip]) -> ActionStatus:
    duration = get_movieclip_duration(movie_clip)
    if duration < 2:
        return ActionStatus(False, f'Image sequence too short: {duration}!')

    extend_scene_timeline_start(1)
    extend_scene_timeline_end(duration, force=True)

    return ActionStatus(True, f'Timeline duration 1 - {duration}')
