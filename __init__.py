
# engine/__init__.py
"""
engine package

Usage examples:
    from engine.shader import Mesh
    from engine.math import Transform
"""
from .core.constants import ReikiFlags
DEPTH_TEST = ReikiFlags.DEPTH_TEST
CULL_FACE = ReikiFlags.CULL_FACE
BLEND = ReikiFlags.BLEND
NONE = ReikiFlags.NONE

# Re-export subpackages so `engine.shader` works.
#from . import utils
from . import shader
from . import core
from . import imports
from . import math
from . import Input
from . import Shapes
from . import utils

__all__ = ["shader", "core", "imports", "math", "Input", "Shapes", "utils"]
