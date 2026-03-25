from __future__ import annotations
from typing import cast, Tuple
import numpy as np
from ..Input import InputManager
import moderngl as mgl
from abc import ABC, abstractmethod


def normalize(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v)
    if n < 1e-8:
        return v
    return v / n

class BaseCamera(ABC):
    def __init__(self) -> None:
        self.position = np.array([0.0, 50.0, 60.0], dtype=float)
        self.target   = np.array([0.0, 0.0, 0.0], dtype=float)
        self.up       = np.array([0.0, 1.0, 0.0], dtype=float)


        self.pitch = 0.0
        self.yaw   = 0.0

        self.fov        = 90.0
        self.near       = 0.1
        self.far        = 1000.0
        self.aspect = 16/9

    @abstractmethod
    def update(self, dt, input: InputManager):
        pass




    def get_view_matrix(self) -> np.ndarray:
        f = normalize(self.target - self.position)               # forward (towards -Z in view if you prefer)
        s = normalize(np.cross(f, self.up))     # side
        u = np.cross(s, f)                      # true up

        M = np.eye(4, dtype=np.float32)

        M[0, :3] = s
        M[1, :3] = u
        M[2, :3] = -f

        M[0, 3] = -np.dot(s, self.position)
        M[1, 3] = -np.dot(u, self.position)
        M[2, 3] =  np.dot(f, self.position)
        return M


    def get_projection_matrix(self) -> np.ndarray:
        f = 1.0 / np.tan(np.radians(self.fov) / 2.0)
        nf = 1.0 / (self.near - self.far)
        P = np.zeros((4, 4), dtype=np.float64)
        P[0,0] = f / max(self.aspect, 1e-8)
        P[1,1] = f
        P[2,2] = (self.far + self.near) * nf
        P[2,3] = (2.0 * self.far * self.near) * nf
        P[3,2] = -1.0
        return P

    def apply_to_shader(self, prog: mgl.Program, view, proj) -> None:
        view_data = cast(mgl.Uniform, prog[view])
        view_data.write(self.get_view_matrix().T.astype('f4').tobytes())

        proj_data = cast(mgl.Uniform, prog[proj])
        proj_data.write(self.get_projection_matrix().T.astype('f4').tobytes())


class Camera(BaseCamera):
    def __init__(self, name) -> None:
        super().__init__()
        self.name: str = name
        self.yaw: float = -90
        self.speed: float = 0.2
        self.sensitivity: float = 0.1

        self.front: np.ndarray = np.array([0.0, 0.0, -1.0], dtype=np.float32)

    def get_view_matrix(self) -> np.ndarray:
        f = normalize(self.front)               # forward (towards -Z in view if you prefer)
        s = normalize(np.cross(f, self.up))     # side
        u = np.cross(s, f)                      # true up

        M = np.eye(4, dtype=np.float32)

        M[0, :3] = s
        M[1, :3] = u
        M[2, :3] = -f

        M[0, 3] = -np.dot(s, self.position)
        M[1, 3] = -np.dot(u, self.position)
        M[2, 3] =  np.dot(f, self.position)
        return M
    
    def update(self, dt, input: InputManager) -> None:
        if input.is_down("forward"):
            self.position += self.front * self.speed

        if input.is_down("backward"):
            self.position -= self.front * self.speed

        if input.is_down("right"):
            self.position += self.right() * self.speed

        if input.is_down("left"):
            self.position -= self.right() * self.speed

        if input.is_mouse_drag("right"):
            self.rotate(input.mouse_dx, input.mouse_dy)
            self.update_vectors()

    def right(self) -> np.ndarray:
        return normalize(np.cross(self.front, self.up))
    
    def rotate(self, yaw_delta: float = 0.0, pitch_delta: float = 0.0) -> None:
        self.yaw += yaw_delta * self.sensitivity
        self.pitch += pitch_delta * self.sensitivity
        self.pitch = np.clip(self.pitch, -89.0, 89.0)


    def update_vectors(self) -> None:
        # Beregn ny front-vektor basert på vinkler
        y = np.radians(self.yaw)
        p = np.radians(self.pitch)

        self.front = normalize(np.array([
            np.cos(y) * np.cos(p),
            np.sin(p),
            np.sin(y) * np.cos(p)
        ], dtype=np.float32))

