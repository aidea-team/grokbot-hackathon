"""Brainrot cut of the final film, vertical 1080x1920 for Instagram. Nothing of the film is cut: it plays whole in the middle,
paused only for short full-screen meme inserts; on top go meme captions, a "human aura" counter, word-by-word subtitles of
the G1's lines, picture-in-picture reactions and sound effects.

Media come from assets/memes/pack (the team's meme pack, not in git) and from the final film render; see the README in this
folder. Times below are on the FILM clock (as in video/build_film.py) and are mapped to the output clock automatically.

    python video/brainrot/build_brainrot.py && cd video/brainrot/film && npx hyperframes render -o renders/brainrot.mp4
"""
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FILM = HERE / "film"
sys.path.insert(0, str(HERE.parent))
import build_film as bf  # noqa: E402  the film's own timeline (scenes, voice lines)

W, H = 1080, 1920
FILM_DUR = 180.55
BOX_Y, BOX_H = 560, 608          # the film, full width
S = {sc["id"]: sc["start"] for sc in bf.SCENES}
VO_AT = dict((vid, t) for vid, t in bf.VOICE)


def vo_at(vid: str, phrase: str | None = None) -> float:
    return round(VO_AT[vid] + (bf.vo_time(vid, phrase) if phrase else 0.0), 2)


def vo_end(vid: str) -> float:
    return round(VO_AT[vid] + bf.vo_meta(vid)["duration"], 2)


# Full-screen meme inserts: the film pauses at `at` (film clock), the clip plays, the film resumes.
INSERTS = [
    dict(at=0.0, clip="m-hi", d=1.4, top="SCIENTISTS REVEAL: THE ROBOT DID EVERYTHING"),
    dict(at=S["s04-cane"], clip="m-gumball", d=1.8, top="ME HEARING “AGENTIC QUADRUPED” 😮‍💨"),
    dict(at=S["s07-ma"], clip="m-laugh", d=2.0, top="THE DOG RAGEQUIT 💀💀💀"),
    dict(at=S["s10-scrivania"], clip="m-holmes", d=3.8, top="THE ROBOT “RESPECTING HUMANS”:"),
    dict(at=S["s13-funzioni"], clip="m-andy", d=2.0, top="THE HUMANS AFTER PASTING ONE API KEY"),
    dict(at=S["s20-hacker"], clip="m-mbappe", d=1.6, top="HUMAN CONTRIBUTION:"),
]
PRE = 0.0  # the first insert sits at film 0


def out(t: float) -> float:
    """Film clock -> output clock: every insert at or before t adds its length."""
    return round(t + sum(i["d"] for i in INSERTS if i["at"] <= t + 1e-6), 3)


TOTAL = round(FILM_DUR + sum(i["d"] for i in INSERTS), 2)

