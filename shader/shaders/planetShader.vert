#version 330

in vec3 in_pos;
in vec3 in_norm;
in vec4 in_color;

uniform mat4 u_model;
uniform mat4 projection;
uniform mat4 view;

out vec4 o_color;
out vec3 o_normal;
out vec4 o_fragPosition;
out vec3 v_local_pos;

void main() {
    // Pass the vertex color through
    o_color = in_color;
    v_local_pos = in_pos;

    // Calculate the world position of the vertex
    vec4 worldPos = u_model * vec4(in_pos, 1.0);
    o_fragPosition = worldPos;

    // Transform the normal (using the mat3 of the model matrix)
    // This handles rotation correctly for the lighting
    o_normal = mat3(u_model) * in_norm;

    gl_Position = projection * view * u_model * vec4(in_pos, 1.0);
}