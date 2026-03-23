from enum import IntFlag, auto

class ReikiFlags(IntFlag):
    NONE       = 0
    DEPTH_TEST = auto()
    CULL_FACE  = auto()
    BLEND      = auto()