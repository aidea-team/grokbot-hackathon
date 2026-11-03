# Cloud, automazione, app e MCP: Anthropic ↔ SpaceXSI (Grok Bot, Cursor, Grok)

> **Verificato il:** 2026-11-03. Lato Grok, la fonte primaria è [../bots-imagine/grok-bots.md](../bots-imagine/grok-bots.md). Oggi ho riletto `docs.x.ai/grok-bot/*.md` (computer-and-apps, shared-bots, skills-routines, files-and-results, inference-hooks, faq) e `docs.x.ai/grok/connectors*.md`. Lato Cursor ho letto cloud-agent, automations, Cloud Agents API v1, Bugbot, integrazioni Slack/GitHub/Linear, browser, self-hosted "My Machines", pricing. Lato Anthropic ho letto `code.claude.com/docs` (scheduled tasks, ex routines; cloud sessions; Remote Control; Chrome; computer use; Projects; Artifacts; channels; cloud environments; Code Review), `claude.com/docs/claude-tag` e `platform.claude.com/docs/en/managed-agents/*`.
> Niente è stato provato dal vivo. ⚠️ = non verificato o dedotto.
> Dev tools e Agent SDK sono in [dev-tools-and-agents.md](dev-tools-and-agents.md). Le API Messages ↔ Responses sono in [api-platform.md](api-platform.md), il workflow pratico in [claude-code-workflow.md](claude-code-workflow.md).

## In breve

