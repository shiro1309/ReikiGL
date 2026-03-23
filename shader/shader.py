from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

import moderngl


def import_shader(
    ctx: moderngl.Context,
    shader_name: str,
    *,
    shader_dir: Optional[Path] = None,
    defines: Optional[Dict[str, str]] = None,
) -> moderngl.Program:
    """
    Load, compile, and link a pair of GLSL shaders (<name>.vert + <name>.frag)
    into a ModernGL Program.

    Parameters
    ----------
    ctx : moderngl.Context
        The active ModernGL context to compile/link the program in.
    shader_name : str
        Base name of the shader files (without extension). For example,
        if `shader_name='basic'`, this function will look for:
            - <shader_dir>/basic.vert
            - <shader_dir>/basic.frag
    shader_dir : Optional[pathlib.Path], keyword-only
        Directory containing the shader files. Defaults to a `shaders/`
        folder located next to the *calling* file.
    defines : Optional[Dict[str, str]], keyword-only
        Optional `#define` values to prepend to both vertex and fragment
        shader sources. Example:
            defines={"USE_FOG": "1", "MAX_LIGHTS": "4"}

    Returns
    -------
    moderngl.Program
        The compiled and linked shader program.

    Raises
    ------
    FileNotFoundError
        If either the vertex or fragment shader file does not exist.
    moderngl.Error
        If shader compilation or program linking fails. The exception
        message will include the underlying GLSL error log.

    Notes
    -----
    - This function assumes standard GLSL (`#version` lines should be present
      in your shader sources).
    - If you're building matrices with NumPy, remember OpenGL expects column-major
      layout when uploading to uniforms (you can send `matrix.T.tobytes()`).
    """
    # Resolve default shader directory to "<current_file>/shaders"
    if shader_dir is None:
        # __file__ points at the module where this function lives.
        # Use .parent / 'shaders' to find sibling "shaders" folder.
        shader_dir = Path(__file__).parent / "shaders"

    vertex_path = shader_dir / f"{shader_name}.vert"
    fragment_path = shader_dir / f"{shader_name}.frag"

    if not vertex_path.is_file():
        raise FileNotFoundError(f"Vertex shader not found: {vertex_path}")
    if not fragment_path.is_file():
        raise FileNotFoundError(f"Fragment shader not found: {fragment_path}")

    vertex_source = vertex_path.read_text(encoding="utf-8")
    fragment_source = fragment_path.read_text(encoding="utf-8")

    # Optionally prepend #defines for compile-time toggles
    if defines:
        prefix = "\n".join(
            [f"#define {k} {v}" if v is not None else f"#define {k}" for k, v in defines.items()]
        )
        prefix += "\n"
        vertex_source = prefix + vertex_source
        fragment_source = prefix + fragment_source

    # Compile & link; ModernGL will raise moderngl.Error on failure,
    # which includes the full GLSL error log.
    program = ctx.program(
        vertex_shader=vertex_source,
        fragment_shader=fragment_source,
    )
    return program