# Grok Voice: kit per il Grok Hackathon at the Museum (Pavia, 4–5 nov 2026)

> Verificato il: **2026-11-03** su docs.x.ai (pagine `.md`, schema `voice-realtime.ws.json`), cookbook `github.com/xai-org/xai-cookbook` (commit `002788b`, 26 ott 2026), blog x.ai. La doc ufficiale si firma "SpaceXSI"; endpoint su `api.x.ai`.
> ⚠️ = non verificato o fonti in contraddizione. **Nessun test contro l'API reale** (niente key): gli esempi sono stati eseguiti contro un mock locale del protocollo.

## Indice
| File | Contenuto |
|---|---|
| [voice-agent-realtime.md](voice-agent-realtime.md) | Voice Agent API: endpoint, auth/ephemeral token, sessione, audio, VAD, barge-in, voci, lingue, prompting, resumption, compatibilità OpenAI, prezzi/limiti |
| [events-reference.md](events-reference.md) | Elenco completo eventi client/server con payload |
| [tool-calling-in-voice.md](tool-calling-in-voice.md) | Function calling (robot/simulatori), parallel calls, MCP, anti-sovrapposizione audio |
| [tts-stt.md](tts-stt.md) | TTS REST + WebSocket (speech tags, formati), STT REST + streaming (Smart Turn) |
| [custom-voices.md](custom-voices.md) | Voice cloning: requisiti, limiti, **restrizioni** (USA, consenso) |
| [telephony-twilio.md](telephony-twilio.md) | Twilio Media Streams passo passo, SIP diretto, telefono d'epoca senza telefonia |
| [code-samples.md](code-samples.md) | Esempi pronti + stato di verifica |
| [gotchas.md](gotchas.md) | Trappole: eco, barge-in, costi, limiti, Twilio |
| [examples/](examples/) | `voice_agent_local.py`, `twilio_bridge.py`, `browser/`, `tts_stream_play.py` |

## TL;DR
- **Voice Agent** = `wss://api.x.ai/v1/realtime?model=grok-voice-latest` (→ `grok-voice-3.0`), protocollo **compatibile OpenAI Realtime**. `session.update` → `input_audio_buffer.append` (PCM16 24 kHz base64, chunk 100 ms) → ricevi `response.output_audio.delta`. Con `turn_detection: server_vad` il turno e le interruzioni sono automatici.
- **Tool calling** in sessione: `response.function_call_arguments.done` → eseguite → `conversation.item.create {type: function_call_output}` → `response.create`. Anche tool server-side: `web_search`, `x_search`, `file_search`, `mcp`.
- **Italiano supportato** (`it`) in Voice Agent, TTS e STT. Voci built-in (default `eve`; storiche `ara, rex, sal, eve, leo`; lista completa da `GET /v1/tts/voices`).
- **Telefonia**: Twilio Media Streams con μ-law nativo (`audio/pcmu`, zero transcodifica) oppure SIP diretto `sip.voice.x.ai`.
- **Costi**: $0.08/min voice agent (+$0.004 per messaggio di testo), TTS $15/1M caratteri, STT $0.10–0.20/h.
- **Blocchi**: custom voices solo USA + verifica consenso (niente cloni di personaggi da registrazioni); 10 sessioni concorrenti a Tier 0; sessione max 120 min.

