# grokbot-hackathon: contesto per Claude Code

Repo del team **aidea** (Federico Romeo, Federico Rios, Francesco Puddu) per il **Grok Hackathon at the Museum**: Ctrl+Alt Museum di Pavia, **mer 4 → gio 5 novembre 2026**, organizzato con il team Grok di **SpaceXSI** (ex xAI, poi SpaceXAI). Brief: prendere un hardware del museo, collegarlo a Grok (API, Grok Voice o Grok Bot) e giovedì pomeriggio mostrare qualcosa che all'inizio non funzionava.

La ricerca è stata fatta il **2026-11-03** e sta tutta in [`docs/`](docs/README.md). **Prima di scrivere codice che tocca un'API Grok o un hardware, leggi il file docs pertinente** (tabella sotto): model id, endpoint e formati sono verificati lì e qui sotto c'è solo il riassunto. Nessuno snippet è stato ancora eseguito contro l'API vera (non avevamo una key): al primo uso verifica e, se qualcosa è sbagliato, **correggi il file in `docs/`**.

## Dove trovare cosa

| Ti serve | Leggi |
|---|---|
| Indice completo della documentazione | [docs/README.md](docs/README.md) |
| Agenda, regole, giuria, criteri, cosa consegnare | [docs/event/hackathon.md](docs/event/hackathon.md), [docs/event/grokbot-site.md](docs/event/grokbot-site.md), [docs/event/calendar-and-luma.md](docs/event/calendar-and-luma.md) |
| Il museo e la sua collezione | [docs/event/museum.md](docs/event/museum.md) |
| Stato di SpaceXSI e dei prodotti Grok | [docs/event/spacexai-landscape.md](docs/event/spacexai-landscape.md) |
| Le 17 idee, le 3 scommesse, il piano delle 36 ore | [docs/ideas/ideas.md](docs/ideas/ideas.md) |
| Cosa esiste già (prior art) | [docs/ideas/prior-art.md](docs/ideas/prior-art.md) |
| Domande allo staff (giro hardware mer 9:00) | [docs/ideas/staff-questions.md](docs/ideas/staff-questions.md) |
| Modelli, prezzi, rate limit | [docs/grok-api/models.md](docs/grok-api/models.md) |
| Chiamare Grok (Responses API, SDK, streaming) | [docs/grok-api/responses-and-chat.md](docs/grok-api/responses-and-chat.md), [docs/grok-api/sdk-quickstart.md](docs/grok-api/sdk-quickstart.md) |
| Function calling e structured output | [docs/grok-api/tools-and-structured-output.md](docs/grok-api/tools-and-structured-output.md) |
| Immagini in input (camera del robot, webcam) | [docs/grok-api/vision.md](docs/grok-api/vision.md) |
| Tool server-side (web/X search, code exec, MCP) | [docs/grok-api/agentic-server-tools.md](docs/grok-api/agentic-server-tools.md) |
| Latenza, errori, trappole | [docs/grok-api/gotchas.md](docs/grok-api/gotchas.md) |
| Voce realtime con tool calling | [docs/voice/README.md](docs/voice/README.md) → [voice-agent-realtime.md](docs/voice/voice-agent-realtime.md), [events-reference.md](docs/voice/events-reference.md), [tool-calling-in-voice.md](docs/voice/tool-calling-in-voice.md) |
| TTS / STT, telefonia Twilio/SIP, voci custom | [docs/voice/tts-stt.md](docs/voice/tts-stt.md), [docs/voice/telephony-twilio.md](docs/voice/telephony-twilio.md), [docs/voice/custom-voices.md](docs/voice/custom-voices.md) |
| Esempi vocali pronti da lanciare | [docs/voice/examples/](docs/voice/examples/) |
| Grok Bot (il "bot framework"), X, Grok Imagine | [docs/bots-imagine/README.md](docs/bots-imagine/README.md) |
| Grok Build (CLI di coding `grok`) | [docs/grok-api/grok-build.md](docs/grok-api/grok-build.md), [docs/bots-imagine/grok-build.md](docs/bots-imagine/grok-build.md) |
| Hardware del museo e SDK (cane, droni, simulatori, retro) | [docs/hardware/README.md](docs/hardware/README.md) |
| Architettura LLM → robot sicura, tool JSON pronti, validatore | [docs/hardware/llm-robot-architecture.md](docs/hardware/llm-robot-architecture.md) |
| **Equivalente Grok di ogni cosa Anthropic, e cosa usare per cosa** | [docs/claude-vs-grok/README.md](docs/claude-vs-grok/README.md) → [models.md](docs/claude-vs-grok/models.md), [api-platform.md](docs/claude-vs-grok/api-platform.md), [dev-tools-and-agents.md](docs/claude-vs-grok/dev-tools-and-agents.md), [cloud-and-automation.md](docs/claude-vs-grok/cloud-and-automation.md) |
| **Come lavoriamo: Claude Code costruisce, Grok gira** | [docs/claude-vs-grok/claude-code-workflow.md](docs/claude-vs-grok/claude-code-workflow.md), [preflight-checklist.md](docs/claude-vs-grok/preflight-checklist.md) |

