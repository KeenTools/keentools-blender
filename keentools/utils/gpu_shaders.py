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


_log = KTLogger(__name__)


_use_old_shaders: bool = BVersion.use_old_bgl_shaders
_log.output(f'_use_old_shaders: {_use_old_shaders}')


def circular_dot_2d_shader(use_old: bool = _use_old_shaders) -> Any:
    shader_name = 'circular_dot_3d_shader'

    vertex_vars = '''
    uniform mat4 ModelViewProjectionMatrix;
    in vec2 pos;
    in vec4 color;
    flat out vec4 finalColor;
    '''

    vertex_glsl = '''
    void main()
    {
        gl_Position = ModelViewProjectionMatrix * vec4(pos, 0.0, 1.0);
        finalColor = color;
    }
    '''

    fragment_vars = '''
    flat in vec4 finalColor;
    out vec4 fragColor;
    '''

    fragment_glsl = '''
    void main() {
        vec2 cxy = 2.0 * gl_PointCoord - 1.0;
        float r = dot(cxy, cxy);
        float delta = fwidth(r);
        float alpha = 1.0 - smoothstep(1.0 - delta, 1.0 + delta, r);
        if (alpha <= 0.0) discard;
        fragColor = finalColor * alpha;
    }
    '''

    if use_old:
        shader = gpu.types.GPUShader(vertex_vars + vertex_glsl,
                                     fragment_vars + fragment_glsl)
        _log.magenta(f'{shader_name}: Old Shader')
        return shader

    vert_out = gpu.types.GPUStageInterfaceInfo(f'{shader_name}_interface')
    vert_out.flat('VEC4', 'finalColor')

    shader_info = gpu.types.GPUShaderCreateInfo()
    shader_info.push_constant('MAT4', 'ModelViewProjectionMatrix')
    shader_info.vertex_in(0, 'VEC2', 'pos')
    shader_info.vertex_in(1, 'VEC4', 'color')
    shader_info.vertex_out(vert_out)
    shader_info.fragment_out(0, 'VEC4', 'fragColor')

    shader_info.vertex_source(vertex_glsl)
    shader_info.fragment_source(fragment_glsl)

    shader = gpu.shader.create_from_info(shader_info)
    _log.output(f'{shader_name}: GPU Shader')
    return shader


def circular_dot_3d_shader(use_old: bool = _use_old_shaders) -> Any:
    shader_name = 'circular_dot_3d_shader'

    vertex_vars = '''
    uniform mat4 ModelViewProjectionMatrix;
    in vec3 pos;
    in vec4 color;
    flat out vec4 finalColor;
    '''

    vertex_glsl = '''
    void main()
    {
        gl_Position = ModelViewProjectionMatrix * vec4(pos, 1.0);
        finalColor = color;
    }
    '''

    fragment_vars = '''
    flat in vec4 finalColor;
    out vec4 fragColor;
    '''

    fragment_glsl = '''
    void main() 
    {
        vec2 cxy = 2.0 * gl_PointCoord - 1.0;
        float r = dot(cxy, cxy);
        float delta = fwidth(r);
        float alpha = 1.0 - smoothstep(1.0 - delta, 1.0 + delta, r);
        if (alpha <= 0.0) discard;
        fragColor = finalColor * alpha;
    }
    '''

    if use_old:
        shader = gpu.types.GPUShader(vertex_vars + vertex_glsl,
                                     fragment_vars + fragment_glsl)
        _log.magenta(f'{shader_name}: Old Shader')
        return shader

    vert_out = gpu.types.GPUStageInterfaceInfo(f'{shader_name}_interface')
    vert_out.flat('VEC4', 'finalColor')

    shader_info = gpu.types.GPUShaderCreateInfo()
    shader_info.push_constant('MAT4', 'ModelViewProjectionMatrix')
    shader_info.vertex_in(0, 'VEC3', 'pos')
    shader_info.vertex_in(1, 'VEC4', 'color')
    shader_info.vertex_out(vert_out)
    shader_info.fragment_out(0, 'VEC4', 'fragColor')

    shader_info.vertex_source(vertex_glsl)
    shader_info.fragment_source(fragment_glsl)

    shader = gpu.shader.create_from_info(shader_info)
    _log.output(f'{shader_name}: GPU Shader')
    return shader


