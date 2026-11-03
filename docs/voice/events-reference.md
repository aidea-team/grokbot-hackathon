# Events reference: `wss://api.x.ai/v1/realtime`

> Verificato il: **2026-11-03**. Fonte primaria: schema ufficiale `https://docs.x.ai/voice-realtime.ws.json` + API reference Voice. Esempi JSON presi dallo schema.
> ⚠️ = non verificato / incoerenze tra fonti.

## Connessione

- URL: `wss://api.x.ai/v1/realtime`
- Query: `model` (`grok-voice-latest` | `grok-voice-3.0` | `grok-voice-2.0`, default latest), `reasoning.effort` (`high` | `none`), `call_id` (solo SIP, da webhook `realtime.call.incoming`; ignora `model`), `conversation_id` (resumption).
- Header: `Authorization: Bearer <API key o ephemeral token>` **oppure** `Sec-WebSocket-Protocol: xai-client-secret.<token>` (browser).

## Client → Server (10 eventi)

| Evento | Campi | Note |
|---|---|---|
| `session.update` | `session{...}` | vedi [voice-agent-realtime.md](voice-agent-realtime.md#parametri-di-sessione-sessionupdate). Risposta: `session.updated` |
| `input_audio_buffer.append` | `audio` (base64) | nessun ack dal server. Con `transport: "binary"` mandare frame binari raw. |
| `input_audio_buffer.commit` | — | solo con `turn_detection: null`. Ack `input_audio_buffer.committed` |
| `input_audio_buffer.clear` | — | scarta audio non committato. Ack `input_audio_buffer.cleared` |
| `conversation.item.create` | `item`, `previous_item_id?` | item `message` (role `user`/`assistant`/`system`, content `input_text`/`input_audio`/`text`/`audio`), `function_call` (seed history), `function_call_output`, `force_message` |
| `conversation.item.delete` | `item_id` | ack `conversation.item.deleted` |
| `conversation.item.truncate` | `item_id`, `content_index`, `audio_end_ms` | dopo barge-in: ms realmente riprodotti. Ack `conversation.item.truncated` |
| `response.create` | `response{instructions?, modalities?, metadata?}` | automatico con server_vad; necessario dopo tool output o per far parlare l'agente per primo |
| `response.cancel` | `response_id?` | annulla risposta in corso (manuale; in VAD è automatico) |

Esempi:
```json
{"type": "input_audio_buffer.append", "audio": "<base64 PCM16>"}
{"type": "conversation.item.create", "item": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "Ciao!"}]}}
{"type": "conversation.item.create", "item": {"type": "function_call_output", "call_id": "call_001", "output": "{\"ok\": true}"}}
{"type": "conversation.item.create", "item": {"type": "force_message", "role": "assistant", "interruptible": false, "content": [{"type": "output_text", "text": "Testo fisso."}]}}
{"type": "conversation.item.truncate", "item_id": "msg_004", "content_index": 0, "audio_end_ms": 1500}
{"type": "response.create", "response": {"instructions": "Rispondi solo in italiano per questo turno.", "metadata": {"trigger": "sensore_1"}}}
{"type": "response.cancel"}
```
Unsupported (OpenAI): `conversation.item.retrieve`; `output_audio_buffer.clear` solo WebRTC/SIP.

## Server → Client

### Sessione / conversazione
| Evento | Campi chiave |
|---|---|
| `session.created` | `session{id, object:"realtime.session", model, instructions, voice, turn_detection, tools, replace, reasoning}` |
| `conversation.created` | `conversation{id, object:"realtime.conversation"}` → id per resumption |
| `session.updated` | eco della config (incluso `replace`) |
| `error` | `error{type, code, message, param, event_id}`; type ∈ `invalid_request_error`, `invalid_event`, `internal_error`, `timeout`, `max_duration` |

### Input audio / turni utente
| Evento | Campi chiave |
|---|---|
| `input_audio_buffer.speech_started` | `item_id`, `audio_start_ms` — **trigger barge-in lato client** |
| `input_audio_buffer.speech_stopped` | `item_id`, `audio_end_ms` |
| `input_audio_buffer.committed` | `item_id`, `previous_item_id` |
| `input_audio_buffer.cleared` | — |
| `input_audio_buffer.timeout_triggered` | `item_id`, `audio_start_ms`, `audio_end_ms` (idle_timeout_ms scattato, il server fa check-in) |
| `input_audio_buffer.dtmf_event_received` | `event` (`0-9*#`), `received_at` — **solo SIP** |
| `conversation.item.input_audio_transcription.updated` | `item_id`, `transcript` **cumulativo** (solo con `transcription.model: "grok-transcribe"`) |
| `conversation.item.input_audio_transcription.completed` | `item_id`, `transcript` |

### Conversation items
| Evento | Campi chiave |
|---|---|
| `conversation.item.added` | `item{id, type: message/function_call/function_call_output, status, role, content[]}`, `previous_item_id` |
| `conversation.item.deleted` | `item_id` |
| `conversation.item.truncated` | `item_id`, `content_index`, `audio_end_ms`, `transcript` (estensione xAI) |
| `conversation.item.created` | ⚠️ citato solo per il replay di resumption ("replayed turns arrive as `conversation.item.created`"), non è nello schema |

### Risposte dell'assistente
| Evento | Campi chiave |
|---|---|
| `response.created` | `response{id, status:"in_progress", output:[], metadata}` |
| `response.output_item.added` | `response_id`, `output_index`, `item` (message o function_call con `call_id`, `name`) |
| `response.content_part.added` / `.done` | `item_id`, `content_index`, `part{type: audio/text, transcript}` |
| `response.output_audio.delta` | `response_id`, `item_id`, `output_index`, `content_index`, **`delta` (base64 audio)** |
| `response.output_audio.done` | — |
| `response.output_audio_transcript.delta` | `delta` (testo) |
| `response.output_audio_transcript.done` | `transcript` (testo completo) |
| `response.text.delta` **e** `response.output_text.delta` | modalità testo: gestire entrambi i nomi |
| `response.function_call_arguments.delta` | `call_id`, `delta` (JSON parziale) |
| `response.function_call_arguments.done` | **`call_id`, `name`, `arguments` (stringa JSON)** |
| `response.output_item.done` | `item` completo (per function_call contiene anche `arguments`) |
| `response.done` | `response{id, status: completed/cancelled/incomplete, usage{input_tokens, output_tokens, total_tokens}, metadata}` |

Nota: la doc dice che l'audio può arrivare anche come `response.audio.delta` (nome legacy) quando `output.transport = json`. ⚠️ Gestire entrambi per sicurezza.
Il cookbook phone gestisce anche `response.cancelled` ⚠️ (non nello schema).

### MCP (tool server-side)
`mcp_list_tools.in_progress | completed | failed`, `response.mcp_call_arguments.delta | done`, `response.mcp_call.in_progress | completed | failed`. Solo informativi: l'esecuzione è lato xAI.

## Sequenza tipica (dallo schema)
```
S session.created → S conversation.created → C session.update → S session.updated
→ C conversation.item.create → S conversation.item.added → C response.create
→ S response.created → S response.output_item.added → S response.content_part.added
→ S response.output_audio.delta (xN) / response.output_audio_transcript.delta (xN)
→ S response.output_audio.done → S response.output_audio_transcript.done
→ S response.content_part.done → S response.output_item.done → S response.done
```

## Altri endpoint WebSocket voice
- **TTS streaming** `wss://api.x.ai/v1/tts?language=..&voice=..&codec=..`: client `text.delta`, `text.done`, `text.clear`, `session.update{replace}`; server `audio.delta`, `audio.done{trace_id}`, `audio.clear`, `session.updated`, `error`. Vedi [tts-stt.md](tts-stt.md).
- **STT streaming** `wss://api.x.ai/v1/stt?...`: client frame binari audio, `{"type":"finalize"}`, `{"type":"audio.done"}`; server `transcript.created`, `transcript.partial`, `transcript.done`, `error`.

## Fonti
- https://docs.x.ai/voice-realtime.ws.json
- https://docs.x.ai/tts-streaming.ws.json · https://docs.x.ai/stt-streaming.ws.json
- https://docs.x.ai/developers/rest-api-reference/inference/voice.md
- https://docs.x.ai/developers/model-capabilities/audio/speech-to-speech.md
- https://github.com/xai-org/xai-cookbook/blob/main/examples/voice-agent-phone/xai/src/index.ts
