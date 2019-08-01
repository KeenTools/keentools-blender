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


from pykeentools import FaceBuilder
from pykeentools import BodyBuilder

from . config import BuilderType


class UniBuilder:
    def __init__(self, builder_type=BuilderType.FaceBuilder, ver=-1):
        self.builder_type = BuilderType.NoneBuilder
        self.builder = None
        self.version = -1

        if builder_type == BuilderType.FaceBuilder:
            self.init_facebuilder(ver)
        elif builder_type == BuilderType.BodyBuilder:
            self.init_bodybuilder()
        print("END UNIBUILDER")

    def init_facebuilder(self, ver):
        print("INIT FB")
        if ver < 0:
            latest_version = FaceBuilder.latest_face_version()
            self.builder = FaceBuilder(latest_version)
            self.version = latest_version
        else:
            self.builder = FaceBuilder(ver)
            self.version = ver
        self.builder_type = BuilderType.FaceBuilder
        print("END INIT FB")


    def init_bodybuilder(self):
        self.builder = BodyBuilder()
        self.builder_type = BuilderType.BodyBuilder
        self.version = -1

    def get_builder(self):
        return self.builder

    def get_version(self):
        return self.version

    def get_latest_version(self):
        if self.builder_type == BuilderType.NoneBuilder:
            return FaceBuilder.latest_face_version()
        else:
            return -1

    def get_builder_type(self):
        return self.builder_type

    def new_builder(self, builder_type=BuilderType.NoneBuilder):
        b_type = builder_type
        if builder_type == BuilderType.NoneBuilder:
            b_type = self.builder_type

        if b_type == BuilderType.FaceBuilder:
            self.init_facebuilder(-1)  # const!
        elif b_type == BuilderType.BodyBuilder:
            self.init_bodybuilder()
        return self.builder
