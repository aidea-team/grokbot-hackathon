"""Compare cloud object detectors on photos of a desk scene (desk, chair, PC).

Backends (all via HTTP API, nothing runs locally):
  sam3    Roboflow serverless SAM 3, text prompts -> masks + boxes   (needs ROBOFLOW_API_KEY)
  rfdetr  Roboflow serverless RF-DETR, COCO classes -> boxes         (needs ROBOFLOW_API_KEY + `pip install inference-sdk`)
  grok    Grok vision asked for JSON boxes, the "generic LLM" baseline (needs XAI_API_KEY)

Usage:
  python src/vision/detect_test.py desk1.jpg desk2.jpg
  python src/vision/detect_test.py desk.jpg --backends sam3,grok --prompts "desk,office chair,monitor"

Writes an annotated side-by-side image per photo to logs/vision/ and one JSONL line per call
(latency, detections) so results can be quoted as numbers.
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import requests
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "logs" / "vision"
MAX_SIDE = 1024
DEFAULT_PROMPTS = "desk,office chair,computer monitor,keyboard,computer mouse,laptop"
# COCO has no "desk": dining table is the closest class, monitors are "tv".
COCO_ALIASES = {"desk": "dining table", "table": "dining table", "office chair": "chair",
                "computer monitor": "tv", "monitor": "tv", "computer mouse": "mouse"}
PALETTE = ["#e6194b", "#3cb44b", "#4363d8", "#f58231", "#911eb4", "#008080", "#9a6324", "#800000"]


@dataclass
class Det:
    label: str
    score: float | None
    box: tuple[float, float, float, float]  # x0, y0, x1, y1 in pixels of the resized image
    polygon: list[tuple[float, float]] | None = None


@dataclass
class Result:
    backend: str
    seconds: float
    dets: list[Det] = field(default_factory=list)
    error: str | None = None


def load_image(path: Path) -> tuple[Image.Image, bytes]:
    img = Image.open(path).convert("RGB")
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=85)
    return img, buf.getvalue()


def _poly_box(points: list[tuple[float, float]]) -> tuple[float, float, float, float]:
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def _find_polygons(node) -> list[list[tuple[float, float]]]:
    """Roboflow's concept_segment per-prediction schema is not documented in the page we read, so look for
    anything shaped like a polygon (list of [x, y] pairs) under the prediction, whatever the key is."""
    found: list[list[tuple[float, float]]] = []
    if isinstance(node, list):
        if node and all(isinstance(p, (list, tuple)) and len(p) == 2 and all(isinstance(v, (int, float)) for v in p) for p in node):
            found.append([(float(p[0]), float(p[1])) for p in node])
        else:
            for item in node:
                found += _find_polygons(item)
    elif isinstance(node, dict):
        for v in node.values():
            found += _find_polygons(v)
    return found


def run_sam3(jpeg: bytes, prompts: list[str], key: str, raw_path: Path) -> list[Det]:
    r = requests.post(
        "https://serverless.roboflow.com/sam3/concept_segment",
        headers={"Authorization": f"Bearer {key}"},
        json={
            "image": {"type": "base64", "value": base64.b64encode(jpeg).decode()},
            "prompts": [{"type": "text", "text": p} for p in prompts],
            "output_prob_thresh": 0.5,
            "format": "polygon",
        },
        timeout=60,
    )
    r.raise_for_status()
    data = r.json()
    raw_path.write_text(json.dumps(data)[:200_000])  # keep the real schema around to fix the parser if needed
    dets: list[Det] = []
    for prompt, res in zip(prompts, data.get("prompt_results", [])):
        for pred in res.get("predictions", []):
            polys = _find_polygons(pred)
            score = next((pred[k] for k in ("confidence", "score", "prob") if isinstance(pred.get(k), (int, float))), None)
            if polys:
                biggest = max(polys, key=len)
                dets.append(Det(prompt, score, _poly_box(biggest), biggest))
    return dets


def run_rfdetr(jpeg: bytes, prompts: list[str], key: str, size: tuple[int, int]) -> list[Det]:
    from inference_sdk import InferenceHTTPClient  # lazy: optional dependency

    client = InferenceHTTPClient(api_url="https://serverless.roboflow.com", api_key=key)
    out = client.infer(Image.open(io.BytesIO(jpeg)), model_id="rfdetr-base")
    wanted = {COCO_ALIASES.get(p, p) for p in prompts}
    dets = []
    for p in out.get("predictions", []):
        if p["class"] in wanted:
            x, y, w, h = p["x"], p["y"], p["width"], p["height"]
            dets.append(Det(p["class"], p["confidence"], (x - w / 2, y - h / 2, x + w / 2, y + h / 2)))
    return dets


def run_grok(jpeg: bytes, prompts: list[str], key: str, size: tuple[int, int]) -> list[Det]:
    text = (
        "Detect every instance of these objects in the image: " + ", ".join(prompts) + ". "
        'Reply with JSON only: {"detections":[{"label":"<one of the names above>","box":[x0,y0,x1,y1]}]} '
        "with box coordinates normalised to 0..1 relative to image width and height (origin top-left). "
        "Skip objects that are not visible."
    )
    r = requests.post(
        "https://api.x.ai/v1/responses",
        headers={"Authorization": f"Bearer {key}"},
        json={
            "model": "grok-4.3",
            "reasoning": {"effort": "none"},
            "store": False,
            "input": [{"role": "user", "content": [
                {"type": "input_image", "image_url": "data:image/jpeg;base64," + base64.b64encode(jpeg).decode(), "detail": "high"},
                {"type": "input_text", "text": text},
            ]}],
        },
        timeout=90,
    )
    r.raise_for_status()
    body = r.json()
    out_text = "".join(
        c.get("text", "") for item in body.get("output", []) if item.get("type") == "message" for c in item.get("content", [])
    )
    start, end = out_text.find("{"), out_text.rfind("}")
    parsed = json.loads(out_text[start:end + 1])
    w, h = size
    return [Det(d["label"], None, (d["box"][0] * w, d["box"][1] * h, d["box"][2] * w, d["box"][3] * h)) for d in parsed.get("detections", [])]


def annotate(img: Image.Image, dets: list[Det], labels: list[str], title: str) -> Image.Image:
    base = img.copy().convert("RGBA")
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for det in dets:
        color = PALETTE[labels.index(det.label) % len(PALETTE)] if det.label in labels else "#ffffff"
        if det.polygon:
            d.polygon(det.polygon, fill=color + "66", outline=color)
        d.rectangle(det.box, outline=color, width=3)
        tag = det.label + (f" {det.score:.2f}" if det.score is not None else "")
        d.rectangle((det.box[0], det.box[1] - 16, det.box[0] + 7 * len(tag) + 6, det.box[1]), fill=color)
        d.text((det.box[0] + 3, det.box[1] - 14), tag, fill="white")
    d.rectangle((0, 0, base.width, 20), fill="#000000bb")
    d.text((6, 4), title, fill="white")
    return Image.alpha_composite(base, layer).convert("RGB")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("images", nargs="+", type=Path)
    ap.add_argument("--backends", default="sam3,grok", help="comma list of: sam3, rfdetr, grok")
    ap.add_argument("--prompts", default=DEFAULT_PROMPTS, help="comma list of objects to find")
    args = ap.parse_args()

    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
    except ImportError:
        pass
    rf_key, xai_key = os.environ.get("ROBOFLOW_API_KEY", ""), os.environ.get("XAI_API_KEY", "")
    prompts = [p.strip() for p in args.prompts.split(",") if p.strip()]
    backends = [b.strip() for b in args.backends.split(",") if b.strip()]
    needs = {"sam3": ("ROBOFLOW_API_KEY", rf_key), "rfdetr": ("ROBOFLOW_API_KEY", rf_key), "grok": ("XAI_API_KEY", xai_key)}
    for b in backends:
        if b not in needs:
            sys.exit(f"backend sconosciuto: {b}")
        if not needs[b][1]:
            sys.exit(f"{b}: manca {needs[b][0]} in .env")

    OUT.mkdir(parents=True, exist_ok=True)
    log = (OUT / "runs.jsonl").open("a")
    for path in args.images:
        img, jpeg = load_image(path)
        tiles, rows = [], []
        for b in backends:
            t0 = time.perf_counter()
            res = Result(b, 0.0)
            try:
                if b == "sam3":
                    res.dets = run_sam3(jpeg, prompts, rf_key, OUT / f"{path.stem}.sam3.raw.json")
                elif b == "rfdetr":
                    res.dets = run_rfdetr(jpeg, prompts, rf_key, img.size)
                else:
                    res.dets = run_grok(jpeg, prompts, xai_key, img.size)
            except Exception as e:  # keep going: one failing backend must not hide the others
                res.error = f"{type(e).__name__}: {e}"
            res.seconds = time.perf_counter() - t0
            counts = {p: sum(1 for d in res.dets if d.label == COCO_ALIASES.get(p, p) or d.label == p) for p in prompts}
            rows.append((b, res, counts))
            tiles.append(annotate(img, res.dets, prompts + [COCO_ALIASES.get(p, p) for p in prompts], f"{b}  {res.seconds:.2f}s  {len(res.dets)} det"))
            log.write(json.dumps({
                "ts": time.time(), "image": path.name, "backend": b, "seconds": round(res.seconds, 3), "error": res.error,
                "counts": counts, "dets": [{"label": d.label, "score": d.score, "box": [round(v, 1) for v in d.box]} for d in res.dets],
            }) + "\n")
        sheet = Image.new("RGB", (img.width * len(tiles), img.height))
        for i, t in enumerate(tiles):
            sheet.paste(t, (i * img.width, 0))
        out_img = OUT / f"{path.stem}.compare.jpg"
        sheet.save(out_img, quality=88)

        print(f"\n== {path.name} -> {out_img.relative_to(ROOT)}")
        print(f"{'backend':8} {'sec':>6}  " + "  ".join(f"{p[:14]:>14}" for p in prompts))
        for b, res, counts in rows:
            if res.error:
                print(f"{b:8} {res.seconds:6.2f}  ERRORE {res.error[:120]}")
            else:
                print(f"{b:8} {res.seconds:6.2f}  " + "  ".join(f"{counts[p]:>14}" for p in prompts))
    log.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