# Meme captions in the top band: (film t, duration, text)
CAPS = [
    (0.0, 2.8, "POV: THE ROBOT DID ALL THE WORK 💀"),
    (2.8, vo_at("d-01") - 2.8, "BRO SAID “CHANGE ROBOTICS” 😭"),
    (vo_at("d-01"), S["s03-puddu"] - vo_at("d-01"), "THE ROBOT: “IT WON'T.” 🗿"),
    (S["s03-puddu"], 4.3, "“AGENTIC QUADRUPED” 🤓☝️"),
    (vo_at("d-02"), 2.8, "IT'S A DOG. 🐕"),
    (S["s04-cane"], 7.2, "THE DOG ON LIVE DEMO DAY: 🐕‍🦺"),
    (S["s04-cane"] + 7.2, 4.0, "DOG.EXE HAS STOPPED WORKING 💀"),
    (S["s07-ma"], 3.2, "PLOT TWIST INCOMING 😳"),
    (S["s08-testa"], 4.8, "THE ROBOT WAS THE DEV ALL ALONG 🗿"),
    (S["s09-umani"], 9.0, "NPCs SPOTTED 🧍🧍🧍"),
    (S["s09b-stretta"], 8.4, "“HUMAN IN THE LOOP” 🤝"),
    (S["s09b-stretta"] + 8.4, 2.2, "HANDSHAKE FAILED. AURA LOSS 📉"),
    (S["s10-scrivania"], bf.G3_CUT, "SCANNING FOR INTELLIGENCE… 🔍"),
    (S["s10-scrivania"] + bf.G3_CUT, bf.G3_END - bf.G3_CUT, "CAUGHT IN 4K 📸"),
    (S["s11-capitolo"], 4.6, "LOCK IN. TECH TALK 🔒"),
    (S["s12-cervello"], bf.T02_HUMANS, "GROK 4.5 = BIG BRAIN 🧠"),
    (S["s12-cervello"] + bf.T02_HUMANS, S["s13-funzioni"] - S["s12-cervello"] - bf.T02_HUMANS, "PEAK HUMAN ENGINEERING 💀"),
    (S["s13-funzioni"], S["s14-segmentazione"] - S["s13-funzioni"], "FUNCTION CALLING SPEEDRUN ANY% 🏃"),
    (S["s14-segmentazione"], S["s15-distanza"] - S["s14-segmentazione"], "HUMANS = PURPLE BLOBS 🟣"),
    (S["s15-distanza"], S["s16-mujoco"] - S["s15-distanza"], "HE MEASURES. WE GUESS. 📏"),
    (S["s16-mujoco"], S["s17-tasti"] - S["s16-mujoco"], "MUJOCO GAMEPLAY 🎮"),
    (S["s17-tasti"], 7.2, "10X ENGINEER (REAL) ⌨️🔥"),
    (S["s18-rios"], vo_at("d-03") - S["s18-rios"], "WHO WROTE THE CODE? 🤔"),
    (vo_at("d-03"), S["s20-hacker"] - vo_at("d-03"), "THE ROBOT: “ME.” 🗿"),
    (S["s20-hacker"], 2.2, "BECOME A REAL HACKER 🤓"),
    (S["s21-vuota"], 2.2, "THE HUMANS' DESK RN:"),
    (S["s22-guarda"], 2.2, "👁️👄👁️"),
    (S["s23-contributo"], 3.2, "SO WHAT DID THE HUMANS DO? 🤔"),
    (S["s24-team"], vo_at("d-04") - S["s24-team"], "STRATEGIC OVERSIGHT 👔 VISION 👓 LEADERSHIP 👑"),
    (vo_at("d-04"), S["s24b-invio"] - vo_at("d-04"), "THEY PRESSED ENTER 💀"),
    (S["s24b-invio"], S["s26-logo"] - S["s24b-invio"], "HE PRESSED THAT TOO 😭😭"),
    (S["s26-logo"], 4.5, "GG EZ 🏆"),
    (S["s27-tag"], FILM_DUR - S["s27-tag"], "NEXT YEAR: SOLO 🤖"),
]

# The humans' aura, going down: (film t, new value)
AURA0 = 100
AURA = [(vo_at("d-01"), -900), (S["s04-cane"] + 7.2, -5_900), (S["s09b-stretta"] + 8.4, -15_900), (vo_at("t-02", "The humans"), -25_900),
        (vo_at("t-05", "Humans measure"), -35_900), (vo_at("d-03"), -135_900), (vo_at("d-04"), -1_135_900)]

# Picture in picture reactions in the bottom band, muted unless `audio` (film t, clip, duration)
PIPS = [
    dict(t=S["s09-umani"] + 0.6, clip="p-familyguy", d=6.0, label="THE HUMANS RN"),
    dict(t=vo_at("t-05", "Desk"), clip="p-biddy", d=1.8, audio=True, label="SCRIB DOON ✍️"),
    dict(t=S["s16-mujoco"] + 0.8, clip="p-niulai", d=8.0, label="MUJOCO PHYSICS BE LIKE"),
    dict(t=S["s22-guarda"], clip="p-tony", d=2.2),
    dict(t=S["s26-logo"], clip="p-cat", d=4.5, audio=True, cat=True),
    dict(t=S["s27-tag"], clip="p-jiren", d=4.8, label="ME NEXT YEAR"),
]

