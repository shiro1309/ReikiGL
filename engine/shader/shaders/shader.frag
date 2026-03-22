#version 430

in vec3 v_norm;
in vec3 v_pos;
flat in int v_mesh_id;

layout (std430, binding = 1) buffer MeshColors {
    vec4 colors[];
};

out vec4 f_color;

uniform vec3 u_light_pos = vec3(10.0, 10.0, 10.0);
uniform vec4 u_base_color = vec4(0.7, 0.7, 0.8, 1.0);

void main() {
    vec3 n = normalize(v_norm);
    vec3 l = normalize(u_light_pos - v_pos);
    
    // Enkel lambertian belysning + litt ambient
    float diff = max(dot(n, l), 0.2);
    
    f_color = vec4(u_base_color.rgb * diff, u_base_color.a);
}