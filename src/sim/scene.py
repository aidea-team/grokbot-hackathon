"""The dog's world: Menagerie's Go1 scene in a new, purpose-built environment (rebuilt 2026-11-04).

SIMULATION ONLY. Everything is simulated by MuJoCo's rigid-body physics:
- static props (stairs, scaffold, platforms, barriers, the person) are fixed to the world;
- the light ball is a free body: the dog can push it and make it roll.
Geoms are named "<label>_<n>", so a contact tells which object was touched.
LANDMARKS is the single source of truth for what the chat agent can be told about the world (describe()).

Layout, with the dog at the origin facing +x (y is to its left):
  ahead:   2 m of empty floor, then 8 steps (5 cm each) up to a scaffold platform 0.4 m high, rails on 3 sides;
  sides:   coloured low platforms, only to the left and right of the stair/scaffold line;
  behind:  5 barriers of growing height (0.10 .. 0.60 m), then a life-size standing person.
"""
from __future__ import annotations

import itertools
import math

import mujoco
import numpy as np

from models import model_path

BOX, SPHERE, CYL, ELLIPSOID, CAPSULE = (
    mujoco.mjtGeom.mjGEOM_BOX, mujoco.mjtGeom.mjGEOM_SPHERE, mujoco.mjtGeom.mjGEOM_CYLINDER,
    mujoco.mjtGeom.mjGEOM_ELLIPSOID, mujoco.mjtGeom.mjGEOM_CAPSULE,
)

FAST_RENDER = True  # False brings back shadows, floor reflection and antialiasing (nicer, ~4x slower per frame)

ORANGE = (0.95, 0.45, 0.10, 1.0)
RED = (0.85, 0.15, 0.15, 1.0)
BLUE = (0.20, 0.40, 0.90, 1.0)
GREEN = (0.20, 0.70, 0.35, 1.0)
YELLOW = (0.95, 0.80, 0.15, 1.0)
PURPLE = (0.55, 0.30, 0.75, 1.0)
WHITE = (0.92, 0.92, 0.92, 1.0)
GLASS = (0.30, 0.80, 0.90, 0.28)

# (description for the agent, x, y)
BARRIER_X = (-1.5, -2.5, -3.5, -4.5, -5.5)
BARRIER_H = (0.10, 0.20, 0.30, 0.45, 0.60)
PERSON_XY = (-8.0, 0.0)
LANDMARKS: list[tuple[str, float, float]] = [
    ("davanti a te: 2 metri di pavimento completamente vuoto (da x=0 a x=2)", 1.0, 0.0),
    ("scala di 8 gradini grigi larga 1 m (alzata 0,05 m, pedata 0,20 m) da x=2,0 a x=3,6, centrata su y=0, che sale "
     "verso +x fino all'impalcatura", 2.8, 0.0),
    ("impalcatura: piattaforma di legno 2 m x 1,8 m a 0,4 m di quota, da x=3,6 a x=5,6 e da y=-0,9 a y=+0,9, con "
     "parapetti metallici su tre lati: ci si sale solo dalla scala", 4.6, 0.0),
    ("a sinistra (y=+2,4), piattaforme basse colorate alte 0,15 m: rossa a x=2,7, blu a x=4,2, verde a x=5,7", 4.0, 2.4),
    ("a destra (y=-2,4), piattaforme basse colorate alte 0,15 m: gialla a x=2,7, arancione a x=4,2, viola a x=5,7",
     4.0, -2.4),
    ("alle tue spalle, 5 barriere larghe 1,6 m e di altezza crescente (0,10 / 0,20 / 0,30 / 0,45 / 0,60 m) a "
     "x=-1,5 / -2,5 / -3,5 / -4,5 / -5,5", -3.5, 0.0),
    ("palla arancione piccola e leggerissima (raggio 0,12 m, rotola lontano al minimo urto)", -0.8, 1.3),
    ("una persona in piedi a grandezza reale (1,75 m), di fronte a te se guardi indietro, in fondo alle barriere "
     "(maglia blu, pantaloni scuri)", PERSON_XY[0], PERSON_XY[1]),
]


