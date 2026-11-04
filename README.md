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

**Mock (default): MuJoCo con fisica vera, stessi comandi del cane vero.** Il simulatore non ha un suo linguaggio di comandi: riceve **esattamente quello che riceverebbe il Go1**. I tool (`src/dog/commands.py`: `walk`, `turn`, `stand`, `stand_up`, `lie_down`, `recovery`, `backflip`, `jump_yaw`, `straight_hand`, `dance`, `damping`) diventano chiamate al driver (`walk(vx, vyaw, secondi)`, `primitive(modo, secondi)`) con lo **stesso codice** per cane e simulatore; il `SimDriver` (`src/sim/sim_driver.py`) mette sul "filo" simulato una velocità o un modo Go1 (STAND_UP, BACKFLIP, JUMPYAW, DANCE1/2, DAMPING…) e `src/sim/dog_world.py` li interpreta come farebbe il firmware: a catena aperta (velocità × tempo, niente correzioni di rotta), i modi partono sul fronte di salita e il cane li finisce da sé. Cosa è fisica e cosa è controllo (aggiornato la notte del 4/11): le zampe sono i servo PD del modello Menagerie guidati da un trotto con cinematica inversa, e **sono loro a spingere**: la velocità e lo yaw sono regolati dall'ampiezza del passo (stima di velocità → traiettoria dei piedi) e la tenuta della rotta dal controllo di yaw; pitch e roll anche dalla lunghezza delle zampe. Resta uno **stabilizzatore invisibile** sul tronco (`INVISIBLE_ASSIST` in `dog_world.py`), ridotto però a una frazione: forza massima 4 N (era 30, il peso del cane è ~125 N), coppia di assetto 10 Nm (era 40), coppia di yaw 6 Nm (era 25); si spegne se il cane si ribalta. Con questi valori la scala si sale e il passo segue i comandi (~0,5 m/s al massimo, il resto è limite dell'andatura). **Salti:** il decollo è la spinta delle zampe (flessione profonda → estensione, limitata dalle coppie del Go1): +0,3 m sopra la posizione eretta, ~0,4 s di volo; nessuna velocità di lancio data da noi. **Rotazione** (flip, yaw di `jump_yaw`): una coppia sul tronco applicata solo mentre i piedi spingono sul pavimento, con tetto 60 Nm (= le due zampe posteriori alla coppia massima dei motori); dopo lo stacco nulla agisce sul corpo. Se la spinta non basta, il cane sotto-ruota e cade davvero. ⚠️ Assunzioni non verificate sul cane: una velocità da sdraiato/caduto non fa nulla (serve `stand_up`/`recovery`), i parametri di salto/flip/giravolta. In più il simulatore dà un feedback fisico che il cane vero non ha (oggetto toccato, bloccato, caduto).

**Modalità `both` (cane vero + mock).** Terzo pulsante in alto a destra: la chat manda **gli stessi comandi** al cane vero e al simulatore. Serve `--real` all'avvio e la stessa checklist di arming del cane vero. Il cane vero comanda: un comando va prima a lui (validazione, stato, una azione alla volta) e solo se lo accetta arriva anche al simulatore, che è uno specchio a tempo reale. L'agente vede le **telecamere reali** e l'odometria stimata del cane; la posa del simulatore è mostrata accanto (`sim: x … y …`) per confronto. STOP agisce su entrambi. Il simulatore riparte dall'origine quando si entra in `both`.

**Il mondo (`src/sim/scene.py`, ricostruito il 4/11).** Cane all'origine verso +x: **2 m di pavimento vuoto**, poi una **scala** (8 gradini da 5 cm) che porta a una **impalcatura** (piattaforma a 0,4 m, parapetti su tre lati: ci si sale solo dalla scala); **ai lati** piattaforme colorate basse; **dietro** 5 barriere di altezza crescente (0,10→0,60 m) e una **persona in piedi a grandezza reale** (1,75 m); una palla leggera che rotola.

**Real: il cane vero, solo se lo vuole una persona.** Non basta cliccare:
1. `mjpython src/chat/app.py --real` lo lancia **un umano**, sul Wi-Fi del cane, e deve scrivere `go` nel terminale. Senza `--real` lo switch è rifiutato e le webcam reali non sono raggiungibili.
2. Nel browser, REAL richiede la checklist spuntata (cane in piedi con spazio, nessuno vicino, telecomando in mano) e il click su "arma e collega": si connette (la batteria viene solo mostrata) ed entra in `IDLE`.
3. **Nessun limite numerico, di proposito (4/11): i guardrail li riscrive il team.** Il modello vede tutte le primitive del Go1: `walk`, `turn`, `stand`, `stand_up`, `lie_down`, `recovery`, `backflip`, `jump_yaw`, `straight_hand`, `dance` (stile 1|2), `damping` e `finish`. Gli argomenti sono controllati solo nel tipo (numeri finiti); non ci sono né range, né geofence, né batteria minima, né tetto di velocità nel driver (`src/dog/driver.py`, `PRIMITIVES`: **le durate dei modi sono stime non verificate sul cane**). Restano una azione alla volta, `DOG_MAX_STEPS_REAL` passi per missione (20) e odometria a circuito aperto. ⚠️ `backflip`, `jump_yaw`, `dance` e `damping` non sono mai stati provati sul cane vero.
4. **Kill switch indipendenti dal modello:** pulsante STOP (grande, nel banner rosso) o Esc nel browser, **INVIO nel terminale**. Dopo lo stop il cane resta `HALTED` finché una persona non lo riarma. Watchdog: se il browser tace per 3 s mentre il cane si muove, si ferma. Il telecomando fisico resta comunque in mano a qualcuno.
5. Tutto finisce in `logs/chat-AAAAMMGG.jsonl` (proposta, verdetto, esecuzione, kill) e `logs/dog-*.jsonl`.

**Webcam reali.** In real la pagina mostra in grande le camere del cane (cam1 davanti, cam2 basso, cam4 lato; clic su una piccola per portarla in primo piano) tramite il relay di `src/dog/cams.py` (sola lettura, serve `ffmpeg`). La cam1 è anche l'occhio dell'agente.

**Test** (nessuno tocca il cane: usano `MockDriver`):

```bash
python tests/test_real_safety.py   # 14 test: tool inesistenti, argomenti malformati, nessun limite numerico, tutte le primitive, kill switch, watchdog, armamento
python tests/test_sim.py           # il simulatore riceve gli stessi comandi del cane, il mondo, la scala, le primitive
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
- [`src/sim/`](#simulatore-mujoco-srcsim): viewer e smoke test MuJoCo, percorsi dei modelli Go1 / UR5e.
- [`scripts/setup.sh`](scripts/setup.sh): setup dell'ambiente del team.
- [`docs/`](docs/README.md): tutta la ricerca preparatoria (Grok API, Grok Voice, Grok Bot, Imagine, SDK dell'hardware, evento, giuria, idee). Parti da [docs/README.md](docs/README.md).
- [`CLAUDE.md`](CLAUDE.md): contesto e fatti chiave per Claude Code, con la mappa dei docs.
- [`docs/voice/examples/`](docs/voice/examples/): client vocali pronti (locale con mic/casse, browser con token effimero, bridge Twilio, TTS streaming). Primo smoke test della Voice API: `set -a && source .env && set +a && python docs/voice/examples/voice_agent_local.py --text`.

## Il progetto

Hardware confermato: **cane robot Unitree Go1**. Idea da decidere: vedi [docs/ideas/ideas.md](docs/ideas/ideas.md) e [docs/event/tracks.md](docs/event/tracks.md) (traccia D *Robot Dog Patrol*).
