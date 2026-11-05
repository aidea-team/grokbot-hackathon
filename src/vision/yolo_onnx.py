"""Small instance-segmentation models on CPU with onnxruntime (no torch), for the live view.

  yolo    YOLO26n-seg, the 80 COCO classes (chair, tv, laptop, keyboard, mouse, dining table, person ... no "desk"):
          ~70 ms per frame on an i7-1360P (~14 fps)
  yoloe   YOLOE-26s-seg "embin": open vocabulary like SAM 3, the classes are text embeddings given at run time (up to 16 at once):
          ~220-290 ms per frame (~3-4 fps). The embeddings of an office vocabulary are precomputed in yoloe_vocab.npz
          (scripts/yoloe_vocab.py adds words; it needs the 260 MB text encoder, only there)

Weights (AGPL-3.0, Ultralytics) are downloaded on first use to vendor/models/ (gitignored) and checked against a SHA-256.
Both take a 640x640 letterbox; masks come from 32 prototypes at 160x160 like every YOLO-seg.
"""
from __future__ import annotations

import ast
import hashlib
import urllib.request
from pathlib import Path

import cv2
import numpy as np

from segmenters import ALIASES, Detection

ROOT = Path(__file__).resolve().parents[2]
MODELS = ROOT / "vendor" / "models"
VOCAB = Path(__file__).resolve().parent / "yoloe_vocab.npz"
WEIGHTS = {
    "yolo26n-seg.onnx": ("https://huggingface.co/DeveloperDobby/yolo26n-seg/resolve/main/yolo26n-seg.onnx",
                         "1f2416b179a84cb832c424f8e3cae4d6468e07f02c527d563008b73898f72dbe"),
    "yoloe-26s-seg-embin.onnx": ("https://huggingface.co/harvestsu/yoloe-26s-seg-onnx/resolve/main/embin/yoloe-26s-seg-embin.onnx",
                                 "4336f6ead3f6bacabd2111f40d19cb6ae99e7d17e0fb21823a347be9ff28fcac"),
}


def weights(name: str) -> Path:
    path = MODELS / name
    url, sha = WEIGHTS[name]
    if not path.exists():
        MODELS.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".part")
        print(f"downloading {name} ...")
        urllib.request.urlretrieve(url, tmp)
        tmp.rename(path)
    if hashlib.sha256(path.read_bytes()).hexdigest() != sha:
        path.unlink()
        raise RuntimeError(f"{name}: checksum diverso da quello atteso, file cancellato (riprova)")
    return path


def _session(path: Path, threads: int):
    import onnxruntime as ort
    so = ort.SessionOptions()
    so.intra_op_num_threads = threads  # leave cores to the simulator / stereo matcher
    so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    return ort.InferenceSession(str(path), so, providers=["CPUExecutionProvider"])


def _letterbox(rgb: np.ndarray, n: int = 640) -> tuple[np.ndarray, float, int, int]:
    h, w = rgb.shape[:2]
    r = min(n / h, n / w)
    nw, nh = round(w * r), round(h * r)
    top, left = (n - nh) // 2, (n - nw) // 2
    img = cv2.copyMakeBorder(cv2.resize(rgb, (nw, nh)), top, n - nh - top, left, n - nw - left, cv2.BORDER_CONSTANT, value=(114, 114, 114))
    return np.ascontiguousarray(img.transpose(2, 0, 1)[None], dtype=np.float32) / 255.0, r, left, top


def _masks(coeffs: np.ndarray, boxes: np.ndarray, proto: np.ndarray, r: float, left: int, top: int, h0: int, w0: int,
           n: int = 640) -> list[np.ndarray]:
    """Prototype masks -> one bool mask per detection at the frame size (cropped to its box, letterbox padding removed)."""
    c, mh, mw = proto.shape
    s = mw / n
    logits = (coeffs @ proto.reshape(c, -1)).reshape(-1, mh, mw)
    nh, nw = round(h0 * r * s), round(w0 * r * s)  # content area at prototype scale
    t, lft = round(top * s), round(left * s)
    out = []
    for m, (x1, y1, x2, y2) in zip(logits, boxes * s):
        crop = np.zeros_like(m)
        y1, y2, x1, x2 = max(int(y1), 0), int(np.ceil(y2)), max(int(x1), 0), int(np.ceil(x2))
        crop[y1:y2, x1:x2] = m[y1:y2, x1:x2]
        content = crop[t:t + nh, lft:lft + nw]
        out.append(cv2.resize(content, (w0, h0), interpolation=cv2.INTER_LINEAR) > 0)
    return out


