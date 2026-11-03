# Code samples pronti

> Verificato il: **2026-11-03**.
> **Stato di verifica**: nessuna API key xAI disponibile durante la ricerca, quindi **nessun esempio è stato eseguito contro l'API reale** ⚠️. Ogni esempio è stato scritto seguendo docs.x.ai + cookbook ufficiale ed è stato **eseguito contro un mock locale** del protocollo realtime/TTS (stessi nomi evento e payload dello schema ufficiale) per verificare: handshake, `session.update`, chunk audio da 100 ms, barge-in, parallel tool calls con un solo `response.create`, bridge Twilio (media/clear/mark). Il JS del client browser è solo syntax-checked (`node --check`).
> Primo test da fare domattina con la key vera: `python examples/voice_agent_local.py --text`.

## File in `examples/`

| File | Cosa fa | Test |
|---|---|---|
| [voice_agent_local.py](examples/voice_agent_local.py) | Mic/casse locali (sounddevice) ↔ Voice Agent, tool `move_robot`, barge-in, half-duplex anti-eco, retry/reconnect con resumption, modalità `--text` | mock: OK (testo + audio con sounddevice finto) |
| [twilio_bridge.py](examples/twilio_bridge.py) | FastAPI: `/twiml` + WS `/media-stream`, μ-law passthrough, `clear` su barge-in, `mark` per attendere la riproduzione prima del `response.create` post-tool | mock xAI + Twilio finto: OK |
| [browser/index.html](examples/browser/index.html) + [browser/server.py](examples/browser/server.py) | Browser diretto a xAI con ephemeral token, AudioWorklet 24 kHz, scheduling playback, barge-in + `conversation.item.truncate`, tool che chiama `/robot` sul server | server: OK con mock token; JS: syntax check |
| [tts_stream_play.py](examples/tts_stream_play.py) | Streaming TTS → casse (PCM 24 kHz), multi-utterance, per telecronache | mock: OK |
| [requirements.txt](examples/requirements.txt) | dipendenze | — |

```bash
cd docs/voice/examples
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt          # Linux: sudo apt install libportaudio2
export XAI_API_KEY=xai-...
python voice_agent_local.py --text       # 1) smoke test senza audio
python voice_agent_local.py              # 2) voce, half-duplex (casse aperte)
python voice_agent_local.py --full-duplex  # 3) con cuffie / speakerphone con AEC
python -m sounddevice                    # elenca i device; se 24 kHz non va: --rate 48000
```

