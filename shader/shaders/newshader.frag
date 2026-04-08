#version 430

in vec3 v_norm;
in vec3 v_pos;
in vec4 v_color; // <-- Add this! This comes from the Vertex Shader

out vec4 f_color;

uniform vec3 u_light_pos = vec3(20.0, 20.0, 20.0);

void main() {
    vec3 n = normalize(v_norm);
    vec3 l = normalize(u_light_pos - v_pos);

    float diff = max(dot(n, l), 0.2);

    f_color = vec4(v_color.rgb * diff, v_color.a);

    //float ambient = 0.3;
    //float diff = max(dot(normalize(v_norm), vec3(0, 0, 1)), 0.0);
    //
    //// Use v_color instead of u_color
    //f_color = vec4(v_color.rgb * (diff + ambient), v_color.a);
}