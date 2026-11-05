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
# The y-* clips are the segmented footage made by scripts/yoloe_footage.py (branch sam3) with English labels, e.g.
#   python scripts/yoloe_footage.py assets/footage/pov-robot.mov -o video/assets/yolo/en-pov.mp4 --start 0.5 --duration 6.1 --solid person
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
    "y-testa":   (YOLO / "en-testa.mp4", 0.0, 5.0, "crop=1280:720:0:180," + FIT),
    "y-tra":     (YOLO / "en-tra.mp4", 0.0, 5.5, FIT),
    "y-pov":     (YOLO / "en-pov.mp4", 0.0, 6.0, FIT),
    "y-arriva":  (YOLO / "en-arriva.mp4", 0.0, 7.5, FIT),
    "y-pov2":    (YOLO / "en-pov2.mp4", 0.0, 7.8, FIT),
    # vertical phone clip in a 16:9 frame: the same clip blurred and darkened behind fills the width
    "c-vert":    (FOOT / "g1-cammina-con-umani.mp4", 0.0, 4.85,
                  "split[a][b];[a]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,boxblur=40:4,"
                  "eq=brightness=-0.12:saturation=0.85[bg];[b]scale=-2:1080[fg];[bg][fg]overlay=(W-w)/2:0"),
    # interviews (phone video; the sound comes from the recorder, see INTERVIEW_AUDIO) and the silent looks to camera
    "i-romeo":       (FOOT / "int-romeo.mp4", 0.0, 9.8, FIT),
    "i-puddu":       (FOOT / "int-puddu.mp4", 0.0, 14.8, FIT),
    "i-rios":        (FOOT / "int-rios.mp4", 0.0, 13.15, FIT),
    "i-team":        (FOOT / "int-team.mp4", 0.0, 9.7, FIT),
    "i-romeo-muto":  (FOOT / "int-romeo-muto.mp4", 0.0, 7.7, FIT),
    "i-puddu-muto":  (FOOT / "int-puddu-muto.mp4", 0.0, 5.7, FIT),
    "i-rios-muto":   (FOOT / "int-rios-muto.mp4", 0.0, 6.1, FIT),
    # Francesco's screen recording (2852x1984, Retina): the chat box while the mission is sent, and the whole dashboard
    "r-chat":        (FOOT / "r1-dashboard-chat.mov", 5.0, 3.6, "crop=1600:900:170:1080," + FIT),
    "r-typing":      (FOOT / "r1-dashboard-chat.mov", 0.6, 4.6, "crop=1600:900:170:1080," + FIT),
    "r-full":        (FOOT / "r1-dashboard-chat.mov", 0.0, 27.68, "crop=2580:1451:120:200," + FIT),
    "r-full-low":    (FOOT / "r1-dashboard-chat.mov", 10.0, 17.68, "crop=2580:1451:120:533," + FIT),  # chat steps above the subtitles
    # Francesco's second recording (26.7 s): "Grok 4.5" in the header, simulator + segmented objects + depth side by side, chat
    "r2-full":       (FOOT / "r2-dashboard-finale.mov", 0.0, 26.7, "crop=2580:1451:120:200," + FIT),
    "r2-low":        (FOOT / "r2-dashboard-finale.mov", 9.0, 17.7, "crop=2580:1451:120:533," + FIT),
    "r2-chat":       (FOOT / "r2-dashboard-finale.mov", 0.8, 4.4, "crop=1600:900:170:1080," + FIT),
    "r2-percep":     (FOOT / "r2-dashboard-finale.mov", 8.0, 18.7, "crop=1450:816:1240:460," + FIT),
    "r-steps":       (FOOT / "r1-dashboard-chat.mov", 14.0, 13.6, "crop=1760:990:170:900," + FIT),
    "r-objects":     (FOOT / "r1-dashboard-chat.mov", 14.0, 13.6, "crop=1440:810:1250:400," + FIT),
    "r-mujoco":      (FOOT / "r1-dashboard-chat.mov", 8.0, 19.6, "crop=1060:596:180:570," + FIT),
}
# Recorder track -> phone timeline: phone_t = recorder_t + offset (s). Measured by cross-correlating the phone's own audio
# with the recorder (peak z 32-79, same offset within 1 ms on both halves of each take: no drift).
INTERVIEW_AUDIO = {"romeo": 0.930, "puddu": 0.666, "rios": -5.665, "team": 1.619}
LOUDNORM = "loudnorm=I=-18:TP=-2:LRA=11"
# id: (photo, (left, top, right, bottom) as fractions of the upright photo, giving a 16:9 crop)
PHOTOS = {
    "img-gru":       (FOOT / "foto-g1-appeso-alla-gru.jpg", (0.0, 0.22, 1.0, 0.64)),
    "img-seduto":    (FOOT / "foto-g1-cane-guinzaglio.heic", (0.0, 0.125, 1.0, 0.875)),
    "img-perplesso": (FOOT / "foto-team-perplesso.heic", (0.0, 0.15, 1.0, 0.57)),
    "img-conumano":  (FOOT / "foto-g1-con-umano.heic", (0.0, 0.14, 1.0, 0.56)),
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
    for f in VO.glob("*.wav"):  # voice lines, levelled like the interviews
        dst = d / f"vo-{f.name}"
        if not fresh(dst) or dst.stat().st_mtime < f.stat().st_mtime:
            run(["ffmpeg", "-v", "error", "-y", "-i", str(f), "-af", LOUDNORM, "-ar", "48000", "-ac", "1", str(dst)])
    for who, off in INTERVIEW_AUDIO.items():  # recorder audio re-timed onto the phone video, same length as the video
        dst = d / f"int-{who}.wav"
        if fresh(dst):
            continue
        dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                              str(FOOT / f"int-{who}.mp4")], capture_output=True, text=True, check=True).stdout.strip()
        shift = f"adelay={round(off * 1000)}:all=1," if off > 0 else ""
        run(["ffmpeg", "-v", "error", "-y", "-ss", str(max(0.0, -off)), "-i", str(FOOT / f"int-{who}.ogg"),
             "-af", f"{shift}highpass=f=70,{LOUDNORM},apad,atrim=0:{dur}", "-ac", "1", "-ar", "48000", str(dst)])
        print("audio", dst.name)
    shutil.copy2(BRAG / "sfx" / "ui" / "mouseclick1.ogg", d / "click.ogg")
    shutil.copy2(BRAG / "music" / "happy-beats-business-moves-vol-12-by-ende-dot-app.mp3", d / "music2.mp3")
    amb = d / "ambient.wav"  # soft room air, 4 minutes, no events: placed at its film time so nothing ever repeats
    if not fresh(amb):
        run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anoisesrc=color=brown:amplitude=0.5:duration=240:seed=7",
             "-af", "highpass=f=40,lowpass=f=420,volume=0.18", "-ac", "2", "-ar", "48000", str(amb)])


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
