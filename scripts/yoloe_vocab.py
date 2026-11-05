"""Precompute YOLOE text embeddings for a vocabulary -> src/vision/yoloe_vocab.npz (a few KB, committed).

The live view then needs only the 43 MB detector, not the 260 MB text encoder. Run this only to add words:
  python scripts/yoloe_vocab.py                       # the default office vocabulary
  python scripts/yoloe_vocab.py "coffee machine" "fire extinguisher"   # add words to the existing file
Downloads (once, to vendor/models/): the YOLOE text encoder (MobileCLIP, ONNX) and OpenAI's CLIP BPE vocabulary.
"""
from __future__ import annotations

import gzip
import hashlib
import re
import sys
import urllib.request
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "vision"))
from yolo_onnx import MODELS, VOCAB, _session  # noqa: E402

ENCODER = ("text_encoder_pe.onnx", "https://huggingface.co/harvestsu/yoloe-26s-seg-onnx/resolve/main/embin/text_encoder_pe.onnx",
           "f6ae696fb76323e21e629399c347767ba9bf97005546fd607c71c6fe9b014db1")
BPE = ("bpe_simple_vocab_16e6.txt.gz", "https://raw.githubusercontent.com/openai/CLIP/main/clip/bpe_simple_vocab_16e6.txt.gz", None)
DEFAULT = ["desk", "table", "chair", "office chair", "tv", "monitor", "computer monitor", "screen", "laptop", "computer", "pc tower",
           "keyboard", "mouse", "computer mouse", "person", "cup", "mug", "bottle", "phone", "tablet", "book", "backpack", "bag", "box",
           "door", "window", "cabinet", "shelf", "sofa", "plant", "lamp", "printer", "whiteboard", "trash can", "robot", "robot dog",
           "cable", "headphones", "red cylinder", "blue cylinder"]


def fetch(name: str, url: str, sha: str | None) -> Path:
    path = MODELS / name
    if not path.exists():
        MODELS.mkdir(parents=True, exist_ok=True)
        print(f"downloading {name} ...")
        urllib.request.urlretrieve(url, path)
    if sha and hashlib.sha256(path.read_bytes()).hexdigest() != sha:
        path.unlink()
        raise SystemExit(f"{name}: unexpected checksum, deleted")
    return path


class ClipTokenizer:
    """OpenAI CLIP byte-level BPE (the reference algorithm, reading the official merges file)."""

    def __init__(self, bpe_path: Path):
        bs = list(range(33, 127)) + list(range(161, 173)) + list(range(174, 256))
        cs, n = bs[:], 0
        for b in range(256):
            if b not in bs:
                bs.append(b)
                cs.append(256 + n)
                n += 1
        self.byte_enc = dict(zip(bs, map(chr, cs)))
        merges = [tuple(m.split()) for m in gzip.open(bpe_path).read().decode("utf-8").split("\n")[1:49152 - 256 - 2 + 1]]
        vocab = list(self.byte_enc.values())
        vocab += [v + "</w>" for v in vocab] + ["".join(m) for m in merges] + ["<|startoftext|>", "<|endoftext|>"]
        self.enc = {v: i for i, v in enumerate(vocab)}
        self.ranks = {m: i for i, m in enumerate(merges)}

    def _bpe(self, token: str) -> tuple[str, ...]:
        word = tuple(token[:-1]) + (token[-1] + "</w>",)
        while len(word) > 1:
            best = min(((word[i], word[i + 1]) for i in range(len(word) - 1)), key=lambda p: self.ranks.get(p, 1e18))
            if best not in self.ranks:
                break
            new, i = [], 0
            while i < len(word):
                if i < len(word) - 1 and (word[i], word[i + 1]) == best:
                    new.append(word[i] + word[i + 1])
                    i += 2
                else:
                    new.append(word[i])
                    i += 1
            word = tuple(new)
        return word

    def __call__(self, text: str, length: int = 77) -> np.ndarray:
        ids = []
        for w in re.findall(r"[a-z]+|[0-9]|[^\sa-z0-9]+", " ".join(text.split()).lower()):
            ids += [self.enc[p] for p in self._bpe("".join(self.byte_enc[b] for b in w.encode()))]
        ids = [49406] + ids[:length - 2] + [49407]
        out = np.zeros((1, length), np.int32)
        out[0, :len(ids)] = ids
        return out


def main() -> int:
    words = [w.lower().strip() for w in sys.argv[1:]] or DEFAULT
    old = {}
    if VOCAB.exists():
        v = np.load(VOCAB)
        old = {str(w): e for w, e in zip(v["words"], v["embeddings"])}
    tok = ClipTokenizer(fetch(*BPE))
    enc = _session(fetch(*ENCODER), 4)
    for w in words:
        pe = enc.run(None, {"tokens": tok(w)})[0].reshape(-1)
        old[w] = (pe / np.linalg.norm(pe)).astype(np.float16)
    names = sorted(old)
    np.savez_compressed(VOCAB, words=np.array(names), embeddings=np.stack([old[n] for n in names]))
    print(f"{VOCAB}: {len(names)} words")
    return 0


if __name__ == "__main__":
    sys.exit(main())
