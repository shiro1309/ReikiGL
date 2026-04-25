import numpy as np
from typing import cast
import moderngl as mgl
from .camera import Camera, BaseCamera
from ..shader import import_shader
from dataclasses import dataclass
from ..math import transform
from abc import ABC, abstractmethod


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



    def draw(self, model: np.ndarray, camera: BaseCamera) -> None:
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
            model_data = cast(mgl.Uniform, self.program["model"])
            model_data.write(model.astype('f4').tobytes())
        
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
            model_data = cast(mgl.Uniform, self.program["model"])
            model_data.write(model.astype('f4').tobytes())
        
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

    def update_matrix(self) -> None:
        # 1. Full World Matrix (T * R * S)
        # Using the explicit compose_model provided in the previous turn
        self.full_world_matrix = transform.compose_model(self.position, self.rotation, self.scale)
        
        # 2. Inverse Matrix for Raycasting
        self.inv_full_matrix = np.linalg.inv(self.full_world_matrix)
        
        # 3. GPU Matrix (No Translation for Hybrid Shader)
        self.gpu_model_matrix = transform.compose_model((0,0,0), self.rotation, self.scale)

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
            model_data = cast(mgl.Uniform, self.program["model"])
            model_data.write(self.gpu_model_matrix.astype('f4').tobytes())
        
        camera.apply_to_shader(self.program, "u_view", "u_projection")

        self.vao.render(mgl.TRIANGLE_FAN, vertices=self.cap_verts, first=self.bottom_offset)
        self.vao.render(mgl.TRIANGLE_FAN, vertices=self.cap_verts, first=self.top_offset)
        self.vao.render(mgl.TRIANGLE_STRIP, vertices=self.side_verts, first=self.side_offset)



################################################################
#
#                         NEW SHAPES
#
################################################################

from abc import ABC, abstractmethod
import numpy as np
import moderngl as mgl
from typing import Tuple, Union, Optional
from .batch import Batch3D
from ..math import transform

from abc import ABC, abstractmethod
from typing import Tuple, List, Optional, Union
import numpy as np
import numpy.typing as npt
import moderngl as mgl
from icosphere import icosphere

class ShapeBase(ABC):
    def __init__(
        self, 
        ctx: mgl.Context, 
        program: mgl.Program, 
        batch: Optional[Batch3D] = None,
        vertCol: bool = False
    ):
        self._ctx: mgl.Context = ctx
        self._program: mgl.Program = program
        self._batch: Optional[Batch3D] = batch
        
        # Transformation State
        self._x: float = 0.0
        self._y: float = 0.0
        self._z: float = 0.0
        self._rotation: float = 0.0
        self._rgba: np.ndarray = np.array([255, 255, 255, 255], dtype="f4")
        
        # The Model Matrix (Always 4x4 float64 or float32)
        self.matrix: npt.NDArray[np.float64] = np.eye(4, dtype=np.float64)

        self.vertCol = vertCol

        #self.color = self._rgba
        
        # GPU Resource Handles
        self.mesh_id: Optional[str] = None
        self.vao: Optional[mgl.VertexArray] = None
        self.vbo: Optional[mgl.Buffer] = None
        self.ibo: Optional[mgl.Buffer] = None

    @abstractmethod
    def _create_vertices(self) -> None:
        """Each child must implement this to define its geometry."""
        pass

    def _setup_standalone(self, vertices: np.ndarray, indices: List[int]) -> None:
        """
        Creates standalone GPU buffers. 
        Matches the '3f 3f' layout (Position, Normal).
        """
        vbo = self._ctx.buffer(np.array(vertices, dtype='f4'))
        ibo = self._ctx.buffer(np.array(indices, dtype='i4'))
        
        # Link the VBO to the 'location' indices in the shader
        # 3f (in_pos) + 3f (in_norm)
        if not self.vertCol:
            self.vao = self._ctx.vertex_array(
                self._program, 
                [(vbo, '3f 2x4 3f', 'in_pos', 'in_norm')], 
                ibo
            )
        else:
            self.vao = self._ctx.vertex_array(
                self._program, 
                [(vbo, '3f 2x4 3f 4f', 'in_pos', 'in_norm', 'in_color')], 
                ibo
            )

    def _update_translation(self) -> None:
        """Uses the library's compose_model to sync the matrix."""
        # Ensure your compose_model returns a 4x4 numpy array
        self.matrix = transform.compose_model(
            translation=(self._x, self._y, self._z),
            euler=(0, 0, np.radians(self._rotation)), 
            scale_val=(1.0, 1.0, 1.0)
        )
        
        if self._batch and self.mesh_id is not None:
            self._batch.set_model(str(self.mesh_id), self.matrix)

    def _update_color(self) -> None:
        if self._batch and self.mesh_id is not None:
            norm_color = np.array(self._rgba, dtype='f4')
            self._batch.set_mesh_color(self.mesh_id, norm_color)

    @property
    def color(self) -> np.ndarray:
        return self._rgba

    @color.setter
    def color(self, value: Tuple[int, int, int, int]):
        self._rgba = np.array(value, dtype=np.float32)
        self._update_color()

    def draw(self, camera: BaseCamera):
        if not self.vao:
            return

        # 1. Update Matrix (Assuming compose_model is available)
        self.matrix = transform.compose_model(
            translation=(self._x, self._y, self._z),
            euler=(0, 0, 0),
            scale_val=(1, 1, 1)
        )

        # 2. Upload Uniforms
        #self.program['projection'].write(camera.get_projection_matrix().T.astype('f4'))
        #self.program['view'].write(camera.get_view_matrix().T.astype('f4'))
        camera.apply_to_shader(self._program, "view", "projection")
        self._program['u_model'].write(self.matrix.T.astype('f4').copy())
        if not self.vertCol:
            norm_color = np.array(self._rgba, dtype='f4') / 255.0
            self._program['u_color'].write(norm_color)

        # 3. Render
        self.vao.render(mgl.TRIANGLES)

    @property
    def z(self) -> float: return self._z
    @z.setter
    def z(self, value) -> None:
        self._z = value
        self._update_translation()

    def move_z(self, value) -> None:
        self._z += value
        self._update_translation()



