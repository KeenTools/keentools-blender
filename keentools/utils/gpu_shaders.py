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

from .kt_logging import KTLogger
from .version import BVersion
from ..addon_config import Config
from .shaders import (flat_color_2d_vertex_shader,
                      flat_color_3d_vertex_shader,
                      circular_dot_fragment_shader,
                      uniform_3d_vertex_local_shader,
                      smooth_3d_fragment_shader,
                      solid_line_vertex_shader,
                      solid_line_fragment_shader,
                      residual_vertex_shader,
                      residual_fragment_shader,
                      simple_fill_vertex_shader,
                      simple_fill_vertex_local_shader,
                      black_fill_fragment_shader,
                      lit_vertex_local_shader,
                      lit_fragment_shader,
                      raster_image_mask_vertex_shader,
                      raster_image_mask_fragment_shader,
                      raster_image_vertex_shader,
                      raster_image_fragment_shader)


_log = KTLogger(__name__)


_use_old_shaders: bool = BVersion.version < (3, 5, 0) or not Config.use_gpu_shaders
_log.output(f'_use_old_shaders: {_use_old_shaders}')


def circular_dot_2d_shader(use_old: bool=_use_old_shaders) -> Any:
    shader_name = 'circular_dot_3d_shader'
    if use_old:
        shader = gpu.types.GPUShader(flat_color_2d_vertex_shader(),
                                     circular_dot_fragment_shader())
        _log.output(_log.color('magenta', f'{shader_name}: Old Shader'))
        return shader

    vert_out = gpu.types.GPUStageInterfaceInfo(f'{shader_name}_interface')
    vert_out.flat('VEC4', 'finalColor')

    shader_info = gpu.types.GPUShaderCreateInfo()
    shader_info.push_constant('MAT4', 'ModelViewProjectionMatrix')
    shader_info.vertex_in(0, 'VEC2', 'pos')
    shader_info.vertex_in(1, 'VEC4', 'color')
    shader_info.vertex_out(vert_out)
    shader_info.fragment_out(0, 'VEC4', 'fragColor')

    shader_info.vertex_source(
        '''
        void main()
        {
            gl_Position = ModelViewProjectionMatrix * vec4(pos, 0.0, 1.0);
            finalColor = color;
        }
        '''
    )

    shader_info.fragment_source(
        '''
        void main() {
                vec2 cxy = 2.0 * gl_PointCoord - 1.0;
                float r = dot(cxy, cxy);
                float delta = fwidth(r);
                float alpha = 1.0 - smoothstep(1.0 - delta, 1.0 + delta, r);
                fragColor = finalColor * alpha;
        }
        '''
    )

    shader = gpu.shader.create_from_info(shader_info)
    del vert_out
    del shader_info
    _log.output(f'{shader_name}: GPU Shader')
    return shader


def circular_dot_3d_shader(use_old: bool=_use_old_shaders) -> Any:
    shader_name = 'circular_dot_3d_shader'
    if use_old:
        shader = gpu.types.GPUShader(flat_color_3d_vertex_shader(),
                                     circular_dot_fragment_shader())
        _log.output(_log.color('magenta', f'{shader_name}: Old Shader'))
        return shader

    vert_out = gpu.types.GPUStageInterfaceInfo(f'{shader_name}_interface')
    vert_out.flat('VEC4', 'finalColor')

    shader_info = gpu.types.GPUShaderCreateInfo()
    shader_info.push_constant('MAT4', 'ModelViewProjectionMatrix')
    shader_info.vertex_in(0, 'VEC3', 'pos')
    shader_info.vertex_in(1, 'VEC4', 'color')
    shader_info.vertex_out(vert_out)
    shader_info.fragment_out(0, 'VEC4', 'fragColor')

    shader_info.vertex_source(
        '''
        void main()
        {
            vec4 pos_4d = vec4(pos, 1.0);
            gl_Position = ModelViewProjectionMatrix * pos_4d;
            finalColor = color;
        }
        '''
    )

    shader_info.fragment_source(
        '''
        void main() {
                vec2 cxy = 2.0 * gl_PointCoord - 1.0;
                float r = dot(cxy, cxy);
                float delta = fwidth(r);
                float alpha = 1.0 - smoothstep(1.0 - delta, 1.0 + delta, r);
                fragColor = finalColor * alpha;
        }
        '''
    )

    shader = gpu.shader.create_from_info(shader_info)
    del vert_out
    del shader_info
    _log.output(f'{shader_name}: GPU Shader')
    return shader


