"""Run the dashboard's segmentation (YOLOE / YOLO, same models and drawing style as src/vision/live.py) on a recorded video,
frame by frame, and write an annotated MP4 plus a JSONL with what was found in every frame.

Phone footage has no depth, so the labels carry no distance or height (the status bar says so): only the simulator and the
G1's stereo head can measure. Decoding and encoding go through ffmpeg (HEVC from phones, rotation metadata applied).

    python scripts/yoloe_footage.py assets/footage/pov-verso-scrivania-1.mp4 -o out/pov-yoloe.mp4
    python scripts/yoloe_footage.py IN.mov -o OUT.mp4 --start 4 --duration 8 --width 1920 --it --solid person
    python scripts/yoloe_footage.py IN.mov -o OUT.mp4 --vf "transpose=1,crop=iw:iw*9/16" --prompts person laptop chair
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "vision"))

from live import DEFAULT_PROMPTS, _dedup, _text  # noqa: E402  same drawing helpers as the live dashboard

# Fixed colours per label (RGB), so the same object keeps its colour across clips; aidea violet for people.
COLORS = {"person": (143, 63, 255), "desk": (245, 130, 49), "chair": (230, 25, 75), "laptop": (60, 180, 75),
          "keyboard": (67, 99, 216), "mouse": (0, 150, 150), "monitor": (255, 249, 74), "table/desk": (245, 130, 49)}
ITALIAN = {"person": "umano", "desk": "scrivania", "chair": "sedia", "laptop": "portatile", "keyboard": "tastiera",
           "mouse": "mouse", "monitor": "monitor", "table/desk": "tavolo", "backpack": "zaino", "bottle": "bottiglia",
           "cup": "tazza", "cell phone": "telefono", "dog": "cane"}


def probe(path: str, vf: str, start: float, duration: float | None, width: int) -> tuple[int, int, float]:
    """Output size after rotation + user filter + scale, and the source frame rate."""
    args = ["ffmpeg", "-v", "error", "-ss", str(start), "-i", path, "-frames:v", "1",
            "-vf", ",".join(f for f in [vf, f"scale={width}:-2"] if f), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    one = subprocess.run(args, capture_output=True, check=True).stdout
    rate = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=avg_frame_rate",
                           "-of", "default=nw=1:nk=1", path], capture_output=True, text=True, check=True).stdout.split()[0]
    num, den = (float(x) for x in rate.strip(",").split("/"))
    h = len(one) // (3 * width)
    return width, h, num / den if den else 30.0


def draw(rgb: np.ndarray, dets, backend: str, seg_ms: float, italian: bool, solid: set[str]) -> np.ndarray:
    img = rgb.copy()
    over = img.copy()
    color = lambda lab: COLORS.get(lab, (200, 200, 200))  # noqa: E731
    for d in dets:
        over[d.mask] = color(d.label)
    img = cv2.addWeighted(over, 0.42, img, 0.58, 0)
    for d in dets:  # opaque fill for these labels: hides who they are (other participants in the footage)
        if d.label in solid:
            img[d.mask] = (0.15 * img[d.mask] + 0.85 * np.array(color(d.label))).astype(np.uint8)
    scale = max(0.45, img.shape[1] / 1280 * 0.6)
    bar = int(28 * scale / 0.6)
    taken = [(0, 0, img.shape[1], bar)]
    for d in sorted(dets, key=lambda d: d.box[1]):
        cs, _ = cv2.findContours(d.mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(img, cs, -1, color(d.label), max(2, int(2 * scale / 0.6)))
        tag = (ITALIAN.get(d.label, d.label) if italian else d.label) + (f" {d.score:.2f}" if d.score is not None else "")
        _text(img, tag, int((d.box[0] + d.box[2]) / 2) - int(6 * scale / 0.45) * len(tag) // 2, int(d.box[1]) + bar,
              color(d.label), scale, taken=taken)
    status = (f"{backend} {seg_ms:.0f} ms | {len(dets)} oggetti | niente profondita' (video da telefono)" if italian else
              f"{backend} {seg_ms:.0f} ms | {len(dets)} objects | no depth (phone video)")
    _text(img, status, 6, bar - 6, (230, 230, 230), scale * 0.9)
    return img


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input")
    ap.add_argument("-o", "--output", required=True, help="annotated .mp4 (H.264); a .jsonl with the detections is written next to it")
    ap.add_argument("--backend", choices=["yoloe", "yolo"], default="yoloe")
    ap.add_argument("--prompts", nargs="+", help="YOLOE words (from src/vision/yoloe_vocab.npz); default: the dashboard's")
    ap.add_argument("--conf", type=float, default=None, help="confidence threshold (default: the model's)")
    ap.add_argument("--start", type=float, default=0.0, help="seconds into the clip")
    ap.add_argument("--duration", type=float, default=None, help="seconds to process (default: to the end)")
    ap.add_argument("--fps", type=float, default=None, help="output/analysis fps (default: source, at most 30)")
    ap.add_argument("--width", type=int, default=1280, help="output width in px (height follows the aspect ratio)")
    ap.add_argument("--vf", default="", help="extra ffmpeg filter applied first, e.g. a crop of the useful region")
    ap.add_argument("--it", action="store_true", help="Italian labels (person -> umano, desk -> scrivania, ...)")
    ap.add_argument("--solid", nargs="*", default=[], metavar="LABEL",
                    help="labels filled opaque instead of tinted, e.g. --solid person to anonymise people")
    ap.add_argument("--threads", type=int, default=4)
    a = ap.parse_args()

    from yolo_onnx import YoloeSegmenter, YoloSegmenter
    kw = {"threads": a.threads} | ({"conf": a.conf} if a.conf is not None else {})
    seg = YoloeSegmenter(a.prompts or DEFAULT_PROMPTS["yoloe"], **kw) if a.backend == "yoloe" else YoloSegmenter(**kw)

    w, h, src_fps = probe(a.input, a.vf, a.start, a.duration, a.width)
    fps = a.fps or min(src_fps, 30.0)
    chain = ",".join(f for f in [a.vf, f"fps={fps}", f"scale={w}:{h}"] if f)
    dec = ["ffmpeg", "-v", "error", "-ss", str(a.start)] + (["-t", str(a.duration)] if a.duration else []) + \
          ["-i", a.input, "-an", "-vf", chain, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    enc = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(fps), "-i", "-",
           "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)]
    src = subprocess.Popen(dec, stdout=subprocess.PIPE)
    dst = subprocess.Popen(enc, stdin=subprocess.PIPE)
    log = open(out.with_suffix(".jsonl"), "w")
    n, t0, frame_bytes = 0, time.time(), w * h * 3
    try:
        while (buf := src.stdout.read(frame_bytes)) and len(buf) == frame_bytes:
            rgb = np.frombuffer(buf, np.uint8).reshape(h, w, 3)
            ts = time.perf_counter()
            dets = _dedup(seg(rgb))
            ms = 1000 * (time.perf_counter() - ts)
            dst.stdin.write(draw(rgb, dets, a.backend, ms, a.it, set(a.solid)).tobytes())
            log.write(json.dumps({"frame": n, "t": round(a.start + n / fps, 3), "seg_ms": round(ms, 1),
                                  "objects": [{"label": d.label, "score": round(float(d.score or 0), 3),
                                               "box": [round(v, 1) for v in d.box], "area": round(float(d.mask.mean()), 4)}
                                              for d in dets]}) + "\n")
            n += 1
            if n % 30 == 0:
                print(f"{n} frame, {n / (time.time() - t0):.1f} fps", file=sys.stderr)
    finally:
        log.close()
        dst.stdin.close()
        dst.wait()
        src.wait()
    print(f"{out}: {n} frame a {fps:g} fps, {w}x{h}, {time.time() - t0:.0f} s; rilevamenti in {out.with_suffix('.jsonl')}")


if __name__ == "__main__":
    main()
