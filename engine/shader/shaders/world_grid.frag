#version 330 core
in vec3 worldPos;
uniform vec3 cameraPos;
out vec4 f_color;

const vec3  SMALL_GRID_COLOR = vec3(0.286, 0.286, 0.286)*3;  // Farge på 1m ruter
const vec3  LARGE_GRID_COLOR = vec3(0.326, 0.326, 0.326)*2.5;  // Farge på 10m ruter
const vec3  X_AXIS_COLOR     = vec3(0.584, 0.24, 0.286);  // Rød X-akse
const vec3  Z_AXIS_COLOR     = vec3(0.388, 0.5412, 0.153);  // Grønn Z-akse

// --- STYRKE OG TYKKELSE ---
const float SMALL_OPACITY    = 0.2;                  // Gjennomsiktighet 1m ruter
const float LARGE_OPACITY    = 0.4;                  // Gjennomsiktighet 10m ruter
const float AXIS_OPACITY     = 0.6;                  // Styrke på aksene
const float LINE_THICKNESS   = 1.0;                  // Generell tykkelse i piks

const float LARGE_GRID_FALLOFF = 400;
const float SMALL_GRID_FALLOFF = 250;

float grid(vec2 p, float size, float thickness) {
    vec2 coord = p / size;
    
    // fwidth forteller oss hvor mye 'coord' endrer seg per piksel.
    // Ved å gange med 'thickness', tvinger vi linjen til å være X piksler bred.
    vec2 derivative = fwidth(coord);
    vec2 grid = abs(fract(coord - 0.5) - 0.5) / (derivative * thickness);
    
    float line = min(grid.x, grid.y);
    return 1.0 - min(line, 1.0);
}

void main() {
    float d = length(worldPos.xz - cameraPos.xz);
    
    float globalFalloff = smoothstep(LARGE_GRID_FALLOFF, 20.0, d);
    float smallGridFalloff = smoothstep(SMALL_GRID_FALLOFF, 15.0, d);

    // 3. Beregn rutenett-masker
    float g1 = grid(worldPos.xz, 1.0, LINE_THICKNESS);        // 1m
    float g2 = grid(worldPos.xz, 10.0, LINE_THICKNESS * 1.5); // 10m

    // 4. Akse-masker
    float xMask = 1.0 - smoothstep(0.0, fwidth(worldPos.z) * LINE_THICKNESS * 2.0, abs(worldPos.z));
    float zMask = 1.0 - smoothstep(0.0, fwidth(worldPos.x) * LINE_THICKNESS * 2.0, abs(worldPos.x));

    // 5. Fjern grid der aksene er
    float maskNoAxis = 1.0 - max(xMask, zMask);
    
    // Bruk den spesifikke falloffen på det lille rutenettet (cleanG1)
    float cleanG1 = g1 * maskNoAxis * smallGridFalloff;
    float cleanG2 = g2 * maskNoAxis;

    // 6. Farge-kombinasjon
    vec3 gridPart = (SMALL_GRID_COLOR * cleanG1 * SMALL_OPACITY) + 
                    (LARGE_GRID_COLOR * cleanG2 * LARGE_OPACITY);
    
    vec3 axisPart = (X_AXIS_COLOR * xMask * AXIS_OPACITY) + 
                    (Z_AXIS_COLOR * zMask * AXIS_OPACITY);

    // Bruk globalFalloff på hele resultatet til slutt
    vec3 finalRGB = (gridPart + axisPart) * globalFalloff;
    
    float alphaG1 = cleanG1 * SMALL_OPACITY;
    float alphaG2 = cleanG2 * LARGE_OPACITY;
    float alphaAxes = max(xMask, zMask) * AXIS_OPACITY;

    float finalAlpha = max(max(alphaG1, alphaG2), alphaAxes) * globalFalloff;

    if (finalAlpha < 0.01) discard;
    f_color = vec4(finalRGB, finalAlpha);
}