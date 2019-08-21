# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2019  KeenTools

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
import logging
import time

import bpy
import blf

from . edges import FBEdgeShader2D, FBEdgeShader3D
from . points import FBPoints2D, FBPoints3D
from .. config import get_main_settings


def force_stop_shaders():
    FBEdgeShader2D.handler_list = []
    FBEdgeShader3D.handler_list = []
    FBText.handler_list = []
    FBPoints2D.handler_list = []
    FBPoints3D.handler_list = []


class FBStopTimer:
    active = False

    @classmethod
    def set_active(cls):
        cls.active = True

    @classmethod
    def set_inactive(cls):
        cls.active = False

    @classmethod
    def is_active(cls):
        return cls.active

    @classmethod
    def check_pinmode(cls):
        logger = logging.getLogger(__name__)
        settings = get_main_settings()
        if not cls.is_active():
            # Timer works when shouldn't
            logger.debug("STOP INACTIVE")
            return None
        # Timer is active
        if not settings.pinmode:
            # But we are not in pinmode
            force_stop_shaders()
            cls.stop()
            logger.debug("STOP FORCE")
            return None

        logger.debug("NEXT CALL")
        # Interval to next call
        return 1.0

    @classmethod
    def start(cls):
        logger = logging.getLogger(__name__)
        cls.stop()
        bpy.app.timers.register(cls.check_pinmode, persistent=True)
        logger.debug("REGISTER TIMER")
        cls.set_active()

    @classmethod
    def stop(cls):
        logger = logging.getLogger(__name__)
        if bpy.app.timers.is_registered(cls.check_pinmode):
            logger.debug("UNREGISTER TIMER")
            bpy.app.timers.unregister(cls.check_pinmode)
        cls.set_inactive()


class FBText:
    """ Text on screen output in Modal view"""
    # Test only
    counter = 0

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

    def __init__(self):
        self.text_draw_handler = None
        self.message = [
            "Pin Mode ",
            "Press 'Esc' to Exit "
        ]

    def set_message(self, msg):
        self.message = msg

    @classmethod
    def inc_counter(cls):
        cls.counter += 1

    def text_draw_callback(self, op, context):
        # Force Stop
        if self.is_handler_list_empty():
            self.unregister_handler()
            return

        self.inc_counter()
        # TESTING
        settings = get_main_settings()
        opnum = settings.opnum
        camnum = settings.current_camnum
        # Draw text
        if len(self.message) > 0:
            region = context.region
            text = "Cam [{0}] {1}".format(camnum, self.message[0])
            # TESTING
            subtext = "{} {}".format(self.message[1], opnum)
            # subtext = self.message[1]

            xt = int(region.width / 2.0)

            blf.size(0, 24, 72)
            blf.position(0, xt - blf.dimensions(0, text)[0] / 2, 60, 0)
            blf.draw(0, text)

            blf.size(0, 20, 72)
            blf.position(0, xt - blf.dimensions(0, subtext)[0] / 2, 30, 1)
            blf.draw(0, subtext)  # Text is on screen

    def register_handler(self, args):
        # Draw text on screen registration
        self.text_draw_handler = bpy.types.SpaceView3D.draw_handler_add(
            self.text_draw_callback, args, "WINDOW", "POST_PIXEL")
        self.add_handler_list(self.text_draw_handler)

    def unregister_handler(self):
        if self.text_draw_handler is not None:
            bpy.types.SpaceView3D.draw_handler_remove(
                self.text_draw_handler, "WINDOW")
            self.remove_handler_list(self.text_draw_handler)
        self.text_draw_handler = None


# --------------
# FPSMeter usage:
# fps = FPSMeter()
# fps.tick()
# print(fps.update_indicator())
class FPSMeter:
    def __init__(self, buf_length=5):
        self.start_time = time.time()
        self.indicator = "None"
        self.counter = 0
        self.buffer = [self.start_time for _ in range(buf_length)]
        self.head = 0
        self.buf_length = len(self.buffer)

    def prev_index(self, ind):
        prev_ind = ind - 1
        if prev_ind < 0:
            prev_ind = self.buf_length
        return prev_ind

    def next_index(self, ind):
        next_ind = ind + 1
        if next_ind >= self.buf_length:
            next_ind = 0
        return next_ind

    def update_indicator(self):
        new_time = self.buffer[self.head]
        old_time = self.buffer[self.next_index(self.head)]
        delta = new_time - old_time
        d = 0.0
        if delta > 0.00001:
            d = (self.buf_length - 1) / delta
        self.indicator = "{0:.2f}".format(d)
        return self.indicator

    def tick(self):
        self.head = self.next_index(self.head)
        self.buffer[self.head] = time.time()
        self.counter += 1
