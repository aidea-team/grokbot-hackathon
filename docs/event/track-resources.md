# Risorse pubbliche citate nelle tracce: cosa sono e come usarle in 5 minuti

> **Verificato il:** 2026-11-03 sera. URL, licenze e versioni controllati oggi su GitHub (API), PyPI, Hugging Face, figshare, Docker Hub e sui siti ufficiali; fonti in fondo.
> **Legenda:** ⚠️ = non verificato oppure dedotto. **Nessuno snippet è stato eseguito** (tranne dove indicato): sono presi dai README o dalle doc ufficiali, adattati.
> Le tracce: [tracks.md](tracks.md) (testo originale in [raw/tracks.txt](raw/tracks.txt)). Bracci: [../hardware/robot-arm.md](../hardware/robot-arm.md). Cane: [../hardware/robot-dog.md](../hardware/robot-dog.md). Voce: [../voice/README.md](../voice/README.md).

## Riepilogo

| Risorsa | Traccia | Cos'è | Licenza | Dove |
|---|---|---|---|---|
| YOLO-World | A | Detector open-vocabulary (oggetti da testo) | GPL-3.0 (repo); via Ultralytics AGPL-3.0 | [AILab-CVC/YOLO-World](https://github.com/AILab-CVC/YOLO-World) |
| EdiFabric EDIFACT examples | B | File EDI di esempio ORDERS, DESADV, INVOIC (+ esempi C#) | ⚠️ nessun file di licenza | [EdiFabric/EDIFACT.NET](https://github.com/EdiFabric/EDIFACT.NET) (ex `EDIFACT-Examples`, redirect) |
| python-a38 | B | Fattura elettronica italiana (FatturaPA) in Python | Apache-2.0 | [Truelite/python-a38](https://github.com/Truelite/python-a38), PyPI `a38` |
| CUAD | B | 510 contratti con clausole annotate (41 categorie) | CC BY 4.0 | [HF theatticusproject/cuad](https://huggingface.co/datasets/theatticusproject/cuad) |
| threeway | B | Baseline deterministica di riconciliazione PO ↔ ricevimento ↔ fattura | MIT | [Bhavya-Dhoot/threeway](https://github.com/Bhavya-Dhoot/threeway), PyPI `threeway` |
| GrainSet | B (stretch) | 350K immagini di chicchi (di cui 31K riso) con difetti annotati | ⚠️ conflitto: CC BY-NC-SA 4.0 (sito) vs CC BY 4.0 (figshare) | [grainnet.github.io/GrainSet](https://grainnet.github.io/GrainSet.html) |
| Bottle_defect | C | Immagini di bottiglie con etichette storte, grinzose, con bolle | CC BY 4.0 (da snippet ⚠️) | [Roboflow detect-wownu/bottle_defect](https://universe.roboflow.com/detect-wownu/bottle_defect) |
| CosIng | C | Banca dati UE degli ingredienti cosmetici (nomi INCI ufficiali) | Riuso dati Commissione UE ⚠️ | [ec.europa.eu/growth/tools-databases/cosing](https://ec.europa.eu/growth/tools-databases/cosing/) |
| LeRobot | C, 05 | Libreria HF per robot learning: dataset con video, policy (ACT, SmolVLA…) | Apache-2.0 (codice) | [huggingface/lerobot](https://github.com/huggingface/lerobot) |
| unitree_sdk2_python | D | SDK ufficiale Unitree (DDS su Ethernet) | BSD-3-Clause | [unitreerobotics/unitree_sdk2_python](https://github.com/unitreerobotics/unitree_sdk2_python) |
| go2_ros2_sdk | D | SDK ROS2 non ufficiale per Go2 (WebRTC/CycloneDDS) | BSD-2-Clause | [abizovnuralem/go2_ros2_sdk](https://github.com/abizovnuralem/go2_ros2_sdk) |
| Frigate | D | NVR con object detection locale, eventi via MQTT e HTTP API | MIT | [blakeblackshear/frigate](https://github.com/blakeblackshear/frigate) (v0.18.2) |
| voice-agent-phone | D | Esempio xAI: agente vocale al telefono con Twilio (Node/TS) | "Beta Testing License" xAI (MIT-like) | [xai-cookbook/examples/voice-agent-phone](https://github.com/xai-org/xai-cookbook/tree/main/examples/voice-agent-phone) |
| pyalex / OpenAlex | 01 | Client Python per OpenAlex (paper, autori, citazioni) | MIT (libreria), CC0 (dati) | [J535D165/pyalex](https://github.com/J535D165/pyalex) |
| BERTopic | 01 | Topic modeling con embedding, anche nel tempo | MIT | [MaartenGr/BERTopic](https://github.com/MaartenGr/BERTopic) |
| tau-bench / tau2-bench | 02 | Task per agenti con tool e utente simulato | MIT | [sierra-research/tau2-bench](https://github.com/sierra-research/tau2-bench), [tau-bench](https://github.com/sierra-research/tau-bench) |
| MAST / MAST-Data | 03 | Tassonomia di 14 failure mode + 1.642 trace annotate | CC BY 4.0 (dati); ⚠️ repo senza licenza | [MAST](https://github.com/multi-agent-systems-failure-taxonomy/MAST), [HF mcemri/MAST-Data](https://huggingface.co/datasets/mcemri/MAST-Data) |
| Who&When | 03 | 184 fallimenti multi-agente con agente e step colpevole | ⚠️ dataset senza licenza dichiarata; repo codice MIT | [HF Kevin355/Who_and_When](https://huggingface.co/datasets/Kevin355/Who_and_When) |
| xai-sdk-python | 04 (e tutte) | SDK Python ufficiale (gRPC) | Apache-2.0 | [xai-org/xai-sdk-python](https://github.com/xai-org/xai-sdk-python), PyPI `xai-sdk` 1.21.0 |
| voice-agent-web | 04 | Esempio xAI: agente vocale nel browser (React + backend Python/Node) | "Beta Testing License" xAI | [xai-cookbook/examples/voice-agent-web](https://github.com/xai-org/xai-cookbook/tree/main/examples/voice-agent-web) |
| eLabFTW | 06 | Quaderno di laboratorio open source con inventario, prenotazioni e API | AGPL-3.0 | [elabftw/elabftw](https://github.com/elabftw/elabftw) (5.6.15) |

**Versione di Python consigliata: 3.12.** `ur_rtde` ha wheel solo fino a 3.12, `lerobot` 0.6.1 e `tau2-bench` richiedono ≥ 3.12 (tau2 < 3.14), `a38` ≥ 3.11, `xai-sdk` e `bertopic` ≥ 3.10.

**Trappole di nome su PyPI:** `frigate` su PyPI **non** è Frigate NVR (si usa Docker); `tau2` su PyPI è un altro progetto (chilton-group): tau2-bench si installa dal repo; `python-a38` non esiste su PyPI, il pacchetto è `a38`.

---

## Traccia A · CTRL+F: SEA

### YOLO-World (e l'alternativa con Grok vision)

- **Cos'è:** detector "open-vocabulary" (CVPR 2024): gli dai una lista di classi in testo libero ("red mug", "scissors") e trova i box in tempo reale, senza riaddestrare. Esiste anche "YOLO-World-Image" con prompt da immagine (preview, HF Space) ⚠️ per il modo "trova questa foto".
- **Licenza:** il repo ufficiale è **GPL-3.0**. Il modo più rapido per usarlo è il pacchetto **Ultralytics** (`ultralytics` 8.4.x), che è **AGPL-3.0**: va bene per l'hackathon (repo pubblico), da tenere presente per un prodotto.
- **5 minuti:**
  ```python
  # pip install ultralytics        (scarica i pesi al primo uso)
  from ultralytics import YOLO
  model = YOLO("yolov8s-worldv2.pt")          # anche -world.pt, m/l/x; solo i v2 si esportano
  model.set_classes(["red mug", "scissors", "toy car"])
  res = model.predict("frame.jpg", conf=0.15)[0]
  for b in res.boxes:
      print(res.names[int(b.cls)], float(b.conf), b.xyxy[0].tolist())   # pixel x1,y1,x2,y2
  ```
- **Alternativa con Grok vision** (nessun modello locale, gestisce descrizioni complesse e "cosa è fuori posto"): mandare il frame a `grok-4.7` con `input_image` e chiedere un JSON strutturato ([../grok-api/vision.md](../grok-api/vision.md), [../grok-api/tools-and-structured-output.md](../grok-api/tools-and-structured-output.md)).
  ```python
  schema = {"type": "object", "additionalProperties": False, "required": ["found", "label", "box", "why"],
            "properties": {"found": {"type": "boolean"}, "label": {"type": "string"},
                           "box": {"type": "array", "items": {"type": "number"}, "description": "x1,y1,x2,y2 normalised 0-1"},
                           "why": {"type": "string"}}}
  resp = client.responses.create(model="grok-4.7", input=[{"role": "user", "content": [
      {"type": "input_image", "image_url": f"data:image/jpeg;base64,{b64}", "detail": "high"},
      {"type": "input_text", "text": "Find: 'the thing you use to cut paper'. Return its box."}]}],
      text={"format": {"type": "json_schema", "name": "find", "schema": schema, "strict": True}})
  ```
  ⚠️ La precisione dei box restituiti da Grok **non è documentata né misurata**: la combinazione più robusta è **YOLO-World (o OWLv2) per i box candidati + Grok per scegliere/spiegare** (gli si passano i crop numerati). Alternative open-vocabulary con licenza Apache-2.0: OWLv2 (`google/owlv2-base-patch16-ensemble`) e Grounding DINO (`IDEA-Research/grounding-dino-tiny`) via `transformers`.
- **Per la traccia:** "Find this" (box + il braccio indica, vedi la calibrazione camera → tavolo in [robot-arm.md §3.7](../hardware/robot-arm.md#37-utensile-stampato-e-vassoi)); "What changed" = detection su scena di riferimento e scena nuova + confronto dei box (IoU) + Grok che spiega. Metriche della giuria: trovati su 10, tempo medio, falsi allarmi.

---

## Traccia B · Best Rice Company

### EdiFabric EDIFACT examples (ORDERS, DESADV, INVOIC)

- **Cos'è:** il repo citato `EdiFabric/EDIFACT-Examples` oggi fa **redirect a `EdiFabric/EDIFACT.NET`**: esempi C# della libreria commerciale EdiFabric (.NET) più una cartella `Files/` di interchange di esempio. Quelli che ci servono:
  - `Files/EDIFACT/PurchaseOrder.txt` → `ORDERS:D:96A:UN` (e varianti: `PurchaseOrders.txt`, `PurchaseOrderInvalid.txt`, `PurchaseOrderMultiLine.txt`)
  - `Files/EANCOM/DespatchAdvice.txt` → `DESADV:D:96A:UN:EAN007`
  - `Files/EDIFACT/Invoice.txt` → `INVOIC:D:96A:UN`; `Files/EANCOM/Invoice.txt` → `INVOIC:D:01B:UN:EAN011`
  - anche `PurchaseOrderResponse.txt` (ORDRSP) e `CONTRL.txt`
- **Licenza:** ⚠️ nessun file LICENSE nel repo; la libreria EdiFabric è commerciale (serve una serial key, il README ne fornisce una di prova a quota limitata). **Non serve la libreria**: usiamo solo i file di esempio come formato di riferimento e generiamo i nostri con Grok.
- **5 minuti (Python, senza .NET):** `pydifact` (MIT, 0.2.3, Python ≥ 3.10).
  ```python
  # pip install pydifact ; curl -LO https://raw.githubusercontent.com/EdiFabric/EDIFACT.NET/master/Files/EDIFACT/PurchaseOrder.txt
  from pydifact.segmentcollection import Interchange
  ic = Interchange.from_file("PurchaseOrder.txt")
  for msg in ic.get_messages():
      for seg in msg.segments:
          print(seg.tag, seg.elements)        # es. LIN, QTY, PRI, NAD, DTM
  ```
- **Per la traccia:** input "ordine della GDO" realistico (EANCOM è lo standard della grande distribuzione); un agente Grok legge ORDERS, il sistema genera DESADV e INVOIC sintetici, poi confronto ordine ↔ consegna ↔ fattura.

### python-a38 (fattura elettronica italiana)

- **Cos'è:** libreria Truelite per generare, validare, convertire (XML ↔ JSON ↔ Python) e renderizzare (HTML/PDF via XSLT) la FatturaPA. Implementa "solo parte della specifica" ma fa round-trip degli esempi ufficiali di fatturapa.gov.it.
- **Licenza:** Apache-2.0. PyPI: **`a38`** 0.1.8, Python ≥ 3.11. Ultimo push del repo: gennaio 2024.
- **5 minuti:**
  ```bash
  pip install a38
  a38tool json fattura.xml        # XML FatturaPA -> JSON (comodo da dare a Grok)
  a38tool validate fattura.xml    # validazione
  ```
  In Python si costruisce con le classi `a38.FatturaPrivati12`, `a38.CedentePrestatore`, `a38.CessionarioCommittente`… (esempio completo nel README) e si valida con `a38.validation.Validation`.
- **Per la traccia:** la fattura generata a fine processo è una FatturaPA vera (sintetica) e validata, non un PDF qualsiasi. Esempi XML ufficiali: https://www.fatturapa.gov.it/it/lafatturapa/esempi/ ⚠️ link dal README, non aperto.

### CUAD (Contract Understanding Atticus Dataset)

- **Cos'è:** 510 contratti commerciali (EDGAR) con oltre 13.000 annotazioni su 41 tipi di clausola (es. "Cap on Liability", "Termination for Convenience", "Most Favored Nation") ⚠️ conteggi dal paper, non ricontati. NeurIPS 2021.
- **Licenza:** CC BY 4.0 (tag HF).
- **5 minuti:** il dataset HF `theatticusproject/cuad` contiene `CUAD_v1/CUAD_v1.json` (formato SQuAD) e i PDF; `theatticusproject/cuad-qa` usa uno script di caricamento (non supportato dalle versioni recenti di `datasets` ⚠️): meglio scaricare il JSON.
  ```python
  # pip install huggingface_hub
  import json
  from huggingface_hub import hf_hub_download
  p = hf_hub_download("theatticusproject/cuad", "CUAD_v1/CUAD_v1.json", repo_type="dataset")
  data = json.load(open(p))["data"]                       # SQuAD: title -> paragraphs -> qas -> answers
  print(len(data), data[0]["title"], data[0]["paragraphs"][0]["qas"][0]["question"][:120])
  ```
- **Per la traccia:** clausole di contratto reali per far citare a Grok "la clausola X del contratto quadro" quando propone come chiudere una contestazione (penali, termini di consegna, tolleranze).

### threeway (baseline di riconciliazione)

- **Cos'è:** CLI e libreria Python **senza dipendenze** (solo stdlib, `Decimal`) che riconcilia ordine (PO), ricevimento merce (GRN) e fattura riga per riga, con chiave **PO + codice articolo**, e assegna uno stato (`not_started`, `matched`, `check`, `exception`) e **un motivo**: fatturato ma non ricevuto; fatturato più del ricevuto; ricevuto più dell'ordinato; consegna parziale; prezzo diverso dal PO; scarto di valore a quantità uguali; righe orfane. Gestisce tolleranze, unità di misura (`--uom-map`) e cut-off di data.
- **Licenza:** MIT. PyPI `threeway` 1.1.0, Python ≥ 3.9. ⚠️ Repo giovane (creato a settembre 2026, 0 stelle).
- **5 minuti:**
  ```bash
  pip install threeway
  git clone --depth 1 https://github.com/Bhavya-Dhoot/threeway && cd threeway/examples
  threeway --po purchase_orders.csv --grn goods_received.csv --invoice invoices.csv --only-exceptions
  threeway --po purchase_orders.csv --grn goods_received.csv --invoice invoices.csv --format json > baseline.json
  # exit code: 0 tutto riconciliato, 1 eccezioni, 2 errore di input
  ```
- **Per la traccia:** è **la baseline deterministica** da battere ("orders reconciled correctly on a test set, better than the deterministic baseline"). Strategia: stesso test set, threeway vs agente Grok; Grok deve aggiungere valore dove threeway si ferma (unità diverse non mappate, codici articolo scritti male, email di contestazione) e citare il documento.

### GrainSet (stretch: qualità visiva del riso)

- **Cos'è:** "An annotated grain kernel image database for visual quality inspection" (Scientific Data 2023): oltre 350K immagini di singoli chicchi (frumento 200K, mais 19K, sorgo 102K, **riso 31K**) con morfologia, peso e categorie di danno annotate da ispettori. Download su figshare: `rice.zip` 2,6 GB, `GrainSet-tiny.zip` 0,7 GB (campione del 2%).
- **Licenza: da verificare, come dice la traccia.** Il sito del progetto dice **CC BY-NC-SA 4.0, "must not be used for commercial purposes"**; i record figshare (rice, tiny) riportano **CC BY 4.0**. Per l'hackathon (non commerciale) va bene in entrambi i casi; citarlo e dichiarare il conflitto nel README.
- **5 minuti:** scaricare `GrainSet-tiny` (https://doi.org/10.6084/m9.figshare.22989029.v1), prendere 20–50 immagini di riso sane e difettose, chiedere a Grok vision una classificazione con spiegazione e confrontarla con le etichette (baseline: classificatore del paper ⚠️).
- **Per la traccia:** stretch goal "visual quality control of the rice grain".

---

## Traccia C · Labelling from the Model Pack

### Bottle_defect (Roboflow Universe)

- **Cos'è:** dataset di object detection del workspace `detect-wownu` con 10 classi, tra cui **`label_bubble`, `label_skew`, `label_wrinkling`** (etichetta con bolle, storta, grinzosa) e difetti di tappo e marcatura (`cap_deform`, `cap_worn`, `marking_abnormal`, …). Piccolo e poco usato ⚠️.
- **Licenza:** CC BY 4.0 (dichiarata dalla traccia e dallo snippet della pagina; ⚠️ la pagina non si è aperta dal nostro ambiente).
- **5 minuti:** dalla pagina del progetto → Dataset → Download (formati YOLO/COCO), oppure con il pacchetto `roboflow` e una API key gratuita ⚠️:
  ```python
  # pip install roboflow
  from roboflow import Roboflow
  rf = Roboflow(api_key="...")
  ds = rf.workspace("detect-wownu").project("bottle_defect").version(1).download("yolov8")   # numero di versione ⚠️
  ```
- **Per la traccia:** esempi negativi per tarare il giudizio di conformità di Grok (storta / grinzosa / bolle) prima di avere le confezioni vere; set di test per misurare "il più grave errore è accettare un pack sbagliato" (falsi accettati).

### CosIng (INCI ufficiali UE)

- **Cos'è:** la banca dati della Commissione europea sugli ingredienti cosmetici: nome INCI, CAS/EC, funzioni, restrizioni (allegati del Regolamento 1223/2009). Oltre 15.000 ingredienti, aperta al pubblico.
- **Licenza:** ⚠️ non indicata esplicitamente; si applica la politica di riuso dei documenti della Commissione (in genere riuso consentito con citazione della fonte).
- **5 minuti:** cercare sul sito ufficiale e usare l'export dei risultati (PDF / XLS / CSV, secondo la guida utente ⚠️ non provato). Non abbiamo trovato un dump completo ufficiale su data.europa.eu; esistono copie di terzi (Zenodo, API non ufficiali) ⚠️ da non usare come fonte di verità.
  ```python
  # once you have an export cosing.csv: build a lookup to validate the INCI list read by Grok from the back label
  import csv, difflib
  inci = {r["INCI name"].upper() for r in csv.DictReader(open("cosing.csv", encoding="utf-8"))}   # nome colonna ⚠️
  def check(name):
      n = name.strip().upper()
      return n in inci, difflib.get_close_matches(n, inci, n=3, cutoff=0.85)
  ```
- **Per la traccia:** controllo deterministico "l'INCI sull'etichetta è un nome ufficiale?" accanto al giudizio di Grok ("a wrong INCI is a compliance problem").

### LeRobot

- **Cos'è:** la libreria di Hugging Face per robot learning: formato **LeRobotDataset** (Parquet + MP4) sul Hub, policy in PyTorch (ACT, Diffusion, SmolVLA, Pi0…), CLI per teleoperare, registrare, addestrare, valutare e fare rollout. Hardware nativo: SO-100/SO-101, Koch, LeKiwi…; plugin community per UR5e, xArm, Franka ⚠️ non provati.
- **Licenza:** Apache-2.0 (codice); ogni dataset ha la sua (es. `lerobot/svla_so101_pickplace` Apache-2.0, `lerobot/pusht` e `lerobot/aloha_static_cups_open` MIT).
- **5 minuti:**
  ```python
  # pip install 'lerobot[dataset]'      (0.6.1, Python >= 3.12)
  from lerobot.datasets.lerobot_dataset import LeRobotDataset
  ds = LeRobotDataset("lerobot/svla_so101_pickplace")
  print(ds.num_episodes, ds.fps, ds.meta.camera_keys)     # attributi ⚠️ da verificare sulla versione installata
  frame = ds[0]                                            # dict: observation.images.*, observation.state, action
  ```
  ```bash
  lerobot-train --policy.type=act --dataset.repo_id=lerobot/svla_so101_pickplace --policy.push_to_hub=false   # serve GPU
  ```
- **Per la traccia C:** stretch "learning the cycle from a video" (ma con 36 ore e un UR, addestrare una policy è fuori portata realistica: meglio usare i video come riferimento per Grok). **Per la traccia 05:** video di dimostrazioni da cui generare tutorial prima di avere i video veri dei bracci. Dettagli bracci: [../hardware/robot-arm.md §4.5](../hardware/robot-arm.md#45-so-100--so-101-con-lerobot).

---

## Traccia D · Robot Dog Patrol

### unitree_sdk2_python e go2_ros2_sdk

Già documentati in [../hardware/robot-dog.md](../hardware/robot-dog.md): `unitree_sdk2_python` (BSD-3-Clause, DDS su Ethernet, **solo Go2 EDU**) in §1.3; `go2_ros2_sdk` (BSD-2-Clause, ROS2, Go2 Air/Pro/EDU via WebRTC o CycloneDDS) in §1.4; la strada consigliata per qualunque Go2 resta WebRTC (`unitree_webrtc_connect`, §1.2). Vale solo se il cane è un Unitree: va confermato al kick-off.

### Frigate (eventi camera)

- **Cos'è:** NVR open source con object detection in tempo reale su stream RTSP/HTTP; zone, tracked objects, snapshot, review; integrazione GenAI (descrizioni con un provider OpenAI-compatibile ⚠️ formato config cambiato tra versioni).
- **Licenza:** MIT. Ultima release **v0.18.2** (15 ott 2026). Gira in Docker (`ghcr.io/blakeblackshear/frigate:stable`); il pacchetto PyPI `frigate` è un'altra cosa.
- **5 minuti** (smartphone come camera: un'app "IP camera" che espone RTSP ⚠️ URL dipende dall'app):
  ```yaml
  # config/config.yml (minimo, ⚠️ da validare con lo schema della 0.18)
  mqtt: {enabled: true, host: 192.168.1.10}
  cameras:
    phone1:
      ffmpeg:
        inputs: [{path: "rtsp://192.168.1.50:8554/live", roles: [detect]}]
      detect: {width: 1280, height: 720}
      zones:
        restricted: {coordinates: "0.1,0.1,0.5,0.1,0.5,0.9,0.1,0.9"}
  objects: {track: [person, backpack, suitcase]}
  ```
  ```bash
  docker run -d --name frigate --shm-size=256m -v $PWD/config:/config -v $PWD/media:/media/frigate \
    -p 8971:8971 -p 5000:5000 -p 8554:8554 ghcr.io/blakeblackshear/frigate:stable
  docker run -d --name mqtt -p 1883:1883 eclipse-mosquitto   # ⚠️ mosquitto 2.x richiede config per accettare client esterni
  ```
- **Eventi:** topic MQTT **`frigate/events`**, payload `{"type": "new"|"update"|"end", "before": {...}, "after": {...}}` con `id`, `camera`, `label`, `current_zones`, `entered_zones`, `has_snapshot`; topic `frigate/reviews` (severity `detection` → `alert`); snapshot JPEG su `frigate/<camera>/<object>/snapshot`.
  ```python
  # pip install paho-mqtt requests
  import json, requests, paho.mqtt.client as mqtt
  def on_message(client, userdata, msg):
      ev = json.loads(msg.payload); a = ev["after"]
      if ev["type"] == "new" and "restricted" in a["current_zones"]:
          jpg = requests.get(f"http://localhost:5000/api/events/{a['id']}/snapshot.jpg").content
          handle_anomaly(a["camera"], a["label"], jpg)          # -> Grok vision decides whether to send the dog
  c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2); c.on_message = on_message
  c.connect("localhost", 1883); c.subscribe("frigate/events"); c.loop_forever()
  ```
- **HTTP API:** porta **5000** non autenticata (solo rete interna), **8971** autenticata (JWT, admin creato al primo avvio, password nei log). Endpoint verificati nell'OpenAPI 0.18.2: `GET /api/events`, `GET /api/events/{event_id}/snapshot.jpg`, `GET /api/{camera_name}/latest.{extension}`, `POST /api/events/{camera_name}/{label}/create` (evento manuale: comodo per inscenare anomalie), `GET /api/review`.
- **Senza Frigate** (più semplice in 36 ore): leggere un frame ogni 1–2 s dallo smartphone con OpenCV e mandarlo a Grok vision con `detail: "low"`; Frigate serve se si vuole detection continua, zone e storico.
- **Per la traccia:** evento → missione → verifica → allerta; il log richiesto dalla giuria può partire dagli eventi Frigate (id, timestamp, zona).

### voice-agent-phone (Twilio)

- **Cos'è:** esempio ufficiale nel cookbook xAI, `examples/voice-agent-phone/xai`: server Node.js + TypeScript (Express + WebSocket) che collega **Twilio Media Streams** al Voice Agent xAI, passando l'audio **μ-law senza conversioni**. Endpoint `/twiml` (webhook chiamata in entrata) e `/call-status-update`; **chiamata in uscita** con `npm run outbound` (l'agente parla per primo).
- **Licenza:** "Beta Testing License" di X.AI LLC (testo MIT-like + clausole "beta" e "nessun supporto"); il cookbook avverte che gli esempi non sono production-ready.
- **5 minuti:**
  ```bash
  git clone --depth 1 https://github.com/xai-org/xai-cookbook && cd xai-cookbook/examples/voice-agent-phone/xai
  npm install && cp .env.example .env      # XAI_API_KEY, HOSTNAME=<dominio ngrok>
  ngrok http 3000 &                         # poi: npm run dev
  # outbound: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER, TARGET_PHONE_NUMBER -> npm run outbound
  ```
  Serve un account Twilio con un numero e ngrok. Equivalente Python già nel repo: [../voice/examples/twilio_bridge.py](../voice/examples/twilio_bridge.py); guida completa (anche SIP diretto) in [../voice/telephony-twilio.md](../voice/telephony-twilio.md).
- **Per la traccia:** "an alert goes out to a test number", anche come chiamata vocale. Niente chiamate reali a vigilanza o polizia (fuori scope).

---

## Traccia 01 · Research Radar

### pyalex / OpenAlex

- **Cos'è:** client Python per l'API OpenAlex (works, authors, sources, institutions, topics…), con filtri concatenabili, paginazione, `group_by`, ricostruzione degli abstract in chiaro (`w["abstract"]`) e ricerca semantica `Works().similar()`.
- **Licenza:** MIT (libreria, 0.21), **CC0** (dati OpenAlex).
- **Attenzione (novità):** senza API key si hanno **100 crediti al giorno** (solo test); con una **API key gratuita** 100.000 al giorno; le richieste di lista costano 1 credito, quelle singole 0; massimo 100 richieste/s. **Creare la key stanotte** su openalex.org/settings/api.
- **5 minuti:**
  ```python
  # pip install pyalex
  import os, pyalex
  from pyalex import Works
  pyalex.config.api_key = os.environ["OPENALEX_API_KEY"]
  q = (Works().search("reinforcement learning")
              .filter(from_publication_date="2026-08-05", to_publication_date="2026-11-03"))
  rows = []
  for page in q.paginate(per_page=200, n_max=1000):         # query riproducibile: salvarla nel README
      for w in page:
          rows.append({"id": w["id"], "title": w["title"], "date": w["publication_date"],
                       "abstract": w["abstract"], "cited_by": w["cited_by_count"]})
  ```
- **Per la traccia:** la "reproducible query" da 500–1.000 record. Le altre fonti citate (arXiv, PubMed/Europe PMC) hanno API proprie gratuite ⚠️ non verificate oggi.

### BERTopic

- **Cos'è:** topic modeling con embedding (sentence-transformers) + UMAP + HDBSCAN + c-TF-IDF; supporta **topics over time**, rappresentazioni con LLM, visualizzazioni.
- **Licenza:** MIT. 0.17.4, Python ≥ 3.10.
- **5 minuti:**
  ```python
  # pip install bertopic
  from bertopic import BERTopic
  docs = [r["title"] + ". " + (r["abstract"] or "") for r in rows]
  stamps = [r["date"] for r in rows]
  model = BERTopic(min_topic_size=10)
  topics, _ = model.fit_transform(docs)
  print(model.get_topic_info().head(12))                   # Topic, Count, Name (parole chiave)
  tot = model.topics_over_time(docs, stamps, nr_bins=12)   # per la timeline e il "What changed?"
  ```
  Poi **Grok dà i nomi ai cluster**: per ogni topic gli si passano `model.get_topic(i)` e `model.get_representative_docs(i)` e si chiede un nome breve + una frase con gli id dei paper come fonte. BERTopic ha anche una representation `OpenAI` che potrebbe puntare a `https://api.x.ai/v1` ⚠️ non provato.
- **Per la traccia:** 5–10 cluster con nomi leggibili, timeline, confronto fra due finestre.

---

## Traccia 02 · GitHub Benchmark Arena

### tau-bench / tau2-bench

- **Cos'è:** benchmark di Sierra per agenti che usano tool parlando con un **utente simulato** in domini realistici. `tau-bench` è la v1 (airline, retail); **`tau2-bench`** è quella attiva (aggiornata ieri) con domini `mock`, `airline`, `retail`, `telecom`, `banking_knowledge`, `intake`, modalità testo e **voce full-duplex** (provider realtime OpenAI, Gemini e **xAI**), leaderboard su taubench.com (ci sono già submission Grok).
- **Licenza:** MIT (entrambi).
- **5 minuti:**
  ```bash
  git clone --depth 1 https://github.com/sierra-research/tau2-bench && cd tau2-bench
  uv sync                          # Python >= 3.12, < 3.14 (oppure pip install -e .)
  cp .env.example .env             # LiteLLM: XAI_API_KEY per i modelli xAI
  tau2 run --domain mock --agent-llm xai/grok-4.7 --user-llm xai/grok-4.7 --num-trials 1 --num-tasks 2   # nome LiteLLM ⚠️
  tau2 view                        # risultati in data/simulations/
  ```
- **Per la traccia:** suite di task con utente simulato e successo verificabile, già pronta; "Grok è il modello fisso" → si confrontano gli harness (adapter comune) con agent LLM = Grok. Docker per isolare i repo sotto test (regola della traccia).

---

## Traccia 03 · Agent Failure Lab

### MAST e MAST-Data

- **Cos'è:** "Why Do Multi-Agent LLM Systems Fail?" (Berkeley, arXiv 2503.13657): tassonomia **MAST** di 14 failure mode in 3 gruppi. *Specification*: 1.1 Disobey Task Specification, 1.2 Disobey Role Specification, 1.3 Step Repetition, 1.4 Loss of Conversation History, 1.5 Unaware of Termination Conditions. *Inter-Agent Misalignment*: 2.1 Conversation Reset, 2.2 Fail to Ask for Clarification, 2.3 Task Derailment, 2.4 Information Withholding, 2.5 Ignored Other Agent's Input, 2.6 Reasoning-Action Mismatch. *Task Verification*: 3.1 Premature Termination, 3.2 No or Incomplete Verification, 3.3 Incorrect Verification.
- **Dati:** HF **`mcemri/MAST-Data`** (il README del repo cita ancora il vecchio nome `mcemri/MAD`): `MAD_full_dataset.json` con **1.642 trace** (7 framework: AG2, MetaGPT, ChatDev, Magentic, AppWorld, HyperAgent, OpenManus; 8 benchmark; 5 LLM) annotate in binario sui 14 codici (annotazioni LLM-as-judge), e `MAD_human_labelled_dataset.json` con 19 trace annotate da 3 persone.
- **Licenza:** CC BY 4.0 (dataset); ⚠️ il repo del codice non dichiara licenza.
- **5 minuti:**
  ```python
  import json
  from huggingface_hub import hf_hub_download
  p = hf_hub_download("mcemri/MAST-Data", "MAD_full_dataset.json", repo_type="dataset")
  data = json.load(open(p))
  r = data[0]; print(r["mas_name"], r["llm_name"], r["benchmark_name"], r["mast_annotation"])
  ```
- **Per la traccia:** ground truth per misurare l'accuratezza del "Grok diagnosta"; le categorie della traccia (Plan, Tool use, Context, Reasoning, Execution, Verification) si mappano in parte su MAST (mapping da scrivere e dichiarare).

### Who&When

- **Cos'è:** benchmark di **failure attribution** (ICML 2025, arXiv 2505.00212): 184 task falliti di sistemi multi-agente (generati con CaptainAgent e "hand-crafted" come Magentic-One, su query GAIA e AssistantBench), ciascuno con **agente responsabile**, **step decisivo** e spiegazione.
- **Licenza:** ⚠️ la card HF non dichiara licenza; il repo del codice `mingyin1/Agents_Failure_Attribution` è MIT.
- **5 minuti:**
  ```python
  from datasets import load_dataset          # pip install datasets
  hc = load_dataset("Kevin355/Who_and_When", "Hand-Crafted")["train"]
  ag = load_dataset("Kevin355/Who_and_When", "Algorithm-Generated")["train"]
  print(hc.column_names)                      # nomi dei campi ⚠️ da leggere al primo avvio
  ```
- **Per la traccia:** misura "precisione nel trovare lo step rilevante" (agente + step), esattamente una delle metriche di giudizio.

---

## Traccia 04 · Voice Control

### xai-sdk-python

- **Cos'è:** SDK Python ufficiale (gRPC) per chat, tool calling, structured output, immagini, ecc. `pip install xai-sdk` (1.21.0, Python ≥ 3.10, Apache-2.0).
- **5 minuti:** vedi [../grok-api/sdk-quickstart.md](../grok-api/sdk-quickstart.md) (non duplichiamo qui). Schema base dal README: `from xai_sdk import Client; from xai_sdk.chat import system, user; chat = Client().chat.create(model=..., messages=[system("...")]); chat.append(user("...")); r = chat.sample()`.
- ⚠️ Per **Grok Voice realtime** l'SDK non è necessario: si parla col WebSocket `wss://api.x.ai/v1/realtime` (protocollo compatibile OpenAI Realtime), vedi [../voice/voice-agent-realtime.md](../voice/voice-agent-realtime.md).

### voice-agent-web

- **Cos'è:** esempio ufficiale `examples/voice-agent-web`: client **React + TypeScript** (`client/`, porta 5173) con trascrizione live, console di debug degli eventi e indicatore microfono, e due backend intercambiabili (`xai/backend-python` FastAPI + websockets, `xai/backend-nodejs` Express + ws, porta 8000). Il backend Python crea i **token effimeri** con `POST https://api.x.ai/v1/realtime/client_secrets` (endpoint `/session`). C'è anche una cartella `openai/` per confronto.
- **Licenza:** "Beta Testing License" X.AI (come tutto il cookbook).
- **5 minuti:**
  ```bash
  git clone --depth 1 https://github.com/xai-org/xai-cookbook && cd xai-cookbook/examples/voice-agent-web
  (cd xai/backend-python && ./start.sh)      # XAI_API_KEY nel .env del backend ⚠️ (vedi .env.example)
  (cd client && ./start.sh)                  # poi http://localhost:5173
  ```
- **Per la traccia:** UI pronta per la demo davanti alla giuria; i tool del braccio ([../hardware/robot-arm.md §5](../hardware/robot-arm.md#5-le-skill-come-tool-json-per-grok)) vanno aggiunti nel backend, dove passano gli eventi `response.function_call_arguments.done`. Alternativa senza browser già nel repo: [../voice/examples/voice_agent_local.py](../voice/examples/voice_agent_local.py); versione browser nostra: [../voice/examples/browser/](../voice/examples/browser/).

---

## Traccia 05 · Robot Skill Passport

- **Manuali dei bracci "available online":** se sono UR e-Series, i manuali utente e il manuale URScript sono sul sito Universal Robots (sezione download, ⚠️ può richiedere registrazione myUR). Dettagli e indizi sul modello: [../hardware/robot-arm.md](../hardware/robot-arm.md).
- **Video di dimostrazione per prototipare:** dataset LeRobot (sopra), es. `lerobot/svla_so101_pickplace`; i frame si estraggono dagli MP4 del dataset.
- **Nessun'altra risorsa pubblica citata.**

---

## Traccia 06 · LabOS

### eLabFTW

- **Cos'è:** quaderno elettronico di laboratorio open source con **Resources** (inventario: `/items`, tipi in `/items_types`), **Scheduler** (prenotazioni di una risorsa, con ricorrenze), team, permessi e API REST.
- **Licenza:** AGPL-3.0. Ultima release 5.6.15 (21 ott 2026). Immagine Docker `elabftw/elabimg`; installazione guidata con lo script `elabctl` (https://get.elabftw.net) ⚠️ procedura non provata, richiede MySQL e HTTPS: **più di 5 minuti**.
- **API v2** (OpenAPI in `apidoc/v2/openapi.yaml`; la v3 è "design stage"): base `https://<host>/api/v2/`, header `Authorization: <API key>` (la key si crea in Settings). Prenotazioni:
  ```bash
  # bookings of a resource (the path id is the ITEM id, not the event id)
  curl -H "Authorization: $ELAB_KEY" https://eln.local/api/v2/events/42
  curl -X POST -H "Authorization: $ELAB_KEY" -H "Content-Type: application/json" \
       -d '{"title":"Team aidea - arm 3","start":"2026-11-05T09:00:00+01:00","end":"2026-11-05T09:30:00+01:00"}' \
       https://eln.local/api/v2/events/42
  # all events of the team: GET /api/v2/events ; one booking: GET|PATCH|DELETE /api/v2/event/{id}
  ```
  Client Python: `pip install elabapi-python` (6.0.1, generato da OpenAPI; esempi nella cartella `examples` del repo `elabftw/elabapi-python`).
- **Per la traccia:** base per inventario e calendario. ⚠️ Valutare se in 36 ore conviene montare eLabFTW o scrivere un backend minimo (SQLite + regole) con l'API di eLabFTW come modello: le regole richieste (niente sovrapposizioni, slot da 30 minuti, staff presente) vanno comunque in un validatore nostro, non nel prompt.

---

## Fonti

- Tracce: https://pavia.grokbot.it/tracks ; repo del sito https://github.com/aletheia/grok-bot-hackathon (PR #14: elenco delle risorse mantenute nella traduzione)
- YOLO-World: https://github.com/AILab-CVC/YOLO-World ; Ultralytics YOLO-World: https://docs.ultralytics.com/models/yolo-world/ ; https://github.com/ultralytics/ultralytics ; OWLv2 https://huggingface.co/google/owlv2-base-patch16-ensemble ; Grounding DINO https://github.com/IDEA-Research/GroundingDINO
- EdiFabric: https://github.com/EdiFabric/EDIFACT.NET (redirect da https://github.com/EdiFabric/EDIFACT-Examples) ; pydifact: https://github.com/nerdocs/pydifact
- python-a38: https://github.com/Truelite/python-a38 , https://pypi.org/project/a38/
- CUAD: https://github.com/TheAtticusProject/cuad (redirect a The-Atticus-Project/cuad), https://huggingface.co/datasets/theatticusproject/cuad
- threeway: https://github.com/Bhavya-Dhoot/threeway , https://pypi.org/project/threeway/
- GrainSet: https://grainnet.github.io/GrainSet.html , https://github.com/hellodfan/GrainSet , https://doi.org/10.1038/s41597-023-02660-8 , figshare API https://api.figshare.com/v2/articles/22987292
- Bottle_defect: https://universe.roboflow.com/detect-wownu/bottle_defect (dati da snippet di ricerca)
- CosIng: https://ec.europa.eu/growth/tools-databases/cosing/ ; guida https://ec.europa.eu/growth/tools-databases/cosing/assets/images/CosIng_FO.pdf
- LeRobot: https://github.com/huggingface/lerobot , https://huggingface.co/docs/lerobot/index , https://pypi.org/project/lerobot/
- Unitree: https://github.com/unitreerobotics/unitree_sdk2_python , https://github.com/abizovnuralem/go2_ros2_sdk
- Frigate: https://github.com/blakeblackshear/frigate , https://docs.frigate.video/integrations/mqtt , `docs/docs/configuration/authentication.md` e `docs/static/frigate-api.yaml` (tag v0.18.2)
- xAI cookbook (commit `002788b`, 26 ott 2026): https://github.com/xai-org/xai-cookbook/tree/main/examples/voice-agent-phone , https://github.com/xai-org/xai-cookbook/tree/main/examples/voice-agent-web , licenza https://github.com/xai-org/xai-cookbook/blob/main/LICENSE
- xai-sdk-python: https://github.com/xai-org/xai-sdk-python , https://pypi.org/project/xai-sdk/
- pyalex: https://github.com/J535D165/pyalex ; OpenAlex rate limit: https://docs.openalex.org/how-to-use-the-api/rate-limits-and-authentication
- BERTopic: https://github.com/MaartenGr/BERTopic , https://maartengr.github.io/BERTopic/
- tau-bench: https://github.com/sierra-research/tau-bench ; tau2-bench: https://github.com/sierra-research/tau2-bench , https://taubench.com
- MAST: https://github.com/multi-agent-systems-failure-taxonomy/MAST , https://huggingface.co/datasets/mcemri/MAST-Data , https://arxiv.org/abs/2503.13657
- Who&When: https://huggingface.co/datasets/Kevin355/Who_and_When , https://github.com/mingyin1/Agents_Failure_Attribution , https://arxiv.org/abs/2505.00212
- eLabFTW: https://github.com/elabftw/elabftw (`apidoc/v2/openapi.yaml`), https://doc.elabftw.net/api.html , https://github.com/elabftw/elabapi-python , https://hub.docker.com/r/elabftw/elabimg
