"""The dog's world: Menagerie's Go1 scene plus props (hurdle, hoop, tunnel, slalom, finish, shapes).

SIMULATION ONLY. Everything here is simulated by MuJoCo's rigid-body physics (DogSim calls mj_step):
- static props (hurdle, hoop, tunnel, finish) are fixed to the world;
- light props (ball, cube, column, tower, egg, pouf, slalom poles) are free bodies with a mass: the dog can
  push them, knock them over and make them roll.
Geoms are named "<label>_<n>", so a contact tells which object was touched.
LANDMARKS is the single source of truth for what the chat agent can be told about the world (describe()).

The dog starts at (0, 0) facing +x, y is to its left.
"""
from __future__ import annotations

import itertools
import math

import mujoco
import numpy as np

from models import model_path

BOX, SPHERE, CYL, ELLIPSOID = (
    mujoco.mjtGeom.mjGEOM_BOX, mujoco.mjtGeom.mjGEOM_SPHERE, mujoco.mjtGeom.mjGEOM_CYLINDER,
    mujoco.mjtGeom.mjGEOM_ELLIPSOID,
)

ORANGE = (0.95, 0.45, 0.10, 1.0)
RED = (0.85, 0.15, 0.15, 1.0)
BLUE = (0.20, 0.40, 0.90, 1.0)
GREEN = (0.20, 0.70, 0.35, 1.0)
YELLOW = (0.95, 0.80, 0.15, 1.0)
PURPLE = (0.55, 0.30, 0.75, 1.0)
WHITE = (0.92, 0.92, 0.92, 1.0)
GLASS = (0.30, 0.80, 0.90, 0.28)

# (description for the agent, x, y)
LANDMARKS: list[tuple[str, float, float]] = [
    ("ostacolo basso: due paletti con una barra a 0,45 m di quota (si passa sotto o ci si salta sopra)", 1.5, 0.0),
    ("cerchio verticale arancione, raggio 0,55 m, centro a 0,75 m di quota, con un sostegno a terra al centro "
     "(ci si salta attraverso)", 3.0, 0.0),
    ("tunnel trasparente lungo 2,4 m da x=4,5 a x=6,9, largo 0,8 m e alto 0,65 m (si attraversa camminando lungo y=0)",
     5.7, 0.0),
    ("slalom: 4 paletti rossi leggeri (si ribaltano se urtati) a x=8,5 (y=+0,45), x=10 (y=-0,45), "
     "x=11,5 (y=+0,45), x=13 (y=-0,45)", 10.75, 0.0),
    ("traguardo: arco a scacchi tra y=-0,8 e y=+0,8 (alto 1,1 m)", 15.0, 0.0),
    ("cubo blu (lato 0,5 m, leggero: si può spingere)", 2.5, 2.2),
    ("palla gialla (raggio 0,35 m, rotola)", 1.5, -2.0),
    ("colonna viola alta 1,2 m (si può spingere)", -2.0, 1.5),
    ("torre di 3 cubi (verde, arancione, rosso), si può far crollare", -1.5, -2.0),
    ("uovo verde (ellissoide)", 6.0, -2.6),
    ("cilindro bianco basso (pouf)", 7.5, 2.4),
]


def describe() -> str:
    return "\n".join(f"- {d}: centro in ({x:g}, {y:g})" for d, x, y in LANDMARKS)


_ids = itertools.count(1)


def _geom(parent, kind, size, pos, rgba, label, quat=None, mass=None):
    s = list(size) + [0.0] * (3 - len(size))
    g = parent.add_geom(name=f"{label}_{next(_ids)}", type=kind, size=s, pos=list(pos), rgba=list(rgba))
    if quat is not None:
        g.quat = list(quat)
    if mass is not None:
        g.mass = mass
    return g


def _free_body(spec, label, pos):
    """A prop that physics can move: its own body with a free joint."""
    body = spec.worldbody.add_body(name=f"{label}_body_{next(_ids)}", pos=list(pos))
    body.add_freejoint()
    return body


def _rot_x(angle: float) -> list[float]:
    return [math.cos(angle / 2), math.sin(angle / 2), 0.0, 0.0]


def _hurdle(spec, x):
    w = spec.worldbody
    for y in (-0.6, 0.6):
        _geom(w, CYL, (0.03, 0.25), (x, y, 0.25), WHITE, "hurdle")
    _geom(w, CYL, (0.025, 0.6), (x, 0.0, 0.45), RED, "hurdle", quat=_rot_x(math.pi / 2))


def _hoop(spec, x, zc=0.75, radius=0.55, n=20):
    w = spec.worldbody
    seg = radius * math.sin(math.pi / n) * 1.08
    for i in range(n):
        th = 2 * math.pi * i / n
        _geom(w, BOX, (0.03, seg, 0.03), (x, radius * math.cos(th), zc + radius * math.sin(th)),
              ORANGE, "hoop", quat=_rot_x(th + math.pi / 2))
    _geom(w, BOX, (0.04, 0.04, (zc - radius) / 2), (x, 0.0, (zc - radius) / 2), WHITE, "hoop")  # stand


