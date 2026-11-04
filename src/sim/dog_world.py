"""Always-on MuJoCo world for the Go1, simulated with real rigid-body physics (mj_step). SIMULATION ONLY.

What is physics: gravity, contacts and friction, collisions with the props, pushing / knocking over the light
props, jumps in flight, landings, falls. All of it is MuJoCo's own dynamics (src/sim/scene.py builds the world).

What is control (the Menagerie Go1 ships without a walking policy, training one needs RL):
- legs: PD position actuators (the model's own) driven by a trot generator with inverse kinematics;
- trunk: a bounded stabiliser (limited force/torque on the trunk) tracks the commanded speed/turn rate and
  keeps the body upright while standing/walking. It is off in flight, so jumps and flips tumble for real;
- jumps/flips: at take-off the trunk is given the launch velocity (vertical, horizontal, spin) the commanded
  height needs; everything after that is free physics. A flip that is badly timed lands badly.

DogSim.run() owns the viewer and must run in the main thread (on macOS: under `mjpython`). Other threads call
submit() / clear() / reset_pose() / capture() / snapshot(); commands run one after another.
No safety limits here (virtual world), only numeric sanity checks. Nothing here can reach real hardware.
"""
from __future__ import annotations

import inspect
import io
import math
import os
import queue
import sys
import threading
import time
from typing import Callable, Iterator

if sys.platform == "darwin":  # CGL contexts work off the main thread (GLFW's do not), needed under mjpython
    os.environ.setdefault("MUJOCO_GL", "cgl")

import mujoco
import numpy as np

import cameras
from scene import build_model

Leg = tuple[float, float, float]  # hip, thigh, calf joint targets (rad)
Gen = Iterator[None]

G = 9.81
STAND: Leg = (0.0, 0.9, -1.8)
CROUCH: Leg = (0.0, 1.35, -2.6)
PUSH: Leg = (0.0, 0.55, -1.25)
TUCK: Leg = (0.0, 1.45, -2.7)
FOLD: Leg = (0.0, 1.7, -2.75)  # leg folded under the body (lying)
FR, FL, RR, RL = range(4)
LINK = 0.213  # thigh and calf length (m)
Z_FOOT = -0.265  # standing foot height below the thigh joint
Z_START = 0.28
FRAME_DT = 1 / 60
HOPS = {"jump", "backflip", "frontflip"}
JOINT_MIN = np.array([-0.863, -0.686, -2.818] * 4)
JOINT_MAX = np.array([0.863, 4.501, -0.888] * 4)

POSES: dict[str, list[Leg]] = {
    "stand": [STAND] * 4,
    "sit": [(0.0, 0.75, -1.5)] * 2 + [FOLD] * 2,  # front legs up, rear legs folded
    "lie_down": [FOLD] * 4,
    "bow": [FOLD] * 2 + [STAND] * 2,  # front down, rear up
}

# Trunk stabiliser presets: gains for velocity, yaw rate, pitch, roll, full "get upright" torque.
MODES: dict[str, dict[str, float]] = {
    "stand": dict(v=1.0, yaw=1.0, pitch=1.0, roll=1.0, full=0.0),
    "pose": dict(v=1.0, yaw=1.0, pitch=0.0, roll=1.0, full=0.0),  # sit / lie / bow: let the body pitch
    "air": dict(v=0.0, yaw=0.0, pitch=0.0, roll=0.0, full=0.0),  # free flight
    "land": dict(v=0.4, yaw=0.4, pitch=0.5, roll=0.6, full=0.0),
    "getup": dict(v=1.0, yaw=1.0, pitch=0.0, roll=0.0, full=1.0),
}
KV, FMAX = 60.0, 30.0  # trunk speed tracking: N per (m/s), force cap
KW, TZMAX = 6.0, 25.0  # yaw rate tracking (feet planted on the floor resist turning)
KP, KD, TMAX = 100.0, 6.0, 40.0  # pitch/roll stabiliser: Nm/rad, Nm/(rad/s), torque cap
KFULL = 60.0  # self-righting torque (get_up only)
FADE_FROM, FADE_TO = 0.4, 0.8  # tilt (rad) range over which the stabiliser fades out: a fallen dog gets no help


def smooth(s: float) -> float:
    s = min(1.0, max(0.0, s))
    return s * s * (3 - 2 * s)


def lerp(a, b, s: float):
    return tuple(x + (y - x) * s for x, y in zip(a, b))


