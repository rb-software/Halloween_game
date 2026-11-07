from panda3d.core import Shader as PandaShader
from ursina import Shader, Vec2


def create_material_shader():
    return Shader(
        language=Shader.GLSL,
        name="porous_material_shader",
        vertex="""#version 120
uniform struct {
    vec4 position;
    vec3 color;
    vec3 attenuation;
    vec3 spotDirection;
    float spotCosCutoff;
    float spotExponent;
    sampler2DShadow shadowMap;
    mat4 shadowViewMatrix;
} p3d_LightSource[1];
uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat4 p3d_ModelViewMatrix;
uniform mat4 p3d_ProjectionMatrix;
uniform mat4 p3d_ModelMatrix;
uniform mat3 p3d_NormalMatrix;
attribute vec4 p3d_Vertex;
attribute vec3 p3d_Normal;
attribute vec4 p3d_Color;
attribute vec2 p3d_MultiTexCoord0;
uniform vec2 texture_scale;
uniform vec2 texture_offset;
uniform float mesh_relief;
varying vec2 texcoords;
varying vec3 view_position;
varying vec3 view_normal;
varying vec4 vertex_color;
varying vec4 shadow_coordinate;

void main() {
    view_position = vec3(p3d_ModelViewMatrix * p3d_Vertex);
    view_normal = normalize(p3d_NormalMatrix * p3d_Normal);
    vec3 world_position = vec3(p3d_ModelMatrix * p3d_Vertex);
    float broad_wave = sin(world_position.x * 1.7 + world_position.z * 0.9)
        * sin(world_position.y * 2.1 + world_position.x * 0.7);
    float fine_wave = sin(world_position.x * 4.3 + world_position.y * 2.7)
        * sin(world_position.z * 3.4 - world_position.y * 1.9);
    float relief = (broad_wave * 0.72 + fine_wave * 0.28) * mesh_relief;
    view_position += view_normal * relief;
    gl_Position = p3d_ProjectionMatrix * vec4(view_position, 1.0);
    shadow_coordinate = p3d_LightSource[0].shadowViewMatrix
        * vec4(view_position, 1.0);
    texcoords = p3d_MultiTexCoord0 * texture_scale + texture_offset;
    vertex_color = p3d_Color;
}
""",
        fragment="""#version 120
uniform struct {
    vec4 position;
    vec3 color;
    vec3 attenuation;
    vec3 spotDirection;
    float spotCosCutoff;
    float spotExponent;
    sampler2DShadow shadowMap;
    mat4 shadowViewMatrix;
} p3d_LightSource[1];
uniform struct {
    vec4 ambient;
} p3d_LightModel;
uniform sampler2D p3d_Texture0;
uniform sampler2D environment_map;
uniform sampler2D roughness_map;
uniform sampler2D occlusion_map;
uniform float occlusion_strength;
uniform float reflection_strength;
uniform float shadow_strength;
uniform vec4 p3d_ColorScale;
varying vec2 texcoords;
varying vec3 view_position;
varying vec3 view_normal;
varying vec4 vertex_color;
varying vec4 shadow_coordinate;

const float PI = 3.14159265359;
uniform vec3 fog_color;
uniform float fog_density;

vec2 environment_uv(vec3 direction) {
    return vec2(
        atan(direction.z, direction.x) / (2.0 * PI) + 0.5,
        asin(clamp(direction.y, -1.0, 1.0)) / PI + 0.5
    );
}

void main() {
    vec4 albedo = texture2D(p3d_Texture0, texcoords) * p3d_ColorScale * vertex_color;
    vec3 N = normalize(view_normal);

    float roughness = clamp(texture2D(roughness_map, texcoords).r, 0.12, 1.0);
    float occlusion = mix(
        1.0,
        texture2D(occlusion_map, texcoords).r,
        occlusion_strength
    );
    vec3 V = normalize(-view_position);
    float NdotV = max(dot(N, V), 0.001);
    vec3 reflection_direction = reflect(-V, N);
    vec3 environment_reflection = texture2D(
        environment_map,
        environment_uv(reflection_direction)
    ).rgb;
    float fresnel_reflection = 0.25 + 0.75 * pow(1.0 - NdotV, 5.0);
    float reflection_amount = reflection_strength
        * fresnel_reflection
        * (1.0 - roughness * 0.65);
    float shadow_visibility = 1.0;
    if (shadow_strength > 0.5) {
        vec4 shadow_sample = shadow_coordinate;
        shadow_sample.z += 0.0015;
        vec2 texel = vec2(1.0 / 1024.0) * shadow_sample.w;
        float shadow_sum = shadow2DProj(
            p3d_LightSource[0].shadowMap,
            shadow_sample + vec4(-0.25 * texel.x, -0.25 * texel.y, 0.0, 0.0)
        ).r;
        shadow_sum += shadow2DProj(
            p3d_LightSource[0].shadowMap,
            shadow_sample + vec4(0.25 * texel.x, 0.25 * texel.y, 0.0, 0.0)
        ).r;
        shadow_visibility = shadow_sum * 0.5;
    }
    float ambient_shadow = mix(0.68, 1.0, shadow_visibility);
    vec3 lighting = albedo.rgb
        * p3d_LightModel.ambient.rgb
        * 1.0
        * occlusion
        * ambient_shadow;
    lighting = mix(
        lighting,
        environment_reflection * albedo.rgb,
        reflection_amount
    );

    for (int i = 0; i < 1; ++i) {
        vec3 light_vector = p3d_LightSource[i].position.xyz
            - view_position * p3d_LightSource[i].position.w;
        float light_distance = length(light_vector);
        vec3 L = normalize(light_vector);
        float NdotL = max(dot(N, L), 0.0);
        vec3 H = normalize(L + V);
        float NdotH = max(dot(N, H), 0.0);
        float VdotH = max(dot(V, H), 0.0);
        float alpha = roughness * roughness;
        float alpha_squared = alpha * alpha;
        float distribution_base = NdotH * NdotH * (alpha_squared - 1.0) + 1.0;
        float distribution = alpha_squared / max(
            PI * distribution_base * distribution_base,
            0.001
        );
        float geometry_k = (roughness + 1.0) * (roughness + 1.0) / 8.0;
        float geometry_light = NdotL / max(
            NdotL * (1.0 - geometry_k) + geometry_k,
            0.001
        );
        float geometry_view = NdotV / max(
            NdotV * (1.0 - geometry_k) + geometry_k,
            0.001
        );
        vec3 fresnel = vec3(0.04)
            + vec3(0.96) * pow(1.0 - VdotH, 5.0);
        vec3 specular = distribution * geometry_light * geometry_view * fresnel
            / max(4.0 * NdotL * NdotV, 0.001);
        vec3 diffuse = (vec3(1.0) - fresnel) * albedo.rgb / PI;
        float attenuation = 1.0 / max(
            1.0,
            p3d_LightSource[i].attenuation.x
                + p3d_LightSource[i].attenuation.y * light_distance
                + p3d_LightSource[i].attenuation.z * light_distance * light_distance
        );
        lighting += (
            diffuse * NdotL
            + specular * NdotL
        ) * p3d_LightSource[i].color * attenuation * shadow_visibility;
    }

    float fog_amount = 1.0 - exp(-length(view_position) * fog_density);
    lighting = mix(lighting, fog_color, clamp(fog_amount, 0.0, 1.0));
    gl_FragColor = vec4(lighting, albedo.a);
}
""",
        default_input={
            "texture_scale": Vec2(1, 1),
            "texture_offset": Vec2(0, 0),
            "mesh_relief": 0.0,
        },
    )


