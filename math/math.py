import numpy as np
from typing import Tuple, Optional
import numpy.typing as npt



def reflect(incident: npt.NDArray[np.float32], normal: npt.NDArray[np.float32]) -> npt.NDArray[np.float32]:
    incident /= np.linalg.norm(incident)
    normal /= np.linalg.norm(normal)
    return incident - 2*(np.dot(normal, incident)) * normal

def refract(incident: npt.NDArray[np.float32], normal: npt.NDArray[np.float32], n1: float=1.0, n2: float=1.5) -> npt.NDArray[np.float32]:
    eta = n1/n2
    incident /= np.linalg.norm(incident)
    normal /= np.linalg.norm(normal)

    cos_i = np.dot(normal, incident)
    sin2_t = 1.0 - eta**2 * (1.0 - cos_i**2)
    if sin2_t < 0.0:
        return reflect(incident, normal)
    
    return eta * incident - (eta * cos_i + np.sqrt(sin2_t)) * normal


def sjekk_rotert_sirkel(start: npt.NDArray[np.float32], 
                        retning: npt.NDArray[np.float32], 
                        senter: npt.NDArray[np.float32], 
                        normal: npt.NDArray[np.float32], 
                        radius: float
                        ) ->Tuple[bool, Optional[npt.NDArray[np.float32]], Optional[np.float32]]:
    """
    Sjekker kollisjon med en fylt sirkel i 3D.
    - normal: Vektoren som står vinkelrett på sirkelens flate (f.eks [0,0,1] for flat)
    """
    # Normaliser vektorer for sikkerhets skyld
    retning = (retning / np.linalg.norm(retning)).astype(np.float32)
    normal = (normal / np.linalg.norm(normal)).astype(np.float32)

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
