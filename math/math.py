import numpy as np
from typing import Tuple, Optional

def reflect(incident: np.ndarray, normal: np.ndarray) -> np.ndarray:
    incident /= np.linalg.norm(incident)
    normal /= np.linalg.norm(normal)
    return incident - 2*(np.dot(normal, incident)) * normal

def refract(incident: np.ndarray, normal: np.ndarray, n1: float=1.0, n2: float=1.5) -> np.ndarray:
    eta = n1/n2
    incident /= np.linalg.norm(incident)
    normal /= np.linalg.norm(normal)

    dot_ni = np.dot(normal, incident)
    check = 1.0 - eta**2 * (1.0 - dot_ni**2)
    if check < 0:
        return reflect(incident, normal)
    else:
        return eta * incident - (eta * dot_ni + np.sqrt(check)) * normal

def handle_refraction(ray_vec, actual_normal, n1, n2):
    eta = n1 / n2
    # Since actual_normal now always faces the ray, cos_i is always positive
    cos_i = -np.dot(actual_normal, ray_vec) 
    
    sin2_t = eta**2 * (1.0 - cos_i**2)
    
    if sin2_t > 1.0:
        return None  # Total Internal Reflection
        
    cos_t = np.sqrt(1.0 - sin2_t)
    return eta * ray_vec + (eta * cos_i - cos_t) * actual_normal

normal = np.array([0,1,0], dtype=np.float32)
incidentVector = np.array([0.707,-0.707,0], dtype=np.float32)


def sjekk_rotert_sirkel(start: np.ndarray[np.float32], 
                        retning: np.ndarray[np.float32], 
                        senter: np.ndarray[np.float32], 
                        normal: np.ndarray[np.float32], 
                        radius: float
                        ) ->Tuple[bool, Optional[np.ndarray[np.float32]], Optional[np.float32]]:
    """
    Sjekker kollisjon med en fylt sirkel i 3D.
    - normal: Vektoren som står vinkelrett på sirkelens flate (f.eks [0,0,1] for flat)
    """
    # Normaliser vektorer for sikkerhets skyld
    retning = retning / np.linalg.norm(retning)
    normal = normal / np.linalg.norm(normal)

    # 1. Finn punktet der linjen krysser sirkelens plan
    # Formel: t = ((senter - start) dot normal) / (retning dot normal)
    nevner = np.dot(retning, normal)
    
    if abs(nevner) < 1e-6:
        return False, None, None

    t = np.dot(senter - start, normal) / nevner

    if t < 0:
        return False, None, None

    # 2. Beregn det nøyaktige treffpunktet P i 3D-rommet
    P = start + t * retning

    # 3. Sjekk om avstanden fra senter til P er mindre enn radius
    # Vi bruker vanlig 3D-avstand her
    avstand = np.linalg.norm(P - senter)

    if avstand <= radius:
        return True, P, t
    else:
        return False, None, None
