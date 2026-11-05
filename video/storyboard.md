# Storyboard: "Chi ha fatto cosa"

Video del team aidea per il Grok Hackathon at the Museum (Pavia, 4-5 novembre 2026).

- **Formato:** 1920×1080, 30 fps, circa 90 s.
- **Stile:** mockumentary alla The Office, camera a mano, silenzi lunghi un secondo di troppo, cartelli su nero. Le interviste sono in stile DMAX: parliamo in inglese, l'audio originale si abbassa e un doppiatore italiano parla sopra, con i sottotitoli.
- **Regola comica:** il doppiatore italiano dice sempre la verità. In inglese ci vantiamo, in italiano si sgonfia tutto. La prima intervista è tradotta fedelmente, per far credere che il doppiaggio sia normale.
- **Il G1 parla in italiano**, con una voce piatta e un po' sprezzante. Nessuno spiega le battute.
- **Voci:** Grok TTS (`POST /v1/tts`, `language: it`). Scelte misurando la variazione di tono di tutte le 28 voci: **G1 = `liora`** (la più espressiva, per niente robotica), **doppiatore = `helios`** (la più bassa e piatta, da doppiatore annoiato). Battute in `video/vo-lines.json`, generate con `python video/make_vo.py`.
- **Grafica:** palette aidea (nero `#0a0a12`, viola `#4300de` / `#8f3fff`, giallo `#fff94a`), font Artific (`src/ui/static/fonts/`), logo `video/assets/aidea-logo.webp`. "aidea" sempre minuscolo, niente trattini lunghi nei testi.
- **Audio:** l'audio delle clip non ha parlato utile: lo usiamo solo come rumore di sala nei silenzi. Musica: un brano in bundle con brag ("Happy Beats / Business Moves", ende.app, CC BY 4.0, va citato), solo nell'atto 1 e nel finale. Effetti sonori: tasti e clic amplificati (Kenney, in bundle con brag).

## Timeline (montaggio attuale, bozza v4)

Generata da `video/build_film.py`. Durata 2:50. **Tutto in inglese** (voce, scritte, sottotitoli). Narra il G1 **in prima persona**, voce Grok TTS `orion`. Nelle interviste la prima frase vera si sente piena, poi l'inglese scende e il G1 "corregge" sopra.

| Scena | Inizio | Cosa si vede | Cosa si sente / si legge |
|---|---|---|---|
| s01 | 0:00 | Foto del G1 appeso alla gru | "Wednesday, 4:37 PM." |
| s02 | 0:03 | Romeo | "In 36 hours we built…" → G1: "In thirty-six hours, **I** built something that is going to change robotics. Forever." |
| s03 | 0:12 | Puddu (jump cut) | "It's a fully autonomous, multimodal…" → G1: "It's a dog. It walks." → "…natural language" |
| s04 | 0:19 | Il G1 porta a spasso il cane | Musica, "Obeys." "Moves." "Understands."; la musica si ferma quando il cane si accuccia |
| s05 | 0:29 | Puddu muto (breve) | Silenzio |
| s07 | 0:31 | Cartello | "But there's something I haven't told you." |
| s08-s10 | 0:34 | Testa del G1, umani segmentati, POV robot, Romeo muto | "I programmed the dog." / "These are the humans…" / "…And a human taking the credit." |
| s11 | 0:54 | Capitolo "How I work (explained for humans)" | "Now let me explain how I work. Slowly." |
| s12 | 0:58 | Zoom su "Grok 4.5" nella dashboard, poi il video verticale del G1 con due di noi (sfondo sfocato) | **MY BRAIN · Grok 4.5 · xAI API**. "The humans pasted the key into the .env file. Their most technical moment." |
| s13 | 1:10 | Mano del G1 sulla tastiera, "Go to the desk!" scritto in chat, passi dell'agente nella dashboard | **FUNCTION CALLING · move · look · finish** |
| s14 | 1:23 | Girato vero segmentato (etichette in inglese) | **SEGMENTATION · YOLOE** (+ SAM 3) |
| s15 | 1:38 | Pannelli oggetti + profondità, poi la tabella live distanza/altezza | **DISTANCE & HEIGHT · mask × depth**. "…These numbers come to me with every image, so I don't walk into things." |
| s16 | 1:55 | Dashboard intera, il G1 simulato che va alla scrivania | **SIMULATOR · MuJoCo** |
| s17 | 2:07 | Jump cut sui tasti | "I wrote the dog's code. They picked the slide font." |
| s18 | 2:14 | Rios (accorciato, senza il fermo immagine) | "Who wrote the code?" → G1: "Me." |
| s20-s22 | 2:22 | "Become a real Hacker", scrivania vuota, il G1 in camera | Silenzio |
| s23 | 2:29 | Cartello | "I asked the humans what they contributed." |
| s24 | 2:32 | Il team ("THE HUMANS") | "Strategic oversight. Vision. Leadership." → G1: "They pressed enter." |
| s25 | 2:39 | Invio in chat | Clic, la musica riparte |
| s26-s27 | 2:42 | Logo con crediti tecnici, calci del G1 | "Next year, I'm coming alone." |