def describe() -> str:
    return "\n".join(f"- {d}: centro in ({x:g}, {y:g})" for d, x, y in LANDMARKS)


_ids = itertools.count(1)


def _geom(parent, kind, size, pos, rgba, label, quat=None, mass=None, roll=None):
    s = list(size) + [0.0] * (3 - len(size))
    g = parent.add_geom(name=f"{label}_{next(_ids)}", type=kind, size=s, pos=list(pos), rgba=list(rgba))
    if quat is not None:
        g.quat = list(quat)
    if mass is not None:
        g.mass = mass
    if roll is not None:  # rolling resistance (m): without it a ball rolls almost forever. condim 6 enables it
        g.condim = 6
        g.friction = [1.0, 0.005, roll]
    return g


def _free_body(spec, label, pos):
    """A prop that physics can move: its own body with a free joint."""
    body = spec.worldbody.add_body(name=f"{label}_body_{next(_ids)}", pos=list(pos))
    body.add_freejoint()
    return body


def _rot_x(angle: float) -> list[float]:
    return [math.cos(angle / 2), math.sin(angle / 2), 0.0, 0.0]


def _stairs(spec, x0, x1, yc, half_w=0.5, n=8, rise=0.05):
    """Solid steps climbing towards +x: step i spans x0+i*tread..x1 and is (i+1)*rise tall."""
    w = spec.worldbody
    tread = (x1 - x0) / n
    for i in range(n):
        xa = x0 + i * tread
        h = (i + 1) * rise
        _geom(w, BOX, ((x1 - xa) / 2, half_w, h / 2), ((xa + x1) / 2, yc, h / 2), (0.62, 0.62, 0.66, 1.0), "stairs")


def _scaffold(spec, x0, x1, y0, y1, h=0.4):
    """Raised platform on poles. Rails on the three sides other than x0 (where the stairs arrive), so the only way up
    is the stairs; the platform deck is thin so the dog can also not squeeze under the rails."""
    w = spec.worldbody
    xc, yc, hx, hy = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2, (y1 - y0) / 2
    steel = (0.55, 0.57, 0.60, 1.0)
    _geom(w, BOX, (hx, hy, 0.03), (xc, yc, h - 0.03), (0.75, 0.62, 0.40, 1.0), "scaffold")  # deck, top at z=h
    for x in (x0 + 0.05, x1 - 0.05):
        for y in (y0 + 0.05, y1 - 0.05):  # legs
            _geom(w, CYL, (0.03, (h - 0.06) / 2), (x, y, (h - 0.06) / 2), steel, "scaffold")
    for y in (y0 + 0.05, y1 - 0.05):  # cross braces under the deck
        _geom(w, BOX, (hx, 0.015, 0.015), (xc, y, 0.15), steel, "scaffold")
    for x in (x1 - 0.05,):
        _geom(w, BOX, (0.015, hy, 0.015), (x, yc, 0.15), steel, "scaffold")
    rail_z = (h + 0.18, h + 0.36)
    for z in rail_z:  # long sides (y0, y1) and the back (x1)
        for y in (y0 + 0.02, y1 - 0.02):
            _geom(w, BOX, (hx, 0.015, 0.015), (xc, y, z), steel, "scaffold")
        _geom(w, BOX, (0.015, hy, 0.015), (x1 - 0.02, yc, z), steel, "scaffold")
    for x, y in ((x0 + 0.02, y0 + 0.02), (x0 + 0.02, y1 - 0.02), (x1 - 0.02, y0 + 0.02), (x1 - 0.02, y1 - 0.02),
                 (xc, y0 + 0.02), (xc, y1 - 0.02)):  # posts
        _geom(w, CYL, (0.015, 0.19), (x, y, h + 0.19), steel, "scaffold")


