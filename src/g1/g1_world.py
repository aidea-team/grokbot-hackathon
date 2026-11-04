"""G1World: the Unitree G1 humanoid (29 DoF) in MuJoCo.

Legs: Unitree's standard locomotion policy (g1_policy.py) driven by HIGH-LEVEL velocity commands (vx, vy, vyaw), at
50 Hz exactly like unitree_rl_gym's deploy_mujoco.py, PD torques at 500 Hz.
Waist + arms (17 joints): PD position control around targets that a human (or later the agent) sets: jog a joint
(IJKL...), set a pose, or play a preset. The policy knows nothing about the arms: it just sees their effect on the
body like it would on the real robot.
Physics runs in a background thread at real time; rendering (orbit view + head camera) has its own thread.
"""
from __future__ import annotations

import io
import os
import sys
import threading
import time
from pathlib import Path

import numpy as np

os.environ.setdefault("MUJOCO_GL", "cgl" if os.uname().sysname == "Darwin" else "egl")
import mujoco  # noqa: E402
from PIL import Image  # noqa: E402

from g1_policy import LstmPolicy  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "vision"))
from rgbd import RGBD, Floor, Intrinsics  # noqa: E402

SCENE = Path(__file__).parent / "assets" / "scene.xml"
# "default": two coloured cylinders 4 m ahead (chat/camera tests). "desk": an office corner (desk, monitor, keyboard, chair) for perception.
SCENES = {"default": SCENE, "desk": Path(__file__).parent / "assets" / "scene_desk.xml"}

# Two interchangeable leg/whole-body controllers (both Unitree's, both in the simulator only):
#   "gym12": unitree_rl_gym motion.pt, 12 leg joints, arms/waist held by PD at our targets (jog, gestures work); arms forward at ~90 deg
#   "lab29": unitree_rl_lab velocity/v0 (onnx), ALL 29 joints driven by the policy (arms near its default pose, elbows ~55 deg);
#            no jog/gestures here (the policy owns the arms); command ranges x [-0.5, 1], y +-0.3, yaw +-0.2
CONTROLLERS = {"gym12": "unitree_rl_gym · 12 giunti, braccia a 90° (le muovi tu)", "lab29": "unitree_rl_lab · 29 giunti, braccia della policy"}

# Legs: from unitree_rl_gym deploy/deploy_mujoco/configs/g1.yaml
KPS = np.array([100, 100, 100, 150, 40, 40] * 2, np.float32)
KDS = np.array([2, 2, 2, 4, 2, 2] * 2, np.float32)
DEFAULT_Q = np.array([-0.1, 0, 0, 0.3, -0.2, 0] * 2, np.float32)
ANG_VEL_SCALE, DOF_VEL_SCALE, ACTION_SCALE = 0.25, 0.05, 0.25
CMD_SCALE = np.array([2.0, 2.0, 0.25], np.float32)
SIM_DT, DECIMATION, GAIT_PERIOD = 0.002, 10, 0.8
MAX_VX, MAX_VY, MAX_VYAW = 1.0, 0.4, 1.0  # command envelope of the standard policy (training range is [-1, 1])
FALLEN_Z = 0.45  # pelvis height below which the robot is considered fallen
CMD_RATE = np.array([1.5, 1.5, 3.0], np.float32)  # command slew (units/s): the policy is trained on smooth commands

# Waist + arms: qpos[19:36] / qvel[18:35] / ctrl[12:29]
UPPER = [
    "waist_yaw", "waist_roll", "waist_pitch",
    "left_shoulder_pitch", "left_shoulder_roll", "left_shoulder_yaw", "left_elbow",
    "left_wrist_roll", "left_wrist_pitch", "left_wrist_yaw",
    "right_shoulder_pitch", "right_shoulder_roll", "right_shoulder_yaw", "right_elbow",
    "right_wrist_roll", "right_wrist_pitch", "right_wrist_yaw",
]
UPPER_KP = np.array([200, 200, 200] + [40, 40, 40, 40, 20, 15, 15] * 2, np.float32)
UPPER_KD = np.array([5, 5, 5] + [1.5, 1.5, 1.5, 1.5, 0.8, 0.5, 0.5] * 2, np.float32)
UPPER_SLEW = 1.5  # rad/s: how fast the arm target moves toward a goal (presets, sliders)
JOG_RATE = 1.0    # rad/s at full key press
# The real G1 locks waist roll/pitch in most firmware modes and the policy was not trained with them: held at 0
LOCKED = {"waist_roll", "waist_pitch"}
UPPER_IDX = {n: i for i, n in enumerate(UPPER)}

