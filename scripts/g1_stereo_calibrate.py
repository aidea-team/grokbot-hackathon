"""Calibrate the G1 head's stereo with a tape measure (about 15 minutes, no checkerboard) -> src/g1/stereo_calib.json.

Put a flat target with some texture (a box, a poster, a person) in the CENTRE of the image at 4-6 distances between 0.7 and 4 m,
measured with a tape from the lenses along the optical axis. For each one type the distance in metres + ENTER: the script takes
the median disparity of the central patch over a few frames. With 3+ points it fits z = k / (d - d0), which absorbs the unknown
focal length, baseline and toe-in of the module, prints the error of each point and saves the file. The vertical shift between the
eyes and whether the halves are swapped are estimated from the images.

  python scripts/g1_stereo_calibrate.py           # the real head (UDP discovery, like the app); only the camera is used
Then restart the G1 app: the depth label changes from "stereo (non calibrato)" to "stereo".
"""
from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "g1"))
sys.path.insert(0, str(ROOT / "src" / "vision"))
from g1_real import _Camera  # noqa: E402
from stereo import StereoCalib, StereoDepth  # noqa: E402


def central_disparity(cam: _Camera, stereo: StereoDepth, frames: int = 8) -> tuple[float, float] | None:
    """Median disparity (px) of the central 12% patch over `frames` frames, and its spread (IQR)."""
    vals, n = [], -1
    for _ in range(frames):
        n, pair = cam.get_pair(n, 3.0)
        if pair is None:
            return None
        _, disp, _, _, _ = stereo.disparity(pair[0], pair[1])
        h, w = disp.shape
        patch = disp[int(h * 0.44):int(h * 0.56), int(w * 0.44):int(w * 0.56)]
        good = patch[patch > 0.5]
        if good.size > 0.3 * patch.size:
            vals.append(np.median(good))
    if len(vals) < frames // 2:
        return None
    return float(np.median(vals)), float(np.subtract(*np.percentile(vals, [75, 25])))


def main() -> int:
    cam = _Camera()
    keep = threading.Event()

    def keepalive() -> None:  # the reader stops 5 s after the last request: keep it running while you type
        while not keep.wait(1.0):
            cam.get(-1, 0.0)
    threading.Thread(target=keepalive, daemon=True).start()
    calib = StereoCalib.load()
    calib.kind, calib.k, calib.d0, calib.dy_px, calib.swap = "simple", None, 0.0, None, None  # measured again below
    stereo = StereoDepth(calib)
    print("waiting for the stereo head ...")
    n, pair = cam.get_pair(-1, 20.0)
    if pair is None:
        print(f"no stereo stream: {cam.error}")
        return 1
    stereo.disparity(pair[0], pair[1])  # estimates swap and the vertical shift on this frame
    calib.size = (pair[0].shape[1], pair[0].shape[0])
    print(f"stream ok: {calib.size[0]}x{calib.size[1]} per eye, halves {'SWAPPED' if calib.swap else 'in order'}, "
          f"vertical shift {calib.dy_px if calib.dy_px is not None else 'not found (little texture)'} px")
    pts = []
    while True:
        s = input("distance of the central target in metres (empty = fit and save): ").strip().replace(",", ".")
        if not s:
            break
        try:
            z = float(s)
        except ValueError:
            continue
        r = central_disparity(cam, stereo)
        if r is None:
            print("  no reliable disparity in the centre: more texture, or closer than ~0.4 m?")
            continue
        pts.append((z, *r))
        print(f"  {z:.2f} m -> disparity {r[0]:.2f} px (spread {r[1]:.2f})")
    keep.set()
    if len(pts) < 3:
        print("need at least 3 distances: nothing saved")
        return 1
    z, d = np.array([p[0] for p in pts]), np.array([p[1] for p in pts])
    (k, d0), *_ = np.linalg.lstsq(np.c_[1 / z, np.ones_like(z)], d, rcond=None)  # d = k / z + d0
    for zi, di in zip(z, d):
        print(f"  {zi:.2f} m: fit says {k / (di - d0):.3f} m ({(k / (di - d0) - zi) * 100:+.1f} cm)")
    calib.k, calib.d0, calib.guessed = float(k), float(d0), False
    print(f"k = {k:.2f}, d0 = {d0:.2f} (as f*B: baseline {k / ((calib.size[0] / 2) / np.tan(np.radians(calib.hfov_deg) / 2)) * 1000:.0f} mm "
          f"if the FOV is really {calib.hfov_deg:.0f} deg) -> saved to {calib.save()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