## Strumenti di Claude Code già configurati in questa repo

- **`.mcp.json` → `xai-docs`** (`https://docs.x.ai/api/mcp`, nessuna auth, verificato): approvalo al primo `claude`. Prima di scrivere codice su un'API Grok, **cerca nelle docs live con `mcp__xai-docs__search_docs` / `get_doc_page`** invece di andare a memoria: i docs xAI cambiano di continuo.
- **Skill `grok-api`** (`.claude/skills/grok-api/`): model id, endpoint, formati dei tool, regole di runtime. Si carica quando scrivi codice che chiama Grok.
- **Skill `robot-safety`** (`.claude/skills/robot-safety/`): whitelist, validatore, kill switch, mock-first. Si carica quando scrivi codice che muove hardware. **Non lanciare mai `--real` sull'hardware: lo fa un umano.**
- Grok Build (`grok`) legge gli stessi `CLAUDE.md`, skill e `.mcp.json`; Cursor legge [AGENTS.md](AGENTS.md), che rimanda qui.

## Fatti chiave (riassunto, dettagli e fonti nei docs)

**Grok API**
- Base URL `https://api.x.ai/v1`, header `Authorization: Bearer $XAI_API_KEY`. API raccomandata: **Responses** (`POST /v1/responses`); Chat Completions è deprecata ma funziona; l'SDK OpenAI funziona cambiando `base_url`. Compatibilità Anthropic deprecata: non usarla.
- Modelli: `grok-4.7` (punta, 500k ctx, testo+immagini, reasoning **non disattivabile**, `reasoning.effort` low/medium/high/xhigh); `grok-build-0.1` (coding); per bassa latenza `grok-4.3` con `reasoning.effort: "none"` o `grok-4.20-0309-non-reasoning`. Niente varianti `-fast` via API.
- Tool: forma piatta `{"type":"function","name","description","parameters"}`; risposta `function_call` → rimandare `function_call_output` con `call_id`. Per i robot usare `parallel_tool_calls: false`.
- Vision: jpg/png ≤ 20 MiB, URL o data URL base64, `detail` low/high/auto.
- SDK: `xai-sdk` (Python ≥ 3.10), `openai`, `@ai-sdk/xai`. Docs MCP: `claude mcp add --transport http xai-docs https://docs.x.ai/api/mcp`.

**Grok Voice**
- `wss://api.x.ai/v1/realtime?model=grok-voice-latest` (= `grok-voice-3.0`), protocollo **compatibile OpenAI Realtime**. Audio default PCM16 mono 24 kHz base64; `audio/pcmu` 8 kHz per telefonia.
- `turn_detection: {"type":"server_vad"}` (impostarlo sempre esplicitamente). Su `input_audio_buffer.speech_started` svuotare il proprio buffer di playback (barge-in).
- Tool: `response.function_call_arguments.done` → eseguire → `conversation.item.create` con `function_call_output` → `response.create`.
- Italiano supportato. Voci built-in (default `eve`). **Custom Voices non usabile** (solo USA, niente cloning da registrazioni).
- Browser: token effimero da `POST /v1/realtime/client_secrets`. $0.08/min, sessione max 120 min.

