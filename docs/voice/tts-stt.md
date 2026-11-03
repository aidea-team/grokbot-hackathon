# Text to Speech e Speech to Text (API standalone)

> Verificato il: **2026-11-03** su docs.x.ai. ⚠️ = non verificato.
> Quando usarle invece del Voice Agent: **telecronache** (testo generato da un LLM o da regole → voce), annunci, battute pre-registrate, trascrizione separata con logica vostra (es. comando vocale → parser → robot senza LLM).

---

## Text to Speech

### REST: `POST https://api.x.ai/v1/tts`
```bash
curl -X POST https://api.x.ai/v1/tts \
  -H "Authorization: Bearer $XAI_API_KEY" -H "Content-Type: application/json" \
  -d '{"text": "Benvenuti al Ctrl+Alt Museum! [laugh] Pronti?", "voice_id": "rex", "language": "it",
       "output_format": {"codec": "mp3", "sample_rate": 24000}}' \
  --output out.mp3
```
| Parametro | Note |
|---|---|
| `text` (req) | max **60.000 caratteri**; supporta speech tags |
| `language` (req) | BCP-47 o `auto`. Lista: `auto, en, ar-EG, ar-SA, ar-AE, bn, zh, fr, de, hi, id, it, ja, ko, pt-BR, pt-PT, ru, es-MX, es-ES, tr, vi` (**`it` supportato**) |
| `voice_id` | default `eve`; built-in o custom; case-insensitive |
| `output_format.codec` | `mp3` (default), `wav`, `pcm`, `mulaw`, `alaw` |
| `output_format.sample_rate` | 8000, 16000, 22050, 24000 (default), 44100, 48000 |
| `output_format.bit_rate` | solo mp3: 32000…192000 (default 128000) |
| `speed` | 0.7–1.5 |
| `optimize_streaming_latency` | `0` qualità, `1` primo chunk più piccolo, `2` minimo TTFA (la API reference elenca solo 0/1 ⚠️) |
| `text_normalization` | numeri/abbreviazioni → forma parlata |
| `with_timestamps` | risposta JSON `{audio (base64), content_type, duration, audio_timestamps{graph_chars, graph_times}}` (per lip-sync / sottotitoli); aggiunge latenza |
| `replace` | mappa pronunce, valori anche in IPA (`{"nginx": "/ˈɛndʒɪn ˈɛks/"}`); max 200 entry |

Risposta (senza timestamps): **byte audio raw** (es. `audio/mpeg`). Content-type: mp3 `audio/mpeg`, wav `audio/wav`, pcm `audio/pcm`, mulaw `audio/basic`, alaw `audio/alaw`.
Request timeout: 15 min. Errori: 400, 401, 404 (voice sconosciuta), 429, 500, 503.

### Speech tags (lista dalla API reference)
- Inline: `[pause]`, `[long-pause]`, `[hum-tune]`, `[laugh]`, `[chuckle]`, `[giggle]`, `[cry]`, `[tsk]`, `[tongue-click]`, `[lip-smack]`, `[breath]`, `[inhale]`, `[exhale]`, `[sigh]`
- Wrapping: `<soft>`, `<whisper>`, `<loud>`, `<build-intensity>`, `<decrease-intensity>`, `<higher-pitch>`, `<lower-pitch>`, `<slow>`, `<fast>`, `<sing-song>`, `<singing>`, `<emphasis>`
- Esempio telecronaca: `"<build-intensity>Ed eccolo che parte, il cane robot accelera</build-intensity> [pause] <loud>INCREDIBILE!</loud>"`
- ⚠️ Non documentato se i tag funzionano anche nell'output del Voice Agent realtime (lì il testo lo genera il modello).

### Streaming WebSocket: `wss://api.x.ai/v1/tts`
- Config via query: `language` (req), `voice`, `codec` (default mp3; anche `ulaw`), `sample_rate`, `bit_rate`, `speed`, `optimize_streaming_latency` (0/1/2), `text_normalization`, `with_timestamps`.
- Parametri invalidi → HTTP 400/404 **prima** dell'upgrade.
- Client: `{"type":"text.delta","delta":"..."}` (max 60k char per delta), `{"type":"text.done"}`, `{"type":"text.clear"}` (barge-in, risposta `audio.clear`), `{"type":"session.update","replace":{...}}`.
- Server: `audio.delta` (base64), `audio.done` (`trace_id`), `audio.clear`, `session.updated`, `error`.
- **Multi-utterance**: dopo `audio.done` si può mandare altro testo sulla stessa connessione (evita ~600 ms di handshake per i client lontani).
- Limiti: testo totale illimitato, **50 sessioni concorrenti per team** (pagina TTS; la tabella rate limits dice 100 a T0 ⚠️), session permit TTL 600 s, moderazione asincrona fail-open.
- Per riprodurre direttamente: `codec=pcm&sample_rate=24000` → PCM16 mono da scrivere sulla scheda audio. Esempio testato contro mock: [examples/tts_stream_play.py](examples/tts_stream_play.py).
- Browser: i codec raw (pcm/mulaw/alaw) non sono decodificabili da `<audio>`/`decodeAudioData` → usare mp3/wav, oppure PCM con Web Audio manuale. Mai chiamare TTS dal browser con la API key (non esistono ephemeral token per TTS: proxy dal vostro server).

