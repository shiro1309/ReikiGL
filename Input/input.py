from __future__ import annotations
from typing import Dict, List
from dataclasses import dataclass, field
from pyglet.window import key, mouse

from typing import Dict, List, Set, Literal
from pyglet.window import mouse

class InputManager:
    
    """
    Translate raw key events into action states per frame:
        - down:     action held
        - pressed:  action was triggered this frame (edge on key-down)
        - released: action was realesed this frame (edge on key-up)

    Supports multiple action 'contexts', each with its own action->keys map.
    """
    
    
    def __init__(self) -> None:

        self.context: Dict[str, KeyBindings] = {}
        self.active: List[str] = []

        # KeyBoard Inputs
        self._down: Set[int] = set()
        self._pressed: Set[int] = set()
        self._released: Set[int] = set()

        # Mouse Inputs
        self.mouse_keys = {
            "left" : 1,
            "middle": 2,
            "right": 4,
            "back": 8,
            "forward": 16
        }

        self.mouse_down: Set[int] = set()
        self.mouse_pressed: Set[int] = set()
        self.mouse_released: Set[int] = set()
        self.mouse_state: Dict[str, Dict[str, bool]] = {}

        # Mouse Movement
        self.mouse_x: int = 0
        self.mouse_y: int = 0
        self.mouse_dx: int = 0
        self.mouse_dy: int = 0
        self.temp_mouse_dx: int = 0
        self.temp_mouse_dy: int = 0

        self.mouse_scroll_dx = 0
        self.temp_mouse_scroll_dx = 0
        self.mouse_scroll_dy = 0
        self.temp_mouse_scroll_dy = 0
        self.scrolling = False
        self.scroll_timer = 0

        self.mouse_moving = False
        self.mouse_moving_timer = 0

        # Derived action state (logical), rebuilt every update()
        self.state: Dict[str, Dict[str, bool]] = {}

    # -------------- Context management --------------
    def add_context(self, name: str, kb: KeyBindings, activate: bool = False) -> None:
        self.context[name] = kb
        if activate and name not in self.active:
            self.active.append(name)

    def activate(self, name: str) -> None:
        if name in self.context and name not in self.active:
            self.active.append(name)

    def deactivate(self, name: str) -> None:
        if name in self.active:
            self.active.remove(name)

    # -------------- Per-frame update --------------
    def update(self) -> None:
        self.state = organising_key_inputs(self)
        self.mouse_state = organising_mouse_key_inputs(self)

        # one-frame edges are cleared here
        self._pressed.clear()
        self._released.clear()
        self.mouse_pressed.clear()
        self.mouse_released.clear()
        self.mouse_dx = 0
        self.mouse_dy = 0
        self.mouse_dx = self.temp_mouse_dx
        self.mouse_dy = self.temp_mouse_dy
        self.temp_mouse_dx = 0
        self.temp_mouse_dy = 0
        self.mouse_scroll_dx = self.temp_mouse_scroll_dx
        self.mouse_scroll_dy = self.temp_mouse_scroll_dy
        self.temp_mouse_scroll_dx = 0
        self.temp_mouse_scroll_dy = 0

        self.mouse_moving_timer = max(self.mouse_moving_timer-1, 0)
        if self.mouse_moving_timer == 0:
            self.mouse_moving = False

        self.scroll_timer = max(self.scroll_timer-1, 0)
        if self.scroll_timer == 0:
            self.scrolling = False

    # -------------- Event entry points (call from your window) --------------
    def on_key_press(self, symbol: int, modifiers: int) -> None:
        if symbol in self._down:
            return  # ignore OS key repeat

        self._down.add(symbol)
        self._pressed.add(symbol)

    def on_key_release(self, symbol: int, modifiers: int) -> None:
        self._down.discard(symbol)
        self._released.add(symbol)
    
    def on_mouse_motion(self, x: int, y: int, dx: int, dy: int) -> None:
        self.mouse_x = x
        self.mouse_y = y
        self.temp_mouse_dx += dx
        self.temp_mouse_dy += dy
        self.mouse_moving = True
        self.mouse_moving_timer = 2

    def on_mouse_drag(self, x: int, y: int, dx: int, dy: int, buttons: int, modifiers: int) -> None:
        self.mouse_x = x
        self.mouse_y = y
        self.temp_mouse_dx += dx
        self.temp_mouse_dy += dy
        self.mouse_moving = True
        self.mouse_moving_timer = 2
        for btn in [mouse.LEFT, mouse.RIGHT, mouse.MIDDLE]:
            if buttons & btn:
                self.mouse_down.add(btn)
            else:
                self.mouse_down.discard(btn)

    def on_mouse_press(self, x: int, y: int, button: int, modifiers: int) -> None:
        if button not in self.mouse_down:
            self.mouse_pressed.add(button)
        self.mouse_down.add(button)

    def on_mouse_release(self, x: int, y: int, button: int, modifiers: int) -> None:
        self.mouse_down.discard(button)
        self.mouse_released.add(button)

    def on_mouse_scroll(self, x: int, y: int, scroll_x: float, scroll_y: float) -> None:
        self.mouse_x = x
        self.mouse_y = y
        self.temp_mouse_scroll_dx = scroll_x
        self.temp_mouse_scroll_dy = scroll_y
        self.scrolling = True
        self.scroll_timer = 2


    # -------------- Check key state & queries functions --------------
    def is_down(self, action: str) -> bool:
        return self.state.get(action, {}).get("down", False)

    def is_pressed(self, action: str) -> bool:
        return self.state.get(action, {}).get("pressed", False)

    def is_released(self, action: str) -> bool:
        return self.state.get(action, {}).get("released", False)

    def is_mouse_down(self, button: str) -> bool:
        return self.mouse_state.get(button, {}).get("down", False)
    
    def is_mouse_pressed(self, button: str) -> bool:
        return self.mouse_state.get(button, {}).get("pressed", False)

    def is_mouse_released(self, button: str) -> bool:
        return self.mouse_state.get(button, {}).get("released", False)
    
    def is_mouse_drag(self, button: Literal["left", "middle", "right", "back", "forward"]) -> bool:
        return self.is_mouse_down(button) and self.mouse_moving

    def on_deactivate(self) -> None:
        """Clear pressed states when window loses focus."""
        self._down.clear()
        self._pressed.clear()
        self._released.clear()
        self.mouse_down.clear()
        self.mouse_pressed.clear()
        self.mouse_released.clear()


