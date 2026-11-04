# Claude ↔ Grok: cosa usare per cosa

> Sintesi del 2026-11-03 per chi conosce a fondo lo stack Anthropic e costruisce tutto con Claude Code, ma deve far girare Grok a runtime. I dettagli, le fonti e i ⚠️ stanno nei file linkati. **Niente di questa cartella è stato eseguito con una key reale** (solo il docs MCP xAI e le skill sono stati verificati davvero).

## Il principio

**Claude Code costruisce, Grok gira.** Claude Code (con il docs MCP xAI e le skill di progetto) scrive tutto il codice. Il codice che va in demo chiama **solo** Grok: API, Voice, Imagine, Bot. Grok Build e Grok Bot vanno usati per un lavoro reale e visibile, perché la giuria SpaceXSI li apprezza. Dettagli in [claude-code-workflow.md](claude-code-workflow.md).

## File di questa cartella

| File | Cosa contiene |
|---|---|
| [models.md](models.md) | Opus/Sonnet/Haiku/Fable ↔ `grok-4.7`/`grok-4.3`/`grok-4.20-*`/`grok-build-0.1`: prezzi affiancati, rate limit, raccomandazioni per ruolo, id da non usare |
| [api-platform.md](api-platform.md) | Messages ↔ Responses, tool use, thinking ↔ reasoning, caching, batch, file, citazioni, server tool, vision, computer use, voce, Imagine, SDK, errori: circa 45 corrispondenze con snippet affiancati |
| [dev-tools-and-agents.md](dev-tools-and-agents.md) | Claude Code ↔ Grok Build (`grok`) ↔ Cursor CLI (`agent`) feature per feature (30 righe); Agent SDK ↔ Cursor SDK / `grok -p` / ACP |
| [cloud-and-automation.md](cloud-and-automation.md) | Managed Agents, routine, sessioni cloud, browser/computer use, Slack/GitHub/Linear, claude.ai ↔ grok.com, MCP: chi è client e chi server, ricetta per esporre l'hardware via MCP |
| [claude-code-workflow.md](claude-code-workflow.md) | Guida operativa: setup, delega a Grok Build, struttura mock-first, contratti, metriche, lavoro in 3, come rendere visibili gli strumenti SpaceXSI |
| [preflight-checklist.md](preflight-checklist.md) | Cosa fare stasera: installazioni, `grok login`, PortAudio, VICE, rete WSL, test offline |

## Il dizionario: "conosco X di Anthropic, cosa uso lato Grok?"

### Modelli e API
| Anthropic | Grok / SpaceXSI | Quanto è vicino | Note |
|---|---|---|---|
| Opus 5.5 | `grok-4.7` | ≈ | Punta, 500k di contesto, reasoning non disattivabile |
| Sonnet 5.5 | `grok-4.3` | ≈ | 1M di contesto, effort di default `low` |
| Haiku 5.5 | `grok-4.3` con `reasoning.effort:"none"` / `grok-4.20-0309-non-reasoning` | ~ | Costa circa 12 volte Haiku in input |
| (nessun modello di coding dedicato) | `grok-build-0.1` | — | Modello di coding via API |
| Messages API `POST /v1/messages` | Responses API `POST /v1/responses` | ≈ | Si usa l'SDK `openai` con `base_url="https://api.x.ai/v1"`. **Non usare l'SDK `anthropic`** (la compatibilità è deprecata) |
| History lato client | `store=False` + `input += response.output`, oppure `previous_response_id` | ≈ | `store` è **true di default**, con 30 giorni di retention |
| `tool_use` / `tool_result` (`tool_use_id`) | `function_call` / `function_call_output` (`call_id`) | = | Argomenti come stringa JSON, niente `is_error` |
| `disable_parallel_tool_use` | `parallel_tool_calls=False` | = | Usarlo sempre per i robot |
| `strict: true`, `messages.parse` | Tool sempre strict; `responses.parse(text_format=)` | = | |
| Extended/adaptive thinking, `effort` | `reasoning.effort` (`none`…`xhigh`) | ≈ | Gli item `reasoning` con `encrypted_content` vanno ripassati invariati, come i blocchi thinking firmati |
| `cache_control` | Cache automatica + `prompt_cache_key` | ~ | Scrittura gratis, ma i token in cache contano nel limite TPM |
| Batch API (−50%) | `/v1/batches` (−20%) | ≈ | Non disponibile per `grok-build-0.1` |
| Web search / web fetch | `web_search` (naviga anche le pagine) | ≈ | Non c'è un fetch separato |
| — | `x_search` | Solo Grok | Leggere X senza account né X API |
| Code execution tool | `code_interpreter` (`code_execution` in xai-sdk) | ≈ | |
| Files API + ricerca su documenti | Files + Collections (`file_search`) | ≈ | Per creare le Collections serve una Management key |
| MCP connector (beta) | Remote MCP tool `{"type":"mcp","server_url",...}` (GA) | ≈ | Lo stesso server MCP è usabile anche da Grok Voice. **Rifiuta localhost e IP privati**: serve un tunnel |
| Memory tool | — | ✗ | Va fatto a mano, con file o un DB |
| Computer use | — | ✗ | Il più vicino è il browser del computer cloud di Grok Bot |
| Vision (immagini + PDF) | Vision solo jpg/png ≤ 20 MiB | ~ | I PDF vanno convertiti in immagini o passati con Files |
| Token counting | `POST /v1/tokenize-text` | ~ | Conta solo il testo |
| (nessuna API vocale) | **Grok Voice Agent** realtime, TTS, STT | Solo Grok | Compatibile con OpenAI Realtime. Vedi [../voice/](../voice/README.md) |
| (nessuna generazione di media) | **Grok Imagine** immagini e video | Solo Grok | Vedi [../bots-imagine/grok-imagine.md](../bots-imagine/grok-imagine.md) |