def _platform(spec, x, y, color, size=1.2, h=0.15):
    """A low coloured block, fixed to the world (the dog can walk up onto it: 15 cm is above its step clearance, so
    it is a real obstacle to climb or go around)."""
    _geom(spec.worldbody, BOX, (size / 2, size / 2, h / 2), (x, y, h / 2), color, "platform")


def _barrier(spec, x, h, half_w=0.8, depth=0.08):
    """A solid wall across the dog's path, h metres tall."""
    t = (h - 0.10) / 0.50  # colour ramps from green (low) to red (tall)
    color = (0.2 + 0.7 * t, 0.75 - 0.5 * t, 0.2, 1.0)
    _geom(spec.worldbody, BOX, (depth, half_w, h / 2), (x, 0.0, h / 2), color, "barrier")


def _person(spec, x, y, facing=0.0):
    """A life-size standing person (1.75 m), fixed to the world, made of simple solids. facing: yaw in radians."""
    w = spec.worldbody
    c, s_ = math.cos(facing), math.sin(facing)

    def at(dx, dy, z):  # offset in the person's frame -> world
        return (x + dx * c - dy * s_, y + dx * s_ + dy * c, z)
    skin, shirt, pants, shoe = (0.87, 0.68, 0.55, 1.0), (0.15, 0.30, 0.75, 1.0), (0.12, 0.12, 0.18, 1.0), (0.05, 0.05, 0.05, 1.0)
    for dy in (-0.09, 0.09):
        _geom(w, CAPSULE, (0.065, 0.36), at(0, dy, 0.50), pants, "person")  # legs, 0.07 .. 0.93
        _geom(w, BOX, (0.13, 0.05, 0.035), at(0.05, dy, 0.035), shoe, "person")  # feet
    _geom(w, BOX, (0.10, 0.20, 0.30), at(0, 0, 1.18), shirt, "person")  # torso 0.88 .. 1.48
    for dy in (-0.26, 0.26):
        _geom(w, CAPSULE, (0.045, 0.28), at(0, dy, 1.18), shirt, "person")  # arms along the sides
    _geom(w, CAPSULE, (0.05, 0.04), at(0, 0, 1.54), skin, "person")  # neck
    _geom(w, SPHERE, (0.11,), at(0, 0, 1.64), skin, "person")  # head, top at 1.75 m


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
    # ahead: 2 m empty, then the stairs and the scaffold
    _stairs(spec, 2.0, 3.6, 0.0)
    _scaffold(spec, 3.6, 5.6, -0.9, 0.9)
    # sides: coloured low platforms, only left and right of the stairs / scaffold line
    for x, left, right in ((2.7, RED, YELLOW), (4.2, BLUE, ORANGE), (5.7, GREEN, PURPLE)):
        _platform(spec, x, 2.4, left)
        _platform(spec, x, -2.4, right)
    # behind: barriers of growing height, then the person (facing the dog's start point, i.e. +x)
    for x, h in zip(BARRIER_X, BARRIER_H):
        _barrier(spec, x, h)
    _person(spec, *PERSON_XY, facing=0.0)
    _geom(_free_body(spec, "feather", (-0.8, 1.3, 0.12)), SPHERE, (0.12,), (0, 0, 0), ORANGE, "feather", mass=0.05,
          roll=0.003)
    spec.option.integrator = mujoco.mjtIntegrator.mjINT_IMPLICITFAST  # stabler with the PD leg actuators
    model = spec.compile()
    if FAST_RENDER:
        # Measured on the 3 dog cameras: shadows + floor reflection + MSAA = 39 ms/frame, without = 10 ms.
        model.light_castshadow[:] = 0  # no shadow maps (the biggest cost)
        model.mat_reflectance[:] = 0  # floor mirror = a second render pass
        model.vis.quality.offsamples = 0  # no antialiasing on offscreen (camera) frames
    return model
