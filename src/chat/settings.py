"""Runtime settings of the agent loop, editable from the web UI (settings dialog) without restarting.

Every optimisation that could change the dog's behaviour is a setting here, so it can be switched off if it
regresses. DEFAULTS KEEP THE ORIGINAL BEHAVIOUR, except two pure wins that change nothing the model sees
(parallel camera capture, HTTP connection reuse). Read at the start of every step, so changes apply live.
Persisted to logs/settings.json.
"""
from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

import cameras

RESOLUTIONS = ["320x240", "512x384", "640x480"]
EFFORTS = ["", "none", "low", "medium", "high"]  # "" = OPENAI_REASONING_EFFORT from .env


@dataclass
class Settings:
    # --- cameras (all brains)
    cams: list[str] = field(default_factory=lambda: [c.name for c in cameras.CAMERAS])  # "front" always on
    resolution: str = "512x384"      # simulator only: the real dog's streams have their own size
    jpeg_quality: int = 80           # simulator only (30-95)
    parallel_capture: bool = True    # grab the cameras at the same time instead of one after the other
    # --- JEV (Decisions API)
    jev_session: bool = True         # reuse the HTTP/TLS connection (+ warm it up at mission start)
    jev_multi: bool = False          # allow a 2nd action (turn/walk) from the same call; simulator only
    jev_multi_min_conf: float = 0.85 # both actions must reach this confidence
    jev_reduced_angles: bool = False # no +-90 deg turns: fewer, calmer choices
    jev_finish_llm: bool = False     # on `finish`, one LLM call writes the answer (JEV cannot write text)
    # --- LLM agent (Responses API)
    llm_effort: str = ""             # "" = from .env
    llm_thought: bool = True         # ask for the `thought` field (output tokens = latency)
    llm_log_steps: int = 15          # previous steps shown to the model

    def width_height(self) -> tuple[int, int]:
        w, h = self.resolution.split("x")
        return int(w), int(h)


DEFAULTS = Settings()


def sanitize(data: dict, base: Settings | None = None) -> Settings:
    """Apply `data` over `base` (or the defaults), ignoring unknown keys and clamping bad values."""
    out = Settings(**asdict(base or DEFAULTS))
    names = {f.name for f in fields(Settings)}
    for k, v in data.items():
        if k not in names:
            continue
        try:
            if k == "cams":
                valid = [c for c in cameras.BY_NAME if c in list(v)]
                v = ["front"] + [c for c in valid if c != "front"]
            elif k == "resolution":
                v = v if v in RESOLUTIONS else out.resolution
            elif k == "jpeg_quality":
                v = min(95, max(30, int(v)))
            elif k == "jev_multi_min_conf":
                v = min(0.99, max(0.5, float(v)))
            elif k == "llm_effort":
                v = v if v in EFFORTS else ""
            elif k == "llm_log_steps":
                v = min(30, max(1, int(v)))
            else:
                v = bool(v)
        except (TypeError, ValueError):
            continue
        setattr(out, k, v)
    return out


class SettingsStore:
    def __init__(self, path: Path | None = None):
        self._path, self._lock = path, threading.Lock()
        self._s = DEFAULTS
        if path is not None and path.exists():
            try:
                self._s = sanitize(json.loads(path.read_text()))
            except (OSError, ValueError):
                pass

    def get(self) -> Settings:
        with self._lock:
            return Settings(**asdict(self._s))  # a copy: a step sees one consistent snapshot

    def update(self, data: dict) -> Settings:
        with self._lock:
            self._s = sanitize(data, self._s)
            self._save()
            return Settings(**asdict(self._s))

    def reset(self) -> Settings:
        with self._lock:
            self._s = Settings(**asdict(DEFAULTS))
            self._save()
            return Settings(**asdict(self._s))

    def _save(self) -> None:
        if self._path is None:
            return
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(json.dumps(asdict(self._s), indent=1))
        except OSError:
            pass
