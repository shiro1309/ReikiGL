#version 150 core

in vec3 position;
in vec4 colors;
in vec3 translation;

out vec4 vertex_colors;

uniform mat4 model;
uniform mat4 u_projection;
uniform mat4 u_view;

void main()
{
    vec3 world_pos = position + translation;
    gl_Position = u_projection * u_view * model * vec4(world_pos, 1.0);
    vertex_colors = colors;
}
