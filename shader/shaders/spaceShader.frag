#version 330

in vec3 o_position;
in vec4 o_color;
in vec3 o_normal;
in vec4 o_fragPosition;

out vec4 color;

uniform vec3 u_light_pos;
uniform vec3 u_diffuseColor = vec3(1.0);
uniform float u_light_size = 20.0;     // Larger = softer shadows/transitions
uniform float u_light_intensity = 1.0; 

void main() {
    vec3 norm = normalize(o_normal);
    
    // Calculate vector to light
    vec3 lightVec = u_light_pos - o_fragPosition.xyz;
    float distance = length(lightVec);
    vec3 lightDir = normalize(lightVec);

    // --- AREA LIGHT TRICK: Light Wrapping ---
    // Instead of a hard cutoff at dot(n, l) == 0, we allow the light to 
    // "wrap" around the object slightly, mimicking a large area source.
    float wrap = 0.5; 
    float diffIntensity = max(dot(norm, lightDir) + wrap, 0.0) / (1.0 + wrap);

    // --- AREA LIGHT TRICK: Soft Falloff ---
    // Blender Area Lights don't just cut off; they fade based on the inverse square law
    // We add u_light_size to the denominator to prevent "infinite" brightness when close.
    float attenuation = u_light_intensity / (1.0 + (distance * distance) / (u_light_size * u_light_size));

    // Combine with a strong baseline to ensure it's "well lit"
    vec3 lighting = u_diffuseColor * (diffIntensity * attenuation);
    
    // Add a subtle "Hemisphere" ambient so the backside isn't black
    vec3 ambient = vec3(0.1, 0.1, 0.15); 

    vec3 finalRGB = o_color.rgb * (lighting + ambient);
    
    // Optional: Boost saturation for that "strong" look
    color = vec4(finalRGB * 1.2, o_color.a);
}