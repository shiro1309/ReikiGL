import moderngl, numpy as np
from typing import Tuple

class Mesh:

    """
    A GPU-resident drawable mesh consisting of a VBO, IBO, and VAO.

    This class packages together all ModernGL objects required to render a
    triangle mesh: a vertex buffer (VBO), an index buffer (IBO), and a
    vertex array object (VAO). It is designed to work with interleaved
    vertex data and a user-supplied vertex attribute layout.

    Parameters
    ----------
    ctx : moderngl.Context
        The active ModernGL context used to create buffers and the VAO.
    vao_data : numpy.ndarray
        A 2D NumPy array of shape (N, M) containing interleaved vertex
        attributes. Common layouts include:
            - [px, py, pz, u, v, nx, ny, nz]
            - [px, py, pz, nx, ny, nz]
        The array must be float32 (`dtype='f4'`).
    indices : numpy.ndarray
        A 1D NumPy array of integer indices (`dtype='i4'`) defining how
        vertices are assembled into triangles. Typically length is a
        multiple of 3 for TRIANGLES.
    fmt : str
        A ModernGL format string describing how vertex data is laid out.
        Examples:
            '3f 2f 3f'   → position, uv, normal
            '3f 2x4 3f' → skip UVs, only read pos + normal
            '3f 2x4 3x4' → only position (skip UV + normal)
        Format blocks must match the attribute names given in `attrs`.
    attrs : Tuple[str, ...]
        A tuple of shader attribute names, one per non-skip block in `fmt`.
        For example:
            fmt='3f 2x4 3f'
            attrs=('in_pos', 'in_norm')
        Attribute names must match those declared in the vertex shader and
        must be *used* in the shader, otherwise ModernGL may optimize
        them out and raise `KeyError`.
    prog : moderngl.Program
        The shader program that this mesh will bind attributes for.
        The VAO is created specifically for this program.

    Attributes
    ----------
    vbo : moderngl.Buffer
        GPU buffer holding vertex data.
    ibo : moderngl.Buffer
        GPU buffer holding triangle index data.
    vao : moderngl.VertexArray
        Assembled VAO that binds the VBO to shader attributes.
    index_count : int
        Number of indices stored in `ibo`, typically used by render code.

    Notes
    -----
    - The same VBO can be shared between multiple programs **only** if a
      separate VAO is created per program, since VAOs encode attribute
      bindings.
    - The vertex format (`fmt`) must match the interleaved structure of
      `vao_data`. Skipping fields with `x` (e.g., `2x4` to skip 2 floats)
      allows reusing a single VBO for multiple shaders.
    - This class does not perform rendering itself; callers should use
      `mesh.vao.render()`.

    Examples
    --------
    Creating a mesh with position + normal attributes::

        vao_data = np.array([...], dtype='f4')
        indices  = np.array([...], dtype='i4')

        mesh = Mesh(
            ctx,
            vao_data,
            indices,
            fmt='3f 2x4 3f',
            attrs=('in_pos', 'in_norm'),
            prog=shader_program
        )

    Rendering::

        shader_program['u_model'].write(model_matrix)
        mesh.vao.render()
    """

    def __init__(self, ctx: moderngl.Context, vao_data: np.ndarray, indices: np.ndarray, fmt: str, attrs: Tuple, prog: moderngl.Program) -> None:
        self.vbo = ctx.buffer(vao_data.tobytes())
        self.ibo = ctx.buffer(indices.tobytes())
        self.vao = ctx.vertex_array(
            prog,
            [(self.vbo, fmt, *attrs)],
            self.ibo
        )
        self.index_count = len(indices)