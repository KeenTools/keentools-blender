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

import sys
import platform
import bpy

from .addon_config import Config, get_gpu_backend


USER_MESSAGES = {
    'WE_CANNOT_SHIP': [
        'We cannot ship our core library with our addon due to Blender ',
        'license limitations, so you need to install it yourself.'],

    'RESTART_BLENDER_TO_UNLOAD_CORE': [
        'Before installing the new Core version you need '
        'to relaunch Blender.'],

    'PYKEENTOOLS_OK': ['The core library has been installed successfully']
}


ERROR_MESSAGES = {
    'OS_32_BIT': [
        'Error (1010): you have a 32-bit OS or Blender. ',
        'To use our add-on you need a 64-bit OS and Blender. '
    ],

    'BLENDER_32_BIT': [
        'Error (1020): you are using a 32-bit version of Blender. ',
        'To use our add-on you need a 64-bit version of Blender. '],

    'BLENDER_TOO_OLD': [
        'Error (1030): you are using an outdated version of Blender '
        'which we don\'t support. ',
        'Please install the latest official version '
        'of Blender downloaded from their site: www.blender.org'],

    'BLENDER_WITH_UNSUPPORTED_PYTHON': [
        'Error (1040): you are using Blender with an unsupported ',
        'version of Python built in. This may happen when you install ',
        'Blender from Linux repositories. Please install an official ',
        'version of Blender downloaded from www.blender.org website.'],

    'OLD_ADDON': [
        'Error (1050): you have most likely installed an outdated ',
        'version of FaceBuilder add-on. Please download the latest one ',
        'from our web site: https://keentools.io '],

    'NUMPY_PROBLEM': [
        'Error (1060): we have detected a critical issue with '
        'NumPy Python library: ',
        'it\'s either not available or incompatible. ',
        'It can happen when Blender is not using its built-in '
        'Python libraries, ',
        'for some reason relying on the Python libraries '
        'installed in your OS. ',
        'Please try reinstalling Blender using a package from ',
        'the official Blender website: blender.org'],

    'CORE_NOT_INSTALLED': [
        'Error (1070): Core library is not installed.'],

    'INSTALLED_WRONG_INSTEAD_CORE': [
        'Error (1080): you\'ve tried to install either a corrupted archive, ',
        'or something that is not a KeenTools Core library package. ',
        'Please, remove it using the button below, then come to our site ',
        'and download a proper KeenTools Core package and try '
        'to install it again.'],

    'CORE_CANNOT_IMPORT': [
        'Error (1090): the installed Core is corrupted. ',
        'The file you\'ve tried to install seemed to be corrupted. ',
        'Please try to download and install it again. Note that ',
        'versions of the add-on and the Core library should match.'],

    'CORE_HAS_NO_VERSION': [
        'Error (1100): the loaded Core library seems to be corrupted.',
        'You can try to uninstall it using the button bellow, ',
        'and then download and install the Core again.'],

    'CORE_VERSION_PROBLEM': [
        'Error (1110): the installed Core library is outdated. '
        'You can experience issues. ',
        'We recommend you to update the addon and the Core library.'],

    'UNSUPPORTED_GPU_BACKEND': [
        'Error (1120): this version of addon does not support Metal shaders. ',
        'You won\'t be able to use its full functionality ',
        'until you change the back-end to OpenGL.',
        ' ',
        'You can switch to OpenGL back-end in Blender Preferences -> System.',
        'Just select \'OpenGL\' instead of \'Metal\' in dropdown menu.',
        'Then you must restart Blender to apply these changes.',
        ' ',
        'We are working hard to support new shaders in our next versions '
        'of the addon.'],

    'UNKNOWN': ['Unknown error (0000)']
}


def _get_text_scale_y():
    if hasattr(Config, 'text_scale_y'):
        return Config.text_scale_y
    else:
        return 0.75


def split_long_string(txt, length=80):
    return [txt[i:i + length] for i in range(0, len(txt), length)]


def get_system_info():
    txt_arr = []
    txt_arr.append('Blender version: {} API: {}'.format(bpy.app.version_string,
               '.'.join([str(x) for x in bpy.app.version])))
    txt_arr.append('Python: {}'.format(sys.version))
    arch = platform.architecture()
    txt_arr.append('Platform: {} / {}'.format(arch[1], arch[0]))
    txt_arr.append('Machine: {}, {}'.format(platform.machine(),
                                     platform.processor()))
    txt_arr.append('System: {}'.format(platform.platform()))
    txt_arr.append('GPU backend: {}'.format(get_gpu_backend()))
    return txt_arr


def get_gpu_info():
    txt_arr = []
    try:
        import gpu
        txt_arr.append(f'Video: {gpu.platform.renderer_get()}')
        txt_arr.append(f'Vendor: {gpu.platform.vendor_get()}')
        txt_arr.append(f'Version: {gpu.platform.version_get()}')
        txt_arr.append(f'max_texture_size: '
                       f'{gpu.capabilities.max_texture_size_get()}')
        txt_arr.append(f'max_textures: '
                       f'{gpu.capabilities.max_textures_get()}')
    except Exception as err:
        txt_arr.append(str(err))
    return txt_arr


def draw_system_info(layout):
    box = layout.box()
    col = box.column()
    col.scale_y = _get_text_scale_y()
    txt_arr = get_system_info()
    for txt in txt_arr:
        col.label(text=txt)
    return box


def draw_warning_labels(layout, content, alert=True, icon='INFO'):
    row = layout.row()
    col = row.column()
    col.operator(Config.kt_pref_computer_info_idname,
                 text='', icon=icon, emboss=False)

    col = row.column()
    col.alert = alert
    col.scale_y = _get_text_scale_y()
    for txt in content:
        col.label(text=txt)
    return col


def draw_labels(layout, arr):
    for t in arr:
        layout.label(text=t)


def draw_long_label(layout, txt, length=80):
    draw_labels(layout, split_long_string(txt, length))


def draw_long_labels(layout, arr, length=80):
    for txt in arr:
        draw_long_label(layout, txt, length)