def wrap(angle: float) -> float:
    return (angle + math.pi) % (2 * math.pi) - math.pi


def leg_ik(x: float, z: float) -> tuple[float, float]:
    """Thigh and calf angles that put the foot at (x forward, z up) relative to the thigh joint."""
    d = min(max(math.hypot(x, z), 0.09), 2 * LINK - 1e-3)
    theta2 = -math.acos(max(-1.0, min(1.0, d * d / (2 * LINK * LINK) - 1.0)))
    beta = math.atan2(-x, -z)
    return beta - theta2 / 2, theta2


# ---------------------------------------------------------------- action registry

ACTIONS: dict[str, dict] = {}


def num(desc: str) -> dict:
    return {"type": "number", "description": desc}


def action(name: str, description: str, properties: dict | None = None, required: tuple = ()):
    def deco(fn):
        ACTIONS[name] = {
            "fn": fn,
            "description": description,
            "parameters": {"type": "object", "properties": properties or {}, "required": list(required)},
        }
        return fn
    return deco


# ---------------------------------------------------------------- action helpers
# Every action is a generator taking the DogSim as first arg. It sets commands (speed, goals, mode) and
# `yield`s once per frame; DogSim then runs the physics for that frame. d.dt is the (time-scaled) frame time.

def wait(d: "DogSim", seconds: float) -> Gen:
    t = 0.0
    while t < seconds:
        t += d.dt
        yield


def go_pose(d: "DogSim", name: str, seconds: float = 0.9) -> Gen:
    d.set_mode("stand" if name == "stand" else "pose")
    d.v_cmd = d.w_cmd = 0.0
    d.goal_legs(POSES[name], rate=3.0)
    yield from wait(d, seconds)
    d.posture = name


def get_up(d: "DogSim") -> Gen:
    """Self-righting after a fall: strong upright torque plus some lift, legs back to the standing pose."""
    d.v_cmd = d.w_cmd = 0.0
    d.set_mode("getup")
    d.goal_legs(POSES["stand"], rate=6.0)
    t, ok = 0.0, 0.0
    while t < 6.0:
        t += d.dt
        d.lift = 0.45 if d.tilt() > 0.5 else 0.2  # partial unloading while rolling over, almost none after
        ok = ok + d.dt if (d.tilt() < 0.3 and d.z > 0.2 and d.support() >= 3) else 0.0
        if ok > 0.5:
            break
        yield
    d.lift = 0.0
    d.set_mode("land")
    yield from wait(d, 0.4)
    d.set_mode("stand")
    d.posture = "stand"


def stand_up(d: "DogSim") -> Gen:
    if d.tilt() > 0.7:  # fallen over: needs the self-righting routine
        yield from get_up(d)
    elif d.posture != "stand" or d.z < 0.2:  # sitting / lying / bowing: just stand up
        yield from go_pose(d, "stand", 1.0)
    d.set_mode("stand")


# ---------------------------------------------------------------- actions

@action("walk", "Cammina in avanti (distanza positiva) o indietro (negativa), mantenendo la direzione corrente. "
        "Per correre usa speed_mps alto. Se incontra un ostacolo solido si ferma contro di esso.",
        {"distance_m": num("Metri da percorrere, negativo = indietro"),
         "speed_mps": num("Velocità in m/s (default 0.8, camminata ~0.8, corsa 1.5-2)")},
        required=("distance_m",))
def walk(d, distance_m: float, speed_mps: float = 0.8) -> Gen:
    yield from stand_up(d)
    speed = min(abs(speed_mps) or 0.8, 2.5)  # the trot generator and trunk force cap what is physically reachable
    direction = 1.0 if distance_m >= 0 else -1.0
    target, heading = abs(distance_m), d.yaw
    hx, hy = math.cos(heading), math.sin(heading)
    x0, y0 = d.x, d.y
    t, history = 0.0, []
    d.set_mode("stand")
    while True:
        s = ((d.x - x0) * hx + (d.y - y0) * hy) * direction
        remaining = target - s
        if remaining <= 0.02:
            break
        d.v_cmd = direction * speed * min(1.0, 0.2 + remaining / 0.3)
        d.w_cmd = max(-0.6, min(0.6, 2.0 * wrap(heading - d.yaw)))  # hold the heading
        t += d.dt
        history.append((t, s))
        if t > 1.2:  # stuck: less than 12% of the commanded progress in the last second
            t_old, s_old = next((h for h in history if h[0] >= t - 1.0), history[0])
            if (s - s_old) < 0.12 * speed * (t - t_old) and d.support_props():
                d.stuck = True
                break
        if t > target / max(0.05, speed) * 3 + 4:  # never walk forever
            break
        yield
    d.v_cmd = d.w_cmd = 0.0
    yield from wait(d, 0.4)


