import numpy as np
import math
from icosphere import icosphere
from typing import Tuple, List

from ..math import noise

def create_uv_sphere(radius: float, sectors: int = 20, stacks: int = 20) -> Tuple[list[float], list[int]]:
    vertices = []
    indices = []

    # Generate Vertices
    for i in range(stacks + 1):
        phi = math.pi / 2 - i * math.pi / stacks
        for j in range(sectors + 1):
            theta = j * 2 * math.pi / sectors
            
            # Position (x, y, z)
            x = radius * math.cos(phi) * math.cos(theta)
            y = radius * math.cos(phi) * math.sin(theta)
            z = radius * math.sin(phi)
            
            # For our '3f 2f 3f' format: Pos, Tex, Normal
            # Position
            vertices.extend([x, y, z])
            # TexCoord (Optional 0,0 for now)
            vertices.extend([j / sectors, i / stacks])
            # Normal (For a sphere, normalized position is the normal)
            mag = math.sqrt(x*x + y*y + z*z)
            vertices.extend([x/mag, y/mag, z/mag] if mag != 0 else [0, 0, 1])

    # Generate Indices
    for i in range(stacks):
        k1 = i * (sectors + 1)
        k2 = k1 + sectors + 1
        for j in range(sectors):
            if i != 0:
                indices.extend([k1 + j, k2 + j, k1 + j + 1])
            if i != (stacks - 1):
                indices.extend([k1 + j + 1, k2 + j, k2 + j + 1])
                
    return vertices, indices

def create_icosphere_fast(radius: float, subdivisions: int = 3):
    # 1. Get raw geometry (Vertices are Nx3, Faces are Mx3)
    vertices, faces = icosphere(subdivisions)
    
    # Scale by radius
    vertices = vertices * radius
    
    # 2. Generate Normals
    # For a sphere centered at 0,0,0, the normal is just the normalized position
    # vertices is already normalized by the library (unit sphere), 
    # but we'll re-calculate to be safe after radius scaling.
    norms = vertices / np.linalg.norm(vertices, axis=1, keepdims=True)
    
    # 3. Generate UVs (Spherical Mapping)
    x, y, z = vertices[:, 0], vertices[:, 1], vertices[:, 2]
    u = 0.5 + np.arctan2(z, x) / (2 * np.pi)
    v = 0.5 - np.arcsin(y / radius) / np.pi
    uvs = np.stack([u, v], axis=1)
    
    # 4. Interleave the data: [Pos(3), UV(2), Norm(3)]
    # This creates an (N, 8) array
    packed_data = np.hstack([vertices, uvs, norms]).astype('f4')
    
    # 5. Flatten for your batch system
    final_vertices = packed_data.ravel().tolist()
    final_indices = faces.astype('u4').ravel().tolist()
    
    return final_vertices, final_indices

def create_icosphere_fast_color(radius: float, subdivisions: int = 3):
    vertices, faces = icosphere(subdivisions)
    vertices = vertices * radius

    # 2. Generate Normals
    # For a sphere centered at 0,0,0, the normal is just the normalized position
    # vertices is already normalized by the library (unit sphere), 
    # but we'll re-calculate to be safe after radius scaling.
    norms = vertices / np.linalg.norm(vertices, axis=1, keepdims=True)
    
    # 3. Generate UVs (Spherical Mapping)
    x, y, z = vertices[:, 0], vertices[:, 1], vertices[:, 2]
    u = 0.5 + np.arctan2(z, x) / (2 * np.pi)
    v = 0.5 - np.arcsin(y / radius) / np.pi
    uvs = np.stack([u, v], axis=1)

    # 3.5 add color channel
    col_channel = np.full((vertices.shape[0], 4), 1.0)

    
    # 4. Interleave the data: [Pos(3), UV(2), Norm(3)]
    # This creates an (N, 8) array
    packed_data = np.hstack([vertices, uvs, norms, col_channel]).astype('f4')
    
    # 5. Flatten for your batch system
    final_vertices = packed_data.ravel().tolist()
    final_indices = faces.astype('u4').ravel().tolist()
    
    return final_vertices, final_indices

def create_planet_fast_color(radius: float, subdivisions: int = 64, octaves: int = 8, persistence: float=0.5, lacunarity: float=2.0):
    # 1. Generate the raw Icosphere
    vertices, faces = icosphere(subdivisions)
    
    # 2. Setup Noise Gradients (N_GRAD must be large enough for high frequencies)
    N_GRAD = 32
    DIST_STR = 0.1
    SEA_LEVEL = 0.6

    phi = np.random.uniform(0, 2*np.pi, (N_GRAD, N_GRAD, N_GRAD))
    costheta = np.random.uniform(-1, 1, (N_GRAD, N_GRAD, N_GRAD))
    theta = np.arccos(costheta)
    grads = np.stack([
        np.sin(theta)*np.cos(phi), 
        np.sin(theta)*np.sin(phi), 
        np.cos(theta)
    ], axis=-1)

    # 3. Calculate Fractal Noise (Sampling per vertex)
    # The 'base_freq' controls the size of continents
    base_freq = 1.2 
    noise_vals = noise.vectorized_fractal_3d(
        vertices[:,0] * base_freq, 
        vertices[:,1] * base_freq, 
        vertices[:,2] * base_freq, 
        grads, 
        octaves=octaves,
        persistence=persistence,
        lacunarity=lacunarity
    )
    
    # Normalize noise to 0.0 - 1.0 range
    v_min, v_max = noise_vals.min(), noise_vals.max()
    elev = (noise_vals - v_min) / (v_max - v_min)

    # Redistribution (Power Curves)
    elev = np.power(elev, 0.7)

    # adding the displacment
    displacement_strength = radius * DIST_STR

    land_mask = np.maximum(0, elev - SEA_LEVEL) 
    final_radius = radius + (land_mask * displacement_strength)

    # 4. Generate Geometry
    scaled_vertices = vertices * final_radius[:, np.newaxis]
    norms = vertices # Unit vector direction
    
    u = 0.5 + np.arctan2(vertices[:, 2], vertices[:, 0]) / (2 * np.pi)
    v = 0.5 - np.arcsin(vertices[:, 1]) / np.pi
    uvs = np.stack([u, v], axis=1)

    # 5. Color Palette Logic (Per-Vertex)
    col_channel = np.zeros((vertices.shape[0], 4))
    for i in range(vertices.shape[0]):
        e = elev[i]
        if e < 0.50:   col_channel[i] = [0.1, 0.2, 0.6, 1.0] # Deep Ocean
        elif e < 0.6:  col_channel[i] = [0.2, 0.4, 0.8, 1.0] # Coast
        elif e < 0.70: col_channel[i] = [0.9, 0.8, 0.5, 1.0] # Beach
        elif e < 0.80: col_channel[i] = [0.2, 0.5, 0.1, 1.0] # Forest
        elif e < 0.90: col_channel[i] = [0.4, 0.3, 0.2, 1.0] # Rock/Dirt
        else:          col_channel[i] = [1.0, 1.0, 1.0, 1.0] # Snow Caps

    # 6. Interleave and Flatten
    packed_data = np.hstack([scaled_vertices, uvs, norms, col_channel]).astype('f4')
    
    return packed_data.ravel().tolist(), faces.astype('u4').ravel().tolist()



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