### Agenti, dev tool e cloud
| Anthropic | Grok / SpaceXSI / Cursor | Quanto è vicino | Note |
|---|---|---|---|
| Claude Code CLI | **Grok Build** (`grok`); Cursor CLI (`agent`) | = (clone dichiarato) | Grok Build **legge già** `CLAUDE.md`, `.claude/skills`, agents, hooks, plugin e `.mcp.json` di questa repo |
| `claude -p --output-format json` | `grok -p --output-format json`; `agent -p --force` | = | Cursor senza `--force` non scrive file |
| `CLAUDE.md` | Grok: `CLAUDE.md`/`AGENTS.md`/`.grok/rules`; Cursor: `AGENTS.md`, `.cursor/rules` | = / ~ | Per Cursor la repo ha un [`AGENTS.md`](../../AGENTS.md) che rimanda a `CLAUDE.md` |
| Skills, subagents, plugin, marketplace | Stesso formato in `.grok/` e `.cursor/`; marketplace ufficiale `xai-org/plugin-marketplace` | = | |
| Hooks | `.grok/hooks/*.json`, stesso schema | ≈ | **Grok è fail-open**: per la sicurezza dell'hardware non affidarsi agli hook |
| `/loop`, `/goal`, worktree, `/rewind`, plan mode | Gli stessi comandi in Grok Build | = | |
| Claude Agent SDK | Cursor SDK (`@cursor/sdk`, `cursor-sdk`); `grok -p` o ACP (`grok agent stdio`); `@grok/agent-sdk` (troppo nuovo) | ~ | Lato xAI puro non c'è un "Agent SDK": per i tool nostri il loop si scrive a mano sulla Responses API |
| Tool Runner | Loop manuale in xai-sdk / Vercel AI SDK `stopWhen`; loop server-side con `max_turns` solo per i tool di xAI | ~ | |
| Managed Agents | Cursor Cloud Agents API (beta); Grok Bot (senza API) | ~ | |
| Scheduled tasks / routines, `/fire` webhook | **Grok Bot routines** (cron ≥ 5 min, webhook che risponde solo 200); Cursor Automations | ≈ | Il risultato arriva nella chat del Bot, non a chi chiama |
| Sessioni cloud (`claude --cloud`), Remote Control | Cursor Cloud Agents (`&` nella CLI), My Machines; Grok Bot "execution on this computer" | ~ | |
| Claude in Chrome / computer use | Browser del computer cloud di Grok Bot; browser integrato di Cursor | ~ | Claude in Chrome **non supporta WSL** |
| Claude Tag (Slack), claude-code-action, Code Review | Grok Bot in Slack, `@cursor` su Slack/GitHub/Linear, Bugbot | ≈ | Non c'è una GitHub Action ufficiale per Grok Build |
| claude.ai: Projects, Artifacts, Memory, connettori | grok.com: Projects, Connectors (Custom MCP); Grok Bot | ~ | Vedi [cloud-and-automation.md](cloud-and-automation.md) |
| Billing: abbonamento Claude / API key | Crediti API xAI (Grok Build con key, Responses, Voice) **≠** pool della X Subscription (Cursor, Grok Bot) | — | I crediti dell'evento probabilmente non coprono Cursor né Grok Bot ⚠️ |

