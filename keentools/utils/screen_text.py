# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2022 KeenTools

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

import bpy
import blf


class KTScreenText:
    """ Text on screen output in Modal view"""
    _counter = 0

    # Store all draw handlers registered by class objects
    handler_list = []

    @classmethod
    def add_handler_list(cls, handler):
        cls.handler_list.append(handler)

    @classmethod
    def remove_handler_list(cls, handler):
        if handler in cls.handler_list:
            cls.handler_list.remove(handler)

    @classmethod
    def is_handler_list_empty(cls):
        return len(cls.handler_list) == 0

    def __init__(self, target_class=bpy.types.SpaceView3D):
        self.text_draw_handler = None
        self._target_class = target_class
        self._work_area = None

        self.defaults = {'color': (1., 1., 1., 0.5),
                         'size': 24,
                         'shadow_color': (0., 0., 0., 0.75),
                         'shadow_blur': 5,
                         'x': None,
                         'y': 60}
        self.set_message(self.get_default_text())

    def get_default_text(self):
        return [
            {'text': 'Pin Mode ',
             'color': (1., 1., 1., 0.5),
             'size': 24,
             'y': 60},  # line 1
            {'text': 'ESC: Exit | LEFT CLICK: Create Pin | '
                     'RIGHT CLICK: Delete Pin | TAB: Hide/Show',
             'color': (1., 1., 1., 0.5),
             'size': 20,
             'y': 30}  # line 2
        ]

    def _fill_all_fields(self, text_arr):
        for row in text_arr:
            for name in self.defaults:
                if name not in row.keys():
                    row[name] = self.defaults[name]
        return text_arr

    def get_target_class(self):
        return self._target_class

    def set_target_class(self, target_class):
        self._target_class = target_class

    def set_message(self, msg):
        self.message = self._fill_all_fields(msg)

    @classmethod
    def inc_counter(cls):
        cls._counter += 1
        return cls._counter

    @classmethod
    def get_counter(cls):
        return cls._counter

    def text_draw_callback(self, context):
        # Force Stop
        if self.is_handler_list_empty():
            self.unregister_handler()
            return

        if self._work_area != context.area:
            return

        if len(self.message) == 0:
            return

        region = context.region
        xc = int(region.width * 0.5)  # horizontal center
        yc = int(region.height * 0.5)  # vertical center
        font_id = 0

        for row in self.message:
            blf.color(font_id, *row['color'])

            blf.enable(font_id, blf.SHADOW)
            blf.shadow(font_id, row['shadow_blur'], *row['shadow_color'])
            blf.shadow_offset(font_id, 1, -1)

            blf.size(font_id, row['size'], 72)

            xp = row['x'] if row['x'] is not None \
                else xc - blf.dimensions(font_id, row['text'])[0] * 0.5
            yp = row['y'] if row['y'] is not None else yc
            blf.position(font_id, xp, yp, 0)
            blf.draw(font_id, row['text'])

    def register_handler(self, context):
        self._work_area = context.area

        self.text_draw_handler = self.get_target_class().draw_handler_add(
            self.text_draw_callback, (context,), 'WINDOW', 'POST_PIXEL')
        self.add_handler_list(self.text_draw_handler)

    def unregister_handler(self):
        if self.text_draw_handler is not None:
            self.get_target_class().draw_handler_remove(
                self.text_draw_handler, 'WINDOW')
            self.remove_handler_list(self.text_draw_handler)
        self.text_draw_handler = None
        self._work_area = None

    def get_work_area(self):
        return self._work_area