def create_skin_shader():
    return Shader(
        language=Shader.GLSL,
        name="subsurface_skin_shader",
        vertex="""#version 120
uniform struct {
    vec4 position;
    vec3 color;
    vec3 attenuation;
    vec3 spotDirection;
    float spotCosCutoff;
    float spotExponent;
} p3d_LightSource[1];
uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat4 p3d_ModelViewMatrix;
uniform mat3 p3d_NormalMatrix;
attribute vec4 p3d_Vertex;
attribute vec3 p3d_Normal;
attribute vec4 p3d_Color;
attribute vec2 p3d_MultiTexCoord0;
varying vec2 texcoords;
varying vec3 view_position;
varying vec3 view_normal;
varying vec4 vertex_color;

void main() {
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
    view_position = vec3(p3d_ModelViewMatrix * p3d_Vertex);
    view_normal = normalize(p3d_NormalMatrix * p3d_Normal);
    texcoords = p3d_MultiTexCoord0;
    vertex_color = p3d_Color;
}
""",
        fragment="""#version 120
uniform struct {
    vec4 position;
    vec3 color;
    vec3 attenuation;
    vec3 spotDirection;
    float spotCosCutoff;
    float spotExponent;
} p3d_LightSource[1];
uniform struct { vec4 ambient; } p3d_LightModel;
uniform sampler2D p3d_Texture0;
uniform vec4 p3d_ColorScale;
uniform vec3 subsurface_color;
uniform float subsurface_strength;
varying vec2 texcoords;
varying vec3 view_position;
varying vec3 view_normal;
varying vec4 vertex_color;

void main() {
    vec4 albedo = texture2D(p3d_Texture0, texcoords)
        * p3d_ColorScale * vertex_color;
    vec3 N = normalize(view_normal);
    vec3 V = normalize(-view_position);
    vec3 to_light = p3d_LightSource[0].position.xyz
        - view_position * p3d_LightSource[0].position.w;
    float light_distance = length(to_light);
    vec3 L = normalize(to_light);
    float NdotL = dot(N, L);
    float wrapped_diffuse = max((NdotL + 0.35) / 1.35, 0.0);
    float back_scatter = pow(max(dot(-N, L + V * 0.35), 0.0), 2.0);
    float attenuation = 1.0 / max(
        1.0,
        p3d_LightSource[0].attenuation.x
            + p3d_LightSource[0].attenuation.y * light_distance
            + p3d_LightSource[0].attenuation.z * light_distance * light_distance
    );
    vec3 direct_light = p3d_LightSource[0].color * attenuation;
    vec3 diffuse = albedo.rgb * direct_light * wrapped_diffuse;
    vec3 transmission = albedo.rgb * subsurface_color * direct_light
        * back_scatter * subsurface_strength;
    vec3 ambient = albedo.rgb * p3d_LightModel.ambient.rgb * 0.55;
    gl_FragColor = vec4(ambient + diffuse + transmission, albedo.a);
}
""",
    )


