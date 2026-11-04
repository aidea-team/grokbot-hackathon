"""Stereo depth for a side-by-side camera (the G1's custom head: 3200x1200 SBS, decoded at 1600x600 = 800x600 per eye).

OpenCV StereoSGBM on rectified pairs, ~45 ms at 800x600 on a laptop CPU (i7-1360P). Learned stereo models were measured on the
same CPU at 0.4-2.6 s per frame (HITNet, CREStereo, Fast-ACVNet; see docs/vision/live-perception.md): not live.

Calibration file (src/g1/stereo_calib.json, or the path in G1_STEREO_CALIB), "kind":
  "opencv"  full stereo calibration (K1 D1 K2 D2 R T at "size", e.g. from a checkerboard): undistort + rectify.
  "simple"  ideal parallel module: horizontal FOV + baseline, a vertical shift dy (px) between the eyes and, optionally, a fit
            z = k / (d - d0) from tape-measured distances (scripts/g1_stereo_calibrate.py) that absorbs errors in f, B and toe-in.
Without a file: "simple" with GUESSED values (75 deg, 60 mm): every distance is off by the same unknown factor until calibrated.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

import cv2
import numpy as np

from rgbd import Intrinsics

DEFAULT_CALIB = Path(__file__).resolve().parents[1] / "g1" / "stereo_calib.json"


@dataclass
class StereoCalib:
    kind: str = "simple"
    size: tuple[int, int] = (800, 600)   # per-eye size the numbers below refer to
    hfov_deg: float = 75.0               # simple: horizontal field of view of one eye
    baseline_m: float = 0.060            # simple: distance between the lenses
    dy_px: float | None = None           # simple: right eye row shift; None = estimate it from the first frames
    k: float | None = None               # simple: tape fit z = k / (d - d0), d = disparity in px at `size`
    d0: float = 0.0
    swap: bool | None = None             # left/right halves swapped; None = detect it on the first frame
    guessed: bool = True                 # nothing measured yet: distances are only indicative
    opencv: dict = field(default_factory=dict)  # kind "opencv": K1 D1 K2 D2 R T as nested lists

    @classmethod
    def load(cls, path: Path | None = None) -> "StereoCalib":
        path = Path(path or os.environ.get("G1_STEREO_CALIB") or DEFAULT_CALIB)
        if not path.exists():
            return cls()
        data = json.loads(path.read_text())
        data["size"] = tuple(data.get("size", (800, 600)))
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def save(self, path: Path | None = None) -> Path:
        path = Path(path or os.environ.get("G1_STEREO_CALIB") or DEFAULT_CALIB)
        path.write_text(json.dumps(asdict(self), indent=2) + "\n")
        return path


def estimate_dy(left: np.ndarray, right: np.ndarray) -> float | None:
    """Vertical offset (px) of the right eye: median dy of ORB matches. None if the scene has too little texture."""
    orb = cv2.ORB_create(1500)
    k1, d1 = orb.detectAndCompute(left, None)
    k2, d2 = orb.detectAndCompute(right, None)
    if d1 is None or d2 is None:
        return None
    matches = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True).match(d1, d2)
    dys = [k2[m.trainIdx].pt[1] - k1[m.queryIdx].pt[1] for m in matches
           if abs(k2[m.trainIdx].pt[1] - k1[m.queryIdx].pt[1]) < 30 and k1[m.queryIdx].pt[0] - k2[m.trainIdx].pt[0] > -2]
    return float(np.median(dys)) if len(dys) >= 20 else None


class StereoDepth:
    """(left RGB, right RGB) -> (left rectified RGB, depth z in m with NaN where unknown, intrinsics of that image, timings)."""

    def __init__(self, calib: StereoCalib | None = None, num_disparities: int = 96, block: int = 5):
        self.calib = calib or StereoCalib.load()
        self.num_disp = num_disparities  # 96 at f~520 px, B 60 mm: down to ~0.33 m
        self.sgbm = cv2.StereoSGBM_create(minDisparity=0, numDisparities=num_disparities, blockSize=block,
                                          P1=8 * block * block, P2=32 * block * block, disp12MaxDiff=1, uniquenessRatio=10,
                                          speckleWindowSize=100, speckleRange=2, preFilterCap=63, mode=cv2.STEREO_SGBM_MODE_SGBM_3WAY)
        self._maps = None  # (size, map_l, map_r, K, f*B) for kind "opencv"

    def _rectify_opencv(self, size: tuple[int, int]):
        if self._maps is None or self._maps[0] != size:
            c = self.calib.opencv
            s = size[0] / self.calib.size[0]
            K1, K2 = np.array(c["K1"], float), np.array(c["K2"], float)
            K1[:2] *= s
            K2[:2] *= s
            D1, D2, R, T = (np.array(c[n], float) for n in ("D1", "D2", "R", "T"))
            R1, R2, P1, P2, _, _, _ = cv2.stereoRectify(K1, D1, K2, D2, size, R, T, alpha=0)
            ml = cv2.initUndistortRectifyMap(K1, D1, R1, P1, size, cv2.CV_16SC2)
            mr = cv2.initUndistortRectifyMap(K2, D2, R2, P2, size, cv2.CV_16SC2)
            K = Intrinsics(P1[0, 0], P1[1, 1], P1[0, 2], P1[1, 2], size[0], size[1])
            self._maps = (size, ml, mr, K, abs(P2[0, 3]))  # P2[0,3] = -f*B
        return self._maps

    def __call__(self, left: np.ndarray, right: np.ndarray) -> tuple[np.ndarray, np.ndarray, Intrinsics, dict]:
        rect, disp, K, fB, timings = self.disparity(left, right)
        c, w = self.calib, rect.shape[1]
        with np.errstate(divide="ignore", invalid="ignore"):
            if c.kind == "simple" and c.k:
                d = disp * (c.size[0] / w)  # the fit is in disparities at calib.size
                z = c.k / (d - c.d0)
                z[d <= c.d0 + 0.5] = np.nan
            else:
                z = fB / disp
                z[disp <= 0.5] = np.nan
        z[(z < 0.2) | (z > 15)] = np.nan
        return rect, z.astype(np.float32), K, timings

    def disparity(self, left: np.ndarray, right: np.ndarray) -> tuple[np.ndarray, np.ndarray, Intrinsics, float, dict]:
        """-> (left rectified RGB, disparity in px (<= 0 = none), its intrinsics, f*B from the calibration, timings)."""
        t0 = time.perf_counter()
        c = self.calib
        if c.swap is None:  # wrong order gives almost no valid disparity: try both once
            gl, gr = cv2.cvtColor(left, cv2.COLOR_RGB2GRAY), cv2.cvtColor(right, cv2.COLOR_RGB2GRAY)
            c.swap = (self.sgbm.compute(gr, gl) > 0).mean() > 1.5 * (self.sgbm.compute(gl, gr) > 0).mean()
        if c.swap:
            left, right = right, left
        h, w = left.shape[:2]
        if c.kind == "opencv":
            _, ml, mr, K, fB = self._rectify_opencv((w, h))
            left = cv2.remap(left, ml[0], ml[1], cv2.INTER_LINEAR)
            right = cv2.remap(right, mr[0], mr[1], cv2.INTER_LINEAR)
        else:
            if c.dy_px is None:  # retried on every frame until the scene has enough texture
                c.dy_px = estimate_dy(cv2.cvtColor(left, cv2.COLOR_RGB2GRAY), cv2.cvtColor(right, cv2.COLOR_RGB2GRAY))
            if c.dy_px:
                right = cv2.warpAffine(right, np.float32([[1, 0, 0], [0, 1, -c.dy_px * h / c.size[1]]]), (w, h))
            f = (w / 2) / np.tan(np.radians(c.hfov_deg) / 2)
            K, fB = Intrinsics(f, f, w / 2, h / 2, w, h), f * c.baseline_m
        gl, gr = cv2.cvtColor(left, cv2.COLOR_RGB2GRAY), cv2.cvtColor(right, cv2.COLOR_RGB2GRAY)
        t1 = time.perf_counter()
        disp = self.sgbm.compute(gl, gr).astype(np.float32) / 16
        t2 = time.perf_counter()
        return left, disp, K, fB, {"rectify_ms": round((t1 - t0) * 1000, 1), "match_ms": round((t2 - t1) * 1000, 1)}
