# Pre-flight checklist: sera di mar 3 novembre 2026

> **Scritta il:** 2026-11-03. Da fare su **ognuno dei 3 portatili**. ✅ = verificato su questa macchina (WSL2, Claude Code 2.1.317, Node 24, Python 3.12); ⚠️ = da verificare.
> Contesto e motivazioni in [claude-code-workflow.md](claude-code-workflow.md). Primi passi API e Voice in [README.md](../../README.md) e [grok-api/README.md](../grok-api/README.md).

## 1. Repo e Claude Code
- [ ] `git clone git@github.com:aidea-team/grokbot-hackathon.git && cd grokbot-hackathon && git pull`
- [ ] `claude --version` (≥ 2.1.317 qui ✅) e `claude` nella repo: **approvare il server `xai-docs`** da `.mcp.json`, poi `/mcp` deve mostrarlo connesso. Da shell: `claude mcp get xai-docs` → niente più `Pending approval`.
- [ ] In una sessione: `/skills` (o chiedere "quali skill hai?") → devono comparire `grok-api` e `robot-safety` ✅ (verificato con `claude -p`).
- [ ] Prova del docs MCP: *"usa xai-docs search_docs per 'function calling'"* → risultati reali.
- [ ] Ognuno accede a GitHub dal proprio account con permesso di push. ⚠️ Se useremo `claude --cloud`, collegare la repo a claude.ai/code stasera.

## 2. Grok Build e plugin (opzionale, ma serve per §5 del workflow)
- [ ] `curl -fsSL https://x.ai/cli/install.sh | bash`, poi `export PATH="$HOME/.grok/bin:$PATH"` nel `.bashrc`, poi `which -a grok agent` (attenzione al conflitto con la Cursor CLI) ⚠️
- [ ] `grok login` (in WSL senza browser: `grok login --device-auth`) e poi `grok models` deve funzionare ⚠️
- [ ] `grok inspect` nella repo → deve vedere `CLAUDE.md`, `.claude/skills/*` e `xai-docs` ⚠️
- [ ] In Claude Code: `/plugin marketplace add xai-org/grok-build-plugin-cc`, `/plugin install grok-build@xai-grok-build`, `/reload-plugins`, `/grok-build:check` → "ready" ⚠️
- [ ] Prova a vuoto: `/grok-build:review --wait` su un diff banale. Annotare tempo e consumo.
- [ ] Decidere se bloccare la delega proattiva: `"permissions": {"deny": ["Agent(grok-build:grok-delegate)"]}` in `.claude/settings.local.json` ⚠️

## 3. Python, venv, dipendenze
- [ ] `python3 --version` ≥ 3.10 (per `xai-sdk`); qui 3.12 ✅. `uv` è presente qui ✅.
- [ ] `python3 -m venv .venv && source .venv/bin/activate`
- [ ] `pip install -r docs/voice/examples/requirements.txt xai-sdk openai pytest`
- [ ] SDK dell'hardware **in anticipo**, perché al museo la rete potrebbe essere lenta: `pip download` / `pip install djitellopy opencv-python unitree_webrtc_connect` (vedi [robot-dog.md](../hardware/robot-dog.md), [drones.md](../hardware/drones.md)). Portarsi una wheelhouse: `pip download -d wheels/ <pacchetti>`.
- [ ] Windows (simulatore di volo MSFS): Python **64 bit** nativo Windows con `pip install SimConnect`. SimConnect non gira in WSL ([flight-simulator.md](../hardware/flight-simulator.md)).

## 4. Audio (Grok Voice)
- [ ] PortAudio: `sudo apt install -y libportaudio2` (per compilare: `portaudio19-dev`); su macOS `brew install portaudio`.
- [ ] `python -c "import sounddevice as sd; print(sd.query_devices())"` → microfono e casse visibili. ⚠️ In WSL l'audio passa da WSLg/PulseAudio e il microfono può non comparire: in quel caso il client voce va fatto girare su Windows nativo o su un altro portatile.
- [ ] Cuffie o speaker con poco eco a portata di mano (barge-in, [voice/gotchas.md](../voice/gotchas.md)).

