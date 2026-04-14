from pyglet.window import key, mouse
from .input import (
    KeyBindings, 
    symbols_from_strings, 
    organising_key_inputs, 
    organising_mouse_key_inputs, 
    InputManager
)

# This makes them available when you import your input folder
__all__ = [
    "key", 
    "mouse", 
    "KeyBindings", 
    "symbols_from_strings", 
    "organising_key_inputs", 
    "organising_mouse_key_inputs", 
    "InputManager"
]