class Rectangle(ShapeBase):
    def __init__(self, ctx, program, x, y, width, height, batch=None) -> None:
        super().__init__(ctx, program, batch)
        # We store coordinates, but the actual 'positioning' 
        # should ideally happen via the Model Matrix.
        self.width, self.height = width, height
        
        self._create_vertices()
        
        # Set initial position via matrix
        self.matrix = np.eye(4, dtype='f4')
        # Translate to x, y
        self.matrix[3, :2] = [x, y] 
        self._update_translation()

    def _create_vertices(self) -> None:
        w, h = self.width, self.height
        
        # Format: x, y, z,  uv_x, uv_y,  nx, ny, nz (8 floats per vertex)
        # Normals are all 0, 0, 1 (pointing straight out of the screen)
        vertices = [
            # pos          # uv    # normal
            0, 0, 0,       0, 0,   0, 0, 1,  # Bottom Left
            w, 0, 0,       1, 0,   0, 0, 1,  # Bottom Right
            0, h, 0,       0, 1,   0, 0, 1,  # Top Left
            w, h, 0,       1, 1,   0, 0, 1,  # Top Right
        ]
        
        indices = [0, 1, 2, 1, 3, 2]

        if self._batch:
            # Register with 8-float stride compatibility
            self.mesh_id = self._batch.add_mesh(vertices, indices)
        
        self._setup_standalone(vertices, indices)

class Rectangle3D(ShapeBase):
    def __init__(self, ctx, program, x, y, z, width, height, batch=None) -> None:
        super().__init__(ctx, program, batch)
        # We store coordinates, but the actual 'positioning' 
        # should ideally happen via the Model Matrix.
        self.width, self.height = width, height
        
        self._create_vertices()
        
        # Set initial position via matrix
        self.matrix = np.eye(4, dtype='f4')
        # Translate to x, y
        self.matrix[3, :3] = [x, y, z] 
        self._update_translation()

    def _create_vertices(self) -> None:
        w, h = self.width, self.height
        
        # Format: x, y, z,  uv_x, uv_y,  nx, ny, nz (8 floats per vertex)
        # Normals are all 0, 0, 1 (pointing straight out of the screen)
        vertices = [
            # pos          # uv    # normal
            0, 0, 0,       0, 0,   0, -1, 0,  # Bottom Left
            w, 0, 0,       1, 0,   0, -1, 0,  # Bottom Right
            0, 0, h,       0, 1,   0, -1, 0,  # Top Left
            w, 0, h,       1, 1,   0, -1, 0,  # Top Right
        ]
        
        indices = [0, 1, 2, 1, 3, 2]

        if self._batch:
            # Register with 8-float stride compatibility
            self.mesh_id = self._batch.add_mesh(vertices, indices)
        
        self._setup_standalone(vertices, indices)

import math

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


class Sphere(ShapeBase):
    def __init__(self, ctx, program, x, y, z, radius, subdivision_frequency: int = 4, color=(255, 255, 255, 255), batch=None, vertCol=False) -> None:
        super().__init__(ctx, program, batch, vertCol)
        self._x, self._y, self._z = x, y, z
        self._radius = radius
        self._rgba = color
        self.subdivision_frequency = subdivision_frequency
        self._create_vertices()

    def _create_vertices(self) -> None:
        # 1. Generate (pos, norm) only for a simple 3f 3f layout
        verts, indices = create_icosphere_fast(self._radius, self.subdivision_frequency)
        
        if self._batch:
            self.mesh_id = self._batch.add_mesh(verts, indices)
            self._update_translation()
            # Batch color update logic here
        self._setup_standalone(verts, indices)
        self._update_translation()

class SphereC(ShapeBase):
    def __init__(self, ctx, program, x, y, z, radius, subdivision_frequency: int = 4, color=(255, 255, 255, 255), batch=None, vertCol=False) -> None:
        super().__init__(ctx, program, batch, vertCol)
        self._x, self._y, self._z = x, y, z
        self._radius = radius
        self._rgba = color
        self.subdivision_frequency = subdivision_frequency
        self._create_vertices()

    def _create_vertices(self) -> None:
        # 1. Generate (pos, norm) only for a simple 3f 3f layout
        verts, indices = create_icosphere_fast_color(self._radius, self.subdivision_frequency)
        
        if self._batch:
            self.mesh_id = self._batch.add_mesh(verts, indices)
            self._update_translation()
            # Batch color update logic here
        self._setup_standalone(verts, indices)
        self._update_translation()



    