# Grok Imagine API (immagini e video)

> Verificato il **2026-11-03** su docs.x.ai (pagine `.md`: Imagine overview, Image Generation/Editing, Video Overview/Generation/Editing/Extension/Reference-to-Video, REST API reference Images e Videos, Models, Pricing, Release notes, migration guide del 2 novembre).
> Endpoint provati con chiave non valida (risposte 400 "Incorrect API key" / 422 schema → path esistenti). SDK ispezionati: `xai-sdk` 1.21.0 (Python), `ai` 7.0.162 + `@ai-sdk/xai` 5.0.38 (JS). **Nessuna generazione reale eseguita** (niente API key disponibile).
> ⚠️ = non verificato.

## TL;DR

- Base URL `https://api.x.ai/v1`, auth `Authorization: Bearer $XAI_API_KEY` (chiavi da https://console.x.ai).
- **Immagini**: `POST /v1/images/generations` e `POST /v1/images/edits` — **sincroni** (risposta con URL temporaneo o base64), opzionale `deferred: true` + polling `GET /v1/images/{request_id}`.
- **Video**: `POST /v1/videos/generations` | `/v1/videos/edits` | `/v1/videos/extensions` — **sempre asincroni**: ritorna `request_id`, poi polling `GET /v1/videos/{request_id}` finché `status == "done"`. "Typically takes up to several minutes".
- Modelli consigliati: **`grok-imagine-image-2.0`** ($0.04/img) e **`grok-imagine-video-1.5`** ($0.08/s) oppure **`grok-imagine-video-1.5-lite`** ($0.02/s, il più economico) per video semplici.
- Video: **1–15 s** (default 8), **480p** (default) / 720p / **1080p** (nativo su 1.5), audio generato di default con **lip-sync**; image-to-video, reference-to-video (fino a 14 immagini + 3 voci preset), primo/ultimo frame e keyframe. **Editing ed extension solo con `grok-imagine-video`** (max 720p).
- URL dei risultati **temporanei**: scaricare subito o usare `storage_options` per un URL pubblico permanente.

## Modelli, prezzi, rate limit

| Model id | Cosa fa | Prezzo | Rate limit | Note |
|---|---|---|---|---|
| `grok-imagine-image-2.0` | text→image, image edit (fino a 5 immagini) | **$0.04 / immagine** | 6 req/s | param `quality` (`low`/`medium`/`auto`), `2k`, ratio `21:9`, `5:2` |
| `grok-imagine-image` | v1.0 text→image/edit | $0.02 / immagine | ⚠️ | non toccato dal retirement |
| `grok-imagine-image-quality` | **ritirato il 2026-11-02** | — | — | ora servito da `grok-imagine-image-2.0` con `quality: "low"` |
| `grok-imagine-video-1.5` | T2V, I2V (1080p nativo), reference-to-video, voci, first/last/keyframe | **$0.080 / s** | 10 req/s | alias `grok-imagine-video-1.5-preview`, `grok-imagine-video-1.5-2026-05-30` |
| `grok-imagine-video-1.5-lite` | T2V, I2V (1080p upscalato da 720p) | **$0.020 / s** | 10 req/s | niente reference/voci/keyframe |
| `grok-imagine-video` | T2V, I2V (max 720p), reference (7 img, 10 s), **edit**, **extension** | $0.050 / s | 10 req/s | unico modello per editing/extension |

- Image edit: *"billed for both the input image and the generated output image"* (⚠️ costo dell'input non quantificato nelle docs).
- `quality: auto` (default) oggi = `low` per generazione e `medium` per edit; *"Images are billed at the quality they are served at"*. ⚠️ La tabella prezzi mostra un solo prezzo flat ($0.04) per 2.0; la pagina Video Overview dice "Per-second prices by resolution are listed on the Models page", ma la pagina Models mostra un prezzo unico per modello.
- Ogni risposta include `usage.cost_in_usd_ticks` (costo esatto della richiesta).
- Violazioni di policy: la generazione viene comunque addebitata; violazioni bloccate prima (Responses API) $0.05.
- Regioni: us-east-1, us-west-2 (+ us-saltlake-2 per video). Batch API supporta immagini/video (prezzo standard, URL validi 1 h).

## Immagini

### Generazione — `POST /v1/images/generations`
| Campo | Valori |
|---|---|
| `model` | `grok-imagine-image-2.0` |
| `prompt` | testo |
| `n` | 1–10 (default 1) — Python xAI SDK: `sample()` per 1, `sample_batch(n=...)` per più |
| `aspect_ratio` | `1:1`, `3:4`, `4:3`, `9:16`, `16:9`, `2:3`, `3:2`, `9:19.5`, `19.5:9`, `9:20`, `20:9`, `1:2`, `2:1`, `21:9`, `5:2`, `auto` (default) |
| `resolution` | `1k` (default), `2k` (l'API reference elenca anche `1.5k` ⚠️) |
| `quality` | `low`, `medium`, `auto` (solo 2.0) |
| `response_format` | `url` (default, temporaneo) o `b64_json` |
| `deferred` | `true` → ritorna `request_id`, poll `GET /v1/images/{id}` (`pending` 202 / `done` 200 / `failed`), risultati tenuti 24 h, solo `url` |
| `storage_options` | `{filename, expires_after (3600–2592000 s), public_url}` → salva su Files API e dà URL pubblico permanente |
| `output.upload_urls` | URL presigned (S3/GCS/Azure) dove fare PUT del risultato |

Risposta: `data[i].url` o `data[i].b64_json`, `mime_type`, `usage`. L'xAI SDK espone anche `respect_moderation` e `model`.

### Editing — `POST /v1/images/edits`
- `image: {url | file_id}` (URL pubblico o **data URI base64**, JPEG/PNG/WebP) oppure `images: [...]` per multi-image (**fino a 5** con 2.0).
- Stessi `aspect_ratio`, `resolution`, `n`, `response_format`, `deferred`.
- ⚠️ **`client.images.edit()` dell'SDK OpenAI NON funziona** (usa multipart; xAI vuole JSON): usare xAI SDK, Vercel AI SDK o HTTP diretto. `client.images.generate()` dell'SDK OpenAI invece funziona (parametri extra via `extra_body`).
- Multi-turn: usare l'output come input del passo successivo.

### Tool `image_generation` dentro la chat
Nella Responses API si può dare a Grok il tool `{"type": "image_generation"}`: il modello decide quando generare/editare, scrive il prompt e restituisce l'immagine base64 in un item `image_generation_call` (campo `result`). Utile per agenti; per controllo diretto su ratio/risoluzione usare gli endpoint sopra. Non esposto dal Vercel AI SDK.

### Tempi
⚠️ Le docs non danno tempi per le immagini: la chiamata è sincrona ("Image generation normally completes within the request"). Per parallelizzare prompt diversi: `AsyncClient` + `asyncio.gather`.

## Video

### Endpoint
| Azione | Endpoint | Modelli |
|---|---|---|
| Text-to-video / image-to-video / reference-to-video / first-last-keyframe | `POST /v1/videos/generations` | 1.5, 1.5-lite (no reference), classic |
| Edit video | `POST /v1/videos/edits` | `grok-imagine-video` |
| Extend video | `POST /v1/videos/extensions` | `grok-imagine-video` |
| Stato/risultato | `GET /v1/videos/{request_id}` | — |

### Campi principali (`/videos/generations`)
| Campo | Note |
|---|---|
| `prompt` | obbligatorio per T2V e R2V; opzionale per I2V |
| `image` | `{url | file_id}` → primo frame (I2V). L'output **mantiene l'aspect ratio dell'immagine** (`aspect_ratio` ignorato) |
| `duration` | 1–15 s, default **8** (accetta anche `seconds`) |
| `aspect_ratio` | `1:1`, `16:9` (default), `9:16`, `4:3`, `3:4`, `3:2`, `2:3`, `21:9`, `5:2` |
| `resolution` | `480p` (default, più veloce), `720p`, `1080p` (1.5 nativo; lite upscalato; reference max 720p; classic max 720p) |
| `generate_audio` | default true; `false` = video muto |
| `reference_images` | fino a **14** (1.5) / 7 (classic); nel prompt si citano come `<IMAGE_0>`, `<IMAGE_1>`... |
| `reference_audios` | fino a **3** voci preset (`{"voice_id": "eve"}`, stessi id del TTS), citate come `<AUDIO_0>`... Solo 1.5. Voci custom solo per partner |
| `last_frame` | pin dell'ultimo frame (1.5). `image` = `last_frame` → loop |
| `keyframes` | fino a 4 `{image, timestamp_s}` strettamente dentro la clip, griglia 1/3 s (1.5) |
| `storage_options`, `output.upload_url` | persistenza / upload diretto su bucket |

### Edit ed extension (`grok-imagine-video`)
| | Edit | Extension |
|---|---|---|
| Input | `video: {url | file_id}` `.mp4` (H.264/H.265/AV1) | idem |
| Lunghezza sorgente | **max 8.7 s** | **2–15 s** |
| `duration` | non supportato (stessa durata) | **2–10 s** (default 6) = solo la parte aggiunta |
| Output | stessa durata/ratio/risoluzione, max **720p** | sorgente + estensione in un unico clip, max 720p |

### Polling e stati
- Stati: `pending` (con `progress` 0–99), `done` (`video.url`, `video.duration`, `respect_moderation`, `model`, `usage`), `failed` (`error.code`: `invalid_argument`, `permission_denied`, `failed_precondition`, `service_unavailable`, `internal_error`). Lo snippet bash della overview gestisce anche `expired` ⚠️ (non elencato nella reference).
- xAI SDK Python: `client.video.generate(...)` fa start+poll (default timeout **10 min**, intervallo 1 s; parametri `timeout`, `interval` come `timedelta`); manuale con `start()` / `get()`; extension con `extend()` / `extend_start()`.
- Vercel AI SDK: `experimental_generateVideo` con `providerOptions.xai.pollTimeoutMs` / `pollIntervalMs` (default 5 s); URL in `result.providerMetadata.xai.videoUrl`.
- Alternativa al polling per immagini deferred: webhook di management per eventi `image.generation.completed/failed`, `image.edit.completed/failed`. ⚠️ Eventi webhook per i video non documentati nella pagina letta.

### Tempi di generazione
Docs: *"asynchronous process that typically takes up to several minutes"*; più lungo con prompt complessi, durata maggiore, 1080p, editing. Per demo live: **480p, 5–6 s, modello lite**, e far partire la generazione in background mentre si fa altro. ⚠️ Nessun benchmark ufficiale in secondi.

## Input da file e output persistenti
- Ovunque si può usare `file_id` (Files API) al posto di URL: `image.file_id`, `video.file_id`, `reference_images[].file_id` (xAI SDK: `image_file_id`, `video_file_id`, `reference_image_file_ids`).
- `storage_options.public_url` → link pubblico permanente (utile per postare su X o mostrare in una UI senza scaricare). `data[i].url` resta comunque effimero.

## Content policy
Generazioni soggette a moderazione (`respect_moderation`). Richieste con marchi, personaggi protetti o persone reali spesso vengono bloccate (indicazione esplicita nelle docs di Grok Bot). Media generati "not used for training" (docs Imagine).

## Idee per l'hackathon
- **Camera del robot → image edit**: foto dalla webcam del cane robot / braccio → `images/edits` con data URI → "dipinto", "poster", ecc.
- **Highlight video**: frame del simulatore di volo/guida → image-to-video 5 s 480p lite → post su X.
- **Personaggio parlante**: reference-to-video con `reference_audios` (voce preset) per far "parlare" il robot (vedi cookbook "Photo to Talking Character").

## Fonti

- https://docs.x.ai/developers/model-capabilities/imagine
- https://docs.x.ai/developers/model-capabilities/images/generation
- https://docs.x.ai/developers/model-capabilities/images/editing
- https://docs.x.ai/developers/model-capabilities/video/overview
- https://docs.x.ai/developers/model-capabilities/video/generation
- https://docs.x.ai/developers/model-capabilities/video/image-to-video
- https://docs.x.ai/developers/model-capabilities/video/reference-to-video
- https://docs.x.ai/developers/model-capabilities/video/editing
- https://docs.x.ai/developers/model-capabilities/video/extension
- https://docs.x.ai/developers/model-capabilities/imagine/files/outputs
- https://docs.x.ai/developers/tools/image-generation
- https://docs.x.ai/developers/rest-api-reference/inference/images
- https://docs.x.ai/developers/rest-api-reference/inference/videos
- https://docs.x.ai/developers/models (+ pagine `models/grok-imagine-*`)
- https://docs.x.ai/developers/pricing
- https://docs.x.ai/developers/migration/imagine-image-quality-nov-2
- https://docs.x.ai/developers/release-notes
- https://github.com/xai-org/xai-cookbook (esempi `photo-to-talking-character`, `storyboard-to-film`, `product-video-ad`, `photo-to-time-lapse`)
