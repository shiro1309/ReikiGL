import numpy as np
import numpy.typing as npt
from typing import Tuple

# -----------------------
# Vector helpers
# -----------------------
def normalize(v, eps=1e-8) -> npt.NDArray[np.float64]:
    v = np.asarray(v, dtype=np.float64)
    n = np.linalg.norm(v)
    return v if n < eps else (v / n)

def dot(a, b) -> np.float64:
    return np.float64(np.dot(a, b))

def cross(a, b) -> npt.NDArray[np.float64]:
    return np.cross(a, b)

# -----------------------
# Matrix builders (4x4)
# All return np.float32 arrays.
# Convention:
#   - Right-handed view space
#   - OpenGL clip space (Z in [-1,1])
# -----------------------

def translate(vec: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
    """Return a 4x4 translation matrix."""
    T = np.eye(4, dtype=np.float64)
    T[:3, 3] = np.asarray(vec, dtype=np.float64)[:3]
    return T


def scale(scale_vec: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
    """Return a 4x4 scaling matrix."""
    S = np.eye(4, dtype=np.float64)
    sx, sy, sz = (np.asarray(scale_vec, dtype=np.float64)[:3]
                  if np.ndim(scale_vec) else (scale_vec, scale_vec, scale_vec))
    S[0, 0], S[1, 1], S[2, 2] = sx, sy, sz
    return S


def rotate_z(theta: float) -> npt.NDArray[np.float64]:
    c, s = np.cos(theta), np.sin(theta)
    R = np.eye(4, dtype=np.float64)
    R[0,0], R[0,1], R[1,0], R[1,1] = c, -s, s, c
    return R

def rotate_x(theta: float) -> npt.NDArray[np.float64]:
    c, s = np.cos(theta), np.sin(theta)
    R = np.eye(4, dtype=np.float64)
    R[1,1], R[1,2], R[2,1], R[2,2] = c, -s, s, c
    return R

def rotate_y(theta: float) -> npt.NDArray[np.float64]:
    c, s = np.cos(theta), np.sin(theta)
    R = np.eye(4, dtype=np.float64)
    R[0,0], R[0,2], R[2,0], R[2,2] = c, s, -s, c
    return R

def rotate_euler(rx: float, ry: float, rz: float, order="XYZ") -> npt.NDArray[np.float64]:
    axes = {
        'X': rotate_x(rx),
        'Y': rotate_y(ry),
        'Z': rotate_z(rz),
    }
    M = np.eye(4, dtype=np.float64)
    for axis in order:
        M = axes[axis] @ M
    return M

def compose_model(translation=(0,0,0), euler=(0,0,0),  scale_val=(1,1,1), order="XYZ") -> npt.NDArray[np.float64]:
    T = translate(translation)
    S = scale(scale_val)
    R = rotate_euler(*euler, order=order)

    # Model = T * R * S (column-vector convention)
    return T @ R @ S

def transform_point(M: npt.NDArray[np.float64], p: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
    v = np.array([p[0], p[1], p[2], 1.0], dtype=np.float64)
    r = M @ v
    return (r[:3] / r[3]) if r[3] != 0 else r[:3]

def scale_vectorized(scales):
    # scales shape: (N, 3)
    N = scales.shape[0]
    S = np.zeros((N, 4, 4))
    S[:, 0, 0] = scales[:, 0] # x-skala
    S[:, 1, 1] = scales[:, 1] # y-skala
    S[:, 2, 2] = scales[:, 2] # z-skala
    S[:, 3, 3] = 1            # Homogen koordinat
    return S

def translate_vectorized(pos):
    # pos shape: (N, 3)
    N = pos.shape[0]
    T = np.eye(4)[np.newaxis, :, :].repeat(N, axis=0) # Lag N identitetsmatriser
    T[:, 0:3, 3] = pos  # Sett x, y, z inn i kolonne 3 for alle matriser
    return T