def line_3d_local_shader(use_old: bool=_use_old_shaders) -> Any:
    shader_name = 'line_3d_local_shader'
    if use_old:
        shader = gpu.types.GPUShader(uniform_3d_vertex_local_shader(),
                                     smooth_3d_fragment_shader())
        _log.output(_log.color('magenta', f'{shader_name}: Old Shader'))
        return shader

    vert_out = gpu.types.GPUStageInterfaceInfo(f'{shader_name}_interface')
    vert_out.flat('VEC4', 'finalColor')

    shader_info = gpu.types.GPUShaderCreateInfo()
    shader_info.push_constant('MAT4', 'ModelViewProjectionMatrix')
    shader_info.uniform_buf(0, 'mat4', 'modelMatrix')
    shader_info.push_constant('VEC4', 'color')
    shader_info.push_constant('FLOAT', 'adaptiveOpacity')

    shader_info.vertex_in(0, 'VEC3', 'pos')
    shader_info.vertex_out(vert_out)
    shader_info.fragment_out(0, 'VEC4', 'fragColor')

    shader_info.vertex_source(
        '''
        void main()
        {
            gl_Position = ModelViewProjectionMatrix * modelMatrix * vec4(pos, 1.0);
            finalColor = color;
            finalColor.a = color.a * adaptiveOpacity;
        }
        '''
    )

    txt = '''
        void main()
        {
            fragColor = finalColor;
        }
        '''

    shader_info.fragment_source(txt)

    shader = gpu.shader.create_from_info(shader_info)
    del vert_out
    del shader_info
    _log.output(f'{shader_name}: GPU Shader')
    return shader


def solid_line_2d_shader(use_old: bool=_use_old_shaders) -> Any:
    shader_name = 'solid_line_3d_shader'
    if use_old:
        shader = gpu.types.GPUShader(solid_line_vertex_shader(),
                                     solid_line_fragment_shader())
        _log.output(_log.color('magenta', f'{shader_name}: Old Shader'))
        return shader

    vert_out = gpu.types.GPUStageInterfaceInfo(f'{shader_name}_interface')
    vert_out.flat('VEC4', 'finalColor')

    shader_info = gpu.types.GPUShaderCreateInfo()
    shader_info.push_constant('MAT4', 'ModelViewProjectionMatrix')

    shader_info.vertex_in(0, 'VEC2', 'pos')
    shader_info.vertex_in(1, 'VEC4', 'color')
    shader_info.vertex_out(vert_out)
    shader_info.fragment_out(0, 'VEC4', 'fragColor')

    shader_info.vertex_source(
        '''
        void main()
        {
            gl_Position = ModelViewProjectionMatrix * vec4(pos, 0.0, 1.0);
            finalColor = color;
        }
        '''
    )

    txt = '''
        void main()
        {
            fragColor = finalColor;
        }
        '''

    shader_info.fragment_source(txt)

    shader = gpu.shader.create_from_info(shader_info)
    del vert_out
    del shader_info
    _log.output(f'{shader_name}: GPU Shader')
    return shader


def residual_2d_shader(use_old: bool=_use_old_shaders) -> Any:
    shader_name = 'residual_2d_shader'
    if use_old:
        shader = gpu.types.GPUShader(residual_vertex_shader(),
                                     residual_fragment_shader())
        _log.output(_log.color('magenta', f'{shader_name}: Old Shader'))
        return shader

    vert_out = gpu.types.GPUStageInterfaceInfo(f'{shader_name}_interface')
    vert_out.smooth('VEC4', 'finalColor')
    vert_out.smooth('FLOAT', 'v_LineLength')

    shader_info = gpu.types.GPUShaderCreateInfo()
    shader_info.push_constant('MAT4', 'ModelViewProjectionMatrix')
    shader_info.vertex_in(0, 'VEC2', 'pos')
    shader_info.vertex_in(1, 'VEC4', 'color')
    shader_info.vertex_in(2, 'FLOAT', 'lineLength')
    shader_info.vertex_out(vert_out)
    shader_info.fragment_out(0, 'VEC4', 'fragColor')

    shader_info.vertex_source(
        '''
        void main()
        {
            v_LineLength = lineLength;
            gl_Position = ModelViewProjectionMatrix * vec4(pos, 0.0, 1.0);
            finalColor = color;
        }
        '''
    )

    txt = '''
        void main()
        {
            if (step(sin(v_LineLength), -0.3f) == 1) discard;
            fragColor = finalColor;
        }
        '''

    shader_info.fragment_source(txt)

    shader = gpu.shader.create_from_info(shader_info)
    del vert_out
    del shader_info
    _log.output(f'{shader_name}: GPU Shader')
    return shader