# Presets: name -> list of (pose, hold_seconds). Poses are {joint: radians}; missing joints go to 0 (rest).
# Same names as the G1's own arm-action service (G1ArmActionClient) where the motion is simple; see README.
def _both(name: str, v: float, mirror: bool = False) -> dict:
    return {f"left_{name}": v, f"right_{name}": -v if mirror else v}


def _side(side: str, **kw) -> dict:
    """Pose of one arm: _side("right", shoulder_pitch=-1.5). Roll/yaw are given for the LEFT arm; mirrored for the right."""
    mir = {"shoulder_roll", "shoulder_yaw", "wrist_roll", "wrist_yaw"}
    return {f"{side}_{k}": (-v if side == "right" and k in mir else v) for k, v in kw.items()}


def _wiggle(base: dict, joint: str, amp: float, n: int = 5, dt: float = 0.35) -> list[tuple[dict, float]]:
    return [({**base, joint: amp * (1 if i % 2 == 0 else -1)}, dt) for i in range(n)]


_R = {"right_shoulder_pitch": -2.2, "right_shoulder_roll": -0.4, "right_elbow": 0.4}
_HEART = {"shoulder_pitch": -1.8, "elbow": 1.5, "shoulder_roll": -0.1, "shoulder_yaw": 0.0}
# Unitree arm-action ids (G1ArmActionClient.ExecuteAction), unitree_sdk2_python g1_arm_action_client.py
ARM_ACTION_IDS = {"release_arm": 99, "two_hand_kiss": 11, "left_kiss": 12, "right_kiss": 13, "hands_up": 15, "clap": 17,
                  "high_five": 18, "hug": 19, "heart": 20, "right_heart": 21, "reject": 22, "right_hand_up": 23,
                  "x_ray": 24, "face_wave": 25, "high_wave": 26, "shake_hand": 27}
# Presets: name -> list of (pose, hold_seconds). Poses are {joint: radians}; missing joints go to 0 (rest). These are OUR
# approximations of the robot's built-in motions (the real ones are recorded by Unitree and played by the robot).
PRESETS: dict[str, list[tuple[dict, float]]] = {
    "release_arm": [({}, 0.5)],
    "two_hand_kiss": [({**_side("left", shoulder_pitch=-1.4, elbow=1.9), **_side("right", shoulder_pitch=-1.4, elbow=1.9)}, 1.5), ({}, 0.0)],
    "left_kiss": [(_side("left", shoulder_pitch=-1.4, elbow=1.9), 1.5), ({}, 0.0)],
    "right_kiss": [(_side("right", shoulder_pitch=-1.4, elbow=1.9), 1.5), ({}, 0.0)],
    "hands_up": [({**_both("shoulder_pitch", -2.6), **_both("shoulder_roll", 0.25, True)}, 1.5), ({}, 0.0)],
    "clap": [({**_both("shoulder_pitch", -1.1), **_both("elbow", 0.9), **_both("shoulder_roll", 0.05, True)}, 0.8)]
            + [({**_both("shoulder_pitch", -1.1), **_both("elbow", 0.9), **_both("shoulder_roll", s_, True)}, 0.25)
               for s_ in (-0.25, 0.1, -0.25, 0.1, -0.25)] + [({}, 0.0)],
    "high_five": [(_side("right", shoulder_pitch=-1.9, shoulder_roll=0.15, elbow=0.2), 2.0), ({}, 0.0)],
    "hug": [({**_both("shoulder_pitch", -0.7), **_both("shoulder_roll", 0.8, True), **_both("elbow", 0.5)}, 1.0),
            ({**_both("shoulder_pitch", -0.7), **_both("shoulder_roll", -0.1, True), **_both("shoulder_yaw", 0.6, True),
              **_both("elbow", 1.0)}, 1.5), ({}, 0.0)],
    "heart": [({**_side("left", **_HEART), **_side("right", **_HEART)}, 2.0), ({}, 0.0)],
    "right_heart": [(_side("right", **_HEART), 2.0), ({}, 0.0)],
    "reject": [({**_both("shoulder_pitch", -0.7), **_both("elbow", 0.9)}, 0.6)]
              + [({**_both("shoulder_pitch", -0.7), **_both("elbow", 0.9), **_both("shoulder_yaw", y, True)}, 0.3)
                 for y in (0.6, -0.6, 0.6, -0.6)] + [({}, 0.0)],
    "right_hand_up": [({"right_shoulder_pitch": -2.6, "right_shoulder_roll": -0.25}, 1.5), ({}, 0.0)],
    "x_ray": [({**_both("shoulder_pitch", -2.3), **_both("shoulder_roll", 0.9, True)}, 2.0), ({}, 0.0)],
    "face_wave": [(_side("right", shoulder_pitch=-1.7, elbow=1.8), 0.6)]
                 + _wiggle(_side("right", shoulder_pitch=-1.7, elbow=1.8), "right_wrist_roll", 0.9) + [({}, 0.0)],
    "high_wave": [(_R, 0.8)] + _wiggle(_R, "right_shoulder_yaw", 0.5) + [({}, 0.0)],
    "shake_hand": [(_side("right", shoulder_pitch=-0.9, elbow=0.4), 1.0)]
                 + _wiggle(_side("right", shoulder_pitch=-0.9, elbow=0.4), "right_elbow", 0.2, 6, 0.3) + [({}, 0.0)],
}
# SDK LocoClient.WaveHand()/ShakeHand() are the robot's own wave / handshake task: same motions here
PRESETS["wave_hand"] = PRESETS["high_wave"]
SIM_BY_ID = {i: n for n, i in ARM_ACTION_IDS.items()}  # the robot names its actions differently (e.g. blow_kiss_with_both_hands = 11): match by id


