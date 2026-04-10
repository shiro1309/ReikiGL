#version 330

in vec3 o_position;
in vec4 o_color;
in vec3 o_normal;
in vec4 o_fragPosition;

out vec4 color;

// Material properties
uniform vec3 u_diffuseColor = vec3(1.0);
uniform vec3 u_specularColor = vec3(1.0);

// Flattened GlobalState for easier Python binding
uniform vec3 u_light_pos;
uniform vec3 u_camera_pos;

void main() {
    vec4 baseColor = o_color;

    // Diffuse computations
    vec3 norm = normalize(o_normal);
    vec3 lightDirection = normalize(u_light_pos - o_fragPosition.xyz);
    
    // Ambient - added a small baseline so it's not pitch black in shadow
    float ambient = 0.15;
    float diffIntensity = max(dot(norm, lightDirection), 0.0);
    vec3 diffuseColor = (diffIntensity + ambient) * u_diffuseColor;

    // Specular computations (Phong)
    vec3 reflectedLight = normalize(reflect(-lightDirection, norm));
    vec3 observerDirection = normalize(u_camera_pos - o_fragPosition.xyz);
    
    // S = str * (ref . obs)^n
    float specFactor = pow(max(dot(observerDirection, reflectedLight), 0.0), 32.0); // 32 is a standard shininess
    vec3 specular = specFactor * u_specularColor;

    // Compute the final colors
    // We multiply the base vertex color by the combined light factors
    color = vec4(baseColor.rgb * (diffuseColor + specular), baseColor.a);
}