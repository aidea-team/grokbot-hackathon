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
3. installa **MuJoCo** (`pip install mujoco`, già in `requirements.txt`) e clona i modelli di **`mujoco_menagerie`** in `vendor/mujoco_menagerie`, fissato a un commit (Go1 e UR5e);
4. crea `.env` copiandolo da `.env.example`, se non esiste già;
5. fa uno smoke test: import delle librerie, 1 s di fisica simulata per Go1 e UR5e, e una camminata del cane **in mock**.

Poi:

```bash
source .venv/bin/activate
```

Infine apri `.env` e incolla la `XAI_API_KEY` dell'evento.

**Perché l'SDK del cane e i modelli MuJoCo non sono nella repo:** è codice di terzi. Li cloniamo in `vendor/`, che è in `.gitignore`, così non finiscono nei commit e non creano conflitti. I commit fissati in `scripts/setup.sh` garantiscono che tutti abbiano la stessa versione. **Non committate niente da `vendor/`.**

**Problemi comuni**
- *`python3.12` non trovato*: su macOS `brew install python@3.12`, su Ubuntu `apt install python3.12 python3.12-venv`. Oppure indica un altro interprete: `PYTHON=/percorso/python3.12 ./scripts/setup.sh`.
- *`sounddevice` dà errore all'avvio di uno script vocale*: manca PortAudio. Su Ubuntu `apt install libportaudio2`, su macOS `brew install portaudio`.
- *Windows*: usate WSL, oppure eseguite a mano i passi dello script.
- *Il viewer MuJoCo non si apre su macOS*: va lanciato con `mjpython` (installato insieme a `mujoco` nella venv), non con `python`.

## Simulatore MuJoCo (`src/sim/`)

Serve per provare i movimenti **prima** di toccare l'hardware: è il backend "mock" fisico, e ci permette di misurare successi e fallimenti anche senza il robot davanti.

```bash
source .venv/bin/activate
mjpython src/sim/view.py go1      # macOS: viewer interattivo del Go1
python src/sim/view.py ur5e       # Linux/Windows: plain python va bene
python src/sim/check_mujoco.py    # test headless, senza finestra
```

- Modelli disponibili: `go1` (cane) e `ur5e` (braccio). In `mujoco_menagerie` **non c'è l'UR3e**: se il braccio dei tracks è un UR3e, l'UR5e è l'approssimazione più vicina (stessa cinematica, scale diverse).
- `src/sim/models.py` dà i percorsi dei modelli; per usarli nel vostro codice: `from sim.models import model_path`.
- Il viewer è solo per guardare. Quando colleghiamo Grok, i comandi passano comunque dalla whitelist e dal validatore (vedi [docs/hardware/llm-robot-architecture.md](docs/hardware/llm-robot-architecture.md)), e il simulatore prende il posto dell'hardware reale.

## Chat col cane (`src/chat/`): agente a ciclo percezione → azione

Una webapp dove parli al cane. Un messaggio avvia una **missione**: a ogni passo il modello (OpenAI, Responses API) guarda la telecamera frontale, ragiona, sceglie **una sola azione atomica**, la esegue, guarda di nuovo, fino a `finish`. Se l'immagine è vuota gira un po' alla volta per ritrovarsi. Ogni passo si vede in chat (vista, ragionamento, azione).

```bash
cp .env.example .env     # poi metti OPENAI_API_KEY (e, se vuoi, OPENAI_MODEL / OPENAI_REASONING_EFFORT)
mjpython src/chat/app.py # macOS; Linux/Windows: python. Apre http://127.0.0.1:8765 e la finestra 3D
```

Lo switch **mock · MuJoCo / real · cane** è in alto a destra.

**Mock (default): MuJoCo con fisica vera.** `src/sim/dog_world.py` simula con `mj_step`: gravità, contatti, attrito, urti, cadute, oggetti leggeri che si spostano (`src/sim/scene.py`: ostacolo, cerchio, tunnel, slalom, forme). Cosa è fisica e cosa è controllo: le zampe sono i servo PD del modello Menagerie guidati da un trotto con cinematica inversa; un **stabilizzatore limitato** sul tronco tiene l'assetto e la velocità mentre cammina (si spegne se il cane si ribalta, quindi un cane caduto resta caduto); nei salti e nei flip il tronco riceve la velocità di lancio e da lì in poi è fisica libera, quindi un atterraggio sbagliato fa cadere davvero. Per la camminata nessuna policy RL: non c'era.