def line_3d_local_shader(use_old: bool = _use_old_shaders) -> Any:
    shader_name = 'line_3d_local_shader'

    vertex_vars = '''
    uniform mat4 ModelViewProjectionMatrix;
    uniform mat4 modelMatrix;
    uniform vec4 color;
    uniform float adaptiveOpacity;
    in vec3 pos;
    out vec4 finalColor;
    '''

    vertex_glsl = '''
    void main()
    {
        gl_Position = ModelViewProjectionMatrix * modelMatrix * vec4(pos, 1.0);
        finalColor = color;
        finalColor.a = color.a * adaptiveOpacity;
    }
    '''

    fragment_vars = '''
    in vec4 finalColor;
    out vec4 fragColor;
    '''

    # TODO: add sRGB color mapping
    fragment_glsl = '''
    void main()
    {
        fragColor = finalColor;
    }
    '''

    if use_old:
        shader = gpu.types.GPUShader(vertex_vars + vertex_glsl,
                                     fragment_vars + fragment_glsl)
        _log.magenta(f'{shader_name}: Old Shader')
        return shader

    vert_out = gpu.types.GPUStageInterfaceInfo(f'{shader_name}_interface')
    vert_out.flat('VEC4', 'finalColor')

    shader_info = gpu.types.GPUShaderCreateInfo()
    shader_info.push_constant('MAT4', 'ModelViewProjectionMatrix')
    shader_info.push_constant('MAT4', 'modelMatrix')
    shader_info.push_constant('VEC4', 'color')
    shader_info.push_constant('FLOAT', 'adaptiveOpacity')

    shader_info.vertex_in(0, 'VEC3', 'pos')
    shader_info.vertex_out(vert_out)
    shader_info.fragment_out(0, 'VEC4', 'fragColor')

    shader_info.vertex_source(vertex_glsl)
    shader_info.fragment_source(fragment_glsl)

    shader = gpu.shader.create_from_info(shader_info)
    _log.output(f'{shader_name}: GPU Shader')
    return shader


def solid_line_2d_shader(use_old: bool = _use_old_shaders) -> Any:
    shader_name = 'solid_line_3d_shader'

    vertex_vars = '''
    uniform mat4 ModelViewProjectionMatrix;
    in vec2 pos;
    in vec4 color;
    flat out vec4 finalColor;
    '''

    vertex_glsl = '''
    void main()
    {
        gl_Position = ModelViewProjectionMatrix * vec4(pos, 0.0, 1.0);
        finalColor = color;
    }
    '''

    fragment_vars = '''
    flat in vec4 finalColor;
    out vec4 fragColor;
    '''

    # TODO: add sRGB color mapping
    fragment_glsl = '''
    void main()
    {
        fragColor = finalColor;
    }
    '''

    if use_old:
        shader = gpu.types.GPUShader(vertex_vars + vertex_glsl,
                                     fragment_vars + fragment_glsl)
        _log.magenta(f'{shader_name}: Old Shader')
        return shader

    vert_out = gpu.types.GPUStageInterfaceInfo(f'{shader_name}_interface')
    vert_out.flat('VEC4', 'finalColor')

    shader_info = gpu.types.GPUShaderCreateInfo()
    shader_info.push_constant('MAT4', 'ModelViewProjectionMatrix')

    shader_info.vertex_in(0, 'VEC2', 'pos')
    shader_info.vertex_in(1, 'VEC4', 'color')
    shader_info.vertex_out(vert_out)
    shader_info.fragment_out(0, 'VEC4', 'fragColor')

    shader_info.vertex_source(vertex_glsl)
    shader_info.fragment_source(fragment_glsl)

    shader = gpu.shader.create_from_info(shader_info)
    _log.output(f'{shader_name}: GPU Shader')
    return shader