## 10 fatti chiave
1. Endpoint realtime `wss://api.x.ai/v1/realtime`; modelli `grok-voice-latest` = `grok-voice-3.0` (2.0 deprecato). Query `?model=`, `?reasoning.effort=high|none`.
2. Auth: server `Authorization: Bearer $XAI_API_KEY`; browser `POST /v1/realtime/client_secrets {"expires_after":{"seconds":N}}` (max 3600) → `value` → subprotocol `xai-client-secret.<value>`. Un token = una sessione.
3. Audio: `audio/pcm` PCM16 LE mono (8k/16k/22.05k/24k/32k/44.1k/48k, default 24k), `audio/pcmu` / `audio/pcma` 8 kHz, `audio/opus` 24 kHz; transport `json` (base64) o `binary`.
4. `turn_detection: {"type":"server_vad"}` (barge-in automatico, evento `input_audio_buffer.speech_started` → svuotare il buffer locale) o `null` (commit manuale). `idle_timeout_ms` per check-in proattivi.
5. Eventi principali: client `session.update`, `input_audio_buffer.append|commit|clear`, `conversation.item.create|delete|truncate`, `response.create|cancel`; server `session.created|updated`, `conversation.created`, `response.output_audio.delta`, `response.output_audio_transcript.delta`, `response.function_call_arguments.done`, `response.done`, `error`.
6. Estensioni xAI: `force_message` (frase fissa via TTS, niente `response.create`), `response.create.response.instructions` (override per un turno), `replace` (pronuncia), `resumption` (replay history 30 min).
7. Lingue S2S: `en, ar-EG/SA/AE, bn, zh, fr, de, hi, id, it, ja, ko, pt-BR/PT, ru, es-MX/ES, tr, vi` + auto-detect; `language_hint`, `keyterms` (100×50 char).
8. TTS: `POST /v1/tts` (`text` ≤ 60k char, `voice_id`, `language` obbligatorio, codec mp3/wav/pcm/mulaw/alaw) e `wss://api.x.ai/v1/tts` (`text.delta`/`text.done`/`text.clear`), speech tags `[laugh]`, `<whisper>`… STT: `POST /v1/stt` e `wss://api.x.ai/v1/stt` (`grok-voice-transcribe-2.0`, 38+ lingue, Smart Turn).
9. Custom voices: `POST /v1/custom-voices` (multipart, ≤120 s, Enterprise), console gratis fino a 30 voci; `voice_id` 8 char usabile in realtime e TTS. **Solo USA (no Illinois)**, verifica passphrase.
10. Limiti/prezzi: $0.08/min (billing = durata sessione con server_vad), max 120 min/sessione, T0 10 sessioni concorrenti, regione `us-east-1`, latenza "under one second".

## Quale strada per le nostre idee
| Idea | Stack consigliato | Note |
|---|---|---|
| Agente vocale che comanda robot/simulatori | `examples/voice_agent_local.py` su laptop accanto all'hardware, tool `function` che chiamano l'SDK del robot | Cuffie o speakerphone con AEC per il barge-in; altrimenti half-duplex |
| Telefono d'epoca con personaggi | Cornetta → scheda audio USB → `voice_agent_local.py`; un set `voice`+`instructions` per personaggio; gancio = apri/chiudi sessione | **Voci clonate di personaggi non realistiche** (consenso + USA): built-in + persona. `force_message` per la battuta d'apertura |
| Agente telefonico (Twilio) per ordini al cane | `examples/twilio_bridge.py` + ngrok + numero USA Twilio | Numero italiano = bundle regolatorio (giorni) |
| Telecronache vocali | (a) Voice Agent con eventi testo + `response.create` (interattivo); (b) LLM testo Grok + `examples/tts_stream_play.py` con speech tags | (b) più espressivo (tag) e controllabile; (a) permette domande del pubblico |

## Primi 15 minuti domattina
1. `export XAI_API_KEY=...` (chiedere al team SpaceXAI se ci sono crediti/tier hackathon e se le custom voices sono abilitate).
2. `curl -s https://api.x.ai/v1/tts/voices -H "Authorization: Bearer $XAI_API_KEY"` → lista voci reale.
3. `python examples/voice_agent_local.py --text` → verifica handshake e tool.
4. `python examples/voice_agent_local.py` con il microfono che useremo in demo; misurare eco e latenza nella sala vera.

## Fonti principali
- https://docs.x.ai/llms.txt (indice) · https://docs.x.ai/llms-full.txt
- https://docs.x.ai/developers/model-capabilities/audio/voice.md
- https://docs.x.ai/developers/model-capabilities/audio/speech-to-speech.md
- https://docs.x.ai/developers/rest-api-reference/inference/voice.md · https://docs.x.ai/voice-realtime.ws.json
- https://docs.x.ai/developers/pricing.md · https://docs.x.ai/developers/rate-limits.md
- https://github.com/xai-org/xai-cookbook
- https://x.ai/news/grok-voice-3 · https://x.ai/news/grok-voice-think-fast-2 · https://x.ai/news/grok-custom-voices
- Docs MCP server (per interrogare la doc da un agente): https://docs.x.ai/api/mcp
