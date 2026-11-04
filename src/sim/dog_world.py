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
SWING_LIFT, SWING_SHAPE = 0.09, 1.0  # foot clearance in the swing phase (m) and how early it rises (<1 = earlier)
GAIT_RATE = 12.0  # joint target slew (rad/s) while walking: pose changes leave it lower (3-6), which cripples the trot
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
    "limp": dict(v=0.0, yaw=0.0, pitch=0.0, roll=0.0, full=0.0),  # DAMPING: no help at all
}
KV, KI, FMAX = 60.0, 250.0, 30.0  # trunk speed tracking: N per (m/s), N per (m/s*s) integral (the firmware regulates speed itself), force cap
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


# ---------------------------------------------------------------- behaviours
# The simulator does NOT have its own command language any more: it receives what the real dog receives
# (src/dog/commands.py -> SimDriver): a velocity (vx, vyaw) and/or a Go1 high-level MODE. Each mode that makes the
# dog do something on its own is a generator here, started on the rising edge of the mode (like the dog's firmware).

BEHAVIORS: dict[str, Callable] = {}


def behavior(mode: str):
    def deco(fn):
        BEHAVIORS[mode] = fn
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
    d._leg_rates[:] = GAIT_RATE


# ---------------------------------------------------------------- actions

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


@behavior("JUMPYAW")
def jump_yaw(d) -> Gen:
    """JUMPYAW: a jump on the spot with a 90 degree yaw turn in the air (parameters are our guess of the firmware's)."""
    yield from _hop(d, 0.6, 0.0, 0.0, 90.0)


@behavior("BACKFLIP")
def backflip(d) -> Gen:
    """BACKFLIP: one full backward somersault. A bad landing makes the dog fall for real."""
    yield from _hop(d, 0.9, -0.3, -1.0, 0.0)


@behavior("STAND_UP")
def stand_up_mode(d) -> Gen:
    if d.tilt() > 0.7:  # fallen over: needs the self-righting routine
        yield from get_up(d)
    else:
        yield from go_pose(d, "stand", 1.0)
    d._leg_rates[:] = GAIT_RATE


@behavior("RECOVERY")
def recovery(d) -> Gen:
    yield from get_up(d)
    d._leg_rates[:] = GAIT_RATE


@behavior("STAND_DOWN")
def lie_down(d) -> Gen:
    yield from stand_up(d)
    yield from go_pose(d, "lie_down", 1.4)


def _dance(d, style: int) -> Gen:
    """Dances while its mode is still being sent (like the firmware: stop sending, the dance ends)."""
    yield from stand_up(d)
    d.set_mode("stand")
    t = 0.0
    base = POSES["stand"]
    while d.requested_mode() == f"DANCE{style}" and t < 120.0:
        t += d.dt
        ramp = min(1.0, t / 0.4)
        if style == 2:  # sway: yaw swings and the front-right paw goes up on the beat
            d.w_cmd = 1.6 * ramp * math.sin(2 * math.pi * 1.0 * t)
            beat = max(0.0, math.sin(2 * math.pi * 2.0 * t))
            d.goal_leg(FR, lerp(base[FR], (0.0, -0.3, -1.3), smooth(ramp * beat)), rate=20.0)
        else:  # bounce: squat and rise twice a second while wiggling
            squat = 0.5 + 0.5 * math.sin(2 * math.pi * 2.0 * t)
            d.goal_legs([lerp(STAND, CROUCH, 0.7 * squat * ramp)] * 4, rate=12.0)
            d.w_cmd = 1.8 * ramp * math.sin(2 * math.pi * 1.0 * t)
        yield
    d.w_cmd = 0.0
    d.goal_legs(POSES["stand"], rate=6.0)
    yield from wait(d, 0.6)
    d._leg_rates[:] = GAIT_RATE


@behavior("DANCE1")
def dance1(d) -> Gen:
    yield from _dance(d, 1)


@behavior("DANCE2")
def dance2(d) -> Gen:
    yield from _dance(d, 2)


