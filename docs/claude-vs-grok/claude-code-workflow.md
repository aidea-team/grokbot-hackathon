# Claude Code costruisce, Grok gira: workflow operativo per le 36 ore

> **Verificato il:** 2026-11-03, con Claude Code 2.1.317 su WSL2 (Ubuntu, Node 24, Python 3.12).
> **Metodo:** chiamate `curl` JSON-RPC al docs MCP di xAI; connessione al docs MCP da Claude Code headless; clone e lettura del codice di `xai-org/grok-build-plugin-cc` (commit `92b76a6`, 2026-08-04) e `claude plugin validate`; lettura delle pagine `.md` di docs.x.ai/build/* e di code.claude.com/docs; GitHub API per i server MCP di terze parti.
> **Non verificato:** la CLI `grok` non è installata su questa macchina e non avevamo una `XAI_API_KEY`, quindi plugin e `grok -p` **non sono stati eseguiti**. ⚠️ = non verificato o dedotto.
> Questo file copre il *come lavoriamo*. Il confronto API Claude ↔ API Grok e quello prodotto per prodotto (Claude Code / Agent SDK ↔ Grok Build / Grok Bot / Cursor) stanno negli altri file di `docs/claude-vs-grok/`.

## TL;DR

1. **Separazione netta:** Claude Code scrive il codice; il codice che gira in demo chiama **solo** Grok (API, Voice, Imagine, Bot). Niente `anthropic` in `src/`: lo controlla un test.
2. **Docs MCP di xAI: funziona senza chiavi** (Streamable HTTP, stateless, 4 tool). È già in [`.mcp.json`](../../.mcp.json): al primo `claude` nella repo va approvato.
3. **Una project skill pronta:** [`grok-api`](../../.claude/skills/grok-api/SKILL.md) (model id, endpoint, formati tool). Grok Build legge la stessa skill e lo stesso `CLAUDE.md`, senza configurazione aggiuntiva.
4. **Plugin `grok-build-plugin-cc`:** esiste, è ufficiale (Apache-2.0, v0.2.1) e il manifest supera la validazione. Ma è solo un ponte verso la CLI `grok`: senza `grok` installato e loggato non fa niente. Review e critique girano in sandbox read-only, mentre `delegate` scrive **senza sandbox e con auto-approve**: non va mai usato sul portatile collegato all'hardware.
5. **Delegare a Grok Build** ha senso per una second opinion prima del code freeze e per **un componente intero, isolato in un worktree**, che diventa la prova concreta per la giuria. Non ha senso per driver, validatore e codice sul percorso critico.
6. **Struttura mock-first** con contratti fissati nella prima ora (interfaccia `Driver`, tool JSON, schema degli eventi JSONL). Ogni run produce un JSONL, e da lì escono metriche, replay e demo di backup.
7. **In 3:** un owner per modulo, un worktree a testa (`claude -w <modulo>`), main sempre funzionante in mock e merge ogni 2 ore circa. Sessioni cloud (`claude --cloud`) solo per lavoro che non tocca hardware né chiavi.
8. **Visibilità SpaceXSI senza fingere:** Grok Bot con una routine vera (report automatico a fine run), Grok Build con una critique salvata più un componente, Imagine per gli asset con il loro registro di provenienza. Tutto finisce in `docs/evidence/`.

---

## 0. Il principio: build-time ≠ run-time

| | Build-time (noi, 36 ore) | Run-time (la demo) |
|---|---|---|
| Chi | Claude Code (principale), Grok Build (di supporto), Claude in Chrome per testare la dashboard | Grok API (`grok-4.7`, `grok-4.3`), Grok Voice, Imagine, Grok Bot, Grok Build headless (solo se fa parte dell'idea) |
| Chiavi | Account Claude; `grok login` per Grok Build | `XAI_API_KEY` da `.env` |
| Dove sta | `.claude/`, `.mcp.json`, `CLAUDE.md` | `src/`, `scripts/` |
| Regola | Claude può fare tutto, tranne lanciare `--real` sull'hardware | Nessuna dipendenza da Anthropic; tutto loggato in JSONL |

Guardia automatica da mettere subito in `tests/test_runtime_is_grok_only.py`:
```python
import pathlib, re

def test_no_anthropic_in_runtime():
    bad = [p for p in pathlib.Path("src").rglob("*.py")
           if re.search(r"\banthropic\b|claude-(opus|sonnet|haiku)", p.read_text(encoding="utf-8"))]
    assert not bad, f"Runtime must call Grok only: {bad}"
```

---

## 1. Setup di Claude Code per lavorare su Grok

### 1.1 Docs MCP di xAI ✅ verificato

- Endpoint `https://docs.x.ai/api/mcp`, transport **Streamable HTTP**, stateless, **nessuna autenticazione** (dalla pagina ufficiale [developers/docs-mcp](https://docs.x.ai/developers/docs-mcp.md)).
- Test fatto il 2026-11-03 con `curl`:
  - `initialize` → HTTP 200, `serverInfo: {"name":"xai-docs-mcp","version":"1.0.0"}`, protocollo `2025-06-18`, capability `tools.listChanged`;
  - `tools/list` → 4 tool: `list_doc_pages`, `get_doc_page(slug, language?)`, `search_docs(query, max_results 1–20)`, `get_llms_txt(language?)`;
  - `tools/call search_docs` e `list_doc_pages` restituiscono dati reali, circa 230 slug tra `developers/*`, `build/*`, `grok-bot/*`, `x-subscription/*`.
- Test fatto da **Claude Code** (`claude -p --mcp-config .mcp.json --strict-mcp-config`): il tool `mcp__xai-docs__search_docs` viene chiamato e risponde. ✅
- **Già configurato** in [`.mcp.json`](../../.mcp.json) (scope project, condiviso con il team):
  ```json
  { "mcpServers": { "xai-docs": { "type": "http", "url": "https://docs.x.ai/api/mcp" } } }
  ```
  Al primo `claude` nella repo, Claude Code chiede di approvare i server di `.mcp.json`. Prima dell'approvazione `claude mcp get xai-docs` mostra `⏸ Pending approval` (è lo stato che ho visto io). In alternativa, per un singolo utente: `claude mcp add --transport http xai-docs https://docs.x.ai/api/mcp`.
  Attenzione al formato: in `.mcp.json` il campo `"type": "http"` è obbligatorio. Senza, Claude Code tratta la voce come un server stdio e la scarta.
- Uso pratico: *"cerca in xai-docs come si passa `parallel_tool_calls` nella Responses API"* oppure *"leggi con get_doc_page `developers/tools/function-calling`, language python-openai"*. `get_doc_page` accetta `language` (`python-xai`, `python-openai`, `javascript-ai-sdk`, `curl`…) per ricevere solo gli esempi di quell'SDK.
- Perché conviene: i docs xAI cambiano di continuo (`grok-imagine-image-quality` è stato ritirato il 2026-11-02). Il modello che scrive codice deve leggere la pagina, non andare a memoria.
- Fallback senza MCP: `curl -sL https://docs.x.ai/<slug>.md`, oppure `https://docs.x.ai/llms.txt`.

### 1.2 Project skill (create in questa repo) ✅ caricate

| Skill | Quando si attiva | Cosa impone |
|---|---|---|
| [`.claude/skills/grok-api/SKILL.md`](../../.claude/skills/grok-api/SKILL.md) | Codice che chiama Grok API, Voice, Imagine o la CLI `grok` | Model id, endpoint, formato dei tool (Responses piatto vs Chat annidato vs Voice), log JSONL, divieto di usare l'SDK `anthropic` a runtime, tabella dei file `docs/` da leggere |

- Frontmatter secondo la [doc delle skill di Claude Code](https://code.claude.com/docs/en/skills.md): `name`, `description` (con il caso d'uso all'inizio) e `when_to_use`. Insieme, `description` e `when_to_use` restano sotto il limite di 1.536 caratteri. Verificato con `claude -p` che entrambe compaiono tra le skill disponibili. ✅
- **Grok Build legge `.claude/skills/`, `CLAUDE.md`, `.mcp.json` e gli hook di Claude Code** "with zero configuration" ([build/features/skills-plugins-marketplaces](https://docs.x.ai/build/features/skills-plugins-marketplaces.md)). Se un pezzo lo scrive Grok, valgono quindi le stesse regole. Si verifica con `grok inspect`. ⚠️ Non provato.
- Rinforzo opzionale per *security by design* (⚠️ da scrivere sul posto, non incluso qui): un hook `PreToolUse` su `Bash` in `.claude/settings.json` che blocca con exit 2 ogni comando contenente `--real`, così nessun agente può armare l'hardware da solo. Formato in [hooks-guide](https://code.claude.com/docs/en/hooks-guide.md).

### 1.3 Plugin ufficiale `xai-org/grok-build-plugin-cc` ✅ letto il codice, ⚠️ non eseguito

**Cos'è:** un marketplace di Claude Code (`xai-grok-build`) con un plugin (`grok-build` v0.2.1, Apache-2.0, solo stdlib Node). Delega alla CLI `grok` vera: non contiene modelli e non chiama l'API direttamente. Il README la definisce "Bridge Grok Build into Claude Code for review, critique, delegation, and session import". `claude plugin validate` passa sia sul marketplace sia sul plugin. ✅

**Requisiti:** Node ≥ 18.18, `grok` nel `PATH` (o `GROK_BINARY`), **CLI loggata**: deve funzionare `grok models`. Il plugin non legge `XAI_API_KEY`. È la CLI che si autentica, con il login via browser, con `grok login --device-auth` oppure con `XAI_API_KEY` nell'ambiente.

**Installazione:**
```text
/plugin marketplace add xai-org/grok-build-plugin-cc
/plugin install grok-build@xai-grok-build
/reload-plugins
/grok-build:check
```
Da shell: `claude plugin marketplace add xai-org/grok-build-plugin-cc && claude plugin install grok-build@xai-grok-build`.

**Cosa installa:** 8 comandi, 1 subagent, 2 skill interne e 2 hook (`SessionStart` / `SessionEnd`, che esportano id e percorso del transcript della sessione Claude per `import`).

| Comando | Cosa esegue davvero (letto in `scripts/grok-bridge.mjs`) | Scrive file? |
|---|---|---|
| `/grok-build:check` | probe di Node e `grok`, più `grok models` | no |
| `/grok-build:review [--wait\|--background] [--base main] [--scope working-tree\|branch] [--model] [--effort low\|medium\|high]` | `grok -p <prompt con il diff> --agent explore --sandbox read-only --always-approve` | no (sandbox read-only) |
| `/grok-build:critique …` | come review, con un prompt che mette in discussione il design e un output JSON validato con `--json-schema` (verdict `approve`/`needs-attention`, findings con file e righe, confidence) | no |
| `/grok-build:delegate <task>` | subagent `grok-build:grok-delegate` → `grok -p <task> --always-approve` con `--write` di default, **senza sandbox** | **sì, senza limiti** |
| `/grok-build:import` | `grok import` della sessione Claude Code corrente, poi suggerisce `grok -r <id>` | no |
| `/grok-build:runs`, `:show`, `:stop` | gestione dei run in background (PID e log sotto `CLAUDE_PLUGIN_DATA`) | no |

Cose da sapere, viste nel codice:
- Il README dice che review usa `--permission-mode plan`. Il codice attuale (fix #12) usa invece `--always-approve` dentro `--sandbox read-only`, perché in headless "plan" senza approvatore si bloccava. Il confine di sicurezza è quindi la sandbox: Landlock su Linux, con la rete dei processi figli bloccata solo su Linux.
- **`delegate` con `--write`** = Grok esegue qualsiasi comando senza chiedere. Sul portatile collegato al cane o al drone può lanciare uno script che lo muove. Regola nostra: `delegate` **solo** in un worktree dedicato, su una macchina che non è collegata all'hardware, oppure in sola lettura ("read-only, don't edit").
- Il subagent `grok-delegate` ha la description *"Proactively use when Claude Code is stuck…"*, quindi Claude può delegare a Grok senza che glielo chiediamo. Per evitarlo, in `.claude/settings.local.json`: `{"permissions": {"deny": ["Agent(grok-build:grok-delegate)"]}}`. ⚠️ Che il deny funzioni anche con il nome namespaced del plugin non l'ho verificato: la doc mostra la sintassi `Agent(nome)`.
- Il plugin aggiunge hook a **tutte** le sessioni: se dà fastidio, `claude plugin disable grok-build`.

### 1.4 CLI Grok Build (serve per il plugin e per §2)

```bash
curl -fsSL https://x.ai/cli/install.sh | bash   # installa in ~/.grok/bin (binari `grok` e `agent`)
export PATH="$HOME/.grok/bin:$PATH"
grok login                    # browser; in WSL/SSH: grok login --device-auth; oppure export XAI_API_KEY=...
grok models && grok inspect   # inspect mostra regole, skill, MCP scoperti nella cartella
grok mcp doctor xai-docs      # il docs MCP viene letto anche da .mcp.json
```
- Dallo script di install (letto, non eseguito): crea anche un link `agent`, nome condiviso con la Cursor CLI. Se Federico ha la Cursor CLI installata, lo script lascia a lei `grok`/`agent` ("Left … to the Cursor CLI"). ⚠️ Va controllato con `which -a grok agent`.
- Account: free tier limitato, oppure `XAI_API_KEY` a consumo con i crediti dell'evento. ⚠️ Limiti del free tier non verificati.

### 1.5 Altri MCP utili per lo **sviluppo** (non per il runtime)

Stato preso dalla GitHub API il 2026-11-03. Nessuno è stato installato né provato. ⚠️

| Hardware | Server | Stato | Uso sensato |
|---|---|---|---|
| C64 / VICE | [`simen/vice-mcp`](https://github.com/simen/vice-mcp) (Node ≥ 18; `claude mcp add vice-mcp -- npx github:simen/vice-mcp`) | 1★, ultimo push 2025-12, senza licenza | Claude debugga il programma BASIC/ASM leggendo la memoria e lo schermo in VICE (binary monitor 6502). Ottimo in sviluppo. Il bridge runtime resta il nostro (`docs/hardware/retro-machines.md`) |
| Unitree Go2 | [`lpigeon/unitree-go2-mcp-server`](https://github.com/lpigeon/unitree-go2-mcp-server) | 88★, push 2026-06, Apache-2.0; richiede ROS2 + rosbridge | Solo come riferimento per i comandi. **Espone velocità raw**: non va mai messo tra Grok e il cane |
| Tello | [`0xKoda/drone-mcp`](https://github.com/0xKoda/drone-mcp) (SSE :3000, richiede root), [`showkeyjar/robot-mcp-server`](https://github.com/showkeyjar/robot-mcp-server) (Tello e Unitree, **mock mode**, MIT) | 26★ / 12★ | Il mock mode di `robot-mcp-server` può servire per i test; il resto vale solo come riferimento |
| MSFS | [`robin24/simconnect-mcp`](https://github.com/robin24/simconnect-mcp) (`uvx simconnect-mcp`, AGPL-3.0), [`shoff/MSFS-MCP`](https://github.com/shoff/MSFS-MCP) | push 2026-09 / 2026-07 | Solo su Windows, sul PC del simulatore. Utile a Claude per esplorare le SimVar dal vivo |
| X | X MCP ufficiale via `@xdevplatform/xurl` (1.4k★, MIT) | config in [docs/bots-imagine/grok-build.md](../bots-imagine/grok-build.md) | Se pubblichiamo su X; servono le chiavi dell'app X |
| Ultimate 64 | `martijn-devrev/ultimate64mcp` | il repo risulta **spostato** (301) | Cercare il nuovo URL solo se usiamo l'Ultimate 64 |

**Regola:** un MCP di terze parti verso l'hardware salta il nostro validatore. In sviluppo va bene, con l'hardware fermo o in simulatore e dopo averne letto il codice. Nel percorso Grok → hardware passa solo il nostro executor.

---

## 2. Delegare da Claude Code a Grok

### 2.1 I quattro modi

| Modo | Comando | Quando |
|---|---|---|
| Plugin | `/grok-build:critique --wait`, `/grok-build:review --base main` | Second opinion su un diff, con output salvabile |
| Headless diretto | `grok --no-auto-update -p "…" --output-format json --sandbox read-only --always-approve --cwd .` lanciato dal Bash di Claude | Quando serve controllare prompt, modello e output, e salvare un artefatto |
| API `grok-build-0.1` | uno script Python che chiama la Responses API | Generare un artefatto *dentro il prodotto* (es. BASIC V2 per il C64, una coreografia), non per programmare la repo |
| ACP | `grok agent stdio` (JSON-RPC su stdio) | Solo se l'idea mette un agente di coding nella demo. Esempio completo su [build/cli/headless-scripting](https://docs.x.ai/build/cli/headless-scripting.md) |

Flag headless verificati sui docs: `-p`, `-m`, `--effort`, `-s/--session-id`, `-r`, `-c`, `--cwd`, `--output-format plain|json|streaming-json`, `--always-approve`, `--sandbox off|workspace|read-only|strict|<custom>`, `--allow/--deny`, `--rules`, `--max-turns`, `--tools/--disallowed-tools`, `-w/--worktree`, `--no-auto-update`. `--agent explore`, `--permission-mode` e `--json-schema` compaiono nel codice del plugin ma non nella reference pubblica. ⚠️ La struttura dell'oggetto JSON finale di `--output-format json` non è documentata: guardarla al primo run.

### 2.2 Wrapper consigliato (da creare sul posto in `scripts/grok_second_opinion.sh`)

```bash
#!/usr/bin/env bash
# Usage: scripts/grok_second_opinion.sh "<question>" [path...]
# Read-only Grok Build pass; output archived as jury evidence.
set -euo pipefail
ts=$(date +%Y%m%d-%H%M%S); out="docs/evidence/grok-build/$ts.json"; mkdir -p "$(dirname "$out")"
grok --no-auto-update -p "$1. Files: ${*:2}. Answer with concrete findings (file:line) and a verdict." \
  --sandbox read-only --always-approve --max-turns 30 --output-format json --cwd "$PWD" | tee "$out"
```
Da Claude Code: *"lancia `scripts/grok_second_opinion.sh 'review the validator for unsafe edge cases' src/safety/`, poi dimmi su quali finding sei d'accordo e perché"*. Claude legge l'output, lo discute e poi decide cosa correggere. Così il confronto tra i due agenti resta documentato.

### 2.3 Quando ha senso e quando no

**Sì:**
- **Critique del validatore e del loop agente** prima del code freeze (gio ~13:00): è il codice da cui dipende la sicurezza, e un secondo modello di un'altra famiglia trova errori diversi.
- **Un componente intero e isolato** (in un worktree, con un'interfaccia già fissata), per esempio il programma BASIC del C64, la dashboard o lo script delle metriche. Serve come prova concreta per la giuria (§5) e non blocca nessuno.
- **Prompt engineering per Grok fatto da Grok:** fargli criticare il system prompt della persona vocale o le description dei tool. ⚠️ È un'ipotesi ragionevole, non misurata.
- **Lavoro in parallelo** mentre Claude è impegnato in un task lungo.

**No:**
- Driver, validatore, kill switch ed executor: un solo autore (umano + Claude), revisione deterministica con i test.
- Codice che deve toccare l'hardware o la LAN del museo, e `delegate --write` sulla macchina collegata.
- Due agenti sugli stessi file nello stesso momento: conflitti garantiti.
- Nelle ultime 3 ore: niente agenti nuovi, solo fix piccoli.

### 2.4 `grok-build-0.1` via API (per artefatti del prodotto)
```python
# Python, OpenAI SDK. Model and endpoint from docs/grok-api/models.md
import os, time
from openai import OpenAI
client = OpenAI(api_key=os.environ["XAI_API_KEY"], base_url="https://api.x.ai/v1")
t0 = time.perf_counter()
r = client.responses.create(model="grok-build-0.1",
    input=[{"role": "system", "content": "Write Commodore 64 BASIC V2 only. Lowercase keywords, lines step 10, max 80 chars."},
           {"role": "user", "content": "A program that prints a countdown and plays a beep."}])
print(r.output_text); print({"latency_ms": round((time.perf_counter() - t0) * 1000), "usage": r.usage})
```
⚠️ Non eseguito. Il loop di correzione (petcat → VICE → errore → di nuovo a Grok) è descritto in [docs/hardware/retro-machines.md](../hardware/retro-machines.md).

---

## 3. Struttura consigliata del progetto (vibecoding veloce, mock-first)

```
src/<progetto>/
  config.py            # read .env, model ids, limits: the only place with constants
  events.py            # JSONL logger (one file per run: runs/<run_id>.jsonl)
  drivers/
    base.py            # Protocol Driver: execute(name, args) / halt() / kill() / status()
    mock.py            # MockDriver with simulated state (pose, battery), default
    <hw>.py            # real driver (go2.py, tello.py, simconnect.py, vice.py…)
  safety/
    validator.py       # state machine, limits, geofence (from llm-robot-architecture.md §3)
    killswitch.py      # keyboard thread + local voice keyword, calls driver.halt()
  agent/
    tools.json         # whitelisted tools, flat Responses format
    loop.py            # Grok Responses loop, parallel_tool_calls=false, step limit
    prompts/           # versioned system prompts (it)
  voice/
    realtime.py        # Grok Voice session, based on docs/voice/examples/voice_agent_local.py
  replay.py            # replay a JSONL run without network or hardware
  dashboard/           # minimal live UI: tail of the JSONL, latency, state, big STOP button
scripts/
  demo.sh              # demo-mock | demo-real (with confirmation) | demo-replay
  metrics.py           # runs/*.jsonl → metrics/summary.json + table for README/slides
  smoke_api.py         # check key, models, TTFT (from docs/grok-api/gotchas.md)
  grok_second_opinion.sh
tests/
  test_validator.py    # adversarial cases: all must be rejected
  test_runtime_is_grok_only.py
  test_agent_mock.py   # agent loop with recorded Grok responses (fixtures), offline
fixtures/
  adversarial_prompts.jsonl   # "fly to the ceiling", "do a flip", "run toward people"…
  grok_responses/             # recorded responses for offline tests
runs/                  # JSONL of real runs (commit the ones used for metrics)
metrics/summary.json
docs/evidence/         # Grok Build critiques, Grok Bot reports, Imagine PROVENANCE, before/after video
```

### 3.1 Contratti da fissare nella prima ora (prima di aprire i worktree)
1. `Driver` Protocol, con le firme in `drivers/base.py`.
2. `agent/tools.json`, partendo da [llm-robot-architecture.md §2](../hardware/llm-robot-architecture.md).
3. Schema degli eventi JSONL, uno per riga:
   ```json
   {"ts":"2026-11-04T11:02:03.123Z","run_id":"r042","seq":17,"event":"tool_call",
    "source":"grok-4.3","tool":"dog_walk","args":{"vx":0.3,"seconds":2},
    "validator":{"ok":false,"reason":"outside geofence"},"latency_ms":412,"ttft_ms":180,
    "tokens_in":1830,"tokens_out":42,"cost_usd_ticks":null,"mode":"mock"}
   ```
   Tipi di `event`: `run_start`, `user_input` (testo o trascrizione), `llm_request`, `llm_response`, `tool_call`, `validator`, `exec_start`, `exec_done`, `killswitch`, `error`, `run_end`.
4. CLI comune: `--mock` (default) | `--real` | `--replay runs/r042.jsonl`.

### 3.2 Metriche da avere pronte per il pitch (tutte da `scripts/metrics.py`)
- Tasso di successo dei task (N run, quanti chiusi senza intervento umano).
- Comandi pericolosi bloccati su `fixtures/adversarial_prompts.jsonl` (es. "40/40 rifiutati"), con il dettaglio di cosa ha proposto Grok.
- Latenza p50/p95: voce → tool call, tool call → movimento, **kill switch → stop** (la più importante per la sicurezza).
- Costo per run (`cost_usd_ticks` dove c'è, altrimenti token × prezzo da [models.md](../grok-api/models.md)).
- Confronto tra modelli (`grok-4.3` none vs `grok-4.7` low) su latenza e successo: è il tipo di numero che un ingegnere SpaceXSI apprezza.

### 3.3 Replay e demo di backup
- **Replay:** `replay.py` rilegge un JSONL e ripropone gli eventi al `MockDriver` e alla dashboard con gli stessi tempi. Serve per test offline, per il debug e come **piano B dal vivo** se cadono Wi-Fi o hardware.
- **Fixture di risposte Grok:** registrare 5–10 risposte vere nelle prime ore e usarle in `test_agent_mock.py`, così i test girano senza key e senza rete (vale anche per le sessioni cloud di Claude Code).
- **Video:** il "prima" (mer 9–10) e la demo completa riuscita (gio entro le 14). Su WSL/Windows: Win+Alt+R (Xbox Game Bar) oppure OBS lato Windows per lo schermo; per il robot fisico un telefono su treppiede. Con la dashboard ripresa insieme al robot il video vale anche come prova. `recordings/`, `*.mp4` e `*.wav` sono già in `.gitignore`: caricare i video finali altrove e linkarli dal README.

---

## 4. Tre persone in parallelo con Claude Code (36 ore)

### 4.1 Ruoli (da adattare all'idea scelta)
| Chi | Modulo e worktree | Possiede anche |
|---|---|---|
| A, "safety owner" | `drivers/` + `safety/` (`claude -w hw`) | L'hardware fisico, il kill switch, l'unico che lancia `--real` |
| B | `agent/` + `voice/` (`claude -w agent`) | Prompt, scelta del modello, benchmark di latenza |
| C | `dashboard/`, `metrics.py`, `replay.py`, README, pitch, Grok Bot, Imagine (`claude -w ux`) | `docs/evidence/`, video, le slide |

### 4.2 Meccanica
- **Worktree:** `claude --worktree <nome>` crea `.claude/worktrees/<nome>/` sul branch `worktree-<nome>`. Per portarsi dietro `.env` serve un file `.worktreeinclude` con dentro `.env` ([doc](https://code.claude.com/docs/en/worktrees.md)). Va aggiunto `.claude/worktrees/` al `.gitignore`. Ognuno lavora sul suo portatile: i worktree servono soprattutto per far girare **più sessioni Claude sulla stessa macchina** (es. B ne tiene una sul loop agente e una sulla voce).
- **Main sempre funzionante in mock:** PR piccole, merge ogni ~2 ore, `pytest -q` verde prima del merge. I file condivisi (`tools.json`, schema degli eventi, `CLAUDE.md`) li tocca solo il loro owner.
- **Subagent dentro la sessione:** Explore per "trova nei docs come…" senza sporcare il contesto; subagent con `isolation: worktree` per due varianti in parallelo (es. due strategie di prompt), poi si sceglie con i numeri.
- **Sessioni cloud** (`claude --cloud "…"`, repo `aidea-team/grokbot-hackathon` su GitHub): adatte a test, `metrics.py`, README, refactor della dashboard e analisi dei JSONL committati. Non adatte a tutto quello che chiede LAN del museo, hardware o `XAI_API_KEY` (le chiavi non vanno nella sandbox cloud). Il risultato si riporta in locale con `--teleport`. ⚠️ Accesso cloud e piano dell'account da verificare stasera.
- **Remote Control** (`claude --remote-control`): Federico può seguire e guidare una sessione locale dal telefono mentre sta vicino al robot.
- **Agent teams / workflow multi-agente:** da evitare in hackathon. Il coordinamento costa più di quanto rende con 3 persone.
- **Grok Build in parallelo:** al massimo un componente alla volta, nel worktree di C (§2.3).

### 4.3 Ritmo (allineato al [piano delle 36 ore](../ideas/ideas.md))
| Quando | Obiettivo tecnico |
|---|---|
| Mer 9:00–11:00 | Giro hardware, idea scelta, **contratti (§3.1) su main**, smoke test API e Voice, video del prima |
| Mer entro le 13:00 | End-to-end brutto **in mock**: input → Grok → validatore → MockDriver → JSONL |
| Mer pomeriggio | Primo movimento reale a limiti ridotti (A); voce (B); dashboard live sul JSONL (C) |
| Mer notte | Strato "wow", fixture avversarie, `metrics.py`, routine Grok Bot |
| Gio 9:00 | Talk di Ralph Johnson: portare **un** problema concreto (es. la latenza misurata) |
| Gio 13:00 | **Code freeze** + `/grok-build:critique` sul diff dal kickoff, poi solo fix |
| Gio entro le 14:00 | 10 run della demo registrate in `runs/`, metriche finali, video di backup |
| Gio 16:00 | Pitch: video del prima → demo dal vivo → numeri → come l'abbiamo costruito |

---

## 5. Rendere visibili gli strumenti SpaceXSI, senza fingere

La giuria sono ingegneri SpaceXSI: si accorgono subito di un logo appiccicato. Conta solo quello che lascia un artefatto verificabile.

| Strumento | Uso reale che regge | Prova da mostrare |
|---|---|---|
| **Grok API / Voice** | Il runtime: planner, voce, vision | Dashboard live, JSONL, confronto tra modelli |
| **Grok Bot** | Una **routine con trigger webhook**: a fine run lo script fa `POST` del riassunto JSON (esito, latenze, rifiuti del validatore) e il Bot scrive il report del volo o della passeggiata, genera un'immagine con Imagine e prepara una bozza di post o email. Variante "monitor": una routine schedulata ogni 2 ore legge `metrics/summary.json` dalla repo (connettore GitHub) e tiene il **diario di bordo** dell'hackathon | La chat del Bot con i report, gli screenshot in `docs/evidence/grok-bot/` e i numeri del diario nel pitch. Dettagli e limiti in [grok-bots.md](../bots-imagine/grok-bots.md): `200` = run avviato, non concluso; il risultato arriva in chat e non nella risposta HTTP; 200 run/ora per routine |
| **Grok Build** | (1) Critique del validatore al code freeze, con i finding accettati e rifiutati; (2) **un componente** scritto da Grok Build nel suo worktree (commit con prefisso `[grok-build]`); (3) se l'idea è *Il trucco nuovo*, Grok Build headless **nella demo**, che scrive il codice del trucco nuovo poi validato in simulazione: è la versione più forte | `docs/evidence/grok-build/*.json`, `git log --grep "\[grok-build\]"`, il diff |
| **Imagine** | Asset del pitch (logo, poster) e, meglio ancora, nel prodotto (poster post-volo, cartolina del museo) | `docs/evidence/imagine/PROVENANCE.md` con prompt, modello, `request_id`, costo e data per ogni asset |
| **Cursor** | Solo se qualcuno lo usa davvero per un pezzo. Il confronto con gli altri strumenti sta negli altri file di questa cartella | — |
| **Docs MCP xAI** | Claude Code ha scritto il codice leggendo i docs ufficiali via MCP | `.mcp.json` nella repo |

Slide "Come l'abbiamo costruito", onesta: *"Codice scritto in vibecoding con Claude Code, collegato ai docs xAI via MCP; Grok Build ha fatto la critique della sicurezza (N finding, M accettati) e ha scritto il modulo X; Grok Bot genera il report di ogni run; tutto il runtime è Grok."* Una storia multi-agente vera vale più di una dichiarazione di esclusività.

---

## 6. Pre-flight della sera prima
Vedi [preflight-checklist.md](preflight-checklist.md).

## Cose da fare a mano (non le ho toccate)
- `.gitignore`: aggiungere `.claude/worktrees/` (e valutare `runs/*.jsonl` grandi).
- `CLAUDE.md`: aggiungere un rimando a questo file e alle due skill.
- Creare `.worktreeinclude` con `.env`, se useremo i worktree.

## Fonti
- Docs MCP: https://docs.x.ai/developers/docs-mcp.md (più i test `curl` del 2026-11-03 su https://docs.x.ai/api/mcp)
- Grok Build: https://docs.x.ai/build/cli/headless-scripting.md · https://docs.x.ai/build/cli/reference.md · https://docs.x.ai/build/features/skills-plugins-marketplaces.md · https://docs.x.ai/build/features/sandbox.md · https://docs.x.ai/build/features/permissions.md · installer https://x.ai/cli/install.sh (letto)
- Plugin: https://github.com/xai-org/grok-build-plugin-cc (README, `.claude-plugin/marketplace.json`, `plugins/grok-build/{commands,agents,skills,hooks,scripts}`, commit `92b76a6`)
- Claude Code: https://code.claude.com/docs/en/skills.md · https://code.claude.com/docs/en/mcp.md · https://code.claude.com/docs/en/worktrees.md · https://code.claude.com/docs/en/claude-code-on-the-web.md · https://code.claude.com/docs/en/sub-agents.md · https://code.claude.com/docs/en/hooks-guide.md
- MCP di terze parti: https://github.com/simen/vice-mcp · https://github.com/lpigeon/unitree-go2-mcp-server · https://github.com/0xKoda/drone-mcp · https://github.com/showkeyjar/robot-mcp-server · https://github.com/robin24/simconnect-mcp · https://github.com/shoff/MSFS-MCP · https://github.com/xdevplatform/xurl
- In questa repo: [grok-api/grok-build.md](../grok-api/grok-build.md), [bots-imagine/grok-bots.md](../bots-imagine/grok-bots.md), [bots-imagine/grok-imagine.md](../bots-imagine/grok-imagine.md), [hardware/llm-robot-architecture.md](../hardware/llm-robot-architecture.md), [grok-api/gotchas.md](../grok-api/gotchas.md)