## 1. Hello world realtime (20 righe, solo testo in → audio su file)
Utile per verificare key, modello e voce italiana in 10 secondi.
```python
import asyncio, base64, json, os, wave
from websockets.asyncio.client import connect

async def main():
    async with connect("wss://api.x.ai/v1/realtime?model=grok-voice-latest",
                       additional_headers={"Authorization": f"Bearer {os.environ['XAI_API_KEY']}"}) as ws:
        await ws.send(json.dumps({"type": "session.update", "session": {
            "voice": "eve", "instructions": "You speak Italian. Be brief.",
            "turn_detection": {"type": "server_vad"},
            "audio": {"output": {"format": {"type": "audio/pcm", "rate": 24000}}}}}))
        await ws.send(json.dumps({"type": "conversation.item.create", "item": {
            "type": "message", "role": "user", "content": [{"type": "input_text", "text": "Ciao! Chi sei?"}]}}))
        await ws.send(json.dumps({"type": "response.create"}))
        pcm = bytearray()
        async for raw in ws:
            ev = json.loads(raw)
            if ev["type"] == "response.output_audio.delta":
                pcm += base64.b64decode(ev["delta"])
            elif ev["type"] == "response.output_audio_transcript.done":
                print("Grok:", ev.get("transcript"))
            elif ev["type"] == "error":
                print("ERR", ev["error"])
            elif ev["type"] == "response.done":
                break
    with wave.open("hello.wav", "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(bytes(pcm))

asyncio.run(main())
```
(Dalla doc: il quick start manda `session.update` subito dopo l'apertura; il cookbook aspetta `conversation.created`. Entrambi i pattern sono ufficiali.)

## 2. Stessa cosa con l'SDK OpenAI (compatibilità)
```python
import asyncio, os
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key=os.environ["XAI_API_KEY"], base_url="https://api.x.ai/v1")

async def main():
    async with client.realtime.connect(model="grok-voice-latest") as conn:
        await conn.session.update(session={"voice": "eve", "instructions": "Parla italiano.",
                                           "turn_detection": {"type": "server_vad"}})
        await conn.conversation.item.create(item={"type": "message", "role": "user",
                                                   "content": [{"type": "input_text", "text": "Ciao!"}]})
        await conn.response.create()
        async for ev in conn:
            print(ev.type)
            if ev.type == "response.done":
                break

asyncio.run(main())
```
⚠️ Snippet ufficiale (docs "Migrating from OpenAI Realtime") ma l'SDK OpenAI può validare i tipi degli eventi: eventi solo-xAI (es. `input_audio_buffer.timeout_triggered`) potrebbero non essere tipizzati. Per l'hackathon preferire WebSocket raw.

## 3. Client locale mic/casse + tool (estratto del cuore)
File completo: [examples/voice_agent_local.py](examples/voice_agent_local.py). Punti chiave:
```python
# configurazione
{"type": "session.update", "session": {
    "voice": "eve", "instructions": INSTRUCTIONS,
    "turn_detection": {"type": "server_vad"},
    "audio": {"input": {"format": {"type": "audio/pcm", "rate": 24000}, "transcription": {"language_hint": "it"}},
              "output": {"format": {"type": "audio/pcm", "rate": 24000}}},
    "tools": TOOLS, "resumption": {"enabled": True}}}

# microfono: blocchi da 100 ms (2400 campioni @24k) -> base64
sd.RawInputStream(samplerate=24000, channels=1, dtype="int16", blocksize=2400, callback=cb)
ws.send(json.dumps({"type": "input_audio_buffer.append", "audio": base64.b64encode(chunk).decode()}))

# eventi
"response.output_audio.delta"          -> player.feed(base64.b64decode(ev["delta"]))
"input_audio_buffer.speech_started"    -> player.clear()          # barge-in
"response.function_call_arguments.done"-> pending.append(ev)
"response.done"                        -> esegui pending, function_call_output x N, attendi fine playback, 1x response.create
```

## 4. Browser (ephemeral token)
Server che conia il token (estratto di [browser/server.py](examples/browser/server.py)):
```python
req = urllib.request.Request("https://api.x.ai/v1/realtime/client_secrets",
    data=json.dumps({"expires_after": {"seconds": 60}}).encode(),
    headers={"Authorization": f"Bearer {XAI_API_KEY}", "Content-Type": "application/json"}, method="POST")
# -> {"value": "...", "expires_at": ...}
```
Browser:
```js
const { value } = await (await fetch("/session", { method: "POST" })).json();
const ws = new WebSocket("wss://api.x.ai/v1/realtime?model=grok-voice-latest", [`xai-client-secret.${value}`]);
```
Avvio: `cd examples/browser && XAI_API_KEY=... python server.py` → http://localhost:8000 (getUserMedia richiede localhost o https; per un tablet in LAN serve https, es. ngrok).

## 5. Bridge Twilio
Vedi [telephony-twilio.md](telephony-twilio.md) e [examples/twilio_bridge.py](examples/twilio_bridge.py). Nucleo:
```python
# Twilio -> xAI
if msg["event"] == "media" and st["ready"]:
    await xai.send(json.dumps({"type": "input_audio_buffer.append", "audio": msg["media"]["payload"]}))
# xAI -> Twilio
if t == "response.output_audio.delta":
    await tw.send_text(json.dumps({"event": "media", "streamSid": sid, "media": {"payload": ev["delta"]}}))
if t == "input_audio_buffer.speech_started":
    await tw.send_text(json.dumps({"event": "clear", "streamSid": sid}))
# session: "audio": {"input": {"format": {"type": "audio/pcmu"}}, "output": {"format": {"type": "audio/pcmu"}}}
```

## 6. TTS / STT / Custom voice one-liner
```bash
# TTS -> mp3
curl -s -X POST https://api.x.ai/v1/tts -H "Authorization: Bearer $XAI_API_KEY" -H "Content-Type: application/json" \
  -d '{"text":"Signore e signori, [pause] si parte!","voice_id":"rex","language":"it"}' -o tele.mp3
# Lista voci
curl -s https://api.x.ai/v1/tts/voices -H "Authorization: Bearer $XAI_API_KEY"
# STT
curl -s -X POST https://api.x.ai/v1/stt -H "Authorization: Bearer $XAI_API_KEY" -F language=it -F file=@rec.wav
# Ephemeral token
curl -s -X POST https://api.x.ai/v1/realtime/client_secrets -H "Authorization: Bearer $XAI_API_KEY" \
  -H "Content-Type: application/json" -d '{"expires_after":{"seconds":300}}'
# Custom voices del team
curl -s https://api.x.ai/v1/custom-voices -H "Authorization: Bearer $XAI_API_KEY"
```
TTS streaming → casse: [examples/tts_stream_play.py](examples/tts_stream_play.py).

## 7. Esempi ufficiali da clonare
```bash
git clone --depth 1 https://github.com/xai-org/xai-cookbook.git
# examples/voice-agent-phone/xai      Twilio (Node/TS, inbound + outbound)
# examples/voice-agent-web            React + backend Python/Node (token effimeri)
# examples/voice-agent-webrtc         browser WebRTC <-> server Node <-> xAI WS
# examples/live-interpreter           pagina HTML pura + token, retry, half-duplex (ottimo riferimento)
# examples/voice-agent-mobile/swift   iOS tester app
```

## Fonti
- https://docs.x.ai/developers/model-capabilities/audio/speech-to-speech.md
- https://docs.x.ai/developers/model-capabilities/audio/ephemeral-tokens.md
- https://docs.x.ai/developers/model-capabilities/audio/text-to-speech.md
- https://docs.x.ai/developers/model-capabilities/audio/speech-to-text.md
- https://github.com/xai-org/xai-cookbook (examples/voice-agent-*, examples/live-interpreter)
- https://python-sounddevice.readthedocs.io/
- https://websockets.readthedocs.io/ (API `websockets.asyncio.client.connect`, parametro `additional_headers`)
