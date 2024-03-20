# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2023 KeenTools

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

from typing import Tuple, Optional, Any
from copy import deepcopy

from ...addon_config import get_settings


_text_opacity: float = 1.0


def _get_viewport(product: int) -> Any:
    settings = get_settings(product)
    return settings.loader().viewport()


def revert_default_screen_message(unregister: bool=False,
                                  *, product: int) -> None:
    vp = _get_viewport(product)
    vp.revert_default_screen_message(unregister=unregister)


def single_line_screen_message(message: str,
                               *, color: Tuple = (1.0, 0., 0., _text_opacity),
                               register: bool = False,
                               context: Optional[Any] = None,
                               product: int) -> None:
    vp = _get_viewport(product)
    vp.message_to_screen([{'text': message, 'color': color}],
                         register=register, context=context)


def playback_mode_screen_message(product: int) -> None:
    vp = _get_viewport(product)
    vp.message_to_screen([
        {'text': 'Playback animation',
         'color': (0., 1., 0., _text_opacity),
         'size': 24,
         'y': 60},  # line 1
        {'text': 'ESC: Exit | TAB: Hide/Show',
         'color': (1., 1., 1., _text_opacity),
         'size': 20,
         'y': 30}])  # line 2


def in_edit_mode_screen_message(product: int) -> None:
    vp = _get_viewport(product)
    vp.message_to_screen([
        {'text': 'Object is in EDIT MODE',
         'color': (1., 0., 1., _text_opacity),
         'size': 24,
         'y': 60},  # line 1
        {'text': 'ESC: Exit | TAB: Hide/Show',
         'color': (1., 1., 1., _text_opacity),
         'size': 20,
         'y': 30}])  # line 2


def how_to_show_wireframe_screen_message(product: int) -> None:
    vp = _get_viewport(product)
    default_txt = deepcopy(vp.texter().get_default_text())
    default_txt[0]['text'] = 'Press TAB to show wireframe'
    default_txt[0]['color'] = (1., 0., 1., _text_opacity)
    vp.message_to_screen(default_txt)


def analysing_screen_message(message: str, *, product: int) -> None:
    vp = _get_viewport(product)
    vp.message_to_screen(
        [{'text': 'Analysing... Please wait', 'y': 60,
          'color': (1.0, 0.0, 0.0, _text_opacity)},
         {'text': message, 'y': 30,
          'color': (1.0, 1.0, 1.0, _text_opacity)}])


def clipping_changed_screen_message(near: float, far: float,
                                    *, product: int) -> None:
    vp = _get_viewport(product)
    default_txt = deepcopy(vp.texter().get_default_text())
    near_str = f'{near:.1f}' if near > 0.1 else f'{near:.3f}'
    default_txt[0]['text'] = f'Camera clipping planes ' \
                             f'have been changed: ' \
                             f'{near_str} / {far:.1f}'
    default_txt[0]['color'] = (1.0, 0.0, 1.0, _text_opacity)
    vp.message_to_screen(default_txt)


def operation_calculation_screen_message(operation_name: str,
                                         operation_help: str,
                                         *, product: int) -> None:
    vp = _get_viewport(product)
    vp.message_to_screen(
        [{'text': f'{operation_name} calculating... Please wait',
          'y': 60, 'color': (1.0, 0.0, 0.0, _text_opacity)},
         {'text': operation_help,
          'y': 30, 'color': (1.0, 1.0, 1.0, _text_opacity)}])


def staged_calculation_screen_message(operation_name: str,
                                      operation_help: str,
                                      *, finished_frames: int = 0,
                                      total_frames: int = 1,
                                      current_stage: int = 0,
                                      total_stages: int = 1,
                                      product: int) -> None:
    stages = '' if total_stages == 1 else \
        f'Stage {current_stage}/{total_stages}. '
    vp = _get_viewport(product)
    percent = 100 * finished_frames / total_frames if total_frames != 0 else 0
    vp.message_to_screen(
        [{'text': f'{stages}{operation_name} {percent:.1f}% '
                  f'({finished_frames}/{total_frames})',
          'y': 60, 'color': (1.0, 0.0, 0.0, _text_opacity)},
         {'text': operation_help,
          'y': 30, 'color': (1.0, 1.0, 1.0, _text_opacity)}])


def texture_projection_screen_message(current_num: int,
                                      total_frames: int,
                                      *, product: int) -> None:
    vp = _get_viewport(product)
    vp.message_to_screen(
        [{'text': 'Projection: '
                  f'{current_num}/{total_frames}', 'y': 60,
          'color': (1.0, 0.0, 0.0, _text_opacity)},
         {'text': 'ESC to abort', 'y': 30,
          'color': (1.0, 1.0, 1.0, _text_opacity)}])
