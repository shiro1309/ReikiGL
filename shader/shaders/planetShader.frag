#version 330

in vec4 o_color;
in vec3 o_normal;
in vec4 o_fragPosition;
in vec3 v_local_pos;

out vec4 color;

uniform vec3 u_light_pos;
uniform vec3 u_camera_pos;
uniform float u_time;

// --- DEEP OCEAN TWEAKS ---
uniform vec3  u_ocean_target    = vec3(0.1, 0.2, 0.6);
uniform float u_ocean_foam_lvl  = 0.45;
uniform float u_ocean_foam_scl  = 8.0;   
uniform float u_ocean_foam_spd  = 0.4;

// --- COAST TWEAKS ---
uniform vec3  u_coast_target    = vec3(0.2, 0.4, 0.8);
uniform float u_coast_foam_lvl  = 0.35;  
uniform float u_coast_foam_scl  = 20.0;  
uniform float u_coast_foam_spd  = 0.8;   

uniform vec3  u_foam_color      = vec3(1.0, 1.0, 1.0);
uniform float u_color_tolerance = 0.25; 

// --- CLOUD TWEAKS ---
uniform float u_cloud_scale     = 0.5;   // Set to 0.5 for those big continent clouds
uniform float u_cloud_speed     = 0.1;
uniform float u_cloud_density   = 0.65;  // Higher = fewer, larger clouds
uniform float u_cloud_shadow    = 0.4;   // Shadow strength

// --- LIGHTING ---
uniform vec3  u_light_color     = vec3(1.0, 0.95, 0.9);
uniform float u_light_intensity = 1.0;
uniform float u_shininess       = 12.0;

// --- NOISE HELPERS ---
float hash(vec3 p) {
    p = fract(p * 0.3183099 + 0.1);
    p *= 17.0;
    return fract(p.x * p.y * p.z * (p.x + p.y + p.z));
}

float noise(vec3 x) {
    vec3 i = floor(x);
    vec3 f = fract(x);
    f = f * f * (3.0 - 2.0 * f);
    return mix(mix(mix(hash(i + vec3(0, 0, 0)), hash(i + vec3(1, 0, 0)), f.x),
                   mix(hash(i + vec3(0, 1, 0)), hash(i + vec3(1, 1, 0)), f.x), f.y),
               mix(mix(hash(i + vec3(0, 0, 1)), hash(i + vec3(1, 0, 1)), f.x),
                   mix(hash(i + vec3(0, 1, 1)), hash(i + vec3(1, 1, 1)), f.x), f.y), f.z);
}

float fbm(vec3 p) {
    float v = 0.0; float a = 0.5;
    for (int i = 0; i < 6; i++) {
        v += a * noise(p); p *= 2.0; a *= 0.5;
    }
    return v;
}

void main() {
    vec3 baseSurfaceRGB = o_color.rgb;
    float foamValue = 0.0;

    // 1. Water Detection & Foam
    float distToOcean = distance(baseSurfaceRGB, u_ocean_target);
    float distToCoast = distance(baseSurfaceRGB, u_coast_target);

    if (distToOcean < u_color_tolerance) {
        float n = noise(v_local_pos * u_ocean_foam_scl + (u_time * u_ocean_foam_spd));
        foamValue = clamp((n - u_ocean_foam_lvl) * 3.0, 0.0, 1.0);
    } 
    else if (distToCoast < u_color_tolerance) {
        float n = noise(v_local_pos * u_coast_foam_scl + (u_time * u_coast_foam_spd));
        float shimmer = noise(v_local_pos * 40.0 - u_time) * 0.2;
        foamValue = clamp((n - u_coast_foam_lvl) * 4.0 + shimmer, 0.0, 1.0);
    }

    baseSurfaceRGB = mix(baseSurfaceRGB, u_foam_color, foamValue);

    // 2. Lighting Calculation
    vec3 norm = normalize(o_normal);
    vec3 lightDir = normalize(u_light_pos - o_fragPosition.xyz);
    vec3 viewDir = normalize(u_camera_pos - o_fragPosition.xyz);

    float diff = max(dot(norm, lightDir), 0.0);
    vec3 ambient = vec3(0.2, 0.2, 0.25);
    vec3 diffuse = diff * u_light_color * u_light_intensity;

    vec3 reflectDir = reflect(-lightDir, norm);
    float specFactor = pow(max(dot(viewDir, reflectDir), 0.0), u_shininess);
    float waterMask = (distToOcean < 0.2 || distToCoast < 0.2) ? 1.5 : 0.3;
    vec3 specular = specFactor * vec3(1.0) * waterMask; 

    // The lit surface without clouds
    vec3 litSurface = baseSurfaceRGB * (diffuse + ambient) + specular;



    // 3. Cloud Logic (Big & Rare)
    float cloudScale = u_cloud_scale;

    float angle = u_time * 0.05;
    mat3 rot = mat3(
        cos(angle), 0, sin(angle),
        0, 1, 0,
        -sin(angle), 0, cos(angle)
    );
    
    vec3 seed = v_local_pos + vec3(u_time * u_cloud_speed);
    vec3 warp;
    warp.x = fbm(rot * (v_local_pos * 1.1 + seed));
    warp.y = fbm(rot * (v_local_pos * 1.2 + seed.yzx));
    warp.z = fbm(rot * (v_local_pos * 1.3 + seed.zxy));

    vec3 finalCloudPos = (v_local_pos + warp * 0.7) * cloudScale + (rot * seed * 0.2);

    // Cloud noise
    float rawNoise = fbm(finalCloudPos);
    
    // Create a very large, slow mask to break up the clouds into "weather systems"
    // We use the XYZ coordinates to make the mask irregular
    float mask = fbm(rot * (v_local_pos * (cloudScale * 0.3) - (u_time * 0.01)));
    mask = smoothstep(0.35, 0.55, mask);

    // Calculate Alpha
    float alpha = smoothstep(u_cloud_density, u_cloud_density + 0.2, rawNoise);
    alpha *= mask;

    // 4. Cloud Shadows (sampled slightly offset toward light)
    vec3 shadowPos = finalCloudPos + (lightDir * 0.03 * cloudScale);
    float shadowAlpha = smoothstep(u_cloud_density, u_cloud_density + 0.2, fbm(shadowPos));
    shadowAlpha *= mask;

    // 5. Final Assembly
    // Apply shadow to surface
    vec3 finalRGB = litSurface * (1.0 - shadowAlpha * u_cloud_shadow);
    // Blend white clouds on top
    finalRGB = mix(finalRGB, vec3(1.0), alpha);

    color = vec4(finalRGB, o_color.a);
}