"""SAM 3 masks + monocular depth (Roboflow serverless Depth Anything): how far is each object?

SAM 3 says which pixels belong to an object, the depth model gives a value for every pixel, and the median of
the depth inside each mask is that object's "closeness". The depth model returns RELATIVE depth normalised to
0..1 per image (1 = closest), not metres: to get metres calibrate with two objects at known distances.

Needs ROBOFLOW_API_KEY in .env. Usage:
  python src/vision/sam3_depth.py desk.jpg                               # relative closeness per object
  python src/vision/sam3_depth.py desk.jpg --calib "3=0.6,9=1.8"         # metres, from objects #3 (0.6 m) and #9 (1.8 m)
  python src/vision/sam3_depth.py desk.jpg --calib "3=0.6,9=1.8" --cached  # re-use the saved answers, no API calls

Writes logs/vision/<photo>.depth.jpg (depth map | masks with closeness), the raw answers
(<photo>.sam3.raw.json, <photo>.depth.json) and one JSONL line per run to logs/vision/sam3_depth_runs.jsonl.
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import requests
from PIL import Image, ImageDraw

from detect_test import OUT, PALETTE, ROOT, load_image
from sam3_segment import Instance, parse_instances, segment

DEPTH_URL = "https://serverless.roboflow.com/infer/depth-estimation"
DEFAULT_MODEL = "depth-anything-v3/small"
DEFAULT_PROMPTS = "desk,chair,laptop,computer mouse"
# near = warm, far = cool
_STOPS = [(0.0, (40, 20, 120)), (0.33, (30, 120, 200)), (0.66, (250, 200, 40)), (1.0, (220, 40, 30))]


def call_depth(jpeg: bytes, key: str, model: str, raw_path: Path) -> dict:
    r = requests.post(
        DEPTH_URL,
        headers={"Authorization": f"Bearer {key}"},
        json={"model_id": model, "image": {"type": "base64", "value": base64.b64encode(jpeg).decode()},
              "depth_map_format": "png16"},  # json is 15 MB for 1024 px; png16 is 0.4 MB
        timeout=90,
    )
    r.raise_for_status()
    data = r.json()
    data.pop("image", None)  # the server's own colourised preview: not needed
    raw_path.write_text(json.dumps(data))
    return data


def decode_depth(data: dict, size: tuple[int, int]) -> np.ndarray:
    """-> float32 array (h, w), 1.0 = closest, 0.0 = farthest, resized to `size` if needed."""
    im = Image.open(io.BytesIO(base64.b64decode(data["normalized_depth"])))
    arr = np.asarray(im).astype(np.float32) / (65535.0 if im.mode.startswith("I") else 255.0)
    if (arr.shape[1], arr.shape[0]) != size:
        arr = np.asarray(Image.fromarray(arr, mode="F").resize(size, Image.BILINEAR))
    return arr


def mask_of(inst: Instance, size: tuple[int, int]) -> np.ndarray:
    im = Image.new("L", size, 0)
    d = ImageDraw.Draw(im)
    for poly in inst.polygons:
        d.polygon(poly, fill=1)
    return np.asarray(im, dtype=bool)


def fit_calibration(points: list[tuple[float, float]]) -> tuple[float, float]:
    """closeness c = a / d + b (depth models give inverse depth up to scale and shift); two (c, metres) points fix a and b."""
    (c1, d1), (c2, d2) = points
    a = (c1 - c2) / (1 / d1 - 1 / d2)
    return a, c1 - a / d1


def metres(c: float, calib: tuple[float, float] | None) -> float | None:
    if calib is None:
        return None
    a, b = calib
    return a / (c - b) if a > 0 and c - b > 1e-3 else None


def colorize(depth: np.ndarray) -> Image.Image:
    xs, rgb = [s[0] for s in _STOPS], np.array([s[1] for s in _STOPS], dtype=np.float32)
    out = np.stack([np.interp(depth, xs, rgb[:, k]) for k in range(3)], axis=-1)
    return Image.fromarray(out.astype(np.uint8))


def render(img: Image.Image, depth: np.ndarray, rows: list[dict], insts: list[Instance], prompts: list[str], title: str) -> Image.Image:
    color = {p: PALETTE[i % len(PALETTE)] for i, p in enumerate(prompts)}
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for inst in insts:
        for poly in inst.polygons:
            d.polygon(poly, fill=color[inst.prompt] + "70", outline=color[inst.prompt], width=2)
    for inst, row in zip(insts, rows):
        x, y = inst.anchor()
        tag = f"#{row['id']} {inst.prompt} c={row['median']:.2f}" + (f" ~{row['metres']:.1f}m" if row["metres"] else "")
        d.rectangle((x - 3, y - 8, x + 7 * len(tag) + 3, y + 8), fill="#000000b0")
        d.text((x, y - 6), tag, fill="white")
    d.rectangle((0, 0, img.width, 20), fill="#000000bb")
    d.text((6, 4), title, fill="white")
    masks = Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")
    dep = colorize(depth)
    dd = ImageDraw.Draw(dep)
    dd.rectangle((0, 0, img.width, 20), fill=(0, 0, 0))
    dd.text((6, 4), "profondita' relativa: rosso = vicino, blu = lontano", fill="white")
    sheet = Image.new("RGB", (img.width * 2, img.height))
    sheet.paste(dep, (0, 0))
    sheet.paste(masks, (img.width, 0))
    return sheet


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image", type=Path)
    ap.add_argument("--prompts", default=DEFAULT_PROMPTS)
    ap.add_argument("--thresh", type=float, default=0.5)
    ap.add_argument("--model", default=DEFAULT_MODEL, help="depth-anything-v3/small|base, depth-anything-v2/small")
    ap.add_argument("--calib", default="", help='two known distances as "id=metres,id=metres" (ids from the table)')
    ap.add_argument("--cached", action="store_true", help="re-use the saved SAM 3 / depth answers, no API calls")
    args = ap.parse_args()

    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
    except ImportError:
        pass
    key = os.environ.get("ROBOFLOW_API_KEY", "")
    if not key and not args.cached:
        sys.exit("manca ROBOFLOW_API_KEY in .env")
    prompts = [p.strip() for p in args.prompts.split(",") if p.strip()]

    OUT.mkdir(parents=True, exist_ok=True)
    stem = args.image.stem
    sam_raw, depth_raw = OUT / f"{stem}.sam3.raw.json", OUT / f"{stem}.depth.json"
    img, jpeg = load_image(args.image)

    t_sam = t_depth = 0.0
    wall0 = time.perf_counter()
    if args.cached:
        sam_data, depth_data = json.loads(sam_raw.read_text()), json.loads(depth_raw.read_text())
        insts = parse_instances(sam_data, prompts, img.size)
    else:
        def run_sam():
            t = time.perf_counter()
            return segment(jpeg, prompts, key, args.thresh, img.size, sam_raw), time.perf_counter() - t

        def run_depth():
            t = time.perf_counter()
            return call_depth(jpeg, key, args.model, depth_raw), time.perf_counter() - t

        with ThreadPoolExecutor(2) as ex:  # the two calls are independent: run them together
            f_sam, f_depth = ex.submit(run_sam), ex.submit(run_depth)
            (insts, t_sam), (depth_data, t_depth) = f_sam.result(), f_depth.result()
    wall = time.perf_counter() - wall0

    depth = decode_depth(depth_data, img.size)
    total = img.width * img.height
    rows = []
    for n, inst in enumerate(insts, 1):
        vals = depth[mask_of(inst, img.size)]
        if vals.size == 0:
            vals = np.array([np.nan])
        rows.append({"id": n, "prompt": inst.prompt, "score": inst.score, "area_pct": round(100 * inst.area() / total, 1),
                     "median": float(np.nanmedian(vals)), "p10": float(np.nanpercentile(vals, 10)),
                     "p90": float(np.nanpercentile(vals, 90)), "metres": None})

    calib = None
    if args.calib:
        pts = []
        for part in args.calib.split(","):
            i, m = part.split("=")
            pts.append((rows[int(i) - 1]["median"], float(m)))
        if len(pts) != 2 or pts[0][1] == pts[1][1] or pts[0][0] == pts[1][0]:
            sys.exit("--calib vuole due oggetti diversi, a due distanze diverse, con closeness diversa")
        calib = fit_calibration(pts)
        for r in rows:
            r["metres"] = metres(r["median"], calib)

    sheet = render(img, depth, rows, insts, prompts, f"SAM 3 + {args.model}  {wall:.1f}s")
    out_img = OUT / f"{stem}.depth.jpg"
    sheet.save(out_img, quality=88)

    print(f"\n== {args.image.name} -> {out_img.relative_to(ROOT)}   SAM 3 {t_sam:.1f}s | profondita' {t_depth:.1f}s | totale {wall:.1f}s")
    print(f"{'id':>3} {'prompt':16} {'score':>5} {'area%':>6} {'closeness (p10-p90)':>22} {'metri':>7}")
    for r in sorted(rows, key=lambda r: -r["median"]):
        sc = f"{r['score']:.2f}" if r["score"] is not None else "-"
        m = f"{r['metres']:.2f}" if r["metres"] else "-"
        print(f"{r['id']:>3} {r['prompt']:16} {sc:>5} {r['area_pct']:>6} {r['median']:>9.2f} ({r['p10']:.2f}-{r['p90']:.2f}) {m:>7}")
    with (OUT / "sam3_depth_runs.jsonl").open("a") as log:
        log.write(json.dumps({"ts": time.time(), "image": args.image.name, "model": args.model, "cached": args.cached,
                              "sam3_s": round(t_sam, 2), "depth_s": round(t_depth, 2), "wall_s": round(wall, 2),
                              "calib": calib, "instances": rows}) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
