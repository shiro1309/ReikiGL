import ReikiGL
import pyglet

class Application(ReikiGL.core.AppWindow):
    def __init__(self, width, height, title) -> None:
        super().__init__(width=width, height=height, title=title, vsync=False, flags=ReikiGL.DEPTH_TEST | ReikiGL.CULL_FACE)
        pyglet.clock.schedule_interval(self.update, 1 / 60)

    def on_draw(self) -> None:
        self.clear()

    def update(self, dt) -> None:
        self.input.update() # update the key states

app = ReikiGL.core.AppWindow()
app.run()