Legenda: **=** equivalente diretto · **≈** stessa funzione con differenze · **~** il più simile · **✗** manca · *Solo Grok*: Anthropic non ha un equivalente.

## Matrice decisionale per l'hackathon

| Cosa devo fare | Usa | Perché / come |
|---|---|---|
| Scrivere tutto il codice | **Claude Code** + docs MCP `xai-docs` + skill `grok-api` | È lo strumento che conosci. L'MCP evita di scrivere a memoria su docs che cambiano ogni giorno |
| Cervello del robot (pianificazione, scelta dei tool) | `grok-4.7` su Responses, `parallel_tool_calls=False` | Il modello migliore. Il reasoning non si spegne, quindi lo usiamo dove 1–3 s sono accettabili |
| Loop veloce (comandi brevi, classificazione, giudice) | `grok-4.3` con `reasoning.effort:"none"` | Latenza minima |
| Interfaccia vocale con tool sull'hardware | **Grok Voice Agent** (`grok-voice-latest`) | Fa voce e tool calling in un'unica sessione. Partire da [../voice/examples/voice_agent_local.py](../voice/examples/voice_agent_local.py) |
| Telecronaca / lettura di testo | TTS streaming | Più economico e controllabile di una sessione realtime |
| Vedere la scena (camera robot, schermo C64) | Vision su `grok-4.7` o `grok-4.3` (jpg, `detail:"low"` per la velocità) | |
| Far generare codice a runtime (es. "il trucco nuovo") | `grok-build-0.1` via API, oppure `grok -p` headless in sandbox | Grok che scrive codice è proprio la storia da raccontare alla giuria |
| Esporre l'hardware a più agenti | **Un unico MCP server** (Streamable HTTP) + tunnel | Lo usano Claude Code in sviluppo e Grok (Responses, Voice, Bot) a runtime. Vedi la ricetta in [cloud-and-automation.md](cloud-and-automation.md) |
| Leggere X | `x_search` (server tool) | Niente account né OAuth |
| Postare su X | X API v2 con OAuth utente | Il tag @bot non funziona dall'UE |
| Asset visivi, trailer, poster | **Grok Imagine** | Immagini sincrone, video asincroni con polling |
| Second opinion / review prima del code freeze | **Grok Build** read-only (`grok -p` o il plugin `grok-build-plugin-cc` con review/critique) | Diventa prova d'uso per la giuria. **Mai `delegate`** sul portatile collegato all'hardware |
| Un componente isolato costruito "da Grok" | Grok Build in un worktree dedicato | Uso reale e visibile, fuori dal percorso critico |
| Report automatico a fine run, diario di bordo | **Grok Bot** routine con webhook | Mostra Grok Bot al lavoro su una parte vera. Le prove vanno in `docs/evidence/` |
| Lavoro in parallelo tra noi 3 | Claude Code con worktree (`claude -w <modulo>`), main sempre funzionante in mock | Contratti fissati nella prima ora. Dettagli in [claude-code-workflow.md](claude-code-workflow.md) §4 |
| Task lunghi senza hardware (dashboard, test, README) | Sessioni cloud di Claude Code | Mai chiavi né hardware nel cloud |
| Sicurezza dell'hardware | **Validatore deterministico + kill switch locale** nel nostro codice | Non affidarla né all'LLM né agli hook (Grok è fail-open). Vedi [../hardware/llm-robot-architecture.md](../hardware/llm-robot-architecture.md) |
| Metriche per la giuria | Log JSONL di ogni run → `scripts/metrics.py` | Successi, rifiuti agli attacchi, latenze p50/p95, costo |

## Cosa non fare

- Non usare l'SDK `anthropic` o modelli Claude nel codice di runtime (in [claude-code-workflow.md](claude-code-workflow.md) c'è un test che lo impedisce).
- Non usare id inventati come `grok-4.7-fast` o `grok-4.7-reasoning`: via API non esistono. L'elenco completo è in [models.md](models.md).
- Non registrare un MCP su `localhost` per i tool server-side di xAI: viene rifiutato, serve un tunnel pubblico.
- Non far girare `grok ... delegate --write` o `--yolo` sulla macchina collegata al robot.
