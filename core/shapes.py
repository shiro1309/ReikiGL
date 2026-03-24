import numpy as np
from typing import cast
import moderngl as mgl
from .camera import Camera, BaseCamera
from ..shader import import_shader
from dataclasses import dataclass

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

