
#version 150 core

in vec4 vertex_colors;
out vec4 final_color;

void main()
{
    // Write the vertex color
    final_color = vertex_colors;

    // Alpha test style discard
    if (final_color.a < 0.01)
        discard;
}
