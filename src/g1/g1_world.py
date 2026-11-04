"""G1World: the Unitree G1 humanoid in MuJoCo, driven by Unitree's standard locomotion policy.

Only HIGH-LEVEL commands exist: a velocity (vx, vy, vyaw) plus stop/reset. The 12 leg joints are controlled by the
pretrained policy (g1_policy.py) at 50 Hz exactly like unitree_rl_gym's deploy_mujoco.py; PD torques run at 500 Hz.
Nothing else moves (the upper body is fixed in this model, like in the policy's training).
Physics runs in a background thread at real time and also renders the camera frames (offscreen, JPEG).
"""
from __future__ import annotations

import io
import os
import threading
import time
from pathlib import Path

import numpy as np

os.environ.setdefault("MUJOCO_GL", "cgl" if os.uname().sysname == "Darwin" else "egl")
import mujoco  # noqa: E402
from PIL import Image  # noqa: E402

from g1_policy import LstmPolicy  # noqa: E402

SCENE = Path(__file__).parent / "assets" / "scene.xml"

# From unitree_rl_gym deploy/deploy_mujoco/configs/g1.yaml
KPS = np.array([100, 100, 100, 150, 40, 40] * 2, np.float32)
KDS = np.array([2, 2, 2, 4, 2, 2] * 2, np.float32)
DEFAULT_Q = np.array([-0.1, 0, 0, 0.3, -0.2, 0] * 2, np.float32)
ANG_VEL_SCALE, DOF_VEL_SCALE, ACTION_SCALE = 0.25, 0.05, 0.25
CMD_SCALE = np.array([2.0, 2.0, 0.25], np.float32)
SIM_DT, DECIMATION, GAIT_PERIOD = 0.002, 10, 0.8
# Command envelope of the standard policy (training ranges in unitree_rl_gym g1_config: x [-1,1]... we stay inside)
MAX_VX, MAX_VY, MAX_VYAW = 0.8, 0.4, 1.0
FALLEN_Z = 0.45  # pelvis height below which the robot is considered fallen
CMD_RATE = np.array([1.5, 1.5, 3.0], np.float32)  # command slew (units/s): the policy is trained on smooth commands


def gravity_in_body(quat: np.ndarray) -> np.ndarray:
    qw, qx, qy, qz = quat
    return np.array([2 * (-qz * qx + qw * qy), -2 * (qz * qy + qw * qx), 1 - 2 * (qw * qw + qz * qz)], np.float32)


class G1World:
    def __init__(self, width: int = 800, height: int = 450):
        self.model = mujoco.MjModel.from_xml_path(str(SCENE))
        self.model.opt.timestep = SIM_DT
        self.data = mujoco.MjData(self.model)
        self.policy = LstmPolicy()
        self.width, self.height = width, height
        self._lock = threading.Lock()
        self._cmd = np.zeros(3, np.float32)       # requested (vx, vy, vyaw)
        self._cmd_eff = np.zeros(3, np.float32)   # slewed command fed to the policy
        self._cmd_t = 0.0
        self._reset_flag = True
        self._jpeg: bytes | None = None
        self._frame_n = 0
        self._cond = threading.Condition()
        self._stop = False
        self._last_view = time.monotonic()  # the renderer idles when nobody is watching
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
        c = np.array([np.clip(vx, -MAX_VX, MAX_VX), np.clip(vy, -MAX_VY, MAX_VY), np.clip(vyaw, -MAX_VYAW, MAX_VYAW)], np.float32)
        with self._lock:
            self._cmd, self._cmd_t = c, time.monotonic()

    def stop(self) -> None:
        self.command(0, 0, 0)

    def reset(self) -> None:
        with self._lock:
            self._cmd[:] = 0
            self._reset_flag = True

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
                "sim_time": round(self.sim_time, 1)}

    def frame(self, after: int = -1, timeout: float = 2.0) -> tuple[int, bytes | None]:
        """Latest JPEG; blocks until a frame newer than `after` exists (for MJPEG streaming)."""
        self._last_view = time.monotonic()
        with self._cond:
            self._cond.wait_for(lambda: self._frame_n > after or self._stop, timeout)
            return self._frame_n, self._jpeg

    # ------------------------------------------------------------------ internals
    def _do_reset(self) -> None:
        m, d = self.model, self.data
        mujoco.mj_resetData(m, d)
        d.qpos[2] = 0.793
        d.qpos[7:19] = DEFAULT_Q
        mujoco.mj_forward(m, d)
        self.policy.reset()
        self._action = np.zeros(12, np.float32)
        self._target = DEFAULT_Q.copy()
        self._cmd_eff[:] = 0
        self._counter = 0
        self.sim_time = 0.0
        self.fallen = False
        self._pose = d.qpos.copy()

    def _observe(self) -> np.ndarray:
        d = self.data
        phase = (self._counter * SIM_DT) % GAIT_PERIOD / GAIT_PERIOD
        obs = np.concatenate([
            d.qvel[3:6] * ANG_VEL_SCALE, gravity_in_body(d.qpos[3:7]), self._cmd_eff * CMD_SCALE,
            d.qpos[7:19] - DEFAULT_Q, d.qvel[6:18] * DOF_VEL_SCALE, self._action,
            [np.sin(2 * np.pi * phase), np.cos(2 * np.pi * phase)]]).astype(np.float32)
        return obs

    def _render_loop(self) -> None:
        """Own thread (rendering costs ~50 ms/frame and must not slow the physics): draws a copy of the state."""
        renderer = mujoco.Renderer(self.model, height=self.height, width=self.width)  # GL context lives in this thread
        rd = mujoco.MjData(self.model)
        while not self._stop:
            t = time.monotonic()
            if t - self._last_view > 3.0:  # nobody is looking: do not burn a core
                time.sleep(0.2)
                continue
            rd.qpos[:] = self._pose  # one atomic numpy copy; tearing between two physics steps is invisible
            mujoco.mj_forward(self.model, rd)
            if self.follow:
                self.cam.lookat[:] = rd.qpos[0:3] + np.array([0, 0, -0.1])
            renderer.update_scene(rd, camera=self.cam)
            buf = io.BytesIO()
            Image.fromarray(renderer.render()).save(buf, "JPEG", quality=80)
            with self._cond:
                self._jpeg, self._frame_n = buf.getvalue(), self._frame_n + 1
                self._cond.notify_all()
            time.sleep(max(0.0, 1 / 25 - (time.monotonic() - t)))
        renderer.close()

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
            tau = (self._target - d.qpos[7:19]) * KPS - d.qvel[6:18] * KDS
            d.ctrl[:] = np.clip(tau, -139, 139)  # the largest joint limit (xml actuatorfrcrange clamps each joint)
            mujoco.mj_step(self.model, d)
            self._counter += 1
            steps += 1
            self.sim_time = steps * SIM_DT
            if self._counter % DECIMATION == 0:
                step = CMD_RATE * (SIM_DT * DECIMATION)
                self._cmd_eff += np.clip(want - self._cmd_eff, -step, step)
                if not self.fallen:
                    self._action = self.policy(self._observe())
                    self._target = self._action * ACTION_SCALE + DEFAULT_Q
                if d.qpos[2] < FALLEN_Z and not self.fallen:
                    self.fallen, self.falls = True, self.falls + 1
                    self._target = DEFAULT_Q.copy()
                    self._cmd_eff[:] = 0
            if self._counter % 20 == 0:
                self._pose = self.data.qpos.copy()
            ahead = t0 + steps * SIM_DT - time.monotonic()  # real-time pacing
            if ahead > 0:
                time.sleep(min(ahead, 0.01))
