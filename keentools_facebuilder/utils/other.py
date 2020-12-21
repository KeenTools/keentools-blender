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

from . edges import FBEdgeShader2D, FBRasterEdgeShader3D
from . points import FBPoints2D, FBPoints3D
from .. config import get_main_settings


def force_ui_redraw(area_type="PREFERENCES"):
    for window in bpy.data.window_managers['WinMan'].windows:
        for area in window.screen.areas:
            if area.type == area_type:
                area.tag_redraw()


def force_stop_shaders():
    FBEdgeShader2D.handler_list = []
    FBRasterEdgeShader3D.handler_list = []
    FBText.handler_list = []
    FBPoints2D.handler_list = []
    FBPoints3D.handler_list = []
    force_ui_redraw('VIEW_3D')


def _setup_ui_elements(*args):
    try:
        bpy.context.space_data.overlay.show_floor = args[0]
        bpy.context.space_data.overlay.show_axis_x = args[1]
        bpy.context.space_data.overlay.show_axis_y = args[2]
        bpy.context.space_data.overlay.show_cursor = args[3]
    except Exception:
        pass


def hide_ui_elements():
    state = UserState.get_state()
    if state is not None:
        return

    try:
        UserState.put_state(bpy.context.space_data.overlay.show_floor,
                            bpy.context.space_data.overlay.show_axis_x,
                            bpy.context.space_data.overlay.show_axis_y,
                            bpy.context.space_data.overlay.show_cursor)
    except Exception:
        pass
    _setup_ui_elements(False, False, False, False)


def restore_ui_elements():
    state = UserState.get_state()
    if state is None:
        return
    try:
        _setup_ui_elements(*state)
        UserState.reset_state()
    except AttributeError:
        pass


class UserState:
    _state = None

    @classmethod
    def put_state(cls, *args):
        cls._state = (*args,)

    @classmethod
    def get_state(cls):
        return cls._state

    @classmethod
    def reset_state(cls):
        cls._state = None


class FBTimer:
    _active = False

    @classmethod
    def set_active(cls, value=True):
        cls._active = value

    @classmethod
    def set_inactive(cls):
        cls._active = False

    @classmethod
    def is_active(cls):
        return cls._active

    @classmethod
    def _start(cls, callback, persistent=True):
        logger = logging.getLogger(__name__)
        cls._stop(callback)
        bpy.app.timers.register(callback, persistent=persistent)
        logger.debug("REGISTER TIMER")
        cls.set_active()

    @classmethod
    def _stop(cls, callback):
        logger = logging.getLogger(__name__)
        if bpy.app.timers.is_registered(callback):
            logger.debug("UNREGISTER TIMER")
            bpy.app.timers.unregister(callback)
        cls.set_inactive()


class FBStopShaderTimer(FBTimer):
    _uuid = ''
    @classmethod
    def check_pinmode(cls):
        logger = logging.getLogger(__name__)
        settings = get_main_settings()
        if not cls.is_active():
            # Timer works when shouldn't
            logger.debug("STOP SHADER INACTIVE")
            return None
        # Timer is active
        if not settings.pinmode:
            # But we are not in pinmode
            force_stop_shaders()
            cls.stop()
            logger.debug("STOP SHADER FORCE")
            return None
        else:
            if settings.pinmode_id != cls.get_uuid():
                # pinmode id externally changed
                force_stop_shaders()
                cls.stop()
                logger.debug("STOP SHADER FORCED BY PINMODE_ID")
                return None

        # Interval to next call
        return 1.0

    @classmethod
    def get_uuid(cls):
        return cls._uuid

    @classmethod
    def start(cls, uuid=''):
        cls._uuid = uuid
        cls._start(cls.check_pinmode, persistent=True)

    @classmethod
    def stop(cls):
        cls._stop(cls.check_pinmode)


class FBText:
    """ Text on screen output in Modal view"""
    # Test only
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

    def __init__(self):
        self.text_draw_handler = None
        self.message = [
            "Pin Mode ",  # line 1
            "ESC: Exit | LEFT CLICK: Create Pin | RIGHT CLICK: Delete Pin "
            "| TAB: Hide/Show"  # line 2
        ]

    def set_message(self, msg):
        self.message = msg

    @classmethod
    def inc_counter(cls):
        cls._counter += 1
        return cls._counter

    @classmethod
    def get_counter(cls):
        return cls._counter

    def text_draw_callback(self, op, context):
        # Force Stop
        if self.is_handler_list_empty():
            self.unregister_handler()
            return

        settings = get_main_settings()

        # TESTING
        # self.inc_counter()
        camera = settings.get_camera(settings.current_headnum,
                                     settings.current_camnum)
        # Draw text
        if camera is not None and len(self.message) > 0:
            region = context.region
            text = "{0} [{1}]".format(self.message[0], camera.get_image_name())
            subtext = "{} | {}".format(self.message[1], settings.opnum)

            xt = int(region.width / 2.0)

            blf.size(0, 24, 72)
            blf.position(0, xt - blf.dimensions(0, text)[0] / 2, 60, 0)
            blf.draw(0, text)

            blf.size(0, 20, 72)
            blf.position(0, xt - blf.dimensions(0, subtext)[0] / 2, 30, 1)
            blf.draw(0, subtext)  # Text is on screen

    def register_handler(self, args):
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
