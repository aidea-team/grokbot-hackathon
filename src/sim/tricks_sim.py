"""SIMULATION ONLY: Go1 high jump + backflip in the MuJoCo viewer.

    mjpython src/sim/tricks_sim.py            # macOS (viewer needs mjpython)
    python src/sim/tricks_sim.py --slow 3     # Linux/Windows, 3x slow motion

This is a scripted animation, not a physical controller: the trunk follows a ballistic
trajectory (real gravity, constant horizontal speed, one full 360 deg rotation for the flip)
and the legs interpolate crouch -> push -> tuck -> landing. Contacts are not simulated.
It says nothing about whether a real Go1 could do this: BACKFLIP / JUMPYAW are deliberately
NOT exposed by src/dog/driver.py and must stay that way. Real physics would need an RL policy.
"""
from __future__ import annotations

import argparse
import math
import sys
import time
from pathlib import Path

import mujoco
import mujoco.viewer

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dog"))
from driver import JsonlLog  # noqa: E402
from models import model_path  # noqa: E402

G = 9.81
Z_STAND = 0.27
Z_CROUCH = 0.17
STAND = (0.0, 0.9, -1.8)
CROUCH = (0.0, 1.35, -2.6)
PUSH = (0.0, 0.55, -1.25)  # legs extended while pushing off
TUCK = (0.0, 1.45, -2.7)  # legs pulled in flight
VIEWER_DT = 1 / 60


def smooth(s: float) -> float:
    s = min(1.0, max(0.0, s))
    return s * s * (3 - 2 * s)


def lerp(a, b, s):
    return tuple(x + (y - x) * s for x, y in zip(a, b))


class Show:
    def __init__(self, slow: float):
        self.slow = slow
        self.model = mujoco.MjModel.from_xml_path(str(model_path("go1")))
        self.data = mujoco.MjData(self.model)
        mujoco.mj_resetDataKeyframe(self.model, self.data, self.model.key("home").id)
        self.log = JsonlLog()
        self.v = mujoco.viewer.launch_passive(self.model, self.data)
        self.v.cam.type = mujoco.mjtCamera.mjCAMERA_TRACKING
        self.v.cam.trackbodyid = self.model.body("trunk").id
        self.v.cam.distance, self.v.cam.azimuth, self.v.cam.elevation = 3.5, 150, -12
        self.x = 0.0

    def pose(self, x, z, pitch, leg):
        d = self.data
        d.qpos[0], d.qpos[1], d.qpos[2] = x, 0.0, z
        # rotation about +y by `pitch` (negative = nose up and over backwards)
        d.qpos[3:7] = (math.cos(pitch / 2), 0.0, math.sin(pitch / 2), 0.0)
        for i in range(4):
            d.qpos[7 + 3 * i: 10 + 3 * i] = leg
        d.qvel[:] = 0.0
        mujoco.mj_forward(self.model, d)

    def play(self, duration: float, fn) -> bool:
        """Run fn(s in 0..1) -> (x, z, pitch, leg) in wall-clock time. False if window closed."""
        t0 = time.monotonic()
        while (s := (time.monotonic() - t0) / (duration * self.slow)) < 1.0:
            if not self.v.is_running():
                return False
            self.pose(*fn(s))
            self.v.sync()
            time.sleep(VIEWER_DT)
        self.pose(*fn(1.0))
        self.v.sync()
        return True

    def trick(self, name: str, height: float, vx: float, spin: float) -> bool:
        """Crouch, push off, ballistic flight reaching `height` above standing, land, recover.

        vx: horizontal speed in flight (m/s). spin: total pitch in radians (0 = plain jump).
        """
        v0 = math.sqrt(2 * G * height)
        flight = 2 * v0 / G
        x0 = self.x
        self.log.event("sim_trick", name=name, height_m=height, flight_s=round(flight, 3),
                       spin_rad=spin, vx=vx, slow=self.slow)
        print(f"{name}: apex +{height:.2f} m, flight {flight:.2f} s (x{self.slow:g} slow-mo)")

        ok = self.play(0.5, lambda s: (x0, lerp((Z_STAND,), (Z_CROUCH,), smooth(s))[0], 0.0,
                                       lerp(STAND, CROUCH, smooth(s))))
        ok = ok and self.play(0.12, lambda s: (x0, lerp((Z_CROUCH,), (Z_STAND + 0.1,), s)[0], 0.0,
                                               lerp(CROUCH, PUSH, smooth(s))))

        def flight_fn(s):
            t = s * flight
            z = Z_STAND + 0.1 + v0 * t - 0.5 * G * t * t
            # tuck in the first third, extend again to land
            tuck = smooth(s / 0.3) * (1 - smooth((s - 0.75) / 0.25))
            leg = lerp(PUSH, TUCK, tuck) if s < 0.75 else lerp(TUCK, STAND, smooth((s - 0.75) / 0.25))
            return (x0 + vx * t, z, -spin * smooth(min(1.0, s / 0.92)), leg)

        ok = ok and self.play(flight, flight_fn)
        self.x = x0 + vx * flight
        x1 = self.x
        ok = ok and self.play(0.25, lambda s: (x1, lerp((Z_STAND,), (Z_CROUCH,), math.sin(math.pi * s))[0],
                                               0.0, lerp(STAND, CROUCH, math.sin(math.pi * s))))
        return ok and self.play(0.4, lambda s: (x1, Z_STAND, 0.0, STAND))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--slow", type=float, default=2.0, help="slow-motion factor (default 2)")
    ap.add_argument("--jump", type=float, default=1.0, help="jump apex height in m (default 1.0)")
    ap.add_argument("--flip", type=float, default=0.9, help="backflip apex height in m (default 0.9)")
    args = ap.parse_args()

    try:
        show = Show(args.slow)
    except RuntimeError as e:
        raise SystemExit(f"{e}\nOn macOS run this script with `mjpython` instead of `python`.") from e

    time.sleep(1.0)
    try:
        ok = show.trick("high jump", args.jump, 0.3, 0.0)
        time.sleep(0.5)
        ok = ok and show.trick("backflip", args.flip, -0.4, 2 * math.pi)
        if ok:
            print("done: close the viewer window (or Ctrl+C) to exit")
        while show.v.is_running():
            show.v.sync()
            time.sleep(VIEWER_DT)
    except KeyboardInterrupt:
        pass
    show.v.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