def gravity_in_body(quat: np.ndarray) -> np.ndarray:
    qw, qx, qy, qz = quat
    return np.array([2 * (-qz * qx + qw * qy), -2 * (qz * qy + qw * qx), 1 - 2 * (qw * qw + qz * qz)], np.float32)


class G1World:
    def __init__(self, width: int = 800, height: int = 450, head_size: tuple[int, int] = (640, 360), controller: str = "gym12",
                 scene: str = "default"):
        if scene not in SCENES:
            raise ValueError(f"scene {scene!r}: choose from {sorted(SCENES)}")
        self.scene = scene
        self.model = mujoco.MjModel.from_xml_path(str(SCENES[scene]))
        self.model.opt.timestep = SIM_DT
        self.data = mujoco.MjData(self.model)
        self.policy = LstmPolicy()
        if controller not in CONTROLLERS:
            raise ValueError(f"controller {controller!r}: choose from {sorted(CONTROLLERS)}")
        self.controller = controller
        self._pending_controller: str | None = None
        self._robot_ids: dict[str, int] = {}  # robot action name -> id, set by the app from the robot's own list
        self._lab = None  # LabPolicy, loaded the first time lab29 is selected (needs onnxruntime)
        self._target29 = np.zeros(29, np.float32)
        self.width, self.height, self.head_size = width, height, head_size
        # joint limits of the upper body, in UPPER order
        self._lo = np.zeros(len(UPPER), np.float32)
        self._hi = np.zeros(len(UPPER), np.float32)
        for i, n in enumerate(UPPER):
            r = self.model.joint(n + "_joint").range
            self._lo[i], self._hi[i] = r
        # torque limit per actuator (= per joint, same order as ctrl): the xml's actuatorfrcrange
        self._frc = self.model.jnt_actfrcrange[self.model.actuator_trnid[:, 0], 1].astype(np.float32)
        self._lock = threading.Lock()
        self._cmd = np.zeros(3, np.float32)       # requested (vx, vy, vyaw)
        self._cmd_eff = np.zeros(3, np.float32)   # slewed command fed to the policy
        self._cmd_t = 0.0
        self._jog = np.zeros(len(UPPER), np.float32)  # joint velocity request, fraction of JOG_RATE in [-1, 1]
        self._jog_t = 0.0
        self._goal = np.zeros(len(UPPER), np.float32)    # where the arm target is heading (sliders / presets)
        self._utarget = np.zeros(len(UPPER), np.float32)  # the position target actually given to the PD
        self._seq: list[tuple[np.ndarray, float]] = []
        self._seq_name: str | None = None
        self._seq_until = 0.0
        self._reset_flag = True
        self._damped = False
        self._jpeg: dict[str, bytes | None] = {"view": None, "head": None}
        self._frame_n = {"view": 0, "head": 0}
        self._rgbd: RGBD | None = None  # head RGB + exact depth, rendered only when someone asks (head_rgbd)
        self._rgbd_n = 0
        self._rgbd_req = False
        self._cond = threading.Condition()
        self._stop = False
        self._last_view = {"view": time.monotonic(), "head": 0.0}  # a renderer idles when nobody is watching it
        self._thread: threading.Thread | None = None
        self._pose = np.zeros(self.model.nq)
        self.sim_time = 0.0
        self.fallen = False
        self.falls = 0
        self.cam = mujoco.MjvCamera()
        self.cam.type, self.cam.distance, self.cam.azimuth, self.cam.elevation = mujoco.mjtCamera.mjCAMERA_FREE, 3.0, 145.0, -15.0
        self.follow = True

    # ------------------------------------------------------------------ public API (thread-safe)
    def start(self) -> None:
        if self._thread is None:
            self._thread = threading.Thread(target=self._run, daemon=True, name="g1-world")
            self._thread.start()

    def shutdown(self) -> None:
        self._stop = True
        if self._thread:
            self._thread.join(timeout=3)

    def command(self, vx: float, vy: float, vyaw: float) -> None:
        """High-level velocity command (m/s, m/s, rad/s), clipped to the policy's envelope. Valid for 0.4 s (watchdog)."""
        lo, hi = self.limits()
        c = np.clip(np.array([vx, vy, vyaw], np.float32), lo, hi)
        with self._lock:
            self._cmd, self._cmd_t = c, time.monotonic()

    def limits(self) -> tuple[np.ndarray, np.ndarray]:
        """(low, high) of (vx, vy, vyaw) for the selected controller."""
        if self.controller == "lab29":
            from g1_policy_lab import CMD_LIMITS
            return CMD_LIMITS
        return np.array([-MAX_VX, -MAX_VY, -MAX_VYAW], np.float32), np.array([MAX_VX, MAX_VY, MAX_VYAW], np.float32)

    def set_controller(self, name: str) -> bool:
        """Switch the walking controller (the robot is put back on its feet with the new one)."""
        if name not in CONTROLLERS:
            return False
        with self._lock:
            self._pending_controller = name
            self._cmd[:] = 0
            self._reset_flag = True
        return True

    def stop(self) -> None:
        """Stop walking AND freeze the arms where they are (cancels a preset in progress)."""
        self.command(0, 0, 0)
        with self._lock:
            self._jog[:] = 0
            self._seq, self._seq_name = [], None
            self._goal = self._utarget.copy()

    def jog(self, rates: dict[str, float]) -> None:
        """Move upper-body joints at `rate` (-1..1 of 1 rad/s) while this is repeated (0.4 s watchdog). Keys: UPPER names."""
        if self.controller == "lab29":
            return False  # the policy owns the arms
        j = np.zeros(len(UPPER), np.float32)
        for n, r in rates.items():
            if n in UPPER_IDX and n not in LOCKED:
                j[UPPER_IDX[n]] = float(np.clip(r, -1, 1))
        with self._lock:
            self._jog, self._jog_t = j, time.monotonic()
            if j.any():
                self._seq, self._seq_name = [], None
                self._goal = self._utarget.copy()

    def set_pose(self, pose: dict[str, float]) -> None:
        """Send joints (radians, clipped to their limits) toward `pose`; the others keep their target."""
        if self.controller == "lab29":
            return False
        with self._lock:
            self._seq, self._seq_name = [], None
            g = self._goal.copy()
            for n, v in pose.items():
                if n in UPPER_IDX and n not in LOCKED:
                    i = UPPER_IDX[n]
                    g[i] = np.clip(v, self._lo[i], self._hi[i])
            self._goal = g

    def play(self, name: str) -> bool:
        name = name if name in PRESETS else next((n for n in (SIM_BY_ID.get(self._robot_ids.get(name)),) if n), name)
        if self.controller == "lab29":
            return False  # gestures are keyframes on our PD arms; with lab29 the policy owns them
        if name not in PRESETS:
            return False
        steps = []
        for pose, hold in PRESETS[name]:
            g = np.zeros(len(UPPER), np.float32)
            for n, v in pose.items():
                g[UPPER_IDX[n]] = np.clip(v, self._lo[UPPER_IDX[n]], self._hi[UPPER_IDX[n]])
            steps.append((g, hold))
        with self._lock:
            self._seq, self._seq_name, self._seq_until = steps, name, 0.0
        return True

    def set_fsm(self, fsm_id: int) -> dict | bool:
        """FSM request as the real robot's LocoClient.SetFsmId: only what the simulator can show (1 = Damp, 500/501 = on its feet)."""
        if fsm_id == 1:
            self.damp()
        elif fsm_id in (500, 501):
            self.reset()
        else:
            return False
        return {"requested": fsm_id, "fsm": fsm_id, "changed": True}

    def stand_height(self, high: bool) -> bool:
        return False  # not simulated (the open policy has one fixed height)

    def balance_mode(self, mode: int) -> bool:
        return False  # not simulated

    def reset(self) -> None:
        """LocoClient.Start()/StandUp: stand up again (here the robot is simply put back on its feet)."""
        with self._lock:
            self._cmd[:] = 0
            self._reset_flag = True

    def damp(self) -> None:
        """LocoClient.Damp()/ZeroTorque(): all motors go limp (the robot collapses) until reset()."""
        with self._lock:
            self._cmd[:] = 0
            self._seq, self._seq_name = [], None
            self._damped = True

    def set_orbit(self, azimuth: float | None = None, distance: float | None = None, elevation: float | None = None) -> None:
        if azimuth is not None:
            self.cam.azimuth = azimuth
        if distance is not None:
            self.cam.distance = float(np.clip(distance, 1.0, 10.0))
        if elevation is not None:
            self.cam.elevation = float(np.clip(elevation, -85, 0))

    def snapshot(self) -> dict:
        d = self.data
        yaw = float(np.degrees(np.arctan2(2 * (d.qpos[3] * d.qpos[6] + d.qpos[4] * d.qpos[5]),
                                          1 - 2 * (d.qpos[5] ** 2 + d.qpos[6] ** 2))))
        return {"robot": "g1", "x": round(float(d.qpos[0]), 3), "y": round(float(d.qpos[1]), 3), "z": round(float(d.qpos[2]), 3),
                "yaw_deg": round(yaw, 1), "vx": round(float(self._cmd_eff[0]), 2), "vy": round(float(self._cmd_eff[1]), 2),
                "vyaw": round(float(self._cmd_eff[2]), 2), "fallen": self.fallen, "falls": self.falls,
                "sim_time": round(self.sim_time, 1), "preset": self._seq_name, "damped": self._damped,
                "controller": self.controller, "controllers": CONTROLLERS,
                "arms": {n: round(float(self._utarget[i]), 2) for i, n in enumerate(UPPER) if n not in LOCKED},
                "arm_limits": {n: [round(float(self._lo[i]), 2), round(float(self._hi[i]), 2)]
                               for i, n in enumerate(UPPER) if n not in LOCKED}}

    def frame(self, after: int = -1, timeout: float = 2.0, view: str = "view") -> tuple[int, bytes | None]:
        """Latest JPEG of `view` ("view" = orbit camera, "head" = the robot's head camera); blocks until one newer than
        `after` exists (for MJPEG streaming)."""
        self._last_view[view] = time.monotonic()
        with self._cond:
            self._cond.wait_for(lambda: self._frame_n[view] > after or self._stop, timeout)
            return self._frame_n[view], self._jpeg[view]

    def gesture_names(self) -> list[str]:
        """Gestures the simulator can show (our keyframe approximations)."""
        return [n for n in PRESETS if n != "release_arm"]

    def is_busy(self) -> bool:
        """A preset (arm action) is still playing."""
        return bool(self._seq or self._seq_name)

    def head_jpeg(self, timeout: float = 3.0) -> bytes | None:
        """One fresh frame of the head camera (what the agent will look through)."""
        n, _ = self.frame(-1, 0.1, "head")
        return self.frame(n, timeout, "head")[1]

    def head_rgbd(self, timeout: float = 5.0) -> RGBD | None:
        """Head camera RGB + exact metric depth from the SAME physics state, with the floor plane known from the camera pose.
        Rendered on request (the depth pass costs ~60 ms at 640x360), so it costs nothing when perception is off."""
        self._last_view["head"] = time.monotonic()  # wakes the renderer up
        with self._cond:
            n = self._rgbd_n
            self._rgbd_req = True
            self._cond.wait_for(lambda: self._rgbd_n > n or self._stop, timeout)
            return self._rgbd if self._rgbd_n > n else None

    # ------------------------------------------------------------------ internals
    def _do_reset(self) -> None:
        m, d = self.model, self.data
        if self._pending_controller is not None:
            self.controller, self._pending_controller = self._pending_controller, None
        mujoco.mj_resetData(m, d)
        d.qpos[2] = 0.793
        if self.controller == "lab29":
            if self._lab is None:
                from g1_policy_lab import LabPolicy
                self._lab = LabPolicy()
            self._lab.reset()
            self._target29 = self._lab.default_targets()
            d.qpos[7:36] = self._target29  # arms and waist start in the policy's own default pose
        else:
            d.qpos[7:19] = DEFAULT_Q
        mujoco.mj_forward(m, d)
        self.policy.reset()
        self._action = np.zeros(12, np.float32)
        self._target = DEFAULT_Q.copy()
        self._cmd_eff[:] = 0
        self._goal[:] = 0
        self._utarget[:] = 0
        self._seq, self._seq_name = [], None
        self._counter = 0
        self.sim_time = 0.0
        self.fallen = False
        self._damped = False
        self._pose = d.qpos.copy()

    def _observe(self) -> np.ndarray:
        d = self.data
        phase = (self._counter * SIM_DT) % GAIT_PERIOD / GAIT_PERIOD
        return np.concatenate([
            d.qvel[3:6] * ANG_VEL_SCALE, gravity_in_body(d.qpos[3:7]), self._cmd_eff * CMD_SCALE,
            d.qpos[7:19] - DEFAULT_Q, d.qvel[6:18] * DOF_VEL_SCALE, self._action,
            [np.sin(2 * np.pi * phase), np.cos(2 * np.pi * phase)]]).astype(np.float32)

    def _publish(self, view: str, rgb: np.ndarray) -> None:
        buf = io.BytesIO()
        Image.fromarray(rgb).save(buf, "JPEG", quality=80)
        with self._cond:
            self._jpeg[view], self._frame_n[view] = buf.getvalue(), self._frame_n[view] + 1
            self._cond.notify_all()

    def _render_loop(self) -> None:
        """Own thread (rendering costs ~50 ms/frame and must not slow the physics): draws a copy of the state."""
        r_view = mujoco.Renderer(self.model, height=self.height, width=self.width)  # GL context lives in this thread
        r_head = mujoco.Renderer(self.model, height=self.head_size[1], width=self.head_size[0])
        r_depth = None  # created the first time perception asks for depth
        rd = mujoco.MjData(self.model)
        while not self._stop:
            t = time.monotonic()
            want_view, want_head = t - self._last_view["view"] < 3.0, t - self._last_view["head"] < 3.0
            if not (want_view or want_head):  # nobody is looking: do not burn a core
                time.sleep(0.2)
                continue
            rd.qpos[:] = self._pose  # one atomic numpy copy; tearing between two physics steps is invisible
            mujoco.mj_forward(self.model, rd)
            if want_view:
                if self.follow:
                    self.cam.lookat[:] = rd.qpos[0:3] + np.array([0, 0, -0.1])
                r_view.update_scene(rd, camera=self.cam)
                self._publish("view", r_view.render())
            if want_head:
                r_head.update_scene(rd, camera="head_cam")
                rgb = r_head.render()
                self._publish("head", rgb)
                if self._rgbd_req:
                    if r_depth is None:
                        r_depth = mujoco.Renderer(self.model, height=self.head_size[1], width=self.head_size[0])
                        r_depth.enable_depth_rendering()
                    self._publish_rgbd(rgb, r_depth, rd, t)
            time.sleep(max(0.0, 1 / 25 - (time.monotonic() - t)))
        r_view.close()
        r_head.close()
        if r_depth is not None:
            r_depth.close()

    def _publish_rgbd(self, rgb: np.ndarray, r_depth: "mujoco.Renderer", rd: "mujoco.MjData", t: float) -> None:
        t0 = time.perf_counter()
        r_depth.update_scene(rd, camera="head_cam")
        z = r_depth.render().astype(np.float32)
        far = self.model.vis.map.zfar * self.model.stat.extent
        z[z >= 0.99 * far] = np.nan  # sky / nothing hit
        cid = self.model.camera("head_cam").id
        R = rd.cam_xmat[cid].reshape(3, 3)  # columns: camera axes (x right, y up, z backward) in the world
        up = np.array([R[2, 0], -R[2, 1], -R[2, 2]])  # world up in OpenCV camera axes (y down, z forward)
        w, h = self.head_size
        frame = RGBD(rgb.copy(), z, Intrinsics.from_fovy(float(self.model.cam_fovy[cid]), w, h),
                     Floor(up, float(rd.cam_xpos[cid][2]), "sim"), t, "sim", self._rgbd_n + 1,
                     {"depth_ms": round((time.perf_counter() - t0) * 1000, 1)})
        with self._cond:
            self._rgbd, self._rgbd_n, self._rgbd_req = frame, self._rgbd_n + 1, False
            self._rgbd_pose = rd.qpos.copy()  # the exact state of that frame (tests rebuild ground-truth masks from it)
            self._cond.notify_all()

    def _step_upper(self, dt: float, now: float) -> None:
        """Called once per control tick (50 Hz): advance jog / preset and move the target toward the goal."""
        with self._lock:
            if now - self._jog_t < 0.4 and self._jog.any():
                self._goal = np.clip(self._goal + self._jog * JOG_RATE * dt, self._lo, self._hi)
                self._goal[[UPPER_IDX[n] for n in LOCKED]] = 0
            elif self._seq and now >= self._seq_until:
                g, hold = self._seq.pop(0)
                self._goal, self._seq_until = g, now + hold + np.max(np.abs(g - self._utarget)) / UPPER_SLEW
            if not self._seq and self._seq_name and now >= self._seq_until:
                self._seq_name = None
            goal = self._goal
        step = UPPER_SLEW * dt
        self._utarget += np.clip(goal - self._utarget, -step, step)

    def _run(self) -> None:
        self._do_reset()
        threading.Thread(target=self._render_loop, daemon=True, name="g1-render").start()
        t0, steps = time.monotonic(), 0
        while not self._stop:
            with self._lock:
                if self._reset_flag:
                    self._reset_flag = False
                    self._do_reset()
                    t0, steps = time.monotonic(), 0
                fresh = time.monotonic() - self._cmd_t < 0.4
                want = self._cmd.copy() if fresh else np.zeros(3, np.float32)
            d = self.data
            tau = np.empty(29, np.float32)
            if self.controller == "lab29":
                from g1_policy_lab import DAMPING, STIFFNESS
                tau[:] = (self._target29 - d.qpos[7:36]) * STIFFNESS - d.qvel[6:35] * DAMPING
            else:
                tau[:12] = (self._target - d.qpos[7:19]) * KPS - d.qvel[6:18] * KDS
                tau[12:] = (self._utarget - d.qpos[19:36]) * UPPER_KP - d.qvel[18:35] * UPPER_KD
            if self._damped:  # limp: only the joint damping Unitree's damp mode gives (kp 0, kd 2)
                tau[:] = -2.0 * d.qvel[6:35]
            d.ctrl[:] = np.clip(tau, -self._frc, self._frc)
            mujoco.mj_step(self.model, d)
            self._counter += 1
            steps += 1
            self.sim_time = steps * SIM_DT
            if self._counter % DECIMATION == 0:
                step = CMD_RATE * (SIM_DT * DECIMATION)
                self._cmd_eff += np.clip(want - self._cmd_eff, -step, step)
                if self.controller == "lab29":
                    if not self.fallen and not self._damped:
                        obs = self._lab.observe(d.qvel[3:6], gravity_in_body(d.qpos[3:7]), self._cmd_eff, d.qpos[7:36], d.qvel[6:35])  # upright = (0, 0, -1)
                        self._target29 = self._lab.targets(self._lab.act(obs))
                else:
                    self._step_upper(SIM_DT * DECIMATION, time.monotonic())
                    if not self.fallen and not self._damped:
                        self._action = self.policy(self._observe())
                        self._target = self._action * ACTION_SCALE + DEFAULT_Q
                if d.qpos[2] < FALLEN_Z and not self.fallen:
                    self.fallen, self.falls = True, self.falls + 1
                    self._target = DEFAULT_Q.copy()
                    if self.controller == "lab29":
                        self._target29 = self._lab.default_targets()
                    self._cmd_eff[:] = 0
            if self._counter % 20 == 0:
                self._pose = self.data.qpos.copy()
            ahead = t0 + steps * SIM_DT - time.monotonic()  # real-time pacing
            if ahead > 0:
                time.sleep(min(ahead, 0.01))
