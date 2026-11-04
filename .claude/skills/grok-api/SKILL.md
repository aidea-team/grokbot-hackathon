---
name: grok-api
description: Cheat sheet for writing runtime code that calls Grok (xAI/SpaceXSI) in this repo - Responses API, function calling, vision, Grok Voice realtime, TTS/STT, Imagine image/video, Grok Build headless. Use whenever you write, fix or review code that imports xai_sdk / openai with base_url api.x.ai, opens wss://api.x.ai, posts to /v1/images or /v1/videos, or shells out to the grok CLI. Gives verified model ids, endpoints and tool formats, and points to the docs/ file to read before coding.
when_to_use: Trigger on "chiama Grok", "Grok API", "Grok Voice", "realtime", "Imagine", "xai-sdk", "XAI_API_KEY", "grok-4.7", "grok -p", or any new module under src/ that talks to an LLM. Do NOT use the Claude API / Anthropic SDK for runtime code in this repo.
---

# Grok API: regole per il codice runtime di questa repo

Il progetto viene **costruito** con Claude Code ma **gira** su Grok. Nessun modello Claude e nessun SDK `anthropic` nel codice runtime (`src/`, `scripts/`): se ti viene da importarlo, fermati.

Fatti verificati il 2026-11-03 sui docs ufficiali. Prima di scrivere codice **leggi il file indicato** nella tabella in fondo; se hai il server MCP `xai-docs` (vedi `.mcp.json`) usa `search_docs` / `get_doc_page` per controllare la pagina aggiornata invece di andare a memoria: i docs cambiano spesso (es. `grok-imagine-image-quality` ritirato il 2026-11-02).

## Endpoint e auth
- REST: `https://api.x.ai/v1`, header `Authorization: Bearer $XAI_API_KEY`. Chiave solo da env (`.env`, mai nel codice né nei log).
- API raccomandata: **Responses** `POST /v1/responses`. Chat Completions è deprecata (usarla solo se una libreria lo impone). **Mai** l'endpoint Anthropic-compatibile `/v1/messages` (fully deprecated).
- SDK: `xai-sdk` (Python ≥ 3.10, gRPC, timeout solo sul client) oppure `openai` con `base_url="https://api.x.ai/v1"` (passare `api_key` esplicita). JS: `openai` con `baseURL`, o `ai` + `@ai-sdk/xai` (`xai.responses("grok-4.7")`).

## Model id (con il punto, niente `-fast` via API)
| Uso | Model id | Note |
|---|---|---|
| Qualità, vision, pianificazione | `grok-4.7` | 500k ctx, reasoning **non disattivabile**, `reasoning.effort` low/medium/high(default)/xhigh |
| Bassa latenza (robot, dialogo) | `grok-4.3` + `reasoning: {"effort": "none"}` | unico modello con `none` |
| Bassa latenza alternativa | `grok-4.20-0309-non-reasoning` | |
| Codice generato via API | `grok-build-0.1` | 256k ctx |
| Voce realtime | `grok-voice-latest` (= `grok-voice-3.0`) | |
| Immagini | `grok-imagine-image-2.0` | sincrono, $0.04/img |
| Video | `grok-imagine-video-1.5` / `-1.5-lite`; edit/extension solo `grok-imagine-video` | asincrono |

Id vecchi visti online (`grok-3`, `grok-4-fast-*`, `grok-code-fast-1`, `grok-2-vision-*`) sono ritirati e rediretti: non usarli. Al primo avvio con la key: `curl -s https://api.x.ai/v1/models -H "Authorization: Bearer $XAI_API_KEY"`.

## Function calling (Responses API)
- Tool **piatto**: `{"type":"function","name":...,"description":...,"parameters":{"type":"object",...}}`.
- Il modello risponde con item `function_call` (`call_id`, `name`, `arguments` stringa JSON) → tu rimandi `{"type":"function_call_output","call_id":...,"output":"<json string>"}` con `previous_response_id` (o la history completa).
- Chat Completions invece usa la forma annidata `{"type":"function","function":{...}}` e `tool_calls` / `role: "tool"`: non mescolare i due formati.
- Hardware: **sempre** `parallel_tool_calls: false`, limite di passi nel loop, e ogni call passa dal validatore (vedi `docs/hardware/llm-robot-architecture.md`).
- Structured output: `text.format` con `json_schema` (`additionalProperties` false di default). Con `grok-4.7` ripassa invariati gli item di reasoning nei multi-turn stateless.

