# ReikiGL

En lettvektig Python-pakke for [Sett inn kort beskrivelse, f.eks. OpenGL-håndtering].

## Installasjon som Git-submodul

For å bruke ReikiGL i et annet prosjekt, anbefales det å legge den til som en submodul. Dette holder koden din oppdatert og separert fra hovedprosjektet.

1. Legg til submodulen:
```bash
git submodule add https://github.com/shiro1309/ReikiGL.git
```

2. Initialiser (for nye kloner):
```bash
git submodule update --init --recursive
```

## Brukseksempel

Når submodulen er lagt til (og __init__.py ligger i rota av ReikiGL-mappen), kan du importere den direkte i Python:

```python
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
```

## Prosjektstruktur

For at importen skal fungere sømløst, er prosjektet organisert slik:
- __init__.py: Eksponerer pakkens funksjonalitet.
- main.py: Kjernefunksjonalitet.
- .gitmodules: Konfigurasjon for Git.