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


import keentools_facebuilder.blender_independent_packages.pykeentools_loader as pkt

from . config import BuilderType, Config


class UniBuilder:
    def __init__(self, builder_type=BuilderType.FaceBuilder,
                 ver=Config.unknown_mod_ver):  # const
        self.builder_type = BuilderType.NoneBuilder
        self.builder = None
        self.version = ver

        if builder_type == BuilderType.FaceBuilder:
            self.init_facebuilder(ver)
        elif builder_type == BuilderType.BodyBuilder:
            self.init_bodybuilder()

    def init_facebuilder(self, ver=Config.unknown_mod_ver):
        latest_version = pkt.module().FaceBuilder.latest_face_version()
        if ver == Config.unknown_mod_ver or ver > latest_version:
            self.builder = pkt.module().FaceBuilder(latest_version)
            self.version = latest_version
        else:
            self.builder = pkt.module().FaceBuilder(ver)
            self.version = ver
        self.builder_type = BuilderType.FaceBuilder

    def init_bodybuilder(self, ver=Config.unknown_mod_ver):
        self.builder = pkt.module().BodyBuilder()
        self.builder_type = BuilderType.BodyBuilder
        self.version = ver

    def get_builder(self):
        return self.builder

    def get_version(self):
        return self.version

    def get_latest_version(self):
        if self.builder_type in {BuilderType.NoneBuilder,
                                 BuilderType.FaceBuilder}:
            return pkt.module().FaceBuilder.latest_face_version()
        else:
            return Config.unknown_mod_ver

    def get_builder_type(self):
        return self.builder_type

    def new_builder(self, builder_type=BuilderType.NoneBuilder,
                    ver=Config.unknown_mod_ver):
        b_type = builder_type
        if builder_type == BuilderType.NoneBuilder:
            b_type = self.builder_type

        if b_type == BuilderType.FaceBuilder:
            self.init_facebuilder(ver)
        elif b_type == BuilderType.BodyBuilder:
            self.init_bodybuilder(ver)
        return self.builder

    def sync_version(self, ver=Config.unknown_mod_ver):
        if self.version == ver and self.version != Config.unknown_mod_ver:
            return self.builder
        if self.builder_type == BuilderType.FaceBuilder:
            self.init_facebuilder(ver)
        elif self.builder_type == BuilderType.BodyBuilder:
            self.init_bodybuilder(ver)
        return self.builder
