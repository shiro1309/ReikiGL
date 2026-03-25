import numpy as np
from typing import cast
import moderngl as mgl
from .camera import Camera, BaseCamera
from ..shader import import_shader
from dataclasses import dataclass
from ..math import *

class Grid:
    def __init__(self, shader, ctx: mgl.Context) -> None:
        self.ctx = ctx
        self.prog = import_shader(self.ctx, shader)

        vertices = np.array([
            -1000.0, -0.01, -1000.0,
             1000.0, -0.01, -1000.0,
            -1000.0, -0.01,  1000.0,
             1000.0, -0.01,  1000.0,
        ], dtype='f4')
        vbo = self.ctx.buffer(vertices)
        self.vao = self.ctx.simple_vertex_array(self.prog, vbo, 'in_position')

    def draw(self, camera: BaseCamera) -> None:
        self.ctx.wireframe = False
        self.ctx.disable(mgl.CULL_FACE)
        self.ctx.enable(mgl.BLEND)

        camera.apply_to_shader(self.prog, 'm_view', 'm_proj')
        self.add_to_shader(self.prog, np.array(camera.position, 'f4'), 'cameraPos')

        self.vao.render(mgl.TRIANGLE_STRIP)
        
        self.ctx.disable(mgl.BLEND)
        self.ctx.enable(mgl.CULL_FACE)

    def add_to_shader(self, prog: mgl.Program, matrix: np.ndarray, where: str) -> None:
        data = cast(mgl.Uniform, prog[where])
        data.write(matrix.astype('f4').tobytes())


class Line3D:
    def __init__(self, ctx: mgl.Context, p0, p1, program: mgl.Program, *,color: tuple[int, int, int, int] | tuple[int, int, int] = (255, 255, 255, 255), translation=(0,0,0)) -> None:
        self.ctx = ctx
        self.program = program
        self.translation = np.array(translation, dtype="f4")

        r, g, b, *a = color
        self.color = r/255, g/255, b/255, a[0]/255 if a else 1

        self.color

        self.p0 = np.array(p0, dtype="f4")
        self.p1 = np.array(p1, dtype="f4")

        # make initial VBO + VAO
        self._build_buffers()

        

    def _build_buffers(self) -> None:
        v0 = (*self.p0, *self.color, *self.translation)
        v1 = (*self.p1, *self.color, *self.translation)

        vertex_data = np.array([*v0, *v1], dtype="f4")

        self.vbo = self.ctx.buffer(vertex_data.tobytes())

        self.vao = self.ctx.vertex_array(
            self.program,
            [(self.vbo, "3f 4f 3f", "position", "colors", "translation")],
        )

    # -------------------------------------------------------------
    # UPDATE LINE ENDPOINTS
    # -------------------------------------------------------------
    def set_points(self, p0, p1) -> None:
        self.p0[:] = p0
        self.p1[:] = p1
        self._build_buffers()

    def set_point0(self, p) -> None:
        self.p0[:] = p
        self._build_buffers()

    def set_point1(self, p) -> None:
        self.p1[:] = p
        self._build_buffers()

    # -------------------------------------------------------------
    # MOVE ENDPOINTS RELATIVE
    # -------------------------------------------------------------
    def move_points(self, dp0, dp1) -> None:
        self.p0 += np.array(dp0)
        self.p1 += np.array(dp1)
        self._build_buffers()

    def move_point0(self, dp) -> None:
        self.p0 += np.array(dp)
        self._build_buffers()

    def move_point1(self, dp) -> None:
        self.p1 += np.array(dp)
        self._build_buffers()

    # -------------------------------------------------------------
    # TRANSLATION (moves whole line)
    # -------------------------------------------------------------
    def set_translation(self, t) -> None:
        self.translation[:] = t
        self._build_buffers()

    def move(self, dx, dy, dz) -> None:
        self.translation += np.array([dx, dy, dz], dtype="f4")
        self._build_buffers()



    def draw(self, model: np.ndarray, camera: Camera) -> None:
        """All matrices MUST be numpy float32 4x4."""

        self.ctx.enable(mgl.BLEND)
        self.ctx.blend_func = mgl.SRC_ALPHA, mgl.ONE_MINUS_SRC_ALPHA
        
        # Skru av Culling så vi ser den fra baksiden
        self.ctx.disable(mgl.CULL_FACE)

        modeldata = cast(mgl.Uniform, self.program["model"])
        modeldata.write(model.astype('f4').tobytes())

        camera.apply_to_shader(self.program, "u_view", "u_projection")

        self.vao.render(mode=self.ctx.LINES)


