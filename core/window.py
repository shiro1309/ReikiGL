import pyglet

from typing import Callable, Optional
import engine

class AppWindow(pyglet.window.Window):
    
    def __init__(self, width: int=800, height: int=600, title: str="Pyglet OOP App", vsync: bool= False, *args, **kwargs) -> None:
        super().__init__(width=width, height=height, caption=title, vsync=vsync, *args, **kwargs)

        

        self.input: engine.Input.InputManager = engine.Input.InputManager()  # reference back to the applicatio
        self.keys = pyglet.window.key.KeyStateHandler()
        self.push_handlers(self.keys)
        
        self.batch = pyglet.graphics.Batch()


    # --------------- Screen Events ---------------
    def on_draw(self) -> None:
        self.clear()
    
    def on_deactivate(self) -> None:
        self.input.on_deactivate()
    
    def on_resize(self, width: int, height: int) -> None:
        """ change the size of the difrent scenes and the renderer so they get the info"""
        pass

    # --------------- Engine events ---------------
    def run(self) -> None:
        pyglet.app.run()

    def exit(self) -> None:
        pyglet.app.exit()

    def get_aspect_ratio(self) -> float:
        return max(self.width / self.height, 1e-6)
    
    # --------------- User Input ---------------
    # most of the User Input events are forwarded to the coresponding function in the InputManager
    def on_key_press(self, symbol: int, modifiers: int) -> None:
        self.input.on_key_press(symbol, modifiers)

    def on_key_release(self, symbol: int, modifiers: int) -> None:
        self.input.on_key_release(symbol, modifiers)

    # --------------- Mouse User Input ---------------
    def on_mouse_motion(self, x: int, y: int, dx: int, dy: int) -> None:
        self.input.on_mouse_motion(x, y, dx, dy)

    def on_mouse_press(self, x: int, y: int, button: int, modifiers: int) -> None:
        self.input.on_mouse_press(x, y, button, modifiers)

    def on_mouse_release(self, x: int, y: int, button: int, modifiers: int) -> None:
        self.input.on_mouse_release(x, y, button, modifiers)
    
    def on_mouse_drag(self, x: int, y: int, dx: int, dy: int, buttons: int, modifiers: int) -> None:
        self.input.on_mouse_drag(x, y, dx, dy, buttons, modifiers)

    def on_mouse_scroll(self, x: int, y: int, scroll_x: float, scroll_y: float) -> None:
        self.input.on_mouse_scroll(x, y, scroll_x, scroll_y)

    