- **Lato SpaceXSI, il "cloud agentico" ha due facce, entrambe di Cursor.** **Cursor Cloud Agents** (VM per repo, API REST `api.cursor.com/v1/agents`, SDK, Automations) è l'equivalente di cloud sessions + Managed Agents. **Grok Bot** (teammate con computer cloud persistente, routine, connettori) è l'equivalente di Claude Tag + Cowork + scheduled tasks, ma **senza API per pilotarlo**.
- **Routine.** Claude "scheduled tasks" (ex routines), Grok Bot routines e Cursor Automations si somigliano molto: schedule, webhook con bearer, eventi GitHub e Slack. Differenza chiave: **il webhook di Claude restituisce l'URL della sessione**, quello di Grok Bot risponde solo `200` (il risultato arriva in chat).
- **MCP è il ponte universale.** Un solo server MCP **Streamable HTTP** dietro un tunnel pubblico è usabile da Claude Code, Grok Build, Cursor, Responses API (tool `mcp`), grok.com Connectors (Custom) e Grok Bot. Da xAI le connessioni partono dai *loro* server, quindi serve un URL HTTPS pubblico. Ricetta [in fondo](#ricetta-esporre-lhardware-come-mcp-server-per-tutti).
- **Browser.** Claude in Chrome **non funziona in WSL**, che è il nostro ambiente, e il computer use della CLI è solo per macOS. Per una demo browser usare il browser del computer cloud di Grok Bot o il tool Browser di Cursor.

## Tabella di corrispondenza

| Anthropic | SpaceXSI / Cursor (più simile) | Grado di somiglianza |
|---|---|---|
| **Claude Managed Agents** (API beta `managed-agents-2026-04-01`: agent + environment + session, sandbox gestita o self-hosted, vaults, MCP, skills, multiagent) | **Cursor Cloud Agents API v1** (`POST api.cursor.com/v1/agents`, runs, stream, artifacts, `mcpServers`) + **Cursor SDK** runtime `cloud` + **`@grok/agent-sdk`** (deployed agents) | Alto per le sessioni su VM; Cursor è orientato alle repo/PR (ma ammette "no-repo agents") |
| Managed Agents **scheduled deployments** (cron) | **Cursor Automations** (cron) / `@grok/agent-sdk` schedules | Alto |
| **Scheduled tasks cloud** (ex routines, `/schedule`, claude.ai/code/routines: trigger schedule / API `/fire` / GitHub) | **Grok Bot routines** (schedule, webhook, email, Slack, GitHub, Linear, Sentry, PagerDuty) e **Cursor Automations** (cron, GitHub/GitLab/Bitbucket, Slack, webhook, Linear, PagerDuty) | Alto |
| Desktop scheduled tasks / `/loop` | `/loop` di Grok Build (locale) | Alto (vedi [dev-tools-and-agents.md](dev-tools-and-agents.md)) |
| **Cloud sessions** (claude.ai/code, `claude --cloud`, `--teleport`, app mobile) | **Cursor Cloud Agents** (cursor.com/agents, app iOS, `&` dalla CLI per l'handoff al cloud) | Alto |
| **Remote Control** (sessione locale pilotata da web/telefono) | **Cursor "My Machines"** (il loop gira nel cloud Cursor, i tool sul tuo PC via `agent worker start`); **Grok Bot "Execution on this computer"** | Medio: il loop sta nel cloud, non in locale |
| **Projects in Claude Code** (thread paralleli cloud con memoria condivisa) | Grok Bot (più Bot in parallelo, group chat, handoff); Cursor Agents Window | Medio |
| **Claude in Chrome** / **computer use** (CLI solo macOS, Desktop, API tool) | **Computer cloud di Grok Bot** (browser persistente, "Teach a task", take-over); **Cursor**: tool Browser nell'agente, computer use + remote desktop nei Cloud Agents | Alto come capacità. Ma la Grok API **non ha un tool computer-use** ⚠️ (non presente nell'elenco tool di docs.x.ai) |
| **Claude Tag** (Claude in Slack: `@Claude`, sandbox effimera, Team/Enterprise, public beta) | **Grok Bot condivisi** in Slack + trigger Slack; **`@cursor` in Slack** (Cloud Agent) | Alto |
| **claude-code-action** / GitHub app / **Code Review** (Team/Enterprise) | **Bugbot** (Premium+), `@cursor` su PR/issue, Automations con trigger GitHub; Grok Bot con trigger GitHub | Alto (Bugbot ≈ Code Review) |
| **Channels** (Telegram/Discord/iMessage → sessione aperta) | Grok Bot via X Chat, email `@mail.grokbot.com`, Slack; tag @bot su X (**non dall'UE**) | Medio |
| **Claude.ai Projects** | Grok **Projects** su grok.com ⚠️ (citati solo in una FAQ: "missing features like Projects") | ⚠️ |
| **Artifacts** (claude.ai e Claude Code) | Grok Bot **Pages** (report e dashboard nella Library, rollout); Cursor **Canvases** | Medio-alto |
| **Memory** di claude.ai | Memoria per-Bot di Grok Bot; memoria dell'app Grok ⚠️ (solo fonti terze) | Medio |
| **Connettori** claude.ai (inclusi i custom remote MCP) | **grok.com/connectors**: built-in (Gmail/Calendar, Drive, OneDrive, Outlook, Teams, SharePoint, Salesforce), catalogo OAuth, **Custom MCP** (URL pubblico) | Alto |
| **Research** | DeepSearch nell'app Grok ⚠️; `/deep-research` in Grok Build; Grok Bot | Medio |
| **Cowork** / Claude Desktop (agente sui tuoi file) | **Grok Bot** desktop (macOS/Windows/Linux) + mobile | Medio-alto |
| Voice mode dell'app Claude | Grok Voice (app) e voice chat con i Bot | Alto |
| — | **Companions** (solo app iOS) | Nessun equivalente |

## Managed Agents ↔ Cursor Cloud Agents ↔ Grok Bot

| | Claude Managed Agents | Cursor Cloud Agents (API/SDK) | Grok Bot |
|---|---|---|---|
| Interfaccia | API REST (beta), Console, CLI | REST `api.cursor.com/v1/agents` (public beta, Basic/Bearer con `CURSOR_API_KEY`), SDK TS/Python, web, Slack, GitHub, Linear | **Solo app/chat** (desktop, mobile, Slack, X Chat, email). **Nessuna API per creare o pilotare i Bot** |
| Ambiente | Sandbox cloud Anthropic o self-hosted (workers) | VM isolata per agente con repo clonata, `.cursor/environment.json`/Dockerfile, snapshot; self-hosted (Team Pools, My Machines) | **Un** computer cloud persistente per account, condiviso dai Bot (`/workspace`, cookie, login) |
| Modelli | Claude | Modelli Cursor (Grok 4.7, Composer 2.5…) + terze parti | Scelta automatica ("no model picker") |
| Output | Event stream, file, outcome | Branch/PR, artifacts (screenshot, video, log), stream SSE dei run | Messaggi in chat, file, Pages, bozze email |
| Human in the loop | Permission policies | Hook, piano, PR | **Approvals + Auto Review** prima delle azioni esterne; Vault per le credenziali |
| Costo | Token API + ore di sandbox | Pool del piano (Premium+), oppure key | Pool X Subscription (Premium+) |

**Per l'hackathon:** l'unico modo di "chiamare un agente cloud SpaceXSI da codice e avere indietro il risultato" è la **Cursor Cloud Agents API** (o l'SDK), e richiede un piano Premium. Con Grok Bot il ritorno verso il nostro codice passa da un MCP server nostro, da un comando sul laptop o da un servizio che leggiamo (Sheets, Slack, file). Vedi [../bots-imagine/grok-bots.md](../bots-imagine/grok-bots.md#limiti-e-gotcha-rilevanti-per-la-demo).

## Routine e trigger: chi chiama chi

| | Claude scheduled tasks (cloud) | Grok Bot routine | Cursor Automations |
|---|---|---|---|
| Creazione | claude.ai/code/routines o `/schedule` nella CLI | Chiedendolo in chat al Bot | cursor.com/automations, Agents Window, skill `/automate`, template del Marketplace |
| Schedule | Preset (hourly, daily…) o one-off; **minimo 1 h** | Linguaggio naturale; **minimo 5 min** | Preset o **cron**; può partire in ritardo, mai in anticipo |
| Webhook | `POST https://api.anthropic.com/v1/claude_code/routines/<trig_id>/fire` con `Authorization: Bearer …`, `anthropic-beta: experimental-cc-routine-2026-04-01`, body `{"text": "..."}` | URL + key mostrati nella sezione **Webhook** della routine (desktop); `Authorization: Bearer <key>`; body JSON opzionale | URL privato + API key generati al salvataggio dell'automation |
| Risposta del webhook | JSON con `claude_code_session_id` e `claude_code_session_url` | **Solo `200` = run avviato**; il risultato va in chat | ⚠️ non dettagliata |
| Payload | Arriva avvolto in `<routine-fire-payload>` e trattato come **dato non fidato** (il prompt deve chiedere esplicitamente di usarlo) | Arriva al Bot insieme all'istruzione della routine | Contesto dell'evento |
| Altri trigger | Eventi GitHub | Slack, GitHub, Linear, Sentry, PagerDuty, email (con filtro mittente) | GitHub (il set più ricco: label, CI completed, review…), GitLab, Bitbucket, Slack (solo canali pubblici), Linear, PagerDuty |
| Limiti | Cap orari per task e per account (research preview) | 50 routine per Bot, 300 run/h totali, 200 run/h per routine, nessun retry | Fatturate come Cloud Agents; contesto sempre massimo |
| Identità | Il tuo account (commit e messaggi "come te") | Il tuo account; email inviate dalle routine restano **bozza** | "Run as Me" o service account (team) |

**Per l'hackathon.** Pattern "l'hardware sveglia un agente": l'evento del robot (caduta, pulsante, sensore) fa `POST` al webhook di una **routine Grok Bot**, che è la scelta visibile per la giuria. Snippet in [../bots-imagine/code-samples.md](../bots-imagine/code-samples.md#8-grok-bot-trigger-webhook-da-hardware). Se ci serve il risultato in modo sincrono, la routine non basta: si chiama la Responses API.

## Sessioni cloud e "lavora mentre il laptop è chiuso"

- **Claude:** cloud session (`claude --cloud`, `--teleport` per riportarla in locale), Remote Control (sessione locale vista da web/telefono), Projects (thread paralleli cloud), agent view (`claude agents`, locale).
- **Cursor:** Cloud Agents su cursor.com/agents e app iOS; dalla CLI basta mettere `&` davanti al messaggio per spostare la conversazione su un Cloud Agent. **My Machines** (`agent worker start`) è l'opposto di Remote Control: il loop gira nel cloud Cursor e i comandi sul tuo PC, con connessione solo in uscita. Utile se l'hardware è attaccato al laptop.
- **Grok Bot:** lavora 24/7 sul computer cloud; con **Execution on this computer** (Ask every time / Always allow / Never allow) lancia comandi sul laptop collegato all'hardware.
- **Grok Build:** nessuna modalità cloud documentata (c'è `/share` via URL della sessione). Per "cloud" si usa Cursor.

## Browser e computer use

| | Dove gira | Note per noi |
|---|---|---|
| Claude in Chrome (estensione + Claude Code/VS Code) | Chrome/Edge locale, con i tuoi login | **Non supportato in WSL** (dice la doc): sul nostro setup non va |
| Computer use della CLI di Claude Code | Il tuo Mac | Solo macOS, Pro/Max/Ultra, non funziona in `-p` |
| Computer use tool della Messages API | La tua VM | Nessun equivalente nella Grok API ⚠️ |
| **Browser del computer cloud di Grok Bot** | Cloud Cursor, sessioni persistenti condivise fra Bot | Un Bot fa un computer-use task alla volta. Si guarda e si prende il controllo dal pannello. "Teach a task" registra fino a 10 min di dimostrazione e ne fa una skill. Si può far uscire il traffico dal proprio IP ("Route traffic through this computer") |
| **Cursor Browser** (agente IDE/CLI) | Browser integrato | Screenshot, console e network; nessun setup |
| **Cursor Cloud Agents computer use** | VM con desktop | Remote desktop per prendere il controllo; `--computer-use` sui worker self-hosted |

## Integrazioni: Slack, GitHub, Linear

- **Slack.** *Claude Tag* (Team/Enterprise, public beta): `@Claude` nei canali, sandbox effimera, connettori impostati dall'admin, spesa per uso con un tetto. *Cursor*: app Slack, `@cursor <prompt>` avvia un Cloud Agent sulla repo (serve lo usage-based pricing). *Grok Bot*: Bot **condivisi** col team Cursor e usabili in Slack; routine con trigger "messaggio Slack"; il connettore Slack posta **come l'utente**.
- **GitHub.** *Claude*: `anthropics/claude-code-action`, GitHub app, **Code Review** gestita (Team/Enterprise), trigger GitHub nelle scheduled tasks. *Cursor*: **Bugbot** (review automatica a ogni push, `cursor review` / `bugbot run` nei commenti, link "Fix in Cursor/Web"), `@cursor` su PR/issue, Automations con trigger GitHub, CLI in GitHub Actions. *Grok Bot*: routine su eventi GitHub e app GitHub connessa. *Grok Build*: nessuna action ufficiale, solo `grok -p` in uno step.
- **Linear.** Cursor `@cursor` in Linear e trigger nelle Automations; Grok Bot con app Linear e trigger "issue creata"; Claude tramite connettori MCP o Claude Tag.
- **Per l'hackathon:** attivare **Bugbot** sulla repo GitHub del progetto (se abbiamo Premium) è un modo a costo zero di "usare Cursor" in modo visibile nella cronologia delle PR.

## App consumer: claude.ai ↔ grok.com / Grok Bot

| claude.ai | Grok | Stato della verifica |
|---|---|---|
| Projects (chat + file + istruzioni) | Projects su grok.com | ⚠️ Esistono (FAQ ufficiale: "missing features like Projects" su host non standard), dettagli non documentati |
| Artifacts | Grok Bot **Pages**; Cursor **Canvases** | Verificato (Pages in rollout, Grok Bot ≥ 0.60.0) |
| Memory | Memoria per-Bot (Grok Bot); memoria account dell'app ⚠️ | Grok Bot verificato, app no |
| Connettori + custom MCP | grok.com/connectors: built-in, catalogo, **Custom** (URL MCP pubblico; guida ufficiale al tunneling) | Verificato |
| Research | DeepSearch ⚠️, `/deep-research` (Grok Build) | Grok Build verificato |
| Cowork / Desktop | Grok Bot desktop | Verificato |
| — | Grok Imagine, Companions (solo iOS) | Verificato |

Per i piani: Grok Chat, Voice, Imagine e Build sono già su Plus ($8). **Grok Bot**, Cloud Agents, Automations e Bugbot partono da **Premium ($30/mese)**. Tutto attinge allo stesso pool settimanale; la Grok API è fatturata a parte. Fonte: cursor.com/docs/models-and-pricing; dettagli e piani legacy in [../bots-imagine/grok-bots.md](../bots-imagine/grok-bots.md#accesso-prezzi-crediti).

## MCP: chi è client e chi è server

| Prodotto | Ruolo | Trasporti | Dove gira la connessione |
|---|---|---|---|
| Claude Code | Client (stdio, HTTP, SSE). Anche server con `claude mcp serve` ⚠️ | stdio, HTTP | Dalla tua macchina: `localhost` va bene |
| Messages API MCP connector / Managed Agents | Client remoto | HTTP | Dai server Anthropic: serve un URL pubblico |
| claude.ai connettori custom | Client remoto | HTTP | Dai server Anthropic |
| **Responses API** tool `mcp` | Client remoto: `server_url`, `server_label`, `allowed_tools`, `authorization`, `headers`. **Niente `require_approval`** | Streamable HTTP, SSE | Dai server SpaceXSI: **URL HTTPS pubblico** |
| **Grok Voice** (speech-to-speech) | Client remoto ⚠️ (citato nella pagina Remote MCP, vedi [../grok-api/agentic-server-tools.md](../grok-api/agentic-server-tools.md#remote-mcp)) | come sopra | Server SpaceXSI |
| **grok.com Connectors → Custom** | Client remoto; **rifiuta `localhost` e IP privati** | Streamable HTTP, SSE (no SSE con i quick tunnel Cloudflare) | Server SpaceXSI |
| **Grok Bot** | Client: MCP per URL **o per comando sul suo computer cloud** (condiviso fra i Bot); reti private richiedono approvazione | URL, stdio sul computer cloud | Dal cloud Cursor |
| **Grok Build** | Client | stdio, HTTP (`grok mcp add --transport http …`) | Dalla tua macchina |
| **Cursor** (IDE, CLI, SDK, Cloud Agents) | Client | stdio, SSE, Streamable HTTP; OAuth | Locale; i Cloud Agents passano dal backend Cursor |
| Server MCP offerti da SpaceXSI/X | Server | HTTP | `https://docs.x.ai/api/mcp` (docs), `https://api.x.com/mcp` (X API via `xurl`, vedi [../bots-imagine/x-integration.md](../bots-imagine/x-integration.md)) |

### Ricetta: esporre l'hardware come MCP server per tutti

1. **Un server, un trasporto.** Usare un MCP server **Streamable HTTP** su `localhost:8000/mcp` sul laptop collegato al robot. Deve esporre **solo le primitive in whitelist**, con il validatore deterministico *dentro* il server, così vale per qualsiasi client. Il kill switch locale resta indipendente. Vedi [../hardware/llm-robot-architecture.md](../hardware/llm-robot-architecture.md).
   ```python
   # pip install "mcp[cli]"   ⚠️ skeleton not executed
   from mcp.server.fastmcp import FastMCP

   mcp = FastMCP("robot")

   @mcp.tool()
   def move(direction: str, meters: float) -> str:
       """Move the robot. direction: forward|back|left|right. meters: 0.1-1.0."""
       # validate(direction, meters) -> raise on violation; then call the hardware SDK
       return "ok"

   if __name__ == "__main__":
       mcp.run(transport="streamable-http")   # serves http://127.0.0.1:8000/mcp
   ```
2. **Raggiungibilità.** I client locali (Claude Code, Grok Build, Cursor CLI) usano direttamente `http://localhost:8000/mcp`. I client remoti (Responses API, Voice, grok.com, Grok Bot, Cursor Cloud Agents) richiedono un tunnel: `cloudflared tunnel --url http://localhost:8000` (Streamable HTTP ok) oppure `ngrok http 8000` (necessario se si usa SSE). L'URL del quick tunnel cambia a ogni riavvio, quindi va ri-registrato.
3. **Autenticazione.** Mettere un bearer token nel server o nel reverse proxy (⚠️ FastMCP non lo fa da solo senza configurare l'auth). Passarlo come `authorization` nella Responses API, come `--header "Authorization: Bearer …"` in Claude Code e Grok Build, e come `headers` in `.cursor/mcp.json`.
4. **Registrazione nei client:**
   - Claude Code: `claude mcp add --transport http robot https://<tunnel>/mcp --header "Authorization: Bearer $ROBOT_TOKEN"`
   - Grok Build: `grok mcp add --transport http robot https://<tunnel>/mcp --header "Authorization: Bearer ${ROBOT_TOKEN}"` (oppure `[mcp_servers.robot]` in `~/.grok/config.toml`; legge anche `.mcp.json`)
   - Cursor: `.cursor/mcp.json` → `{"mcpServers": {"robot": {"url": "https://<tunnel>/mcp", "headers": {"Authorization": "Bearer ..."}}}}`
   - Responses API: `{"type": "mcp", "server_url": "https://<tunnel>/mcp", "server_label": "robot", "allowed_tools": ["move"], "authorization": "<token>"}`. Codice in [../grok-api/agentic-server-tools.md](../grok-api/agentic-server-tools.md#remote-mcp)
   - grok.com: Connectors → New Connector → **Custom** → URL del tunnel
   - Grok Bot: in chat, *"Add the MCP server at https://<tunnel>/mcp"*. Aspettarsi una card di approvazione
5. **Latenza.** Con il remote MCP ogni tool call fa il giro SpaceXSI → tunnel → laptop. Per il controllo real-time (cane, drone) usare il **function calling locale** (il nostro codice esegue la `function_call`) e tenere l'MCP per Grok Bot o per la demo "stesso robot, più agenti". ⚠️ Latenza da misurare e loggare in JSONL.

## ⚠️ Non verificato

- Projects, memoria e DeepSearch dell'app Grok (solo menzioni indirette o fonti terze).
- Assenza di un tool computer-use nella Grok API (dedotta dall'elenco dei tool).
- Formato della risposta del webhook delle Cursor Automations.
- Remote MCP dentro Grok Voice (citazione indiretta, latenza ignota).
- `claude mcp serve` (a memoria) e lo skeleton FastMCP (non eseguito).
- Se l'evento fornisca un piano Cursor Premium o Grok Bot (da chiedere al kick-off).

## Fonti

- Grok Bot: https://docs.x.ai/grok-bot/computer-and-apps.md, …/shared-bots.md, …/skills-routines-and-automations.md, …/files-and-results.md, …/inference-hooks.md, …/faq.md, …/bots.md (lette il 2026-11-03); vedi anche le fonti in [../bots-imagine/grok-bots.md](../bots-imagine/grok-bots.md#fonti)
- Grok app: https://docs.x.ai/grok/overview.md, https://docs.x.ai/grok/faq.md, https://docs.x.ai/grok/connectors.md, https://docs.x.ai/grok/connectors/custom-mcp-tunneling.md
- Cursor: https://cursor.com/docs/cloud-agent.md, …/cloud-agent/automations.md, …/cloud-agent/api/endpoints.md, …/cloud-agent/capabilities.md, …/cloud-agent/self-hosted/my-machines.md, …/bugbot.md, …/integrations/slack.md, …/integrations/github.md, …/integrations/linear.md, …/agent/tools/browser.md, …/agent/tools/canvas.md, …/sdk/typescript.md, …/agent-sdk.md, …/models-and-pricing.md
- Claude Code: https://code.claude.com/docs/en/routines.md, …/scheduled-tasks.md, …/claude-code-on-the-web.md, …/remote-control.md, …/claude-projects.md, …/chrome.md, …/computer-use.md, …/artifacts.md, …/channels.md, …/cloud-environments.md, …/self-hosted-environments.md, …/code-review.md, …/github-actions.md
- Claude Tag: https://claude.com/docs/claude-tag
- Managed Agents: https://platform.claude.com/docs/en/managed-agents/overview.md, https://platform.claude.com/docs/en/managed-agents/scheduled-deployments.md
- Remote MCP xAI: https://docs.x.ai/developers/tools/remote-mcp.md (riassunta in [../grok-api/agentic-server-tools.md](../grok-api/agentic-server-tools.md))