def dashed_2d_shader(use_old: bool = _use_old_shaders, *,
                     start: float = 5.0, step: float = 10.0,
                     threshold: float = 5.5) -> Any:
    shader_name = 'dashed_2d_shader'

    vertex_vars = '''
    uniform mat4 ModelViewProjectionMatrix;
    in vec2 pos;
    in float lineLength;
    in vec4 color;
    flat out vec4 finalColor;
    out float v_LineLength;
    '''

    vertex_glsl = '''
    void main()
    {
        gl_Position = ModelViewProjectionMatrix * vec4(pos, 0.0, 1.0);
        finalColor = color;
        v_LineLength = lineLength;
    }
    '''

    fragment_vars = '''
    flat in vec4 finalColor;
    in float v_LineLength;            
    out vec4 fragColor;
    '''

    fragment_glsl = '''
    void main()
    {
        if (mod(v_LineLength + ''' + f'{start}, {step}) > {threshold}' + ''') discard;
        fragColor = finalColor;
    }
    '''

    if use_old:
        shader = gpu.types.GPUShader(vertex_vars + vertex_glsl,
                                     fragment_vars + fragment_glsl)
        _log.magenta(f'{shader_name}: Old Shader')
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

    shader_info.vertex_source(vertex_glsl)
    shader_info.fragment_source(fragment_glsl)

    shader = gpu.shader.create_from_info(shader_info)
    _log.output(f'{shader_name}: GPU Shader')
    return shader