@action("turn", "Gira su sé stesso: gradi positivi = a sinistra (antiorario), negativi = a destra.",
        {"degrees": num("Angolo in gradi (360 = giro completo)"),
         "rate_dps": num("Velocità angolare in gradi/s (default 90)")},
        required=("degrees",))
def turn(d, degrees: float, rate_dps: float = 90.0) -> Gen:
    yield from stand_up(d)
    rate = min(math.radians(abs(rate_dps) or 90.0), 3.0)
    direction = 1.0 if degrees >= 0 else -1.0
    remaining, prev, t = math.radians(abs(degrees)), d.yaw, 0.0
    limit = remaining / max(0.05, rate) * 3 + 4  # never turn forever
    d.set_mode("stand")
    while remaining > 0.015 and t < limit:
        d.w_cmd = direction * rate * min(1.0, 0.15 + remaining / 0.4)
        d.v_cmd = 0.0
        yield
        t += d.dt
        remaining -= direction * wrap(d.yaw - prev)
        prev = d.yaw
    d.w_cmd = 0.0
    yield from wait(d, 0.35)


@action("go_to", "Va al punto (x, y) del mondo: si gira verso il punto e ci cammina. "
        "Origine (0,0) = punto di partenza, +x = davanti all'avvio, +y = sinistra.",
        {"x_m": num("Coordinata x in metri"), "y_m": num("Coordinata y in metri"),
         "speed_mps": num("Velocità in m/s (default 0.8)")},
        required=("x_m", "y_m"))
def go_to(d, x_m: float, y_m: float, speed_mps: float = 0.8) -> Gen:
    dx, dy = x_m - d.x, y_m - d.y
    dist = math.hypot(dx, dy)
    if dist < 1e-3:
        return
    yield from turn(d, math.degrees(wrap(math.atan2(dy, dx) - d.yaw)))
    yield from walk(d, dist, speed_mps)


def _hop(d: "DogSim", height: float, travel: float, flip: float, spin_deg: float) -> Gen:
    """Crouch, push off (launch velocity), then free physics in flight, landing and, if needed, a fall."""
    yield from stand_up(d)
    v0 = math.sqrt(2 * G * max(height, 0.05))
    T = 2 * v0 / G  # flight time for a landing at take-off height
    yaw0 = d.yaw
    d.v_cmd = d.w_cmd = 0.0
    d.set_mode("pose")
    d.goal_legs([CROUCH] * 4, rate=6.0)
    yield from wait(d, 0.45)
    d.goal_legs([PUSH] * 4, rate=60.0)
    yield from wait(d, 0.09)
    # take-off: launch velocity, then the body is on its own
    vx, vy = travel / T * math.cos(yaw0), travel / T * math.sin(yaw0)
    d.set_mode("air")
    d.launch((vx, vy, v0), (0.0, flip * 2 * math.pi / (T * 1.03), math.radians(spin_deg) / T))
    d.goal_legs([TUCK] * 4, rate=30.0)
    t, landed = 0.0, False
    while t < T * 1.8 + 0.6:
        t += d.dt
        if t > 0.62 * T:
            d.goal_legs([STAND] * 4, rate=25.0)
        if t > 0.2 and d.support() > 0:
            landed = True
            break
        yield
    d.set_mode("land")
    d.goal_legs([STAND] * 4, rate=10.0)
    yield from wait(d, 0.7)
    if d.tilt() < 0.7:
        d.set_mode("stand")
        d.posture = "stand"
    if landed and d.touched_action:
        d.crashed = True


@action("jump", "Salto sul posto o in avanti, con eventuale giravolta in aria. Se urta qualcosa cade davvero.",
        {"height_m": num("Altezza dell'apice in metri (default 1.0)"),
         "forward_m": num("Metri percorsi in avanti durante il salto (default 0)"),
         "spin_deg": num("Giravolta in aria in gradi, es. 360 (default 0)")})
def jump(d, height_m: float = 1.0, forward_m: float = 0.0, spin_deg: float = 0.0) -> Gen:
    yield from _hop(d, height_m, forward_m, 0.0, spin_deg)


