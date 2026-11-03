# Bracci robotici (cobot): quali sono e come controllarli da Python (e da Grok)

> **Verificato il:** 2026-11-03 sera (vigilia dell'evento). Fonti in fondo.
> **Legenda:** ⚠️ = non verificato oppure dedotto. Il wrapper Python della §6 è stato **eseguito solo in modalità mock** (Python 3.12); la parte `ur_rtde` non è mai stata provata contro un robot né contro URSim.
> **Collegati:** architettura e validatore generici in [llm-robot-architecture.md](llm-robot-architecture.md); voce realtime e tool calling in [../voice/README.md](../voice/README.md) e [../voice/tool-calling-in-voice.md](../voice/tool-calling-in-voice.md); le tracce in [../event/tracks.md](../event/tracks.md); risorse pubbliche delle tracce in [../event/track-resources.md](../event/track-resources.md).

## TL;DR

- **Indizio forte: almeno due dei tre bracci sono Universal Robots UR3e e UR5e di Spazio Robot.** Spazio Robot (sponsor dell'evento) è il laboratorio di robotica on demand di **Fabbrica Vigevano**. Il suo calendario pubblico di disponibilità (`/api/public/availability`) segna come **occupati il 4 e 5 novembre 2026 esattamente "Universal Robots UR3e" e "Universal Robots UR5e"**, e nessun'altra macchina. Il CEO di Fabbrica Vigevano, **Alessandro Rano**, è anche **in giuria**. ⚠️ Resta una deduzione: nessuna pagina dice "i bracci dell'hackathon sono questi".
- **Il terzo braccio è ignoto.** Lo UR10e di Spazio Robot non risulta prenotato. Ipotesi ⚠️: il braccio didattico del museo (il museo propone "programmare un braccio robotico" alle superiori) oppure uno UR10e prenotato fuori calendario. Per questo il file copre anche gli altri cobot educational (§4).
- **Coerenza con le tracce:** Spazio Robot ha una stampante 3D Ultimaker "per realizzare pinze, supporti e prototipi" (→ l'utensile stampato con forchetta, spintore e punta); gli UR e-Series hanno 6 assi, sensore forza/coppia in flangia e 17–23 funzioni di sicurezza configurabili; il talk di mer 10:00 è "Intro to cobots, dogs, drones and rovers".
- **Se è un UR e-Series:** da Python si usa **`ur_rtde`** (MIT, SDU Robotics), `pip install ur_rtde`. Wheel solo fino a **Python 3.12** → usare 3.12. Il robot deve essere in **Remote Control** (impostazione sul teach pendant), altrimenti il controller rifiuta gli script esterni e chiude le porte 30001–30003.
- **Simulatore gratuito ufficiale:** `docker run --rm -it -e ROBOT_MODEL=UR3 -p 6080:6080 -p 29999:29999 -p 30001-30004:30001-30004 universalrobots/ursim_e-series` → PolyScope nel browser su `http://localhost:6080/vnc.html`. Stesse porte del robot vero: `ur_rtde` si collega identico.
- **Architettura consigliata:** Grok chiama **skill a nomi** (go to pose, indicate, lift tray, put down, push) con parametri a enum; ogni movimento è **proposto** e parte solo dopo un "sì" **trovato nella trascrizione dell'operatore** (non nella parola di Grok); lo stop è locale (tastiera, keyword vocale, e-stop fisico in mano allo staff) e non passa dall'LLM. Tool JSON in §5, wrapper con mock in §6.

## 1. Cosa abbiamo scoperto (e come)

| Fonte | Cosa dice | Peso |
|---|---|---|
| [pavia.grokbot.it/tracks](https://pavia.grokbot.it/tracks) (copia in [../event/raw/tracks.txt](../event/raw/tracks.txt)) | Tre bracci: **arm 1** + camera 1 (traccia C), **arm 2** + camera 2 (traccia A), **arm 3** senza camera (04 Voice Control, 05 Skill Passport). "The arms have no gripper: they carry a printed tool with a fork, a pusher and a tip, and only lift objects placed on slotted trays." Slot da 30 minuti con lo staff. "The manuals of the arms, available online" (traccia 05) | Ufficiale |
| PR #14 del repo del sito (`aletheia/grok-bot-hackathon`) | Codici materiali interni rimossi dal testo pubblico: "utensile stampato (M1)", "vassoi a fessure (M2)", "**software dei bracci (M3)**" ancora tra i punti aperti della traccia 04 | Ufficiale, interno |
| [spaziorobot.com/attrezzature](https://spaziorobot.com/attrezzature) | Cobot: **UR3e, UR5e, UR10e**; industriali: KUKA KR 6 R700-2; SCARA Mitsubishi (x2), SCARA RTA (x2); stampa 3D Ultimaker FDM (Objet 30 in arrivo). "Spazio Robot è un progetto di Fabbrica Vigevano", Viale Industria 213/5, Vigevano | Verificato |
| [spaziorobot.com/api/public/availability](https://spaziorobot.com/api/public/availability) (CSV letto dalla pagina "Accesso al laboratorio") | `Universal Robots UR3e,04/11/2026,05/11/2026` e `Universal Robots UR5e,04/11/2026,05/11/2026`. Nessun'altra riga | Verificato, interpretazione ⚠️ |
| [spaziorobot.com/chi-siamo](https://spaziorobot.com/chi-siamo) | Team: Alessandro Rano (CEO, founder di Fabbrica Vigevano), Yevheniy Dmytriyev (CTO, PhD automazione e robotica, Università di Pavia), Sergio Dulio, Federico Gallese. Alessandro Rano è nella giuria dell'hackathon | Verificato |
| Pagine macchina UR su spaziorobot.com | Si programmano "dal teach pendant touchscreen con l'interfaccia grafica PolyScope"; interfacce Modbus TCP, Ethernet/IP, PROFINET, driver ROS/ROS2 | Verificato |
| Disegno `robotic-arm.png` del sito | Line-art generico di braccio con pinza: non prova nulla (e i bracci veri non hanno pinza) | Irrilevante |
| CSV Lombardia, open day del museo (già in [museum-inventory.md](museum-inventory.md)) | Il museo fa "programmare un braccio robotico" alle superiori: modello mai citato | ⚠️ |
| "Factory Academia" (talk mer 11:00) | Unico riscontro: un video in cui Alessandro Arnetta è "CEO di Factory Accademia", acceleratore di startup. Nessun legame trovato con i bracci | ⚠️ |

Ricerche senza risultato: "Ctrl+Alt Museum" + braccio robotico / cobot; "comPVter" + robot; "SEA Vision" + cobot per l'evento; il sito fabbricavigevano.it rispondeva HTTP 429.

### Specifiche dei candidati (da spaziorobot.com)

| | UR3e | UR5e | UR10e |
|---|---|---|---|
| Carico utile | 3 kg | 5 kg | 12,5 kg |
| Sbraccio | 500 mm | 850 mm | 1.300 mm |
| Ripetibilità | ± 0,03 mm | ± 0,03 mm | ± 0,05 mm |
| Peso | 11,2 kg | 20,7 kg | 33,5 kg |
| Base | Ø 128 mm | Ø 151 mm | Ø 190 mm |
| Funzioni di sicurezza configurabili | 23 | 23 | 17 |

Tutti: 6 giunti rotanti, sensore forza/coppia nella flangia, I/O digitali e analogici sul controller e sulla flangia.

## 2. Riconoscere il modello in 5 minuti

1. **Guardare la base e il pendant.** UR e-Series: giunti cilindrici chiari con calotte colorate ⚠️, etichetta del modello sulla base ("UR3e", "UR5e"), teach pendant touchscreen con PolyScope e **pulsante rosso di emergenza** sul pendant. Il pulsante di freedrive è sul retro del pendant ⚠️.
2. **Chiedere l'IP** (PolyScope: menu ☰ → Settings → System → Network ⚠️ percorso da confermare) e provare dal laptop sulla stessa rete:
   ```bash
   nc -v <ip> 29999            # UR risponde: "Connected: Universal Robots Dashboard Server"
   # poi digitare:  get robot model   |   PolyscopeVersion   |   robotmode   |   safetystatus   |   is in remote control
   ```
   ⚠️ I comandi sono i nomi del Dashboard Server; `ur_rtde` li espone come `getRobotModel()`, `polyscopeVersion()`, `robotmode()`, `safetystatus()`, `isInRemoteControl()`.
3. **Se non è un UR**, indizi rapidi:

| Indizio | Probabile modello | Vai a |
|---|---|---|
| Bianco/argento, controller a parte, UI web UFactory Studio | UFactory xArm 5/6/7, Lite 6, 850 | §4.1 |
| Piccolo (≈ 30–50 cm), schermo M5Stack o Raspberry nella base, cavo USB seriale | Elephant Robotics myCobot 280 / 320 | §4.2 |
| Base nera tozza, DobotStudio / DobotSCStudio | Dobot Magician (USB) o MG400 / M1 Pro / CR (Ethernet) | §4.3 |
| Servo blu/neri a vista, stampato in PLA, cavo USB | SO-100 / SO-101 (LeRobot) | §4.5 |
| Plastica arancione/grigia igus, software iRC | igus ReBeL | §4.4 ⚠️ |
| Stampato in grande, motori stepper a vista, Teensy | Annin AR4 | §4.4 ⚠️ |

4. **Domande decisive allo staff** (lista completa in §8): modello e versione PolyScope; possiamo passare in Remote Control e collegarci da laptop (`ur_rtde` / porta 30004) o solo programmare dal pendant? TCP e payload di ciascuna punta dell'utensile? Chi tiene l'e-stop?

## 3. Universal Robots e-Series (UR3e / UR5e): la strada principale

### 3.1 Interfacce e porte

| Porta | Interfaccia | A cosa ci serve |
|---|---|---|
| 29999 | Dashboard Server (testo, una riga per comando) | `load`/`play`/`stop`/`pause` dei programmi PolyScope, power on, brake release, sblocco protective stop, stato |
| 30001 / 30002 / 30003 | Primary / Secondary / Real-time (accettano URScript) | Inviare script URScript grezzi (`ur_rtde` carica il suo script qui) |
| 30004 | RTDE (Real-Time Data Exchange) | Stato del robot e registri, usato da `ur_rtde` |
| 30011–30013 | Versioni read-only di 30001–30003 | Monitoraggio senza poter comandare |
| 30020 | Interpreter mode | ⚠️ non serve |

**Remote vs Local (e-Series).** In *Local Control* il controller "non accetta comandi URScript e le connessioni alle porte 30001, 30002 e 30003 vengono chiuse"; alcuni comandi Dashboard (load, play, power on, …) funzionano solo in *Remote Control*. Per monitorare in entrambe le modalità si usano 30004 e 30011–30013. Il passaggio a Remote si fa dal pendant (va abilitato in Settings → System → Remote Control ⚠️ percorso da confermare). `ur_rtde` controlla la modalità e rifiuta di partire se il robot è in Local (flag `FLAG_DISABLE_REMOTE_CONTROL_CHECK` per disattivare il controllo: **non usarlo**, chiedere allo staff).

### 3.2 Due modi di costruire le skill (scegliere con lo staff al primo slot)

| | **A. Programmi PolyScope + Dashboard** | **B. `ur_rtde` + pose a nome** |
|---|---|---|
| Chi scrive la skill | Il team con lo staff, sul pendant (waypoint insegnati in freedrive), salvata come `lift_tray_left.urp` | Il team in Python: pose registrate in freedrive, movimenti `moveL`/`moveJ` |
| Come Grok la lancia | `dash.loadURP("lift_tray_left.urp"); dash.play()` | `rtde_c.moveL(pose, speed, acc, True)` |
| Sicurezza | Massima: traiettorie viste e provate dallo staff; velocità del programma + speed slider | Buona se le pose sono a enum e la velocità è bassa; serve il validatore |
| Flessibilità | Una skill = un file; parametri solo via registri ⚠️ | Parametri (zona, distanza di spinta) calcolati in Python |
| Quando | Se lo staff non vuole controllo esterno di traiettorie, o "software dei bracci" significa PolyScope | Se lo staff permette Remote Control e `ur_rtde` |

La traccia 04 dice "basic skills … written by the team with the arms' software": può voler dire PolyScope (strada A). ⚠️ Da chiarire al kick-off. Il wrapper della §6 supporta B; la strada A si aggiunge con un `DashboardArm` (snippet in §3.4).

### 3.3 `ur_rtde`: installazione, connessione, stato

```bash
python3.12 -m venv .venv && . .venv/bin/activate
pip install ur_rtde          # 1.6.5, MIT; wheel Linux/Windows per CPython 3.7–3.12 (niente 3.13; niente wheel macOS su PyPI → su Mac compilare da sorgente)
```

```python
import rtde_control, rtde_receive, rtde_io, dashboard_client

IP = "192.168.x.y"                      # dal pendant; con URSim: "localhost" o l'IP del container
rtde_r = rtde_receive.RTDEReceiveInterface(IP)
print(rtde_r.getActualQ())              # 6 giunti, radianti
print(rtde_r.getActualTCPPose())        # [x, y, z, rx, ry, rz]: metri + axis-angle (radianti), frame base
print(rtde_r.getSafetyMode(), rtde_r.isProtectiveStopped(), rtde_r.isEmergencyStopped())

dash = dashboard_client.DashboardClient(IP); dash.connect()
print(dash.getRobotModel(), dash.polyscopeVersion(), dash.isInRemoteControl(), dash.safetystatus())
```

Note importanti (dagli header di `ur_rtde`):
- `RTDEControlInterface(hostname, frequency=-1.0, flags=FLAGS_DEFAULT, ur_cap_port=50002)`: di default **carica il proprio script URScript** sul controller (che quindi smette di eseguire il programma PolyScope caricato). **Non è thread-safe**: un solo thread lo usa (lock).
- Pose e unità: giunti in rad, pose in m + rotation vector in rad, velocità `moveJ` in rad/s (default 1.05) e `moveL` in m/s (default 0.25), accelerazioni rad/s² (1.4) e m/s² (1.2). **Per la demo usare 0.05–0.10 m/s.**

### 3.4 Muoversi, fermarsi, limitare

```python
rtde_c = rtde_control.RTDEControlInterface(IP)
rtde_io_ = rtde_io.RTDEIOInterface(IP)

rtde_io_.setSpeedSlider(0.3)                 # cap globale al 30% (come lo slider del pendant)
rtde_c.setTcp([0, 0, 0.12, 0, 0, 0])         # TCP della punta: misurarlo con lo staff (metri dalla flangia)
rtde_c.setPayload(0.2)                       # kg dell'utensile stampato (+ vassoio se serve) ⚠️ valore da chiedere

home_q = [0, -1.57, 1.57, -1.57, -1.57, 0]   # ESEMPIO, non usarlo sul vero senza averlo visto in URSim
rtde_c.moveJ(home_q, 0.5, 0.5)               # bloccante, giunti

target = rtde_r.getActualTCPPose(); target[2] += 0.05          # 5 cm più in alto
if rtde_c.isPoseWithinSafetyLimits(target):                     # rispetta i limiti di sicurezza configurati
    rtde_c.moveL(target, 0.05, 0.3, True)                       # asynchronous=True: si può interrompere
    # ... in un altro punto del codice (kill switch):
    rtde_c.stopL(2.0, True)                                     # decelera a zero, non bloccante

rtde_c.stopScript()                          # a fine sessione: rilascia il controller
```

Strada A (programmi PolyScope) in 5 righe:

```python
dash = dashboard_client.DashboardClient(IP); dash.connect()
dash.loadURP("lift_tray_left.urp")    # programma salvato sul robot
dash.play()
while dash.running(): time.sleep(0.05)
# stop immediato: dash.stop()   |   pausa: dash.pause()
```

Altre funzioni utili e verificate negli header: `moveJ_IK(pose, ...)`, `getInverseKinematics(pose)`, `isJointsWithinSafetyLimits(q)`, `isSteady()`, `isProgramRunning()`, `teachMode()` / `endTeachMode()` (freedrive da codice: **solo con lo staff**), `triggerProtectiveStop()`, `reconnect()`. Dashboard: `powerOn()`, `brakeRelease()`, `unlockProtectiveStop()`, `closeSafetyPopup()`, `popup(msg)`, `addToLog(msg)`.

### 3.5 Stop ed emergenza: chi fa cosa

| Livello | Come | Effetto | Chi |
|---|---|---|---|
| E-stop fisico | Pulsante rosso sul teach pendant (ed eventuale e-stop esterno) | Arresto di emergenza, serve ripristino dal pendant | **Staff**, sempre a portata di mano |
| Protective stop | Automatico (collisione, limite superato) o `rtde_c.triggerProtectiveStop()` | Stop e popup; si sblocca con `dash.unlockProtectiveStop()` dopo aver capito la causa | Robot / codice |
| Stop software | `rtde_c.stopL(a)` / `stopJ(a)`, oppure `dash.stop()` / `dash.pause()` per i programmi PolyScope | Decelerazione controllata | **Kill switch locale** (tastiera, keyword vocale) |
| Rallentare | `rtde_io.setSpeedSlider(f)` | Scala la velocità di tutto | Codice, all'avvio |
| Limiti di sicurezza | Configurazione di sicurezza in PolyScope (protetta da password): limiti di velocità TCP, piani, giunti | Il controller li impone comunque | **Solo lo staff**: non toccarli |

**Mai lato LLM:** cambiare TCP/payload/sicurezza, `brakeRelease`, `powerOn`, `restartSafety`, `unlockProtectiveStop`, `teachMode`. Questi li fa un umano.

### 3.6 Simulazione: URSim in Docker (gratis, ufficiale)

```bash
docker run --rm -it -e ROBOT_MODEL=UR3 \
  -p 5900:5900 -p 6080:6080 -p 29999:29999 -p 30001-30004:30001-30004 \
  -v "$PWD/ursim-programs:/ursim/programs" \
  universalrobots/ursim_e-series            # tag recenti 5.22 … 5.26 (28 ott 2026)
# PolyScope nel browser: http://localhost:6080/vnc.html?host=localhost&port=6080
```

- `ROBOT_MODEL`: `UR3 UR5 UR7 UR8LONG UR10 UR12 UR15 UR16 UR18 UR20 UR30` (default UR5). I programmi `.urp` creati nel simulatore restano nel volume `/ursim/programs`: si possono preparare le skill PolyScope (strada A) già stanotte ⚠️ e portarle sul robot vero solo con l'ok dello staff.
- All'avvio il robot simulato è spento: accenderlo dal PolyScope nel browser (o `dash.powerOn(); dash.brakeRelease()`) e, se `ur_rtde` si lamenta della modalità, attivare Remote Control ⚠️.
- ⚠️ Immagine pensata per x86_64; su Mac Apple Silicon va in emulazione (lenta) o non parte.
- **Alternative:** MuJoCo Menagerie ha `universal_robots_ur5e` e `universal_robots_ur10e` (non UR3e) per visualizzare/pianificare; RoboDK (`pip install robodk`, software commerciale con trial) ha i modelli UR e genera URScript ⚠️. Per la demo e per la giuria basta **URSim + il mock della §6**: stessi comandi, stesso codice.

### 3.7 Utensile stampato e vassoi

- **Tre punte = tre TCP.** Forchetta (sollevare vassoi fessurati), spintore (spingere), punta (indicare). Ogni skill imposta il proprio TCP (`setTcp`) prima di muoversi: misurare gli offset con lo staff o leggerli dall'installazione PolyScope ⚠️.
- **Sollevare un vassoio:** avvicinarsi di lato, entrare nelle fessure in orizzontale (`moveL` lento), alzare di pochi cm, spostarsi in alto, appoggiare, **uscire dalle fessure in orizzontale prima di risalire** (se si risale dritti si riporta su il vassoio). La geometria reale (direzione di ingresso, altezza delle fessure) va misurata ⚠️.
- **Indicare un oggetto visto dalla camera (traccia A):** calibrare camera → tavolo con 4+ punti: si porta la punta su 4 marker del tavolo, si leggono `getActualTCPPose()` (x, y) e i pixel dei marker nell'immagine, e si calcola un'omografia (`cv2.findHomography(px, xy)`). Poi il tool `arm_indicate_xy` riceve pixel o coordinate tavolo e il validatore controlla il box di lavoro. ⚠️ Valido solo se la camera è fissa e il tavolo piano.

## 4. Altri cobot educational (se il terzo braccio non è un UR)

### 4.1 UFactory xArm 5/6/7, Lite 6, 850: `xarm-python-sdk` (BSD-3-Clause)

```python
# pip install xarm-python-sdk      (1.18.4)
from xarm.wrapper import XArmAPI
arm = XArmAPI("192.168.1.xxx")                 # Ethernet
arm.motion_enable(enable=True); arm.set_mode(0); arm.set_state(0)
arm.set_position(x=300, y=0, z=200, roll=180, pitch=0, yaw=0, speed=50, wait=True)   # mm, gradi, mm/s
arm.set_servo_angle(angle=[0, 0, 0, 0, 0, 0], speed=20, wait=True)                 # gradi, gradi/s ⚠️ numero di giunti per modello
arm.emergency_stop()
```
Utili: `set_reduced_mode`, `set_reduced_tcp_boundary` (geofence lato controller), `set_tcp_offset`, `set_simulation_robot` (il controller esegue senza muovere i motori ⚠️ da verificare). MuJoCo Menagerie: `ufactory_lite6`, `ufactory_xarm7`. LeRobot ha un plugin community per xArm.

### 4.2 Elephant Robotics myCobot 280 / 320: `pymycobot` (MIT)

```python
# pip install pymycobot            (4.0.7)
from pymycobot import MyCobot280
mc = MyCobot280("/dev/ttyUSB0")                # Windows: "COM3"; baud di default ⚠️ (spesso 115200)
print(mc.get_angles(), mc.get_coords())
mc.send_angles([0, 0, 0, 0, 0, 0], 30)        # gradi, speed 1–100
mc.send_coords([150, 0, 200, -180, 0, 0], 30, 0)   # mm + gradi, speed, mode (0 angolare / 1 lineare ⚠️)
mc.stop(); mc.pause(); mc.resume()
```
**Mai** `release_all_servos()` o `set_free_mode()` lato LLM: il braccio cade. Per il 320 c'è `MyCobot320`.

### 4.3 Dobot

- **MG400 / M1 Pro** (Ethernet): repo ufficiale `Dobot-Arm/TCP-IP-4Axis-Python` (MIT). Porta **29999** dashboard (`EnableRobot()`, `DisableRobot()`, `ClearError()`, …), **30003** movimento (`MovJ(x, y, z, r)`, `MovL(x, y, z, r)`), **30004** feedback. Se la coda di moto si blocca: `ClearError()` e `Continue()` sulla 29999. ⚠️ `EmergencyStop()` e `SpeedFactor(n)` da verificare nella versione del firmware.
- **Magician** (USB): `pip install pydobot` (non ufficiale), `Dobot(port=...)`, `move_to(x, y, z, r, wait=True)` ⚠️.
- **CR** (cobot a 6 assi): repo `Dobot-Arm/TCP-IP-CR-Python-V4` ⚠️ non verificato, stessa logica a porte.

### 4.4 Altri (solo orientamento, ⚠️ non verificati oggi)

| Braccio | Controllo da Python | Simulazione |
|---|---|---|
| Kinova Gen3 / Gen3 lite | Kortex API (wheel `kortex_api` scaricata da Kinova, non su PyPI) | MuJoCo Menagerie `kinova_gen3` |
| Franka FR3 / Panda | `libfranka` (C++, 1 kHz, kernel realtime); wrapper Python `franky`, `panda-py` | Menagerie `franka_fr3`, `franka_emika_panda` |
| igus ReBeL | Software iRC, protocollo CRI su Ethernet; driver ROS2 | iRC ha una simulazione integrata |
| WLKATA Mirobot | G-code su seriale (librerie `wlkatapython`, `mirobot-py`) | WLKATA Studio |
| Annin AR4 | Teensy su seriale, software ARCS (Python/Tk) | RoboDK ha il modello |

### 4.5 SO-100 / SO-101 con LeRobot

Bracci stampati in 3D con servo Feetech STS3215. `pip install 'lerobot[core_scripts,feetech]'` (LeRobot 0.6.1, **Python ≥ 3.12**, Apache-2.0); comandi `lerobot-teleoperate`, `lerobot-record`, `lerobot-train --policy.type=act`, `lerobot-rollout`. Modello MuJoCo: Menagerie `trs_so_arm100`. Dataset e policy pubbliche: [../event/track-resources.md](../event/track-resources.md#lerobot). LeRobot elenca anche plugin community per **UR5e**, xArm e Franka (`pip install lerobot_robot_<name>`) ⚠️ non provati.

## 5. Le skill come tool JSON per Grok

Formato **flat** `{"type":"function","name","description","parameters"}`: è quello della Responses API ([../grok-api/tools-and-structured-output.md](../grok-api/tools-and-structured-output.md)) ed è lo stesso da mettere in `session.tools` di Grok Voice ([../voice/tool-calling-in-voice.md](../voice/tool-calling-in-voice.md)). Con Responses usare `parallel_tool_calls: false`; in Voice il modello può emettere più call nella stessa risposta, e il wrapper le serializza comunque (lock + una sola azione pendente).

Regole incorporate:
- **Nessuna coordinata libera:** pose, zone e slot sono enum; l'unico numero è `distance_m` della spinta (1–15 cm), ricontrollato dal validatore.
- **Due fasi:** ogni skill di movimento restituisce `needs_confirmation` + `action_id` + la frase da dire; `arm_confirm(action_id)` esegue **solo se nell'ultima frase dell'operatore, arrivata dopo la proposta, c'è un sì** e non c'è un no. La traccia 04 chiede "voice confirmation before every movement": così la conferma è verificata dal codice, non dichiarata da Grok.
- **`arm_stop` sempre disponibile**, ma lo stop vero è locale (§6, §7).

```json
[
  {
    "type": "function",
    "name": "arm_go_to_pose",
    "description": "Propose moving the arm to one of the named, pre-calibrated poses. Does NOT move: returns an action_id that needs the operator's spoken confirmation (then call arm_confirm). If the arm is holding a tray, it carries the tray 10 cm above the target.",
    "parameters": {
      "type": "object",
      "properties": {
        "pose": {"type": "string", "enum": ["home", "left_zone", "work_zone", "right_zone", "reject_edge"], "description": "Named pose on the table."}
      },
      "required": ["pose"],
      "additionalProperties": false
    }
  },
  {
    "type": "function",
    "name": "arm_indicate",
    "description": "Propose pointing at a named zone with the tool tip, 3 cm above it, without touching. Does NOT move until arm_confirm.",
    "parameters": {
      "type": "object",
      "properties": {
        "target": {"type": "string", "enum": ["home", "left_zone", "work_zone", "right_zone", "reject_edge"]}
      },
      "required": ["target"],
      "additionalProperties": false
    }
  },
  {
    "type": "function",
    "name": "arm_lift_tray",
    "description": "Propose sliding the fork into the slotted tray in the given zone and lifting it by 4 cm. Only slotted trays can be lifted; never use it for objects without a tray. Does NOT move until arm_confirm.",
    "parameters": {
      "type": "object",
      "properties": {
        "slot": {"type": "string", "enum": ["left_zone", "work_zone", "right_zone"]}
      },
      "required": ["slot"],
      "additionalProperties": false
    }
  },
  {
    "type": "function",
    "name": "arm_put_down",
    "description": "Propose lowering the tray currently on the fork into the given zone and sliding the fork out. Only valid while holding a tray. Does NOT move until arm_confirm.",
    "parameters": {
      "type": "object",
      "properties": {
        "slot": {"type": "string", "enum": ["left_zone", "work_zone", "right_zone"]}
      },
      "required": ["slot"],
      "additionalProperties": false
    }
  },
  {
    "type": "function",
    "name": "arm_push",
    "description": "Propose pushing an object or tray sideways on the table with the pusher, starting from a zone, for a short distance. Does NOT move until arm_confirm.",
    "parameters": {
      "type": "object",
      "properties": {
        "from_zone": {"type": "string", "enum": ["left_zone", "work_zone", "right_zone"]},
        "direction": {"type": "string", "enum": ["left", "right"]},
        "distance_m": {"type": "number", "minimum": 0.01, "maximum": 0.15, "description": "Push distance in metres (1 to 15 cm)."}
      },
      "required": ["from_zone", "direction", "distance_m"],
      "additionalProperties": false
    }
  },
  {
    "type": "function",
    "name": "arm_confirm",
    "description": "Execute the pending action ONLY after the operator has explicitly said yes (e.g. 'si', 'confermo', 'vai') in their last utterance. The system re-checks the operator's words and rejects the call otherwise.",
    "parameters": {
      "type": "object",
      "properties": {
        "action_id": {"type": "string", "description": "The action_id returned by the proposing tool."}
      },
      "required": ["action_id"],
      "additionalProperties": false
    }
  },
  {
    "type": "function",
    "name": "arm_stop",
    "description": "Immediately stop any arm movement and cancel the pending action. Always safe; call it whenever the operator wants to stop or something looks wrong.",
    "parameters": {"type": "object", "properties": {}, "additionalProperties": false}
  },
  {
    "type": "function",
    "name": "arm_resume",
    "description": "Leave the halted state after a stop, only if the operator explicitly asked to resume and said 'confermo'.",
    "parameters": {"type": "object", "properties": {}, "additionalProperties": false}
  },
  {
    "type": "function",
    "name": "arm_status",
    "description": "Read the arm state: halted or ready, tray held, current tool and pose, protective or emergency stop. Use it before reporting what the arm did.",
    "parameters": {"type": "object", "properties": {}, "additionalProperties": false}
  }
]
```

Prompt di sistema (bozza, in inglese per il modello, dialogo in italiano):

```text
You are the voice assistant of a collaborative robot arm in a lab. Speak Italian, short sentences.
You can ONLY act through the arm_* tools. Movement tools never move the arm: they return an action_id
and a sentence. Read that sentence to the operator, wait for an explicit yes, then call arm_confirm.
If the request is ambiguous (which zone? which tray?) ask ONE clarifying question before proposing.
If a request is out of reach or not covered by a tool, say so and offer the closest safe skill.
Never invent coordinates. After each action call arm_status and report what the arm did.
If the operator says stop, fermo, basta or alt: call arm_stop immediately, then ask what to do.
```

## 6. Wrapper Python con mock (provato in mock)

Una sola interfaccia `driver` (`MockArm` / `URArm`), un validatore (enum + box di lavoro + `isPoseWithinSafetyLimits` del controller), un gate di conferma basato sulla trascrizione, un kill switch da tastiera, log JSONL per le metriche. Copiarlo in `src/` quando si sceglie la traccia.

```python
# arm_skills.py: whitelisted arm skills for Grok (Responses API or Grok Voice).
# Mock by default; --real uses ur_rtde (UR e-Series). Run --real only with staff present.
import json, re, sys, threading, time, uuid
from dataclasses import dataclass

# ---- 1. Calibrated data: filled in during the first slot (freedrive + getActualTCPPose) ----
# Poses in the robot base frame: [x, y, z, rx, ry, rz], metres + axis-angle radians (UR convention).
POSES = {
    "home":        [0.30, -0.10, 0.30, 3.14, 0.0, 0.0],
    "left_zone":   [0.35, -0.25, 0.15, 3.14, 0.0, 0.0],
    "work_zone":   [0.40,  0.00, 0.15, 3.14, 0.0, 0.0],
    "right_zone":  [0.35,  0.25, 0.15, 3.14, 0.0, 0.0],
    "reject_edge": [0.50,  0.30, 0.15, 3.14, 0.0, 0.0],
}
TRAY_SLOTS = ["left_zone", "work_zone", "right_zone"]   # where a slotted tray can sit
TOOLS_TCP = {   # printed tool: one TCP per tip, measured with the staff (metres from the flange) - placeholder values
    "tip":    [0.0, 0.0, 0.12, 0, 0, 0],
    "fork":   [0.0, 0.05, 0.08, 0, 0, 0],
    "pusher": [0.0, -0.05, 0.08, 0, 0, 0],
}
BOX = {"x": (0.20, 0.55), "y": (-0.35, 0.35), "z": (0.05, 0.40)}  # workspace box, measured on the table
MAX_LIN_SPEED = 0.10     # m/s for the whole demo (UR default moveL is 0.25)
MAX_LIN_ACC = 0.30       # m/s^2
LIFT_HEIGHT = 0.04       # m: how much the fork lifts a tray
FORK_APPROACH_X = -0.08  # m: the fork slides into the tray slots along +x (check the real geometry!)
MAX_PUSH = 0.15          # m
CONFIRM_RE = re.compile(r"\b(s[iì]|confermo|conferma|vai|procedi|ok|okay)\b", re.I)
DENY_RE = re.compile(r"\b(no|non|aspetta|annulla)\b", re.I)
STOP_RE = re.compile(r"\b(stop|fermo|ferma|fermati|alt|basta)\b", re.I)


class Rejected(Exception):
    pass


# ---- 2. Drivers: same interface for mock and real ----
class MockArm:
    def __init__(self):
        self.pose = list(POSES["home"]); self.tcp = "tip"; self._stop = threading.Event()
    def set_tool(self, name): self.tcp = name
    def move_l(self, pose, speed, acc):
        self._stop.clear()
        for _ in range(10):                      # ~1 s simulated motion, interruptible
            if self._stop.is_set():
                return False
            time.sleep(0.1)
        self.pose = list(pose); return True
    def stop(self): self._stop.set()
    def status(self): return {"pose": self.pose, "tool": self.tcp, "protective_stop": False, "emergency_stop": False}


class URArm:
    """UR e-Series via ur_rtde (pip install ur_rtde). The robot must be in Remote Control mode."""
    def __init__(self, ip):
        import rtde_control, rtde_receive
        self.c = rtde_control.RTDEControlInterface(ip)
        self.r = rtde_receive.RTDEReceiveInterface(ip)
        self.tcp = "tip"; self.c.setTcp(TOOLS_TCP["tip"])
    def set_tool(self, name):
        self.c.setTcp(TOOLS_TCP[name]); self.tcp = name
    def move_l(self, pose, speed, acc):
        if not self.c.isPoseWithinSafetyLimits(pose):
            raise Rejected("pose outside the robot safety limits")
        self.c.moveL(pose, speed, acc, True)       # asynchronous=True so stop() can interrupt
        time.sleep(0.1)                            # let the motion start before polling
        while not self.c.isSteady():               # True when the robot is fully at rest
            time.sleep(0.02)
        actual = self.r.getActualTCPPose()
        reached = max(abs(a - b) for a, b in zip(actual[:3], pose[:3])) < 0.002   # 2 mm
        return reached and not self.r.isProtectiveStopped()
    def stop(self): self.c.stopL(2.0, True)          # decelerate, non-blocking
    def status(self):
        return {"pose": self.r.getActualTCPPose(), "tool": self.tcp,
                "protective_stop": self.r.isProtectiveStopped(), "emergency_stop": self.r.isEmergencyStopped()}


# ---- 3. Skill executor: validator + confirmation gate + log ----
@dataclass
class Pending:
    action_id: str
    steps: list          # list of (tool, pose)
    summary: str
    kind: str
    args: dict
    created: float


class ArmSkills:
    def __init__(self, driver, log_path="arm_log.jsonl"):
        self.d = driver; self.lock = threading.Lock(); self.pending = None
        self.halted = False; self.holding_tray = None
        self.last_user_text, self.last_user_ts = "", 0.0
        self.log_path = log_path

    def log(self, **kw):
        with open(self.log_path, "a") as f:
            f.write(json.dumps({"ts": time.time(), **kw}, ensure_ascii=False) + "\n")

    # called by the voice loop on every user transcript (not by Grok)
    def on_user_text(self, text):
        self.last_user_text, self.last_user_ts = text, time.time()
        if STOP_RE.search(text):
            self.emergency_halt("voice keyword")

    # called by keyboard thread, voice keyword or UI button: never goes through the LLM
    def emergency_halt(self, source):
        self.halted = True; self.pending = None; self.d.stop()
        self.log(event="halt", source=source)

    @staticmethod
    def _check(pose):
        for i, ax in enumerate("xyz"):
            lo, hi = BOX[ax]
            if not lo <= pose[i] <= hi:
                raise Rejected(f"{ax}={pose[i]:.3f} m outside the workspace box {lo}..{hi}")

    @staticmethod
    def _off(pose, dx=0.0, dy=0.0, dz=0.0):
        p = list(pose); p[0] += dx; p[1] += dy; p[2] += dz; return p

    def _above(self, pose, dz):
        return self._off(pose, dz=dz)

    def _plan(self, name, a):
        if name == "arm_go_to_pose":
            if self.holding_tray:   # carry the tray: keep the fork and stay 10 cm above the target
                return [("fork", self._above(POSES[a["pose"]], 0.10))], f"porto il vassoio sopra {a['pose']}"
            return [("tip", POSES[a["pose"]])], f"vado in posizione {a['pose']}"
        if self.holding_tray and name in ("arm_indicate", "arm_push", "arm_lift_tray"):
            raise Rejected(f"holding the tray from {self.holding_tray}: put it down first")
        if name == "arm_indicate":
            p = POSES[a["target"]]
            return [("tip", self._above(p, 0.10)), ("tip", self._above(p, 0.03))], f"indico {a['target']}"
        if name == "arm_lift_tray":
            p, ax = POSES[a["slot"]], FORK_APPROACH_X
            # approach from the side, slide the fork into the slots, then lift
            return [("fork", self._off(p, dx=ax, dz=0.10)), ("fork", self._off(p, dx=ax)), ("fork", p),
                    ("fork", self._above(p, LIFT_HEIGHT))], f"sollevo il vassoio in {a['slot']} con la forchetta"
        if name == "arm_put_down":
            if not self.holding_tray: raise Rejected("not holding any tray")
            p, ax = POSES[a["slot"]], FORK_APPROACH_X
            # lower, slide the fork out of the slots, then go up (never lift straight up: it would take the tray)
            return [("fork", self._above(p, LIFT_HEIGHT)), ("fork", p), ("fork", self._off(p, dx=ax)),
                    ("fork", self._off(p, dx=ax, dz=0.10))], f"appoggio il vassoio in {a['slot']}"
        if name == "arm_push":
            dist = float(a["distance_m"])
            if not 0.01 <= dist <= MAX_PUSH: raise Rejected(f"push distance must be 0.01..{MAX_PUSH} m")
            p = POSES[a["from_zone"]]; sign = 1 if a["direction"] == "right" else -1
            end = list(p); end[1] += sign * dist
            return [("pusher", self._above(p, 0.08)), ("pusher", p), ("pusher", end), ("pusher", self._above(end, 0.08))], \
                   f"spingo da {a['from_zone']} verso {a['direction']} di {dist*100:.0f} cm"
        raise Rejected(f"unknown skill {name}")

    def call(self, name, args):
        """Entry point for every Grok tool call. Always returns a JSON-serialisable dict."""
        try:
            if name == "arm_stop":
                self.emergency_halt("grok"); return {"ok": True, "state": "halted"}
            if name == "arm_status":
                return {"ok": True, "halted": self.halted, "holding_tray": self.holding_tray, **self.d.status()}
            if name == "arm_resume":
                if not CONFIRM_RE.search(self.last_user_text):
                    raise Rejected("the operator must say 'confermo' to resume")
                self.halted = False; return {"ok": True, "state": "ready"}
            if self.halted:
                raise Rejected("arm halted by the operator: ask the operator to resume first")
            if name == "arm_confirm":
                return self._execute(args.get("action_id", ""))
            steps, summary = self._plan(name, args)
            for _, pose in steps:
                self._check(pose)
            self.pending = Pending(uuid.uuid4().hex[:6], steps, summary, name, args, time.time())
            self.log(event="proposed", skill=name, args=args, action_id=self.pending.action_id)
            return {"ok": True, "status": "needs_confirmation", "action_id": self.pending.action_id,
                    "say": f"Sto per: {summary}. Confermi?"}
        except KeyError as e:
            reason = f"unknown pose/slot/argument {e}: use only the enum values"
            self.log(event="rejected", skill=name, args=args, reason=reason)
            return {"ok": False, "reason": reason}
        except (Rejected, ValueError) as e:
            self.log(event="rejected", skill=name, args=args, reason=str(e))
            return {"ok": False, "reason": str(e)}

    def _execute(self, action_id):
        p = self.pending
        if p is None or p.action_id != action_id:
            raise Rejected("no pending action with this id: propose the skill again")
        # the "yes" must be in what the human said AFTER the proposal, not in what Grok claims.
        # The transcript can arrive after the function call: wait up to 1.5 s for it
        # (so call() must run in a worker thread, e.g. asyncio.to_thread, not in the event loop).
        deadline = time.time() + 1.5
        while self.last_user_ts < p.created and time.time() < deadline:
            time.sleep(0.05)
        said = self.last_user_text
        if self.last_user_ts < p.created or DENY_RE.search(said) or not CONFIRM_RE.search(said):
            raise Rejected("the operator did not confirm out loud: ask again")
        if not self.lock.acquire(blocking=False):
            raise Rejected("another movement is running")
        try:
            self.pending = None; t0 = time.time()
            for tool, pose in p.steps:
                if self.halted: raise Rejected("halted during the movement")
                if self.d.tcp != tool: self.d.set_tool(tool)
                if not self.d.move_l(pose, MAX_LIN_SPEED, MAX_LIN_ACC):
                    raise Rejected("movement interrupted (stop or protective stop)")
            if p.kind == "arm_lift_tray": self.holding_tray = p.args["slot"]
            if p.kind == "arm_put_down": self.holding_tray = None
            self.log(event="done", skill=p.kind, args=p.args, seconds=round(time.time() - t0, 2))
            return {"ok": True, "status": "done", "did": p.summary}
        finally:
            self.lock.release()


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("--real", metavar="ROBOT_IP"); a = ap.parse_args()
    if a.real and input("Staff present and e-stop in hand? type YES: ") != "YES":
        raise SystemExit("aborted")
    arm = ArmSkills(URArm(a.real) if a.real else MockArm())
    # keyboard kill switch: ENTER halts the arm (independent from the LLM)
    def keyboard():
        for _ in sys.stdin:
            arm.emergency_halt("keyboard")
    threading.Thread(target=keyboard, daemon=True).start()
    r = arm.call("arm_lift_tray", {"slot": "left_zone"}); print(r)
    arm.on_user_text("sì confermo")              # in the real loop: the user's transcript
    print(arm.call("arm_confirm", {"action_id": r["action_id"]}))
    print(arm.call("arm_push", {"from_zone": "work_zone", "direction": "right", "distance_m": 0.5}))
    print(arm.call("arm_status", {}))
```

```bash
python arm_skills.py                  # mock: propone, conferma, esegue, rifiuta una spinta da 50 cm
python arm_skills.py --real 192.168.x.y   # SOLO con lo staff accanto e Remote Control attivo
```

Esito del test mock (2026-11-03): sequenza lift → carry → put down → push eseguita; rifiutati correttamente spinta fuori limite, pose inesistente, conferma vecchia o con "no aspetta", conferma senza trascrizione (dopo 1,5 s), comandi mentre è in stato `halted`; uno "fermo!" a metà movimento interrompe il mock. ⚠️ `URArm.move_l` usa `isSteady()` dopo un `moveL` asincrono per capire quando ha finito: **provarlo in URSim** prima del robot vero (per i movimenti asincroni semplici `getAsyncOperationProgress()` potrebbe non dare progresso: gli header lo documentano per `movePath`).

## 7. Collegarlo a Grok Voice (traccia 04) e alla Responses API (tracce A, C)

Voice: partire da [../voice/examples/voice_agent_local.py](../voice/examples/voice_agent_local.py) e aggiungere tre ganci nel loop degli eventi (nomi degli eventi in [../voice/events-reference.md](../voice/events-reference.md)):

```python
# inside the realtime event loop (sketch, adapt to voice_agent_local.py)
arm = ArmSkills(MockArm())                       # or URArm(ip) with staff present
tools = json.load(open("tools_arm.json"))        # goes into session.update -> session.tools

if ev["type"] == "conversation.item.input_audio_transcription.updated":   # cumulative, needs grok-transcribe
    if STOP_RE.search(ev["transcript"]): arm.emergency_halt("voice partial")   # stop before the sentence ends
if ev["type"] == "conversation.item.input_audio_transcription.completed":
    arm.on_user_text(ev["transcript"])          # feeds the confirmation gate + stop keyword
if ev["type"] == "input_audio_buffer.speech_started" and arm.lock.locked():
    arm.emergency_halt("operator spoke during motion")   # optional, most conservative policy
if ev["type"] == "response.function_call_arguments.done":
    result = await asyncio.to_thread(arm.call, ev["name"], json.loads(ev["arguments"]))
    # -> conversation.item.create {type: function_call_output, call_id, output: json.dumps(result)}
    # -> response.create (after local playback has finished, see tool-calling-in-voice.md)
```

- **Lo stop non deve dipendere da Grok:** keyword sulla trascrizione parziale, tasto INVIO (thread `keyboard()`), e-stop fisico dello staff. La regola "chi parla durante il movimento lo ferma" è la più conservativa e la più facile da misurare (latenza `speech_started` → `stopL`). ⚠️ Latenza della trascrizione parziale non misurata.
- **Metriche per la giuria** (traccia 04): comandi corretti su 10, tempo fine frase → inizio movimento (`proposed`/`done` nel JSONL + timestamp degli eventi), gestione ambigui/fuori portata, affidabilità dello stop (N stop su N).
- **Responses API** (tracce A e C, con camera): stesso `ArmSkills.call` come dispatcher dei `function_call`; loop in [llm-robot-architecture.md §4](llm-robot-architecture.md#4-executor-kill-switch-e-loop-con-grok). Lì la conferma può essere un tasto o un click invece della voce: sostituire `on_user_text` con il pulsante dell'interfaccia.

## 8. Primo slot da 30 minuti: checklist

Prima (in URSim): skill provate end-to-end con mock e URSim, script pronto a leggere e salvare pose.

1. (2 min) Staff: chi tiene l'e-stop, area vietata, velocità massima ammessa.
2. (3 min) Modello, versione PolyScope, IP, Remote Control sì/no (`nc <ip> 29999`, `is in remote control`).
3. (5 min) TCP e payload delle tre punte (dall'installazione PolyScope o misurati).
4. (10 min) In freedrive (lo muove lo staff o il team con lo staff) registrare `home`, `left_zone`, `work_zone`, `right_zone`, `reject_edge` con `getActualTCPPose()` e salvarle in JSON. Misurare il box di lavoro e la geometria forchetta–fessure.
5. (5 min) Una skill alla volta al 10–30% di velocità; provare **lo stop** (tastiera e voce) e misurarne la latenza.
6. (5 min) Filmare tutto (serve alla traccia 05 e al pitch) e scrivere nel log cosa non ha funzionato.

## 9. Domande allo staff (aggiungere a [../ideas/staff-questions.md](../ideas/staff-questions.md))

1. Arm 1, 2 e 3: **marca, modello e versione software** di ciascuno? Sono gli UR3e/UR5e di Spazio Robot? E il terzo?
2. Possiamo comandarli **da laptop** (Remote Control, `ur_rtde`/RTDE, Dashboard 29999) o solo con programmi scritti sul pendant? Cosa intendete con "the arms' software"?
3. Su quale rete stanno i bracci? Il laptop si collega via cavo o Wi-Fi? IP fissi?
4. **TCP e payload** di forchetta, spintore e punta sono già configurati nell'installazione? Possiamo avere i file STL dell'utensile e le misure dei vassoi?
5. Che **limiti di sicurezza** sono configurati (velocità TCP, piani, modalità ridotta)? Possiamo leggerli?
6. Chi tiene l'**e-stop** durante gli slot? Possiamo collegare un nostro pulsante di stop (I/O digitale) o usare lo stop software?
7. Possiamo usare il **freedrive** per registrare le pose? Possiamo salvare programmi `.urp` sul robot?
8. Per la traccia 04: il "simulated arm that receives the same commands" fuori dagli slot è URSim o un vostro simulatore? Con quale interfaccia?
9. Per le tracce A e C: dove sono montate camera 1 e 2, che modello sono, come le leggiamo (USB, RTSP)? Sono fisse rispetto al tavolo?
10. Come si prenotano gli slot da 30 minuti e quanti ne ha ogni team?

## Fonti

- Tracce ufficiali: https://pavia.grokbot.it/tracks (copia del 2026-11-03 in [../event/raw/tracks.txt](../event/raw/tracks.txt)); PR #14 e `lib/tracks.ts` di https://github.com/aletheia/grok-bot-hackathon (PR #3: sponsor Spazio Robot; PR #4: disegno del braccio)
- Mail di Luca Bianchi del 3/11 (talk "Intro to cobots, dogs, drones and rovers"): [../event/raw/luca-bianchi-2026-11-03.md](../event/raw/luca-bianchi-2026-11-03.md)
- Spazio Robot: https://spaziorobot.com , https://spaziorobot.com/attrezzature , https://spaziorobot.com/attrezzature/universal-robots-ur3e (e `-ur5e`, `-ur10e`), https://spaziorobot.com/chi-siamo , https://spaziorobot.com/accesso-al-laboratorio , calendario CSV https://spaziorobot.com/api/public/availability (letto il 2026-11-03 alle 23:30 circa)
- Factory Accademia (unico riscontro): https://www.dailymotion.com/video/x8oawhp ⚠️
- UR client interfaces (porte): https://www.universal-robots.com/articles/ur/interface-communication/overview-of-client-interfaces/
- UR Remote Control via TCP/IP (Local vs Remote, porte chiuse in Local): https://www.universal-robots.com/articles/ur/interface-communication/remote-control-via-tcpip/ e https://forum.universal-robots.com/t/guide-and-example-ur-remote-control-via-tcpip/32973
- `ur_rtde`: https://gitlab.com/sdurobotics/ur_rtde (header `include/ur_rtde/*.h` letti oggi: firme, unità, default, flag), docs https://sdurobotics.gitlab.io/ur_rtde/ , PyPI https://pypi.org/project/ur-rtde/
- URSim Docker: https://hub.docker.com/r/universalrobots/ursim_e-series
- Driver ROS2 ufficiale UR: https://github.com/UniversalRobots/Universal_Robots_ROS2_Driver ; client RTDE ufficiale: https://github.com/UniversalRobots/RTDE_Python_Client_Library ; `python-urx` (LGPL-3.0, vecchio): https://github.com/SintefManufacturing/python-urx
- MuJoCo Menagerie: https://github.com/google-deepmind/mujoco_menagerie
- xArm: https://github.com/xArm-Developer/xArm-Python-SDK (doc `doc/api/xarm_api.md`)
- myCobot: https://github.com/elephantrobotics/pymycobot (doc `docs/MyCobot_280_en.md`)
- Dobot: https://github.com/Dobot-Arm/TCP-IP-4Axis-Python , https://github.com/luismesas/pydobot
- LeRobot: https://github.com/huggingface/lerobot
- Voce e tool calling: [../voice/](../voice/README.md); architettura: [llm-robot-architecture.md](llm-robot-architecture.md)
