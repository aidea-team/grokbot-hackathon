"""Stereo depth accuracy against ground truth: the fake head renders the desk scene from two cameras 60 mm apart (perfectly
rectified, known focal length) and gives the true depth. Measures StereoDepth's error inside each object and over the whole frame.
This bounds what the matcher can do; a real module adds calibration error on top. Run: python tests/test_vision_stereo.py"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in ("src/vision", "src/g1", "scripts"):
    sys.path.insert(0, str(ROOT / p))
os.environ.setdefault("MUJOCO_GL", "egl")

import cv2  # noqa: E402
import mujoco  # noqa: E402
import numpy as np  # noqa: E402

from fake_g1_head import SimStereoHead  # noqa: E402
from stereo import StereoCalib, StereoDepth  # noqa: E402

OBJECTS = ("desk_", "laptop_", "chair_")


def main() -> int:
    head = SimStereoHead("desk", hfov_deg=75, baseline=0.06)
    stereo = StereoDepth(StereoCalib(hfov_deg=75, baseline_m=0.06, dy_px=0.0, swap=False, guessed=False))
    seg_r = mujoco.Renderer(head.model, height=head.eye[1], width=head.eye[0])
    seg_r.enable_segmentation_rendering()
    fails = 0
    for yaw, x in [(0, 0.1), (-12, 0.9), (8, 1.5)]:
        head.place(yaw, x)
        left, right, truth = head.render()
        _, z, K, tm = stereo(left, right)
        seg_r.update_scene(head.data, camera="stereo_l")
        seg = seg_r.render()[..., 0]
        both = np.isfinite(z) & np.isfinite(truth)
        rel = np.abs(z[both] - truth[both]) / truth[both]
        print(f"view yaw {yaw:+} deg, x {x} m: coverage {np.isfinite(z).mean():.0%}, frame median error {np.median(rel):.1%}, "
              f"{tm['match_ms']:.0f} ms matching")
        for prefix in OBJECTS:
            ids = [i for i in range(head.model.ngeom) if (head.model.geom(i).name or "").startswith(prefix)]
            mask = np.isin(seg, ids)
            if mask.sum() < 200:
                continue
            # like rgbd.measure: drop the border, where stereo matching bleeds the background into the object
            mask = cv2.erode(mask.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
            zm, tz = z[mask & np.isfinite(z)], truth[mask & np.isfinite(truth)]
            if len(zm) < 50:
                print(f"   {prefix:10} no stereo depth inside the object ({mask.sum()} px)")
                fails += 1
                continue
            err = (np.median(zm) - np.median(tz)) / np.median(tz)
            # 10%: dark, flat, textureless surfaces are the worst case for block matching (a black office chair reached +8% in one
            # view); the current scene stays within ~3%
            ok = abs(err) < 0.10
            fails += not ok
            print(f"   {prefix:10} stereo {np.median(zm):.2f} m vs truth {np.median(tz):.2f} m ({err:+.1%}), "
                  f"{len(zm) / mask.sum():.0%} of its pixels have depth {'ok' if ok else 'FAIL'}")
    print("FAILED" if fails else "all ok")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
