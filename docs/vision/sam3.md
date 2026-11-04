# SAM 3 su Roboflow serverless: segmentazione da testo

> **Verificato il:** 2026-11-04 con una chiamata reale (key gratuita Roboflow) su una foto di scrivanie con laptop. I campi della risposta qui sotto sono quelli ricevuti, non quelli delle docs (che non li descrivono).

Meta SAM 3 ospitato da Roboflow: scrivi un concetto in linguaggio naturale ("desk", "chair", "computer") e ottieni **una maschera per ogni istanza** trovata. Niente GPU in locale.

## Chiamata

`POST https://serverless.roboflow.com/sam3/concept_segment`, header `Authorization: Bearer $ROBOFLOW_API_KEY` (la key sta in `.env`, chiave gratuita su app.roboflow.com → Settings → API Keys).

```python
import base64, requests

r = requests.post(
    "https://serverless.roboflow.com/sam3/concept_segment",
    headers={"Authorization": f"Bearer {key}"},
    json={
        "image": {"type": "base64", "value": base64.b64encode(jpeg_bytes).decode()},  # oppure {"type": "url", "value": "https://..."}
        "prompts": [{"type": "text", "text": "desk"}, {"type": "text", "text": "chair"}],  # max 16 per chiamata (dalle docs)
        "output_prob_thresh": 0.5,   # soglia di confidenza: più bassa = più istanze, più falsi positivi
        "format": "polygon",         # "rle" esiste nelle docs, non provato
    },
    timeout=60,
)
r.raise_for_status()
data = r.json()
```

## Cosa torna indietro

```json
{
  "inference_id": null, "frame_id": null,
  "time": 1.13,
  "resolved_model": {"model_id": "sam3/sam3_final", "backend": "torch", "...": "..."},
  "prompt_results": [
    {"echo": {"prompt_index": 0, "type": "text", "text": "desk", "num_boxes": 0},
     "predictions": [
       {"masks": [[[818, 140], [819, 141], "... centinaia di punti ..."]],
        "confidence": 0.914,
        "format": "polygon"}
     ]},
    {"echo": {"prompt_index": 1, "type": "text", "text": "chair", "num_boxes": 0}, "predictions": []}
  ]
}
```

| Campo | Significato |
|---|---|
| `prompt_results[i]` | Una voce per prompt, **nello stesso ordine** della richiesta. `echo.text` ripete il prompt. |
| `predictions` | Una voce per **istanza** trovata. Lista vuota (non un errore) se il concetto non c'è. |
| `predictions[].masks` | **Lista di poligoni** (un'istanza può avere più pezzi staccati). Ogni poligono è una lista di punti `[x, y]` interi, tipicamente centinaia. |
| `predictions[].confidence` | Punteggio 0..1 dell'istanza. |
| `time` | Secondi di inferenza lato server (1,1 s nella prova). Il tempo totale misurato dal client era 3,8 s: il resto è upload e rete. |

**Non ci sono bounding box.** Nessun campo `box` o `x/y/width/height`: la risposta contiene solo i poligoni (`echo.num_boxes` conta i box *esemplare* che mandi tu nel prompt, non quelli trovati). Se servono, si calcolano dai punti:

```python
pts = [p for poly in pred["masks"] for p in poly]
x0, y0, x1, y1 = min(x for x, _ in pts), min(y for _, y in pts), max(x for x, _ in pts), max(y for _, y in pts)
```

Le coordinate sono **in pixel dell'immagine che hai inviato**: se la ridimensioni prima (i nostri script la portano a 1024 px sul lato lungo), riscala per tornare all'originale.

## Risultato sulla foto di prova

3 prompt (`desk`, `chair`, `computer`), 13 istanze in 3,8 s:

| prompt | istanze | area immagine | confidence max |
|---|---|---|---|
| desk | 3 | 35,9 % | 0,80 |
| chair | 0 | 0 % | n/d |
| computer | 10 | 25,9 % | 0,91 |

- Il tavolo è diviso in 3 istanze perché i laptop lo interrompono.
- `computer` prende tutti i laptop, anche lontani o coperti, **e anche il tablet** (0,79). Per escluderlo prova `laptop`.
- `chair` a zero è corretto: nella foto le sedie sono coperte dalle persone sedute.

## Non verificato

- `format: "rle"`, prompt visuali (box esemplare, `"type": "visual"`) e il limite di 16 prompt: dalle docs, mai provati.
- Effetto di `output_prob_thresh` diverso da 0,5.
- Prezzo (circa 0,5 crediti ogni 1.000 immagini) e piano free: dal catalogo "Occhi del cane", da riverificare su roboflow.com/pricing.

## Provarlo

```bash
.venv/bin/python src/vision/sam3_segment.py foto.jpg                      # solo maschere, nessun box
.venv/bin/python src/vision/sam3_segment.py foto.jpg --prompts "desk,laptop,keyboard" --thresh 0.4
.venv/bin/python src/vision/detect_test.py foto.jpg --backends sam3,grok  # confronto con Grok vision
```

Scrivono `logs/vision/<foto>.sam3.jpg` (originale | maschere), la risposta grezza `<foto>.sam3.raw.json` e una riga JSONL per chiamata. Codice: [src/vision/sam3_segment.py](../../src/vision/sam3_segment.py), [src/vision/detect_test.py](../../src/vision/detect_test.py).

## Fonti
- https://docs.roboflow.com/deploy/supported-models/sam3 (endpoint, auth, campi della richiesta)
- Chiamata reale del 2026-11-04 (campi della risposta)
