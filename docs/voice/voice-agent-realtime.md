# Grok Voice Agent API (Speech to Speech, realtime)

> Verificato il: **2026-11-03** su docs.x.ai (pagine `.md` ufficiali + schema `voice-realtime.ws.json`) e sul cookbook `xai-org/xai-cookbook` (commit `002788b`, 26 ott 2026).
> Nota: la documentazione ufficiale si firma **"SpaceXSI"** (es. "SpaceXSI Voice APIs"); l'SDK JS si chiama `@xai-official/sdk` con classe `SpaceXAI`. Gli endpoint restano su `api.x.ai`.
> ⚠️ = non verificato o fonti in contraddizione.

## In breve

| Cosa | Valore |
|---|---|
| Endpoint | `wss://api.x.ai/v1/realtime?model=grok-voice-latest` |
| Modelli | `grok-voice-latest` (alias → `grok-voice-3.0`), `grok-voice-3.0` (flagship, ott 2026), `grok-voice-2.0` (deprecato) |
| Protocollo | JSON su WebSocket, **compatibile OpenAI Realtime API** (con poche differenze, vedi sotto) |
| Auth server | header `Authorization: Bearer $XAI_API_KEY` |
| Auth browser/mobile | ephemeral token via `POST /v1/realtime/client_secrets`, passato come subprotocol `xai-client-secret.<token>` |
| Audio default | PCM16 little-endian, mono, **24 kHz**, base64 in JSON |
| Telefonia | `audio/pcmu` (G.711 μ-law 8 kHz) e `audio/pcma` (A-law) nativi |
| Turn detection | `{"type": "server_vad"}` oppure `null` (manuale / push-to-talk) |
| Barge-in | automatico con `server_vad` (evento `input_audio_buffer.speech_started`) |
| Tool | `function` (client-side), `web_search`, `x_search`, `file_search`, `mcp` (server-side) |
| Lingue | 20+ con italiano (`it`) nella lista ufficiale; auto-detect della lingua |
| Prezzo | **$0.08/min** ($4.80/h) + **$0.004 per text input** (`conversation.item.create` non-audio) |
| Durata max sessione | **120 minuti** |
| Concorrenza | Tier 0: 10 sessioni contemporanee (T1 20, T2 50, T3 100, T4 200) |
| Regione | `us-east-1` (da Pavia aggiungete il RTT transatlantico) |
| Latenza | "under one second" (blog Voice 3.0); TTFA 0.70 s misurato per Voice 2.0 (blog); 0.7–1 s nei test del cookbook live-interpreter |

## Modelli

| Model | Note |
|---|---|
| `grok-voice-latest` | Alias, oggi punta a `grok-voice-3.0`. Default se ometti `model`. |
| `grok-voice-3.0` | Flagship, annunciato 14 ott 2026. Stesso endpoint/eventi/prezzo del 2.0. Consigliato pinnarlo in demo. |
| `grok-voice-2.0` | Deprecato. |

- `reasoning.effort`: `"high"` (default) o `"none"`. Settabile in `session.update`, come query param `?reasoning.effort=none` o nel token effimero. Per compiti semplici (traduzione, comandi brevi) `none` riduce i token; il cookbook live-interpreter riporta però latenza simile (0.7–1 s) con reasoning on/off.
- ⚠️ Il cookbook `live-interpreter` usa il model id `grok-voice-think-fast-2.0`, che **non** compare nell'enum della API reference. Usate `grok-voice-latest` / `grok-voice-3.0`.

## Autenticazione

### Server-side (Python, Node, Raspberry Pi accanto al robot)
```python
from websockets.asyncio.client import connect
async with connect("wss://api.x.ai/v1/realtime?model=grok-voice-latest",
                   additional_headers={"Authorization": f"Bearer {XAI_API_KEY}"}) as ws:
    ...
```

### Ephemeral token (browser / mobile)
1. Il **vostro server** chiama `POST https://api.x.ai/v1/realtime/client_secrets` con la API key.
2. Body: `{"expires_after": {"seconds": 300}}` (max 3600, default 600). Opzionale `session: {model, reasoning: {effort}}`.
   - ⚠️ Contraddizione: la guida Ephemeral Tokens dice "Does not support `session`", mentre la API reference e il cookbook live-interpreter lo usano (solo `model` e `reasoning`). Nel dubbio: niente `session`, passate `model` in query string.
3. Risposta: `{"value": "<token>", "expires_at": <unix_s>}`.
4. Browser: `new WebSocket("wss://api.x.ai/v1/realtime?model=grok-voice-latest", ["xai-client-secret." + value])`.
   - In alternativa il token va anche come `Authorization: Bearer <token>` (client non-browser).
   - Il cookbook web usa i subprotocol stile OpenAI `["realtime", "openai-insecure-api-key.<token>", "openai-beta.realtime-v1"]`: funziona per compatibilità, ma la forma documentata è `xai-client-secret.`.
