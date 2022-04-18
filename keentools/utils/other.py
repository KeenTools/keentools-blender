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

from .edges import (KTEdgeShader2D,
                    KTScreenRectangleShader2D,
                    GTEdgeShaderAll2D,
                    KTEdgeShader3D,
                    KTEdgeShaderLocal3D)
from ..facebuilder.utils.edges import FBRectangleShader2D, FBRasterEdgeShader3D
from .points import KTPoints2D, KTPoints3D
from ..facebuilder.config import FBConfig, get_fb_settings
from ..utils.attrs import set_custom_attribute, get_safe_custom_attribute
from ..utils.timer import KTTimer
from ..utils.ui_redraw import force_ui_redraw
from ..utils.screen_text import KTScreenText


def force_stop_shaders():
    KTEdgeShader2D.handler_list = []
    KTScreenRectangleShader2D.handler_list = []
    GTEdgeShaderAll2D.handler_list = []
    KTEdgeShader3D.handler_list = []
    FBRectangleShader2D.handler_list = []
    FBRasterEdgeShader3D.handler_list = []
    KTEdgeShaderLocal3D.handler_list = []
    KTScreenText.handler_list = []
    KTPoints2D.handler_list = []
    KTPoints3D.handler_list = []
    force_ui_redraw('VIEW_3D')


def _viewport_ui_attribute_names():
    return ['show_floor', 'show_axis_x', 'show_axis_y', 'show_cursor']


def _get_ui_space_data():
    if hasattr(bpy.context, 'space_data') and hasattr(bpy.context.space_data, 'overlay'):
        return bpy.context.space_data.overlay
    return None


def _setup_viewport_ui_state(state_dict):
    python_obj = _get_ui_space_data()
    if python_obj is None:
        logger = logging.getLogger(__name__)
        logger.error('bpy.context.space_data.overlay does not exist')
        return
    attr_names = _viewport_ui_attribute_names()
    for name in attr_names:
        if name in state_dict.keys() and hasattr(python_obj, name):
            try:
                setattr(python_obj, name, state_dict[name])
            except Exception as err:
                logger = logging.getLogger(__name__)
                logger.error('EXCEPTION _setup_viewport_ui_state')
                logger.error('Exception info: {}'.format(str(err)))


def _get_viewport_ui_state():
    python_obj = _get_ui_space_data()
    attr_names = _viewport_ui_attribute_names()
    res = {}
    for name in attr_names:
        if hasattr(python_obj, name):
            try:
                res[name] = getattr(python_obj, name)
            except Exception as err:
                logger = logging.getLogger(__name__)
                logger.error('EXCEPTION _get_viewport_ui_state')
                logger.error('Exception info: {}'.format(str(err)))
    return res


def _force_show_ui_elements():
    _setup_viewport_ui_state({'show_floor': 1, 'show_axis_x': 1,
                              'show_axis_y': 1, 'show_cursor': 1})


def _force_hide_ui_elements():
    _setup_viewport_ui_state({'show_floor': 0, 'show_axis_x': 0,
                              'show_axis_y': 0, 'show_cursor': 0})


def hide_viewport_ui_elements_and_store_on_object(obj):
    state = _get_viewport_ui_state()
    set_custom_attribute(obj, FBConfig.viewport_state_prop_name, state)
    _force_hide_ui_elements()


def unhide_viewport_ui_element_from_object(obj):
    def _unpack_state(states):
        attr_names = _viewport_ui_attribute_names()
        values = {}
        for name in attr_names:
            if name in states.keys():
                values[name] = states[name]
        return values

    attr_value = get_safe_custom_attribute(obj, FBConfig.viewport_state_prop_name)
    if attr_value is None:
        _force_show_ui_elements()  # For old version compatibility
        return

    try:
        attr_dict = attr_value.to_dict()
    except Exception as err:
        _force_show_ui_elements()
        return

    res = _unpack_state(attr_dict)
    _setup_viewport_ui_state(res)


class KTStopShaderTimer(KTTimer):
    _uuid = ''
    @classmethod
    def check_pinmode(cls):
        logger = logging.getLogger(__name__)
        settings = get_fb_settings()
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