**Grok Bot / X / Imagine**
- Grok Bot è un'**app** con computer cloud persistente, non un SDK. Si aggancia via webhook routine, MCP server propri, email, cron. Il tag @bot su X **non funziona dall'UE**.
- Leggere X: tool `x_search` della Responses API. Postare: X API v2 a consumo, OAuth utente.
- Imagine: immagini sincrone (`grok-imagine-image-2.0`), video asincroni (`request_id` + polling `GET /v1/videos/{id}`, 1–15 s, edit ≤ 8,7 s solo con `grok-imagine-video`).

**Hardware** (modelli non pubblicati: confermare al giro di mer 9:00)
- Cane robot (forse Xiaomi CyberDog, ⚠️ da snippet di stampa), simulatore di volo (3 schermi, piattaforma mobile), simulatore di guida, alcuni droni, **braccio robotico** (solo sul sito). Il museo ha anche un Ultimate 64 con REST API e il "chattralino" (telefoni a disco + ChatGPT).
- C64 ↔ LLM: bridge già provato in VICE (monitor binario, porta 6502), vedi [docs/hardware/retro-machines.md](docs/hardware/retro-machines.md).
- Se il cane è un Unitree Go2: WebRTC con `unitree_webrtc_connect`, serve la **chiave AES** del proprietario, un solo client alla volta, comandi di velocità da ripetere in loop, **mai `Damp`**.
- Se i droni sono Tello: comandi UDP testuali, `stop` = hover, `emergency` = motori spenti; atterra da solo dopo 15 s senza comandi (keepalive); collegati al Tello si perde Internet.

**Evento**
- Kick-off **mer 9:00** (il calendario dice 10:00 ed è sbagliato). Gio 9:00 talk di **Ralph Johnson** (SpaceXSI, anche in giuria). Gio 16–19 pitch.
- Da consegnare: **repo GitHub con README, demo 5 min, dataset/fixture, risultati quantitativi, limiti, roadmap**. Criteri: "To be announced"; principi del sito: Reproducibility, Evidence first, Human in the loop, Security by design, Realistic scope.

## Regole di lavoro in questa repo

- **Lingua:** docs e README in italiano; codice, identificatori e commenti tecnici in inglese.
- **Sicurezza hardware:** Grok pianifica, l'hardware esegue. L'LLM chiama solo primitive in whitelist; un validatore deterministico (limiti, geofence) sta tra LLM e robot; kill switch locale (tastiera/voce) sempre attivo e indipendente dall'LLM. Provare sempre prima su mock/simulatore. Vedi [docs/hardware/llm-robot-architecture.md](docs/hardware/llm-robot-architecture.md).
- **Segreti:** `XAI_API_KEY` e altre chiavi solo in `.env` (ignorato da git). Mai committare chiavi, token Twilio o la chiave AES del cane.
- **Misurare:** la giuria vuole risultati quantitativi. Loggare latenze, tool call e successi/fallimenti in file (JSONL) fin dal primo prototipo.
- **Codice del progetto:** quando scegliamo l'idea, il codice va in `src/` (o in una cartella col nome del progetto) con il suo README; aggiornare questo file con la scelta fatta e il comando per avviare la demo.
- **Docs vive:** se una cosa nei docs si rivela sbagliata sul posto (modello hardware, endpoint, comportamento), correggi il file e togli il ⚠️.

## Stato

- 2026-11-03: ricerca completata, nessun codice. Idea non ancora scelta (le 3 scommesse: *Il trucco nuovo*, *Mayday*, *Hackerato con un A4*; vedi [docs/ideas/ideas.md](docs/ideas/ideas.md)).
