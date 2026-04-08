#version 430

// 1. Vertex Attributes
layout (location = 0) in vec3 in_pos;
layout (location = 1) in vec3 in_norm;
layout (location = 2) in int in_mesh_id; // Mandatory for Batch path

// 2. SSBO Buffers (The Batch Data)
layout (std430, binding = 0) buffer ModelMatrices { 
    mat4 models[]; 
};

layout (std430, binding = 1) buffer ColorBuffer    { 
    vec4 colors[]; 
};

// 3. Uniforms (The Standalone & Global Data)
uniform mat4 projection;
uniform mat4 view;
uniform mat4 u_model;           // Standalone Matrix
uniform vec4 u_color; // Standalone Color
uniform bool u_is_batched;      // The Switch

out vec3 v_norm;
out vec4 v_color;

void main() {
    mat4 model_mtx;
    
    if (u_is_batched) {
        // Grab from the SSBO using the vertex's ID
        model_mtx = models[in_mesh_id];
        v_color = colors[in_mesh_id];
    } else {
        // Use the single values sent via uniforms
        model_mtx = u_model;
        v_color = u_color;
    }

    // Normal transform (using the top-left 3x3 of the model matrix)
    v_norm = mat3(model_mtx) * in_norm;
    
    // Final screen position
    gl_Position = projection * view * model_mtx * vec4(in_pos, 1.0);
}