def _detections(labels: list[str], scores: np.ndarray, boxes: np.ndarray, masks: list[np.ndarray], r: float, left: int, top: int):
    out = []
    for lab, sc, b, m in zip(labels, scores, boxes, masks):
        if m.sum() < 20:
            continue
        x1, y1, x2, y2 = (b[0] - left) / r, (b[1] - top) / r, (b[2] - left) / r, (b[3] - top) / r
        out.append(Detection(ALIASES.get(lab, lab), float(sc), m, (float(x1), float(y1), float(x2), float(y2))))
    return out


class YoloSegmenter:
    """YOLO26n-seg, COCO classes. The prompts are ignored: it sees its 80 classes, all of them."""

    def __init__(self, prompts: list[str] | None = None, conf: float = 0.35, threads: int = 4):
        self.sess = _session(weights("yolo26n-seg.onnx"), threads)
        self.names = ast.literal_eval(self.sess.get_modelmeta().custom_metadata_map["names"])
        self.conf = conf

    def __call__(self, rgb: np.ndarray) -> list[Detection]:
        blob, r, left, top = _letterbox(rgb)
        pred, proto = self.sess.run(None, {self.sess.get_inputs()[0].name: blob})
        p = pred[0].T  # (8400, 4 box + 80 classes + 32 mask coefficients); class scores are already sigmoids, no NMS inside
        cls, sc = p[:, 4:84].argmax(1), p[:, 4:84].max(1)
        k = sc > self.conf
        p, cls, sc = p[k], cls[k], sc[k]
        boxes = np.c_[p[:, 0] - p[:, 2] / 2, p[:, 1] - p[:, 3] / 2, p[:, 0] + p[:, 2] / 2, p[:, 1] + p[:, 3] / 2]
        keep = np.array(cv2.dnn.NMSBoxesBatched([[float(x1), float(y1), float(x2 - x1), float(y2 - y1)] for x1, y1, x2, y2 in boxes],
                                                sc.tolist(), cls.tolist(), self.conf, 0.45), dtype=int).reshape(-1) if len(p) else np.zeros(0, int)
        boxes, cls, sc, coef = boxes[keep], cls[keep], sc[keep], p[keep, 84:]
        h0, w0 = rgb.shape[:2]
        return _detections([self.names[int(c)] for c in cls], sc, boxes, _masks(coef, boxes, proto[0], r, left, top, h0, w0), r, left, top)


class YoloeSegmenter:
    """YOLOE-26s-seg with text classes from the precomputed office vocabulary (yoloe_vocab.npz)."""

    def __init__(self, prompts: list[str], conf: float = 0.25, threads: int = 4):
        vocab = np.load(VOCAB)
        known = {str(w): e for w, e in zip(vocab["words"], vocab["embeddings"].astype(np.float32))}
        missing = [p for p in prompts if p.lower() not in known]
        if missing:
            raise ValueError(f"YOLOE non conosce {', '.join(missing)}: usa le parole di yoloe_vocab.npz "
                             f"({', '.join(sorted(known))}) o aggiungile con scripts/yoloe_vocab.py")
        self.words = [p.lower() for p in prompts][:16]
        self.emb = np.zeros((1, 16, 512), np.float32)
        for i, wd in enumerate(self.words):
            self.emb[0, i] = known[wd]
        self.sess = _session(weights("yoloe-26s-seg-embin.onnx"), threads)
        self.conf = conf

    def __call__(self, rgb: np.ndarray) -> list[Detection]:
        blob, r, left, top = _letterbox(rgb)
        det, proto = self.sess.run(None, {"images": blob, "class_embeddings": self.emb})
        d = det[0]  # (300, 6 + 32): x1 y1 x2 y2 conf class, NMS already applied
        d = d[(d[:, 4] >= self.conf) & (d[:, 5] < len(self.words))]
        h0, w0 = rgb.shape[:2]
        return _detections([self.words[int(c)] for c in d[:, 5]], d[:, 4], d[:, :4],
                           _masks(d[:, 6:], d[:, :4], proto[0], r, left, top, h0, w0), r, left, top)


if __name__ == "__main__":  # python src/vision/yolo_onnx.py  -> download + verify both models
    for name in WEIGHTS:
        print(name, weights(name))
