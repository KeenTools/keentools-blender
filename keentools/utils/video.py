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
from typing import Any, Tuple, List, Optional

import bpy
from bpy.types import MovieClip, Image, Scene

from .kt_logging import KTLogger
from ..addon_config import ActionStatus
from .bpy_common import (operator_with_context,
                         bpy_scene,
                         bpy_create_object,
                         bpy_create_camera_data)
from .ui_redraw import get_all_areas


_log = KTLogger(__name__)


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
    _log.output('make_proxy success')
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
        _log.output(f'find_movieclip: {movieclip}')
        try:
            _log.output(f'\nmovieclip.filepath: {movieclip.filepath}\n'
                        f'filepath: {filepath}')
            if os.path.samefile(bpy.path.abspath(movieclip.filepath),
                                bpy.path.abspath(filepath)):
                return movieclip
        except FileNotFoundError as err:
            _log.error(f'find_movieclip FILE NOT FOUND:\n{str(err)}')
        except Exception as err:
            _log.error(f'find_movieclip error:\n{str(err)}')
    return None


def load_movieclip(directory: str, file_names: List[str]) -> Optional[MovieClip]:
    if len(file_names) == 0:
        _log.error('NO FILES HAVE BEEN SELECTED')
        return None

    file_names.sort()
    frame_files = [{'name': name} for name in file_names]
    _log.output(f'load_movieclip DIR: {directory}')
    _log.output(f'load_movieclip FILES: {file_names}')

    old_movieclips = bpy.data.movieclips[:]
    _log.output(f'old_movieclips: {[mc.name for mc in old_movieclips]}')
    try:
        res = bpy.ops.clip.open('EXEC_DEFAULT', files=frame_files,
                                directory=directory)
        _log.output(f'load_movieclip result: {res}')
    except RuntimeError as err:
        _log.error('MOVIECLIP OPEN ERROR: {}'.format(str(err)))
        return None

    new_movieclip = get_new_movieclip(old_movieclips)
    if new_movieclip is not None:
        _log.output(f'new movieclip created: {new_movieclip.name}')
        return new_movieclip

    _log.error('NO NEW MOVIECLIP HAS BEEN CREATED')

    new_movieclip = find_movieclip(os.path.join(directory, file_names[0]))
    if new_movieclip is None:
        _log.error('NO NEW MOVIECLIP IN EXISTING')
        return None

    _log.output(f'EXISTING MOVICLIP HAS BEEN FOUND: {new_movieclip.name}')
    return new_movieclip


def convert_movieclip_to_frames(
        movie_clip: Optional[MovieClip],
        filepath: str, *,
        file_format: str = 'PNG',
        quality: int = 100,
        start_frame: int = 1,
        end_frame: int = -1,
        orientation: int = 0,
        single_frame: bool = False,
        opengl_render: bool = True,
        video_scene_name: str = 'video_scene') -> Optional[str]:
    w, h = get_movieclip_size(movie_clip)
    if w <= 0 or h <= 0:
        return None

    scene = bpy.data.scenes.new(video_scene_name)
    scene_name = scene.name
    sequence_editor = scene.sequence_editor_create()
    sequence_editor.use_cache_final = False
    strip = sequence_editor.sequences.new_clip('video', movie_clip, 2, 1)
    strip.transform.rotation = orientation * 1.5707963  # pi/2 works worse!

    cam_data = bpy_create_camera_data('output_cam_data')
    cam_data.show_background_images = True
    cam_ob = bpy_create_object('output_camera', cam_data)
    scene.collection.objects.link(cam_ob)
    scene.camera = cam_ob

    if orientation % 2 != 0:
        w, h = h, w
    scene.render.resolution_x = w
    scene.render.resolution_y = h
    scene.render.filepath = filepath
    scene.render.use_overwrite = True
    scene.render.use_file_extension = True
    scene.render.image_settings.file_format = file_format
    if file_format == 'JPEG':
        scene.render.image_settings.quality = quality
    scene.frame_start = start_frame
    scene.frame_end = end_frame if end_frame >= 0 else movie_clip.frame_duration
    scene.frame_set(start_frame)
    output_filepath = scene.render.frame_path(frame=start_frame) \
        if not single_frame else filepath
    try:
        if opengl_render:
            operator_with_context(bpy.ops.render.opengl,
                                  {'scene': scene}, animation=not single_frame,
                                  write_still=single_frame,
                                  sequencer=True, view_context=False)
        else:
            # Much slower but works everywhere
            operator_with_context(bpy.ops.render.render,
                                  {'scene': scene}, animation=True)
    except Exception as err:
        output_filepath = None
        _log.error(f'convert_movieclip_to_frames Exception:\n{str(err)}')
    finally:
        _log.output('_cleanup_scene')
        scene = bpy.data.scenes[scene_name]
        scene.sequence_editor_clear()
        bpy.data.scenes.remove(scene)
    return output_filepath


def fit_render_size(movie_clip: Optional[MovieClip]) -> ActionStatus:
    w, h = get_movieclip_size(movie_clip)
    if w <= 0 or h <= 0:
        msg = f'Wrong movie clip frame size {w} x {h}'
        _log.error(msg)
        return ActionStatus(False, msg)

    scene = bpy.context.scene
    scene.render.resolution_x = w
    scene.render.resolution_y = h
    return ActionStatus(True, f'Render size {w} x {h}')


def fit_time_length(movie_clip: Optional[MovieClip]) -> ActionStatus:
    duration = get_movieclip_duration(movie_clip)
    if duration < 2:
        return ActionStatus(False, f'Image sequence too short: {duration}!')

    scene = bpy_scene()
    scene.frame_start = movie_clip.frame_start
    scene.frame_end = movie_clip.frame_start + duration - 1

    return ActionStatus(
        True, f'Timeline duration {scene.frame_start} - {scene.frame_end}')