5. **Un token apre una sola sessione**; la sessione continua anche dopo la scadenza del token (cookbook live-interpreter) → TTL corto (60 s) va bene.
6. Ephemeral token **non** supportati per sessioni SIP (`call_id`).

## Ciclo di vita della sessione

```
client                                   server
  | ---- WebSocket upgrade (101) ------->  |
  | <------------------- session.created   |
  | <-------------- conversation.created   |   (conversation.id → per resumption)
  | session.update --------------------->  |
  | <------------------- session.updated   |   ← solo ORA mandare audio (formato applicato)
  | input_audio_buffer.append (x N) ---->  |
  | <---- input_audio_buffer.speech_started|   (server_vad)
  | <---- input_audio_buffer.speech_stopped|
  | <---- input_audio_buffer.committed     |
  | <---- conversation.item.input_audio_transcription.completed
  | <---- response.created                 |
  | <---- response.output_audio.delta (xN) |   + response.output_audio_transcript.delta
  | <---- response.done                    |
```
Pattern del cookbook ufficiale (phone + web): inviare `session.update` alla ricezione di `conversation.created` (o `session.created`), e **non inviare audio finché non arriva `session.updated`**. Con token effimero il primo `session.updated` riporta le impostazioni del token (senza `instructions`): aspettare quello che contiene le vostre instructions (cookbook live-interpreter).

## Parametri di sessione (`session.update`)

