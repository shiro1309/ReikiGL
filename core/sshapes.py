import math
from typing import Tuple, List

def create_batched_sphere(radius, sectors=20, stacks=20, color=[1.0, 1.0, 1.0, 1.0]) -> Tuple[List, List]:
    vertices = []
    indices = []

    # 1. Generate Vertices (Pos, UV, Norm, Color)
    for i in range(stacks + 1):
        phi = math.pi / 2 - i * math.pi / stacks
        for j in range(sectors + 1):
            theta = j * 2 * math.pi / sectors
            
            # Position
            x = radius * math.cos(phi) * math.cos(theta)
            y = radius * math.cos(phi) * math.sin(theta)
            z = radius * math.sin(phi)
            
            # Normals (for a sphere, normalized pos = normal)
            mag = math.sqrt(x*x + y*y + z*z)
            nx, ny, nz = (x/mag, y/mag, z/mag) if mag != 0 else (0, 0, 1)

            # UVs
            u, v = j / sectors, i / stacks

            # Record: 3f (Pos), 2f (UV), 3f (Norm), 4f (Color) = 12 floats
            vertices.extend([x, y, z, u, v, nx, ny, nz, *color])

    # 2. Generate Indices
    for i in range(stacks):
        k1 = i * (sectors + 1)
        k2 = k1 + sectors + 1
        for j in range(sectors):
            if i != 0:
                indices.extend([k1 + j, k2 + j, k1 + j + 1])
            if i != (stacks - 1):
                indices.extend([k1 + j + 1, k2 + j, k2 + j + 1])
                
    return vertices, indices