Registrazioni dello schermo: la seconda di Francesco (`screen_recording_finale.mov`: "Grok 4.5" nell'intestazione, simulatore + oggetti + profondità) per UI, chat e simulatore; la prima solo per la tabella live di distanze e altezze (nella seconda il pannello laterale è chiuso).

## Interviste da girare (stile DMAX)

**Come girarle (vale per tutte):**
- Telefono **orizzontale**, 4K o 1080p a 30 fps, fermo (treppiede o appoggiato) all'altezza degli occhi, a 1-1,5 m.
- Inquadratura da mezzo busto, la persona su un terzo del quadro (non al centro).
- Si guarda **un intervistatore in piedi accanto al telefono**, non l'obiettivo.
- Sfondo: il museo, meglio se con **il G1 fermo dietro, fuori fuoco**, oppure il cockpit con l'insegna FIAMM.
- Posto silenzioso, telefono vicino a chi parla. L'inglese va tenuto basso ma deve capirsi.
- Recitate con **entusiasmo esagerato**: il contrasto con il doppiaggio piatto è la battuta.
- Per ogni battuta fate 3 prese:
  1. 1 s di silenzio;
  2. la battuta;
  3. 3 s fermi a guardare l'intervistatore;
  4. poi giratevi lentamente verso l'obiettivo e restate 2 s senza espressione.
- Lo sguardo in camera finale lo uso nei tagli.
- Nomi dei file: `intervista-1-romeo.mp4`, `intervista-2-puddu.mp4`, `intervista-3-rios.mp4`, `intervista-4-team.mp4`, nella stessa cartella Drive.

| # | Chi | Dice in inglese | Il doppiatore dice (e i sottotitoli) |
|---|---|---|---|
| 1 | Federico Romeo | "In thirty-six hours, we built something that is going to change robotics. Forever." | "In trentasei ore abbiamo fatto una cosa che cambierà la robotica. Per sempre." (fedele) |
| 2 | Francesco Puddu | "It's a fully autonomous, multimodal, agentic quadruped. It sees. It plans. It reasons. It understands natural language." | "È un cane. Cammina." |
| 3 | Federico Rios | "Who wrote the code? Honestly, it was a real team effort. Everybody contributed equally." | "Il robot." |
| 4 | Tutti e tre, spalla a spalla come in una foto di squadra | Romeo: "Strategic oversight." Puddu: "Vision." Rios: "Leadership." (uno dopo l'altro, fieri) | "Abbiamo premuto Start." (un solo doppiatore per tutti e tre) |

Opzionale: tutti e tre in fila che guardano in camera in silenzio per 5 s, da usare come reazione.

**Montaggio del doppiaggio:**
- L'inglese parte pieno; dopo circa 0,5 s scende a circa -18 dB e attacca il doppiatore.
- Il doppiaggio finisce molto prima dell'inglese, che continua sotto senza sottotitoli: è lì che sta il silenzio imbarazzato.
- Sottotitoli bianchi con bordo nero, in basso al centro. Lower third con il nome in maiuscolo.

## Registrazioni della dashboard (le fa il collega)

**Preparazione, una volta:**

```bash
git fetch origin && git checkout sam3 && git pull origin sam3
./scripts/setup.sh                 # se non l'ha mai lanciato; poi:
source .venv/bin/activate
pip install -r requirements.txt    # onnxruntime e opencv per la percezione
python src/g1/g1_app.py --port 8766 --scene desk
```

**Browser e registrazione:**
- Chrome a schermo intero, zoom 100%, monitor almeno 1920×1080 (meglio 2560×1440). Chiudi le notifiche.
- Apri <http://127.0.0.1:8766/?head=annotated>.
- Nel pannello "Percezione" lascia **YOLOE**.
- Aspetta che sulla telecamera della testa compaiano le etichette con le distanze.
- Registra lo schermo intero a 30 fps (meglio 60), senza audio: su macOS Cmd+Shift+5 → "Registra intero schermo", su Windows/Linux OBS.

| # | Cosa | Durata | Azioni, secondo per secondo |
|---|---|---|---|
| **R1** (obbligatoria) | Scena della scrivania, scheda "oggetti" | 25 s | Cursore fuori dallo schermo. 0-6 s fermo. 6-14 s tieni premuto **W**: il G1 cammina verso la scrivania; lascia quando è a circa 0,8 m. 14-19 s fermo. 19-25 s tieni **A** per girarti piano verso la sedia, poi fermo. **Annota** le distanze di portatile e sedia nei primi secondi: le dice il G1 nella scena 11. |
| **R2** (consigliata) | Chat "Parla al G1" | 30-45 s | Premi **R** per rimettere il G1 al punto di partenza. Cursore visibile. Scrivi nella chat: `vai al portatile e fermati davanti`, premi invia, poi non toccare niente fino alla risposta finale. |
| **R3** (obbligatoria) | Il pulsante Start | 6 s | Zoom del browser al 200% (Cmd/Ctrl +). Scorri fino alla sezione "Modalità del robot", con **Start (R)** al centro dello schermo. Cursore visibile. A 2 s portalo lentamente sul pulsante, a 3,5 s un solo clic, poi resta fermo 2 s. |
| **R4** (opzionale) | Chat del cane nel simulatore | 25 s | `python src/chat/app.py` (su macOS `mjpython`), <http://127.0.0.1:8765>, Go1 in `mock · MuJoCo`. Scrivi `vai verso la scala`, registra finché si ferma. |

R2 e R4 usano l'agente, quindi serve la chiave Grok nel `.env` di quel PC; R1 e R3 no.

Opzionale, mentre giri R1: il flusso pulito della telecamera segmentata, senza interfaccia, in un altro terminale (fermalo con Ctrl+C):

```bash
ffmpeg -use_wallclock_as_timestamps 1 -f mpjpeg -i "http://127.0.0.1:8766/api/perception.mjpg?view=annotated" \
       -vf fps=30 -c:v libx264 -crf 16 -pix_fmt yuv420p r1-percezione-pulita.mp4
```

Carica tutto sulla cartella Drive: `r1-cosa-riconosce.mp4`, `r2-parla-al-g1.mp4`, `r3-start.mp4`, `r4-chat-cane.mp4`.

## Segmentazione sul girato vero (fatta qui)

Stesso modello e stesso disegno della dashboard (YOLOE, `src/vision/yolo_onnx.py`), con lo script `scripts/yoloe_footage.py` del branch `sam3`.
- Etichette in italiano.
- Persone riempite di viola: così gli altri partecipanti non si riconoscono.
- Niente distanze, perché un video da telefono non ha profondità.
- Per ogni clip c'è anche un JSONL con gli oggetti di ogni fotogramma.

| File in `video/assets/yolo/` | Sorgente | Uso |
|---|---|---|
| `yolo-testa-g1.mp4` | `testa-g1-sulla-dashboard.mov` [25-45], ritagliata sulla telecamera della testa | Scena 10 |
| `yolo-g1-arriva-scrivania.mp4` | `g1-arriva-alla-scrivania.mov` [28-39] | Scena 11 |
| `yolo-pov-scrivania.mp4` | `pov-verso-scrivania-1.mp4` [6-14] | Riserva per la scena 11 |
| `yolo-g1-osserva-umani.mp4` | `g1-osserva-umani.mp4` | Riserva per la scena 10 |
| `yolo-g1-tra-partecipanti.mp4` | `g1-tra-i-partecipanti.mp4` | Riserva per la scena 10 |

Per rifarle (dal branch `sam3`):

```bash
python scripts/yoloe_footage.py assets/footage/pov-verso-scrivania-1.mp4 -o out/pov.mp4 --start 6 --duration 8 --width 1920 --it --solid person
```

## Girato disponibile

| File (`assets/footage/`) | Cosa si vede |
|---|---|
| `foto-g1-appeso-alla-gru.jpg` | Mercoledì 16:37, il G1 appeso alla gru |
| `g1-porta-a-spasso-il-cane.mp4` (10 s) | Il G1 porta il Go1 al guinzaglio; a 6-7 s il cane si accuccia |
| `foto-g1-cane-guinzaglio.heic` | La stessa scena; un membro del team, seduto, fissa la camera |
| `foto-team-perplesso.heic` | Due di noi perplessi davanti al G1 |
| `foto-g1-con-umano.heic` | Uno di noi accanto al G1 |
| `g1-cammina-con-umani.mp4` (5 s, verticale) | Il G1 cammina accanto a due di noi ed esce di campo |
| `g1-arriva-alla-scrivania.mov` (39 s, 4K) | Il G1 alla scrivania col portatile, se ne va (12 s), la scrivania resta vuota (14-28 s), lui torna (30-38 s) |
| `testa-g1-sulla-dashboard.mov` (77 s, verticale 4K) | Il telefono riprende la dashboard: la telecamera della testa del G1 vero inquadra le persone |
| `g1-scrivania-tasti-frenetici.mp4` (13 s) | Braccia sulla tastiera, scheda hackertyper.net a 6 s, primo piano della testa a 11-13 s |
| `g1-tasti-closeup.mov`, `g1-tasti-si-gira.mov` (verticali 4K) | Tasti pestati; a 9,5-11,5 s il G1 si gira verso la camera |
| `g1-mano-hackertyper.mp4` (6 s, verticale) | Il guanto che digita su Hacker Typer |
| `g1-osserva-umani.mp4`, `g1-tra-i-partecipanti.mp4`, `g1-cammina-verso-camera.mp4` | Il G1 tra i tavoli dell'hackathon |
| `g1-stretta-di-mano.mp4` (11 s) | Batte il cinque a un uomo in giacca (volto fuori campo) |
| `pov-verso-scrivania-1.mp4`, `pov-verso-scrivania-2.mov` | Soggettiva dal cockpit del simulatore di volo alla scrivania |
| `g1-balla.mp4` (7 s, verticale, bassa risoluzione) | Il G1 balla |
| `pov-robot.mov` (8 s, 4K) | Soggettiva fluida dal cockpit alla scrivania col portatile: la versione segmentata è la scena 11 |
| `g1-extra-212938.mp4` (50 s) | Il G1 da solo nella sala grande, a 29-42 s tira calci |

## Composizione

La composizione HyperFrames è in `video/film/`, generata da `video/build_film.py` (timeline, scritte, sottotitoli dai tempi del TTS, audio). Interviste e registrazioni mancanti sono cartelli "SEGNAPOSTO". Per rigenerare:

```bash
python video/make_vo.py && python video/make_assets.py && python video/build_film.py
cd video/film && npx hyperframes check && npx hyperframes render --quality draft -o renders/bozza.mp4
```

Lower third: Romeo "AI Engineer · aidea", Puddu "AI Engineer · aidea · responsabile del cane", Rios "AI Engineer · aidea · responsabile del font delle slide" (richiamo alla battuta del G1).

## Da decidere

- Se l'intervista 4 regge con tre persone in un'inquadratura sola, o se la giriamo come tre primi piani montati di fila.
