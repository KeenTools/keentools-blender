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


def flat_color_3d_vertex_shader():
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
            ((color      ) & uint(0xFF)) * (1.0f / 255.0f),
            ((color >>  8) & uint(0xFF)) * (1.0f / 255.0f),
            ((color >> 16) & uint(0xFF)) * (1.0f / 255.0f),
            ((color >> 24)             ) * (1.0f / 255.0f));
    #else
        finalColor = color;
    #endif

    #ifdef USE_WORLD_CLIP_PLANES
        world_clip_planes_calc_clip_distance((ModelMatrix * pos_4d).xyz);
    #endif
    }
    '''


def circular_dot_fragment_shader():
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


def flat_color_2d_vertex_shader():
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


def simple_fill_vertex_shader():
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


def simple_fill_vertex_local_shader():
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


def smooth_3d_vertex_local_shader():
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


def smooth_3d_fragment_shader_new():
    return '''
    // Based on gpu.shader.code_from_builtin('3D_SMOOTH_COLOR')['fragment_shader']
    in vec4 finalColor;
    out vec4 fragColor;
    void main()
    {
      fragColor = finalColor;
      fragColor = blender_srgb_to_framebuffer_space(fragColor);
    }
    '''


def smooth_3d_fragment_shader_old():
    return '''
    in vec4 finalColor;
    out vec4 fragColor;
    void main()
    {
      fragColor = finalColor;
    }
    '''


smooth_3d_fragment_shader = smooth_3d_fragment_shader_new \
    if bpy.app.version >= (2, 83, 0) else smooth_3d_fragment_shader_old


def uniform_3d_vertex_local_shader():
    return '''
    uniform mat4 ModelViewProjectionMatrix;
    uniform mat4 modelMatrix;
    uniform vec4 color;

    #ifdef USE_WORLD_CLIP_PLANES
    uniform mat4 ModelMatrix;
    #endif

    in vec3 pos;

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


def black_fill_fragment_shader():
    return '''
    out vec4 fragColor;
    void main()
    {
        fragColor = vec4(0.0, 0.0, 0.0, 1.0);
    }
    '''


def residual_vertex_shader():
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
        gl_Position = ModelViewProjectionMatrix * vec4(pos, 0.0, 1.0f);
        finalColor = color;
    }
    '''


def residual_fragment_shader():
    return '''
    in float v_LineLength;            
    flat in vec4 finalColor;
    out vec4 fragColor;

    void main()
    {
        if (step(sin(v_LineLength), -0.3f) == 1) discard;
        fragColor = finalColor;
    }
    '''


def dashed_fragment_shader():
    return '''
    in float v_LineLength;
    flat in vec4 finalColor;
    out vec4 fragColor;

    void main()
    {
        if (mod(v_LineLength + 5.0f, 10.0f) > 5.5f) discard;
        fragColor = finalColor;
    }
    '''


def solid_line_vertex_shader():
    return '''
    uniform mat4 ModelViewProjectionMatrix;
    in vec2 pos;

    in vec4 color;
    flat out vec4 finalColor;

    void main()
    {
        gl_Position = ModelViewProjectionMatrix * vec4(pos, 0.0, 1.0f);
        finalColor = color;
    }
    '''


def solid_line_fragment_shader():
    return '''
    flat in vec4 finalColor;
    out vec4 fragColor;

    void main()
    {
        fragColor = finalColor;
    }
    '''


def raster_image_vertex_shader():
    return '''
    uniform mat4 ModelViewProjectionMatrix;

    in vec2 texCoord;
    in vec3 pos;
    out vec2 texCoord_interp;

    void main()
    {
      gl_Position = ModelViewProjectionMatrix * vec4(pos, 1.0f);
      texCoord_interp = texCoord;
    }
    '''


def raster_image_fragment_shader():
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


def raster_image_mask_vertex_shader():
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
            0.0f, 1.0f);
        gl_Position.z = 1.0;
        texCoord_interp = texCoord;
    }
    '''


def raster_image_mask_fragment_shader():
    return '''
    uniform sampler2D image;
    uniform vec4 color;
    uniform bool inverted;

    in vec2 texCoord_interp;
    out vec4 fragColor;

    void main()
    {
        vec4 tex = texture(image, texCoord_interp);
        if ((tex[0] == 0) && (tex[1] == 0) && (tex[2] == 0)) {
            if (!inverted) discard;
            fragColor = color;
        } else {
            if (inverted) discard;
            fragColor = color;
        }
    }
    '''
