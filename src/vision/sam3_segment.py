"""SAM 3 (Roboflow serverless) text-prompted segmentation of a desk scene: masks only, no bounding boxes.

Needs ROBOFLOW_API_KEY in .env. Usage:
  python src/vision/sam3_segment.py desk1.jpg desk2.jpg
  python src/vision/sam3_segment.py desk.jpg --prompts "desk,chair,computer monitor,keyboard" --thresh 0.4

Writes logs/vision/<photo>.sam3.jpg (original | masks), the raw API answer to logs/vision/<photo>.sam3.raw.json
and one JSONL line per call to logs/vision/sam3_runs.jsonl (latency, instances, mask area).
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import requests
from PIL import Image, ImageDraw

from detect_test import OUT, PALETTE, ROOT, load_image  # same folder: reuse image loading + colours

DEFAULT_PROMPTS = "desk,chair,computer"
URL = "https://serverless.roboflow.com/sam3/concept_segment"

Polygon = list[tuple[float, float]]


@dataclass
class Instance:
    prompt: str
    score: float | None
    polygons: list[Polygon]  # one instance can be several disjoint pieces

    def area(self) -> float:
        return sum(_area(p) for p in self.polygons)

    def anchor(self) -> tuple[float, float]:
        """Where to put the label: mean of the vertices of the largest piece."""
        big = max(self.polygons, key=_area)
        return sum(x for x, _ in big) / len(big), sum(y for _, y in big) / len(big)


def _area(poly: Polygon) -> float:
    s = 0.0
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        s += x0 * y1 - x1 * y0
    return abs(s) / 2


def _is_num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _polygons(node) -> list[Polygon]:
    """The per-prediction schema of concept_segment is not spelled out in the docs page we read, so accept any
    polygon-shaped value under the prediction: [[x, y], ...] or flat [x0, y0, x1, y1, ...]."""
    found: list[Polygon] = []
    if isinstance(node, list):
        if len(node) >= 3 and all(isinstance(p, (list, tuple)) and len(p) == 2 and all(_is_num(v) for v in p) for p in node):
            found.append([(float(p[0]), float(p[1])) for p in node])
        elif len(node) >= 6 and len(node) % 2 == 0 and all(_is_num(v) for v in node):
            found.append([(float(node[i]), float(node[i + 1])) for i in range(0, len(node), 2)])
        else:
            for item in node:
                found += _polygons(item)
    elif isinstance(node, dict):
        for v in node.values():
            found += _polygons(v)
    return found


def segment(jpeg: bytes, prompts: list[str], key: str, thresh: float, size: tuple[int, int], raw_path: Path) -> list[Instance]:
    r = requests.post(
        URL,
        headers={"Authorization": f"Bearer {key}"},
        json={
            "image": {"type": "base64", "value": base64.b64encode(jpeg).decode()},
            "prompts": [{"type": "text", "text": p} for p in prompts],
            "output_prob_thresh": thresh,
            "format": "polygon",
        },
        timeout=60,
    )
    r.raise_for_status()
    data = r.json()
    raw_path.write_text(json.dumps(data)[:300_000])  # keep the real schema to fix the parser if needed
    out: list[Instance] = []
    for prompt, res in zip(prompts, data.get("prompt_results", [])):
        for pred in res.get("predictions", []):
            polys = _polygons(pred)
            if not polys:
                continue
            score = next((pred[k] for k in ("confidence", "score", "prob") if _is_num(pred.get(k))), None)
            out.append(Instance(prompt, score, polys))
    # If every coordinate is in 0..1 the API returned normalised points: scale them to pixels.
    coords = [v for i in out for p in i.polygons for pt in p for v in pt]
    if coords and max(coords) <= 1.0:
        w, h = size
        for i in out:
            i.polygons = [[(x * w, y * h) for x, y in p] for p in i.polygons]
    return out


def render(img: Image.Image, insts: list[Instance], prompts: list[str], title: str) -> Image.Image:
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    color = {p: PALETTE[i % len(PALETTE)] for i, p in enumerate(prompts)}
    for inst in insts:
        for poly in inst.polygons:
            d.polygon(poly, fill=color[inst.prompt] + "80", outline=color[inst.prompt], width=2)
    for inst in insts:
        x, y = inst.anchor()
        tag = inst.prompt + (f" {inst.score:.2f}" if inst.score is not None else "")
        d.rectangle((x - 3, y - 8, x + 7 * len(tag) + 3, y + 8), fill="#000000b0")
        d.text((x, y - 6), tag, fill="white")
    d.rectangle((0, 0, img.width, 20), fill="#000000bb")
    d.text((6, 4), title, fill="white")
    return Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("images", nargs="+", type=Path)
    ap.add_argument("--prompts", default=DEFAULT_PROMPTS, help="comma list of concepts to segment (max 16)")
    ap.add_argument("--thresh", type=float, default=0.5, help="output_prob_thresh: lower = more instances, more false ones")
    args = ap.parse_args()

    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
    except ImportError:
        pass
    key = os.environ.get("ROBOFLOW_API_KEY", "")
    if not key:
        sys.exit("manca ROBOFLOW_API_KEY in .env (chiave gratuita su app.roboflow.com -> Settings -> API Keys)")
    prompts = [p.strip() for p in args.prompts.split(",") if p.strip()]
    if len(prompts) > 16:
        sys.exit("SAM 3 accetta al massimo 16 prompt per chiamata")

    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "sam3_runs.jsonl").open("a") as log:
        for path in args.images:
            img, jpeg = load_image(path)
            t0 = time.perf_counter()
            try:
                insts = segment(jpeg, prompts, key, args.thresh, img.size, OUT / f"{path.stem}.sam3.raw.json")
                err = None
            except Exception as e:
                insts, err = [], f"{type(e).__name__}: {e}"
            secs = time.perf_counter() - t0

            total = img.width * img.height
            stats = {}
            for p in prompts:
                mine = [i for i in insts if i.prompt == p]
                stats[p] = {
                    "instances": len(mine),
                    "area_pct": round(100 * sum(i.area() for i in mine) / total, 1),
                    "max_score": max((i.score for i in mine if i.score is not None), default=None),
                }
            log.write(json.dumps({"ts": time.time(), "image": path.name, "seconds": round(secs, 3), "thresh": args.thresh,
                                  "error": err, "stats": stats}) + "\n")

            sheet = Image.new("RGB", (img.width * 2, img.height))
            sheet.paste(img, (0, 0))
            sheet.paste(render(img, insts, prompts, f"SAM 3  {secs:.2f}s  {len(insts)} istanze"), (img.width, 0))
            out_img = OUT / f"{path.stem}.sam3.jpg"
            sheet.save(out_img, quality=88)

            print(f"\n== {path.name} -> {out_img.relative_to(ROOT)}   ({secs:.2f}s)")
            if err:
                print(f"ERRORE {err}")
                continue
            print(f"{'prompt':20} {'istanze':>8} {'area %':>8} {'score max':>10}")
            for p, s in stats.items():
                sc = f"{s['max_score']:.2f}" if s["max_score"] is not None else "-"
                print(f"{p:20} {s['instances']:>8} {s['area_pct']:>8} {sc:>10}")
            if not insts:
                print(f"Nessuna maschera letta: guarda la risposta grezza in logs/vision/{path.stem}.sam3.raw.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
