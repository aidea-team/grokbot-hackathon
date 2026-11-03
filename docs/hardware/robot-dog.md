# Cane robot: come controllarlo da codice (e da Grok)

> **Verificato il:** 2026-11-03. README ed esempi letti direttamente dai repo GitHub. Versioni su PyPI a questa data: `unitree_webrtc_connect` 2.2.0, `djitellopy` 2.5.0.
> **Il modello reale del museo NON è noto** (vedi `museum-inventory.md`). Questa guida copre i candidati in ordine di probabilità.
> **Legenda:** ⚠️ = non verificato oppure dedotto.

## 0. Primi 10 minuti: identificare il robot

| Indizio | Modello |
|---|---|
| Quadrupede grigio e bianco di circa 15 kg, LiDAR a "cupola" sul muso, app **Unitree Go** | **Unitree Go2** |
| Go2 con dock di espansione sul dorso, porta Ethernet e computer Jetson | Go2 **EDU** (unico con secondary development ufficiale) |
| Quadrupede Unitree più vecchio, 5 camere stereo "a occhi" sul muso e sui fianchi, app Unitree Go1 | **Unitree Go1** |
| Robottino da tavolo da circa 20 cm, servo, scheda NyBoard o BiBoard | **Petoi Bittle** |
| Quadrupede Xiaomi nero o grigio | **Xiaomi CyberDog / CyberDog 2** |
| Grosso (circa 32 kg), giallo, con tablet di controllo | **Boston Dynamics Spot** (improbabile, ⚠️) |