### Voci
Stessa lista del Voice Agent (`GET /v1/tts/voices`, `GET /v1/tts/voices/{voice_id}`). Vedi [voice-agent-realtime.md#voci](voice-agent-realtime.md#voci).

### Prezzo e rate limit
- **$15.00 / 1M caratteri** (fatturato sul testo inviato, non su quello dopo `replace`).
- Rate: T0 50 RPS, 100 sessioni concorrenti (rate-limits page).
- Una telecronaca di 10 min ≈ 1.500 parole ≈ 9.000 caratteri ≈ $0.14.

### Latenza
⚠️ Nessun numero ufficiale di time-to-first-audio per il TTS. Leve documentate: streaming WS, `optimize_streaming_latency=1|2`, connessione riusata, `with_timestamps=false`.

---

## Speech to Text

### REST: `POST https://api.x.ai/v1/stt` (multipart)
```bash
curl -X POST https://api.x.ai/v1/stt -H "Authorization: Bearer $XAI_API_KEY" \
  -F model=grok-voice-transcribe-2.0 -F language=it -F file=@registrazione.wav
```
- `file` (max 500 MB, **deve essere l'ultimo campo del form**) oppure `url`.
- Container auto-rilevati: wav, mp3, ogg, opus, flac, aac, mp4, m4a, mkv, webm, avi, mov. Raw (`audio_format` + `sample_rate` obbligatori): `pcm`, `mulaw`, `alaw`.
- Opzioni: `language`, `format=true` (ITN numeri/valute; **non disponibile per l'italiano**: lingue `ar, de, en, es, fr, ja, pt, ru, sv, vi, zh`), `multichannel`, `channels`, `diarize`, `keyterm` (ripetibile, max 100), `filler_words`, `vad_threshold` (default 0.5).
- Risposta: `{text, language, duration, words[{text, start, end, confidence, speaker?}], channels?}`.
- Modello: `grok-voice-transcribe-2.0` (default; 1.0 EOL 2 ott 2026). **38+ lingue, italiano incluso** (`it`).

### Streaming WebSocket: `wss://api.x.ai/v1/stt`
```
wss://api.x.ai/v1/stt?model=grok-voice-transcribe-2.0&sample_rate=16000&encoding=pcm&interim_results=true&language=it&smart_turn=0.7&smart_turn_timeout=3000
```
- **Aspettare `transcript.created` prima di inviare audio.**
- Audio: frame **binari** raw (no base64), chunk da ~100 ms (16 kHz PCM16 = 3.200 byte). 16 kHz è il rate nativo del modello.
- `encoding`: `pcm` (default), `mulaw`, `alaw`, `opus` (un pacchetto per frame, mono).
- `endpointing` (default 400 ms di silenzio → `speech_final`), `interim_results` (parziali ogni ~500 ms), `smart_turn` (soglia 0–1, modello ML di fine turno), `smart_turn_timeout` (1–5000 ms), `vad_threshold` (default 0.08), `diarize`, `multichannel`/`channels`, `keyterm`, `filler_words`.
- Client: binari audio, `{"type":"finalize"}` (push-to-talk: chiude l'utterance subito), `{"type":"audio.done"}` (fine; il server chiude dopo `transcript.done`).
- Server: `transcript.created`, `transcript.partial` (`text, words, is_final, speech_final, start, duration, end_of_turn_confidence?`), `transcript.done`, `error` (la maggior parte chiude la connessione).
- Stati: `is_final=false` interim · `is_final=true, speech_final=false` chunk finale · `is_final=true, speech_final=true` fine utterance.

### Prezzo e rate limit
- **$0.10/h REST, $0.20/h streaming**.
- Rate T0: 10 RPS, 100 sessioni concorrenti.

### Esempio Python streaming (dalla doc, adattato a italiano)
```python
import asyncio, json, os
from websockets.asyncio.client import connect

URL = ("wss://api.x.ai/v1/stt?model=grok-voice-transcribe-2.0&sample_rate=16000"
       "&encoding=pcm&interim_results=true&language=it")

async def transcribe(wav_path):
    async with connect(URL, additional_headers={"Authorization": f"Bearer {os.environ['XAI_API_KEY']}"}) as ws:
        assert json.loads(await ws.recv())["type"] == "transcript.created"
        with open(wav_path, "rb") as f:
            f.read(44)                       # salta header WAV (16 kHz mono PCM16)
            while chunk := f.read(3200):     # 100 ms
                await ws.send(chunk)
                await asyncio.sleep(0.1)
        await ws.send(json.dumps({"type": "audio.done"}))
        async for msg in ws:
            ev = json.loads(msg)
            if ev["type"] == "transcript.partial":
                print("FINAL" if ev["is_final"] else "partial", ev["text"])
            elif ev["type"] == "transcript.done":
                print("TOT:", ev["text"]); break

asyncio.run(transcribe("audio.wav"))
```

## Pipeline "a pezzi" vs Voice Agent
| | STT → LLM → TTS (pezzi) | Voice Agent realtime |
|---|---|---|
| Latenza | somma dei tre stadi | < 1 s end-to-end |
| Controllo | totale (regex, LLM testuale a scelta, cache) | prompt + tool |
| Costo | STT $0.20/h + LLM tokens + TTS $15/1M char | $0.08/min (= $4.80/h) |
| Barge-in | da implementare (`finalize`, `text.clear`) | nativo con server_vad |
| Speech tags espressivi | sì (TTS) | ⚠️ non documentato |

## Fonti
- https://docs.x.ai/developers/model-capabilities/audio/text-to-speech.md
- https://docs.x.ai/developers/model-capabilities/audio/speech-to-text.md
- https://docs.x.ai/developers/rest-api-reference/inference/voice.md
- https://docs.x.ai/tts-streaming.ws.json · https://docs.x.ai/stt-streaming.ws.json
- https://docs.x.ai/developers/pricing.md · https://docs.x.ai/developers/rate-limits.md
- https://docs.x.ai/developers/release-notes.md
