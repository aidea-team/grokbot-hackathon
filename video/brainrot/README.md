# Versione brainrot (Instagram, 9:16)

Il film finale intero al centro, mai tagliato: si ferma solo per brevi meme a tutto schermo. Sopra ci sono didascalie meme e il contatore "HUMAN AURA"; sotto, le parole del G1 grandi e le reazioni in sovrimpressione; in più gli effetti sonori. Generata da `build_brainrot.py`, che legge la timeline del film da `video/build_film.py`.

Materiale (non in git, protetto da copyright, uso parodistico):
- `assets/memes/pack/meme-pack/` dal `meme-pack.zip` del team (cartella Drive `brainrot`): clip e sound effect;
- `video/film/renders/finale-v6.mp4`, il film finale.

```bash
python video/brainrot/build_brainrot.py
cd video/brainrot/film && npx hyperframes render -o renders/brainrot.mp4
```

Gli asset in `video/brainrot/film/assets/` (tagli delle clip, film in verticale, sfondo sfocato, effetti) sono prodotti con ffmpeg dai comandi descritti nella sessione e sono ignorati da git.