def create_ambient_occlusion_shader():
    vertex = """#version 120
uniform mat4 p3d_ModelViewProjectionMatrix;
attribute vec4 p3d_Vertex;
attribute vec2 p3d_MultiTexCoord0;
varying vec2 texcoords;

void main() {
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
    texcoords = p3d_MultiTexCoord0;
}
"""
    fragment = """#version 120
uniform sampler2D scene_color;
uniform sampler2D scene_depth;
uniform vec2 inverse_resolution;
uniform float ao_enabled;
uniform float cinematic_enabled;
varying vec2 texcoords;

void main() {
    vec4 color = texture2D(scene_color, texcoords);
    if (ao_enabled < 0.5 && cinematic_enabled < 0.5) {
        gl_FragColor = color;
        return;
    }

    float center_depth = texture2D(scene_depth, texcoords).r;
    if (center_depth >= 0.99999) {
        gl_FragColor = color;
        return;
    }

    float occlusion = 0.0;
    if (ao_enabled > 0.5) {
        vec2 offset = inverse_resolution * 4.0;
        float right_depth = texture2D(scene_depth, texcoords + vec2(offset.x, 0.0)).r;
        float left_depth = texture2D(scene_depth, texcoords - vec2(offset.x, 0.0)).r;
        float up_depth = texture2D(scene_depth, texcoords + vec2(0.0, offset.y)).r;
        float down_depth = texture2D(scene_depth, texcoords - vec2(0.0, offset.y)).r;
        occlusion += smoothstep(0.0004, 0.008, center_depth - right_depth);
        occlusion += smoothstep(0.0004, 0.008, center_depth - left_depth);
        occlusion += smoothstep(0.0004, 0.008, center_depth - up_depth);
        occlusion += smoothstep(0.0004, 0.008, center_depth - down_depth);
    }

    float visibility = 1.0 - min(occlusion * 0.08, 0.3);
    vec3 graded_color = color.rgb * visibility;
    if (cinematic_enabled > 0.5) {
        float luminance = dot(graded_color, vec3(0.2126, 0.7152, 0.0722));
        float highlights = smoothstep(0.28, 0.85, luminance);
        float shadows = 1.0 - smoothstep(0.12, 0.62, luminance);
        graded_color += vec3(0.035, 0.012, -0.018) * highlights;
        graded_color += vec3(-0.012, 0.006, 0.035) * shadows;
        graded_color = graded_color * (1.0 + graded_color * 0.12)
            / (1.0 + graded_color * 0.2);
        float radius = length((texcoords - 0.5) * vec2(1.0, 0.72));
        float vignette = 1.0 - smoothstep(0.32, 0.78, radius) * 0.2;
        graded_color *= vignette;
    }
    gl_FragColor = vec4(graded_color, color.a);
}
"""
    return PandaShader.make(PandaShader.SL_GLSL, vertex, fragment)


