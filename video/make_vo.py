"""Generate the video's voice lines with Grok TTS (POST /v1/tts) from vo-lines.json.

Writes video/assets/vo/<id>.wav (48 kHz mono) and <id>.json with the character timings, used for the subtitles.
Needs XAI_API_KEY in .env. Re-run after editing a line: only changed lines are regenerated.

    python video/make_vo.py            # all lines
    python video/make_vo.py g1-02      # one line
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "assets" / "vo"
LANG = "it"


def env_key() -> str:
    key = os.environ.get("XAI_API_KEY", "")
    env = HERE.parent / ".env"
    if not key and env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("XAI_API_KEY="):
                key = line.split("=", 1)[1].strip()
    if not key:
        sys.exit("manca XAI_API_KEY in .env")
    return key


def tts(text: str, voice: str, speed: float, key: str) -> dict:
    body = {"text": text, "voice_id": voice, "language": LANG, "speed": speed, "with_timestamps": True,
            "output_format": {"codec": "wav", "sample_rate": 48000}}
    req = urllib.request.Request("https://api.x.ai/v1/tts", json.dumps(body).encode(),
                                 {"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def main() -> None:
    global LANG
    spec = json.loads((HERE / "vo-lines.json").read_text())
    LANG = spec.get("language", "it")
    only = set(sys.argv[1:])
    key = env_key()
    OUT.mkdir(parents=True, exist_ok=True)
    for line in spec["lines"]:
        if only and line["id"] not in only:
            continue
        voice = spec["voices"][line["voice"]]
        speed = line.get("speed", spec.get("speed", {}).get(line["voice"], 1.0))
        digest = hashlib.sha1(json.dumps([line["text"], voice, speed, LANG]).encode()).hexdigest()[:12]
        meta = OUT / f"{line['id']}.json"
        if meta.exists() and json.loads(meta.read_text()).get("digest") == digest and not only:
            continue
        r = tts(line["text"], voice, speed, key)
        raw = OUT / f"{line['id']}.raw.wav"
        raw.write_bytes(base64.b64decode(r["audio"]))
        wav = OUT / f"{line['id']}.wav"  # re-mux: the streamed WAV header has no real length
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-ac", "1", "-ar", "48000", str(wav)], check=True)
        raw.unlink()
        dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(wav)],
                                   capture_output=True, text=True, check=True).stdout)
        meta.write_text(json.dumps({"id": line["id"], "voice": voice, "text": line["text"], "subtitle": line["subtitle"],
                                    "duration": round(dur, 3), "digest": digest,
                                    "timestamps": r.get("audio_timestamps")}, ensure_ascii=False, indent=1))
        print(f"{line['id']:8s} {voice:8s} {dur:5.2f}s  {line['subtitle']}")


if __name__ == "__main__":
    main()
