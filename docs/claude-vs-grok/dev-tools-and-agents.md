# Dev tools e agenti: Claude Code ↔ Grok Build ↔ Cursor (+ Agent SDK)

> **Verificato il:** 2026-11-03. Lato Grok, la fonte primaria sono [../grok-api/grok-build.md](../grok-api/grok-build.md) e [../bots-imagine/grok-build.md](../bots-imagine/grok-build.md); oggi ho riletto tutte le pagine `docs.x.ai/build/*.md`, il repo `xai-org/plugin-marketplace` e l'elenco dei repo `xai-org`. Lato Cursor ho letto `cursor.com/docs/*.md` (CLI, rules, skills, subagents, hooks, plugins, MCP, SDK, Agent SDK, pricing). Lato Claude ho letto `code.claude.com/docs/en/*.md` (headless, memory, worktrees, scheduled tasks, agent view, workflows, goal, Agent SDK).
> **Nessuna delle tre CLI è stata installata né eseguita.** ⚠️ = non verificato o dedotto.
> Altri file di questa cartella: modelli in [models.md](models.md), API Messages ↔ Responses in [api-platform.md](api-platform.md), workflow pratico Claude Code → Grok in [claude-code-workflow.md](claude-code-workflow.md). Il cloud, le automazioni, le app e l'MCP sono in [cloud-and-automation.md](cloud-and-automation.md).

## In breve

- **Grok Build (`grok`) è un clone dichiarato di Claude Code.** La doc dice: *"Grok is fully compatible with Claude Code with zero configuration needed"*. Legge `CLAUDE.md`, `.claude/rules/`, skills, agents, hooks, plugin, marketplace e MCP di Claude Code, accetta i flag di Claude Code come alias e importa le sessioni (`grok import`, `/import-claude`). Quindi **la nostra repo è già pronta per Grok Build così com'è**.
- **Cursor CLI (`agent`)** è il terzo agente da terminale e appartiene alla stessa società. Legge `AGENTS.md`, `.cursor/rules/*.mdc`, e per compatibilità anche `.claude/skills/`, `.claude/agents/` e gli hook in `.claude/settings.json`. **Non risulta che legga `CLAUDE.md`** (⚠️ non documentato).
- **Claude Agent SDK.** L'equivalente più vicino è il **Cursor SDK** (`@cursor/sdk` per TS, `cursor-sdk` per Python): l'agente di Cursor come libreria, che gira in locale o nel cloud e può usare Grok 4.7. Lato xAI puro non c'è un "Grok Agent SDK". Ci sono due ripieghi: pilotare `grok` in **headless** o via **ACP**, oppure usare la Responses API con i tool server-side e `max_turns`. Infine esiste **`@grok/agent-sdk`** (era `@cursor/bdk`, v0.6.0, pubblicato su npm il 22/10/2026): serve a definire "agents as code" deployati su Cursor. È più vicino a Managed Agents che all'Agent SDK.
- **Billing, la differenza che conta all'hackathon.** I "API credits" dell'evento sono presumibilmente crediti xAI API. **Li usano Grok Build (con `XAI_API_KEY`), la Responses API e Voice.** Cursor (CLI, SDK, Cloud Agents) e Grok Bot invece consumano il **pool settimanale della X Subscription** (*"The Grok API is billed separately and doesn't draw from the pool"*).

## Tabella di corrispondenza (feature per feature)