class Circle3D:
    def __init__(self, ctx: mgl.Context, radius: float, program: mgl.Program, *, 
                 segments: int = 64, 
                 color: tuple = (255, 255, 255, 255), 
                 translation=(0,0,0)) -> None:
        self.ctx = ctx
        self.program = program
        self.radius = radius
        self.segments = segments
        self.translation = np.array(translation, dtype="f4")

        r, g, b, *a = color
        self.color = r/255, g/255, b/255, a[0]/255 if a else 1

        self._build_buffers()

    def _build_buffers(self) -> None:
        # Generer punkter langs sirkelen (i XY-planet som standard)
        angles = np.linspace(0, 2 * np.pi, self.segments, endpoint=False)
        
        vertices = []
        for angle in angles:
            x = np.cos(angle) * self.radius
            y = np.sin(angle) * self.radius
            z = 0.0
            # Legg til posisjon, farge og translasjon per vertex
            vertices.extend([x, y, z, *self.color, *self.translation])

        vertex_data = np.array(vertices, dtype="f4")

        self.vbo = self.ctx.buffer(vertex_data.tobytes())
        self.vao = self.ctx.vertex_array(
            self.program,
            [(self.vbo, "3f 4f 3f", "position", "colors", "translation")],
        )

    def set_radius(self, radius: float) -> None:
        self.radius = radius
        self._build_buffers()

    def set_translation(self, t) -> None:
        self.translation[:] = t
        self._build_buffers()

    def draw(self, model: np.ndarray, camera) -> None:
        self.ctx.enable(mgl.BLEND)
        self.ctx.blend_func = mgl.SRC_ALPHA, mgl.ONE_MINUS_SRC_ALPHA
        
        # Skru av Culling så vi ser den fra baksiden
        self.ctx.disable(mgl.CULL_FACE)

        if "model" in self.program:
            self.program["model"].write(model.astype('f4').tobytes())
        
        camera.apply_to_shader(self.program, "u_view", "u_projection")

        # Bruker LINE_LOOP for å lukke sirkelen automatisk
        self.vao.render(mode=mgl.LINE_LOOP)

class FilledCircle3D:
    def __init__(self, ctx: mgl.Context, radius: float, program: mgl.Program, *, 
                 segments: int = 64, 
                 color: tuple = (255, 255, 255, 255), 
                 translation=(0,0,0)) -> None:
        self.ctx = ctx
        self.program = program
        self.radius = radius
        self.segments = segments
        self.translation = np.array(translation, dtype="f4")

        r, g, b, *a = color
        self.color = (r/255, g/255, b/255, 0.1)

        self._build_buffers()

    def _build_buffers(self) -> None:
        vertices = []
        
        # 1. SENTRUMPUNKT (Første punkt i en Triangle Fan)
        # Posisjon (0,0,0), farge, translasjon
        vertices.extend([0.0, 0.0, 0.0, *self.color, *self.translation])

        # 2. PUNKTER LANGS OMKRETSEN
        # Vi bruker segments + 1 for å lukke sirkelen helt (endpoint=True)
        angles = np.linspace(0, 2 * np.pi, self.segments + 1, endpoint=True)
        
        for angle in angles:
            x = np.cos(angle) * self.radius
            y = np.sin(angle) * self.radius
            z = 0.0
            vertices.extend([x, y, z, *self.color, *self.translation])

        vertex_data = np.array(vertices, dtype="f4")

        self.vbo = self.ctx.buffer(vertex_data.tobytes())
        self.vao = self.ctx.vertex_array(
            self.program,
            [(self.vbo, "3f 4f 3f", "position", "colors", "translation")],
        )

    def draw(self, model: np.ndarray, camera) -> None:
        # VIKTIG: Aktiver blending RETT før tegning
        self.ctx.enable(mgl.BLEND)
        self.ctx.blend_func = mgl.SRC_ALPHA, mgl.ONE_MINUS_SRC_ALPHA
        
        # Skru av Culling så vi ser den fra baksiden
        self.ctx.disable(mgl.CULL_FACE)

        if "model" in self.program:
            self.program["model"].write(model.astype('f4').tobytes())
        
        camera.apply_to_shader(self.program, "u_view", "u_projection")

        self.vao.render(mode=mgl.TRIANGLE_FAN)


