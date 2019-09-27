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

import os

import bpy.utils.previews


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
        icons_dir = os.path.join(os.path.dirname(__file__), "icons")
        cls.icons.load(
            name, os.path.join(icons_dir, filename), 'IMAGE')

    @classmethod
    def load_icons(cls):
        cls.load_icon("cam_icon", "cam_icon.png")

    @classmethod
    def get_id(cls, name):
        return cls.icons[name].icon_id
