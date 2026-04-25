#version 330

in vec3 o_position;
in vec4 o_color;
in vec3 o_normal;
in vec4 o_fragPosition;

out vec4 color;

// Simple Uniforms (Easier to update in ModernGL)
uniform vec3 u_light_pos;
uniform vec3 u_camera_pos;
uniform vec3 u_light_color = vec3(1.0, 0.95, 0.9);
uniform float u_light_intensity = 1.0;

void main() {
    // 1. Setup vectors
    vec3 norm = normalize(o_normal);
    vec3 lightVec = u_light_pos - o_fragPosition.xyz;
    vec3 lightDir = normalize(lightVec);
    vec3 viewDir = normalize(u_camera_pos - o_fragPosition.xyz);

    // 2. Diffuse (The main "body" of the light)
    // We don't use distance attenuation here so it doesn't fade into a dot
    float diff = max(dot(norm, lightDir), 0.0);
    vec3 diffuse = diff * u_light_color * u_light_intensity;

    // 3. Specular (The "Shiny" reflection from your file)
    vec3 reflectDir = reflect(-lightDir, norm);
    // 12.0 is the shininess power from your file. Increase it for a smaller dot.
    float specFactor = pow(max(dot(viewDir, reflectDir), 0.0), 12.0);
    vec3 specular = specFactor * vec3(1.0); // Pure white shine

    // 4. Ambient (The baseline so the world isn't black)
    // This is the "secret sauce" to make it look like a sunlit world
    vec3 ambient = vec3(0.2, 0.2, 0.25); 

    // 5. Final Combine
    // We multiply the object's color by the light hitting it
    vec3 finalRGB = o_color.rgb * (diffuse + ambient) + specular;

    color = vec4(finalRGB, o_color.a);
}