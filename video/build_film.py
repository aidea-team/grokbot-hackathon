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
    "puddu": ("Francesco Puddu", "AI Engineer · aidea · responsabile del cane"),
    "rios": ("Federico Rios", "AI Engineer · aidea · responsabile del font delle slide"),
    "g1": ("G1 U2", "umanoide · ha fatto tutto lui"),
    "team": ("Il team aidea", "Romeo · Puddu · Rios"),
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
G3_CUT = round(0.4 + vo_time("g1-03", "E un umano") - 0.12, 2)  # cut to a human on "E un umano che si prende il merito"
G3_END = round(0.4 + vo_meta("g1-03")["duration"] + 0.7, 2)
DUCK = 0.15  # interview level under the dubber
SCENES = [
    dict(id="s01-gru", dur=2.8, shots=[dict(kind="img", src="assets/img/img-gru.jpg", t=0, d=2.8, push=(1.0, 1.06, 50, 40))],
         note=dict(text="Mercoledì, ore 16:37.", t=0.3, d=2.3), room=[(0, 2.8, 0.6)]),
    dict(id="s02-romeo", dur=7.6, shots=[clip("i-romeo", 0, 7.6, 1.0)], lt=("romeo", 0.3, 3.6), vo=[("d-01", 0.9)],
         audio=[dict(src="int-romeo", t=0, d=7.6, media=1.0, auto=[(0, 1), (0.8, 1), (1.0, DUCK), (6.9, DUCK), (7.3, 0.7)])]),
    dict(id="s03-puddu", dur=6.8, shots=[clip("i-puddu", 0, 4.3, 2.5), clip("i-puddu", 4.3, 2.5, 9.9)], lt=("puddu", 0.2, 3.4),
         vo=[("d-02", 0.8)],
         audio=[dict(src="int-puddu", t=0, d=4.3, media=2.5, auto=[(0, 1), (0.7, 1), (0.85, DUCK), (3.3, DUCK), (3.6, 0.95)]),
                dict(src="int-puddu", t=4.3, d=2.5, media=9.9, vol=0.95)]),
    dict(id="s04-cane", dur=10.4, shots=[clip("c-cane", 0, 10.4, push=(1.0, 1.06, 60, 70))],
         words=[("Obbedisce.", 1.05, 1.05), ("Si muove.", 2.1, 2.1), ("Capisce.", 4.2, 2.1)],
         music=[dict(t=0, d=7.2, media=1.60, vol=0.55)], room=[(7.2, 3.2, 0.6)]),   # music cut dead when the dog touches the floor
    dict(id="s05-puddu-muto", dur=2.2, shots=[clip("i-puddu-muto", 0, 2.2, 1.2)], room=[(0, 2.2, 0.6)]),
    dict(id="s06-giudici", dur=3.0, card="I giudici non sembravano impressionati.", room=[(0, 3.0, 0.5)]),
    dict(id="s07-ma", dur=3.2, card="Ma c'è una cosa che non vi abbiamo detto.", room=[(0, 3.2, 0.5)]),
    dict(id="s08-testa", dur=4.8, shots=[clip("c-testa", 0, 4.8, rate=0.5)], lt=("g1", 0.4, 3.8), vo=[("g1-01", 0.5)],
         room=[(0, 4.8, 0.25)]),
    dict(id="s09-umani", dur=9.0, shots=[clip("y-testa", 0, 4.3), clip("y-tra", 4.3, 4.7)], vo=[("g1-02", 0.4)], room=[(0, 9.0, 0.25)]),
    dict(id="s10-scrivania", dur=G3_END, shots=[clip("y-pov", 0, G3_CUT), clip("i-romeo-muto", G3_CUT, round(G3_END - G3_CUT, 2), 1.5)],
         vo=[("g1-03", 0.4)], room=[(0, G3_END, 0.25)]),
    dict(id="s11-tasti", dur=7.2, shots=[clip("c-hacker", 0, 2.0), clip("c-closeup", 2.0, 1.8), clip("c-mano", 3.8, 1.6),
                                          clip("c-scrive", 5.4, 1.8)], vo=[("g1-04", 0.3)],
         keys=[0.1, 0.5, 0.85, 1.3, 2.0, 2.4, 2.75, 3.3, 3.8, 4.2, 4.55, 5.0, 5.4, 5.8, 6.3, 6.7]),
    dict(id="s12-rios", dur=8.5, shots=[clip("i-rios", 0, 8.5, 0.4)], lt=("rios", 0.2, 3.4), vo=[("d-03", 1.35)],
         audio=[dict(src="int-rios", t=0, d=8.5, media=0.4, auto=[(0, 1), (1.2, 1), (1.3, DUCK), (2.5, DUCK), (2.7, 0.95)])]),
    dict(id="s13-rios-muto", dur=1.6, shots=[clip("i-rios-muto", 0, 1.6, 1.0)], room=[(0, 1.6, 0.5)]),
    dict(id="s14-hacker", dur=2.2, shots=[dict(kind="img", src="assets/img/img-realhacker.jpg", t=0, d=2.2, snap=(0.35, 2.8, 63, 0))],
         room=[(0, 2.2, 0.5)]),
    dict(id="s15-vuota", dur=2.2, shots=[clip("c-vuota", 0, 2.2)], room=[(0, 2.2, 0.6)]),
    dict(id="s16-guarda", dur=2.2, shots=[clip("c-guarda", 0, 2.2, push=(1.0, 1.08, 50, 35))], room=[(0, 2.2, 0.6)]),
    dict(id="s17-contributo", dur=3.2, card="Abbiamo chiesto al team quale fosse il loro contributo.", room=[(0, 3.2, 0.5)]),
    dict(id="s18-team", dur=7.2, shots=[clip("i-team", 0, 7.2, 1.6)], lt=("team", 0.2, 2.2), vo=[("d-04", 5.15)],
         audio=[dict(src="int-team", t=0, d=7.2, media=1.6, auto=[(0, 1), (5.0, 1), (5.1, 0.2), (7.2, 0.2)])]),
    dict(id="s19-invio", dur=5.2, shots=[clip("r-chat", 0, 2.6, push=(1.0, 1.25, 86, 48)), clip("r-dash", 2.6, 2.6, rate=3)],
         sfx=[("click", 1.9, 1.0)], music_from=1.9),                                   # the music comes back on "invio"
    dict(id="s20-logo", dur=4.0, logo=True),
    dict(id="s21-tag", dur=4.8, shots=[clip("c-tag", 0, 4.8, push=(1.35, 1.45, 74, 62))], vo=[("g1-05", 0.6)]),
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
                tl(f'tl.fromTo("#{wid}", {{scale: 1, transformOrigin: "{ox}% {oy}%"}}, {{scale: {s}, duration: 0.22, ease: "power3.out"}}, {t + at});')
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

    if sc.get("logo"):
        body.append(f'<div id="{sid}-bg" class="clip logo-bg" data-start="0" data-duration="{dur}" data-track-index="1"></div>')
        body.append(f'<img id="{sid}-logo" class="clip logo-img" src="assets/aidea-logo.webp" alt="aidea" data-start="0" data-duration="{dur}" data-track-index="2">')
        body.append(f'<div id="{sid}-sub" class="clip logo-sub" data-start="0" data-duration="{dur}" data-track-index="3">'
                    f'<span id="{sid}-sub-in">Grok Hackathon at the Museum · Pavia · 2026</span></div>')
        tl(f'tl.fromTo("#{sid}-sub-in", {{opacity: 0}}, {{opacity: 1, duration: 0.5, ease: "power2.out"}}, 0.6);')

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
        for m in re.finditer(r"[^.!?]+[.!?]*", s):
            sent = m.group().strip()
            if not sent:
                continue
            a = m.start() + (len(m.group()) - len(m.group().lstrip()))
            b = a + len(sent) - 1
            groups.append(dict(text=sent, start=round(start + ts[a][0] - 0.05, 2), end=round(start + ts[b][1] + 0.35, 2),
                               g1=vid.startswith("g1")))
    for g, nxt in zip(groups, groups[1:]):  # never two on screen
        g["end"] = min(g["end"], nxt["start"] - 0.02)
    return groups


def captions_file(groups: list[dict]) -> str:
    items, js = [], []
    for i, g in enumerate(groups):
        d = round(g["end"] - g["start"], 2)
        color = YELLOW if g["g1"] else "#ffffff"
        items.append(f'<div id="cap{i}" class="clip cap" data-start="{g["start"]}" data-duration="{d}" data-track-index="1">'
                     f'<span id="cap{i}-in" style="color:{color}">{esc(g["text"])}</span></div>')
        js.append(f'    tl.fromTo("#cap{i}-in", {{opacity: 0}}, {{opacity: 1, duration: 0.12, ease: "power2.out"}}, {g["start"]});')
    return f"""<template>
  <style>
{FONT_FACES}
#root {{ position: absolute; inset: 0; pointer-events: none; font-family: "Artific", sans-serif; }}
.cap {{ position: absolute; left: 0; right: 0; bottom: 92px; text-align: center; }}
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
        for t, d, v in sc.get("room", []):
            add(f"a-room{room_k}", "roomtone.wav", s0 + t, min(d, 13.9), 13, v, fade_in=0.15, fade_out=0.15)
            room_k += 1
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
<html lang="it">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={W}, height={H}" />
    <title>chi ha fatto cosa · aidea</title>
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
