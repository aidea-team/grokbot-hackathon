"""MuJoCo-backed Go1 driver: same interface as MockDriver, but you SEE the dog in the viewer.

Used by `python src/dog/walk1m.py --sim` (on macOS: `mjpython src/dog/walk1m.py --sim`).

Honest limits: the Menagerie Go1 has no locomotion controller. The trunk pose is integrated
kinematically from the commanded (vx, vyaw), exactly like MockDriver, and the legs play a
procedural trot animation. It is a visualization, NOT a physical gait: don't use it to
measure balance, slip or energy. Contact physics would need an RL walking policy.
"""
from __future__ import annotations

import math
import time

import mujoco
import mujoco.viewer

from driver import JsonlLog, MockDriver
from models import model_path

# Joint order in qpos[7:]: FR, FL, RR, RL x (hip, thigh, calf). Values from the "home" keyframe.
HOME_LEG = (0.0, 0.9, -1.8)
TROT_HZ = 2.5  # steps per second while walking
THIGH_SWING = 0.30  # rad
CALF_LIFT = 0.45  # rad
# Diagonal pairs move together: FR+RL in phase, FL+RR in antiphase.
LEG_PHASE = (0.0, math.pi, math.pi, 0.0)  # FR, FL, RR, RL
VIEWER_DT = 1 / 60


class SimDriver(MockDriver):
    name = "sim"

    def __init__(self, log: JsonlLog):
        super().__init__(log)
        self.model = mujoco.MjModel.from_xml_path(str(model_path("go1")))
        self.data = mujoco.MjData(self.model)
        mujoco.mj_resetDataKeyframe(self.model, self.data, self.model.key("home").id)
        self.viewer = None
        self._phase = 0.0
        self._gait = 0.0  # 0 = standing, 1 = full trot (eased so legs return smoothly)
        self._last_sync = 0.0

    def connect(self) -> dict:
        try:
            self.viewer = mujoco.viewer.launch_passive(self.model, self.data)
        except RuntimeError as e:
            raise SystemExit(f"{e}\nOn macOS run this script with `mjpython` instead of `python`.") from e
        self.viewer.cam.type = mujoco.mjtCamera.mjCAMERA_TRACKING
        self.viewer.cam.trackbodyid = self.model.body("trunk").id
        self.viewer.cam.distance, self.viewer.cam.azimuth, self.viewer.cam.elevation = 2.2, 140, -20
        info = {"model": "Go1 (MuJoCo, kinematic)", "soc": 100}
        self.log.event("connect", driver=self.name, **info)
        self._render()
        return info

    def _pose_to_qpos(self, moving: bool, dt: float, speed: float) -> None:
        d = self.data
        self._gait += ((1.0 if moving else 0.0) - self._gait) * min(1.0, dt * 8)
        if moving:
            # Faster walking = faster stepping (5 Hz at the 0.4 m/s cap).
            self._phase += 2 * math.pi * max(TROT_HZ, 12.5 * abs(speed)) * dt
        d.qpos[0], d.qpos[1] = self.x, self.y
        d.qpos[3:7] = (math.cos(self.yaw / 2), 0.0, 0.0, math.sin(self.yaw / 2))  # wxyz, yaw only
        for i, off in enumerate(LEG_PHASE):
            s = math.sin(self._phase + off)
            hip, thigh, calf = HOME_LEG
            d.qpos[7 + 3 * i: 10 + 3 * i] = (
                hip,
                thigh + self._gait * THIGH_SWING * s,
                calf + self._gait * CALF_LIFT * max(0.0, math.cos(self._phase + off)),
            )
        d.qvel[:] = 0.0
        mujoco.mj_forward(self.model, d)

    def _step(self, vx: float, vyaw: float) -> None:
        before = time.monotonic()
        # Clamp dt: the first call after connect()/idle would otherwise integrate the whole
        # time since the viewer opened and make the dog jump ahead.
        self._last = max(self._last, before - 0.05)
        dt = before - self._last
        super()._integrate(vx, vyaw)
        self._pose_to_qpos(vx != 0.0 or vyaw != 0.0, dt, vx)
        if before - self._last_sync >= VIEWER_DT:
            self._render()
            self._last_sync = before

    def _render(self) -> None:
        if self.viewer is not None and self.viewer.is_running():
            self.viewer.sync()
        elif self.viewer is not None:
            self.halt()  # closing the window is a kill switch too

    def _send_velocity(self, vx: float, vyaw: float) -> None:
        self._step(vx, vyaw)

    def _send_idle(self) -> None:
        self._step(0.0, 0.0)

    def close(self) -> None:
        super().close()
        if self.viewer is not None and self.viewer.is_running():
            print("walk finished: close the viewer window (or Ctrl+C) to exit")
            try:
                while self.viewer.is_running():
                    self.viewer.sync()
                    time.sleep(VIEWER_DT)
            except KeyboardInterrupt:
                pass
        if self.viewer is not None:
            self.viewer.close()
