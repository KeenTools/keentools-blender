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


blender_srgb_to_framebuffer_space_enabled: bool = bpy.app.version >= (2, 83, 0)


def flat_color_3d_vertex_shader() -> str:
    return '''
    uniform mat4 ModelViewProjectionMatrix;
    #ifdef USE_WORLD_CLIP_PLANES
    uniform mat4 ModelMatrix;
    #endif

    in vec3 pos;
    #if defined(USE_COLOR_U32)
    in uint color;
    #else
    in vec4 color;
    #endif

    flat out vec4 finalColor;

    void main()
    {
        vec4 pos_4d = vec4(pos, 1.0);
        gl_Position = ModelViewProjectionMatrix * pos_4d;

    #if defined(USE_COLOR_U32)
        finalColor = vec4(
            ((color      ) & uint(0xFF)) * (1.0 / 255.0),
            ((color >>  8) & uint(0xFF)) * (1.0 / 255.0),
            ((color >> 16) & uint(0xFF)) * (1.0 / 255.0),
            ((color >> 24)             ) * (1.0 / 255.0));
    #else
        finalColor = color;
    #endif

    #ifdef USE_WORLD_CLIP_PLANES
        world_clip_planes_calc_clip_distance((ModelMatrix * pos_4d).xyz);
    #endif
    }
    '''


def circular_dot_fragment_shader() -> str:
    return '''
    flat in vec4 finalColor;
    out vec4 fragColor;
    void main() {
            vec2 cxy = 2.0 * gl_PointCoord - 1.0;
            float r = dot(cxy, cxy);
            float delta = fwidth(r);
            float alpha = 1.0 - smoothstep(1.0 - delta, 1.0 + delta, r);
            fragColor = finalColor * alpha;
    }
    '''


def flat_color_2d_vertex_shader() -> str:
    return '''
    uniform mat4 ModelViewProjectionMatrix;

    in vec2 pos;
    in vec4 color;

    flat out vec4 finalColor;

    void main()
    {
        gl_Position = ModelViewProjectionMatrix * vec4(pos, 0.0, 1.0);
        finalColor = color;
    }
    '''


def simple_fill_vertex_shader() -> str:
    return '''
    uniform mat4 ModelViewProjectionMatrix;
    #ifdef USE_WORLD_CLIP_PLANES
    uniform mat4 ModelMatrix;
    #endif

    in vec3 pos;

    void main()
    {
        gl_Position = ModelViewProjectionMatrix * vec4(pos, 1.0);

    #ifdef USE_WORLD_CLIP_PLANES
        world_clip_planes_calc_clip_distance((ModelMatrix * vec4(pos, 1.0)).xyz);
    #endif
    }
    '''


def simple_fill_vertex_local_shader() -> str:
    return '''
    uniform mat4 ModelViewProjectionMatrix;
    uniform mat4 modelMatrix;
    #ifdef USE_WORLD_CLIP_PLANES
    uniform mat4 ModelMatrix;
    #endif

    in vec3 pos;

    void main()
    {
        gl_Position = ModelViewProjectionMatrix * modelMatrix * vec4(pos, 1.0);

    #ifdef USE_WORLD_CLIP_PLANES
        world_clip_planes_calc_clip_distance((ModelMatrix * modelMatrix * vec4(pos, 1.0)).xyz);
    #endif
    }
    '''


def smooth_3d_vertex_local_shader() -> str:
    return '''
    uniform mat4 ModelViewProjectionMatrix;
    uniform mat4 modelMatrix;

    #ifdef USE_WORLD_CLIP_PLANES
    uniform mat4 ModelMatrix;
    #endif

    in vec3 pos;
    in vec4 color;

    out vec4 finalColor;

    void main()
    {
      gl_Position = ModelViewProjectionMatrix * modelMatrix * vec4(pos, 1.0);
      finalColor = color;

    #ifdef USE_WORLD_CLIP_PLANES
      world_clip_planes_calc_clip_distance((ModelMatrix * modelMatrix * vec4(pos, 1.0)).xyz);
    #endif
    }
    '''


def smooth_3d_fragment_shader() -> str:
    txt = '''
    // Based on gpu.shader.code_from_builtin('3D_SMOOTH_COLOR')['fragment_shader']
    in vec4 finalColor;
    out vec4 fragColor;
    void main()
    {
        fragColor = finalColor;
    '''
    if blender_srgb_to_framebuffer_space_enabled:
        txt += 'fragColor = blender_srgb_to_framebuffer_space(fragColor);'
    txt += '''
    }
    '''
    return txt


def uniform_3d_vertex_local_shader() -> str:
    txt = '''
    uniform mat4 ModelViewProjectionMatrix;
    uniform mat4 modelMatrix;
    uniform vec4 color;
    uniform float adaptiveOpacity;

    #ifdef USE_WORLD_CLIP_PLANES
    uniform mat4 ModelMatrix;
    #endif

    in vec3 pos;

    out vec4 finalColor;

    void main()
    {
        gl_Position = ModelViewProjectionMatrix * modelMatrix * vec4(pos, 1.0);
        finalColor = color;
        finalColor.a = color.a * adaptiveOpacity;
    #ifdef USE_WORLD_CLIP_PLANES
        world_clip_planes_calc_clip_distance((ModelMatrix * modelMatrix * vec4(pos, 1.0)).xyz);
    #endif
    }
    '''
    return txt


def black_fill_fragment_shader() -> str:
    return '''
    out vec4 fragColor;
    void main()
    {
        fragColor = vec4(0.0, 0.0, 0.0, 1.0);
    }
    '''


