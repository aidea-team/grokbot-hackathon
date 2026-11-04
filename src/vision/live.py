"""Live perception for a robot camera: RGB-D frames -> segmented objects with distance and height, an annotated view and a depth view.

LivePerception pulls frames from `source()` (simulator: exact depth; real robot: stereo; otherwise RGB only), runs the selected
segmenter in its own thread (a fast local model on every frame it can take, SAM 3 in the cloud every few seconds), measures each
object on the SAME frame it was segmented on, and publishes JSON plus two JPEG views. It idles when nobody looks at it.
"""
from __future__ import annotations

import threading
import time
from typing import Callable

import cv2
import numpy as np

from rgbd import RGBD, colorize, measure
from segmenters import Detection

PALETTE = [(230, 25, 75), (60, 180, 75), (67, 99, 216), (245, 130, 49), (145, 30, 180), (0, 150, 150), (200, 160, 40), (240, 50, 230)]
# Prompts that work best per model (all shown with the same names, see segmenters.ALIASES): YOLOE finds monitors as "tv", while SAM 3
# with "tv" also takes the black back of an office chair and finds them as "computer monitor". YOLO ignores prompts (COCO classes).
DEFAULT_PROMPTS = {"yoloe": ["desk", "chair", "tv", "laptop", "keyboard", "mouse", "person"],
                   "sam3": ["desk", "chair", "computer monitor", "laptop", "keyboard", "computer mouse", "person"]}


def _jpeg(rgb: np.ndarray, quality: int = 80) -> bytes:
    return cv2.imencode(".jpg", cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, quality])[1].tobytes()


def _text(img: np.ndarray, s: str, x: int, y: int, color=(255, 255, 255), scale: float = 0.45,
          taken: list | None = None) -> None:
    """Label with a dark background, kept inside the image; with `taken` (rectangles already drawn) it moves down until it is free."""
    (tw, th), _ = cv2.getTextSize(s, cv2.FONT_HERSHEY_SIMPLEX, scale, 1)
    x, y = int(max(0, min(x, img.shape[1] - tw - 4))), int(max(th + 4, y))
    if taken is not None:
        while any(x < r[2] and r[0] < x + tw + 4 and y - th - 4 < r[3] and r[1] < y + 3 for r in taken) and y < img.shape[0] - 4:
            y += th + 7
        taken.append((x, y - th - 4, x + tw + 4, y + 3))
    cv2.rectangle(img, (x, y - th - 4), (x + tw + 4, y + 3), (0, 0, 0), -1)
    cv2.putText(img, s, (x + 2, y), cv2.FONT_HERSHEY_SIMPLEX, scale, color, 1, cv2.LINE_AA)


def _dedup(dets: list[Detection]) -> list[Detection]:
    """Drop a detection when a better-scoring one with the same label covers most of it (models sometimes return both)."""
    keep: list[Detection] = []
    for d in sorted(dets, key=lambda d: -(d.score or 0.0)):
        area = d.mask.sum()
        if all(k.label != d.label or (k.mask & d.mask).sum() < 0.8 * min(area, k.mask.sum()) for k in keep):
            keep.append(d)
    return keep