@action("backflip", "Salto mortale all'indietro (rotazione di 360° in aria). Se sbaglia l'atterraggio cade.",
        {"height_m": num("Altezza dell'apice in metri (default 0.9)"),
         "travel_m": num("Spostamento durante il salto, negativo = indietro (default -0.3)")})
def backflip(d, height_m: float = 0.9, travel_m: float = -0.3) -> Gen:
    yield from _hop(d, height_m, travel_m, -1.0, 0.0)


@action("frontflip", "Salto mortale in avanti (rotazione di 360° in aria). Se sbaglia l'atterraggio cade.",
        {"height_m": num("Altezza dell'apice in metri (default 0.9)"),
         "travel_m": num("Spostamento in avanti durante il salto (default 0.6)")})
def frontflip(d, height_m: float = 0.9, travel_m: float = 0.6) -> Gen:
    yield from _hop(d, height_m, travel_m, 1.0, 0.0)


@action("stand", "Mettiti in piedi (anche da caduto).")
def stand(d) -> Gen:
    if d.tilt() > 0.7:
        yield from get_up(d)
    else:
        yield from go_pose(d, "stand", 1.0)


@action("sit", "Siediti.")
def sit(d) -> Gen:
    yield from stand_up(d)
    yield from go_pose(d, "sit", 1.2)


@action("lie_down", "Sdraiati a pancia in giù.")
def lie_down(d) -> Gen:
    yield from stand_up(d)
    yield from go_pose(d, "lie_down", 1.4)


@action("bow", "Fai un inchino (muso giù, posteriore in alto).")
def bow(d) -> Gen:
    yield from stand_up(d)
    yield from go_pose(d, "bow", 1.2)


@action("wave_paw", "Siediti e saluta / dai la zampa agitando la zampa anteriore destra.",
        {"seconds": num("Durata in secondi (default 3)")})
def wave_paw(d, seconds: float = 3.0) -> Gen:
    yield from stand_up(d)
    yield from go_pose(d, "sit", 1.2)
    seconds, t = max(seconds, 0.6), 0.0
    base = POSES["sit"][FR]
    while t < seconds:
        t += d.dt
        ramp = min(1.0, t / 0.4) * min(1.0, max(0.0, (seconds - t) / 0.4))
        raised = (0.0, -0.3, -1.3 + 0.4 * math.sin(2 * math.pi * 3 * t))
        d.goal_leg(FR, lerp(base, raised, smooth(ramp)), rate=20.0)
        yield
    d.goal_leg(FR, base, rate=6.0)
    yield from wait(d, 0.5)


@action("wiggle", "Scodinzola: scuoti il posteriore a destra e sinistra.",
        {"seconds": num("Durata in secondi (default 2)")})
def wiggle(d, seconds: float = 2.0) -> Gen:
    yield from stand_up(d)
    seconds, t = max(seconds, 0.5), 0.0
    while t < seconds:
        t += d.dt
        ramp = min(1.0, t / 0.2) * min(1.0, max(0.0, (seconds - t) / 0.2))
        d.w_cmd = 2.4 * ramp * math.sin(2 * math.pi * 3 * t)
        yield
    d.w_cmd = 0.0
    yield from wait(d, 0.3)


def _recover(d: "DogSim") -> Gen:
    """After a stop: stop moving and get back to a normal standing pose from wherever the dog is."""
    d.v_cmd = d.w_cmd = 0.0
    yield from stand_up(d)


# ---------------------------------------------------------------- the world

class _Capture:
    """A camera frame requested from another thread, served by the simulator thread."""

    def __init__(self, width: int, height: int, camera: str):
        self.width, self.height, self.camera = width, height, camera
        self.jpeg: bytes | None = None
        self.error: str | None = None
        self.done = threading.Event()


