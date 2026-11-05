# Percezione live del G1: cosa vede, a che distanza, quanto è alto

> **Stato del 2026-11-04 (notte):** funziona nel simulatore e sul percorso del robot vero provato con una **finta testa stereo** (stesso protocollo, nessun robot). **Mai provato sulla testa vera**: la calibrazione dello stereo va fatta sul posto (15 minuti col metro). Le misure di tempo sono su un i7-1360P in WSL2 senza GPU; i Mac dovrebbero essere più veloci (non misurato).

Nella webapp del G1, sotto la telecamera della testa, tre schede:

- **camera**: il video di sempre;
- **oggetti**: le maschere degli oggetti con **distanza** dalla camera e **altezza** dal pavimento;
- **profondità**: la mappa di profondità (rosso vicino, blu lontano).

Il pannello "Percezione" a destra elenca gli oggetti con distanza, altezza e direzione, e permette di scegliere il modello e i prompt. `?head=annotated` nell'URL apre direttamente sugli oggetti: è la "dashboard" da tenere aperta in parallelo.

## Provarla

```bash
python src/g1/g1_app.py --port 8766 --scene desk      # simulatore: scrivania con portatile e mouse, sedia normale
```

Apri <http://127.0.0.1:8766/?head=annotated>. Nel simulatore la profondità è **esatta** (buffer di profondità di MuJoCo).

Come parte la scena `desk`:

- **Scena:** una scrivania con sopra un portatile aperto (tipo MacBook) e un mouse, e una sedia normale a quattro gambe (non da ufficio), come ai tavoli dell'hackathon.
- **Posizione:** il G1 parte a circa 1,7 m dalla scrivania, girato verso il suo centro. Portatile e mouse sono al centro della camera della testa, la sedia quasi intera a sinistra. La vista esterna lo mostra di profilo davanti alla scrivania.
- **Controller:** `lab29`, perché con `gym12` il G1 "fermo" se ne va da solo (1,7 m e 30° in 10 s, misurato).
- **Mantiene la posizione:** senza comandi, il simulatore riporta il robot dove l'hai lasciato, come fa il G1 vero quando non riceve `Move`. Misurato: entro 1 cm e 3° in 30 s.
- **Comandi:** con WASD lo sposti, e la nuova posizione diventa quella da mantenere. R lo rimette al punto di partenza.

Percorso del robot vero **senza robot**: `scripts/fake_g1_head.py` renderizza la scena da due camere a 60 mm e la trasmette come lo streamer della testa (hello UDP 5601, H.264 side-by-side via RTP). Sulla stessa macchina la porta video va spostata, perché ffmpeg occupa anche porta+1 per l'RTCP, che lì è la 5601 della finta testa:

```bash
python scripts/fake_g1_head.py                         # terminale 1
G1_CAMERA_PORT=5610 python tests/test_g1_stereo_stream.py   # terminale 2: discovery + stereo + pavimento
```

Col robot vero (lo avvia una persona, come sempre): `python src/g1/g1_app.py --port 8766 --real`. La camera funziona anche col robot **non armato** ("solo camera"); la profondità viene dallo stereo della testa.

## Cosa arriva all'agente

A ogni passo della chat del G1 (`src/g1/g1_agent.py`), oltre all'immagine della testa, Grok riceve una riga con gli oggetti misurati, dal più vicino: `Percezione misurata (segmentazione + profondità della telecamera, di 0.3 s fa): mouse a 1.90 m, davanti; desk a 2.03 m, 3° a destra, alto 0.75 m; …`. La riga c'è solo se la percezione è attiva, senza errori e l'analisi ha meno di 5 s; altrimenti l'agente lavora sulla sola immagine, come prima. Il prompt gli dice di usare quelle distanze per decidere quanto avanzare e per non urtare gli oggetti, come informazione e non come ordine. Test: `test_perception_line` in `tests/test_g1_agent.py`.

## Modelli di segmentazione

| Backend | Cosa trova | Tempo per frame (misurato) | Dove |
|---|---|---|---|
| **yoloe** (default) | testo libero da un vocabolario d'ufficio di 40 parole (desk, chair, tv, laptop, keyboard, mouse, person…) | 220–350 ms (~3 fps) | CPU, onnxruntime |
| **yolo** | le 80 classi COCO (chair, tv, laptop, keyboard, mouse, dining table, person… **niente "desk"**) | 70–145 ms | CPU, onnxruntime |
| **sam3** | qualsiasi testo, maschere migliori | 1–4 s, quindi a campione ogni N secondi | Roboflow cloud |

