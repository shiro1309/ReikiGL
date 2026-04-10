#version 430

layout (location = 0) in vec3 in_pos;
layout (location = 1) in vec2 in_uv;
layout (location = 2) in vec3 in_norm;
layout (location = 3) in vec4 in_color; // The baked RGBA color
layout (location = 4) in int in_mesh_id; // From the mesh_id_buffer

// Matrix SSBO (Binding 0)
layout (std430, binding = 0) buffer MatrixBuffer {
    mat4 models[];
};

uniform mat4 projection;
uniform mat4 view;

out vec3 v_norm;
out vec4 v_color;

void main() {
    v_norm = in_norm; // We'll handle rotation in the frag or here if needed
    v_color = in_color;
    
    // Fetch this specific mesh's transform
    mat4 model = models[in_mesh_id];
    
    gl_Position = projection * view * model * vec4(in_pos, 1.0);
}