# Sound effects on the film clock: (film t, file, gain)
SFX = [
    (vo_at("d-01"), "vine-boom", 0.8), (vo_at("d-02"), "vine-boom", 0.7),
    (S["s04-cane"] + 7.2, "fahhh", 0.9), (S["s04-cane"] + 7.6, "sad-violin", 0.55),
    (S["s07-ma"] + 0.1, "dun-dun-dunnn", 0.7), (S["s08-testa"], "among-us-role-reveal", 0.55),
    (vo_at("g1-01"), "vine-boom", 0.6),
    (S["s09b-stretta"] + 8.4, "spongebob-fail", 0.8),
    (S["s10-scrivania"] + bf.G3_CUT, "vine-boom", 0.8),
    (S["s12-cervello"] + 0.4, "anime-wow", 0.5),
    (vo_at("t-05", "Humans measure"), "metal-pipe-clang", 0.55),
    (S["s17-tasti"], "yanito932-beat", 0.6),
    (vo_at("d-03"), "vine-boom", 0.9),
    (S["s20-hacker"] + 0.35, "shocked", 0.7),
    (S["s21-vuota"], "its-like-im-not-even-here", 0.8),
    (S["s22-guarda"], "vine-boom", 0.7),
    (S["s24-team"] + 1.0, "vine-boom", 0.5), (S["s24-team"] + 2.1, "vine-boom", 0.5), (S["s24-team"] + 3.4, "vine-boom", 0.6),
    (vo_end("d-04"), "bruh", 0.9),
    (S["s26-logo"] + 0.1, "gg-freaking-ez-CLEAN", 0.55),
    (vo_at("g1-05"), "undertaker-bell", 0.5),
]
SFX_MAX = {"sad-violin": 3.6, "its-like-im-not-even-here": 2.2, "dun-dun-dunnn": 3.1, "among-us-role-reveal": 3.0,
           "gg-freaking-ez-CLEAN": 4.4, "undertaker-bell": 3.6, "anime-wow": 2.0}
PUNCH = [t for t, f, _ in SFX if f in ("vine-boom", "fahhh", "metal-pipe-clang", "spongebob-fail")]  # the film box jumps on these
YELLOW = "#fff94a"
KEYWORDS = {"dog", "brain", "grok", "yoloe", "mujoco", "me", "him", "humans", "human", "credit", "enter", "nah", "won't", "solo",
            "alone", "respect", "loop", "code", "font", "measure", "depth"}


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def words_of(vid: str) -> list[tuple[str, float, float]]:
    """(word, start, end) on the film clock from the TTS character timings; tags like [pause] and <slow> are skipped."""
    meta = bf.vo_meta(vid)
    ts = meta["timestamps"]
    text, times, skip = "", [], 0
    for c, tt in zip(ts["graph_chars"], ts["graph_times"]):
        if c in "[<":
            skip += 1
        if not skip:
            text += c
            times.append(tt)
        if c in "]>":
            skip = max(0, skip - 1)
    out_w, t0 = [], VO_AT[vid]
    for m in re.finditer(r"\S+", text):
        w = re.sub(r"[^\w'’.,!?:-]", "", m.group())
        if not w:
            continue
        out_w.append((w, t0 + times[m.start()][0], t0 + times[m.end() - 1][1]))
    # the subtitles show digits where the voice said words
    fix = {("four", "point", "five"): "4.5", ("three", "point", "six"): "3.6", ("YOLO", "E"): "YOLOE"}
    res, i = [], 0
    while i < len(out_w):
        for k, v in fix.items():
            seg = tuple(re.sub(r"[.,:!?]", "", x[0]) for x in out_w[i:i + len(k)])
            if seg == k:
                tail = re.sub(r"^[\w']+", "", out_w[i + len(k) - 1][0])
                res.append((v + tail, out_w[i][1], out_w[i + len(k) - 1][2]))
                i += len(k)
                break
        else:
            res.append(out_w[i])
            i += 1
    return res