## Vision
`input_image` con URL o data URL base64 (jpg/png ≤ 20 MiB), `detail: "low"` per frame di camera, `store: false` quando mandi immagini.

## Grok Voice (realtime)
- `wss://api.x.ai/v1/realtime?model=grok-voice-latest`, protocollo compatibile **OpenAI Realtime**.
- `session.update` con `turn_detection: {"type":"server_vad"}` esplicito, audio PCM16 mono 24 kHz base64 (telefonia: `audio/pcmu` 8 kHz), tool in `session.tools` formato piatto (se `session.update` dà `error`, provare l'annidato).
- Tool loop: `response.function_call_arguments.done` → esegui → `conversation.item.create` (`function_call_output`) → **un solo** `response.create` dopo tutti gli output e dopo la fine del playback locale.
- Barge-in: su `input_audio_buffer.speech_started` svuota il buffer di riproduzione.
- Browser: token effimero `POST /v1/realtime/client_secrets`, mai la key nel client.
- Il kill switch vocale ("stop", "fermo") si controlla **in locale** sulla trascrizione, prima e indipendentemente dal modello.

## Imagine
- Immagini: `POST /v1/images/generations` (`model`, `prompt`, `n`, `aspect_ratio`, `resolution`, `quality`, `response_format` url|b64_json). Gli URL sono temporanei: scarica subito.
- Video: `POST /v1/videos/generations` → `request_id` → polling `GET /v1/videos/{request_id}` (`pending` / `done` / `failed`), durata 1–15 s. Mai in un percorso real-time.
- Ogni risposta ha `usage.cost_in_usd_ticks`: loggalo.

## Grok Build (CLI `grok`)
Headless: `grok --no-auto-update -p "<prompt>" --output-format json --cwd <dir>`; per sola lettura `--sandbox read-only --always-approve`. Non dare mai a `grok` accesso in scrittura sulla macchina collegata all'hardware. Dettagli e quando usarlo: `docs/claude-vs-grok/claude-code-workflow.md`.

## Obbligatorio in ogni chiamata runtime
1. Log JSONL di ogni richiesta/risposta (modello, latenza ms, TTFT se streaming, token, costo, tool call, esito) nel logger comune del progetto: la giuria vuole numeri.
2. Timeout corto + fallback nel percorso real-time; i timeout lunghi (≥ 900 s) solo per reasoning `high` fuori dal loop.
3. Gestire 429 (rate limit, non ritentato da `xai-sdk`) e `DEADLINE_EXCEEDED`.
4. Un modo per girare **senza rete** (mock del client o replay da JSONL) per test e demo di backup.

## Dove leggere prima di scrivere codice
| Ti serve | File |
|---|---|
| Model id, prezzi, rate limit | `docs/grok-api/models.md` |
| Responses, streaming, reasoning, cache | `docs/grok-api/responses-and-chat.md` |
| Tool e structured output | `docs/grok-api/tools-and-structured-output.md` |
| Vision | `docs/grok-api/vision.md` |
| web_search / x_search / remote MCP | `docs/grok-api/agentic-server-tools.md` |
| SDK e snippet | `docs/grok-api/sdk-quickstart.md` |
| Trappole e benchmark TTFT | `docs/grok-api/gotchas.md` |
| Voce realtime, eventi, tool in voce | `docs/voice/README.md`, `docs/voice/events-reference.md`, `docs/voice/tool-calling-in-voice.md` |
| Esempio vocale funzionante (mock) | `docs/voice/examples/voice_agent_local.py` |
| Imagine | `docs/bots-imagine/grok-imagine.md` |
| Grok Bot (webhook, routine) | `docs/bots-imagine/grok-bots.md` |
| Grok Build | `docs/grok-api/grok-build.md` |
| LLM → hardware sicuro | `docs/hardware/llm-robot-architecture.md` |

Nessuno snippet dei docs era stato eseguito contro l'API vera al 2026-11-03: se qualcosa non torna con la key dell'evento, correggi il file in `docs/` e togli il ⚠️.
