"""Segmentation backends for live perception. Each one maps an RGB frame to Detections (mask at the frame's own size).

  yoloe  YOLOE-26s-seg on CPU (onnxruntime): text prompts from an office vocabulary, ~3-4 fps          (yolo_onnx.py)
  yolo   YOLO26n-seg on CPU: the 80 COCO classes (no "desk"), ~14 fps                                  (yolo_onnx.py)
  sam3   Meta SAM 3 on Roboflow serverless: any text prompt, best masks, 1-4 s per call -> sampled every few seconds.
"""
from __future__ import annotations

import io
import os
from dataclasses import dataclass

import numpy as np
from PIL import Image


# what the models are asked / call things -> what we show (YOLOE finds monitors much better as "tv"; COCO has no "desk")
ALIASES = {"tv": "monitor", "computer monitor": "monitor", "computer mouse": "mouse", "dining table": "table/desk"}


@dataclass
class Detection:
    label: str
    score: float | None
    mask: np.ndarray                          # (h, w) bool, same size as the analysed frame
    box: tuple[float, float, float, float]    # x0, y0, x1, y1 in pixels


def _box(mask: np.ndarray) -> tuple[float, float, float, float]:
    v, u = np.nonzero(mask)
    return (float(u.min()), float(v.min()), float(u.max()), float(v.max())) if len(u) else (0.0, 0.0, 0.0, 0.0)


class Sam3Segmenter:
    """Cloud, 1-4 s per call: the live loop samples it every few seconds (LivePerception.period_s)."""

    def __init__(self, prompts: list[str], thresh: float = 0.5, key: str | None = None):
        self.prompts, self.thresh = prompts, thresh
        self.key = key or os.environ.get("ROBOFLOW_API_KEY", "")
        if not self.key:
            raise RuntimeError("SAM 3: manca ROBOFLOW_API_KEY in .env")

    def __call__(self, rgb: np.ndarray) -> list[Detection]:
        import cv2
        from sam3_segment import segment
        buf = io.BytesIO()
        Image.fromarray(rgb).save(buf, "JPEG", quality=85)
        h, w = rgb.shape[:2]
        out = []
        for inst in segment(buf.getvalue(), self.prompts, self.key, self.thresh, (w, h)):
            mask = np.zeros((h, w), np.uint8)
            cv2.fillPoly(mask, [np.round(np.array(p)).astype(np.int32) for p in inst.polygons], 1)
            mask = mask.astype(bool)
            if mask.any():
                out.append(Detection(ALIASES.get(inst.prompt, inst.prompt), inst.score, mask, _box(mask)))
        return out


def _yoloe(prompts: list[str]):
    from yolo_onnx import YoloeSegmenter  # lazy: onnxruntime and the weights only when chosen
    return YoloeSegmenter(prompts)


def _yolo(prompts: list[str]):
    from yolo_onnx import YoloSegmenter
    return YoloSegmenter(prompts)


# name -> factory(prompts). The first one is the default of the live view.
BACKENDS = {"yoloe": _yoloe, "yolo": _yolo, "sam3": Sam3Segmenter}