def dashed_2d_shader(use_old: bool=_use_old_shaders) -> Any:
    shader_name = 'dashed_2d_shader'
    if use_old:
        shader = gpu.types.GPUShader(residual_vertex_shader(),
                                     residual_fragment_shader())
        _log.output(_log.color('magenta', f'{shader_name}: Old Shader'))
        return shader

    vert_out = gpu.types.GPUStageInterfaceInfo(f'{shader_name}_interface')
    vert_out.smooth('VEC4', 'finalColor')
    vert_out.smooth('FLOAT', 'v_LineLength')

    shader_info = gpu.types.GPUShaderCreateInfo()
    shader_info.push_constant('MAT4', 'ModelViewProjectionMatrix')
    shader_info.vertex_in(0, 'VEC2', 'pos')
    shader_info.vertex_in(1, 'VEC4', 'color')
    shader_info.vertex_in(2, 'FLOAT', 'lineLength')
    shader_info.vertex_out(vert_out)
    shader_info.fragment_out(0, 'VEC4', 'fragColor')

    shader_info.vertex_source(
        '''
        void main()
        {
            v_LineLength = lineLength;
            gl_Position = ModelViewProjectionMatrix * vec4(pos, 0.0, 1.0);
            finalColor = color;
        }
        '''
    )

    txt = '''
        void main()
        {
            if (mod(v_LineLength + 5.0, 10.0) > 5.5) discard;
            fragColor = finalColor;
        }
        '''

    shader_info.fragment_source(txt)

    shader = gpu.shader.create_from_info(shader_info)
    del vert_out
    del shader_info
    _log.output(f'{shader_name}: GPU Shader')
    return shader


def black_fill_shader(use_old: bool=_use_old_shaders) -> Any:
    shader_name = 'black_fill_shader'
    if use_old:
        shader = gpu.types.GPUShader(simple_fill_vertex_shader(),
                                     black_fill_fragment_shader())
        _log.output(_log.color('magenta', f'{shader_name}: Old Shader'))
        return shader

    shader_info = gpu.types.GPUShaderCreateInfo()
    shader_info.push_constant('MAT4', 'ModelViewProjectionMatrix')
    shader_info.vertex_in(0, 'VEC3', 'pos')
    shader_info.fragment_out(0, 'VEC4', 'fragColor')

    shader_info.vertex_source(
        '''  
        void main()
        {
            gl_Position = ModelViewProjectionMatrix * vec4(pos, 1.0);
        }
        '''
    )

    shader_info.fragment_source(
        '''
        void main()
        {
            fragColor = vec4(0.0, 0.0, 0.0, 1.0);
        }
        '''
    )

    shader = gpu.shader.create_from_info(shader_info)
    del shader_info
    _log.output(f'{shader_name}: GPU Shader')
    return shader


def black_fill_local_shader(use_old: bool=_use_old_shaders) -> Any:
    shader_name = 'black_fill_local_shader'
    if use_old:
        shader = gpu.types.GPUShader(simple_fill_vertex_local_shader(),
                                     black_fill_fragment_shader())
        _log.output(_log.color('magenta', f'{shader_name}: Old Shader'))
        return shader

    shader_info = gpu.types.GPUShaderCreateInfo()
    shader_info.push_constant('MAT4', 'ModelViewProjectionMatrix')
    shader_info.uniform_buf(0, 'mat4', 'modelMatrix')
    shader_info.vertex_in(0, 'VEC3', 'pos')
    shader_info.fragment_out(0, 'VEC4', 'fragColor')

    shader_info.vertex_source(
        '''  
        void main()
        {
            gl_Position = ModelViewProjectionMatrix * modelMatrix * vec4(pos, 1.0);
        }
        '''
    )

    shader_info.fragment_source(
        '''
        void main()
        {
            fragColor = vec4(0.0, 0.0, 0.0, 1.0);
        }
        '''
    )

    shader = gpu.shader.create_from_info(shader_info)
    del shader_info
    _log.output(f'{shader_name}: GPU Shader')
    return shader