- **YOLOE** è l'equivalente piccolo di SAM 3 (prompt di testo e maschere). Sulla foto vera del tavolo trova la scrivania intera, i laptop, i mouse e le persone in circa 300 ms. I monitor li trova come **"tv"**, che mostriamo come "monitor": "computer monitor" non funziona.
- Gli embedding del vocabolario sono già calcolati in `src/vision/yoloe_vocab.npz`. Per aggiungere parole serve `scripts/yoloe_vocab.py`, che scarica una volta il text encoder da 260 MB.
- I pesi (YOLO26n-seg 11 MB, YOLOE-26s-seg 43 MB, licenza AGPL-3.0) si scaricano da soli in `vendor/models/` al primo uso, con verifica SHA-256.
- **Scartati:**
  - EfficientSAM3: non c'è un ONNX pubblicato.
  - RF-DETR-Seg nano: 300–400 ms su CPU, più lento di YOLOE e senza testo.
  - Modelli SAM con solo prompt a punti o box (MobileSAM, EdgeSAM, SAM 2.1 tiny): non accettano testo.
  - Roboflow via HTTP: già 0,25–0,5 s di sola rete per frame.

## Profondità

- **Simulatore:** esatta, dal buffer di profondità di MuJoCo (20–60 ms a 640x360). Anche il pavimento (altezza e inclinazione della camera) è esatto, dalla posa della camera.
- **Robot vero:** stereo della testa custom (side-by-side, decodificato a 800x600 per occhio), OpenCV **StereoSGBM** in 30–55 ms. Il pavimento si stima con un **RANSAC** sui punti 3D. I modelli stereo neurali sono stati misurati sulla stessa CPU a 0,4–2,6 s per frame (HITNet, CREStereo, Fast-ACVNet): non sono live.
- **Misura di un oggetto:** la maschera viene erosa, poi si prende la mediana della distanza. Altezza (97° percentile sopra il pavimento) e larghezza vengono solo dai punti vicini alla profondità dell'oggetto, così una maschera che sborda sullo sfondo non le gonfia.

## Risultati misurati

**Geometria, simulatore, maschere esatte** (`tests/test_vision_sim.py`):

| Oggetto | Altezza misurata | Vera |
|---|---|---|
| Portatile (bordo dello schermo) | 0,95 m | 0,96 m |
| Sedia (schienale) | 0,84 m | 0,86 m |
| Scrivania | 0,75 m | 0,75 m |

- Camera: 1,262 m contro 1,262 m, sia dalla posa sia dal RANSAC sulla sola profondità.

**Catena completa nel simulatore con YOLOE** (webapp, `--scene desk`, dal punto di partenza):

| Oggetto | Score | Distanza | Altezza misurata | Vera |
|---|---|---|---|---|
| Sedia | 0,92 | 1,71 m | 0,85 m | 0,86 m |
| Mouse | 0,82 | 1,87 m | 0,79 m | 0,78 m |
| Scrivania | 0,77 | 1,90 m | 0,75 m | 0,75 m |
| Portatile | 0,88 | 2,06 m | 0,96 m | 0,96 m |

Circa 2 analisi al secondo, 320 ms di segmentazione. Qui il limite è il rendering software del simulatore su questa macchina, non il modello. Sullo stesso frame SAM 3 trova scrivania 0,94, sedia 0,93, portatile 0,96 e mouse 0,91.

**Stereo contro verità** (`tests/test_vision_stereo.py`, coppie renderizzate con baseline 60 mm e FOV 75°):

- Errore mediano sul frame: 1,6–1,8%.
- Per oggetto, entro il 3,1% in tutte e tre le viste. Esempi: portatile a 2,09 m contro 2,09 m, scrivania a 1,97 m contro 1,95 m, sedia a 0,98 m contro 0,97 m.
- Con la sedia da ufficio nera e senza texture della prima versione della scena si arrivava a +8%: le superfici scure e uniformi sono il caso peggiore.

Questo è il limite del solo matcher: sul modulo vero si aggiunge l'errore di calibrazione.

**Catena del robot vero con la finta testa** (`tests/test_g1_stereo_stream.py`):

- Discovery, RTP H.264, decodifica, stereo: profondità sul 59% dei pixel, matching in 38 ms.
- Pavimento stimato dallo stereo: camera a 1,261 m (vera 1,25), inclinazione 14,0° (vera 14,0°).

**Calibrazione col metro:** il fit su 4 distanze simulate dà k = 30,94 contro 31,28 ideale. Gli errori residui sono +0,2 cm a 1 m, −4 cm a 2 m, +10 cm a 3 m e −3 cm a 4 m.

## Calibrazione della testa vera (da fare sul posto)

Il modulo stereo non è documentato: il repo `g1-stereo-stream` non è pubblico. Probabilmente è un ELP global shutter 3200x1200 (OG02B10), con la baseline da misurare col calibro. Senza calibrazione l'app usa FOV 75° e baseline 60 mm **ipotizzati** e scrive "stereo (non calibrato)": le distanze sono sbagliate di un fattore costante.

```bash
python scripts/g1_stereo_calibrate.py
```