@dataclass
class KeyBindings:
    """Map game actions to one or more physical keys"""
    mapping : Dict[str, List[int]] = field(default_factory=dict)

def organising_mouse_key_inputs(context: InputManager) -> Dict[str, Dict[str, bool]]:
    """
    Converts the mouse_down, mouse_pressed and mouse_released into a dict for faster accessesing and searching
    """
    mouse_state: Dict[str, Dict[str, bool]] = {}

    for mouse_action, key_id in context.mouse_keys.items():
        mt = mouse_state.get(mouse_action, {"down": False, "pressed": False, "released": False})

        if key_id in context.mouse_down: mt["down"] = True
        if key_id in context.mouse_pressed: mt["pressed"] = True
        if key_id in context.mouse_released: mt["released"] = True

        mouse_state[mouse_action] = mt
    return mouse_state

def organising_key_inputs(context: InputManager) -> Dict[str, Dict[str, bool]]:
    """
    Converts the _down, _pressed and _released into a dict for faster accessesing and searching
    """
    state: Dict[str, Dict[str, bool]] = {}

    for active in context.active:
        kb = context.context.get(active)

        if not kb:
            continue

        for action, keys in kb.mapping.items():
            # set all to false then do a check to confirm
            st = state.get(action, {"down": False, "pressed": False, "released": False})

            if any(_key in context._down for _key in keys): st["down"] = True
            if any(_key in context._pressed for _key in keys): st["pressed"] = True
            if any(_key in context._released for _key in keys): st["released"] = True

            # put the state back into the st
            state[action] = st
    return state

def symbols_from_strings(names: list[str]) -> list[int]:
    """
    Convert strings like ["A","LEFT","ESCAPE"] into pyglet.window.key constants.
    Unknown names are ignored, so you can validate/log if desired.
    """
    table = {n: getattr(key, n) for n in dir(key) if n.isupper()}  # key.A, key.LEFT, ...
    return [table[n] for n in names if n in table]