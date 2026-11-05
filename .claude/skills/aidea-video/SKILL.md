---
name: aidea-video
description: How the team's demo video was made and how to remake or edit it - the mockumentary "who did what" (16:9, HyperFrames, Grok TTS voice of the G1, interviews with external-recorder audio, segmented footage, dashboard recordings) and its vertical brainrot cut. Use when asked to change, re-render or extend the video, add footage, retime a line, or make another version.
---

# aidea demo video

Everything is generated from Python scripts in `video/`; the HyperFrames projects are build output. Raw media is never in git.

## Pipeline (16:9 film, `video/film/`)

1. **Footage** in `assets/footage/` (gitignored), downloaded from the team's public Drive folder with `gdown --folder <url>`; files are hard-linked under scene names (`g1-porta-a-spasso-il-cane.mp4`, `int-romeo.mp4`, `r2-dashboard-finale.mov`, …).
2. **Segmented footage**: `scripts/yoloe_footage.py` (same YOLOE model and drawing as the G1 dashboard) → `video/assets/yolo/en-*.mp4`; `--solid person` anonymises other participants.
3. **Voice**: lines in `video/vo-lines.json` (English, first person, Grok TTS voice `orion`, speech tags like `[pause]`, `<emphasis>`); `python video/make_vo.py` calls `POST /v1/tts` with `XAI_API_KEY` from `.env` and keeps the character timings for subtitles.
4. **Assets**: `python video/make_assets.py` → `video/film/assets/` (H.264 1080p30 proxies with a keyframe per second, HLG→SDR tonemap for phone HDR, 16:9 crops, whole-dashboard frames + slightly blurred copies, interview audio from the external recorder re-timed onto the phone video with offsets found by cross-correlation, Artific fonts, logo).
5. **Composition**: `python video/build_film.py` writes `video/film/index.html` + `compositions/*.html` from one timeline (`SCENES`): shots, lower thirds, cards, focus windows on the dashboard, captions timed from the TTS timestamps, interview ducking, music, ambient air.
6. **Check and render**: `cd video/film && npx hyperframes check && npx hyperframes render --quality looks -o renders/finale.mp4` (~25 min for 3 min on 4 CPUs; `--quality draft` while iterating). Verify with `npx hyperframes audio <file> --json` and a frame sheet.

## Brainrot cut (9:16, `video/brainrot/`)

`python video/brainrot/build_brainrot.py` reads the film timeline and lays the finished film (whole, never cut) in a vertical frame with meme inserts, captions, a "human aura" counter, big word captions and reactions from the team's meme pack (`assets/memes/pack/`, gitignored, copyrighted: parody use only; no explicit variant, no memes from its "do not use" list). Render as above from `video/brainrot/film`.

## Rules that were agreed

- "aidea" always lowercase; no em dashes in on-screen text; jokes target "the humans" (the team) and the situation, never other participants; no mention of the judges.
- Technical claims must be true in the code (e.g. Grok 4.5 via the xAI API; the measured perception line is in the G1 agent prompt since commit "g1 agent: a ogni passo Grok riceve anche la riga di percezione").
- The third-party skills used (brag, HyperFrames, media-use) are installed with `./scripts/install-video-skills.sh`.