def residual_vertex_shader() -> str:
    return '''
    uniform mat4 ModelViewProjectionMatrix;
    in vec2 pos;
    in float lineLength;
    out float v_LineLength;

    in vec4 color;
    flat out vec4 finalColor;

    void main()
    {
        v_LineLength = lineLength;
        gl_Position = ModelViewProjectionMatrix * vec4(pos, 0.0, 1.0);
        finalColor = color;
    }
    '''


def residual_fragment_shader() -> str:
    txt = '''
    in float v_LineLength;            
    flat in vec4 finalColor;
    out vec4 fragColor;

    void main()
    {
        if (step(sin(v_LineLength), -0.3f) == 1) discard;
        fragColor = finalColor;
        '''
    if blender_srgb_to_framebuffer_space_enabled:
        txt += 'fragColor = blender_srgb_to_framebuffer_space(fragColor);'
    txt += '''
    }
    '''
    return txt


def dashed_fragment_shader() -> str:
    txt = '''
    in float v_LineLength;
    flat in vec4 finalColor;
    out vec4 fragColor;

    void main()
    {
        if (mod(v_LineLength + 5.0, 10.0) > 5.5) discard;
        fragColor = finalColor;
        '''
    if blender_srgb_to_framebuffer_space_enabled:
        txt += 'fragColor = blender_srgb_to_framebuffer_space(fragColor);'
    txt += '''
    }
    '''
    return txt


def solid_line_vertex_shader() -> str:
    return '''
    uniform mat4 ModelViewProjectionMatrix;
    in vec2 pos;

    in vec4 color;
    flat out vec4 finalColor;

    void main()
    {
        gl_Position = ModelViewProjectionMatrix * vec4(pos, 0.0, 1.0);
        finalColor = color;
    }
    '''


def solid_line_fragment_shader() -> str:
    txt = '''
    flat in vec4 finalColor;
    out vec4 fragColor;

    void main()
    {
        fragColor = finalColor;
        '''
    if blender_srgb_to_framebuffer_space_enabled:
        txt += 'fragColor = blender_srgb_to_framebuffer_space(fragColor);'
    txt += '''
    }
    '''
    return txt


def raster_image_vertex_shader() -> str:
    return '''
    uniform mat4 ModelViewProjectionMatrix;

    in vec2 texCoord;
    in vec3 pos;
    out vec2 texCoord_interp;

    void main()
    {
      gl_Position = ModelViewProjectionMatrix * vec4(pos, 1.0);
      texCoord_interp = texCoord;
    }
    '''


def raster_image_fragment_shader() -> str:
    return '''
    in vec2 texCoord_interp;
    out vec4 fragColor;
    uniform sampler2D image;
    uniform float opacity;

    void main()
    {
        fragColor = texture(image, texCoord_interp);
        fragColor.a = opacity;
    }
    '''


def raster_image_mask_vertex_shader() -> str:
    return '''
    uniform mat4 ModelViewProjectionMatrix;
    uniform vec2 left;
    uniform vec2 right;

    in vec2 texCoord;
    in vec2 pos;
    out vec2 texCoord_interp;

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


def raster_image_mask_fragment_shader() -> str:
    return '''
    uniform sampler2D image;
    uniform vec4 color;
    uniform bool inverted;
    uniform float maskThreshold;

    in vec2 texCoord_interp;
    out vec4 fragColor;

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


def lit_vertex_local_shader() -> str:
    return '''
    uniform mat4 ModelViewProjectionMatrix;
    uniform mat4 modelMatrix;

    #ifdef USE_WORLD_CLIP_PLANES
    uniform mat4 ModelMatrix;
    #endif

    in vec3 pos;
    in vec3 vertNormal;
    out vec3 calcNormal;
    out vec3 outPos;

    void main()
    {
        mat4 resultMatrix = ModelViewProjectionMatrix * modelMatrix;
        gl_Position = resultMatrix * vec4(pos, 1.0);
        calcNormal = normalize(resultMatrix * vec4(vertNormal, 0.0)).xyz;
        outPos = gl_Position.xyz;

    #ifdef USE_WORLD_CLIP_PLANES
        world_clip_planes_calc_clip_distance((ModelMatrix * vec4(pos, 1.0)).xyz);
    #endif
    }
    '''


def lit_fragment_shader() -> str:
    txt = '''
    uniform vec4 color;
    in vec4 finalColor;
    in vec3 outPos;
    in vec3 calcNormal;
    out vec4 fragColor;

    struct Light
    {
      vec3 position;
      float constant;
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
        float attenuation = 1.0 / (light.constant + light.linear * distance +
                            light.quadratic * (distance * distance));
        vec3 ambient  = light.ambient;
        vec3 diffuse  = light.diffuse * diff ;

        return attenuation * (ambient + diffuse) * surfColor;
    }

    void main()
    {
        float dist = 1000.0;
        Light light1 = Light(vec3( 0.0,  0.0, -dist), 1.0, 0.0, 0.0, vec3(0.0, 0.0, 0.0), vec3(1.0, 1.0, 1.0));
        Light light2 = Light(vec3(-2.0 * dist, 0.0, -dist), 1.0, 0.0, 0.0, vec3(0.0, 0.0, 0.0), vec3(1.0, 1.0, 1.0));
        Light light3 = Light(vec3( 2.0 * dist, 0.0, -dist), 1.0, 0.0, 0.0, vec3(0.0, 0.0, 0.0), vec3(1.0, 1.0, 1.0));
        fragColor = vec4(
            evaluatePointLight(light1, color.rgb, calcNormal, outPos) +
            evaluatePointLight(light2, color.rgb, calcNormal, outPos) +
            evaluatePointLight(light3, color.rgb, calcNormal, outPos), color.a);
    '''
    if blender_srgb_to_framebuffer_space_enabled:
        txt += 'fragColor = blender_srgb_to_framebuffer_space(fragColor);'
    txt += '''
    }
    '''
    return txt
