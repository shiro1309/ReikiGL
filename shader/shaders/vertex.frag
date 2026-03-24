
#version 330
in vec4 vertex_colors; // Må være vec4 for å inkludere alpha
out vec4 f_color;

void main() {
    f_color = vertex_colors; // Her blir v_color.a (alpha) brukt
}