class LivePerception:
    IDLE_S = 5.0     # nobody polled for this long: stop working
    MAX_FPS = 8.0    # main loop (depth view) rate cap

    def __init__(self, source: Callable[[], RGBD | None], backends: dict[str, Callable[[list[str]], Callable]], log=None):
        """`backends`: name -> factory(prompts) returning a segmenter (callable rgb -> list[Detection], with `min_period_s`)."""
        self.source, self.backends, self.log = source, backends, log
        self.enabled = False
        self.backend = next(iter(backends))
        self.period_s = 3.0
        self.prompts = list(DEFAULT_PROMPTS.get(self.backend, DEFAULT_PROMPTS["yoloe"]))
        self._seg, self._seg_key = None, None
        self._job: threading.Thread | None = None
        self._cond = threading.Condition()
        self._jpeg: dict[str, bytes | None] = {"annotated": None, "depth": None}
        self._n = {"annotated": 0, "depth": 0}
        self._result: dict = {"objects": [], "error": None}
        self._seen = 0.0
        self._last_seg = 0.0
        self._last_log = 0.0
        self._colors: dict[str, tuple[int, int, int]] = {}  # label -> colour, in order of appearance (stable, no clashes)
        self._thread: threading.Thread | None = None
        self._stop = False

    # ------------------------------------------------------------------ public API (thread-safe)
    def configure(self, enabled: bool | None = None, backend: str | None = None, period_s: float | None = None,
                  prompts: list[str] | None = None) -> dict:
        if backend is not None:
            if backend not in self.backends:
                raise ValueError(f"backend {backend!r}: scegli tra {sorted(self.backends)}")
            if self.prompts == DEFAULT_PROMPTS.get(self.backend) and backend in DEFAULT_PROMPTS:
                self.prompts = list(DEFAULT_PROMPTS[backend])  # untouched defaults follow the model; custom prompts stay
            self.backend = backend
        if period_s is not None:
            self.period_s = float(np.clip(period_s, 0.0, 60.0))
        if prompts is not None:
            self.prompts = [p.strip() for p in prompts if p.strip()][:16] or list(DEFAULT_PROMPTS.get(self.backend, DEFAULT_PROMPTS["yoloe"]))
        if enabled is not None:
            self.enabled = bool(enabled)
            if self.enabled:
                self._seen = time.monotonic()
                self._ensure_thread()
        with self._cond:
            self._result = {**self._result, "error": None}
        return self.status()

    def status(self) -> dict:
        return {"enabled": self.enabled, "backend": self.backend, "backends": list(self.backends), "period_s": self.period_s,
                "prompts": self.prompts}

    def result(self) -> dict:
        self._seen = time.monotonic()
        with self._cond:
            r = dict(self._result)
        if r.get("analysed_t"):
            r["age_s"] = round(time.monotonic() - r.pop("analysed_t"), 1)
        return {**self.status(), **r}

    def frame(self, after: int = -1, timeout: float = 2.0, view: str = "annotated") -> tuple[int, bytes | None]:
        """Latest JPEG of `view` ("annotated" or "depth"), blocking until one newer than `after` (MJPEG streaming)."""
        self._seen = time.monotonic()
        with self._cond:
            self._cond.wait_for(lambda: self._n[view] > after or self._stop, timeout)
            return self._n[view], self._jpeg[view]

    def shutdown(self) -> None:
        self._stop = True

    # ------------------------------------------------------------------ internals
    def _ensure_thread(self) -> None:
        if self._thread is None or not self._thread.is_alive():
            self._thread = threading.Thread(target=self._run, daemon=True, name="perception")
            self._thread.start()

    def _publish(self, view: str, rgb: np.ndarray) -> None:
        jpg = _jpeg(rgb)
        with self._cond:
            self._jpeg[view], self._n[view] = jpg, self._n[view] + 1
            self._cond.notify_all()

    def _error(self, msg: str) -> None:
        with self._cond:
            self._result = {**self._result, "error": msg}

    def _segmenter(self):
        key = (self.backend, tuple(self.prompts))
        if self._seg_key != key:
            self._error(f"preparo {self.backend} (la prima volta scarica i pesi)…")
            self._seg, self._seg_key = None, key
            try:
                self._seg = self.backends[self.backend](list(self.prompts))
            except Exception:
                self._seg_key = None  # retry on the next frame (e.g. after fixing the prompts)
                raise
        return self._seg

    def _run(self) -> None:
        while not self._stop:
            t0 = time.monotonic()
            if not self.enabled or t0 - self._seen > self.IDLE_S:
                time.sleep(0.2)
                continue
            try:
                frame = self.source()
            except Exception as e:  # noqa: BLE001  (camera/stereo errors are shown, the loop keeps going)
                frame = None
                self._error(f"camera: {e}")
            if frame is None:
                time.sleep(0.5)
                continue
            if frame.depth is not None:
                self._publish("depth", self._draw_depth(frame))
            busy = self._job is not None and self._job.is_alive()
            # cloud backends are sampled every period_s (never faster than they can answer); local ones take every frame they can
            period = max(self.period_s, 2.0) if self.backend == "sam3" else 0.0
            if not busy and t0 - self._last_seg >= period:
                self._last_seg = t0
                self._job = threading.Thread(target=self._analyse, args=(frame,), daemon=True, name="perception-seg")
                self._job.start()
            time.sleep(max(0.0, 1 / self.MAX_FPS - (time.monotonic() - t0)))

    def _analyse(self, frame: RGBD) -> None:
        try:
            seg = self._segmenter()
            t = time.perf_counter()
            dets = _dedup(seg(frame.rgb))
            seg_ms = (time.perf_counter() - t) * 1000
            t = time.perf_counter()
            objs = [self._object(d, frame) for d in dets]
            fuse_ms = (time.perf_counter() - t) * 1000
        except Exception as e:  # noqa: BLE001
            self._error(f"{self.backend}: {e}")
            return
        self._publish("annotated", self._draw(frame, dets, objs, seg_ms))
        floor = None if frame.floor is None else {"height_m": round(frame.floor.d, 3), "pitch_deg": round(frame.floor.pitch_deg(), 1),
                                                  "source": frame.floor.source}
        with self._cond:
            self._result = {"objects": objs, "error": None, "frame": frame.n, "depth_source": frame.source if frame.depth is not None else None,
                            "floor": floor, "size": [frame.rgb.shape[1], frame.rgb.shape[0]], "analysed_t": time.monotonic(),
                            "timings": {"seg_ms": round(seg_ms, 1), "fuse_ms": round(fuse_ms, 1), **frame.timings,
                                        "frame_age_ms": round((time.monotonic() - frame.t) * 1000, 1) if frame.t else None}}
        if self.log is not None and time.monotonic() - self._last_log > 1.0:
            self._last_log = time.monotonic()
            self.log.event("perception", backend=self.backend, seg_ms=round(seg_ms, 1), fuse_ms=round(fuse_ms, 1),
                           depth=frame.source if frame.depth is not None else None, floor=floor,
                           objects=[{k: o[k] for k in ("label", "score", "dist_m", "top_m", "bearing_deg")} for o in objs])

    def _object(self, d: Detection, frame: RGBD) -> dict:
        h, w = d.mask.shape
        x0, y0, x1, y1 = d.box
        return {"label": d.label, "score": None if d.score is None else round(float(d.score), 2),
                "box": [round(x0 / w, 4), round(y0 / h, 4), round(x1 / w, 4), round(y1 / h, 4)], **measure(d.mask, frame)}

    def _color(self, label: str) -> tuple[int, int, int]:
        if label not in self._colors:
            self._colors[label] = PALETTE[len(self._colors) % len(PALETTE)]
        return self._colors[label]

    def _draw(self, frame: RGBD, dets: list[Detection], objs: list[dict], seg_ms: float) -> np.ndarray:
        img = frame.rgb.copy()
        over = img.copy()
        for d in dets:
            over[d.mask] = self._color(d.label)
        img = cv2.addWeighted(over, 0.42, img, 0.58, 0)
        taken = [(0, 0, img.shape[1], 22)]  # the status bar
        for d, o in sorted(zip(dets, objs), key=lambda p: p[0].box[1]):
            cs, _ = cv2.findContours(d.mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(img, cs, -1, self._color(d.label), 2)
            tag = d.label + (f" {o['dist_m']:.2f}m" if o["dist_m"] is not None else "") + \
                (f" h{o['top_m']:.2f}m" if o["top_m"] is not None else "")
            _text(img, tag, int((d.box[0] + d.box[2]) / 2) - 4 * len(tag), int(d.box[1]) + 14, self._color(d.label), taken=taken)
        top = f"{self.backend} {seg_ms:.0f} ms | {len(dets)} oggetti"
        if frame.depth is None:
            top += " | niente profondita'"
        elif frame.floor is not None:
            top += f" | prof. {frame.source} | camera a {frame.floor.d:.2f} m, inclinata {frame.floor.pitch_deg():.0f} gradi"
        else:
            top += f" | prof. {frame.source} | pavimento non visto: niente altezze"
        _text(img, top, 4, 16, (230, 230, 230), 0.42)
        return img

    def _draw_depth(self, frame: RGBD) -> np.ndarray:
        img = colorize(frame.depth)
        valid = np.isfinite(frame.depth)
        cov = 100 * valid.mean()
        _text(img, f"profondita' {frame.source}: rosso = vicino, blu = lontano | copertura {cov:.0f}% "
                   + " ".join(f"{k} {v}" for k, v in frame.timings.items()), 4, 16, (230, 230, 230), 0.42)
        return img