def create_ocean_shader():
    return Shader(
        language=Shader.GLSL,
        name="coastal_water_shader",
        vertex="""#version 120
uniform mat4 p3d_ModelMatrix;
uniform mat4 p3d_ModelViewMatrix;
uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat3 p3d_NormalMatrix;
uniform float water_time;
attribute vec4 p3d_Vertex;
varying vec3 view_position;
varying vec3 view_normal;
varying float wave_light;

void main() {
    vec4 world_position = p3d_ModelMatrix * p3d_Vertex;
    float wave_a = sin(world_position.x * 0.17 + water_time * 0.7);
    float wave_b = sin(world_position.z * 0.25 - water_time * 0.48);
    float wave_height = wave_a * 0.10 + wave_b * 0.055;
    world_position.y += wave_height;
    float slope_x = cos(world_position.x * 0.17 + water_time * 0.7) * 0.017;
    float slope_z = cos(world_position.z * 0.25 - water_time * 0.48) * -0.014;
    vec3 normal = normalize(vec3(-slope_x, 1.0, -slope_z));
    vec4 displaced_vertex = p3d_Vertex + vec4(0.0, wave_height, 0.0, 0.0);
    gl_Position = p3d_ModelViewProjectionMatrix * displaced_vertex;
    view_position = vec3(p3d_ModelViewMatrix * displaced_vertex);
    view_normal = normalize(p3d_NormalMatrix * normal);
    wave_light = wave_a * 0.5 + wave_b * 0.5;
}
""",
        fragment="""#version 120
uniform sampler2D environment_map;
uniform vec3 fog_color;
uniform float fog_density;
varying vec3 view_position;
varying vec3 view_normal;
varying float wave_light;
const float PI = 3.14159265359;

void main() {
    vec3 N = normalize(view_normal);
    vec3 V = normalize(-view_position);
    vec3 reflected = reflect(-V, N);
    vec2 environment_uv = vec2(
        atan(reflected.z, reflected.x) / (2.0 * PI) + 0.5,
        asin(clamp(reflected.y, -1.0, 1.0)) / PI + 0.5
    );
    vec3 sky_reflection = texture2D(environment_map, environment_uv).rgb;
    vec3 deep_water = vec3(0.025, 0.16, 0.21);
    float fresnel = 0.22 + 0.58 * pow(1.0 - max(dot(N, V), 0.0), 4.0);
    vec3 water = mix(deep_water, sky_reflection, fresnel);
    water += vec3(0.018, 0.035, 0.038) * wave_light;
    float fog_amount = 1.0 - exp(-length(view_position) * fog_density);
    gl_FragColor = vec4(mix(water, fog_color, clamp(fog_amount, 0.0, 1.0)), 1.0);
}
""",
    )