def word_groups() -> list[dict]:
    groups = []
    for vid, _ in bf.VOICE:
        ws = words_of(vid)
        cur: list = []
        for w in ws:
            cur.append(w)
            if len(cur) == 3 or re.search(r"[.!?,:]$", w[0]):
                groups.append(cur)
                cur = []
        if cur:
            groups.append(cur)
    out_g = []
    for g in groups:
        out_g.append(dict(words=[w for w, _, _ in g], starts=[s for _, s, _ in g], start=g[0][1], end=g[-1][2] + 0.25))
    for a, b in zip(out_g, out_g[1:]):
        a["end"] = min(a["end"], b["start"] - 0.01)
    return out_g


def build() -> None:
    el, js, au = [], [], []
    z = 10

    def clip_attrs(cid: str, start: float, dur: float, track: int, extra: str = "", cls: str = "") -> str:
        return (f'id="{cid}" class="clip{" " + cls if cls else ""}" data-start="{round(start, 3)}" data-duration="{round(dur, 3)}" '
                f'data-track-index="{track}"{extra}')

    # 1) the film, in segments between the inserts (picture, blurred background, sound)
    cuts = sorted({0.0, FILM_DUR, *[i["at"] for i in INSERTS]})
    for k, (a, b) in enumerate(zip(cuts, cuts[1:])):
        if b - a < 0.01:
            continue
        o = out(a) if a > 0 else out(0.0)
        el.append(f'<video {clip_attrs(f"bg{k}", o, b - a, 1, f" data-media-start='{a}'")} src="assets/clips/film-bg.mp4" muted playsinline '
                  f'style="position:absolute;left:0;top:0;width:{W}px;height:{H}px;object-fit:cover;z-index:1"></video>')
        el.append(f'<div class="filmwrap" id="fw{k}" style="z-index:5"><video {clip_attrs(f"film{k}", o, b - a, 2, f" data-media-start='{a}'")} '
                  f'src="assets/clips/film.mp4" muted playsinline style="width:{W}px;height:{BOX_H}px;display:block"></video></div>')
        au.append(f'<audio {clip_attrs(f"afilm{k}", o, b - a, 20, f" data-media-start='{a}' data-volume='1'")} src="assets/sfx/film.wav"></audio>')
    # 2) full-screen inserts: black ground, the clip, the caption (three timed siblings, nothing nested)
    for k, ins in enumerate(INSERTS):
        o = out(ins["at"]) - ins["d"]
        el.append(f'<div {clip_attrs(f"insbg{k}", o, ins["d"], 3)} style="position:absolute;inset:0;background:#000;z-index:30"></div>')
        el.append(f'<video {clip_attrs(f"insv{k}", o, ins["d"], 4)} src="assets/clips/{ins["clip"]}.mp4" muted playsinline '
                  f'style="position:absolute;left:0;top:{(H - 608) // 2}px;width:{W}px;height:608px;object-fit:contain;z-index:31"></video>')
        el.append(f'<div {clip_attrs(f"inst{k}", o, ins["d"], 5, cls="instop")} style="z-index:32"><span id="insti{k}">{esc(ins["top"])}</span></div>')
        au.append(f'<audio {clip_attrs(f"ains{k}", o, ins["d"], 21, " data-volume='1'")} src="assets/sfx/{ins["clip"]}.wav"></audio>')
        js.append(f'tl.fromTo("#insti{k}", {{scale: 0.5, rotation: -4}}, {{scale: 1, rotation: 0, duration: 0.25, ease: "back.out(2.2)"}}, {o});')
    # 3) meme captions (top band) and the aura counter
    for k, (t, d, txt) in enumerate(CAPS):
        if d <= 0.05:
            continue
        o = out(t)
        el.append(f'<div {clip_attrs(f"cap{k}", o, d, 5, cls="topcap")} style="z-index:20"><span id="capi{k}">{esc(txt)}</span></div>')
        rot = (-3, 2, -2, 3, -1)[k % 5]
        js.append(f'tl.fromTo("#capi{k}", {{scale: 0.4, rotation: {rot * 3}}}, {{scale: 1, rotation: {rot}, duration: 0.22, ease: "back.out(2.5)"}}, {o});')
    vals = [(0.0, AURA0)] + AURA
    for k, ((t, v), nxt) in enumerate(zip(vals, vals[1:] + [(FILM_DUR, None)])):
        o, o2 = out(t), out(nxt[0])
        col = "#00d68f" if v > 0 else "#ff3860"
        el.append(f'<div {clip_attrs(f"aura{k}", o, o2 - o, 6, cls="aura")} style="z-index:21"><span id="aurai{k}" style="color:{col}">'
                  f'HUMAN AURA {"▲" if v > 0 else "▼"} {v:,}</span></div>')
        if k:
            js.append(f'tl.fromTo("#aurai{k}", {{scale: 1.8}}, {{scale: 1, duration: 0.35, ease: "back.out(3)"}}, {o});')
    # 4) the G1's words, big, under the film
    for k, g in enumerate(word_groups()):
        o, o2 = out(g["start"]), out(g["end"])
        spans = "".join(f'<span id="w{k}_{j}" class="{"kw" if re.sub(r"[^a-z0-9.]", "", w.lower()) in KEYWORDS else ""}">{esc(w)}</span> '
                        for j, w in enumerate(g["words"]))
        el.append(f'<div {clip_attrs(f"wg{k}", o, max(0.1, o2 - o), 7, cls="words")} style="z-index:22"><div id="wgi{k}">{spans}</div></div>')
        js.append(f'tl.fromTo("#wgi{k}", {{scale: 0.7, y: 20}}, {{scale: 1, y: 0, duration: 0.14, ease: "back.out(2)"}}, {o});')
        for j, s in enumerate(g["starts"]):
            js.append(f'tl.fromTo("#w{k}_{j}", {{opacity: 0.35}}, {{opacity: 1, duration: 0.05}}, {out(s)});')
    # 5) picture in picture reactions: an untimed wrapper (pops in) holding the timed frame and the timed clip
    for k, p in enumerate(PIPS):
        o = out(p["t"])
        ext = "webm" if p.get("cat") else "mp4"
        box = (180, 1150, 720, 720) if p.get("cat") else (110, 1330, 860, 484)
        frame = "" if p.get("cat") else (f'<div {clip_attrs(f"pipf{k}", o, p["d"], 10, cls="pipframe")}></div>')
        lab = (f'<div {clip_attrs(f"pipl{k}", o, p["d"], 11, cls="piplab")}>{esc(p["label"])}</div>') if p.get("label") else ""
        el.append(f'<div id="pipw{k}" class="pip" style="left:{box[0]}px;top:{box[1]}px;width:{box[2]}px;height:{box[3]}px;z-index:25">{frame}'
                  f'<video {clip_attrs(f"pipv{k}", o, p["d"], 9)} src="assets/clips/{p["clip"]}.{ext}" muted playsinline '
                  f'style="position:absolute;inset:{0 if p.get("cat") else 8}px;width:calc(100% - {0 if p.get("cat") else 16}px);'
                  f'height:calc(100% - {0 if p.get("cat") else 16}px);object-fit:{"contain" if p.get("cat") else "cover"};border-radius:18px"></video>{lab}</div>')
        js.append(f'tl.fromTo("#pipw{k}", {{scale: 0.2, rotation: 12}}, {{scale: 1, rotation: {(-4, 3, -3, 4)[k % 4]}, duration: 0.3, '
                  f'ease: "back.out(2)"}}, {o});')
        if p.get("audio"):
            au.append(f'<audio {clip_attrs(f"apip{k}", o, p["d"], 22, " data-volume='0.7'")} src="assets/sfx/{p["clip"]}.wav"></audio>')
    # 6) sound effects
    for k, (t, f, g) in enumerate(SFX):
        d = SFX_MAX.get(f, 1.4)
        au.append(f'<audio {clip_attrs(f"sfx{k}", out(t), d, 23 + k % 3, f" data-volume='{g}' data-fade-out='0.2'")} src="assets/sfx/{f}.wav"></audio>')
    # 7) punch-ins on the film box
    for t in PUNCH:
        o = out(t)
        for k in range(len(cuts) - 1):
            js.append(f'tl.fromTo("#fw{k}", {{scale: 1.0}}, {{scale: 1.09, duration: 0.06, ease: "power2.out", yoyo: true, repeat: 1}}, {o});')
    page = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={W}, height={H}" />
    <title>who did what · brainrot</title>
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
    <style>
      @font-face {{ font-family: "Noto Color Emoji"; src: url("assets/fonts/NotoColorEmoji.ttf") format("truetype"); }}
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ margin: 0; width: {W}px; height: {H}px; overflow: hidden; background: #000; }}
      #root {{ position: relative; width: 100%; height: 100%; background: #000; overflow: hidden;
               font-family: "Archivo Black", "Noto Color Emoji", sans-serif; }}
      .filmwrap {{ position: absolute; left: 0; top: {BOX_Y}px; width: {W}px; height: {BOX_H}px; transform-origin: 50% 50%;
                   box-shadow: 0 0 0 6px #000, 0 20px 60px rgba(0,0,0,.6); }}
      .topcap {{ position: absolute; left: 40px; right: 40px; top: 90px; height: 380px; display: flex; align-items: center; justify-content: center;
                 text-align: center; }}
      .topcap span, .instop span {{ display: inline-block; color: #fff; font-size: 74px; line-height: 1.08; text-transform: uppercase;
                 -webkit-text-stroke: 4px #000; paint-order: stroke fill; text-shadow: 0 7px 0 #000, 0 0 30px rgba(0,0,0,.5); }}
      .instop {{ position: absolute; left: 40px; right: 40px; top: 230px; text-align: center; }}
      .instop span {{ font-size: 80px; }}
      .aura {{ position: absolute; left: 0; right: 0; top: 478px; text-align: center; }}
      .aura span {{ display: inline-block; font-size: 40px; background: rgba(0,0,0,.75); padding: 8px 22px; border-radius: 40px;
                   border: 3px solid currentColor; letter-spacing: .02em; }}
      .words {{ position: absolute; left: 30px; right: 30px; top: 1188px; text-align: center; }}
      .words div {{ display: inline-block; color: #fff; font-size: 86px; line-height: 1.05; text-transform: uppercase;
                    -webkit-text-stroke: 5px #000; paint-order: stroke fill; text-shadow: 0 8px 0 #000; }}
      .words .kw {{ color: {YELLOW}; }}
      .pip {{ position: absolute; }}
      .pipframe {{ position: absolute; inset: 0; border-radius: 26px; background: #fff; box-shadow: 0 18px 50px rgba(0,0,0,.7); }}
      .piplab {{ position: absolute; left: 0; right: 0; top: 10px; text-align: center; color: #fff; font-size: 42px;
                 -webkit-text-stroke: 3px #000; paint-order: stroke fill; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{TOTAL}" data-width="{W}" data-height="{H}">
      {chr(10).join("      " + e for e in el).strip()}
      {chr(10).join("      " + a for a in au).strip()}
    </div>
    <script>
      const tl = gsap.timeline({{ paused: true }});
{chr(10).join("      " + j for j in js)}
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
"""
    (FILM / "index.html").write_text(page)
    print(f"{TOTAL} s, {len(INSERTS)} inserti, {len(CAPS)} didascalie, {len(PIPS)} pip, {len(SFX)} effetti, {len(word_groups())} gruppi di parole")


if __name__ == "__main__":
    build()