class DogSim:
    def __init__(self, headless: bool = False, log=None):
        self.headless = headless
        self.log = log  # anything with .event(kind, **fields), e.g. driver.JsonlLog
        self.model = build_model()  # Go1 + props (src/sim/scene.py)
        self.data = mujoco.MjData(self.model)
        self.viewer = None
        self.time_scale = 1.0
        self.dt = 0.0

        m = self.model
        self.trunk = m.body("trunk").id
        self.mass = float(sum(m.body_mass[b] for b in range(m.nbody) if m.body_rootid[b] == self.trunk))
        floor = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, "floor")
        self._is_dog = [bool(m.body_rootid[m.geom_bodyid[g]] == self.trunk) for g in range(m.ngeom)]
        self._prop_label = [("" if (g == floor or self._is_dog[g] or not m.geom(g).name)
                             else m.geom(g).name.rsplit("_", 1)[0]) for g in range(m.ngeom)]

        # commands set by the actions
        self.mode = "stand"
        self.gains = MODES["stand"]
        self.v_cmd = self.w_cmd = 0.0
        self.lift = 0.0
        self.posture = "stand"
        self.q_goal = np.zeros(12)
        self.q_des = np.zeros(12)
        self.rate = 6.0
        self._leg_rates = np.full(12, 6.0)
        self.phase = 0.0

        # contacts seen in the last frame / during the current action
        self._support = 0
        self._props_now: set[str] = set()
        self.touched_action: set[str] = set()
        self.stuck = False
        self.crashed = False
        self.last_block: str | None = None  # first prop touched during the last finished action
        self.last_stuck = False
        self.last_crash = False
        self.last_fell = False

        self._queue: queue.Queue = queue.Queue()
        self._gen: Gen | None = None
        self._current: str | None = None
        self._stop_req = False
        self._reset_req = False
        self._quit = threading.Event()
        self._next_id = 0
        self._done = 0
        self._pending: list[str] = []
        self._lock = threading.Lock()
        self._captures: queue.Queue = queue.Queue()
        self._renderers: dict[tuple[int, int], mujoco.Renderer] = {}  # created lazily, in the sim thread
        self._acc = 0.0
        self._reopen_at, self._reopen_failed = 0.0, False
        self._init_state()

    # -------- state read from the physics
    @property
    def x(self) -> float:
        return float(self.data.qpos[0])

    @property
    def y(self) -> float:
        return float(self.data.qpos[1])

    @property
    def z(self) -> float:
        return float(self.data.qpos[2])

    @property
    def yaw(self) -> float:
        w, x, y, z = self.data.qpos[3:7]
        return math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))

    def _rot(self) -> np.ndarray:
        r = np.zeros(9)
        mujoco.mju_quat2Mat(r, self.data.qpos[3:7])
        return r.reshape(3, 3)

    def tilt(self) -> float:
        """Angle between the body's up axis and the world's (0 = upright, pi = upside down)."""
        return math.acos(max(-1.0, min(1.0, float(self._rot()[2, 2]))))

    def support(self) -> int:
        """Number of contacts between the dog and the floor/props in the last frame."""
        return self._support

    def support_props(self) -> bool:
        return bool(self._props_now)

    # -------- commands used by the actions
    def set_mode(self, name: str) -> None:
        self.mode, self.gains = name, MODES[name]

    def goal_legs(self, legs: list[Leg], rate: float = 6.0) -> None:
        self.q_goal = np.array([a for leg in legs for a in leg], dtype=float)
        self._leg_rates[:] = rate

    def goal_leg(self, i: int, leg: Leg, rate: float = 6.0) -> None:
        self.q_goal[3 * i: 3 * i + 3] = leg
        self._leg_rates[3 * i: 3 * i + 3] = rate

    def launch(self, v_world: tuple[float, float, float], omega_body: tuple[float, float, float]) -> None:
        """Take-off: give the trunk its launch velocity (world linear, body angular)."""
        self.data.qvel[0:3] = v_world
        self.data.qvel[3:6] = omega_body

    # -------- thread-safe API
    def submit(self, name: str, args: dict | None = None) -> dict:
        spec = ACTIONS.get(name)
        if spec is None:
            return {"ok": False, "error": f"unknown command {name!r}", "available": sorted(ACTIONS)}
        args = dict(args or {})
        params = inspect.signature(spec["fn"]).parameters
        clean = {}
        for key, value in args.items():
            if key not in list(params)[1:]:
                return {"ok": False, "error": f"{name}: unknown argument {key!r}"}
            try:
                value = float(value)
            except (TypeError, ValueError):
                return {"ok": False, "error": f"{name}.{key}: not a number: {value!r}"}
            if not math.isfinite(value):
                return {"ok": False, "error": f"{name}.{key}: not finite"}
            clean[key] = value
        try:
            inspect.signature(spec["fn"]).bind(None, **clean)
        except TypeError as e:
            return {"ok": False, "error": f"{name}: {e}"}
        label = f"{name}({', '.join(f'{k}={v:g}' for k, v in clean.items())})"
        with self._lock:
            self._next_id += 1
            cmd_id = self._next_id
            self._pending.append(label)
        self._queue.put((cmd_id, name, clean, label))
        self._log("sim_command_queued", id=cmd_id, command=label)
        return {"ok": True, "id": cmd_id, "queued": label, "queue_length": self._queue.qsize() + (1 if self._gen else 0)}

    def clear(self) -> None:
        """Stop everything: drop the queue and abort the current action."""
        self._stop_req = True

    def is_idle(self) -> bool:
        return self._gen is None and self._queue.empty()

    def capture(self, width: int = 512, height: int = 384, camera: str = "front",
                wait_idle: bool = False, timeout: float = 120.0) -> bytes | None:
        """JPEG from the dog's camera, or None. Thread-safe; the frame is rendered by the sim thread.

        wait_idle=True first waits until every queued command has finished (the dog "looks" after moving).
        """
        if wait_idle:
            deadline = time.monotonic() + timeout
            while not self.is_idle() and time.monotonic() < deadline:
                time.sleep(0.1)
        req = _Capture(width, height, cameras.get(camera).mj)
        self._captures.put(req)
        if not req.done.wait(10.0):
            self._log("camera_timeout")
            return None
        if req.error:
            self._log("camera_error", error=req.error)
        return req.jpeg

    def reset_pose(self) -> None:
        """Drop everything and put the dog (and every prop) back at the start."""
        self._reset_req = True

    def set_time_scale(self, scale: float) -> None:
        self.time_scale = min(4.0, max(0.05, float(scale)))

    def shutdown(self) -> None:
        self._quit.set()

    def snapshot(self) -> dict:
        with self._lock:
            pending = list(self._pending)
        fallen = self.tilt() > 0.9
        return {
            "x": round(self.x, 2), "y": round(self.y, 2), "yaw_deg": round(math.degrees(wrap(self.yaw))),
            "z": round(self.z, 2), "posture": "caduto" if fallen else self.posture,
            "current": self._current, "queue": pending[1:] if self._current else pending,
            "done": self._done, "time_scale": self.time_scale,
            "viewer": bool(self.viewer) and self.viewer.is_running() if not self.headless else None,
        }

    # -------- main loop (main thread)
    def run(self) -> None:
        self._open_viewer()
        last = time.monotonic()
        try:
            while not self._quit.is_set():
                now = time.monotonic()
                dt, last = min(now - last, 0.05) * self.time_scale, now
                self.step(dt)
                if self.viewer is not None:
                    if self.viewer.is_running():
                        self.viewer.sync()
                    else:  # window closed: the simulator stays on, the window comes back a moment later
                        try:
                            self.viewer.close()
                        except Exception:  # noqa: BLE001
                            pass
                        self.viewer, self._reopen_at = None, now + 1.0
                elif not self.headless and now >= self._reopen_at:
                    self._reopen_viewer(now)
                time.sleep(max(0.0, FRAME_DT - (time.monotonic() - now)))
        finally:
            for renderer in self._renderers.values():
                renderer.close()
            if self.viewer is not None:
                self.viewer.close()

    def step(self, dt: float) -> None:
        """Advance by dt seconds: run the current action, run the physics, then serve camera requests."""
        self._advance(dt)
        self._serve_captures()

    def _serve_captures(self) -> None:
        while True:
            try:
                req = self._captures.get_nowait()
            except queue.Empty:
                return
            try:
                from PIL import Image
                key = (req.width, req.height)
                if key not in self._renderers:
                    self._renderers[key] = mujoco.Renderer(self.model, height=req.height, width=req.width)
                renderer = self._renderers[key]
                renderer.update_scene(self.data, camera=req.camera)
                buf = io.BytesIO()
                Image.fromarray(renderer.render()).save(buf, format="JPEG", quality=80)
                req.jpeg = buf.getvalue()
            except Exception as e:  # never let a camera problem stop the simulator
                req.error = repr(e)
            req.done.set()

    def _advance(self, dt: float) -> None:
        self.dt = dt
        if self._reset_req:
            self._reset_req = self._stop_req = False
            while not self._queue.empty():
                self._queue.get_nowait()
            with self._lock:
                self._pending.clear()
            self._gen, self._current = None, None
            self._init_state()
            self._log("sim_reset")
        if self._stop_req:
            self._stop_req = False
            while not self._queue.empty():
                self._queue.get_nowait()
            with self._lock:
                self._pending.clear()
            self._current = None
            self._gen = _recover(self)
            self._log("sim_stop")
        if self._gen is None:
            try:
                cmd_id, name, args, label = self._queue.get_nowait()
            except queue.Empty:
                self._physics(dt)
                return
            self._current = label
            self.touched_action, self.stuck, self.crashed = set(), False, False
            self._gen = ACTIONS[name]["fn"](self, **args)
            self._log("sim_command_start", id=cmd_id, command=label)
        try:
            next(self._gen)
        except StopIteration:
            self._finish()
        except Exception as e:  # a broken action must not kill the simulator
            self._log("sim_command_error", command=self._current, error=repr(e))
            self._finish()
            self._gen = _recover(self)
        self._physics(dt)

    def _finish(self) -> None:
        if self._current:
            with self._lock:
                if self._pending:
                    self._pending.pop(0)
            self._done += 1
            touched = sorted(self.touched_action)
            self.last_block = touched[0] if touched else None
            self.last_stuck, self.last_crash = self.stuck, self.crashed
            self.last_fell = self.tilt() > 0.9
            self._log("sim_command_done", command=self._current, touched=touched, stuck=self.stuck,
                      crashed=self.crashed, fell=self.last_fell)
        self._current, self._gen = None, None
        self.v_cmd = self.w_cmd = 0.0

    # -------- physics
    def _init_state(self) -> None:
        m, d = self.model, self.data
        mujoco.mj_resetData(m, d)  # props go back to their initial poses
        d.qpos[0:3] = (0.0, 0.0, Z_START)
        d.qpos[3:7] = (1.0, 0.0, 0.0, 0.0)
        for i, leg in enumerate(POSES["stand"]):
            d.qpos[7 + 3 * i: 10 + 3 * i] = leg
        self.q_goal = np.array([a for leg in POSES["stand"] for a in leg], dtype=float)
        self.q_des = self.q_goal.copy()
        d.ctrl[:] = self.q_des
        self.set_mode("stand")
        self.v_cmd = self.w_cmd = self.lift = self.phase = 0.0
        self.posture = "stand"
        self.last_block, self.last_stuck, self.last_crash, self.last_fell = None, False, False, False
        self._acc = 0.0
        mujoco.mj_forward(m, d)

    def _physics(self, dt: float) -> None:
        m, d = self.model, self.data
        # leg targets: gait while commanded to move, else the goal pose; smoothed by a rate limit
        goal = self._gait_targets(dt) if (self.mode in ("stand", "getup") and self._moving()) else self.q_goal
        step = self._leg_rates * dt
        self.q_des += np.clip(goal - self.q_des, -step, step)
        d.ctrl[:] = np.clip(self.q_des, JOINT_MIN, JOINT_MAX)
        n = int((self._acc + dt) / m.opt.timestep)
        self._acc = self._acc + dt - n * m.opt.timestep
        lock = self.viewer.lock() if self.viewer is not None else None
        if lock is not None:
            lock.__enter__()
        try:
            for _ in range(n):
                d.xfrc_applied[self.trunk] = self._trunk_wrench()
                mujoco.mj_step(m, d)
            if not np.isfinite(d.qpos).all():  # numerical blow-up: never leave the sim in NaN land
                self._log("sim_unstable")
                self._init_state()
        finally:
            if lock is not None:
                lock.__exit__(None, None, None)
        self._scan_contacts()

    def _moving(self) -> bool:
        return abs(self.v_cmd) > 0.02 or abs(self.w_cmd) > 0.05

    def _gait_targets(self, dt: float) -> np.ndarray:
        """Trot: diagonal leg pairs alternate; stance feet sweep backwards, swing feet lift and go forward."""
        speed = max(abs(self.v_cmd), abs(self.w_cmd) * 0.13)
        freq = min(5.0, 2.8 + 2.0 * speed)
        self.phase = (self.phase + freq * dt) % 1.0
        duty = 0.6
        out = np.zeros(12)
        for i in range(4):
            side = 0.13 if i in (FL, RL) else -0.13  # left legs are on +y
            v_i = self.v_cmd - self.w_cmd * side
            stride = max(-0.22, min(0.22, v_i * duty / freq))
            p = (self.phase + (0.0 if i in (FR, RL) else 0.5)) % 1.0
            if p < duty:  # stance
                x, z = stride / 2 - stride * (p / duty), Z_FOOT
            else:  # swing
                u = (p - duty) / (1 - duty)
                x, z = -stride / 2 + stride * u, Z_FOOT + 0.06 * math.sin(math.pi * u)
            th1, th2 = leg_ik(x, z)
            out[3 * i: 3 * i + 3] = (0.0, th1, th2)
        return out

    def _trunk_wrench(self) -> np.ndarray:
        """The bounded stabiliser: force/torque on the trunk (world frame), scaled by the current mode."""
        d = self.data
        R = self._rot()
        g = self.gains
        if self.mode != "getup":  # a dog that has tipped over gets no help from the stabiliser
            tilt = math.acos(max(-1.0, min(1.0, float(R[2, 2]))))
            fade = max(0.0, min(1.0, (FADE_TO - tilt) / (FADE_TO - FADE_FROM)))
            g = {k: v * fade for k, v in g.items()}
        w_world = R @ d.qvel[3:6]
        yaw = math.atan2(R[1, 0], R[0, 0])
        v_des = self.v_cmd * np.array([math.cos(yaw), math.sin(yaw)])
        force = np.zeros(3)
        if g["v"] > 0:
            f = g["v"] * KV * (v_des - d.qvel[0:2])
            n = float(np.linalg.norm(f))
            force[:2] = f * (min(1.0, FMAX * g["v"] / n) if n > 1e-9 else 1.0)
        force[2] = self.lift * self.mass * G
        torque = np.zeros(3)
        if g["yaw"] > 0:
            torque[2] = max(-TZMAX, min(TZMAX, g["yaw"] * KW * (self.w_cmd - w_world[2])))
        if g["pitch"] > 0 or g["roll"] > 0:  # small-angle stabiliser in the body frame
            wb = d.qvel[3:6]
            tb = np.zeros(3)
            tb[0] = g["roll"] * (-KP * R[2, 1] - KD * wb[0])
            tb[1] = g["pitch"] * (KP * R[2, 0] - KD * wb[1])
            torque += R @ np.clip(tb, -TMAX, TMAX)
        if g["full"] > 0:  # works upside down too: rotate the body's up axis towards the world's
            zb = R[:, 2]
            axis = np.cross(zb, [0.0, 0.0, 1.0])
            s = float(np.linalg.norm(axis))
            if s < 1e-6:
                axis, s = R[:, 0].copy(), 1.0  # exactly inverted: roll about the heading axis
            ang = math.atan2(s, float(zb[2]))
            torque += g["full"] * np.clip(KFULL * ang * axis / s - KD * (w_world - w_world[2] * np.array([0, 0, 1.0])),
                                          -TMAX * 0.75, TMAX * 0.75)
        return np.concatenate([force, torque])

    def _scan_contacts(self) -> None:
        d = self.data
        support, props = 0, set()
        for i in range(d.ncon):
            c = d.contact[i]
            a, b = self._is_dog[c.geom1], self._is_dog[c.geom2]
            if a == b:
                continue
            support += 1
            label = self._prop_label[c.geom2 if a else c.geom1]
            if label:
                props.add(label)
        self._support, self._props_now = support, props
        self.touched_action |= props

    def _open_viewer(self) -> None:
        """First open, at startup: a failure here is a setup problem (e.g. plain python on macOS)."""
        if self.headless:
            return
        import mujoco.viewer
        try:
            self.viewer = mujoco.viewer.launch_passive(self.model, self.data)
        except RuntimeError as e:
            raise SystemExit(f"{e}\nOn macOS run this with `mjpython` instead of `python`.") from e
        self._setup_viewer_camera()

    def _reopen_viewer(self, now: float) -> None:
        """After the user closed the window. MuJoCo may still consider the old one open for a moment:
        keep retrying quietly, never take the simulator (or the web app) down."""
        import mujoco.viewer
        try:
            self.viewer = mujoco.viewer.launch_passive(self.model, self.data)
        except RuntimeError as e:
            if not self._reopen_failed:
                self._log("viewer_reopen_failed", error=str(e))
                self._reopen_failed = True
            self._reopen_at = now + 2.0
            return
        self._reopen_failed = False
        self._setup_viewer_camera()
        self._log("viewer_reopened")

    def _setup_viewer_camera(self) -> None:
        cam = self.viewer.cam
        cam.type = mujoco.mjtCamera.mjCAMERA_TRACKING
        cam.trackbodyid = self.trunk
        cam.distance, cam.azimuth, cam.elevation = 3.0, 150, -15

    def _log(self, kind: str, **fields) -> None:
        if self.log is not None:
            self.log.event(kind, **fields)
