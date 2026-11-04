"""Real-robot camera path end to end, without the robot: scripts/fake_g1_head.py plays the stereo head (UDP discovery on 5601 +
side-by-side H.264 over RTP), RealG1.head_rgbd() must find it, decode both eyes, compute stereo depth and fit the floor.
Only the camera is used: RealG1 is never armed, nothing is sent to any robot. Run: python tests/test_g1_stereo_stream.py"""
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "g1"))
os.environ.setdefault("MUJOCO_GL", "egl")
os.environ["G1_CAMERA_PORT"] = "5610"  # on one machine 5600+1 (RTCP) would collide with the fake head's discovery port 5601

import numpy as np  # noqa: E402

from g1_real import RealG1  # noqa: E402

HEIGHT, PITCH = 1.25, 14.0  # the fake head's camera height (m) and tilt (deg)


def main() -> int:
    head = subprocess.Popen([sys.executable, str(ROOT / "scripts" / "fake_g1_head.py"), "--fps", "8"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    real = RealG1()  # never armed: camera only
    try:
        frame, t0 = None, time.monotonic()
        while time.monotonic() - t0 < 40:
            frame = real.head_rgbd(timeout=3.0)
            if frame is not None and frame.depth is not None:
                frame = real.head_rgbd(timeout=3.0) or frame  # a second one: the first frames after the keyframe can be soft
                break
            time.sleep(0.5)
        if frame is None or frame.depth is None:
            print(f"FAILED: no stereo frame ({real.camera.error})")
            return 1
        cov = np.isfinite(frame.depth).mean()
        print(f"got {frame.source} frame {frame.rgb.shape[1]}x{frame.rgb.shape[0]} after {time.monotonic() - t0:.1f} s, "
              f"depth coverage {cov:.0%}, timings {frame.timings}, stream {real.camera.info}")
        fails = 0
        if cov < 0.3:
            print("FAIL: too little depth")
            fails += 1
        f = frame.floor
        if f is None:
            print("FAIL: floor not found")
            fails += 1
        else:
            ok = abs(f.d - HEIGHT) < 0.08 and abs(f.pitch_deg() - PITCH) < 3
            fails += not ok
            print(f"floor from stereo: camera at {f.d:.3f} m (truth {HEIGHT}), tilt {f.pitch_deg():.1f} deg (truth {PITCH}) {'ok' if ok else 'FAIL'}")
        print("FAILED" if fails else "all ok")
        return 1 if fails else 0
    finally:
        head.kill()


if __name__ == "__main__":
    sys.exit(main())
