# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2019-2023  KeenTools

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

from typing import Any

import gpu

from .bpy_common import use_gpu_instead_of_bgl


def bgl_module() -> Any:
    import bgl
    return bgl


def gpu_module() -> Any:
    return gpu


def set_blend_alpha(use_gpu: bool = use_gpu_instead_of_bgl) -> None:
    if use_gpu:
        gpu.state.blend_set('ALPHA')
    else:
        bgl_module().glEnable(bgl_module().GL_BLEND)
        bgl_module().glBlendFunc(bgl_module().GL_SRC_ALPHA,
                                 bgl_module().GL_ONE_MINUS_SRC_ALPHA)


def set_shader_sampler(shader: Any, wireframe_image: Any,
                       use_gpu: bool = use_gpu_instead_of_bgl) -> None:
    if use_gpu:
        shader.uniform_sampler(
            'image', gpu.texture.from_image(wireframe_image))
    else:
        bgl_module().glActiveTexture(bgl_module().GL_TEXTURE0)
        bgl_module().glBindTexture(bgl_module().GL_TEXTURE_2D,
                                   wireframe_image.bindcode)
        shader.uniform_int('image', 0)


def _bool_to_bgl(v: bool) -> Any:
    return bgl_module().GL_FALSE if not v else bgl_module().GL_TRUE


def set_color_mask(r: bool, g: bool, b: bool, a: bool,
                   use_gpu: bool = use_gpu_instead_of_bgl) -> None:
    if use_gpu:
        gpu.state.color_mask_set(r, g, b, a)
    else:
        bgl_module().glColorMask(_bool_to_bgl(r), _bool_to_bgl(g),
                                 _bool_to_bgl(b), _bool_to_bgl(a))


def set_depth_mask(value: bool, use_gpu: bool = use_gpu_instead_of_bgl) -> None:
    if use_gpu:
        gpu.state.depth_mask_set(value)
    else:
        bgl_module().glDepthMask(_bool_to_bgl(value))


def set_depth_test(mode: str = 'LESS_EQUAL',
                   use_gpu: bool = use_gpu_instead_of_bgl) -> None:
    if use_gpu:
        gpu.state.depth_test_set(mode)
    else:
        if mode == 'NONE':
            bgl_module().glDisable(bgl_module().GL_DEPTH_TEST)
        else:
            bgl_module().glEnable(bgl_module().GL_DEPTH_TEST)
            if mode == 'LESS_EQUAL':
                bgl_module().glDepthFunc(bgl_module().GL_LEQUAL)
            elif mode == 'LESS':
                bgl_module().glDepthFunc(bgl_module().GL_LESS)


def set_line_width(line_width: float = 1.0,
                   use_gpu: bool = use_gpu_instead_of_bgl) -> None:
    if use_gpu:
        gpu.state.line_width_set(line_width)
    else:
        bgl_module().glLineWidth(line_width)


def set_point_size(point_size: float,
                   use_gpu: bool = use_gpu_instead_of_bgl) -> None:
    if use_gpu:
        gpu.state.point_size_set(point_size)
    else:
        bgl_module().glPointSize(point_size)


def set_smooth_line(use_gpu: bool = use_gpu_instead_of_bgl) -> None:
    '''
    Only old Blender built-in shaders need for line smoothing
    '''
    if use_gpu:
        pass
    else:
        bgl_module().glEnable(bgl_module().GL_LINE_SMOOTH)
        bgl_module().glHint(bgl_module().GL_LINE_SMOOTH_HINT,
                            bgl_module().GL_NICEST)


def revert_blender_viewport_state(use_gpu: bool = use_gpu_instead_of_bgl) -> None:
    if not use_gpu:
        bgl_module().glDepthMask(bgl_module().GL_TRUE)
        bgl_module().glDisable(bgl_module().GL_DEPTH_TEST)
