#version 430
#extension GL_ARB_shader_draw_parameters : enable

// Layout matcher '3f 2x4 3f'
layout (location = 0) in vec3 in_pos;
layout (location = 1) in vec3 in_norm;
layout (location = 2) in int in_mesh_id;

// SSBO som lagrer alle matrisene for hele batchen
layout (std430, binding = 0) buffer ModelMatrices {
    mat4 models[];
};

uniform mat4 u_view_projection;

out vec3 v_norm;
out vec3 v_pos;
flat out int v_mesh_id; // Sendes til fragment shader

void main() {
    v_mesh_id = in_mesh_id;
    // Hent riktig matrise for denne meshen i batchen
    mat4 model = models[in_mesh_id];
    
    // Beregn verdensposisjon
    vec4 world_pos = model * vec4(in_pos, 1.0);
    v_pos = world_pos.xyz;
    
    // Transformér normaler (enkel variant)
    v_norm = mat3(model) * in_norm;
    
    gl_Position = u_view_projection * world_pos;
}