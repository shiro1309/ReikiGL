import numpy as np
import numpy.typing as npt

def q_conjugate(q: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
    """
    Conjugate of quaternion q = [w, x, y, z].
    """
    return np.array([q[0], -q[1], -q[2], -q[3]])

def q_norm(q: npt.NDArray[np.float64]) -> np.float64:
    """
    Squared norm ||q||^2 of quaternion q.
    """
    return np.float64(np.dot(q,q))

def q_normalize(q: npt.NDArray[np.float64], eps=1e-12) -> npt.NDArray[np.float64]:
    """
    Normalize quaternion to unit length. Raises error if near-zero.
    """
    n = np.linalg.norm(q)
    if n < eps:
        raise ValueError("cant normalize a near-zero quaternion")
    return q / n

def q_inverse(q: npt.NDArray[np.float64], assume_unit=False, eps=1e-12) -> npt.NDArray[np.float64]:
    """
    Inverse of quaternion q.
    If assume_unit=True, returns conjugate directly (faster).
    Otherwise returns conjugate / ||q||^2.
    """
    qc = q_conjugate(q)
    if assume_unit:
        return qc
    n2 = q_norm(q)
    if n2 < eps:
        raise ZeroDivisionError("Cant invert a zero (or near-zero) quaternion.")
    return qc / n2


def is_unit_quaternion(q, tol=1e-6) -> bool:
    return abs(np.dot(q, q) - 1.0) <= tol

def rotate_vec_quat(vec=(0,0,0), theta=0.0, axis=(0,0,0)) -> npt.NDArray[np.float64]:
    """
    Builds a 4x4 matrix whose translation column is the rotated vector.
    theta in radians, axis is the rotation axis.

    Theta is given as a radian
    """

    # 0) set up the variables to be used
    vec = np.asarray(vec, dtype=np.float64)
    axis = np.asarray(axis, dtype=np.float64)

    # 1) Normalize axis
    n = np.linalg.norm(axis)
    if n == 0:
        raise ValueError("Rotation axis must be non-zero.")
    u_hat = axis / n

    # 2) Build unit quaternion
    half = theta / 2.0
    q = np.zeros(4, dtype=np.float64)
    q[0] = np.cos(half)
    q[1:4] = u_hat*np.sin(half)
    # re-normalize
    q /= np.linalg.norm(q)

    # make the "pure" vector
    v = np.array([0.0, *vec], dtype=np.float64)

    v_rot = q_mul(q_mul(q, v), q_conjugate(q))

    return v_rot[1:]

def q_mul(a: npt.NDArray[np.float64], b: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
    aw, ax, ay, az = a
    bw, bx, by, bz = b
    return np.array([
        aw*bw - ax*bx - ay*by - az*bz,
        aw*bx + ax*bw + ay*bz - az*by,
        aw*by - ax*bz + ay*bw + az*bx,
        aw*bz + ax*by - ay*bx + az*bw
    ], dtype=a.dtype)

def quat_rotation_matrix(q: npt.NDArray[np.float64]) -> npt.NDArray:
    w, x, y, z = q
    return np.array([
        [1-2*(y**2+z**2), 2*(x*y - z*w),   2*(x*z + y*w),   0],
        [2*(x*y + z*w),   1-2*(x**2+z**2), 2*(y*z - x*w),   0],
        [2*(x*z - y*w),   2*(y*z + x*w),   1-2*(x**2+y**2), 0],
        [0, 0, 0, 1]
        ], dtype=np.float64)

def rotate_quaternion(quaternion, theta_frame, axis) -> np.ndarray:
    delta_quaternion = build_quaternion(theta_frame, axis)

    quaternion = q_mul(delta_quaternion, quaternion)

    quaternion /= np.linalg.norm(quaternion)

    return quaternion


def build_quaternion(theta, axis) -> np.ndarray:
    axis = np.asarray(axis, dtype=np.float64)
    u_hat = axis / np.linalg.norm(axis)
    half = theta / 2.0
    w = np.cos(half)
    x, y, z = np.sin(half) * u_hat
    return np.array([w, x, y, z], dtype=np.float64)

#--------------------------------------------------------------
# PURE NUMPY QUAT ROTATION (THIS WAS PAIN IN THE ASS TO DO BTW)
#--------------------------------------------------------------

def q_mul_vectorized(a, b) -> npt.NDArray[np.float64]:
    # a og b har shape (N, 4)
    aw, ax, ay, az = a[:, 0], a[:, 1], a[:, 2], a[:, 3]
    bw, bx, by, bz = b[:, 0], b[:, 1], b[:, 2], b[:, 3]
    
    res = np.empty_like(a)
    res[:, 0] = aw*bw - ax*bx - ay*by - az*bz
    res[:, 1] = aw*bx + ax*bw + ay*bz - az*by
    res[:, 2] = aw*by - ax*bz + ay*bw + az*bx
    res[:, 3] = aw*bz + ax*by - ay*bx + az*bw
    return res

def quat_rotation_matrix_vectorized(q) -> npt.NDArray[np.float64]:
    w, x, y, z = q[:, 0], q[:, 1], q[:, 2], q[:, 3]
    N = q.shape[0]
    
    mat = np.zeros((N, 4, 4), dtype=np.float64)
    mat[:, 0, 0] = 1 - 2*(y**2 + z**2)
    mat[:, 0, 1] = 2*(x*y - z*w)
    mat[:, 0, 2] = 2*(x*z + y*w)
    
    mat[:, 1, 0] = 2*(x*y + z*w)
    mat[:, 1, 1] = 1 - 2*(x**2 + z**2)
    mat[:, 1, 2] = 2*(y*z - x*w)
    
    mat[:, 2, 0] = 2*(x*z - y*w)
    mat[:, 2, 1] = 2*(y*z + x*w)
    mat[:, 2, 2] = 1 - 2*(x**2 + y**2)
    
    mat[:, 3, 3] = 1
    return mat

def build_quaternion_vectorized(theta, axis) -> npt.NDArray[np.float64]:
    # theta: (N, 1), axis: (N, 3)
    norm = np.linalg.norm(axis, axis=1, keepdims=True)
    u_hat = np.divide(axis, norm, out=np.zeros_like(axis), where=norm != 0)
    
    half = theta / 2.0
    w = np.cos(half)
    xyz = np.sin(half) * u_hat
    return np.concatenate([w, xyz], axis=1)

def rotate_quaternion_vectorized(quaternion, theta_frame, axis) -> npt.NDArray[np.float64]:
    # quaternion: (N, 4), theta_frame: (N, 1), axis: (N, 3)
    delta_q = build_quaternion_vectorized(theta_frame, axis)
    
    # Multipliser alle samtidig
    new_q = q_mul_vectorized(delta_q, quaternion)
    
    # Normaliser hver rad
    q_norm = np.linalg.norm(new_q, axis=1, keepdims=True)
    return new_q / q_norm