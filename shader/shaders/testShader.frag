#version 430

in vec3 v_norm;
in vec4 v_color;

out vec4 f_color;

void main() {
    // Basic directional lighting (light coming from the camera Z)
    float ambient = 0.3;
    float diff = max(dot(normalize(v_norm), vec3(0, 0, 1)), 0.0);
    
    // Combine the baked color with the lighting
    f_color = vec4(v_color.rgb * (diff + ambient), v_color.a);
}