## 5. Retro (se l'idea tocca il C64)
- [ ] `sudo apt install vice`; il pacchetto **non ha le ROM**: copiarle da `vice-3.7.1.tar.gz` (`data/C64`, `data/DRIVES`) in `/usr/share/vice/` ([retro-machines.md](../hardware/retro-machines.md) §2.1).
- [ ] `x64sc -binarymonitor -binarymonitoraddress ip4://127.0.0.1:6502` si avvia; `petcat -w2 -o t.prg -- t.bas` funziona.
- [ ] Opzionale: `claude mcp add vice-mcp -- npx github:simen/vice-mcp` per il debug da Claude (⚠️ non provato, repo senza licenza: leggere il codice prima).

## 6. Rete (trappole WSL)
- [ ] ⚠️ WSL2 in modalità NAT di default: i pacchetti UDP in ingresso (stato del Tello sulla porta 8890, video sulla 11111) e il WebRTC del Go2 possono non arrivare in WSL. Valutare `networkingMode=mirrored` in `%UserProfile%\.wslconfig` (poi `wsl --shutdown`), oppure far girare il driver su Windows nativo. Provarlo **stasera** con qualsiasi dispositivo UDP.
- [ ] Hotspot dal telefono pronto come seconda rete (collegati al Tello si perde Internet: [drones.md](../hardware/drones.md)).
- [ ] Ciabatta, prolunga, cavo USB-C e cavo Ethernet.

## 7. Chiavi e segreti
- [ ] `cp .env.example .env`; la `XAI_API_KEY` dell'evento arriva mercoledì. Se l'abbiamo prima: `set -a && source .env && set +a && curl -s https://api.x.ai/v1/models -H "Authorization: Bearer $XAI_API_KEY" | grep '"id"'`.
- [ ] `git check-ignore .env` deve stampare `.env` (lo è, da `.gitignore`).
- [ ] Mai incollare la key nella chat di Claude Code o in una sessione cloud; non loggarla nei JSONL.
- [ ] Facoltativi: account Grok Bot attivo (app desktop) e routine di prova con trigger webhook; app X developer solo se postiamo.

## 8. Test offline (senza key e senza hardware)
- [ ] `python docs/voice/examples/voice_agent_local.py --help` parte senza errori di import.
- [ ] Mercoledì mattina, appena c'è la key: `python docs/voice/examples/voice_agent_local.py --text` (smoke della Voice API) e mini-benchmark TTFT da [gotchas.md](../grok-api/gotchas.md).
- [ ] Ognuno sa avviare `claude -w <modulo>` e conosce il proprio ruolo ([workflow §4](claude-code-workflow.md#4-tre-persone-in-parallelo-con-claude-code-36-ore)).

## 9. Kit per la demo
- [ ] Telefono con treppiede o clip per il **video del prima** (mer 9:00) e il backup (gio 14:00); spazio libero ≥ 10 GB.
- [ ] Registrazione schermo pronta su Windows (Win+Alt+R oppure OBS).
- [ ] Nastro adesivo colorato per delimitare l'area (checklist di sicurezza in [llm-robot-architecture.md §6](../hardware/llm-robot-architecture.md)).
- [ ] [staff-questions.md](../ideas/staff-questions.md) stampato o aperto sul telefono.
- [ ] Batterie esterne e caricatori dei portatili.

## 10. Aggiunte dopo le tracce (3/11 sera)

- [ ] **Python 3.12** per tutto il team: `ur_rtde` ha wheel solo fino alla 3.12, e LeRobot e tau2-bench richiedono almeno la 3.12.
- [ ] `pip install ur_rtde` e avvio di **URSim**: `docker run -e ROBOT_MODEL=UR3 -p 6080:6080 -p 29999:29999 -p 30001-30004:30001-30004 universalrobots/ursim_e-series`, con il teach pendant nel browser su `http://localhost:6080`. Vedi [../hardware/robot-arm.md](../hardware/robot-arm.md).
- [ ] Far girare in mock il wrapper `ArmSkills` di robot-arm.md collegato a `voice_agent_local.py --text`.
- [ ] Solo per la traccia 01: creare stasera una API key gratuita OpenAlex (senza key si hanno 100 crediti al giorno).
- [ ] Rileggere [../event/tracks.md](../event/tracks.md) e decidere la traccia prima delle 9:00.