1. Metti un bersaglio con texture (una scatola, un poster, una persona; non uno schermo acceso né un muro bianco) al **centro** dell'immagine.
2. Ripeti a 4–6 distanze misurate col metro, tra 0,7 e 4 m, scrivendo ogni volta la distanza.
3. Lo script stima da solo lo spostamento verticale tra gli occhi e se le due metà sono invertite, poi calcola il fit z = k / (d − d0).
4. Salva il risultato in `src/g1/stereo_calib.json`.

In alternativa si può usare una calibrazione OpenCV completa con la scacchiera (`kind: "opencv"`, matrici K1 D1 K2 D2 R T), letta dallo stesso file.

## Limiti

- **Superfici senza texture:** schermi accesi, muri bianchi, plastica nera opaca. Lo stereo non trova corrispondenze lì, quindi la distanza di quegli oggetti è meno affidabile, o manca.
- **Errore dello stereo con la distanza:** cresce col quadrato della distanza. Con 60 mm di baseline a 800 px, circa 2 cm a 1 m, 6–8 cm a 2 m e 25–35 cm a 4 m (stima teorica della ricerca).
- **Oggetti coperti:** se ne misura solo la parte visibile. Nella prima versione della scena, un PC nascosto dietro la sedia risultava alto 2 cm.
- **SAM 3:** il risultato si riferisce al frame analizzato. In movimento, la vista "oggetti" mostra quel frame con la sua età.
- **Robot simulato:** con `gym12` deriva anche da fermo (si sposta e si gira da solo). Va riportato davanti alla scrivania con WASD.
- **WSL2:** la rete NAT di default potrebbe non far passare broadcast e RTP del robot vero. Non provato: forse serve la rete "mirrored".

## File

- `src/vision/rgbd.py`: intrinseci, punti 3D, pavimento (RANSAC), misura per maschera, colori della profondità.
- `src/vision/live.py`: il worker live (segmentazione nel suo thread, misura sullo stesso frame, viste JPEG, log JSONL).
- `src/vision/segmenters.py`, `src/vision/yolo_onnx.py`: i backend `yoloe`, `yolo` e `sam3`.
- `src/vision/stereo.py`: StereoSGBM, calibrazione.
- `src/g1/g1_world.py` (`head_rgbd`, `--scene desk`), `src/g1/g1_real.py` (coppia stereo e `head_rgbd`), `src/g1/g1_app.py` (`/api/perception`, `/api/perception.mjpg?view=annotated|depth`).
- Script: `scripts/fake_g1_head.py`, `scripts/g1_stereo_calibrate.py`, `scripts/yoloe_vocab.py`.
- Test: `tests/test_vision_sim.py`, `tests/test_vision_stereo.py`, `tests/test_g1_stereo_stream.py`.

## Fonti

- YOLO26-seg e YOLOE: docs.ultralytics.com/tasks/segment, docs.ultralytics.com/models/yoloe.
- ONNX usati: huggingface.co/DeveloperDobby/yolo26n-seg, huggingface.co/harvestsu/yoloe-26s-seg-onnx (embin e text encoder).
- Decodifica YOLOE di riferimento: github.com/suharvest/openvoicestream (MIT).
- Tokenizer CLIP: github.com/openai/CLIP (`bpe_simple_vocab_16e6.txt.gz`).
- Stereo:
  - OpenCV `samples/python/stereo_match.py` e `samples/cpp/stereo_calib.cpp`;
  - PINTO model zoo (HITNet, RealtimeStereo, CREStereo, Fast-ACVNet, misurati e scartati);
  - nicolas.burrus.name/stereo-comparison.
- Modulo probabile: ELP-USB3DGS1200P01 (pagine prodotto ELP/Amazon). Teste stereo Unitree: github.com/unitreerobotics/xr_teleoperate `Device.md`.

## Sul girato del telefono (per il video)

`scripts/yoloe_footage.py` fa passare un video registrato nello stesso modello e con lo stesso disegno della dashboard (maschere, contorni, etichette, barra di stato), fotogramma per fotogramma, e scrive un MP4 H.264 più un JSONL con gli oggetti di ogni fotogramma. Legge HEVC e rotazione dei telefoni tramite ffmpeg. Sul girato non c'è profondità: le etichette hanno solo il nome e la confidenza, niente distanza né altezza.

```bash
pip install onnxruntime opencv-python-headless numpy        # già nella venv se hai fatto setup.sh
python scripts/yoloe_footage.py assets/footage/pov-verso-scrivania-1.mp4 -o out/pov.mp4 --start 6 --duration 8 --width 1920 --it --solid person
```

- `--it` etichette in italiano (person → umano, desk → scrivania…); `--solid person` riempie le persone di colore pieno (anonimizza gli altri partecipanti).
- `--vf` filtro ffmpeg applicato prima (es. `crop=iw:ih*0.47:0:ih*0.30` per tenere solo la telecamera della testa in un video girato allo schermo).
- Misurato su CPU (4 core, nessuna GPU): YOLOE a 1280–1920 px circa 3 fotogrammi al secondo, cioè 2–3 minuti per 10 s di video a 30 fps.