def _tunnel(spec, x0, x1, half_w=0.4, h=0.65):
    w = spec.worldbody
    xc, half_l = (x0 + x1) / 2, (x1 - x0) / 2
    for y in (-half_w, half_w):
        _geom(w, BOX, (half_l, 0.01, h / 2), (xc, y, h / 2), GLASS, "tunnel")
    _geom(w, BOX, (half_l, half_w + 0.03, 0.01), (xc, 0.0, h), GLASS, "tunnel")
    n = 6
    for i in range(n):
        x = x0 + (x1 - x0) * i / (n - 1)
        for y in (-half_w - 0.02, half_w + 0.02):  # frame posts just outside the glass, so the inside stays clear
            _geom(w, BOX, (0.04, 0.03, h / 2), (x, y, h / 2), ORANGE, "tunnel")
        _geom(w, BOX, (0.04, half_w + 0.06, 0.03), (x, 0.0, h + 0.03), ORANGE, "tunnel")


def _slalom(spec, xs, y_off=0.45):
    for i, x in enumerate(xs):  # light poles: they tip over when hit
        y = y_off if i % 2 == 0 else -y_off
        b = _free_body(spec, "slalom", (x, y, 0.28))
        _geom(b, CYL, (0.09, 0.28), (0, 0, 0), RED, "slalom", mass=0.30)
        _geom(b, CYL, (0.095, 0.04), (0, 0, 0.08), WHITE, "slalom", mass=0.05)


def _finish(spec, x, half_w=0.8, h=1.1):
    w = spec.worldbody
    for y in (-half_w, half_w):
        _geom(w, CYL, (0.05, h / 2), (x, y, h / 2), WHITE, "finish")
    cells = 8
    cell_half = half_w / cells
    for i in range(cells):  # checkered banner across the top
        y = -half_w + (i + 0.5) * 2 * cell_half
        _geom(w, BOX, (0.02, cell_half, 0.08), (x, y, h), WHITE if i % 2 else (0.1, 0.1, 0.1, 1.0), "finish")


def _quat(rows) -> list:
    q = np.zeros(4)
    mujoco.mju_mat2Quat(q, np.array(rows, dtype=float).flatten())
    return q.tolist()


def _add_cameras(spec) -> None:
    """The dog's 3 eyes, matching src/sim/cameras.py (trunk frame: +x forward, +y left, +z up; a MuJoCo camera
    looks along its own -z, with +y up in the image). Columns of each matrix = the camera's x, y, z axes."""
    trunk = spec.body("trunk")
    # front: on the muzzle, looks along +x
    trunk.add_camera(name="head", pos=[0.32, 0.0, 0.08], fovy=85.0,
                     quat=_quat([[0, 0, -1], [-1, 0, 0], [0, 1, 0]]))
    # down: under the chin, 50 degrees below the horizon, sees the floor in front of the forepaws
    c, s_ = np.cos(np.radians(50)), np.sin(np.radians(50))
    trunk.add_camera(name="down", pos=[0.30, 0.0, -0.02], fovy=85.0,
                     quat=_quat([[0, s_, -c], [-1, 0, 0], [0, c, s_]]))
    # side: on the left flank, looks along +y
    trunk.add_camera(name="side", pos=[0.12, 0.05, 0.02], fovy=85.0,
                     quat=_quat([[1, 0, 0], [0, 0, -1], [0, 1, 0]]))


def build_model() -> mujoco.MjModel:
    spec = mujoco.MjSpec.from_file(str(model_path("go1")))
    for key in list(spec.keys):  # Menagerie's "home" keyframe has no values for the props' free joints
        spec.delete(key)
    _add_cameras(spec)
    _hurdle(spec, 1.5)
    _hoop(spec, 3.0)
    _tunnel(spec, 4.5, 6.9)
    _slalom(spec, (8.5, 10.0, 11.5, 13.0))
    _finish(spec, 15.0)
    _geom(_free_body(spec, "cube", (2.5, 2.2, 0.25)), BOX, (0.25, 0.25, 0.25), (0, 0, 0), BLUE, "cube", mass=1.5)
    _geom(_free_body(spec, "ball", (1.5, -2.0, 0.35)), SPHERE, (0.35,), (0, 0, 0), YELLOW, "ball", mass=0.6)
    _geom(_free_body(spec, "column", (-2.0, 1.5, 0.6)), CYL, (0.3, 0.6), (0, 0, 0), PURPLE, "column", mass=2.0)
    for i, c in enumerate((GREEN, ORANGE, RED)):
        _geom(_free_body(spec, "tower", (-1.5, -2.0, 0.2 + 0.4 * i)), BOX, (0.2, 0.2, 0.2), (0, 0, 0), c, "tower",
              mass=0.5)
    _geom(_free_body(spec, "egg", (6.0, -2.6, 0.42)), ELLIPSOID, (0.3, 0.3, 0.42), (0, 0, 0), GREEN, "egg", mass=1.0)
    _geom(_free_body(spec, "pouf", (7.5, 2.4, 0.15)), CYL, (0.4, 0.15), (0, 0, 0), WHITE, "pouf", mass=1.5)
    return spec.compile()
