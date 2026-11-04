"""Live perception geometry in the simulator: exact MuJoCo depth + exact masks (segmentation render) must give back the known
distances and heights of the objects of the desk scene. Run: python tests/test_vision_sim.py"""
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "g1"))
sys.path.insert(0, str(ROOT / "src" / "vision"))

import mujoco  # noqa: E402
import numpy as np  # noqa: E402

from g1_world import G1World  # noqa: E402
from rgbd import fit_floor, measure  # noqa: E402

# object (geom name prefix: all its pieces) -> (true top above the floor in m, world x,y of its centre or None)
TRUTH = {"desk_": (0.75, (3.0, 0.0)), "monitor_": (1.21, (3.15, 0.0)), "chair_": (1.04, None), "pc_tower": (0.44, (3.05, 0.5))}
HIDDEN = 3  # geom group used to hide everything but one object


def segment(m: mujoco.MjModel, d: mujoco.MjData, size: tuple[int, int], only: list[int] | None = None) -> np.ndarray:
    """Geom id per pixel of the head camera; with `only`, every other geom is hidden (= the object's unoccluded silhouette)."""
    groups = m.geom_group.copy()
    opt = mujoco.MjvOption()
    if only is not None:
        m.geom_group[:] = HIDDEN
        m.geom_group[only] = 0
        opt.geomgroup[HIDDEN] = 0
    r = mujoco.Renderer(m, height=size[1], width=size[0])
    r.enable_segmentation_rendering()
    r.update_scene(d, camera="head_cam", scene_option=opt)
    seg = r.render()[..., 0].copy()
    r.close()
    m.geom_group[:] = groups
    return seg


def main() -> int:
    w = G1World(scene="desk")
    w.start()
    time.sleep(2.0)  # let the policy settle the robot on its feet
    w.head_rgbd(timeout=15)  # the first one also creates the GL contexts (slow with software rendering)
    frame = w.head_rgbd(timeout=15)
    assert frame is not None, "no RGBD from the simulator"
    pose = w._rgbd_pose.copy()  # the robot sways and steps while standing: masks must come from the frame's own state
    w.shutdown()
    m = w.model
    d = mujoco.MjData(m)
    d.qpos[:] = pose
    mujoco.mj_forward(m, d)
    seg = segment(m, d, w.head_size)
    cam = d.cam_xpos[m.camera("head_cam").id]
    print(f"camera height {frame.floor.d:.3f} m (truth {cam[2]:.3f}), pitch {frame.floor.pitch_deg():.1f} deg, depth {frame.timings}")
    fails = 0
    fit = fit_floor(frame.depth, frame.K)
    ok = fit is not None and abs(fit.d - cam[2]) < 0.05 and abs(fit.pitch_deg() - frame.floor.pitch_deg()) < 3
    fails += not ok
    print(f"floor RANSAC: height {fit.d if fit else None}, pitch {fit.pitch_deg() if fit else None} -> {'ok' if ok else 'FAIL'}")
    for prefix, (top, xy) in TRUTH.items():
        ids = [i for i in range(m.ngeom) if (m.geom(i).name or "").startswith(prefix)]
        mask = np.isin(seg, ids)
        alone = np.isin(segment(m, d, w.head_size, ids), ids)
        vis = mask.sum() / max(alone.sum(), 1)
        if alone.sum() < 50 or vis < 0.6:  # hidden behind something or cut by the image border: only part of it can be measured
            print(f"{prefix:10} only {vis:.0%} visible from here (occluded / out of frame), skipped")
            continue
        r = measure(mask, frame)
        line = f"{prefix:10} {vis:4.0%} visible  top {r['top_m']} (truth {top})  dist {r['dist_m']} ahead {r['ahead_m']} bearing {r['bearing_deg']} width {r['width_m']}"
        bad = r["top_m"] is None or abs(r["top_m"] - top) > 0.05
        if xy is not None:
            true_ahead = float(np.hypot(xy[0] - cam[0], xy[1] - cam[1]))
            line += f" (centre ~{true_ahead:.2f} ahead)"
            bad |= abs(r["ahead_m"] - true_ahead) > 0.3  # the median of the visible surface is not the centre: loose
        print(line, "FAIL" if bad else "ok")
        fails += bad
    print("FAILED" if fails else "all ok")
    return 1 if fails else 0


if __name__ == "__main__":
    os.environ.setdefault("MUJOCO_GL", "egl")
    sys.exit(main())
