"""Write the HyperFrames project in video/film/ (index.html + compositions/*.html) from the timeline below.

The timeline is the single place to retime the film: scenes, shots, lower thirds, cards, voice lines and sound.
Captions are timed from the Grok TTS character timestamps (video/assets/vo/*.json). Interviews and dashboard recordings
that have not arrived yet are placeholder slates (PLACEHOLDER below): drop the file in, set its path, re-run.

    python video/make_assets.py && python video/build_film.py && cd video/film && npx hyperframes check --json
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FILM = REPO / "video" / "film"
VO = REPO / "video" / "assets" / "vo"
W, H = 1920, 1080

YELLOW, VIOLET, VIOLET2, INK, SLATE = "#fff94a", "#4300de", "#8f3fff", "#0a0a12", "#14141f"

LT = {  # lower thirds: (name, role)
    "romeo": ("Federico Romeo", "AI Engineer · aidea"),
    "puddu": ("Francesco Puddu", "AI Engineer · aidea · in charge of the dog"),
    "rios": ("Federico Rios", "AI Engineer · aidea · in charge of the slide font"),
    "g1": ("G1 U2", "humanoid · yes, I did everything"),
    "team": ("The humans", "Romeo · Puddu · Rios"),
}
INTERVIEW_TEXT = {}  # placeholder slates are no longer used (all interviews arrived)


def vo_meta(vid: str) -> dict:
    return json.loads((VO / f"{vid}.json").read_text())


def vo_time(vid: str, phrase: str) -> float:
    """Seconds into a voice line where `phrase` starts (TTS character timestamps, [tags] ignored)."""
    ts = vo_meta(vid)["timestamps"]
    text, times, skip = [], [], False
    for c, tt in zip(ts["graph_chars"], ts["graph_times"]):
        if c == "[":
            skip = True
        if not skip:
            text.append(c)
            times.append(tt[0])
        if c == "]":
            skip = False
    return times["".join(text).index(phrase)]


def clip(src, t, d, media=0.0, **kw) -> dict:
    return dict(kind="video", src=f"assets/clips/{src}.mp4", t=t, d=d, media=media, **kw)


# ---------------------------------------------------------------------------------------------------------------------
# Timeline. Each scene has a duration; starts follow one another. Inside a scene everything is on the scene clock:
#   shots: video/img (t, d, media = offset into the clip, rate, push=(from, to, ox%, oy%), snap=(at, scale, ox%, oy%))
#   vo: [(line id, t)]   audio: interview sound [dict(src, t, d, media, vol, auto=[(t, v)...])]   music, room, keys, sfx
G3_CUT = round(0.4 + vo_time("g1-03", "And a human") - 0.12, 2)  # cut to a human on "And a human taking the credit"
G3_END = round(0.4 + vo_meta("g1-03")["duration"] + 0.7, 2)
DUCK = 0.15  # interview level under the G1's "translation"
F_HEADER = (196, 6, 220, 66)          # "g1  Grok 4.5"
F_SIM = (195, 95, 650, 550)           # External view (MuJoCo)
F_PERCEPTION = (845, 95, 880, 550)    # Objects (distance and height) + Depth
F_CHAT = (195, 650, 1530, 300)        # chat steps + input box
F_STEPS = (195, 650, 1530, 235)       # the agent's steps
F_TABLE = (1285, 245, 440, 160)       # first recording: live table object / distance / height / bearing


def vo_end(vid: str, t: float, tail: float = 0.6) -> float:
    return round(t + vo_meta(vid)["duration"] + tail, 2)


T02_HUMANS = round(0.3 + vo_time("t-02", "The humans") - 0.1, 2)
SCENES = [
    dict(id="s01-gru", dur=2.8, shots=[dict(kind="img", src="assets/img/img-gru.jpg", t=0, d=2.8, push=(1.0, 1.06, 50, 40))],
         note=dict(text="Wednesday, 4:37 PM.", t=0.3, d=2.3), amb=[(0, 2.8, 0.7)]),
    # Interviews, like Rios's: the human says his line in full, the G1 answers in the gap (both always understandable).
    dict(id="s02-romeo", dur=8.6, shots=[clip("i-romeo", 0, 8.6, 1.0)], lt=("romeo", 0.3, 7.6), vo=[("d-01", 5.8)],
         audio=[dict(src="int-romeo", t=0, d=8.6, media=1.0, auto=[(0, 1), (5.6, 1), (5.75, 0.35), (8.1, 0.35), (8.3, 0.8)])]),
    dict(id="s03-puddu", dur=9.9, shots=[clip("i-puddu", 0, 4.3, 2.5), clip("i-puddu-muto", 4.3, 3.0, 2.6), clip("i-puddu", 7.3, 2.6, 9.9)],
         lt=("puddu", 0.2, 8.4), vo=[("d-02", 4.5)], amb=[(4.3, 3.0, 0.7)],
         audio=[dict(src="int-puddu", t=0, d=4.3, media=2.5), dict(src="int-puddu", t=7.3, d=2.6, media=9.9)]),
    dict(id="s04-cane", dur=10.4, shots=[clip("c-cane", 0, 10.4, push=(1.0, 1.06, 60, 70))],
         words=[("Obeys.", 1.05, 1.05), ("Moves.", 2.1, 2.1), ("Understands.", 4.2, 2.1)],
         music=[dict(t=0, d=7.2, media=1.60, vol=0.55)], amb=[(7.2, 3.2, 0.7)]),   # music cut dead when the dog touches the floor
    dict(id="s05-puddu-muto", dur=1.4, shots=[clip("i-puddu-muto", 0, 1.4, 1.2)], amb=[(0, 1.4, 0.7)]),
    dict(id="s07-ma", dur=3.2, card="But there's something I haven't told you.", amb=[(0, 3.2, 0.6)]),
    dict(id="s08-testa", dur=4.8, shots=[clip("c-testa", 0, 4.8, rate=0.5)], lt=("g1", 0.3, 4.4), vo=[("g1-01", 0.5)],
         amb=[(0, 4.8, 0.5)]),
    dict(id="s09-umani", dur=9.0, shots=[clip("y-testa", 0, 4.3), clip("y-tra", 4.3, 4.7)], vo=[("g1-02", 0.4)], amb=[(0, 9.0, 0.4)]),
    dict(id="s10-scrivania", dur=G3_END, shots=[clip("y-pov", 0, G3_CUT), clip("i-romeo-muto", G3_CUT, round(G3_END - G3_CUT, 2), 1.5)],
         vo=[("g1-03", 0.4)], amb=[(0, G3_END, 0.4)]),
    # Technical chapter, still told by the G1. The dashboard is always shown whole (header to input box), never zoomed:
    # the part being explained stays sharp, the rest goes very slightly soft; the explanation sits in the empty header corner.
    dict(id="s11-capitolo", dur=4.6, chapter=("Technical chapter", "How I work", "(explained for humans)"), vo=[("t-01", 0.5)],
         bed=dict(d="tech", vol=0.13, media=12.02)),
    dict(id="s12-cervello", dur=vo_end("t-02", 0.3), low_caps=True,
         shots=[dict(kind="dash", src="d2", t=0, d=T02_HUMANS, media=10.0, focus=[(0.4, T02_HUMANS, F_HEADER)]),
                clip("c-vert", T02_HUMANS, round(vo_end("t-02", 0.3) - T02_HUMANS, 2), 0.0,
                     rate=round(min(1.0, 4.8 / (vo_end("t-02", 0.3) - T02_HUMANS)), 3))],
         ov=[dict(t=0.5, d=round(T02_HUMANS - 0.6, 2), kicker="MY BRAIN", title="Grok 4.5", sub="xAI API · Responses API · function calling", chip=True)],
         vo=[("t-02", 0.3)]),
    dict(id="s13-funzioni", dur=vo_end("t-03", 0.3), low_caps=True,
         shots=[dict(kind="dash", src="d2", t=0, d=4.6, media=0.6, focus=[(0.3, 4.6, F_CHAT)]),
                dict(kind="dash", src="d2", t=4.6, d=round(vo_end("t-03", 0.3) - 4.6, 2), media=10.5, rate=1.6,
                     focus=[(0.0, round(vo_end("t-03", 0.3) - 4.6, 2), F_STEPS)])],
         ov=[dict(t=4.8, d=round(vo_end("t-03", 0.3) - 5.2, 2), kicker="FUNCTION CALLING", title="move · look · finish",
                  sub="Grok picks a function, I run it, then I look again", chip=True)],
         vo=[("t-03", 0.3)]),
    dict(id="s14-segmentazione", dur=vo_end("t-04", 0.3),
         shots=[clip("y-pov2", 0, 6.4, 0.2), clip("y-arriva", 6.4, round(vo_end("t-04", 0.3) - 6.4, 2), 0.0)],
         ov=[dict(t=0.6, d=round(vo_end("t-04", 0.3) - 1.0, 2), kicker="SEGMENTATION", title="YOLOE",
                  sub="masks from text prompts · local · ~3 fps", mini=True)],
         vo=[("t-04", 0.3)]),
    dict(id="s15-distanza", dur=vo_end("t-05", 0.3), low_caps=True,
         shots=[dict(kind="dash", src="d2", t=0, d=5.6, media=12.0, focus=[(0.3, 5.6, F_PERCEPTION)]),
                dict(kind="dash", src="d1", t=5.6, d=round(vo_end("t-05", 0.3) - 5.6, 2), media=20.0,
                     focus=[(0.0, round(vo_end("t-05", 0.3) - 5.6, 2), F_TABLE)])],
         ov=[dict(t=0.5, d=round(vo_end("t-05", 0.3) - 0.9, 2), kicker="DISTANCE & HEIGHT", title="mask × depth",
                  sub="median depth under each mask · height above the floor · live, every frame", chip=True)],
         vo=[("t-05", 0.3)]),
    dict(id="s16-mujoco", dur=vo_end("t-06", 0.3), low_caps=True,
         shots=[dict(kind="dash", src="d2", t=0, d=vo_end("t-06", 0.3), media=8.0, rate=round(18.6 / vo_end("t-06", 0.3), 3),
                     focus=[(0.4, vo_end("t-06", 0.3), F_SIM)])],
         ov=[dict(t=0.6, d=round(vo_end("t-06", 0.3) - 1.0, 2), kicker="SIMULATOR", title="MuJoCo",
                  sub="real physics · Unitree locomotion policy · same commands as the real G1", chip=True)],
         vo=[("t-06", 0.3)], bed_end=True),
    # Back to the comedy
    dict(id="s17-tasti", dur=7.2, shots=[clip("c-hacker", 0, 2.4), clip("c-closeup", 2.4, 2.2), clip("c-scrive", 4.6, 2.6, rate=0.95)],
         vo=[("g1-04", 0.3)], keys=[0.1, 0.5, 0.85, 1.3, 2.0, 2.4, 2.75, 3.3, 3.8, 4.2, 4.6, 5.0, 5.4, 5.8, 6.3, 6.7]),
    dict(id="s18-rios", dur=8.0, shots=[clip("i-rios", 0, 8.0, 0.4)], lt=("rios", 0.2, 6.6), vo=[("d-03", 1.35)],
         audio=[dict(src="int-rios", t=0, d=8.0, media=0.4, auto=[(0, 1), (1.2, 1), (1.3, DUCK), (2.0, DUCK), (2.2, 0.95)])]),
    dict(id="s20-hacker", dur=2.2, shots=[dict(kind="img", src="assets/img/img-realhacker.jpg", t=0, d=2.2, snap=(0.35, 2.8, 63, 0))],
         amb=[(0, 2.2, 0.7)]),
    dict(id="s21-vuota", dur=2.2, shots=[clip("c-vuota", 0, 2.2)], amb=[(0, 2.2, 0.7)]),
    dict(id="s22-guarda", dur=2.2, shots=[clip("c-guarda", 0, 2.2, push=(1.0, 1.08, 50, 35))], amb=[(0, 2.2, 0.7)]),
    dict(id="s23-contributo", dur=3.2, card="I asked the humans what they contributed.", amb=[(0, 3.2, 0.6)]),
    dict(id="s24-team", dur=7.0, shots=[clip("i-team", 0, 7.0, 1.6)], lt=("team", 0.2, 4.6), vo=[("d-04", 5.3)],
         audio=[dict(src="int-team", t=0, d=7.0, media=1.6, auto=[(0, 1), (5.15, 1), (5.25, 0.4), (7.0, 0.4)])]),
    # The G1's finger on the key, slowed down: it pressed enter too
    dict(id="s24b-dito", dur=4.4, shots=[clip("c-mano", 0, 4.4, rate=0.5)], vo=[("g1-06", 0.3)], amb=[(0, 4.4, 0.6)]),
    dict(id="s25-invio", dur=2.4, low_caps=True, shots=[dict(kind="dash", src="d2", t=0, d=2.4, media=3.4)],
         sfx=[("click", 1.2, 1.0)], music_from=1.2),                                   # the message goes, the music comes back
    dict(id="s26-logo", dur=4.5, logo=True),
    dict(id="s27-tag", dur=4.8, shots=[clip("c-tag", 0, 4.8, push=(1.35, 1.45, 74, 62))], vo=[("g1-05", 0.6)]),
]
t0 = 0.0
for _sc in SCENES:
    _sc["start"] = round(t0, 2)
    t0 += _sc["dur"]
DURATION = round(t0, 2)
_inv = next(sc for sc in SCENES if "music_from" in sc)
MUSIC_B = dict(start=round(_inv["start"] + _inv["music_from"], 2), media=17.91, vol=0.5)
MUSIC_B["dur"] = round(DURATION - MUSIC_B["start"], 2)

# Absolute positions, derived from the scenes
VOICE = [(vid, round(sc["start"] + t, 2)) for sc in SCENES for vid, t in sc.get("vo", [])]

# ---------------------------------------------------------------------------------------------------------------------
FONT_FACES = "\n".join(
    f'@font-face {{ font-family: "Artific"; src: url("assets/fonts/Artific-{n}.woff2") format("woff2"); font-weight: {w}; }}'
    for n, w in [("Regular", 400), ("Medium", 500), ("SemiBold", 600), ("Bold", 700), ("Black", 800)])

BASE_CSS = f"""
{FONT_FACES}
#root {{ position: absolute; inset: 0; overflow: hidden; background: {INK}; font-family: "Artific", sans-serif; }}
.full {{ position: absolute; left: 0; top: 0; width: {W}px; height: {H}px; object-fit: cover; }}
.wrap {{ position: absolute; inset: 0; transform-origin: 50% 50%; }}
.lt {{ position: absolute; left: 120px; bottom: 210px; }}
.lt-in {{ display: flex; flex-direction: column; align-items: flex-start; }}
.lt-name {{ background: {VIOLET}; color: #fff; font-weight: 800; font-size: 54px; letter-spacing: 0.01em; text-transform: uppercase;
            padding: 8px 24px 6px; line-height: 1.1; }}
