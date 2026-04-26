#version 330

in vec3 o_position;
in vec4 o_color;
in vec3 o_normal;
in vec4 o_fragPosition;

out vec4 color;

uniform vec3 u_camera_pos;

// --- LIGHT 1: THE SUN (Global/Directional) ---
uniform vec3 u_light_pos;
uniform vec3 u_light_color = vec3(1.0, 0.95, 0.9);
uniform float u_light_intensity = 1.0;

// --- LIGHT 2: SHIP INTERIOR (Local Point Light) ---
uniform vec3  u_ship_light_pos;
uniform vec3  u_ship_light_color = vec3(0.2, 0.6, 1.0); // Cool blue interior?
uniform float u_ship_light_strength = 0.3;

void main() {
    vec3 norm = normalize(o_normal);
    vec3 viewDir = normalize(u_camera_pos - o_fragPosition.xyz);

    // 1. Setup a "Sun Visibility" factor (its for glass rendering)
    // If alpha is >= 0.5, sunFactor is 1.0 (on). 
    // If alpha is < 0.5, sunFactor is 0.0 (off).
    float sunFactor = (o_color.a < 0.5) ? 0.0 : 1.0;

    // --- CALCULATE SUN LIGHT ---
    vec3 sunDir = normalize(u_light_pos - o_fragPosition.xyz);
    float sunDiff = max(dot(norm, sunDir), 0.0);
    vec3 sunFinal = sunDiff * u_light_color * u_light_intensity * sunFactor;

    // --- CALCULATE SHIP LIGHT (with distance fade) ---
    vec3 shipLightVec = u_ship_light_pos - o_fragPosition.xyz;
    float distance = length(shipLightVec);
    vec3 shipLightDir = normalize(shipLightVec);
    
    // Attenuation: Light drops off over distance (1.0 / dist^2)
    float attenuation = 1.0 / (1.0 + 0.1 * distance + 0.01 * (distance * distance));
    
    float shipDiff = max(dot(norm, shipLightDir), 0.0);
    vec3 shipFinal = shipDiff * u_ship_light_color * u_ship_light_strength * attenuation;

    // --- SPECULAR (Combined) ---
    // We'll just use the Sun for the main shiny spot, or add both
    vec3 reflectDir = reflect(-sunDir, norm);
    float specFactor = pow(max(dot(viewDir, reflectDir), 0.0), 12.0);
    vec3 specular = specFactor * vec3(1.0);

    // --- AMBIENT ---
    vec3 ambient = vec3(0.1, 0.1, 0.12); 

    // --- FINAL COMBINE ---
    // Multiply object color by the sum of all light hitting it
    vec3 totalLight = sunFinal + shipFinal + ambient;
    vec3 finalRGB = (o_color.rgb * totalLight) + specular;

    color = vec4(finalRGB, o_color.a);
}