def raster_image_mask_shader(use_old: bool = _use_old_shaders) -> Any:
    shader_name = 'raster_image_mask_shader'

    vertex_vars = '''
    uniform mat4 ModelViewProjectionMatrix;
    uniform vec2 left;
    uniform vec2 right;

    in vec2 texCoord;
    in vec2 pos;
    out vec2 texCoord_interp;
    '''

    vertex_glsl = '''
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

    fragment_vars = '''
    uniform sampler2D image;
    uniform vec4 color;
    uniform bool inverted;
    uniform float maskThreshold;
    uniform int channel;

    in vec2 texCoord_interp;
    out vec4 fragColor;
    '''

    fragment_glsl = '''
    void main()
    {
        vec4 tex = texture(image, texCoord_interp);

        float t = 0.0;
        int denom = 0;
        if ((channel & 1) != 0) { denom++; t += tex[0]; }
        if ((channel & 2) != 0) { denom++; t += tex[1]; }
        if ((channel & 4) != 0) { denom++; t += tex[2]; }
        if ((channel & 8) != 0) { denom++; t += tex[3]; }

        if (denom != 0) { t = t / denom; }

        if (t <= maskThreshold) {
            if (!inverted) discard;
            fragColor = color;
        } else {
            if (inverted) discard;
            fragColor = color;
        }
    }
    '''

    if use_old:
        shader = gpu.types.GPUShader(vertex_vars + vertex_glsl,
                                     fragment_vars + fragment_glsl)
        _log.magenta(f'{shader_name}: Old Shader')
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
    shader_info.push_constant('INT', 'channel')
    shader_info.sampler(0, 'FLOAT_2D', 'image')
    shader_info.vertex_in(0, 'VEC2', 'texCoord')
    shader_info.vertex_in(1, 'VEC2', 'pos')
    shader_info.vertex_out(vert_out)
    shader_info.fragment_out(0, 'VEC4', 'fragColor')

    shader_info.vertex_source(vertex_glsl)
    shader_info.fragment_source(fragment_glsl)

    shader = gpu.shader.create_from_info(shader_info)
    _log.output(f'{shader_name}: GPU Shader')
    return shader


def raster_image_shader(use_old: bool = _use_old_shaders) -> Any:
    shader_name = 'raster_image_shader'

    vertex_vars = '''
    uniform mat4 ModelViewProjectionMatrix;
    uniform mat4 modelMatrix;
    uniform vec3 cameraPos;
    uniform vec2 viewportSize;
    uniform float lineWidth;

    in vec2 texCoord;
    in vec3 pos;
    in vec3 opp;
    in vec3 vertNormal;
    out vec2 texCoord_interp;
    out vec4 vCenterLine;
    out vec3 calcNormal;
    out vec3 camDir;
    '''

    vertex_glsl = '''
    void main()
    {
        float filterRadius = 0.5;
        mat4 resultMatrix = ModelViewProjectionMatrix * modelMatrix;

        float bandWidth = lineWidth + 2.0 * filterRadius;

        vec4 v1 = resultMatrix * vec4(pos, 1.0);
        vec4 v2 = resultMatrix * vec4(opp, 1.0);
        vec2 pix = vec2(2, 2) / viewportSize;

        vCenterLine = v1;

        vec2 p1 = v1.xy / v1.w;
        vec2 p2 = v2.xy / v2.w;
        vec2 dd = 0.5 * normalize(vec2(p1.y - p2.y, p2.x - p1.x) * viewportSize) * bandWidth;
        if (gl_VertexID % 3 == 2){
            dd = -dd;
        }

        v1.xy += dd * pix * v1.w;

        gl_Position = v1;
        texCoord_interp = texCoord;
        calcNormal = normalize(vertNormal);
        camDir = normalize(cameraPos - pos);
    }
    '''

    fragment_vars = '''
    uniform vec2 viewportSize;
    uniform float lineWidth;
    uniform sampler2D image;
    uniform float opacity;
    uniform float adaptiveOpacity;
    uniform bool ignoreBackface;
    in vec2 texCoord_interp;
    in vec4 vCenterLine;
    in vec3 camDir;
    in vec3 calcNormal;
    out vec4 fragColor;
    '''

    fragment_glsl = '''
    float calcAntialiasing(float d, float width, float filterRad)
    {
        return min(1.0, 0.5 + (width * 0.5 - d) / (2.0 * filterRad));
    }

    void main()
    {
        if (ignoreBackface && (dot(calcNormal, camDir) < 0.0)) discard;

        float filterRadius = 0.5;
        float d = length(gl_FragCoord.xy - 0.5 * (vCenterLine.xy / vCenterLine.w + vec2(1, 1)) * viewportSize);
        float antiAliasing = calcAntialiasing(d, lineWidth, filterRadius);
        if (antiAliasing <= 0.0) discard;

        fragColor = texture(image, texCoord_interp);
        fragColor.a = opacity * antiAliasing * adaptiveOpacity;
    }
    '''

    if use_old:
        shader = gpu.types.GPUShader(vertex_vars + vertex_glsl,
                                     fragment_vars + fragment_glsl)
        _log.magenta(f'{shader_name}: Old Shader')
        return shader

    vert_out = gpu.types.GPUStageInterfaceInfo(f'{shader_name}_interface')
    vert_out.smooth('VEC2', 'texCoord_interp')
    vert_out.smooth('VEC4', 'vCenterLine')
    vert_out.smooth('VEC3', 'calcNormal')
    vert_out.smooth('VEC3', 'camDir')

    shader_info = gpu.types.GPUShaderCreateInfo()
    shader_info.push_constant('MAT4', 'ModelViewProjectionMatrix')
    shader_info.push_constant('MAT4', 'modelMatrix')
    shader_info.push_constant('VEC3', 'cameraPos')
    shader_info.push_constant('FLOAT', 'opacity')
    shader_info.push_constant('FLOAT', 'adaptiveOpacity')
    shader_info.sampler(0, 'FLOAT_2D', 'image')

    shader_info.push_constant('VEC2', 'viewportSize')
    shader_info.push_constant('FLOAT', 'lineWidth')

    shader_info.push_constant('BOOL', 'ignoreBackface')

    shader_info.vertex_in(0, 'VEC3', 'pos')
    shader_info.vertex_in(1, 'VEC3', 'opp')
    shader_info.vertex_in(2, 'VEC3', 'vertNormal')
    shader_info.vertex_in(3, 'VEC2', 'texCoord')
    shader_info.vertex_out(vert_out)
    shader_info.fragment_out(0, 'VEC4', 'fragColor')

    shader_info.vertex_source(vertex_glsl)
    shader_info.fragment_source(fragment_glsl)

    shader = gpu.shader.create_from_info(shader_info)
    _log.output(f'{shader_name}: GPU Shader')
    return shader


def uniform_color_3d_shader(use_old: bool = _use_old_shaders) -> Any:
    shader_name = 'uniform_color_3d_shader'

    vertex_vars = '''
    uniform mat4 ModelViewProjectionMatrix;
    uniform mat4 modelMatrix;
    uniform vec2 viewportSize;
    uniform float lineWidth;
    in vec3 pos;
    in vec3 opp;
    out vec4 vCenterLine;
    '''

    vertex_glsl = '''
    void main()
    {
        float filterRadius = 0.5;
        mat4 resultMatrix = ModelViewProjectionMatrix * modelMatrix;

        float bandWidth = lineWidth + 2.0 * filterRadius;

        vec4 v1 = resultMatrix * vec4(pos, 1.0);
        vec4 v2 = resultMatrix * vec4(opp, 1.0);
        vec2 pix = vec2(2, 2) / viewportSize;

        vCenterLine = v1;

        vec2 p1 = v1.xy / v1.w;
        vec2 p2 = v2.xy / v2.w;
        vec2 dd = 0.5 * normalize(vec2(p1.y - p2.y, p2.x - p1.x) * viewportSize) * bandWidth;
        if (gl_VertexID % 3 == 2){
            dd = -dd;
        }

        v1.xy += dd * pix * v1.w;

        gl_Position = v1;
    }
    '''

    fragment_vars = '''
    uniform vec2 viewportSize;
    uniform float lineWidth;
    uniform vec4 color;
    uniform float adaptiveOpacity;
    in vec4 vCenterLine;
    out vec4 fragColor;
    '''

    fragment_glsl = '''
    float calcAntialiasing(float d, float width, float filterRad)
    {
        return min(1.0, 0.5 + (width * 0.5 - d) / (2.0 * filterRad));
    }

    vec4 to_srgb_gamma_vec4(vec4 col)
    {
        vec3 c = max(col.rgb, vec3(0.0));
        vec3 c1 = c * (1.0 / 12.92);
        vec3 c2 = pow((c + 0.055) * (1.0 / 1.055), vec3(2.4));
        col.rgb = mix(c1, c2, step(vec3(0.04045), c));
        return col;
    }

    void main()
    {
        float filterRadius = 0.5;
        float d = length(gl_FragCoord.xy - 0.5 * (vCenterLine.xy / vCenterLine.w + vec2(1, 1)) * viewportSize);
        float antiAliasing = calcAntialiasing(d, lineWidth, filterRadius);
        if (antiAliasing <= 0.0) discard;

        fragColor = to_srgb_gamma_vec4(vec4(color.rgb, color.a * antiAliasing * adaptiveOpacity));
    }
    '''

    if use_old:
        shader = gpu.types.GPUShader(vertex_vars + vertex_glsl,
                                     fragment_vars + fragment_glsl)
        _log.magenta(f'{shader_name}: Old Shader')
        return shader

    vert_out = gpu.types.GPUStageInterfaceInfo(f'{shader_name}_interface')
    vert_out.smooth('VEC4', 'vCenterLine')

    shader_info = gpu.types.GPUShaderCreateInfo()
    shader_info.push_constant('MAT4', 'ModelViewProjectionMatrix')
    shader_info.push_constant('MAT4', 'modelMatrix')
    shader_info.push_constant('VEC4', 'color')
    shader_info.push_constant('FLOAT', 'adaptiveOpacity')

    shader_info.push_constant('VEC2', 'viewportSize')
    shader_info.push_constant('FLOAT', 'lineWidth')

    shader_info.vertex_in(0, 'VEC3', 'pos')
    shader_info.vertex_in(1, 'VEC3', 'opp')
    shader_info.vertex_out(vert_out)
    shader_info.fragment_out(0, 'VEC4', 'fragColor')

    shader_info.vertex_source(vertex_glsl)
    shader_info.fragment_source(fragment_glsl)

    shader = gpu.shader.create_from_info(shader_info)
    _log.output(f'{shader_name}: GPU Shader')
    return shader


def black_offset_fill_local_shader(use_old: bool = _use_old_shaders) -> Any:
    shader_name = 'black_offset_fill_local_shader'

    vertex_vars = '''
    uniform mat4 ModelViewProjectionMatrix;
    uniform mat4 modelMatrix;
    uniform float offset;
    in vec3 pos;
    '''

    vertex_glsl = '''
    void main()
    {
        vec4 pp = ModelViewProjectionMatrix * modelMatrix * vec4(pos, 1.0);
        gl_Position = pp + vec4(0.0, 0.0, offset * (pp.w - pp.z), 0.0);
    }
    '''

    fragment_vars = '''
    out vec4 fragColor;
    '''

    fragment_glsl = '''
    void main()
    {
        fragColor = vec4(0.0, 0.0, 0.0, 1.0);
    }
    '''

    if use_old:
        shader = gpu.types.GPUShader(vertex_vars + vertex_glsl,
                                     fragment_vars + fragment_glsl)
        _log.magenta(f'{shader_name}: Old Shader')
        return shader

    shader_info = gpu.types.GPUShaderCreateInfo()
    shader_info.push_constant('MAT4', 'ModelViewProjectionMatrix')
    shader_info.push_constant('MAT4', 'modelMatrix')
    shader_info.push_constant('FLOAT', 'offset')
    shader_info.vertex_in(0, 'VEC3', 'pos')
    shader_info.fragment_out(0, 'VEC4', 'fragColor')

    shader_info.vertex_source(vertex_glsl)
    shader_info.fragment_source(fragment_glsl)

    shader = gpu.shader.create_from_info(shader_info)
    _log.output(f'{shader_name}: GPU Shader')
    return shader


def lit_aa_local_shader(use_old: bool = _use_old_shaders) -> Any:
    shader_name = 'lit_aa_local_shader'

    vertex_vars = '''
    uniform mat4 ModelViewProjectionMatrix;
    uniform mat4 modelMatrix;
    uniform vec3 cameraPos;

    uniform vec2 viewportSize;
    uniform float lineWidth;

    in vec3 pos;
    in vec3 opp;
    in vec3 vertNormal;
    out vec3 calcNormal;
    out vec3 outPos;
    out vec3 camDir;
    out vec4 vCenterLine;
    '''

    vertex_glsl = '''
    void main()
    {
        float filterRadius = 0.5;
        mat4 resultMatrix = ModelViewProjectionMatrix * modelMatrix;

        float bandWidth = lineWidth + 2.0 * filterRadius;

        vec4 v1 = resultMatrix * vec4(pos, 1.0);
        vec4 v2 = resultMatrix * vec4(opp, 1.0);
        vec2 pix = vec2(2, 2) / viewportSize;

        vCenterLine = v1;

        vec2 p1 = v1.xy / v1.w;
        vec2 p2 = v2.xy / v2.w;
        vec2 dd = 0.5 * normalize(vec2(p1.y - p2.y, p2.x - p1.x) * viewportSize) * bandWidth;
        if (gl_VertexID % 3 == 2){
            dd = -dd;
        }

        v1.xy += dd * pix * v1.w;

        gl_Position = v1;
        calcNormal = normalize(vertNormal);
        outPos = pos;
        camDir = normalize(cameraPos - pos);
    }
    '''

    fragment_vars = '''
    uniform vec4 color;
    uniform float adaptiveOpacity;
    uniform bool ignoreBackface;
    uniform bool litShading;
    uniform vec3 pos1;
    uniform vec3 pos2;
    uniform vec3 pos3;

    uniform vec2 viewportSize;
    uniform float lineWidth;

    in vec4 finalColor;
    in vec3 outPos;
    in vec3 camDir;
    in vec3 calcNormal;
    in vec4 vCenterLine;
    out vec4 fragColor;
    '''

    fragment_glsl = '''
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

    vec4 to_srgb_gamma_vec4(vec4 col)
    {
        vec3 c = max(col.rgb, vec3(0.0));
        vec3 c1 = c * (1.0 / 12.92);
        vec3 c2 = pow((c + 0.055) * (1.0 / 1.055), vec3(2.4));
        col.rgb = mix(c1, c2, step(vec3(0.04045), c));
        return col;
    }

    vec3 to_srgb_gamma_vec3(vec3 col)
    {
        vec3 c = max(col, vec3(0.0));
        vec3 c1 = c * (1.0 / 12.92);
        vec3 c2 = pow((c + 0.055) * (1.0 / 1.055), vec3(2.4));
        col = mix(c1, c2, step(vec3(0.04045), c));
        return col;
    }

    float calcAntialiasing(float d, float width, float filterRad)
    {
        return min(1.0, 0.5 + (width * 0.5 - d) / (2.0 * filterRad));
    }

    void main()
    {
        if (ignoreBackface && (dot(calcNormal, camDir) < 0.0)) discard;

        float filterRadius = 0.5;
        float d = length(gl_FragCoord.xy - 0.5 * (vCenterLine.xy / vCenterLine.w + vec2(1, 1)) * viewportSize);
        float antiAliasing = calcAntialiasing(d, lineWidth, filterRadius);
        if (antiAliasing <= 0.0) discard;

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
                color.a * antiAliasing * adaptiveOpacity);
        } else {
            fragColor = vec4(color.rgb, color.a * antiAliasing * adaptiveOpacity);
        }
    }
    '''

    if use_old:
        shader = gpu.types.GPUShader(vertex_vars + vertex_glsl,
                                     fragment_vars + fragment_glsl)
        _log.magenta(f'{shader_name}: Old Shader')
        return shader

    vert_out = gpu.types.GPUStageInterfaceInfo(f'{shader_name}_interface')
    vert_out.smooth('VEC3', 'calcNormal')
    vert_out.smooth('VEC3', 'outPos')
    vert_out.smooth('VEC3', 'camDir')
    vert_out.smooth('VEC4', 'vCenterLine')

    shader_info = gpu.types.GPUShaderCreateInfo()
    shader_info.push_constant('MAT4', 'ModelViewProjectionMatrix')
    shader_info.push_constant('MAT4', 'modelMatrix')

    shader_info.push_constant('VEC2', 'viewportSize')
    shader_info.push_constant('FLOAT', 'lineWidth')

    shader_info.push_constant('VEC4', 'color')
    shader_info.push_constant('FLOAT', 'adaptiveOpacity')
    shader_info.push_constant('BOOL', 'ignoreBackface')
    shader_info.push_constant('BOOL', 'litShading')

    shader_info.push_constant('VEC3', 'pos1')
    shader_info.push_constant('VEC3', 'pos2')
    shader_info.push_constant('VEC3', 'pos3')

    shader_info.push_constant('VEC3', 'cameraPos')

    shader_info.vertex_in(0, 'VEC3', 'pos')
    shader_info.vertex_in(1, 'VEC3', 'vertNormal')
    shader_info.vertex_in(2, 'VEC3', 'opp')
    shader_info.vertex_out(vert_out)
    shader_info.fragment_out(0, 'VEC4', 'fragColor')

    shader_info.vertex_source(vertex_glsl)
    shader_info.fragment_source(fragment_glsl)

    shader = gpu.shader.create_from_info(shader_info)
    _log.output(f'{shader_name}: GPU Shader')
    return shader


def simple_uniform_color_2d_shader(use_old: bool = _use_old_shaders) -> Any:
    shader_name = 'simple_uniform_color_2d_shader'

    vertex_vars = '''
    uniform mat4 ModelViewProjectionMatrix;
    in vec2 pos;
    '''

    vertex_glsl = '''
    void main()
    {
        gl_Position = ModelViewProjectionMatrix * vec4(pos, 0.0, 1.0);
    }
    '''

    fragment_vars = '''
    uniform vec4 color;
    out vec4 fragColor;
    '''

    fragment_glsl = '''
    void main()
    {
        fragColor = color;
    }
    '''

    if use_old:
        shader = gpu.types.GPUShader(vertex_vars + vertex_glsl,
                                     fragment_vars + fragment_glsl)
        _log.magenta(f'{shader_name}: Old Shader')
        return shader

    shader_info = gpu.types.GPUShaderCreateInfo()
    shader_info.push_constant('MAT4', 'ModelViewProjectionMatrix')
    shader_info.push_constant('VEC4', 'color')
    shader_info.vertex_in(0, 'VEC2', 'pos')
    shader_info.fragment_out(0, 'VEC4', 'fragColor')

    shader_info.vertex_source(vertex_glsl)
    shader_info.fragment_source(fragment_glsl)

    shader = gpu.shader.create_from_info(shader_info)
    _log.output(f'{shader_name}: GPU Shader')
    return shader
