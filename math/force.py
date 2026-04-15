import numpy as np
from typing import List, Tuple

def calculate_em_force(vel: np.ndarray, charge: np.float32, E_field: np.ndarray, B_field: np.ndarray) -> np.ndarray:
    # Lorentz Force: q * (E + v x B)
    v_cross_b = np.cross(vel, B_field)
    return charge * (E_field + v_cross_b)

#v_corss = np.cross(particles[3:6], B_field, axis=0)

def calculate_gravity(p1_pos: np.ndarray, 
                      p1_mass: np.float32, 
                      p1_radius: np.float32, 
                      p2_pos: np.ndarray, 
                      p2_mass: np.float32, 
                      p2_radius: np.float32, 
                      G: np.float32
                      ) -> np.ndarray:
    r_vec = p2_pos - p1_pos
    distance = np.linalg.norm(r_vec)
    
    # Avoid division by zero and extreme forces when overlapping
    if distance < (p1_radius + p2_radius):
        return np.zeros(3)
        
    force_mag = G * (p1_mass * p2_mass) / (distance**3)
    return r_vec * force_mag