| Claude Code | Grok Build (`grok`) | Cursor CLI (`agent`) | Note |
|---|---|---|---|
| Install `npm i -g @anthropic-ai/claude-code` / installer nativo | `curl -fsSL https://x.ai/cli/install.sh \| bash` | `curl https://cursor.com/install -fsS \| bash` | Tutti e tre supportano Linux/WSL |
| Login `claude` / `/login`, `ANTHROPIC_API_KEY` | `grok login` (`--device-auth`), `XAI_API_KEY` | `agent login`, `CURSOR_API_KEY` | Con la key xAI si pagano i token API; col login si paga sull'abbonamento |
| TUI interattiva `claude` | `grok` (TUI fullscreen, con il mouse) | `agent` | |
| Headless `claude -p "..." --output-format json\|stream-json` | `grok -p "..." --output-format plain\|json\|streaming-json` | `agent -p "..." --output-format text\|json\|stream-json` (+ `--stream-partial-output`) | **In Cursor, `-p` senza `--force` non scrive i file** |
| `--max-turns`, `--allowedTools`, `--append-system-prompt` | `--max-turns`, `--tools`/`--disallowed-tools`, `--rules`, `--system-prompt-override` (accetta anche i nomi di Claude) | ⚠️ nessun `--max-turns` documentato | |
| `--json-schema` (output strutturato headless) | ⚠️ non documentato | ⚠️ non documentato | |
| `--resume`, `--continue`, `--fork-session` | `-r`, `-c`, `--fork-session`, `-s <UUID>` | `--resume [id]`, `--continue`, `agent ls` | Sessioni in `~/.grok/sessions/` |
| Permission modes: `default`, `acceptEdits`, `plan`, `auto`, `dontAsk`, `bypassPermissions` | Ask (default), Auto (classifier), Always-approve (`--yolo`), `dontAsk` (headless, pagina Enterprise), Plan | Agent / Plan / Ask; `--force`/`--yolo`; "Run Everything" | Shift+Tab cicla i modi in tutti e tre |
| Regole `permissions.allow/deny` in `settings.json` (`Bash(git *)`) | `[permission] rules = [{action, tool, pattern}]` in TOML; `--allow`/`--deny` | `permissions.allow/deny` con token `Shell(git)`, `Read(glob)`, `Write(glob)` | In Grok `deny` vince sempre; un allow esplicito da config approva anche `rm`/`git push` |
| Sandbox (`/sandbox`, bubblewrap/Seatbelt) | `--sandbox off\|workspace\|devbox\|read-only\|strict` + profili in `.grok/sandbox.toml` | `--sandbox enabled\|disabled`, `agent sandbox run` | Grok: Landlock su Linux; la rete dei processi figli è bloccata solo su Linux |
| `CLAUDE.md`, `CLAUDE.local.md`, `.claude/rules/`, `@import` | `AGENTS.md`/`AGENT.md`/`CLAUDE.md`/`CLAUDE.local.md` + `.grok/rules/*.md` (legge anche `.claude/rules/` e `.cursor/rules/`) | `AGENTS.md` (anche annidati) + `.cursor/rules/*.mdc` con frontmatter | Claude Code legge `AGENTS.md` solo se manca `CLAUDE.md` (dalla v2.1.277). Verifica con `grok inspect` |
| `settings.json` (user / project / local / managed) | `~/.grok/config.toml`, `.grok/config.toml` (solo MCP, plugin e permessi), `managed_config.toml`, `requirements.toml` | `~/.cursor/cli-config.json`, `.cursor/cli.json` | Grok legge anche un sottoinsieme del `managed-settings.json` di Claude |
| Hooks in `settings.json` (`PreToolUse`, `PostToolUse`, `Stop`, …) | `.grok/hooks/*.json`, **stesso schema** (`matcher`, `type: command\|http`). Legge `.claude/settings.json` e `.cursor/hooks.json`. Gli hook di progetto richiedono `/hooks-trust` | `.cursor/hooks.json` con eventi camelCase (`beforeShellExecution`, `afterFileEdit`, `preToolUse`, `stop`…). Legge gli hook di Claude | **Grok è fail-open**: timeout, crash o output malformato lasciano passare il tool, e blocca solo un `deny` esplicito o l'exit 2. Per l'hardware non affidarsi solo all'hook |
| Slash commands (`.claude/commands/`, ora dentro le skills) | Le skill user-invocable diventano `/<skill>`. Legge anche `~/.agents/commands/` e i comandi dei plugin | Comandi built-in + skill (`/plan`, `/ask`, `/debug`, `/goal`) | |
| **Skills** `.claude/skills/<n>/SKILL.md` | `.grok/skills/`, `~/.grok/skills/`, `~/.agents/skills/`, plugin e **quelle di Claude**. Frontmatter: `name`, `description`, `when-to-use`, `paths`, `disable-model-invocation`, `user-invocable` | `.cursor/skills/`, `~/.cursor/skills/`, + `.claude/skills/`, `.codex/skills/` | Stesso formato SKILL.md. Grok ignora `model`/`effort` nel frontmatter |
| **Subagents** `.claude/agents/*.md` (Explore, Plan, general-purpose) | `.grok/agents/`, built-in `general-purpose`, `explore`, `plan` + **personas** (`.grok/personas/*.toml`) | `.cursor/agents/` + `.claude/agents/`; campo `model` (es. `inherit`) | I subagent di Grok non ereditano il gate del plan mode del parent |
| **Plugins/marketplace** `/plugin marketplace add`, `.claude-plugin/marketplace.json` | `grok plugin …`, `grok plugin marketplace add`, `.grok-plugin/marketplace.json`; marketplace ufficiale `xai-org/plugin-marketplace` | `/plugin`, `.cursor-plugin/marketplace.json`, standard aperto Agent Plugins, cursor.com/marketplace | Un plugin Grok ha la stessa struttura di uno Claude: `skills/`, `commands/`, `agents/`, `hooks/hooks.json`, `.mcp.json`, `.lsp.json` |
| MCP client `claude mcp add`, `.mcp.json` | `grok mcp add\|list\|remove\|doctor`, `[mcp_servers.x]` in TOML; legge `.mcp.json`, `~/.claude.json`, `.cursor/mcp.json` | `agent mcp list\|login\|enable`, `.cursor/mcp.json` | Tool esposti come `<server>__<tool>` (Grok) |
| MCP server `claude mcp serve` ⚠️ | — | — | Solo Claude Code si espone come MCP server |
| Output styles | — (il più vicino: `--rules`, `--system-prompt-override`, personas) | — | Nessun equivalente diretto |
| Memory: CLAUDE.md + **auto memory**, `/memory` | `/remember <note>`, `/memory`, `/flush`, `/dream` (consolidamento), `--experimental-memory` (**spenta di default**, `GROK_MEMORY=1`) | ⚠️ non documentata per la CLI | |
| Plan mode | `/plan`, plan review con `a`/`s`/`c`/`q`; auto e always-approve non saltano la review | `/plan`, `--plan` | |
| Checkpoint `/rewind` (Esc Esc) | `/rewind` (Esc Esc) | `/rewind` | Grok ripristina i file su disco |
| `/compact`, `/context` | `/compact`, `/context`, `/session-info` | `/summarize` (`/compress`) | |
| Worktree `claude --worktree` / `-w` | `grok -w [name]`, `--ref`, `grok worktree list\|rm\|gc` | `agent -w [name]`, `--worktree-base`, `.cursor/worktrees.json` | Grok: `~/.grok/worktrees/<repo>/<name>` |
| Background tasks, Monitor tool | `Ctrl+G` task pane, `Ctrl+B` per mandare in background, **monitors** (ogni riga stampata diventa una notifica) | Shell mode | |
| `/loop` (sessione, minimo 1 min, scade dopo 7 giorni) | `/loop 5m …` (minimo 60 s, scade dopo 7 giorni, max 50 task) | — (si usano le Automations cloud) | Identici in pratica |
| `/goal` | `/goal` (con un panel di subagent revisori, `--budget <tokens>`) | `/goal` (in rollout) | |
| Dynamic workflows (script JS che orchestra subagent) | `/create-workflow` → `.grok/workflows/<name>.rhai`, `/workflow`, `/workflows`, `/deep-research` | — | |
| Agent view `claude agents` | `grok dashboard` (`Ctrl+\`) | Agents Window (IDE) | |
| `/btw` | `/btw` | — | |
| Status line | `[ui]` status line (pagina Status Line) | — | |
| IDE: estensione VS Code, plugin JetBrains | Nessuna estensione; integrazione via **ACP** `grok agent stdio` (⚠️ client ACP come Zed non provati) | **È** l'IDE; CLI via ACP `agent acp`; integrazione JetBrains | Claude Code parla ACP solo tramite l'adapter di Zed `@zed-industries/claude-code-acp` (non nativo) |
| ACP | `grok agent stdio`: `initialize` → `authenticate` → `session/new` → `session/prompt` → `session/update` | `agent acp`, auth `cursor_login`, gestisce `session/request_permission` | Stesso protocollo: un client ACP scritto una volta pilota entrambi |
| Modelli alternativi (gateway, Bedrock…) | Qualsiasi endpoint: `[model.x] base_url`, `api_backend = "chat_completions"\|"responses"\|"messages"` | Modelli Cursor (Grok 4.7/4.6/4.5, Composer 2.5) + terze parti (Claude, GPT) a listino da Premium in su | ⚠️ `api_backend = "messages"` farebbe girare Grok Build su un endpoint in formato Anthropic: non provato |
| Import da altri tool | `grok import` (sessioni Claude Code), `/import-claude` (settings) | Importa automaticamente gli hook, le skill e gli agent di Claude | |
| Plugin che fa da ponte | `xai-org/grok-build-plugin-cc` (Claude Code → Grok Build: review, critique, delegate, import) | — | Vedi [../grok-api/grok-build.md](../grok-api/grok-build.md#plugin-ufficiale-per-claude-code-xai-orggrok-build-plugin-cc) |
| GitHub Actions `anthropics/claude-code-action` | **Nessuna action ufficiale** nei repo `xai-org` (⚠️ cercata il 3/11). Si usa `grok --no-auto-update -p …` in uno step con `XAI_API_KEY` | `agent -p` in GitHub Actions (documentato), più Bugbot e le Automations | Vedi [cloud-and-automation.md](cloud-and-automation.md#integrazioni-slack-github-linear) |

## Le differenze che contano davvero

1. **La compatibilità è asimmetrica.** Grok Build legge quasi tutto di Claude Code; Cursor ne legge una parte (skills, agents, hooks, MCP via plugin); Claude Code non legge nulla di `.grok/` né di `.cursor/`. Quindi **la fonte di verità resta in `.claude/` e `CLAUDE.md`**, e gli altri due la ereditano.
2. **`CLAUDE.md` e `AGENTS.md`.** Grok Build li legge entrambi, quindi con un `AGENTS.md` che è un symlink a `CLAUDE.md` caricherebbe lo stesso testo due volte (⚠️ da verificare con `grok inspect`). Cursor legge solo `AGENTS.md`. Claude Code legge `AGENTS.md` solo in assenza di `CLAUDE.md`. Se vogliamo usare Cursor sulla repo serve un `AGENTS.md` o una regola `.cursor/rules/*.mdc` con `alwaysApply: true`. Il "come" è in [claude-code-workflow.md](claude-code-workflow.md).
3. **Hooks fail-open in Grok.** In Claude Code un hook `PreToolUse` che esce con codice 2 blocca. In Grok blocca solo un `deny` esplicito o l'exit 2: timeout (default **5 s**), crash e JSON malformato fanno passare il tool. Per i comandi all'hardware la protezione vera resta il validatore deterministico fuori dall'LLM (vedi [../hardware/llm-robot-architecture.md](../hardware/llm-robot-architecture.md)).
4. **Headless.** Il JSON finale di `grok -p --output-format json` contiene `text`, `stopReason`, `sessionId`, `num_turns`, `usage` e il costo (vedi [../bots-imagine/grok-build.md](../bots-imagine/grok-build.md#headless-script-bot-ci--il-pezzo-utile-per-la-demo)): è lo stesso pattern di `claude -p`. Cursor in `-p` **non applica le modifiche** senza `--force`. Per CI senza prompt, Grok ha `--permission-mode dontAsk` (nega tutto ciò che non ha una allow rule esplicita), come Claude Code.
5. **Memoria.** In Claude Code l'auto memory è attiva; in Grok Build la memoria cross-sessione è sperimentale e spenta. Per l'hackathon conviene mettere tutto in `CLAUDE.md`, che i due tool leggono entrambi.
6. **Modelli.** Grok 4.7 **Fast** esiste solo dentro Grok Build e Cursor, non sull'API (vedi [../grok-api/models.md](../grok-api/models.md)). In Cursor, Grok 4.7 costa $2/$6 per 1M token (Fast $4/$12) e su Plus gira a impostazioni fisse (effort medium, 256k).

## Claude Agent SDK, Tool Runner, loop manuale ↔ equivalenti

| Lato Anthropic | Equivalente più vicino | Cosa cambia |
|---|---|---|
| **Claude Agent SDK** (`@anthropic-ai/claude-agent-sdk`, `claude-agent-sdk`): il loop di Claude Code come libreria, con tool built-in, hooks, subagents, MCP, permessi e sessioni | **Cursor SDK** `@cursor/sdk` (Node ≥ 22.13) / `cursor-sdk` (Python): `Agent.create({ model, local: { cwd } })` oppure `cloud: { repos }`, poi `agent.send()` e `run.stream()`. Ha custom tools (Zod), `mcpServers` inline o da `.cursor/mcp.json`, hooks, sandbox, subagents. Elenca i modelli con `Cursor.models.list()` | **Il più simile a livello di API.** Runtime locale o cloud (VM Cursor). L'inferenza passa sempre da Cursor e si paga sul pool della X Subscription o con la key Cursor, **non con i crediti xAI API**. ⚠️ L'id esatto del modello Grok nell'SDK va letto da `models.list()`. In locale, di default **approva tutti i tool**: vanno messi hook o sandbox |
| Agent SDK "per altri linguaggi": la CLI come subprocess (`claude -p --output-format stream-json`) | `grok -p … --output-format streaming-json` oppure **ACP** `grok agent stdio` (JSON-RPC, esempio Node nelle docs) | **Il più semplice per noi**: gira con `XAI_API_KEY`, quindi coi crediti dell'evento, e porta dietro skills, hooks, MCP e `CLAUDE.md` della repo. Snippet Python in [../bots-imagine/code-samples.md](../bots-imagine/code-samples.md#9-grok-build-headless-da-python) |
| Agent SDK + deploy + trigger ("agent as code") | **`@grok/agent-sdk`** (CLI `agent-sdk init\|dev\|run\|validate\|deploy`): agenti definiti in Markdown + TypeScript (`bot/instructions.md`, tools, skills, subagents, schedules, channels Slack/PR, evals), ospitati da Cursor o self-hosted. È lo stesso harness di Bugbot | Più vicino a **Claude Managed Agents** con le scheduled deployments. Pacchetto molto giovane (0.6.0, ottobre 2026) ⚠️ da non mettere sul percorso critico della demo |
| **Tool Runner** (`client.beta.messages.tool_runner`): loop automatico sui *tuoi* tool | Nessun runner per i tool client-side in `xai-sdk`: il loop si scrive a mano (vedi [../grok-api/tools-and-structured-output.md](../grok-api/tools-and-structured-output.md#snippet-tool-loop-con-la-responses-api-python-openai-sdk)). In TS c'è **Vercel AI SDK** `generateText({ tools, stopWhen: stepCountIs(n) })` con `@ai-sdk/xai`. ⚠️ `@xai-official/sdk` emette eventi `client_tool_call`, ma non ho verificato un runner automatico | Per il robot il loop manuale è comunque preferibile: il validatore e il kill switch si inseriscono tra `function_call` e l'esecuzione |
| **Server tools** (web search, code execution) + loop lato Anthropic | **Tool server-side xAI** (`web_search`, `x_search`, `code_execution`, `collections_search`, `mcp`) con **`max_turns`**: SpaceXSI esegue il loop lato server, e le function client-side lo mettono in pausa e restituiscono il controllo a noi | `max_turns` conta i turni del loop server-side **di una singola richiesta**; dopo una function client-side la richiesta successiva riparte da zero. Dettagli in [../grok-api/agentic-server-tools.md](../grok-api/agentic-server-tools.md) |
| Loop manuale su Messages API | Loop manuale su Responses API (`function_call` → `function_call_output` con `call_id`) | Le differenze di formato sono in [api-platform.md](api-platform.md) |

## Quando usare cosa all'hackathon

| Compito | Strumento | Perché |
|---|---|---|
| Scrivere il codice del progetto (vibecoding) | **Claude Code** | Lo conosciamo, ha auto memory e workflow. La repo è già configurata per lui |
| Seconda opinione o review "made in SpaceXSI" | **Grok Build** via plugin `grok-build-plugin-cc` (`/grok-build:review`, `/grok-build:delegate`) | Zero attrito, e mostra Grok Build alla giuria senza cambiare editor |
| Agente che scrive codice **dentro la demo** (es. "il robot si programma da solo") | **`grok -p --output-format json --cwd robot/ --max-turns N --sandbox workspace`** con allowlist stretta | Il cervello a runtime è Grok, paga con i crediti API, ha log JSON misurabili (`num_turns`, `usage`) |
| Agente embedded in un'app Node/Python con il runtime cloud | Cursor SDK | Solo se abbiamo un abbonamento Premium o superiore. Altrimenti headless o ACP di Grok Build |
| Cervello real-time del robot (latenza bassa) | **Responses API / Grok Voice** con function calling, non un coding agent | Un harness di coding aggiunge secondi di latenza. Vedi [../grok-api/gotchas.md](../grok-api/gotchas.md) |
| Far vedere Cursor | Aprire la repo in Cursor (o `agent`) per un task visibile, e/o Bugbot sulle PR | La giuria cerca "How much Grok Bot and Cursor architected it" ([../event/spacexai-landscape.md](../event/spacexai-landscape.md)) |

## Prezzi e accesso (solo ciò che riguarda questi strumenti)

- **Grok Build.** Con `XAI_API_KEY` si paga a token API (`grok-build-0.1` $1/$2, `grok-4.7` $2/$6 per 1M). Col login rientra nel pool della X Subscription; su **Plus ($8/mese)** c'è già "Build". ⚠️ Free tier citato ma senza limiti pubblicati.
- **Cursor CLI/IDE.** Plus $8 (solo modelli Cursor a impostazioni fisse; niente Cloud Agents, Automations, Bugbot, Grok Bot, modelli terzi); **Premium $30** (aggiunge Cloud Agents, Automations, Bugbot, Grok Bot, modelli terzi a listino); Super $100; Ultra $200. Pool settimanale condiviso con le app Grok e Grok Bot.
- **Cursor SDK / Cloud Agents API.** Stesse regole del piano. Per la CLI headless serve una `CURSOR_API_KEY`.
- **Claude Code / Agent SDK.** Abbonamento Claude (Pro, Max, Ultra, Team, Enterprise) o key API Anthropic. Non tocca i crediti xAI.
- ⚠️ **Da chiedere al kick-off:** se l'evento dà un codice Cursor Pro/Premium con Grok Bot (altre build night SpaceXSI lo davano), vedi [../bots-imagine/grok-bots.md](../bots-imagine/grok-bots.md#accesso-prezzi-crediti).

## ⚠️ Non verificato

- Nessuna CLI eseguita: sintassi esatta di `--allow` in Grok Build e di `--max-turns` in Cursor; mapping dell'id `grok-build` (`grok models`).
- Se Cursor legga `CLAUDE.md` (non documentato: assumere di no).
- Supporto ACP lato client (Zed/JetBrains) per Grok Build: dedotto dal protocollo, non documentato da xAI.
- `claude mcp serve` citato a memoria, non riletto oggi.
- Id dei modelli Grok nel Cursor SDK e nella Cloud Agents API.
- Maturità di `@grok/agent-sdk` (rinominato da `@cursor/bdk` a ottobre 2026).

## Fonti

- Grok Build: https://docs.x.ai/build/overview.md, …/modes-and-commands.md, …/features/skills-plugins-marketplaces.md, …/features/project-rules.md, …/features/hooks.md, …/features/sessions.md, …/features/subagents.md, …/features/worktrees.md, …/features/background-tasks.md, …/features/dashboard.md, …/features/plan-mode.md, …/features/permissions.md, …/features/sandbox.md, …/settings.md, …/settings/reference.md, …/cli/reference.md, …/cli/headless-scripting.md, …/enterprise.md (tutte lette il 2026-11-03)
- https://github.com/xai-org/plugin-marketplace (README), https://api.github.com/orgs/xai-org/repos (elenco repo, nessuna GitHub Action)
- Cursor: https://cursor.com/docs/cli/overview.md, …/cli/headless.md, …/cli/acp.md, …/cli/reference/parameters.md, …/cli/reference/slash-commands.md, …/cli/reference/permissions.md, …/cli/reference/configuration.md, …/cli/github-actions.md, …/rules.md, …/skills.md, …/subagents.md, …/hooks.md, …/reference/third-party-hooks.md, …/plugins.md, …/mcp.md, …/models-and-pricing.md
- Cursor SDK: https://cursor.com/docs/sdk/typescript.md, https://cursor.com/docs/sdk/python.md; Agent SDK: https://cursor.com/docs/agent-sdk.md, https://cursor.com/docs/agent-sdk/quickstart.md; npm `@grok/agent-sdk` (registry.npmjs.org, 0.6.0)
- Claude Code: https://code.claude.com/docs/en/headless.md, …/memory.md (sezione AGENTS.md), …/permission-modes.md, …/worktrees.md, …/scheduled-tasks.md, …/goal.md, …/workflows.md, …/agent-view.md, …/agent-sdk/overview.md
- ACP per Claude Code: https://zed.dev/blog/claude-code-via-acp
- xAI tool loop: https://docs.x.ai/developers/tools/advanced-usage.md