.lt-role {{ background: {YELLOW}; color: {INK}; font-weight: 500; font-size: 32px; padding: 6px 24px; line-height: 1.2; }}
.note {{ position: absolute; left: 120px; bottom: 110px; color: #fff; font-weight: 500; font-size: 40px;
         text-shadow: 0 2px 12px rgba(0,0,0,.85), 0 1px 2px #000; }}
.note.big {{ left: 0; right: 0; bottom: 120px; text-align: center; font-size: 56px; font-weight: 600; }}
.word {{ position: absolute; right: 120px; top: 120px; text-align: right; color: {YELLOW}; font-weight: 800; font-size: 220px; letter-spacing: -0.03em;
         line-height: 1; text-shadow: 0 6px 30px rgba(0,0,0,.55); }}
.card {{ position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; text-align: center; }}
.card-in {{ color: #fff; font-weight: 500; font-size: 76px; max-width: 1400px; line-height: 1.15; letter-spacing: -0.01em; }}
.slate {{ position: absolute; inset: 0; background: {SLATE}; display: flex; flex-direction: column; justify-content: center; padding: 0 160px; }}
.slate-tag {{ color: {INK}; background: {YELLOW}; font-weight: 700; font-size: 28px; padding: 6px 16px; align-self: flex-start; letter-spacing: .08em; }}
.slate-t1 {{ color: #fff; font-weight: 700; font-size: 64px; margin-top: 28px; }}
.slate-t2 {{ color: #d6d6e5; font-weight: 400; font-size: 44px; margin-top: 20px; font-style: italic; max-width: 1500px; }}
.half {{ position: absolute; top: 0; width: 960px; height: {H}px; overflow: hidden; }}
.half video, .half .slate {{ position: absolute; left: -480px; top: 0; width: {W}px; height: {H}px; object-fit: cover; }}
.half .slate {{ left: 0; width: 960px; padding: 0 70px; }}
.logo-bg {{ position: absolute; inset: 0; background: #fff; }}
.logo-img {{ position: absolute; left: 510px; top: 300px; width: 900px; height: 437px; object-fit: contain; }}
.logo-sub {{ position: absolute; left: 0; right: 0; top: 790px; text-align: center; color: #2a2a3a; font-weight: 500; font-size: 36px; }}
.logo-cred {{ position: absolute; left: 0; right: 0; top: 850px; text-align: center; color: #5a5a74; font-weight: 400; font-size: 28px; }}
.ov {{ position: absolute; left: 110px; top: 96px; }}
.ov-in {{ display: inline-flex; flex-direction: column; align-items: flex-start; background: rgba(10,10,18,.78); border-left: 10px solid {YELLOW};
          padding: 22px 34px 26px 28px; max-width: 1500px; }}
.ov-k {{ background: {VIOLET}; color: #fff; font-weight: 700; font-size: 26px; letter-spacing: .14em; padding: 5px 14px; }}
.ov-t {{ color: #fff; font-weight: 800; font-size: 104px; line-height: 1.02; letter-spacing: -0.02em; margin-top: 14px; }}
.ov-s {{ color: {YELLOW}; font-weight: 500; font-size: 32px; line-height: 1.25; margin-top: 12px; }}
.ov.small .ov-t {{ font-size: 64px; }}
.ov.bottom {{ top: auto; bottom: 210px; }}
.ov.right {{ left: auto; right: 110px; }}
.ov.chip {{ left: auto; right: 175px; top: 8px; }}
.ov.chip .ov-in {{ flex-direction: row; flex-wrap: wrap; align-items: baseline; column-gap: 14px; padding: 10px 18px 10px 16px;
                   border-left-width: 6px; max-width: 760px; }}
.ov.chip .ov-k {{ font-size: 18px; padding: 3px 9px; }}
.ov.chip .ov-t {{ font-size: 40px; margin-top: 0; }}
.ov.chip .ov-s {{ font-size: 19px; margin-top: 4px; flex-basis: 100%; }}
.ov.mini {{ left: 70px; top: 60px; }}
.ov.mini .ov-in {{ padding: 12px 20px 14px 16px; border-left-width: 6px; }}
.ov.mini .ov-k {{ font-size: 18px; padding: 3px 9px; }}
.ov.mini .ov-t {{ font-size: 52px; margin-top: 8px; }}
.ov.mini .ov-s {{ font-size: 21px; margin-top: 6px; }}
.chap {{ position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; }}
.chap-k {{ background: {YELLOW}; color: {INK}; font-weight: 700; font-size: 30px; letter-spacing: .16em; padding: 6px 16px; text-transform: uppercase; }}
.chap-t {{ color: #fff; font-weight: 800; font-size: 150px; letter-spacing: -0.03em; margin-top: 26px; line-height: 1; }}
.chap-s {{ color: {VIOLET2}; font-weight: 500; font-size: 48px; margin-top: 22px; }}
"""


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def scene_file(sc: dict) -> str:
    sid, dur = sc["id"], sc["dur"]
    body, js = [], []
    z = 1

    def tl(line: str) -> None:
        js.append("    " + line)

    for i, sh in enumerate(sc.get("shots", [])):
        kind, t, d = sh["kind"], sh["t"], sh["d"]
        wid = f"{sid}-w{i}"
        if kind in ("video", "img"):
            src = sh["src"]
            if kind == "video" and not (FILM / src).exists() and sh.get("fallback"):
                src = sh["fallback"]
            rate = sh.get("rate", 1)
            attrs = f'id="{sid}-m{i}" class="clip full" data-start="{t}" data-duration="{d}" data-track-index="{i + 1}"'
            if kind == "video":
                extra = f' data-media-start="{sh.get("media", 0)}"' + (f' data-playback-rate="{rate}"' if rate != 1 else "")
                media = f'<video {attrs}{extra} src="{src}" muted playsinline></video>'
            else:
                media = f'<img {attrs} src="{src}" alt="">'
            body.append(f'<div class="wrap" id="{wid}" style="z-index:{z}">{media}</div>')
            if "push" in sh:
                a, b, ox, oy = sh["push"]
                tl(f'tl.fromTo("#{wid}", {{scale: {a}, transformOrigin: "{ox}% {oy}%"}}, {{scale: {b}, duration: {d}, ease: "none"}}, {t});')
            if "snap" in sh:
                at, s, ox, oy = sh["snap"]
                origin = f"{ox} {oy}" if isinstance(ox, str) else f"{ox}% {oy}%"
                tl(f'tl.fromTo("#{wid}", {{scale: 1, transformOrigin: "{origin}"}}, {{scale: {s}, duration: 0.22, ease: "power3.out"}}, {t + at});')
        elif kind == "dash":  # whole dashboard; the explained part stays sharp, the rest is the very slightly blurred copy
            src, media, rate = sh["src"], sh.get("media", 0), sh.get("rate", 1)
            extra = f' data-media-start="{media}"' + (f' data-playback-rate="{rate}"' if rate != 1 else "")
            body.append(f'<div class="wrap" style="z-index:{z}"><video id="{sid}-m{i}b" class="clip full" data-start="{t}" data-duration="{d}" '
                        f'data-track-index="{i + 1}"{extra} src="assets/clips/{src}-b.mp4" muted playsinline></video></div>')
            body.append(f'<div class="wrap" id="{wid}" style="z-index:{z}"><video id="{sid}-m{i}" class="clip full" data-start="{t}" data-duration="{d}" '
                        f'data-track-index="{i + 2}"{extra} src="assets/clips/{src}.mp4" muted playsinline></video></div>')
            full = "inset(0px 0px 0px 0px round 0px)"
            tl(f'tl.set("#{wid}", {{clipPath: "{full}"}}, {t});')
            for f0, f1, (x, y, w, h) in sh.get("focus", []):
                rect = f"inset({y}px {W - x - w}px {H - y - h}px {x}px round 14px)"
                tl(f'tl.fromTo("#{wid}", {{clipPath: "{full}"}}, {{clipPath: "{rect}", duration: 0.45, ease: "power2.inOut"}}, {t + f0});')
                tl(f'tl.to("#{wid}", {{clipPath: "{full}", duration: 0.35, ease: "power2.inOut"}}, {round(t + f1 - 0.35, 2)});')
        elif kind == "slate":
            key = sh["key"]
            if key in ("r1", "r3"):
                t1, t2 = {"r1": ("R1 · dashboard, scheda oggetti", "registrazione del collega in arrivo"),
                          "r3": ("R3 · clic su Start (R)", "in arrivo")}[key]
            else:
                t1, t2 = INTERVIEW_TEXT[key][0], f"“{INTERVIEW_TEXT[key][1]}”"
            body.append(f'<div id="{sid}-sl{i}" class="clip slate" data-start="{t}" data-duration="{d}" data-track-index="{i + 1}" style="z-index:{z}">'
                        f'<div class="slate-tag">SEGNAPOSTO</div><div class="slate-t1">{esc(t1)}</div><div class="slate-t2">{esc(t2)}</div></div>')
        elif kind == "split":
            left = f'<video id="{sid}-sp{i}l" src="{sh["left"]}" muted playsinline class="clip" data-start="{t}" data-duration="{d}" data-track-index="{i + 1}"></video>'
            body.append(f'<div class="half" style="left:0;z-index:{z}">{left}</div>')
            body.append(f'<div class="half" style="left:960px;z-index:{z}"><div id="{sid}-sp{i}r" class="clip slate" data-start="{t}" data-duration="{d}" data-track-index="{i + 2}">'
                        f'<div class="slate-tag">SEGNAPOSTO</div><div class="slate-t1">R1 · dashboard</div><div class="slate-t2">cosa riconosce, con le distanze</div></div></div>')
        z += 1

    if "card" in sc:
        body.append(f'<div id="{sid}-card" class="clip card" data-start="0" data-duration="{dur}" data-track-index="1">'
                    f'<div class="card-in" id="{sid}-card-in">{esc(sc["card"])}</div></div>')
        tl(f'tl.fromTo("#{sid}-card-in", {{opacity: 0, filter: "blur(8px)"}}, {{opacity: 1, filter: "blur(0px)", duration: 0.5, ease: "power2.out"}}, 0.25);')
        tl(f'tl.to("#{sid}-card-in", {{opacity: 0, duration: 0.3, ease: "power2.in"}}, {dur - 0.4});')

    if "chapter" in sc:
        k, ttl, sub = sc["chapter"]
        body.append(f'<div id="{sid}-chap" class="clip chap" data-start="0" data-duration="{dur}" data-track-index="1">'
                    f'<div class="chap-k" id="{sid}-chap-k">{esc(k)}</div><div class="chap-t" id="{sid}-chap-t">{esc(ttl)}</div>'
                    f'<div class="chap-s" id="{sid}-chap-s">{esc(sub)}</div></div>')
        tl(f'tl.fromTo("#{sid}-chap-k", {{opacity: 0}}, {{opacity: 1, duration: 0.3, ease: "power2.out"}}, 0.2);')
        tl(f'tl.fromTo("#{sid}-chap-t", {{opacity: 0, filter: "blur(10px)"}}, {{opacity: 1, filter: "blur(0px)", duration: 0.4, ease: "power3.out"}}, 0.35);')
        tl(f'tl.fromTo("#{sid}-chap-s", {{opacity: 0}}, {{opacity: 1, duration: 0.3, ease: "power2.out"}}, 2.6);')

    for j, o in enumerate(sc.get("ov", [])):
        cls = "ov" + "".join(f" {k}" for k in ("small", "bottom", "right", "chip", "mini") if o.get(k))
        body.append(f'<div id="{sid}-ov{j}" class="clip {cls}" data-start="{o["t"]}" data-duration="{o["d"]}" data-track-index="{12 + j}" style="z-index:65">'
                    f'<div class="ov-in" id="{sid}-ov{j}-in"><div class="ov-k">{esc(o["kicker"])}</div><div class="ov-t">{esc(o["title"])}</div>'
                    f'<div class="ov-s">{esc(o["sub"])}</div></div></div>')
        tl(f'tl.fromTo("#{sid}-ov{j}-in", {{clipPath: "inset(0 100% 0 0)"}}, {{clipPath: "inset(0 0% 0 0)", duration: 0.5, ease: "power3.out"}}, {o["t"]});')
        tl(f'tl.to("#{sid}-ov{j}-in", {{opacity: 0, duration: 0.25, ease: "power2.in"}}, {round(o["t"] + o["d"] - 0.3, 2)});')

    if sc.get("logo"):
        body.append(f'<div id="{sid}-bg" class="clip logo-bg" data-start="0" data-duration="{dur}" data-track-index="1"></div>')
        body.append(f'<img id="{sid}-logo" class="clip logo-img" src="assets/aidea-logo.webp" alt="aidea" data-start="0" data-duration="{dur}" data-track-index="2">')
        body.append(f'<div id="{sid}-sub" class="clip logo-sub" data-start="0" data-duration="{dur}" data-track-index="3">'
                    f'<span id="{sid}-sub-in">Grok Hackathon at the Museum · Pavia · 2026</span></div>')
        body.append(f'<div id="{sid}-cred" class="clip logo-cred" data-start="0" data-duration="{dur}" data-track-index="4">'
                    f'<span id="{sid}-cred-in">Grok 4.5 (xAI API) · YOLOE · MuJoCo · Unitree G1 &amp; Go1</span></div>')
        tl(f'tl.fromTo("#{sid}-sub-in", {{opacity: 0}}, {{opacity: 1, duration: 0.5, ease: "power2.out"}}, 0.6);')
        tl(f'tl.fromTo("#{sid}-cred-in", {{opacity: 0}}, {{opacity: 1, duration: 0.5, ease: "power2.out"}}, 1.2);')

    if "note" in sc:
        n = sc["note"]
        cls = "note big" if n.get("big") else "note"
        body.append(f'<div id="{sid}-note" class="clip {cls}" data-start="{n["t"]}" data-duration="{n["d"]}" data-track-index="8" style="z-index:50">'
                    f'<span id="{sid}-note-in">{esc(n["text"])}</span></div>')
        tl(f'tl.fromTo("#{sid}-note-in", {{opacity: 0, filter: "blur(6px)"}}, {{opacity: 1, filter: "blur(0px)", duration: 0.35, ease: "power2.out"}}, {n["t"]});')

    for j, (word, t, d) in enumerate(sc.get("words", [])):
        body.append(f'<div id="{sid}-word{j}" class="clip word" data-start="{t}" data-duration="{d}" data-track-index="{9 + j}" style="z-index:60">'
                    f'<span id="{sid}-word{j}-in">{esc(word)}</span></div>')
        tl(f'tl.fromTo("#{sid}-word{j}-in", {{opacity: 0, filter: "blur(10px)"}}, {{opacity: 1, filter: "blur(0px)", duration: 0.13, ease: "power4.out"}}, {t});')

    if "lt" in sc:
        who, t, d = sc["lt"]
        name, role = LT[who]
        body.append(f'<div id="{sid}-lt" class="clip lt" data-start="{t}" data-duration="{d}" data-track-index="7" style="z-index:70">'
                    f'<div class="lt-in" id="{sid}-lt-in"><div class="lt-name">{esc(name)}</div><div class="lt-role">{esc(role)}</div></div></div>')
        tl(f'tl.fromTo("#{sid}-lt-in", {{clipPath: "inset(0 100% 0 0)"}}, {{clipPath: "inset(0 0% 0 0)", duration: 0.45, ease: "power3.out"}}, {t});')
        tl(f'tl.to("#{sid}-lt-in", {{opacity: 0, duration: 0.25, ease: "power2.in"}}, {t + d - 0.3});')

    if not js:  # keep a timeline even for a scene with no tweens
        tl(f'tl.set({{}}, {{}}, {dur});')
    return f"""<template>
  <style>
{BASE_CSS}
  </style>
  <div id="root" data-composition-id="{sid}" data-width="{W}" data-height="{H}">
    {chr(10).join("    " + b for b in body).strip()}
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
{chr(10).join(js)}
    window.__timelines["{sid}"] = tl;
  </script>
</template>
"""


def caption_groups() -> list[dict]:
    """One group per sentence, timed from the TTS character timestamps (tags like [pause] are not shown)."""
    groups = []
    for vid, start in VOICE:
        meta = json.loads((VO / f"{vid}.json").read_text())
        chars, times = meta["timestamps"]["graph_chars"], meta["timestamps"]["graph_times"]
        text, ts, skip = [], [], False
        for c, tt in zip(chars, times):  # drop [tags] and collapse spaces, keeping each kept char's time
            if c == "[":
                skip = True
            if not skip and not (c == " " and (not text or text[-1] == " ")):
                text.append(c)
                ts.append(tt)
            if c == "]":
                skip = False
        s = "".join(text)
        split = re.compile(r"\S.*?(?:[.!?](?=\s|$)|$)")  # sentence ends; "4.5" and ".env" are not ends
        spoken = [m for m in split.finditer(s) if m.group().strip()]
        shown = [m.group().strip() for m in split.finditer(meta["subtitle"]) if m.group().strip()]
        if len(shown) != len(spoken):  # the subtitle is written differently (digits, names): fall back to what is said
            shown = [m.group().strip() for m in spoken]
        for m, sent in zip(spoken, shown):
            a, b = m.start(), m.start() + len(m.group().rstrip()) - 1
            st = round(start + ts[a][0] - 0.05, 2)
            low = any(sc.get("low_caps") and sc["start"] <= st < sc["start"] + sc["dur"] for sc in SCENES)
            groups.append(dict(text=sent, start=st, end=round(start + ts[b][1] + 0.35, 2), g1=True, low=low))
    for g, nxt in zip(groups, groups[1:]):  # never two on screen
        g["end"] = min(g["end"], nxt["start"] - 0.02)
    return groups


def captions_file(groups: list[dict]) -> str:
    items, js = [], []
    for i, g in enumerate(groups):
        d = round(g["end"] - g["start"], 2)
        color = YELLOW if g["g1"] else "#ffffff"
        items.append(f'<div id="cap{i}" class="clip cap{" low" if g.get("low") else ""}" data-start="{g["start"]}" data-duration="{d}" data-track-index="1">'
                     f'<span id="cap{i}-in" style="color:{color}">{esc(g["text"])}</span></div>')
        js.append(f'    tl.fromTo("#cap{i}-in", {{opacity: 0}}, {{opacity: 1, duration: 0.12, ease: "power2.out"}}, {g["start"]});')
    return f"""<template>
  <style>
{FONT_FACES}
#root {{ position: absolute; inset: 0; pointer-events: none; font-family: "Artific", sans-serif; }}
.cap {{ position: absolute; left: 0; right: 0; bottom: 92px; text-align: center; }}
.cap.low {{ bottom: 22px; }}
.cap span {{ display: inline-block; max-width: 1500px; font-weight: 600; font-size: 48px; line-height: 1.2; padding: 6px 18px;
            background: rgba(10,10,18,.55); text-shadow: 0 2px 3px rgba(0,0,0,.9); }}
  </style>
  <div id="root" data-composition-id="captions" data-width="{W}" data-height="{H}">
    {chr(10).join("    " + it for it in items).strip()}
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
{chr(10).join(js)}
    window.__timelines["captions"] = tl;
  </script>
</template>
"""


def index_file(groups: list[dict]) -> str:
    hosts = []
    for k, sc in enumerate(SCENES):
        hosts.append(f'<div id="{sc["id"]}" data-composition-id="{sc["id"]}" data-composition-src="compositions/{sc["id"]}.html" '
                     f'data-start="{sc["start"]}" data-duration="{sc["dur"]}" data-track-index="{1 + k % 2}" data-track-kind="graphics" '
                     f'data-width="{W}" data-height="{H}" style="z-index:{1 + k % 2}"></div>')
    hosts.append(f'<div id="captions" data-composition-id="captions" data-composition-src="compositions/captions.html" data-start="0" '
                 f'data-duration="{DURATION}" data-track-index="3" data-track-kind="captions" data-width="{W}" data-height="{H}" style="z-index:90"></div>')
    audio = []

    def add(aid: str, src: str, start: float, dur: float, track: int, vol: float = 1.0, media: float | None = None,
            auto: list | None = None, fade_in: float | None = None, fade_out: float | None = None) -> None:
        extra = f' data-media-start="{media}"' if media else ""
        if auto:
            lane = {"version": 1, "lanes": [{"target": "volume", "points": [{"t": t, "v": v} for t, v in auto]}]}
            extra += f" data-automation='{json.dumps(lane, separators=(',', ':'))}'"
        if fade_in:
            extra += f' data-fade-in="{fade_in}"'
        if fade_out:
            extra += f' data-fade-out="{fade_out}"'
        audio.append(f'<audio id="{aid}" class="clip" src="assets/audio/{src}" data-start="{round(start, 2)}" data-duration="{round(dur, 2)}" '
                     f'data-track-index="{track}" data-volume="{vol}"{extra}></audio>')

    for vid, start in VOICE:
        add(f"a-{vid}", f"vo-{vid}.wav", start, vo_meta(vid)["duration"], 10)
    room_k = key_k = 0
    for sc in SCENES:
        s0 = sc["start"]
        for j, a in enumerate(sc.get("audio", [])):
            add(f"a-{sc['id']}-int{j}", f"{a['src']}.wav", s0 + a["t"], a["d"], 11, a.get("vol", 1.0), a.get("media"), a.get("auto"))
        for j, m in enumerate(sc.get("music", [])):
            add(f"a-{sc['id']}-music{j}", "music.mp3", s0 + m["t"], m["d"], 12, m["vol"], m["media"])
        for t, d, v in sc.get("amb", []):  # soft air, read at its own film time: nothing ever repeats
            add(f"a-amb{room_k}", "ambient.wav", s0 + t, d, 13, v, media=round(s0 + t, 2), fade_in=0.2, fade_out=0.2)
            room_k += 1
        if "bed" in sc:  # quiet music bed under the technical chapter, until the scene marked bed_end
            last = next(x for x in SCENES if x.get("bed_end"))
            bd = round(last["start"] + last["dur"] - s0, 2)
            add(f"a-{sc['id']}-bed", "music2.mp3", s0, bd, 17, sc["bed"]["vol"], sc["bed"]["media"], fade_in=1.0, fade_out=1.5)
        for t in sc.get("keys", []):
            add(f"a-key{key_k}", f"key-{1 + key_k % 8}.wav", s0 + t, 0.3, 14 + key_k % 2, 0.7)
            key_k += 1
        for name, t, v in sc.get("sfx", []):
            add(f"a-{sc['id']}-{name}", f"{name}.ogg", s0 + t, 0.06, 16, v)
    g5 = next(t for vid, t in VOICE if vid == "g1-05")  # duck the closing music under the G1's last line
    rel = round(g5 - MUSIC_B["start"], 2)
    add("a-music-b", "music.mp3", MUSIC_B["start"], MUSIC_B["dur"], 12, MUSIC_B["vol"], MUSIC_B["media"],
        auto=[(0, 1), (rel - 0.2, 1), (rel, 0.45), (MUSIC_B["dur"], 0.45)], fade_out=1.4)
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={W}, height={H}" />
    <title>who did what · aidea</title>
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
    <style>
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ margin: 0; width: {W}px; height: {H}px; overflow: hidden; background: {INK}; }}
      #root {{ position: relative; width: 100%; height: 100%; background: {INK}; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{DURATION}" data-width="{W}" data-height="{H}">
      {chr(10).join("      " + h for h in hosts).strip()}
      {chr(10).join("      " + a for a in audio).strip()}
    </div>
    <script>
      const tl = gsap.timeline({{ paused: true }});
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
"""


def main() -> None:
    comp = FILM / "compositions"
    comp.mkdir(parents=True, exist_ok=True)
    for old in comp.glob("s*.html"):
        old.unlink()
    for sc in SCENES:
        (comp / f"{sc['id']}.html").write_text(scene_file(sc))
    groups = caption_groups()
    (comp / "captions.html").write_text(captions_file(groups))
    (FILM / "index.html").write_text(index_file(groups))
    print(f"{len(SCENES)} scene, {len(groups)} sottotitoli, {DURATION} s")


if __name__ == "__main__":
    main()