def lit_local_shader(use_old: bool=_use_old_shaders) -> Any:
    shader_name = 'lit_local_shader'
    if use_old:
        shader = gpu.types.GPUShader(lit_vertex_local_shader(),
                                     lit_fragment_shader())
        _log.output(_log.color('magenta', f'{shader_name}: Old Shader'))
        return shader

    vert_out = gpu.types.GPUStageInterfaceInfo(f'{shader_name}_interface')
    vert_out.smooth('VEC3', 'calcNormal')
    vert_out.smooth('VEC3', 'outPos')
    vert_out.smooth('VEC3', 'camDir')

    shader_info = gpu.types.GPUShaderCreateInfo()
    shader_info.push_constant('MAT4', 'ModelViewProjectionMatrix')
    shader_info.uniform_buf(0, 'mat4', 'modelMatrix')
    shader_info.push_constant('VEC4', 'color')
    shader_info.push_constant('FLOAT', 'adaptiveOpacity')
    shader_info.push_constant('BOOL', 'ignoreBackface')
    shader_info.push_constant('BOOL', 'litShading')

    shader_info.uniform_buf(1, 'vec3', 'pos1')
    shader_info.uniform_buf(2, 'vec3', 'pos2')
    shader_info.uniform_buf(3, 'vec3', 'pos3')

    shader_info.push_constant('VEC3', 'cameraPos')

    shader_info.vertex_in(0, 'VEC3', 'pos')
    shader_info.vertex_in(1, 'VEC3', 'vertNormal')
    shader_info.vertex_out(vert_out)
    shader_info.fragment_out(0, 'VEC4', 'fragColor')

    shader_info.vertex_source(
        '''
        void main()
        {
            mat4 resultMatrix = ModelViewProjectionMatrix * modelMatrix;
            gl_Position = resultMatrix * vec4(pos, 1.0);
            calcNormal = normalize(vertNormal);
            outPos = pos;
            camDir = normalize(cameraPos - pos);
        }
        '''
    )

    txt = '''
    struct Light
    {
      vec3 position;
      float constantVal;
      float linear;
      float quadratic;
      vec3 ambient;
      vec3 diffuse;
    };

    vec3 evaluatePointLight(Light light, vec3 surfColor, vec3 normal, vec3 fragPos)
    {
        vec3 lightDir = normalize(light.position - fragPos);
        float diff = max(dot(normal, lightDir), 0.0); // cos(angle)

        float distance    = length(light.position - fragPos);
        float attenuation = 1.0 / (light.constantVal + light.linear * distance +
                            light.quadratic * (distance * distance));
        vec3 ambient  = light.ambient;
        vec3 diffuse  = light.diffuse * diff ;

        return attenuation * (ambient + diffuse) * surfColor;
    }

    vec4 to_srgb_gamma_vec4(vec4 color)
    {
        vec3 c = max(color.rgb, vec3(0.0));
        vec3 c1 = c * (1.0 / 12.92);
        vec3 c2 = pow((c + 0.055) * (1.0 / 1.055), vec3(2.4));
        color.rgb = mix(c1, c2, step(vec3(0.04045), c));
        return color;
    }

    vec3 to_srgb_gamma_vec3(vec3 color)
    {
        vec3 c = max(color, vec3(0.0));
        vec3 c1 = c * (1.0 / 12.92);
        vec3 c2 = pow((c + 0.055) * (1.0 / 1.055), vec3(2.4));
        color = mix(c1, c2, step(vec3(0.04045), c));
        return color;
    }

    void main()
    {
        if (ignoreBackface && (dot(calcNormal, camDir) < 0.0)) discard;

        if (litShading){
            Light light1;
            light1.position = pos1;
            light1.constantVal = 1.0;
            light1.linear = 0.0;
            light1.quadratic = 0.0;
            light1.ambient = vec3(0.0, 0.0, 0.0);
            light1.diffuse = vec3(1.0, 1.0, 1.0);

            Light light2;
            light2.position = pos2;
            light2.constantVal = 1.0;
            light2.linear = 0.0;
            light2.quadratic = 0.0;
            light2.ambient = vec3(0.0, 0.0, 0.0);
            light2.diffuse = vec3(1.0, 1.0, 1.0);

            Light light3;
            light3.position = pos3;
            light3.constantVal = 1.0;
            light3.linear = 0.0;
            light3.quadratic = 0.0;
            light3.ambient = vec3(0.0, 0.0, 0.0);
            light3.diffuse = vec3(1.0, 1.0, 1.0);

            fragColor = vec4(
                to_srgb_gamma_vec3(evaluatePointLight(light1, color.rgb, calcNormal, outPos)) +
                to_srgb_gamma_vec3(evaluatePointLight(light2, color.rgb, calcNormal, outPos)) +
                to_srgb_gamma_vec3(evaluatePointLight(light3, color.rgb, calcNormal, outPos)),
                color.a * adaptiveOpacity);
        } else {
            fragColor = vec4(color.rgb, color.a * adaptiveOpacity);
        }
    }
    '''

    shader_info.fragment_source(txt)

    shader = gpu.shader.create_from_info(shader_info)
    del vert_out
    del shader_info
    _log.output(f'{shader_name}: GPU Shader')
    return shader