| Parametro | Tipo | Note |
|---|---|---|
| `model` | string | anche via query `?model=` |
| `instructions` | string | system prompt (vedi [Prompting](#prompting)) |
| `reasoning.effort` | `"high"` \| `"none"` | default `high` |
| `voice` | string | built-in (`eve` default) o custom `voice_id` (8 char). Case-insensitive. |
| `tools` | array | `function`, `web_search`, `x_search`, `file_search`, `mcp` |
| `turn_detection.type` | `"server_vad"` \| `null` | ⚠️ settarlo sempre esplicitamente: la guida lo descrive come automatico ma il cookbook live-interpreter commenta "Turn detection is off by default" |
| `turn_detection.idle_timeout_ms` | number | se l'utente tace per N ms dopo la risposta, il server fa un check-in proattivo (evento `input_audio_buffer.timeout_triggered`); si ripete ogni N ms |
| `resumption.enabled` | bool | estensione xAI, vedi [Session resumption](#session-resumption) |
| `audio.input.format.type` | `audio/pcm` \| `audio/pcmu` \| `audio/pcma` \| `audio/opus` | |
| `audio.input.format.rate` | 8000, 16000, 22050, 24000, 32000, 44100, 48000 | solo PCM (lo schema JSON elenca anche 11025) |
| `audio.input.transport` | `"json"` \| `"binary"` | binary = frame WS binari raw, niente base64 |
| `audio.input.transcription.language_hint` | BCP-47 | es. `"it"`. Per es/pt serve la variante (`es-ES`, `pt-BR`). Codici sconosciuti ignorati in silenzio. |
| `audio.input.transcription.keyterms` | string[] | max 100 termini × 50 char (nomi propri, "Ctrl+Alt Museum", nomi dei personaggi) |
| `audio.input.transcription.model` | `"grok-transcribe"` | ⚠️ non nella tabella parametri, ma citato in API reference/cookbook: abilita `conversation.item.input_audio_transcription.updated` (trascrizione live cumulativa) |
| `audio.output.format.*` | come input | input e output possono differire |
| `audio.output.transport` | `"json"` \| `"binary"` | cambia al prossimo confine di risposta |
| `audio.output.speed` | 0.7–1.5 | default 1.0 |
| `replace` | object | `{"Ctrl+Alt": "Control Alt"}`: sostituzioni di pronuncia applicate prima del TTS, il transcript resta invariato. Case-insensitive, whole-word, vince il match più lungo. |

## Formati audio

| Format | Encoding | Sample rate |
|---|---|---|
| `audio/pcm` (default) | Linear16 little-endian, mono | configurabile, default 24000 |
| `audio/pcmu` | G.711 μ-law | 8000 |
| `audio/pcma` | G.711 A-law | 8000 |
| `audio/opus` | Opus raw, un pacchetto per payload | 24000 |

- Consigliato: stesso formato in/out (24 kHz PCM) per evitare resampling; chunk da **100 ms** (24 kHz → 2400 campioni = 4800 byte).
- Se la scheda audio non regge 24 kHz, impostate `rate` al valore nativo (48000/44100/16000): l'API accetta il rate scelto, niente resampling client (il cookbook web fa così con il rate nativo del browser).
- Transport `binary`: l'input accetta **entrambi** i canali (JSON e binario) per il formato configurato; l'output arriva **solo** sul transport scelto. Eventi di lifecycle restano JSON.

## Turn detection, VAD e interruzioni (barge-in)

- `server_vad`: il server rileva inizio/fine parlato, committa il buffer e genera la risposta da solo; basta inviare `input_audio_buffer.append`.
- Interruzione: quando l'utente parla sopra l'agente, il server emette `input_audio_buffer.speech_started` e gestisce l'interruzione ("In VAD mode, interruptions are automatic"). **Il client deve svuotare subito il proprio buffer di riproduzione** (il server ha già inviato audio "in anticipo": arriva più veloce del real-time).
  - Browser: fermare le `AudioBufferSourceNode` programmate.
  - Twilio: inviare `{"event": "clear", "streamSid": ...}`.
- Facoltativo: `conversation.item.truncate {item_id, content_index: 0, audio_end_ms}` per allineare il contesto a ciò che l'utente ha effettivamente sentito; il server risponde `conversation.item.truncated` con il `transcript` troncato (estensione xAI).
- `turn_detection: null` (manuale / push-to-talk): append → `input_audio_buffer.commit` → `response.create`; `input_audio_buffer.clear` per scartare; `response.cancel` per interrompere a mano.
- **Billing**: con `server_vad` si paga la **durata della sessione** (silenzi inclusi); in push-to-talk solo l'audio inviato/ricevuto.
- Non ci sono parametri documentati di soglia/silenzio per il VAD realtime (tipo `threshold`, `silence_duration_ms` di OpenAI). ⚠️ Non testato se vengono accettati.

## Voci

Le stesse voci valgono per Speech to Speech e TTS; ogni voce parla tutte le lingue supportate. Default `eve`.

- Voci "storiche" (cookbook phone): `ara`, `rex`, `sal`, `eve`, `leo`.
- Lista reale da `GET /v1/tts/voices` (verificata il 2026-11-05 con la chiave dell'evento, 28 voci, tutte `multilingual`): maschili `altair, atlas, castor, cosmo, helios, helix, kepler, leo, lumen, lux, naksh, orion, perseus, rex, rigel, sal, sirius, zagan, zenith`; femminili `ara, aurora, carina, celeste, eve, iris, liora, luna, ursa`. La risposta dà solo nome e genere: il timbro va sentito (provini TTS in italiano del G1 e del doppiatore in `video/assets/vo/provini/`, non in git).
- Custom voice: `voice: "<voice_id 8 char>"` (vedi [custom-voices.md](custom-voices.md)).
- ⚠️ Non documentato se `voice` si possa cambiare a metà sessione con un nuovo `session.update` (utile per "più personaggi"). Strategia sicura: una sessione per personaggio.

## Lingue

Lista ufficiale S2S: `en, ar-EG, ar-SA, ar-AE, bn, zh, fr, de, hi, id, it, ja, ko, pt-BR, pt-PT, ru, es-MX, es-ES, tr, vi`. **Italiano supportato** (`it`). Il modello rileva la lingua da solo e risponde nella stessa; per bloccarla mettete nel prompt "Respond only in Italian." e `language_hint: "it"`.

## Prompting

Struttura raccomandata (seconda persona, Markdown, `##` in quest'ordine):
```
## Role & Persona
## Objective
## Conversation Flow
## Guardrails & Escalation
## Voice & Communication Style
## CRITICAL INSTRUCTIONS   (opzionale, regole assolute)
```
Regole utili dalla guida ufficiale:
- Il prompt controlla **cosa** dice l'agente, non il suono della voce. Niente istruzioni su timbro/velocità (usate `voice`, `audio.output.speed`).
- "Spoken word only: no markdown, no lists, no emojis"; 1–2 frasi per turno.
- Citare solo tool realmente presenti in `tools`; preambolo prima dei tool per mascherare la latenza ("Ok, ci penso io!").
- Language lock esplicito; regola "Variety" se diventa ripetitivo.
- Il saluto iniziale non va scritto nel Conversation Flow: lo si provoca a parte (es. `response.create` con `response.instructions` "Greet...") o con `force_message`.

## Funzioni extra (estensioni xAI)

- **`force_message`**: fa pronunciare un testo fisso via TTS senza passare dal modello (disclaimer, battute scriptate, IVR). **Non** inviare `response.create` dopo.
  ```json
  {"type": "conversation.item.create", "item": {"type": "force_message", "role": "assistant",
    "interruptible": false, "content": [{"type": "output_text", "text": "Pronto? Qui parla Leonardo."}]}}
  ```
  `interruptible: false` scarta l'audio dell'utente finché la frase non finisce.
- **Per-response instructions**: `{"type": "response.create", "response": {"instructions": "..."}}` sovrascrive il system prompt per una sola risposta (iniettare stato del gioco/simulatore, cambiare tono). `response.metadata` (max 16 coppie) viene rieco su `response.created`/`response.done`.
- **`replace`**: correzioni di pronuncia (anche su TTS, dove accetta IPA).

## Session resumption

1. Inviare `session.update` con `"resumption": {"enabled": true}`; salvare `conversation.created.conversation.id`.
2. Su reconnect: `wss://api.x.ai/v1/realtime?model=...&conversation_id=<id>` e **rimandare** `resumption.enabled: true`.
3. Vengono riprodotti: trascrizioni utente/assistente, tool call e `function_call_output`. History scade dopo **30 min di inattività**. Nessun evento "resumption completed".

## Compatibilità con OpenAI Realtime API

Funziona l'SDK OpenAI cambiando base URL:
```python
from openai import AsyncOpenAI
client = AsyncOpenAI(api_key=os.environ["XAI_API_KEY"], base_url="https://api.x.ai/v1")
async with client.realtime.connect(model="grok-voice-latest") as conn:
    await conn.session.update(session={"voice": "eve", "instructions": "...", "turn_detection": {"type": "server_vad"}})
```
Differenze documentate:
| OpenAI | xAI |
|---|---|
| `conversation.item.input_audio_transcription.delta` | `conversation.item.input_audio_transcription.updated` (transcript **cumulativo**, solo con `transcription.model: "grok-transcribe"`) |
| `conversation.item.retrieve` / `.retrieved` | non supportati |
| `output_audio_buffer.clear/started/stopped/cleared` | solo WebRTC/SIP |
| `conversation.item.done`, `...transcription.failed`, `...transcription.segment`, `rate_limits.updated` | non emessi |
| — | estensioni: `force_message`, `resumption`, `replace`, `transcript` su `conversation.item.truncated`, `input_audio_buffer.timeout_triggered`, `dtmf_event_received` |
| `response.text.delta` | emessi **sia** `response.text.delta` sia `response.output_text.delta`: gestirli entrambi |

Integrazioni pronte: **Pipecat** `GrokRealtimeLLMService` (`pip install "pipecat-ai[grok]"`), **LiveKit Agents** (realtime model `xai/grok-voice-3.0` via LiveKit Inference o plugin SpaceXAI), Voximplant.

## Prezzi e limiti

| Voce | Valore |
|---|---|
| Speech to Speech (grok-voice-3.0) | $0.08/min ($4.80/h) + $0.004 per text input |
| Cosa costa come text input | ogni `conversation.item.create` dal client, **tranne** `function_call_output` e item con audio. `response.create` non si paga. |
| Billing `server_vad` | durata della sessione (anche i silenzi) → chiudete le sessioni inattive |
| `response.done.usage` | token in/out; il cookbook riporta anche `usage.billable_audio_seconds` ⚠️ (non nello schema) |
| Concurrent sessions grok-voice-3.0 | T0 10, T1 20, T2 50, T3 100, T4 200 (tier per spesa cumulativa: T1 da $50) |
| Max session duration | 120 min (errore `max_duration`) |
| Tool server-side | web_search $5/1k call, x_search $5/1k post, file_search $2.50/1k |
| Endpoint USA "data residency" | **non** serve le voice API: usare l'endpoint globale `api.x.ai` |

## Errori
`error.type`: `invalid_request_error`, `invalid_event`, `internal_error`, `timeout` (inattività ⚠️ durata non documentata), `max_duration`. "Most errors are recoverable and the session stays open." Una config tool invalida produce `error` ma la sessione resta con la config precedente.

## Fonti
- https://docs.x.ai/developers/model-capabilities/audio/voice.md
- https://docs.x.ai/developers/model-capabilities/audio/speech-to-speech.md
- https://docs.x.ai/developers/model-capabilities/audio/speech-to-speech/prompting-guide.md
- https://docs.x.ai/developers/model-capabilities/audio/ephemeral-tokens.md
- https://docs.x.ai/developers/rest-api-reference/inference/voice.md
- https://docs.x.ai/voice-realtime.ws.json
- https://docs.x.ai/developers/pricing.md
- https://docs.x.ai/developers/rate-limits.md
- https://docs.x.ai/developers/release-notes.md
- https://docs.x.ai/developers/advanced-api-usage/regions.md
- https://docs.x.ai/llms-full.txt (sezione `/developers/models/speech-to-speech`: max 120 min, billing server_vad)
- https://github.com/xai-org/xai-cookbook/tree/main/examples/live-interpreter
- https://github.com/xai-org/xai-cookbook/tree/main/examples/voice-agent-web
- https://x.ai/news/grok-voice-3 · https://x.ai/news/grok-voice-think-fast-2
- https://docs.pipecat.ai/server/services/s2s/grok · https://docs.livekit.io/agents/integrations/xai/
