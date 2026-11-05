"""Build the HyperFrames project's media from the raw footage: trimmed/cropped H.264 1080p30 proxies (keyframe every
second, so seeking never freezes), 16:9 crops of the photos, room tone, voice lines, music, sound effects and fonts.

Everything lands in video/film/assets/ (ignored by git: it is derived from assets/footage/, which is not in git either).

    python video/make_assets.py          # build what is missing
    python video/make_assets.py --force  # rebuild everything
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FOOT = REPO / "assets" / "footage"
YOLO = REPO / "video" / "assets" / "yolo"
VO = REPO / "video" / "assets" / "vo"
BRAG = REPO / ".claude" / "skills" / "brag" / "assets"
OUT = REPO / "video" / "film" / "assets"
FORCE = "--force" in sys.argv

FIT = "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080"
# Phone HDR (HLG) to SDR bt709, otherwise the renderer takes its slow HDR path and the colours come out flat.
TONEMAP = ("zscale=tin=arib-std-b67:min=bt2020nc:pin=bt2020:rin=tv:t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,"
           "tonemap=tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p,")


def is_hlg(src: Path) -> bool:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=color_transfer",
                          "-of", "csv=p=0", str(src)], capture_output=True, text=True).stdout.strip()
    return out in ("arib-std-b67", "smpte2084")
# id: (source, start s, duration s, ffmpeg crop/scale chain applied after rotation)
CLIPS = {
    "c-cane":    (FOOT / "g1-porta-a-spasso-il-cane.mp4", 0.0, 10.45, FIT),
    "c-testa":   (FOOT / "g1-scrivania-tasti-frenetici.mp4", 10.8, 2.45, FIT),
    "c-hacker":  (FOOT / "g1-scrivania-tasti-frenetici.mp4", 0.0, 7.0, FIT),
    "c-closeup": (FOOT / "g1-tasti-closeup.mov", 0.8, 2.4, "crop=2160:1215:0:1300," + FIT),
    "c-mano":    (FOOT / "g1-mano-hackertyper.mp4", 0.8, 2.2, "crop=1080:608:0:800," + FIT),
    "c-scrive":  (FOOT / "g1-tasti-si-gira.mov", 3.0, 2.5, "crop=2160:1215:0:1900," + FIT),
    "c-guarda":  (FOOT / "g1-arriva-alla-scrivania.mov", 33.4, 2.6, "crop=1440:810:1230:250," + FIT),
    "c-vuota":   (FOOT / "g1-arriva-alla-scrivania.mov", 15.0, 5.0, FIT),
    "c-tag":     (FOOT / "g1-extra-212938.mp4", 29.0, 7.0, FIT),
    "y-testa":   (YOLO / "yolo-testa-g1.mp4", 2.0, 5.0, "crop=1280:720:0:180," + FIT),
    "y-tra":     (YOLO / "yolo-g1-tra-partecipanti.mp4", 8.0, 5.5, FIT),
    "y-pov":     (YOLO / "yolo-pov-robot.mp4", 0.5, 6.0, FIT),
    "y-arriva":  (YOLO / "yolo-g1-arriva-scrivania.mp4", 3.5, 5.0, FIT),
}
# id: (photo, (left, top, right, bottom) as fractions of the upright photo, giving a 16:9 crop)
PHOTOS = {
    "img-gru":       (FOOT / "foto-g1-appeso-alla-gru.jpg", (0.0, 0.22, 1.0, 0.64)),
    "img-seduto":    (FOOT / "foto-g1-cane-guinzaglio.heic", (0.0, 0.125, 1.0, 0.875)),
    "img-perplesso": (FOOT / "foto-team-perplesso.heic", (0.0, 0.15, 1.0, 0.57)),
}


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def fresh(dst: Path) -> bool:
    return dst.exists() and not FORCE


def clips() -> None:
    d = OUT / "clips"
    d.mkdir(parents=True, exist_ok=True)
    for cid, (src, ss, t, vf) in CLIPS.items():
        dst = d / f"{cid}.mp4"
        if fresh(dst):
            continue
        if not src.exists():
            print(f"skip {cid}: manca {src.name}")
            continue
        try:
            pre = TONEMAP if is_hlg(src) else ""
            run(["ffmpeg", "-v", "error", "-y", "-ss", str(ss), "-t", str(t), "-i", str(src), "-an", "-vf", pre + vf + ",fps=30,format=yuv420p",
                 "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-g", "30", "-color_primaries", "bt709", "-color_trc", "bt709",
                 "-colorspace", "bt709", "-movflags", "+faststart", str(dst)])
            print("clip", cid)
        except subprocess.CalledProcessError:
            dst.unlink(missing_ok=True)
            print(f"skip {cid}: {src.name} non leggibile (ancora in scrittura?)")


def photos() -> None:
    import pillow_heif
    from PIL import Image, ImageOps
    pillow_heif.register_heif_opener()
    d = OUT / "img"
    d.mkdir(parents=True, exist_ok=True)
    for pid, (src, (l, t, r, b)) in PHOTOS.items():
        dst = d / f"{pid}.jpg"
        if fresh(dst):
            continue
        im = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
        w, h = im.size
        box = (int(l * w), int(t * h), int(r * w), int(b * h))
        im.crop(box).resize((2880, 1620), Image.LANCZOS).save(dst, quality=90)  # 1.5x: room for a slow push
        print("photo", pid)


def audio() -> None:
    d = OUT / "audio"
    d.mkdir(parents=True, exist_ok=True)
    tone = d / "roomtone.wav"
    if not fresh(tone):
        run(["ffmpeg", "-v", "error", "-y", "-ss", "14", "-t", "14", "-i", str(FOOT / "g1-arriva-alla-scrivania.mov"),
             "-vn", "-ac", "2", "-ar", "48000", "-af", "highpass=f=80,lowpass=f=6000", str(tone)])
    music = BRAG / "music" / "happy-beats-business-moves-vol-11-by-ende-dot-app.mp3"
    shutil.copy2(music, d / "music.mp3")
    for i in range(1, 9):
        shutil.copy2(BRAG / "sfx" / "keyboard" / f"keypress-{i:03d}.wav", d / f"key-{i}.wav")
    for f in VO.glob("*.wav"):
        shutil.copy2(f, d / f"vo-{f.name}")


def static() -> None:
    fonts = OUT / "fonts"
    fonts.mkdir(parents=True, exist_ok=True)
    for f in (REPO / "src" / "ui" / "static" / "fonts").glob("Artific-*.woff2"):
        shutil.copy2(f, fonts / f.name)
    shutil.copy2(REPO / "video" / "assets" / "aidea-logo.webp", OUT / "aidea-logo.webp")


if __name__ == "__main__":
    static()
    audio()
    photos()
    clips()
