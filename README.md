# grokbot-hackathon

Team **aidea** al **Grok Hackathon at the Museum**: Ctrl+Alt Museum, Pavia, 4–5 novembre 2026.

> Pick a piece of hardware, an API, connect it to Grok (the API, Grok Voice, or the bot framework), and by Thursday afternoon show us something that didn't work when you started.

## Setup (ognuno sul proprio PC, una volta sola)

Serve a tutti per avere lo stesso ambiente: Python 3.12, le stesse dipendenze e lo stesso commit dell'SDK del cane. Lo script si può rilanciare quante volte si vuole.

> ⚠️ **Lancialo con Internet, prima di collegarti al Wi-Fi del cane.** Sul Wi-Fi del cane non c'è Internet: né `pip` né `git clone` funzionano.

```bash
git pull
./scripts/setup.sh
```

Cosa fa `scripts/setup.sh`:

1. crea `.venv/` con **Python 3.12** e installa `requirements.txt` (Grok: `xai-sdk`, `openai`; voce: `websockets`, `sounddevice`; cane: `crcmod`);
2. clona **`free-dog-sdk`** (SDK del Go1) in `vendor/free-dog-sdk`, fissato a un commit testato, e lo rende importabile (`import ucl`) da tutta la venv;
3. crea `.env` copiandolo da `.env.example`, se non esiste già;
4. fa uno smoke test: import delle librerie e una camminata del cane **in mock**.

Poi:

```bash
source .venv/bin/activate
```

Infine apri `.env` e incolla la `XAI_API_KEY` dell'evento.

**Perché l'SDK del cane non è nella repo:** è codice di terzi. Lo cloniamo in `vendor/`, che è in `.gitignore`, così non finisce nei commit e non crea conflitti. Il commit fissato in `scripts/setup.sh` garantisce che tutti abbiano la stessa versione. **Non committate niente da `vendor/`.**

**Problemi comuni**
- *`python3.12` non trovato*: su macOS `brew install python@3.12`, su Ubuntu `apt install python3.12 python3.12-venv`. Oppure indica un altro interprete: `PYTHON=/percorso/python3.12 ./scripts/setup.sh`.
- *`sounddevice` dà errore all'avvio di uno script vocale*: manca PortAudio. Su Ubuntu `apt install libportaudio2`, su macOS `brew install portaudio`.
- *Windows*: usate WSL, oppure eseguite a mano i passi dello script.

## Hello world: il cane Unitree Go1 avanza di 1 m

```bash
python src/dog/walk1m.py            # mock, senza cane: prova che tutto gira
```

Col cane vero:

1. Accendi il cane e fallo alzare in piedi.
2. Collega il PC al Wi-Fi `Unitree_Go…`, password `00000000`.
3. Verifica che risponda: `ping 192.168.12.1`.
4. Lancia `python src/dog/walk1m.py --real` e scrivi `go` per armare.

**INVIO o Ctrl+C = stop.** Il telecomando resta in mano a qualcuno. Dettagli in [src/dog/README.md](src/dog/README.md).

### Quale SDK del cane usiamo (e perché)

- **`free-dog-sdk` (Bin4ry) non è l'SDK ufficiale.** È un reverse engineering in puro Python della `unitree_legged_sdk` di Unitree Robotics: stesso protocollo UDP high-level del Go1, ma **senza le safety features** dell'originale. Lo usiamo perché si installa senza compilare, è fissato a un commit (`0ececb5`) e gira uguale su tutti i PC.
- **Con l'SDK ufficiale (anche via Docker) non avremmo comandi in più.** `free-dog-sdk` espone tutte le modalità high-level del Go1 (`ucl/enums.py`, `MotorModeHigh`): `IDLE`, `FORCE_STAND`, `VEL_WALK`, `POS_WALK`, `PATH`, `STAND_UP`, `STAND_DOWN`, `RECOVERY`, `STRAIGHTHAND`, `DANCE1`, `DANCE2`, `BACKFLIP`, `JUMPYAW`, `DAMPING`, più le andature di `GaitType`.
- **Cosa limita davvero i comandi è il nostro `src/dog/driver.py`**, che oggi usa solo `VEL_WALK` e `IDLE` con i limiti di velocità. Per usare altri comandi si estende il driver, non si cambia SDK.
- ⚠️ `DAMPING` spegne i motori e il cane cade. Nessun limite software copre un comando sbagliato: la prima prova di un comando nuovo sul cane vero va fatta con qualcuno al telecomando.
- Se `free-dog-sdk` desse problemi sul Go1 vero, il piano B è `unitree_legged_sdk` (binding Python da compilare).

## Come lavoriamo insieme (git)

- `main` deve funzionare sempre. Per ogni pezzo di lavoro aprite un branch corto, per esempio `git checkout main && git pull && git checkout -b nome/cosa`.
- Quando un pezzo funziona: `git pull --rebase origin main`, poi push, PR e merge subito. Fatelo spesso, almeno ogni ora.
- Una cartella per componente (`src/dog/`, `src/voice/`, `src/agent/`…), così non vi pestate i piedi.
- **Mai committare** `.env`, chiavi o token. `vendor/` e `logs/` sono già ignorati: dei log committate a mano solo quelli che usate come evidenza per la giuria.

## Cosa c'è qui

- [`src/dog/`](src/dog/README.md): driver del Go1 (mock + reale, limiti di sicurezza, log JSONL) e hello world.
- [`scripts/setup.sh`](scripts/setup.sh): setup dell'ambiente del team.
- [`docs/`](docs/README.md): tutta la ricerca preparatoria (Grok API, Grok Voice, Grok Bot, Imagine, SDK dell'hardware, evento, giuria, idee). Parti da [docs/README.md](docs/README.md).
- [`CLAUDE.md`](CLAUDE.md): contesto e fatti chiave per Claude Code, con la mappa dei docs.
- [`docs/voice/examples/`](docs/voice/examples/): client vocali pronti (locale con mic/casse, browser con token effimero, bridge Twilio, TTS streaming). Primo smoke test della Voice API: `set -a && source .env && set +a && python docs/voice/examples/voice_agent_local.py --text`.

## Il progetto

Hardware confermato: **cane robot Unitree Go1**. Idea da decidere: vedi [docs/ideas/ideas.md](docs/ideas/ideas.md) e [docs/event/tracks.md](docs/event/tracks.md) (traccia D *Robot Dog Patrol*).
