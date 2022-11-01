# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2019-2022 KeenTools

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

from typing import Dict
from collections import namedtuple

from .addon_config import ErrorType


ErrorMessage = namedtuple('ErrorMessage', ['width', 'message'])


_default_width = 400


error_messages: Dict = {
    ErrorType.NoLicense: ErrorMessage(_default_width, [
        'License is not found',
        ' ',
        'You have 0 days of trial left and there is no license installed',
        'or something wrong has happened with the installed license.',
        'Please check the license settings.'
    ]),
    ErrorType.SceneDamaged: ErrorMessage(_default_width, [
        'Scene was damaged',
        ' ',
        'Some objects created by FaceBuilder were missing from the scene.',
        'The scene was restored automatically.'
    ]),
    ErrorType.CannotReconstruct: ErrorMessage(_default_width, [
        'Reconstruction is impossible',
        ' ',
        'Object parameters are invalid or missing.'
    ]),
    ErrorType.CannotCreateObject: ErrorMessage(_default_width, [
        'Cannot create object',
        ' ',
        'An error occurred while creating an object.'
    ]),
    ErrorType.MeshCorrupted: ErrorMessage(_default_width, [
        'Wrong topology',
        ' ',
        'The FaceBuilder mesh is damaged and cannot be used.'
    ]),
    ErrorType.PktProblem: ErrorMessage(_default_width, [
        'KeenTools Core is missing',
        ' ',
        'You need to install KeenTools Core library before using KeenTools addon.'
    ]),
    ErrorType.PktModelProblem: ErrorMessage(_default_width, [
        'KeenTools Core corrupted',
        ' ',
        'Model data cannot be loaded. You need to reinstall KeenTools addon.'
    ]),
    ErrorType.DownloadingProblem: ErrorMessage(650, [
        'Downloading error',
        ' ',
        'An unknown error encountered. The downloaded files might be corrupted. ',
        'You can try downloading them again, '
        'restarting Blender or installing the update manually.',
        'If you want to manually update the add-on: remove the old add-on, ',
        'restart Blender and install the new version of the add-on.'
    ]),
}
