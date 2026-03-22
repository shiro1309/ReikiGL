import pyglet
from pyglet.gl import GL_ONE_MINUS_SRC_ALPHA, GL_SRC_ALPHA
from pyglet.graphics import Batch, Group
from pyglet.graphics.shader import ShaderProgram
import moderngl as mgl
from typing import Tuple


class Cube(pyglet.shapes.ShapeBase):
    def __init__(self, 
        x: float, y: float, z: float,
        side_length: float,
        color: Tuple[int, int, int, int] | Tuple[int, int, int] = (255, 255, 255, 255),
        *,
        vertex_count: int = 36, 
        blend_src: int = mgl.SRC_ALPHA,
        blend_dest: int = mgl.ONE_MINUS_SRC_ALPHA, 
        batch: Batch | None = None, 
        group: Group | None = None, 
        program: ShaderProgram | None = None
    ) -> None:
        super().__init__(vertex_count, blend_src, blend_dest, batch, group, program)
        self._x = x
        self._y = y
        self._z = z
        self._width = side_length
        self._height = side_length
        self._depth = side_length
        self._rotation = 0
        r, g, b, *a = color
        self._rgba = r, g, b, a[0] if a else 255