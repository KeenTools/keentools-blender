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

import bpy
from ..addon_config import Config
from ..facebuilder_config import FBConfig


# Functions for Custom Attributes perform
def has_custom_attribute(obj, attr_name):
    return attr_name in obj.keys()


def get_custom_attribute(obj, attr_name):
    return obj[attr_name]


def get_safe_custom_attribute(obj, attr_name):
    if has_custom_attribute(obj, attr_name):
        return obj[attr_name]
    else:
        return None


def get_custom_attribute_variants(obj, attr_names):
    for attr in attr_names:
        res = get_safe_custom_attribute(obj, attr)
        if res:
            return res
    return None


def set_custom_attribute(obj, attr_name, val):
    obj[attr_name] = val


def has_keentools_attributes(obj):
    attr_name = FBConfig.version_prop_name
    if has_custom_attribute(obj, attr_name):
        return True
    return False


def mark_keentools_object(obj):
    set_custom_attribute(obj, Config.core_version_prop_name, Config.addon_version)


def get_collection_by_name(col_name):
    if col_name not in bpy.context.scene.collection.children:
        fb_col = bpy.data.collections.new(col_name)
        bpy.context.scene.collection.children.link(fb_col)
    else:
        fb_col = bpy.context.scene.collection.children[col_name]
    return fb_col


def get_collection_index_by_name(col_name):
    return bpy.data.collections.find(col_name)


def safe_delete_collection(col):
    if col is not None and len(col.all_objects) == 0:
        bpy.data.collections.remove(col)


def new_collection(col_name):
    fb_col = bpy.data.collections.new(col_name)
    bpy.context.scene.collection.children.link(fb_col)
    return fb_col


def get_obj_collection(obj):
    if obj is None:
        return None
    cols = obj.users_collection
    if len(cols) <= 0:
        return None
    return obj.users_collection[0]


def add_to_fb_collection(obj):
    fb_col = new_collection(FBConfig.default_fb_collection_name)
    fb_col.objects.link(obj)