@behavior("STRAIGHTHAND")
def straight_hand(d) -> Gen:
    """Front-right paw stretched forward while the mode is on (the dog's own duration is unknown to us)."""
    yield from stand_up(d)
    d.set_mode("stand")
    d.goal_leg(FR, (0.0, 0.2, -0.9), rate=8.0)
    t = 0.0
    while d.requested_mode() == "STRAIGHTHAND" and t < 60.0:
        t += d.dt
        yield
    d.goal_leg(FR, STAND, rate=6.0)
    yield from wait(d, 0.6)
    d._leg_rates[:] = GAIT_RATE


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
        self.jpeg_quality = 80  # camera JPEG quality (the agent settings can change it)
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

        # what the dog's high-level interface receives (set by SimDriver from any thread, read by the physics thread)
        self._cmd = {"vx": 0.0, "vyaw": 0.0, "mode": "IDLE"}
        self._last_mode = "IDLE"  # mode seen in the previous frame: behaviours start on the rising edge
        self._ignored_vel_logged = False
        self._limp = False
        self._vint = np.zeros(2)  # integral of the trunk velocity error
        self._gen: Gen | None = None
        self._beh: str | None = None
        self._reset_req = False
        self._quit = threading.Event()
        self._lock = threading.Lock()
        self._clock = threading.Condition()  # notified after every physics frame: SimDriver sleeps on sim time
        self._gain0 = (self.model.actuator_gainprm[:, 0].copy(), self.model.actuator_biasprm[:, 1].copy())
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
    def set_command(self, vx: float | None = None, vyaw: float | None = None, mode: str | None = None) -> None:
        """The simulated UDP link: what Go1Driver would put on the wire (velocity and/or high-level mode)."""
        with self._lock:
            if vx is not None:
                self._cmd["vx"], self._cmd["vyaw"] = float(vx), float(vyaw or 0.0)
            if mode is not None:
                self._cmd["mode"] = mode

    def requested_mode(self) -> str:
        with self._lock:
            return self._cmd["mode"]

    @property
    def sim_time(self) -> float:
        return float(self.data.time)

    def wait_sim_time(self, seconds: float, timeout: float = 5.0) -> None:
        """Block the calling thread until `seconds` of simulated time have passed (or the sim was reset/quit)."""
        t0 = self.sim_time
        deadline = time.monotonic() + timeout
        with self._clock:
            while self.sim_time - t0 < seconds and self.sim_time >= t0 and not self._quit.is_set():
                left = deadline - time.monotonic()
                if left <= 0:
                    break
                self._clock.wait(min(0.05, left))

    def begin_command(self) -> None:
        """Called by SimBody before each tool: reset the per-command feedback (touched props, crash)."""
        self.touched_action, self.crashed = set(), False

    def capture(self, width: int = 512, height: int = 384, camera: str = "front") -> bytes | None:
        """JPEG from the dog's camera, or None. Thread-safe; the frame is rendered by the sim thread.

        """
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
        fallen = self.tilt() > 0.9
        return {
            "x": round(self.x, 2), "y": round(self.y, 2), "yaw_deg": round(math.degrees(wrap(self.yaw))),
            "z": round(self.z, 2), "posture": "caduto" if fallen else self.posture,
            "time_scale": self.time_scale,
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
        with self._clock:
            self._clock.notify_all()

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
                Image.fromarray(renderer.render()).save(buf, format="JPEG", quality=self.jpeg_quality)
                req.jpeg = buf.getvalue()
            except Exception as e:  # never let a camera problem stop the simulator
                req.error = repr(e)
            req.done.set()

    def _advance(self, dt: float) -> None:
        """One frame: read what the (simulated) UDP link carries, run a behaviour or the velocity controller, physics."""
        self.dt = dt
        if self._reset_req:
            self._reset_req = False
            self._gen, self._beh = None, None
            self._init_state()
            self._log("sim_reset")
        with self._lock:
            cmd = dict(self._cmd)
        mode = cmd["mode"]
        edge = mode != self._last_mode
        self._last_mode = mode

        if mode == "DAMPING":  # motors off while this mode is sent; nothing else runs
            if not self._limp:
                self._set_limp(True)
            self._gen, self._beh = None, None
            self.v_cmd = self.w_cmd = 0.0
            self._physics(dt)
            return
        if self._limp:
            self._set_limp(False)

        if self._gen is None and edge and mode in BEHAVIORS:
            self._gen, self._beh = BEHAVIORS[mode](self), mode
            self.touched_action = set(self.touched_action)
            self._log("sim_mode_start", mode=mode)
        if self._gen is not None:  # a behaviour owns the dog until it finishes, whatever is sent meanwhile
            try:
                next(self._gen)
            except StopIteration:
                self._finish()
            except Exception as e:  # a broken behaviour must not kill the simulator
                self._log("sim_behavior_error", mode=self._beh, error=repr(e))
                self._finish()
        else:
            self._velocity_control(cmd["vx"], cmd["vyaw"])
        self._physics(dt)

    def _finish(self) -> None:
        self._log("sim_mode_done", mode=self._beh, fell=self.tilt() > 0.9)
        self._gen, self._beh = None, None
        self.v_cmd = self.w_cmd = 0.0
        self.lift = 0.0

    def _velocity_control(self, vx: float, vyaw: float) -> None:
        """VEL_WALK / IDLE: the trot generator follows (vx, vyaw) open loop, exactly as the dog would."""
        moving = abs(vx) > 1e-6 or abs(vyaw) > 1e-6
        standing = self.posture == "stand" and self.tilt() < 0.7 and self.z > 0.2
        if moving and not standing:  # ASSUMPTION (unverified on the Go1): a velocity from lying / fallen does nothing
            if not self._ignored_vel_logged:
                self._log("sim_velocity_ignored", posture=self.posture, tilt=round(self.tilt(), 2))
                self._ignored_vel_logged = True
            moving = False
        if standing:
            self._ignored_vel_logged = False
        if moving:
            self.set_mode("stand")
            self.v_cmd, self.w_cmd = vx, vyaw
            self._leg_rates[:] = GAIT_RATE
        else:
            self.v_cmd = self.w_cmd = 0.0

    def _set_limp(self, on: bool) -> None:
        """DAMPING: zero the position actuators' stiffness (kp) so the legs go slack; restore it when leaving."""
        m = self.model
        if on:
            m.actuator_gainprm[:, 0] = 0.0
            m.actuator_biasprm[:, 1] = 0.0
            self.set_mode("limp")
            self.posture = "damped"
        else:
            m.actuator_gainprm[:, 0], m.actuator_biasprm[:, 1] = self._gain0
            self.q_des = self.data.qpos[7:19].copy()  # no snap: start from where the legs are
            self.q_goal = self.q_des.copy()
            self.set_mode("pose")
        self._limp = on
        self._log("sim_limp", on=on)

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
        self._vint = np.zeros(2)
        self._cmd.update(vx=0.0, vyaw=0.0, mode="IDLE")
        self._last_mode = "IDLE"
        if self._limp:
            self._set_limp(False)
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
                x, z = -stride / 2 + stride * u, Z_FOOT + SWING_LIFT * math.sin(math.pi * u) ** SWING_SHAPE
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
            err = v_des - d.qvel[0:2]
            self._vint = np.clip(self._vint + err * self.model.opt.timestep, -0.3, 0.3) if self.v_cmd != 0 else self._vint * 0.98
            f = g["v"] * (KV * err + KI * self._vint)
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