def raster_image_mask_shader(use_old: bool=_use_old_shaders) -> Any:
    shader_name = 'raster_image_mask_shader'
    if use_old:
        shader = gpu.types.GPUShader(raster_image_mask_vertex_shader(),
                                     raster_image_mask_fragment_shader())
        _log.output(_log.color('magenta', f'{shader_name}: Old Shader'))
        return shader

    vert_out = gpu.types.GPUStageInterfaceInfo(f'{shader_name}_interface')
    vert_out.smooth('VEC2', 'texCoord_interp')

    shader_info = gpu.types.GPUShaderCreateInfo()
    shader_info.push_constant('MAT4', 'ModelViewProjectionMatrix')
    shader_info.push_constant('VEC2', 'left')
    shader_info.push_constant('VEC2', 'right')
    shader_info.push_constant('VEC4', 'color')
    shader_info.push_constant('BOOL', 'inverted')
    shader_info.push_constant('FLOAT', 'maskThreshold')
    shader_info.sampler(0, 'FLOAT_2D', 'image')
    shader_info.vertex_in(0, 'VEC2', 'texCoord')
    shader_info.vertex_in(1, 'VEC2', 'pos')
    shader_info.vertex_out(vert_out)
    shader_info.fragment_out(0, 'VEC4', 'fragColor')

    shader_info.vertex_source(
        '''
        void main()
        {
            gl_Position = ModelViewProjectionMatrix * vec4(
                left.x + pos.x * (right.x - left.x),
                left.y + pos.y * (right.y - left.y),
                0.0, 1.0);
            gl_Position.z = 1.0;
            texCoord_interp = texCoord;
        }
        '''
    )

    txt = '''
        void main()
        {
            vec4 tex = texture(image, texCoord_interp);
            if ((tex[0] + tex[1] + tex[2]) / 3.0 <= maskThreshold) {
                if (!inverted) discard;
                fragColor = color;
            } else {
                if (inverted) discard;
                fragColor = color;
            }
        }
        '''

    shader_info.fragment_source(txt)

    shader = gpu.shader.create_from_info(shader_info)
    del vert_out
    del shader_info
    _log.output(f'{shader_name}: GPU Shader')
    return shader


def raster_image_shader(use_old: bool=_use_old_shaders) -> Any:
    shader_name = 'raster_image_shader'
    if use_old:
        shader = gpu.types.GPUShader(raster_image_vertex_shader(),
                                     raster_image_fragment_shader())
        _log.output(_log.color('magenta', f'{shader_name}: Old Shader'))
        return shader

    vert_out = gpu.types.GPUStageInterfaceInfo(f'{shader_name}_interface')
    vert_out.smooth('VEC2', 'texCoord_interp')

    shader_info = gpu.types.GPUShaderCreateInfo()
    shader_info.push_constant('MAT4', 'ModelViewProjectionMatrix')
    shader_info.push_constant('FLOAT', 'opacity')
    shader_info.sampler(0, 'FLOAT_2D', 'image')
    shader_info.vertex_in(0, 'VEC2', 'texCoord')
    shader_info.vertex_in(1, 'VEC3', 'pos')
    shader_info.vertex_out(vert_out)
    shader_info.fragment_out(0, 'VEC4', 'fragColor')

    shader_info.vertex_source(
        '''
        void main()
        {
          gl_Position = ModelViewProjectionMatrix * vec4(pos, 1.0);
          texCoord_interp = texCoord;
        }
        '''
    )

    txt = '''
        void main()
        {
            fragColor = texture(image, texCoord_interp);
            fragColor.a = opacity;
        }
        '''

    shader_info.fragment_source(txt)

    shader = gpu.shader.create_from_info(shader_info)
    del vert_out
    del shader_info
    _log.output(f'{shader_name}: GPU Shader')
    return shader
