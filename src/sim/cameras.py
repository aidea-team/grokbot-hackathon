"""The dog's cameras: ONE registry shared by the simulator, the real Go1 and the model's prompt.

The chat has the same interface in mock and real mode: the same three cameras, with the same names, the same
labels and the same description given to the model. Only the source of the pixels changes.

`n` is the Go1's own camera number (ws://<dog>/cam<n>, see src/dog/cams.py): cam1 front, cam2 down, cam4 side
(cam3 is black and cam5 unavailable, checked on site 4/11). `mj` is the camera name inside the MuJoCo model.

TO VERIFY ON THE REAL DOG: which side cam4 looks at. The simulator and the prompt assume the LEFT side (+y); if the
real cam4 looks right, fix `where` of "side" (and the pose in scene._add_cameras) and nothing else.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Camera:
    name: str   # id used by capture(camera=...) and by the web API
    n: int      # real Go1 camera number
    mj: str     # camera name in the MuJoCo model
    label: str  # short label in the UI
    where: str  # placement, as told to the model


CAMERAS: tuple[Camera, ...] = (
    Camera("front", 1, "head", "davanti",
           "sul muso, guarda dritto davanti a te (lungo +x, la direzione in cui cammini)"),
    Camera("down", 2, "down", "basso",
           "sotto il mento, inclinata verso il basso: vede il pavimento subito davanti alle zampe anteriori "
           "(ostacoli bassi, gradini, bordi, oggetti da superare)"),
    Camera("side", 4, "side", "lato",
           "sul fianco sinistro, guarda di lato verso sinistra (+y), a 90° rispetto alla direzione di marcia: "
           "serve per ciò che hai accanto e per controllare da che parte girare"),
)
BY_NAME = {c.name: c for c in CAMERAS}
ALIASES = {"head": "front"}  # legacy default of capture()


def get(name: str) -> Camera:
    return BY_NAME[ALIASES.get(name, name)]


def prompt_block() -> str:
    """The camera paragraph of the system prompt (same text in sim and real)."""
    lines = [f"- cam{c.n} «{c.label}» ({c.name}): {c.where}." for c in CAMERAS]
    return ("Hai 3 telecamere, tutte montate sul tuo corpo. A ogni passo ricevi un'immagine per ciascuna, "
            "ognuna con la sua etichetta:\n" + "\n".join(lines) +
            "\nUsa la giusta telecamera per la domanda: davanti per navigare e riconoscere il bersaglio, basso "
            "per ciò che hai ai piedi, lato per ciò che hai accanto. Se una telecamera risulta non disponibile "
            "lo dice l'etichetta: lavora con le altre.")
