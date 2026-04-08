#version 430

in vec3 v_norm;
in vec4 v_color; // <-- Add this! This comes from the Vertex Shader

out vec4 f_color;

void main() {
    float ambient = 0.3;
    float diff = max(dot(normalize(v_norm), vec3(0, 0, 1)), 0.0);
    
    // Use v_color instead of u_color
    f_color = vec4(v_color.rgb * (diff + ambient), v_color.a);
}