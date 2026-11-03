# Grok Build (coding agent SpaceXAI)

> Verificato il **2026-11-03** su docs.x.ai/build/* (pagine `.md`), repo GitHub `xai-org/grok-build` (README e user guide in `crates/codegen/xai-grok-pager/docs/user-guide/`), installer `https://x.ai/cli/install.sh`, docs.x.ai/developers/pricing e models.
> ⚠️ = non verificato. **CLI non installata né eseguita** in questa ricerca.

## TL;DR

- **Grok Build = CLI/TUI `grok`**, coding agent da terminale (stile Claude Code / Codex): capisce il repo, modifica file, esegue comandi shell, cerca sul web, task in background, subagent, MCP, skill, plugin, hook, sandbox, worktree.
- Tre modalità: **TUI interattiva**, **headless** (`grok -p "..."` con output `json`/`streaming-json`) per script/bot/CI, **ACP** (`grok agent stdio`, JSON-RPC su stdin/stdout) per integrarlo in editor/app.
- **Open source** (Apache-2.0, Rust) su https://github.com/xai-org/grok-build (repo creato 14/07/2026, ~27.7k stelle al 2026-11-03).
- Auth: login browser (OAuth `auth.x.ai`, account grok.com), `--device-auth` per macchine headless, oppure **`XAI_API_KEY`** (billing a token sulla API → si possono usare i crediti API dell'hackathon).
- Modello di default consigliato nelle docs: `grok-build` (API: `grok-build-0.1`, $1/$2 per 1M token in/out, 256k contesto); disponibile anche `grok-4.7` e qualsiasi modello custom OpenAI-compatibile.
- Ha comandi **`/imagine`** e **`/imagine-video`** integrati, `/loop` per prompt ricorrenti, `/deep-research`.
- **Utile per "far scrivere codice a un robot dal vivo"**: un processo (o un altro agente) lancia `grok -p "<istruzione>" --output-format json` nella cartella del firmware/SDK del robot e legge il risultato.

## Installazione

```bash
curl -fsSL https://x.ai/cli/install.sh | bash      # macOS / Linux / Git Bash
irm https://x.ai/cli/install.ps1 | iex             # Windows PowerShell
grok --version
```
L'installer supporta macOS e Linux su **x86_64 e aarch64** (letto nello script) → ⚠️ potenzialmente anche su Raspberry Pi 64-bit, non testato. Env utili dell'installer: `GROK_CHANNEL` (`stable|alpha|enterprise`), `GROK_BIN_DIR`.

## Autenticazione
| Metodo | Come |
|---|---|
| Browser (default) | `grok` al primo avvio, o `grok login` → OAuth su `auth.x.ai`; credenziali in `~/.grok/auth.json` (0600) |
| Device code | `grok login --device-auth` (headless/remote, es. sul PC del robot via SSH) |
| API key | `export XAI_API_KEY="xai-..."`; usata come fallback se non c'è sessione. Se sei già loggato, il token di sessione ha precedenza (`grok logout` per forzare la key) |
| OIDC aziendale | `[grok_com_config.oidc]` in config |

## Prezzi / accesso
- Con **API key**: billing a token del modello usato (es. `grok-build-0.1`: input $1.00, cached $0.20, output $2.00 per 1M token sotto 200k prompt; `grok-4.7`: $2 / $0.50 / $6).
- Con **login grok.com**: rientra negli abbonamenti (The X Subscription / SuperGrok). Le docs ufficiali citano un **"Grok Build's free tier"** (che non include Grok 4.7 Fast). ⚠️ Limiti del free tier non pubblicati; fonti terze sono in disaccordo sulla sua esistenza in passato.
- **Grok 4.7 Fast** (stesso modello su infrastruttura più veloce, 2x prezzo) è disponibile **solo in Cursor e Grok Build**, non sull'API pubblica.

## Uso interattivo (TUI)
```bash
cd your-project
grok
```
Prompt d'esempio dalle docs: `Explain this repo.`, `@src/main.rs Walk me through this file.`

Comandi slash utili: `/model <name>`, `/effort`, `/plan`, `/auto`, `/always-approve`, `/compact`, `/rewind`, `/loop [interval] <prompt>`, `/imagine <prompt>`, `/imagine-video <prompt>`, `/tasks`, `/deep-research <query>`, `/share`, `/export`, `/usage`.
Modi (Shift+Tab): Normal (ask) → Plan → Auto (classifier) → Always-approve.

Supporta `AGENTS.md` (project rules), skill, plugin + marketplace (`xai-org/plugin-marketplace`), hook, subagent, worktree, sandbox profiles, memoria cross-sessione (sperimentale), dashboard agenti (`grok dashboard`). Importa sessioni da Claude Code (`grok import`) e accetta alias dei flag di Claude Code (`--allowedTools`, `--append-system-prompt`, `--dangerously-skip-permissions`, ...).

## Headless (script, bot, CI) — il pezzo utile per la demo

```bash
grok -p "Explain this codebase"
grok -p "List TODO comments" --output-format json
grok -p "Explain the architecture" --output-format streaming-json
grok --no-auto-update -p "..."     # consigliato in automazione
```

Flag principali: `-p/--single`, `--prompt-file`, `--prompt-json`, `-m/--model`, `-s/--session-id <UUID>` (nuova sessione), `-r/--resume`, `-c/--continue`, `--cwd`, `--output-format plain|json|streaming-json|streaming-messages-json`, `--always-approve`/`--yolo`, `--allow <RULE>`, `--deny <RULE>`, `--tools`/`--disallowed-tools` (es. `run_terminal_cmd`, `read_file`, `grep`, `web_search`, `search_replace`), `--max-turns`, `--effort`, `--sandbox <PROFILE>`, `--rules <TEXT>`.

Output `json` (un oggetto a fine run): `text`, `stopReason` (`end_turn`, `max_tokens`, ...), `sessionId`, `requestId`, `num_turns`, `usage` (token), `modelUsage`, costo.

Sessioni headless in `~/.grok/sessions`; con `--session-id`/`--resume` si può fare una conversazione multi-step con lo stesso agente.

### ACP (integrazione in app/editor)
`grok agent stdio` espone un agente **Agent Client Protocol** (JSON-RPC su stdio): `initialize` → `authenticate` (`xai.api_key` o `cached_token`) → `session/new` (con `cwd`, `mcpServers`) → `session/prompt`; il testo arriva come notifiche `session/update` (`agent_message_chunk`). Esempio Node completo nella pagina "Headless & Scripting".

## MCP in Grok Build
```bash
grok mcp add filesystem -- npx -y @modelcontextprotocol/server-filesystem /path/to/dir
grok mcp add --transport http api https://mcp.example.com/mcp --header "Authorization: Bearer ${API_TOKEN}"
grok mcp list ; grok mcp doctor <name>
```
Oppure in `~/.grok/config.toml` sotto `[mcp_servers.<nome>]` (`command`/`args`/`env` o `url`/`headers`, `${VAR}` espanse). Tool esposti come `<server>__<tool>`.

### X MCP in Grok Build
Da docs.x.com (verbatim):
```toml
# ~/.grok/config.toml
[mcp_servers.xapi]
command = "npx"
args = ["-y", "@xdevplatform/xurl", "mcp", "https://api.x.com/mcp"]
enabled = true
startup_timeout_sec = 300

[mcp_servers.xapi.env]
CLIENT_ID = "YOUR_X_APP_CLIENT_ID"
CLIENT_SECRET = "YOUR_X_APP_CLIENT_SECRET"
```

## Permessi (importante se agisce su hardware)
- Regole in config:
  ```toml
  [permission]
  rules = [
    { action = "allow", tool = "bash", pattern = "git *" },
    { action = "allow", tool = "read" },
    { action = "deny",  tool = "bash", pattern = "rm -rf *" },
  ]
  ```
- `--allow` / `--deny` accettano gli stessi pattern per invocazione; filtri: `Bash`, `Edit`, `Read`, `Grep`, `MCPTool`, `WebFetch`, `WebSearch`. `deny` vince sempre. ⚠️ La sintassi esatta di `--allow` da CLI (es. `Bash(pytest*)` vs altro) non è mostrata con esempi: verificare con `grok --help`.
- `--always-approve` salta i prompt (deny e hook restano attivi). Per un robot fisico: preferire allowlist strette + `--sandbox`.

## Pattern "robot che si fa scrivere il codice dal vivo"
1. Repo con l'SDK del robot (es. `robot_sdk.py`) + `AGENTS.md` con regole di sicurezza (velocità max, comandi vietati, "esegui sempre i test in simulazione prima").
2. Input vocale (Grok Voice STT) o testo → `grok -p "<richiesta>" --cwd robot/ --output-format json --max-turns 20` con allowlist limitata.
3. Il risultato (`text` + file modificati) viene validato (test/simulatore) e poi eseguito sul robot.
4. In alternativa, **`/loop`** o un processo esterno per iterare.

Snippet: [code-samples.md](code-samples.md#9-grok-build-headless-da-python).

## Extra
- Plugin Claude Code ufficiale **`xai-org/grok-build-plugin-cc`**: delega review/rescue e trasferimento sessioni a Grok Build dalla nostra installazione Claude Code (`/plugin marketplace add xai-org/grok-build-plugin-cc`, poi `/plugin install grok-build@xai-grok-build`). Richiede `grok` loggato.
- Changelog: https://x.ai/build/changelog (⚠️ non letto: x.ai blocca le richieste non-browser con Cloudflare).

## Fonti
- https://docs.x.ai/build/overview
- https://docs.x.ai/build/cli/headless-scripting
- https://docs.x.ai/build/cli/reference
- https://docs.x.ai/build/modes-and-commands
- https://docs.x.ai/build/features/mcp-servers
- https://docs.x.ai/build/features/permissions
- https://docs.x.ai/developers/models/grok-build-0.1
- https://docs.x.ai/developers/pricing (sezione "Grok 4.7 Fast pricing (Cursor and Grok Build only)")
- https://docs.x.ai/developers/release-notes (maggio 2026: "Grok Build is now available in beta", "Grok Build 0.1")
- https://github.com/xai-org/grok-build (README; user guide `02-authentication.md`, `14-headless-mode.md`)
- https://x.ai/cli/install.sh
- https://github.com/xai-org/grok-build-plugin-cc
- https://docs.x.com/tools/mcp (config X MCP per Grok Build)