class Cylinder3D:
    def __init__(self, ctx: mgl.Context, program: mgl.Program, 
                 radius: float = 1.0, height: float = 2.0, 
                 segments: int = 64, color: tuple = (255, 255, 255, 255),
                 position=(0,0,0), rotation=(0,0,0)) -> None:
        self.ctx = ctx
        self.program = program
        self.radius = radius
        self.height = height
        self.segments = segments
        
        # Math state (f8 for precision)
        self.position = np.array(position, dtype="f8")
        self.rotation = np.array(rotation, dtype="f8") 
        self.scale = np.array((1, 1, 1), dtype="f8")
        
        r, g, b, *a = color
        self.color = r/255, g/255, b/255, a[0]/255 if a else 1
        
        # We maintain TWO matrices:
        # 1. For the GPU (Rotation only)
        self.gpu_model_matrix = np.eye(4, dtype="f8")
        # 2. For the Raycasting (Rotation + Translation)
        self.full_world_matrix = np.eye(4, dtype="f8")
        self.inv_full_matrix = np.eye(4, dtype="f8")
        
        self.update_matrix()
        self._build_buffers()

    def update_matrix(self):
        # 1. Full World Matrix (T * R * S)
        # Using the explicit compose_model provided in the previous turn
        self.full_world_matrix = compose_model(self.position, self.rotation, self.scale)
        
        # 2. Inverse Matrix for Raycasting
        self.inv_full_matrix = np.linalg.inv(self.full_world_matrix)
        
        # 3. GPU Matrix (No Translation for Hybrid Shader)
        self.gpu_model_matrix = compose_model((0,0,0), self.rotation, self.scale)

    def _build_buffers(self) -> None:
        vertices = []
        # We pack the ACTUAL position into the buffer here
        v_trans = [float(self.position[0]), float(self.position[1]), float(self.position[2])]
        
        angles = np.linspace(0, 2 * np.pi, self.segments + 1, endpoint=True)
        h2 = self.height / 2.0 # Centered Y-axis

        # --- BOTTOM CAP ---
        self.bottom_offset = 0
        vertices.extend([0.0, -h2, 0.0, *self.color, *v_trans])
        for a in angles:
            vertices.extend([np.cos(a)*self.radius, -h2, np.sin(a)*self.radius, *self.color, *v_trans])
        self.cap_verts = self.segments + 2

        # --- TOP CAP ---
        self.top_offset = len(vertices) // 10
        vertices.extend([0.0, h2, 0.0, *self.color, *v_trans])
        for a in angles:
            vertices.extend([np.cos(a)*self.radius, h2, np.sin(a)*self.radius, *self.color, *v_trans])

        # --- SIDES ---
        self.side_offset = len(vertices) // 10
        for a in angles:
            x, z = np.cos(a)*self.radius, np.sin(a)*self.radius
            vertices.extend([x, -h2, z, *self.color, *v_trans])
            vertices.extend([x, h2, z, *self.color, *v_trans])
        self.side_verts = (self.segments + 1) * 2

        # Convert to f4 for ModernGL
        vertex_data = np.array(vertices, dtype="f4")
        self.vbo = self.ctx.buffer(vertex_data.tobytes())
        self.vao = self.ctx.vertex_array(
            self.program,
            [(self.vbo, "3f 4f 3f", "position", "colors", "translation")],
        )

    def ray_intersection(self, ray_origin, ray_dir):
        # --- STEP 1: TRANSFORM RAY TO LOCAL ---
        # Origin gets [x, y, z, 1.0], Dir gets [x, y, z, 0.0]
        l_org = (self.inv_full_matrix @ np.append(ray_origin, 1.0))[:3]
        l_dir = (self.inv_full_matrix @ np.append(ray_dir, 0.0))[:3]
        
        # Re-normalize direction in local space
        l_dir_mag = np.linalg.norm(l_dir)
        if l_dir_mag < 1e-8: return None, None
        l_dir /= l_dir_mag

        hits = []
        h2 = self.height / 2.0  # Assumes geometry centered at 0

        # --- STEP 2: LOCAL MATH (Upright Cylinder) ---
        # Side Tube (x^2 + z^2 = r^2)
        a = l_dir[0]**2 + l_dir[2]**2
        if a > 1e-7:
            b = 2 * (l_org[0]*l_dir[0] + l_org[2]*l_dir[2])
            c = l_org[0]**2 + l_org[2]**2 - self.radius**2
            det = b**2 - 4*a*c
            if det >= 0:
                for t in [(-b - np.sqrt(det))/(2*a), (-b + np.sqrt(det))/(2*a)]:
                    if t > 0:
                        p = l_org + l_dir * t
                        if -h2 <= p[1] <= h2:
                            n = np.array([p[0], 0, p[2]])
                            hits.append((t, n / np.linalg.norm(n)))

        # Caps (y = +/- h2)
        for h, ny in [(-h2, -1.0), (h2, 1.0)]:
            if abs(l_dir[1]) > 1e-7:
                t = (h - l_org[1]) / l_dir[1]
                if t > 0:
                    p = l_org + l_dir * t
                    if p[0]**2 + p[2]**2 <= self.radius**2:
                        hits.append((t, np.array([0, ny, 0])))

        if not hits: return None, None
        hits.sort(key=lambda x: x[0])
        t_hit, l_norm = hits[0]
        l_hit_p = l_org + l_dir * t_hit

        # --- STEP 3: TRANSFORM RESULT TO WORLD ---
        w_hit = (self.full_world_matrix @ np.append(l_hit_p, 1.0))[:3]
        # Normals are directions, use W=0
        w_norm = (self.full_world_matrix @ np.append(l_norm, 0.0))[:3]
        
        return w_hit, w_norm / np.linalg.norm(w_norm)
    
    def is_inside(self, world_point: np.ndarray) -> bool:
        """Analytical check: Is the world_point inside the cylinder's volume?"""
        # 1. Transform world point to local space
        # Using [x, y, z, 1.0] to ensure translation is applied
        p_4d = self.inv_full_matrix @ np.append(world_point, 1.0)

        # perspective divide (usually 1.0, but good for safety)
        if abs(p_4d[3]) < 1e-8: return False
        local_p = p_4d[:3] / p_4d[3]

        # 2. Check bounds
        # Since we use h2 = self.height / 2.0 in _build_buffers:
        h2 = self.height / 2.0

        # Check Y (Height)
        if -h2 <= local_p[1] <= h2:
            # Check XZ (Radius)
            dist_sq = local_p[0]**2 + local_p[2]**2
            if dist_sq <= self.radius**2:
                return True

        return False

    def draw(self, camera) -> None:
        self.ctx.enable(mgl.BLEND)
        self.ctx.blend_func = mgl.SRC_ALPHA, mgl.ONE_MINUS_SRC_ALPHA
        self.ctx.disable(mgl.CULL_FACE)

        if "model" in self.program:
            # Send ONLY the rotation matrix to the GPU
            self.program["model"].write(self.gpu_model_matrix.astype('f4').tobytes())
        
        camera.apply_to_shader(self.program, "u_view", "u_projection")

        self.vao.render(mgl.TRIANGLE_FAN, vertices=self.cap_verts, first=self.bottom_offset)
        self.vao.render(mgl.TRIANGLE_FAN, vertices=self.cap_verts, first=self.top_offset)
        self.vao.render(mgl.TRIANGLE_STRIP, vertices=self.side_verts, first=self.side_offset)

