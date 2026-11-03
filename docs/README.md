# Documentazione: indice

> Ricerca preparatoria del **2026-11-03** per il Grok Hackathon at the Museum (Pavia, 4–5 nov 2026). Ogni file ha in testa la data di verifica, in fondo le **Fonti**, e segna con ⚠️ ciò che non è verificato. **Nessuno snippet è stato eseguito contro l'API reale** (niente key prima dell'evento): verificarli subito con la key dell'evento.

## Per orientarsi in 5 minuti

1. [event/hackathon.md](event/hackathon.md): agenda, regole, cosa consegnare, giuria.
2. [ideas/ideas.md](ideas/ideas.md): le 17 idee, le 3 scommesse e le correzioni dopo la ricerca.
3. [hardware/llm-robot-architecture.md](hardware/llm-robot-architecture.md): come collegare Grok all'hardware in modo sicuro.
4. [grok-api/README.md](grok-api/README.md) e [voice/README.md](voice/README.md): i TL;DR tecnici.

## Struttura

### [event/](event/): l'evento
| File | Contenuto |
|---|---|
| [hackathon.md](event/hackathon.md) | Agenda, regole, team size, cosa consegnare, criteri (indizi), giuria con profili, speaker, logistica |
| [grokbot-site.md](event/grokbot-site.md) | Tutto il contenuto di pavia.grokbot.it: tracce, regole, giuria, risorse |
| [calendar-and-luma.md](event/calendar-and-luma.md) | Dati da Google Calendar e Luma, brief originale, discrepanze tra le fonti |
| [museum.md](event/museum.md) | Ctrl+Alt Museum e comPVter: collezione, pezzi iconici, progetti AI già fatti |
| [spacexai-landscape.md](event/spacexai-landscape.md) | SpaceX + xAI + Cursor → SpaceXSI, prodotti Grok a nov 2026, cosa valorizzare davanti alla giuria |

### [ideas/](ideas/): cosa costruire
| File | Contenuto |
|---|---|
| [ideas.md](ideas/ideas.md) | Le 17 idee (Orbita / Luna / Marte), 3 scommesse, piano delle 36 ore, correzioni post-ricerca |
| [prior-art.md](ideas/prior-art.md) | Cosa esiste già per ogni idea (ricerca e prodotti) e come differenziarsi |
| [staff-questions.md](ideas/staff-questions.md) | Checklist per il giro dell'hardware di mer 9:00, con tabella risposte da compilare |

### [grok-api/](grok-api/): Grok API (testo, vision, tool, agentic)
| File | Contenuto |
|---|---|
| [README.md](grok-api/README.md) | Indice, "cosa usare per cosa", 10 fatti chiave, primi 5 minuti |
| [models.md](grok-api/models.md) | Model id, contesto, prezzi, capability, rate limit |
| [responses-and-chat.md](grok-api/responses-and-chat.md) | Auth, base URL, Responses API, Chat Completions, compatibilità OpenAI, streaming, reasoning |
| [tools-and-structured-output.md](grok-api/tools-and-structured-output.md) | Function calling, `tool_choice`, parallel tool calls, JSON schema / Pydantic / Zod |
| [vision.md](grok-api/vision.md) | Input immagini: formati, limiti, base64, `detail` |
| [agentic-server-tools.md](grok-api/agentic-server-tools.md) | web_search, x_search, code execution, Files, Collections, remote MCP, costi |
| [sdk-quickstart.md](grok-api/sdk-quickstart.md) | xai-sdk, OpenAI SDK, Vercel AI SDK, SDK TS, docs MCP per Claude Code |
| [grok-build.md](grok-api/grok-build.md) | Grok Build CLI: headless, ACP, config, plugin per Claude Code |
| [gotchas.md](grok-api/gotchas.md) | Errori, limiti, latenza per robot real-time, mini benchmark TTFT |

### [voice/](voice/): Grok Voice
| File | Contenuto |
|---|---|
| [README.md](voice/README.md) | Indice, TL;DR, quale stack per quale idea, checklist dei primi 15 minuti |
| [voice-agent-realtime.md](voice/voice-agent-realtime.md) | Realtime WebSocket: sessione, audio, VAD, barge-in, voci, lingue |
| [events-reference.md](voice/events-reference.md) | Elenco eventi client/server |
| [tool-calling-in-voice.md](voice/tool-calling-in-voice.md) | Tool calling dentro la sessione vocale |
| [tts-stt.md](voice/tts-stt.md) | TTS e STT REST e streaming |
| [custom-voices.md](voice/custom-voices.md) | Voci custom: requisiti e limiti (non usabili dall'Italia) |
| [telephony-twilio.md](voice/telephony-twilio.md) | Twilio Media Streams e SIP diretto |
| [code-samples.md](voice/code-samples.md) | Snippet commentati |
| [gotchas.md](voice/gotchas.md) | Echo, latenza, interruzioni, riconnessione |
| [examples/](voice/examples/) | `voice_agent_local.py` (mic/casse + tool, `--text`), `twilio_bridge.py`, `browser/`, `tts_stream_play.py` |

### [bots-imagine/](bots-imagine/): Grok Bot, X, Imagine
| File | Contenuto |
|---|---|
| [README.md](bots-imagine/README.md) | Indice, TL;DR, 3 architetture consigliate, domande per il kick-off |
| [grok-bots.md](bots-imagine/grok-bots.md) | Grok Bot (il "bot framework"): computer cloud, routine, webhook, MCP, accesso |
| [x-integration.md](bots-imagine/x-integration.md) | Leggere/postare su X: x_search, X API v2 a consumo, OAuth |
| [grok-imagine.md](bots-imagine/grok-imagine.md) | Immagini e video: modelli, endpoint, prezzi, async |
| [grok-build.md](bots-imagine/grok-build.md) | Grok Build dal lato prodotto: comandi `/imagine`, MCP X |
| [code-samples.md](bots-imagine/code-samples.md) | 10 snippet Python/JS + curl |

### [claude-vs-grok/](claude-vs-grok/README.md): dallo stack Anthropic a Grok, e come lavoriamo
| File | Contenuto |
|---|---|
| [README.md](claude-vs-grok/README.md) | **Dizionario Anthropic → Grok** e matrice decisionale "cosa usare per cosa" |
| [models.md](claude-vs-grok/models.md) | Corrispondenza dei tier, prezzi e rate limit affiancati, raccomandazioni per ruolo |
| [api-platform.md](claude-vs-grok/api-platform.md) | Claude API ↔ Grok API, circa 45 corrispondenze con snippet |
| [dev-tools-and-agents.md](claude-vs-grok/dev-tools-and-agents.md) | Claude Code ↔ Grok Build ↔ Cursor CLI; Agent SDK ↔ equivalenti |
| [cloud-and-automation.md](claude-vs-grok/cloud-and-automation.md) | Managed Agents, routine, sessioni cloud, browser, integrazioni, app, MCP |
| [claude-code-workflow.md](claude-vs-grok/claude-code-workflow.md) | Guida operativa: Claude Code costruisce, Grok gira |
| [preflight-checklist.md](claude-vs-grok/preflight-checklist.md) | Cosa fare la sera prima |

### [hardware/](hardware/README.md): SDK e integrazione dell'hardware
Vedi [hardware/README.md](hardware/README.md): cane robot, droni, braccio, simulatori di volo e guida, cockpit come controller, macchine d'epoca, architettura LLM → robot.
