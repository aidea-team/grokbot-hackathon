"""RGB-D geometry for live perception: intrinsics, back-projection, floor plane, per-object distance / height / width.

Camera frame is OpenCV's: x right, y down, z forward, metres. A depth map holds z (distance along the optical axis) per pixel,
NaN = no measurement. The same code serves the simulator (exact depth from MuJoCo) and the real robot (depth from stereo).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass(frozen=True)
class Intrinsics:
    fx: float
    fy: float
    cx: float
    cy: float
    width: int
    height: int

    @classmethod
    def from_fovy(cls, fovy_deg: float, width: int, height: int) -> "Intrinsics":
        """Pinhole with square pixels and the principal point at the centre (MuJoCo cameras, ideal modules)."""
        f = (height / 2) / np.tan(np.radians(fovy_deg) / 2)
        return cls(float(f), float(f), width / 2, height / 2, width, height)

    def scaled(self, width: int, height: int) -> "Intrinsics":
        sx, sy = width / self.width, height / self.height
        return Intrinsics(self.fx * sx, self.fy * sy, self.cx * sx, self.cy * sy, width, height)


@dataclass(frozen=True)
class Floor:
    """Height above the floor of a camera-frame point p is n·p + d: n = world "up" in camera coordinates, d = camera height."""
    n: np.ndarray
    d: float
    source: str  # "sim" (exact, from the simulator's camera pose) or "fit" (RANSAC on the depth)

    def height(self, pts: np.ndarray) -> np.ndarray:
        return pts @ self.n + self.d

    def pitch_deg(self) -> float:
        """Camera tilt below the horizon (positive = looking down)."""
        return float(np.degrees(np.arcsin(np.clip(-self.n[2], -1, 1))))


@dataclass
class RGBD:
    rgb: np.ndarray            # (h, w, 3) uint8
    depth: np.ndarray | None   # (h, w) float32, metres along z; NaN = unknown. None = no depth source
    K: Intrinsics
    floor: Floor | None = None
    t: float = 0.0             # time.monotonic() of the capture
    source: str = "mono"       # "sim" | "stereo" | "mono"
    n: int = 0                 # frame counter of the source
    timings: dict = field(default_factory=dict)  # ms spent producing it (render, rectify, match ...)


def points(depth: np.ndarray, K: Intrinsics, mask: np.ndarray | None = None, max_points: int = 0) -> np.ndarray:
    """(N, 3) camera-frame points of the valid pixels (inside `mask` if given), evenly thinned to `max_points` if > 0."""
    valid = np.isfinite(depth) & (depth > 0)
    if mask is not None:
        valid &= mask
    v, u = np.nonzero(valid)
    if 0 < max_points < len(v):
        keep = np.linspace(0, len(v) - 1, max_points).astype(np.int64)
        v, u = v[keep], u[keep]
    z = depth[v, u]
    return np.stack([(u - K.cx) * z / K.fx, (v - K.cy) * z / K.fy, z], axis=1)


def fit_floor(depth: np.ndarray, K: Intrinsics, iters: int = 80, tol: float = 0.03, max_points: int = 4000,
              rng: np.random.Generator | None = None) -> Floor | None:
    """RANSAC plane on the lower part of the image whose normal points roughly up (camera within +-50 deg of level).
    None if no convincing floor is visible (too few inliers or an implausible camera height)."""
    rng = rng or np.random.default_rng(0)
    h = depth.shape[0]
    lower = np.zeros_like(depth, dtype=bool)
    lower[int(h * 0.4):] = True
    pts = points(depth, K, lower & (depth < 8.0))
    if len(pts) < 200:
        return None
    if len(pts) > max_points:
        pts = pts[rng.choice(len(pts), max_points, replace=False)]
    best, best_n = None, 0
    for _ in range(iters):
        a, b, c = pts[rng.choice(len(pts), 3, replace=False)]
        n = np.cross(b - a, c - a)
        norm = np.linalg.norm(n)
        if norm < 1e-9:
            continue
        n /= norm
        if n[1] > 0:  # up in camera coordinates has a negative y component (y points down)
            n = -n
        if -n[1] < np.cos(np.radians(50)):
            continue
        d = -float(n @ a)
        inl = np.abs(pts @ n + d) < tol
        if inl.sum() > best_n:
            best, best_n = inl, int(inl.sum())
    if best is None or best_n < 0.15 * len(pts):
        return None
    # least-squares refinement on the inliers
    p = pts[best]
    centroid = p.mean(axis=0)
    n = np.linalg.svd(p - centroid)[2][2]
    if n[1] > 0:
        n = -n
    d = -float(n @ centroid)
    if not 0.2 < d < 3.0:
        return None
    return Floor(n, d, "fit")


def measure(mask: np.ndarray, frame: RGBD, erode_px: int = 2) -> dict:
    """Distance, direction and size of the object under `mask`. The mask is eroded first so that its border pixels, which often
    fall on the background, do not pull the median. Values are None when the depth inside the mask is missing."""
    out = {"dist_m": None, "ahead_m": None, "bearing_deg": None, "top_m": None, "bottom_m": None, "width_m": None, "depth_px": 0}
    if frame.depth is None:
        return out
    m = mask
    if erode_px > 0:
        import cv2
        er = cv2.erode(mask.astype(np.uint8), np.ones((2 * erode_px + 1,) * 2, np.uint8)).astype(bool)
        if er.sum() >= 30:
            m = er
    pts = points(frame.depth, frame.K, m, max_points=5000)  # medians and percentiles do not need more
    out["depth_px"] = int(len(pts))
    if len(pts) < 20:
        return out
    rng = np.linalg.norm(pts, axis=1)
    dist = float(np.median(rng))
    # sizes from the points near the object's own depth: a mask that spills onto the background (coarse masks, stereo edges)
    # moves the median little but the extremes a lot
    band = pts[np.abs(rng - dist) < max(0.3, 0.3 * dist)]
    if len(band) >= 20:
        pts = band
    centre = np.median(pts, axis=0)
    out["dist_m"] = round(dist, 2)
    out["bearing_deg"] = round(float(np.degrees(np.arctan2(centre[0], centre[2]))), 1)  # + = right of the camera axis
    right = np.array([1.0, 0.0, 0.0])
    if frame.floor is not None:
        up = frame.floor.n
        flat = centre - up * (up @ centre)  # the centre projected on the horizontal plane through the camera
        out["ahead_m"] = round(float(np.linalg.norm(flat)), 2)
        hts = frame.floor.height(pts)
        out["top_m"], out["bottom_m"] = round(float(np.percentile(hts, 97)), 2), round(float(np.percentile(hts, 3)), 2)
        right = right - up * (up @ right)
        right /= np.linalg.norm(right)
    lat = pts @ right
    out["width_m"] = round(float(np.percentile(lat, 97) - np.percentile(lat, 3)), 2)
    return out


_STOPS = np.array([[0.0, 30, 20, 110], [0.25, 30, 110, 210], [0.5, 40, 200, 160], [0.75, 250, 200, 40], [1.0, 220, 40, 30]], np.float32)


def colorize(depth: np.ndarray, near: float = 0.4, far: float = 6.0) -> np.ndarray:
    """Depth (m) -> RGB uint8, linear over room distances: red = near, blue = far (>= `far`), dark grey = unknown."""
    t = 1 - (np.clip(depth, near, far) - near) / (far - near)
    t = np.nan_to_num(t, nan=-1.0)
    rgb = np.stack([np.interp(t, _STOPS[:, 0], _STOPS[:, k]) for k in (1, 2, 3)], axis=-1).astype(np.uint8)
    rgb[t < 0] = (25, 25, 28)
    return rgb
