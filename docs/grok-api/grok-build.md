# Grok Build: l'agente di coding di SpaceXSI (CLI/TUI, headless, ACP)

> **Verificato il:** 2026-11-03 su docs.x.ai/build/* e nei repo GitHub `xai-org/grok-build` e `xai-org/grok-build-plugin-cc`.
> ⚠️ Non ho installato né provato la CLI.

## Cos'è
Grok Build è un **coding agent** (in beta dal maggio 2026) che si usa in tre modi:
- **TUI** interattiva a schermo intero;
- **headless** in script o bot (`grok -p`);
- **ACP** (Agent Client Protocol, JSON-RPC su stdio) per integrarlo in IDE e app.

Concettualmente è l'equivalente di Claude Code. Il modello di default è `grok-4.7`. Il modello di coding dedicato è `grok-build-0.1`, disponibile anche via API (vedi [models.md](models.md)). **Grok 4.7 Fast** è disponibile solo dentro Grok Build e Cursor, non sull'API pubblica.

⚠️ Nella pagina Settings, il `config.toml` di esempio usa `default = "grok-build"` ("recommended for coding / agent sessions"), mentre la pagina Grok 4.7 dice che il default è `grok-4.7`. Il mapping esatto dell'id `grok-build` dentro la CLI non è chiaro: si verifica con `grok models`.

## Installazione e login
```bash
curl -fsSL https://x.ai/cli/install.sh | bash          # macOS/Linux
# Windows: irm https://x.ai/cli/install.ps1 | iex
cd your-project && grok                                # al primo avvio apre il browser per il login
export XAI_API_KEY="xai-..." && grok                   # alternativa senza browser
grok login --device-auth                               # login con device code (headless/remoto)
```

## Headless (utile per automatizzare da script o da Claude Code)
```bash
grok -p "Explain this codebase"
grok -p "List TODO comments" --output-format json            # plain | json | streaming-json
grok --no-auto-update -p "..." -m grok-4.7 --cwd ./robot-app --always-approve
```
Flag principali:
- `-p/--single`, `-m/--model`, `--effort <LEVEL>`;
- `-s/--session-id`, `-r/--resume`, `-c/--continue` (le sessioni stanno in `~/.grok/sessions`);
- `--always-approve` (alias `--yolo`), `--allow`/`--deny`, `--sandbox <PROFILE>`;
- `--rules <TEXT>`, `--system-prompt-override`, `--max-turns`, `--tools` / `--disallowed-tools`, `-w/--worktree`.

Accetta anche alcuni flag di Claude Code come alias: `--allowedTools`, `--disallowedTools`, `--append-system-prompt`, `--system-prompt`, `--dangerously-skip-permissions`.

## Sottocomandi utili
`grok models`, `grok inspect [--json]`, `grok mcp add|list|remove|doctor`, `grok sessions list|search|delete`, `grok export <id>`, `grok import` (**importa sessioni da Claude Code**), `grok agent stdio` (ACP), `grok worktree …`, `grok dashboard`, `grok update`.

## Compatibilità con l'ecosistema Claude Code
- Legge le **regole di progetto** da `AGENTS.md`, `CLAUDE.md`, `CLAUDE.local.md` e `.grok/rules/*.md` (legge anche `.claude/rules/` e `.cursor/rules/`).
- Carica le **configurazioni MCP** da `~/.claude.json`, `.cursor/mcp.json` e `.mcp.json`, oltre che da `~/.grok/config.toml`.
- Ha skills, plugin e marketplace, hooks, plan mode, subagents e permessi/sandbox.

## Config: `~/.grok/config.toml` (estratto dai docs)
```toml
[models]
default = "grok-build"
web_search = "grok-4.7"

[model."grok-4.7"]
model = "grok-4.7"
base_url = "https://api.x.ai/v1"
env_key = "XAI_API_KEY"
api_backend = "responses"        # chat_completions | responses | messages
temperature = 0.7
top_p = 0.95
context_window = 500000

[mcp_servers.xai-docs]
url = "https://docs.x.ai/api/mcp"
```

## Plugin ufficiale per Claude Code: `xai-org/grok-build-plugin-cc`
Fa da ponte tra Claude Code e la CLI `grok`, per avere un secondo agente che fa review o a cui delegare task.
```text
/plugin marketplace add xai-org/grok-build-plugin-cc
/plugin install grok-build@xai-grok-build
/reload-plugins
/grok-build:check            # verifica Node ≥ 18.18, `grok` nel PATH e il login (`grok models`)
/grok-build:review --wait    # review read-only dello stato git
/grok-build:critique --wait
/grok-build:delegate investigate the flaky test in auth
/grok-build:import           # importa la sessione Claude Code corrente in Grok
```
Review e critique girano con `--agent explore --sandbox read-only --always-approve` (verificato sul codice del plugin v0.2.1 il 2026-11-03). ⚠️ Il subagent `delegate` usa `--write --always-approve` **senza sandbox** ed è marcato "Proactively use": non usarlo sul portatile collegato all'hardware. Dettagli in [../claude-vs-grok/claude-code-workflow.md](../claude-vs-grok/claude-code-workflow.md).

## Costi e piani
- Via **API key**: si paga a consumo con le tariffe API del modello scelto.
- Via **account / "The X Subscription"**: piani Free ($0, uso limitato), Plus ($8/mese), Premium ($30), Super ($100), Ultra ($200). Grok e Cursor condividono un pool d'uso settimanale. ⚠️ Non ho verificato i limiti esatti del free tier di Grok Build. Grok 4.7 Fast **non** è incluso nel free tier.

## Serve per l'hackathon?
Il nostro coding agent è Claude Code, quindi Grok Build è **opzionale**. Può servire per:
1. ottenere una review "di parte" da Grok tramite il plugin;
2. mostrare ai giudici l'integrazione con l'ecosistema SpaceXSI;
3. usare `grok -p --output-format json` come agente headless dentro una demo.

## Fonti
- https://docs.x.ai/build/overview.md
- https://docs.x.ai/build/cli/headless-scripting.md
- https://docs.x.ai/build/cli/reference.md
- https://docs.x.ai/build/settings.md
- https://docs.x.ai/build/features/mcp-servers.md
- https://docs.x.ai/build/features/project-rules.md
- https://docs.x.ai/developers/grok-4-7.md (sezione "Fast variant")
- https://docs.x.ai/x-subscription/pricing.md
- https://github.com/xai-org/grok-build
- https://github.com/xai-org/grok-build-plugin-cc
