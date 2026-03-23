#version 330
in vec3 worldPos;
uniform vec3 cameraPos;
out vec4 f_color;

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
    
    // 1. Økt falloff-distanse for å se rutenettet lenger (Blender bruker ca 100-500m)
    float maxDist = 200.0;
    float falloff = smoothstep(maxDist, 0.0, d);

    // 2. Lag to lag med rutenett med spesifisert piksel-tykkelse
    // grid(posisjon, rute-størrelse, piksel-tykkelse)
    float g1 = grid(worldPos.xz, 1.0, 1.2) * 0.4;  // De små rutene (1.2 piksler tykke)
    float g2 = grid(worldPos.xz, 10.0, 2.5) * 0.7; // De store rutene (2.5 piksler tykke)
    
    float gridMask = max(g1, g2);
    
    // 3. Gjør fargen lysere for mer kontrast
    vec3 color = vec3(0.6); 

    // Akser med fast tykkelse (X=Rød, Z=Grønn)
    float axisWidth = 0.08;
    if (abs(worldPos.z) < axisWidth) color = vec3(1.0, 0.2, 0.2); 
    if (abs(worldPos.x) < axisWidth) color = vec3(0.2, 1.0, 0.2);

    // 4. Sluttresultat
    // Vi bruker en litt kraftigere alpha-verdi for at det skal "poppe" mer
    float alpha = gridMask * falloff;
    
    // "Early discard" for ytelse
    if (alpha < 0.01) discard;

    f_color = vec4(color, alpha);
}