**Real: il cane vero, solo se lo vuole una persona.** Non basta cliccare:
1. `mjpython src/chat/app.py --real` lo lancia **un umano**, sul Wi-Fi del cane, e deve scrivere `go` nel terminale. Senza `--real` lo switch è rifiutato e le webcam reali non sono raggiungibili.
2. Nel browser, REAL richiede la checklist spuntata (cane in piedi con spazio, nessuno vicino, telecomando in mano) e il click su "arma e collega": si connette, controlla la batteria (≥ 20%) ed entra in `IDLE`.
3. Il modello vede **solo** `walk` (−0,3…0,5 m, 0,05…0,3 m/s), `turn` (±45°, 10…30°/s), `stand` e `finish`: niente salti, flip, posture. I limiti sono nello schema **e** nel validatore (`src/chat/real_body.py`), e il driver ha i suoi (`src/dog/driver.py`). Una azione alla volta, geofence a stima di odometria (`REAL_GEOFENCE_M`, default 2 m), al massimo `DOG_MAX_STEPS_REAL` passi (20). L'odometria è a circuito aperto: una stima.
4. **Kill switch indipendenti dal modello:** pulsante STOP (grande, nel banner rosso) o Esc nel browser, **INVIO nel terminale**. Dopo lo stop il cane resta `HALTED` finché una persona non lo riarma. Watchdog: se il browser tace per 3 s mentre il cane si muove, si ferma. Il telecomando fisico resta comunque in mano a qualcuno.
5. Tutto finisce in `logs/chat-AAAAMMGG.jsonl` (proposta, verdetto, esecuzione, kill) e `logs/dog-*.jsonl`.

**Webcam reali.** In real la pagina mostra in grande le camere del cane (cam1 davanti, cam2 basso, cam4 lato; clic su una piccola per portarla in primo piano) tramite il relay di `src/dog/cams.py` (sola lettura, serve `ffmpeg`). La cam1 è anche l'occhio dell'agente.

**Test** (nessuno tocca il cane: usano `MockDriver`):

```bash
python tests/test_real_safety.py   # 14 test avversari sul validatore: tool vietati, argomenti fuori range, geofence, kill switch, watchdog, batteria
python tests/test_chat_modes.py    # lo switch mock/real via API: senza --real è rifiutato, serve la conferma, stop = HALTED fino al riarmo
```

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

## Come lavoriamo insieme (git)

- `main` deve funzionare sempre. Per ogni pezzo di lavoro aprite un branch corto, per esempio `git checkout main && git pull && git checkout -b nome/cosa`.
- Quando un pezzo funziona: `git pull --rebase origin main`, poi push, PR e merge subito. Fatelo spesso, almeno ogni ora.
- Una cartella per componente (`src/dog/`, `src/voice/`, `src/agent/`…), così non vi pestate i piedi.
- **Mai committare** `.env`, chiavi o token. `vendor/` e `logs/` sono già ignorati: dei log committate a mano solo quelli che usate come evidenza per la giuria.

## Cosa c'è qui

- [`src/dog/`](src/dog/README.md): driver del Go1 (mock + reale, limiti di sicurezza, log JSONL) e hello world.
- [`src/sim/`](#simulatore-mujoco-srcsim): viewer e smoke test MuJoCo, percorsi dei modelli Go1 / UR5e.
- [`scripts/setup.sh`](scripts/setup.sh): setup dell'ambiente del team.
- [`docs/`](docs/README.md): tutta la ricerca preparatoria (Grok API, Grok Voice, Grok Bot, Imagine, SDK dell'hardware, evento, giuria, idee). Parti da [docs/README.md](docs/README.md).
- [`CLAUDE.md`](CLAUDE.md): contesto e fatti chiave per Claude Code, con la mappa dei docs.
- [`docs/voice/examples/`](docs/voice/examples/): client vocali pronti (locale con mic/casse, browser con token effimero, bridge Twilio, TTS streaming). Primo smoke test della Voice API: `set -a && source .env && set +a && python docs/voice/examples/voice_agent_local.py --text`.

## Il progetto

Hardware confermato: **cane robot Unitree Go1**. Idea da decidere: vedi [docs/ideas/ideas.md](docs/ideas/ideas.md) e [docs/event/tracks.md](docs/event/tracks.md) (traccia D *Robot Dog Patrol*).