**Cosa chiedere o leggere subito:** il numero di serie, la **versione firmware** (nell'app: Device → info), la variante (Air, Pro o EDU), se lo staff ha l'**account Unitree** a cui il robot è associato e se è disponibile il **telecomando**.

> Il firmware conta più del modello. Su **Go2 con firmware ≥ 1.1.15** la connessione WebRTC in LAN richiede una **chiave AES-128 per dispositivo**, recuperabile solo con le credenziali dell'account Unitree a cui il robot è associato. Senza quella chiave non ci si collega (vedi §1.2).

---

## 1. Unitree Go2 (il candidato più probabile ⚠️)

### 1.1 Varianti (dal sito Unitree)

| | AIR | PRO | X | EDU |
|---|---|---|---|---|
| Velocità | 0–2,5 m/s | 0–3,5 m/s | 0–3,7 m/s (max circa 5) | 0–3,7 m/s (max circa 5) |
| Peso | circa 15 kg | circa 15 kg | circa 15 kg | circa 15 kg |
| Batteria e autonomia | 8000 mAh, 1–2 h | 8000 mAh, 1–2 h | 8000 mAh, 1–2 h | 15000 mAh, 2–4 h |
| Camera HD grandangolare | sì | sì | sì | sì (più camera di profondità) |
| LiDAR 4D | sì | sì | sì | sì |
| Wi-Fi 6 | sì | sì | sì | sì |
| 4G e GPS | no | sì | sì | sì |
| Voice function | no | sì | sì | sì |
| Secondary development (ufficiale) | no | no | parziale | **sì** |
| Telecomando | opzionale | opzionale | incluso | incluso |

Nella pratica Air e Pro **sono programmabili** via WebRTC, lo stesso protocollo usato dall'app, con librerie community. Lo SDK ufficiale DDS su Ethernet (`unitree_sdk2`) è pensato per la EDU.

### 1.2 Strada A, consigliata per qualunque Go2: WebRTC con `unitree_webrtc_connect`

Il repo si chiamava `legion1581/go2_webrtc_connect`, oggi è `legion1581/unitree_webrtc_connect`. Supporta Go2 AIR, PRO ed EDU, oltre a G1 e R1, senza jailbreak.

Cosa offre su Go2:
- data channel pub/sub e RPC;
- comandi sport;
- video in ricezione;
- audio in invio e ricezione (lo speaker c'è su Pro ed EDU);
- decodifica del point cloud LiDAR;
- VUI (LED, volume, luminosità);
- AudioHub;
- obstacle avoidance API;
- discovery multicast.

```bash
sudo apt install -y python3-pip portaudio19-dev
pip install unitree_webrtc_connect opencv-python
```

**Modi di connessione:**

| Metodo | Quando | Note |
|---|---|---|
| `LocalAP` | Il PC si collega al **Wi-Fi del cane** (il robot fa da hotspot) | IP robot fisso `192.168.12.1` (dal codice del driver) |
| `LocalSTA` | Cane e PC sulla stessa LAN | Serve l'IP del cane (dall'app: Device → Data → Automatic Machine Inspection → STA Network: wlan0) oppure il seriale (discovery multicast) |
| `Remote` | Via TURN server Unitree | Servono SN, email e password dell'account Unitree, ⚠️ e Internet |

**Problemi da sapere:**
- **Un solo client WebRTC alla volta.** Se l'app Unitree Go è collegata compare `RobotBusyError`: **chiudere l'app** prima di connettersi.
- **Firmware ≥ 1.1.15:** serve `aes_128_key`. La si ottiene con `unitree-fetch-aes-key --email ... --password ... --device-type Go2`, che richiede l'account del proprietario. La chiave è per dispositivo e resta stabile. **Chiedere allo staff di recuperarla in anticipo.**
- **Firmware ≥ 1.1.7 usa "MCF"** (Multi-Control Framework): non serve il motion-switcher. Gli `api_id` base sono identici nei due mondi: Damp 1001, StopMove 1003, StandUp 1004, StandDown 1005, RecoveryStand 1006, Move 1008, Sit 1009, RiseSit 1010, SpeedLevel 1015, Hello 1016, Stretch 1017, Dance1 1022, Dance2 1023. **Flip e acrobazie hanno id diversi** (BackFlip è 1044 in normal e 2043 in MCF). Per noi è un motivo in più per **non esporle**.
- I `Move` sono **comandi di velocità** (`x` in m/s avanti, `y` in m/s laterale, `z` in rad/s di yaw), non di distanza. Per "cammina 2 secondi" si inviano Move in loop e poi `StopMove`. ⚠️ Non ho trovato documentato per quanto tempo il robot mantenga l'ultimo Move senza nuovi comandi, quindi va sempre inviato StopMove esplicito.

#### Snippet: connettersi, alzarsi, camminare, girare, sedersi

```python
# go2_basic.py: pip install unitree_webrtc_connect
import asyncio, json, os
from unitree_webrtc_connect.webrtc_driver import UnitreeWebRTCConnection, WebRTCConnectionMethod
from unitree_webrtc_connect.constants import RTC_TOPIC, SPORT_CMD

IP  = os.environ.get("UNITREE_ROBOT_IP")          # None se usiamo LocalAP
KEY = os.environ.get("UNITREE_AES_128_KEY")        # solo firmware >= 1.1.15

def make_conn():
    kw = {"aes_128_key": KEY} if KEY else {}
    if IP:
        return UnitreeWebRTCConnection(WebRTCConnectionMethod.LocalSTA, ip=IP, **kw)
    return UnitreeWebRTCConnection(WebRTCConnectionMethod.LocalAP, **kw)  # 192.168.12.1

async def sport(conn, name, parameter=None):
    payload = {"api_id": SPORT_CMD[name]}
    if parameter is not None:
        payload["parameter"] = parameter
    resp = await conn.datachannel.pub_sub.publish_request_new(RTC_TOPIC["SPORT_MOD"], payload)
    return resp["data"]["header"]["status"]["code"]   # 0 = ok

async def move_for(conn, vx=0.0, vy=0.0, vyaw=0.0, seconds=1.0, hz=10):
    """Velocity command ripetuto per `seconds`, poi StopMove."""
    try:
        for _ in range(int(seconds * hz)):
            await sport(conn, "Move", {"x": vx, "y": vy, "z": vyaw})
            await asyncio.sleep(1 / hz)
    finally:
        await sport(conn, "StopMove")

async def main():
    conn = make_conn()
    await conn.connect()

    # Firmware < 1.1.7: assicurarsi di essere in modalità "normal".
    # Con MCF (>= 1.1.7) questa richiesta può non servire o fallire: va ignorata.
    try:
        r = await conn.datachannel.pub_sub.publish_request_new(
            RTC_TOPIC["MOTION_SWITCHER"], {"api_id": 1001})
        mode = json.loads(r["data"]["data"])["name"]
        if mode != "normal":
            await conn.datachannel.pub_sub.publish_request_new(
                RTC_TOPIC["MOTION_SWITCHER"], {"api_id": 1002, "parameter": {"name": "normal"}})
            await asyncio.sleep(5)
    except Exception as e:
        print("motion switcher non disponibile (MCF?)", e)

    await sport(conn, "StandUp");      await asyncio.sleep(2)
    await sport(conn, "BalanceStand"); await asyncio.sleep(1)
    await sport(conn, "Hello");        await asyncio.sleep(3)
    await move_for(conn, vx=0.3, seconds=2)       # avanti a 0,3 m/s per 2 s
    await move_for(conn, vyaw=0.6, seconds=2)     # rotazione a sinistra a circa 0,6 rad/s
    await sport(conn, "Sit");          await asyncio.sleep(3)
    await sport(conn, "RiseSit");      await asyncio.sleep(2)
    await sport(conn, "StandDown")                # si accuccia (sicuro, motori ancora attivi)

asyncio.run(main())
```

⚠️ Il segno di `z` (positivo = rotazione antioraria, cioè a sinistra) segue la convenzione ROS. Va verificato a bassa velocità al primo test.

#### Snippet: prendere un frame dalla camera (da dare a Grok vision)

```python
# go2_frame.py: il video arriva come track WebRTC (aiortc)
import asyncio, cv2, base64
from unitree_webrtc_connect.webrtc_driver import UnitreeWebRTCConnection, WebRTCConnectionMethod

latest = {"img": None}

async def on_track(track):
    while True:
        frame = await track.recv()
        latest["img"] = frame.to_ndarray(format="bgr24")

async def main():
    conn = UnitreeWebRTCConnection(WebRTCConnectionMethod.LocalAP)
    await conn.connect()
    conn.video.switchVideoChannel(True)
    conn.video.add_track_callback(on_track)
    while latest["img"] is None:
        await asyncio.sleep(0.1)
    ok, jpg = cv2.imencode(".jpg", latest["img"], [cv2.IMWRITE_JPEG_QUALITY, 70])
    b64 = base64.b64encode(jpg.tobytes()).decode()
    print("data:image/jpeg;base64," + b64[:60], "...")  # da passare come image input a Grok
    cv2.imwrite("go2_frame.jpg", latest["img"])

asyncio.run(main())
```

Nell'app finale conviene **una sola connessione** condivisa tra video, comandi e audio, in un unico event loop asyncio. Due client WebRTC non possono coesistere.

#### Audio e speaker (TTS di Grok dal cane)

Lo speaker del Go2 si raggiunge aggiungendo una traccia audio alla peer connection (esempio `examples/go2/audio/mp3_player/play_mp3.py`):

```python
from aiortc.contrib.media import MediaPlayer
player = MediaPlayer("grok_tts.wav")      # file prodotto dal TTS di Grok
conn.pc.addTrack(player.audio)
```

⚠️ Secondo il README di `go2_webrtc_connect`, quello vecchio, il canale audio funziona solo su Pro ed EDU. Esiste anche `live_recv_audio.py` per **ricevere il microfono del cane**, che potrebbe alimentare Grok Voice (⚠️ qualità e latenza non provate).

#### LiDAR, ostacoli, LED

- LiDAR: `conn.datachannel.pub_sub.publish_without_callback("rt/utlidar/switch", "on")`, poi `subscribe("rt/utlidar/voxel_map_compressed", cb)` con `conn.datachannel.set_decoder(decoder_type='libvoxel')`. Utile soprattutto per una "distanza minima frontale" da usare nel validatore.
- Obstacle avoidance integrata: topic `rt/api/obstacles_avoid/request` (`OBSTACLES_AVOID_API["SWITCH_SET"]` con `{"enable": True}`). In MCF c'è anche `SwitchAvoidMode` (2058) e `FreeAvoid` (2048). **Tenerla accesa.**
- VUI (LED, volume): topic `rt/api/vui/request`, esempio `examples/go2/data_channel/vui/vui.py`.

### 1.3 Strada B, solo EDU: `unitree_sdk2_python` (DDS su Ethernet)

- Richiede `cyclonedds==0.10.2`. Se `pip install -e .` non la trova, va compilata (`releases/0.10.x`) e si imposta `CYCLONEDDS_HOME`.
- Si collega il PC alla porta Ethernet del cane con IP statico nella subnet `192.168.123.x/24`. ⚠️ Secondo repo community il Go2 sta su `192.168.123.161`: va verificato con la Quick start ufficiale, che non sono riuscito a leggere perché la pagina si carica via JS.
- **Low-level control:** prima va disattivato `sport_mode` dall'app, altrimenti i comandi vanno in conflitto. **Noi non lo useremo.**

```python
# go2_sdk2.py <iface>   es. python go2_sdk2.py enp2s0
import sys, time
from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.go2.sport.sport_client import SportClient
from unitree_sdk2py.go2.video.video_client import VideoClient

ChannelFactoryInitialize(0, sys.argv[1])
sport = SportClient(); sport.SetTimeout(10.0); sport.Init()
video = VideoClient(); video.SetTimeout(3.0); video.Init()

sport.StandUp(); time.sleep(2)
sport.BalanceStand(); time.sleep(1)
t0 = time.time()
while time.time() - t0 < 2.0:            # avanti 2 s
    sport.Move(0.3, 0.0, 0.0); time.sleep(0.1)
sport.StopMove()
t0 = time.time()
while time.time() - t0 < 2.0:            # gira
    sport.Move(0.0, 0.0, 0.6); time.sleep(0.1)
sport.StopMove()
code, data = video.GetImageSample()      # JPEG in bytes
if code == 0:
    open("frame.jpg", "wb").write(bytes(data))
sport.Sit(); time.sleep(3); sport.RiseSit(); time.sleep(2); sport.StandDown()
```

Metodi disponibili in `SportClient`: `Damp, BalanceStand, StopMove, StandUp, StandDown, RecoveryStand, Euler, Move, Sit, RiseSit, SpeedLevel, Hello, Stretch, Content, Dance1, Dance2, SwitchJoystick, Pose, Scrape, FrontFlip, FrontJump, FrontPounce, Heart, LeftFlip, BackFlip, FreeWalk, FreeBound, FreeJump, FreeAvoid, WalkUpright, CrossStep, StaticWalk, TrotRun, HandStand, ClassicWalk, AutoRecoverySet/Get, SwitchAvoidMode`. Altri client: `ObstaclesAvoidClient`, `VuiClient`, LiDAR switch.

### 1.4 Strada C: ROS2 (`abizovnuralem/go2_ros2_sdk`)

- Supporta AIR, PRO ed EDU via WebRTC (Wi-Fi) oppure CycloneDDS (Ethernet).
- Funziona con ROS2 Humble, Iron o Rolling su Ubuntu 22.04, ed è disponibile un Docker compose (`ROBOT_IP=... CONN_TYPE=webrtc docker-compose up`).
- Offre camera, LiDAR in PointCloud2, SLAM, nav2, foxglove e object detection.
- Anche qui **va chiusa l'app** prima di connettersi.
- Conviene solo se qualcuno del team conosce già ROS2: per un hackathon di 30 ore la Strada A è molto più rapida.

### 1.5 Sicurezza e limiti Go2

| Comando | Effetto | Uso |
|---|---|---|
| `StopMove` (1003) | Azzera la velocità, resta in piedi | **Stop software primario** |
| `StandDown` (1005) | Si accuccia in modo controllato | Fine sessione o soft e-stop |
| `Damp` (1001) | **Motori senza coppia: il cane crolla a terra** | Solo emergenza vera, oppure da accucciato. ⚠️ Da in piedi cade |
| `RecoveryStand` (1006) | Si rialza dopo una caduta | Solo con un operatore |
| `SpeedLevel` (1015) | Livello di velocità | Impostare il minimo all'avvio ⚠️ (valori ammessi non verificati) |

- **Il telecomando fisico** (incluso su X ed EDU, opzionale su Air e Pro) resta in mano a un operatore umano come **override**. ⚠️ Comportamento esatto dell'e-stop da telecomando non verificato: chiederlo allo staff.
- **Limiti da imporre nel nostro validatore** (vedi `llm-robot-architecture.md`): |vx| ≤ 0,4 m/s, |vy| ≤ 0,3 m/s, |vyaw| ≤ 0,8 rad/s, durata ≤ 3 s per comando. **Mai** flip, salti, handstand o pounce in un museo pieno di persone e vetrine.
- Il robot pesa circa 15 kg con zampe in alluminio: può ferire caviglie e mani. Serve un'area delimitata.

### 1.6 Voce e LLM già integrati

- Il Go2 Pro ha una "voice function" e un assistente vocale (nella community chiamato **"BenBen"**) con funzioni GPT pubblicizzate al lancio.
- ⚠️ Fonti di terze parti sono in conflitto: una guida Indro dice che la voce offline supporta **solo il cinese**, un retailer dice solo l'inglese. Una fonte afferma che serve Internet, un'altra no. Un blog WSO2 la descrive come "limited and not customizable".
- **Implicazione:** non contare sull'assistente integrato. Grok va fatto girare sul laptop (microfono del laptop o del cane, poi Grok Voice, poi tool, poi WebRTC) e si usa lo speaker del cane solo come uscita audio.

### 1.7 Simulazione prima del reale

- **`unitreerobotics/unitree_mujoco`** (ufficiale) è un simulatore MuJoCo che parla lo stesso DDS di `unitree_sdk2`. È utile per la Strada B. ⚠️ Non l'ho provato.
- Per la Strada A la cosa più rapida è un **mock driver** con la stessa interfaccia (`stand_up()`, `move(vx, vy, vyaw, s)`, `sit()`, `get_frame()`) che fa log e simula la posa 2D. Il codice Grok e tool si sviluppa contro il mock e si passa al driver reale con un flag `--real`. Vedi `llm-robot-architecture.md`.

---

## 2. Unitree Go1 (se il museo ha un modello più vecchio)

- **Ufficiale:** `unitree_legged_sdk` (v3.8.x per Go1), pensato per la EDU.
- **Community:** `Bin4ry/free-dog-sdk` funziona con high-level e low-level su Air, Pro, Max ed EDU via UDP. Il README avverte che **non include le safety features** dello SDK originale.
- Rete: hotspot del cane, password di default `00000000` (dal README), cane su `192.168.12.1`, PC su `192.168.12.x`.
- Il modulo `go1pylib` (PyPI) offre un wrapper più semplice basato su MQTT. ⚠️ Non provato.

```python
# free-dog-sdk, high-level: estratto dagli esempi del repo
from ucl.highCmd import highCmd
from ucl.unitreeConnection import unitreeConnection, HIGH_WIFI_DEFAULTS
from ucl.enums import MotorModeHigh, GaitType
import time
conn = unitreeConnection(HIGH_WIFI_DEFAULTS); conn.startRecv()
hcmd = highCmd(); conn.send(hcmd.buildCmd())          # handshake
t0 = time.time()
while time.time() - t0 < 2:                           # cammina avanti 2 s
    hcmd.mode = MotorModeHigh.VEL_WALK                # enum verificati in ucl/enums.py
    hcmd.gaitType = GaitType.TROT
    hcmd.velocity = [0.2, 0.0]; hcmd.yawSpeed = 0.0
    conn.send(hcmd.buildCmd()); time.sleep(0.002)
hcmd.mode = MotorModeHigh.IDLE; hcmd.velocity = [0, 0]; conn.send(hcmd.buildCmd())
```

Lo snippet è derivato da `example_walk(highlevel).py` (loop a circa 500 Hz con `sleep(0.002)`). Altri modi in `MotorModeHigh`: `FORCE_STAND`, `STAND_DOWN`, `STAND_UP`, `DAMPING`, `RECOVERY`, `DANCE1` e `DANCE2`.
Camera del Go1: 5 camere stereo gestite da Jetson e Raspberry Pi interni. L'accesso richiede SSH nei moduli interni ⚠️, quindi conviene usare una **webcam USB o del telefono** come "occhi".

## 3. Petoi Bittle (se è un cane da tavolo)

- Firmware OpenCat. Comandi testuali seriali via USB o Bluetooth.
- Token principali: `kbalance`, `ksit`, `krest`, `kwkF` (cammina avanti), `kwkL` e `kwkR` (curva), `ktrL`, `khi` (saluto), `m0 30` (muove il servo 0). ⚠️ `d` compare nella lista dei comandi ma la doc non ne spiega l'effetto. ⚠️ Baud rate non confermato dalla pagina letta (comunemente 115200).

```python
import serial, time
s = serial.Serial("/dev/ttyUSB0", 115200, timeout=1)   # ⚠️ porta e baud da verificare
for tok in ["kbalance", "khi", "kwkF"]:
    s.write((tok + "\n").encode()); time.sleep(2)
s.write(b"kbalance\n"); time.sleep(1); s.write(b"krest\n")
```

Bittle è leggero e innocuo: ottimo per una demo LLM sicura. Alcune versioni hanno una camera AI opzionale ⚠️, altrimenti si usa una webcam esterna.

## 4. Xiaomi CyberDog / CyberDog 2

- Software open source ROS2 (`MiRoboticsLab/cyberdog_ws`, ultimo push aprile 2025). Lo sviluppo richiede di ottenere permessi dev/SSH dall'app Xiaomi. ⚠️ Non approfondito, priorità bassa.

## 5. Boston Dynamics Spot

- `pip install bosdyn-client bosdyn-mission bosdyn-choreography-client` (repo `boston-dynamics/spot-sdk`).
- Flusso obbligatorio: autenticazione, **lease** (si prende il controllo esclusivo), **E-Stop endpoint** (serve un client e-stop attivo, altrimenti i motori non si accendono), `power_on`, `blocking_stand`, comandi via `RobotCommandBuilder.synchro_velocity_command(v_x, v_y, v_rot)`.
- ⚠️ Molto improbabile in un museo no-profit. Non approfondito.

---

## 6. Troubleshooting rapido Go2

| Sintomo | Causa probabile |
|---|---|
| `RobotBusyError` | App Unitree Go aperta su un telefono: chiuderla oppure togliere il Wi-Fi al telefono |
| `AesKeyRequiredError` o `AesKeyRejectedError` | Firmware ≥ 1.1.15: serve la chiave dell'account proprietario |
| `LocalSignalingPortError` | IP sbagliato o non raggiungibile: il driver prova le porte 9991 e 8081 |
| Comandi accettati ma il cane non si muove | Non è in piedi o in BalanceStand, è in un'altra motion mode, oppure il telecomando ha preso il controllo ⚠️ |
| Video nero | Manca `switchVideoChannel(True)`, oppure il loop asyncio è bloccato da codice sincrono (OpenCV o input) |

## Fonti

- Unitree Go2, pagina prodotto e tabella varianti: https://www.unitree.com/go2
- `legion1581/unitree_webrtc_connect` (README, `constants.py`, `webrtc_driver.py`, esempi `examples/go2/*`): https://github.com/legion1581/unitree_webrtc_connect
- PyPI `unitree_webrtc_connect`: https://pypi.org/project/unitree-webrtc-connect/
- `tfoldi/go2-webrtc` (progetto originale): https://github.com/tfoldi/go2-webrtc
- `unitreerobotics/unitree_sdk2_python` (README, `example/go2/*`, `go2/sport/sport_client.py`): https://github.com/unitreerobotics/unitree_sdk2_python
- `unitreerobotics/unitree_sdk2`: https://github.com/unitreerobotics/unitree_sdk2
- Documentazione Unitree (Quick start, sports services): https://support.unitree.com/home/en/developer/Quick_start, https://support.unitree.com/home/en/developer/sports_services (⚠️ non leggibili via fetch, pagina JS)
- `unitreerobotics/unitree_mujoco`: https://github.com/unitreerobotics/unitree_mujoco
- `abizovnuralem/go2_ros2_sdk`: https://github.com/abizovnuralem/go2_ros2_sdk
- `phospho-app/go2_webrtc_connect` (fork, nota sull'audio solo per Pro ed EDU): https://github.com/phospho-app/go2_webrtc_connect
- Voce e "BenBen" (terze parti, in conflitto tra loro): https://indrorobotics.notion.site/Operate-Your-GO2-46498f43491c444a9821d28a91d9db7d, https://wso2.com/library/blogs/how-we-gave-life-to-an-ai-agent-with-unitree-go2-robot/, https://newatlas.com/robotics/unitree-go2-robot-dog-gpt/
- Go1, `Bin4ry/free-dog-sdk`: https://github.com/Bin4ry/free-dog-sdk
- Petoi, serial protocol: https://docs.petoi.com/apis/serial-protocol ; OpenCat: https://github.com/PetoiCamp/OpenCat-Quadruped-Robot
- CyberDog: https://github.com/MiRoboticsLab/cyberdog_ws
- Spot SDK: https://github.com/boston-dynamics/spot-sdk