# blender style camera
# would need multiple modes that can interact
# should be able to go from gimple to normal with no problem
# normal mode is to be left/right and such will be unlocked with shift and move with wasd for all of them
# use scrool wheel to move back and forth but only when shift is not cliked

class BlenderCamera(BaseCamera):
    """
    A Blender-style Orbit (Arcball) camera.
    Uses a 'target' point as the orbit center and calculates position 
    based on distance, yaw, and pitch.
    """
    def __init__(self) -> None:
        super().__init__()
        self.distance = 10

        self.speed = .2
        self.sensitivity = .1

    def zoom(self, scroll_input, speed=0.1, min_dist=0.01) -> None:
        """
        Adjusts distance from target. Multiplicative zoom (1 - input) 
        makes zooming smoother and prevents hitting zero too easily.
        """
        self.distance *= (1 - scroll_input * speed)
        self.distance = max(self.distance, min_dist)

    def update_position(self) -> None:
        """
        Recalculates the camera's world position based on the current 
        target, yaw, pitch, and distance.
        """
        forward, _, _ = self.get_orientation_vectors()

        self.position = self.target + (forward * self.distance)

    def get_orientation_vectors(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Calculates the Local Coordinate System (Basis) for the camera.
        Returns: (Forward, Right, Up) vectors as unit-length np.ndarrays.
        """
        ryaw = np.radians(self.yaw)
        rpitch = np.radians(self.pitch)

        # Calculate Forward Vector (Direction from Target to Camera)
        # Using a standard Spherical to Cartesian coordinate conversion
        f_x = np.cos(rpitch) * np.sin(ryaw)
        f_y = np.sin(rpitch)
        f_z = np.cos(rpitch) * np.cos(ryaw)
        forward = np.array([f_x, f_y, f_z])

        # Calculate Right Vector (Side-to-side movement)
        # Cross product of World Up and Forward keeps 'Right' on the horizontal plane
        world_up = np.array([0, 1, 0])
        right = np.cross(world_up, forward)

        # Guard against Gimbal Lock when looking straight up/down
        if np.linalg.norm(right) < 0.001:
            right = np.array([1, 0, 0])
        else:
            right /= np.linalg.norm(right)

        # Calculate Up Vector (Vertical movement relative to view)
        # This is the 'Screen Up' vector, perpendicular to where we look
        up = np.cross(forward, right)
        up /= np.linalg.norm(up)

        return forward, right, up


    def update(self, dt, input: InputManager) -> None:
        """
        Core logic loop: Handles zooming, panning (Shift+Mid), and orbiting (Mid).
        """
        if input.scrolling:
            self.zoom(input.mouse_scroll_dy)

        _, right, up = self.get_orientation_vectors()

        if input.is_down("shift") and input.is_mouse_drag("right"):
            pan_speed = self.distance * 0.0015

            dx = -input.mouse_dx * pan_speed
            dy = -input.mouse_dy * pan_speed
            
            pan_vector = (right * dx) + (up * dy)
            self.target += pan_vector

        elif input.is_mouse_drag("right"):
            self.yaw -= input.mouse_dx * self.sensitivity
            self.pitch -= input.mouse_dy * self.sensitivity

            self.pitch = np.clip(self.pitch, -89, 89)

        self.update_position()

    def apply_to_shader(self, prog: mgl.Program, view, proj) -> None:
        """
        Writes the camera matrices to the GPU shader.
        Uses .T (transpose) because ModernGL/OpenGL expects Column-Major matrices.
        """
        view_data = cast(mgl.Uniform, prog[view])
        view_data.write(self.get_view_matrix().T.astype('f4').tobytes())

        proj_data = cast(mgl.Uniform, prog[proj])
        proj_data.write(self.get_projection_matrix().T.astype('f4').tobytes())
