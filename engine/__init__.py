
# engine/__init__.py
"""
engine package

Usage examples:
    from engine.shader import Mesh
    from engine.math import Transform
"""

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
