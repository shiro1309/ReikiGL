#version 330

in vec3 in_position;
uniform mat4 m_proj;
uniform mat4 m_view;
out vec3 worldPos;

void main() {
    worldPos = in_position;
    gl_Position = m_proj * m_view * vec4(in_position, 1.0);
}