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
import os

import bpy.utils.previews


_ICONS_DIR = "icons"
_ICONS = (("cam_icon", "cam_icon.png"),)


class FBIcons:
    icons = None

    @classmethod
    def register(cls):
        cls.icons = bpy.utils.previews.new()
        cls.load_icons()

    @classmethod
    def unregister(cls):
        bpy.utils.previews.remove(cls.icons)

    @classmethod
    def load_icon(cls, name, filename):
        logger = logging.getLogger(__name__)
        icons_dir = os.path.join(os.path.dirname(__file__), _ICONS_DIR)
        full_path = os.path.join(icons_dir, filename)
        res = cls.icons.load(name, full_path, 'IMAGE')
        logger.debug("ICON:{} {}".format(name, full_path, res))

    @classmethod
    def load_icons(cls):
        for i in _ICONS:
            cls.load_icon(i[0], i[1])

    @classmethod
    def layout_icons(cls, layout):
        # Testing purpose method
        col = layout.column()
        col.scale_y = 0.75
        for i in _ICONS:
            col.label(text=i[0], icon_value=FBIcons.get_id(i[0]))

    @classmethod
    def get_id(cls, name):
        if name in cls.icons.keys():
            return cls.icons[name].icon_id
        else:
            return 0
