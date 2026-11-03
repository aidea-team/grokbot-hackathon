# Droni indoor: come controllarli da codice (e da Grok)

> **Verificato il:** 2026-11-03. Tello SDK 2.0 User Guide letta in PDF. README e codice letti da GitHub. Versioni su PyPI a questa data: `djitellopy` 2.5.0, `cflib` 0.1.34, `mavsdk-grpc` 4.0.5.
> **I modelli di droni del museo NON sono noti.** Il sito dice solo "A few drones" (vedi `museum-inventory.md`).
> **Legenda:** ⚠️ = non verificato oppure dedotto.

## 0. Identificazione rapida e priorità

| Se vediamo... | È probabilmente | Programmabile da laptop in un hackathon? |
|---|---|---|
| Drone bianco di circa 80 g, Wi-Fi `TELLO-XXXXXX`, marchio Ryze o DJI | **Tello** | **Sì, facilissimo** (SDK UDP testuale) |
| Come sopra ma nero o grigio, scritta "EDU", mission pad colorati | **Tello EDU** | **Sì**, più station mode, swarm e mission pad |
| Micro-drone da circa 30 g su PCB, dongle USB Crazyradio | **Bitcraze Crazyflie 2.x** | Sì (`cflib`), ma serve il Flow deck o un positioning system per l'hover stabile |
| DJI Mini, Air o Mavic con radiocomando | DJI consumer | **Difficile**: solo MSDK Android, Kotlin o Java, per modelli specifici |
| Parrot Anafi | Parrot | Sì (Olympe, Python, solo Linux) ⚠️ |
| Drone "custom" con Pixhawk o flight controller, telemetria | PX4 o ArduPilot | Sì (MAVSDK, pymavlink), ma **indoor senza GPS è delicato** |

**Raccomandazione:** con Tello o Tello EDU la demo "Grok pilota il drone" è fattibile in poche ore. Con altri modelli va valutato alla kick-off se conviene.

---

## 1. DJI / Ryze Tello e Tello EDU (il candidato più probabile ⚠️)

### 1.1 Protocollo (Tello SDK 2.0, verificato sul PDF ufficiale)

| Canale | Direzione | Indirizzo |
|---|---|---|
| Comandi e risposte | PC → `192.168.10.1:8889` UDP | risposta `ok` / `error` |
| Stato (telemetria) | Tello → PC `0.0.0.0:8890` UDP | stringa `pitch:..;roll:..;yaw:..;vgx..;tof:..;h:..;bat:..;baro:..;time:..;agx..` |
| Video H.264 | Tello → PC `0.0.0.0:11111` UDP | dopo `streamon` |

Comandi principali, con range dal PDF:

| Comando | Range | Note |
|---|---|---|
| `command` | n/a | Entra in SDK mode (va inviato per primo) |
| `takeoff` / `land` | n/a | |
| `emergency` | n/a | **Spegne i motori subito: il drone cade** |
| `stop` | n/a | **Hover immediato, "works at any time"** |
| `up/down/left/right/forward/back x` | x = 20–500 cm | Bloccante fino al completamento |
| `cw x` / `ccw x` | x = 1–360° | |
| `go x y z speed` | x, y, z = -500..500, speed = 10–100 cm/s | x, y, z non possono essere tutti tra -20 e 20 |
| `rc a b c d` | -100..100 per ciascun canale | Joystick virtuale (lr, fb, ud, yaw), va inviato in continuo |
| `speed x` | 10–100 cm/s | |
| `streamon` / `streamoff` | n/a | |
| `battery?`, `speed?`, `time?`, `wifi?`, `sdk?`, `sn?` | n/a | Letture |
| `ap ssid pass` | n/a | **Solo EDU**: entra in station mode su un router |
| `mon` / `moff` / `mdirection x` | n/a | **Solo EDU**: mission pad |
| `flip l/r/f/b` | n/a | **Da non esporre a Grok** |

**Safety feature del firmware:** *"If there is no command for 15 seconds, the Tello will land automatically."* Di conseguenza:
- durante le pause in cui Grok "pensa" serve un keepalive (in DJITelloPy c'è `send_keepalive()`);
- in caso di crash del nostro software il Tello atterra da solo entro 15 s, e questo è un vantaggio.

**Reset Wi-Fi:** tenere premuto il tasto di accensione per 5 s. Di default il Wi-Fi non ha password.

### 1.2 Libreria: `djitellopy`

```bash
pip install djitellopy opencv-python
```

Il laptop deve essere collegato al **Wi-Fi del Tello** (`TELLO-XXXXXX`), e quindi in quel momento **non ha Internet per Grok**. Soluzioni:
1. **seconda interfaccia Wi-Fi** (dongle USB), una sul Tello e una su Internet: è la soluzione più semplice;
2. **Ethernet o tethering USB** del telefono per Internet e Wi-Fi integrato sul Tello;
3. **Tello EDU in station mode** (`ap ssid pass`), così Tello e laptop stanno sullo stesso router con Internet.

⚠️ Va verificato come gestisce le route il sistema operativo: la rete del Tello è `192.168.10.0/24` senza gateway, quindi il traffico verso Internet deve uscire dall'altra interfaccia.

#### Snippet: decollo, movimento, frame, atterraggio, emergenza

```python
# tello_basic.py
import cv2, time
from djitellopy import Tello

t = Tello()
t.connect()                         # invia "command", attende lo stato
print("battery %", t.get_battery())
assert t.get_battery() >= 30, "batteria troppo bassa"

t.streamon()
fr = t.get_frame_read()             # thread in background (PyAV)

try:
    t.takeoff()
    t.move_forward(50)              # cm, range 20-500
    t.rotate_clockwise(90)          # gradi, range 1-360
    t.move_up(30)
    img = fr.frame                  # numpy array (via PIL: ordine RGB, ⚠️ vedi nota)
    cv2.imwrite("tello_frame.jpg", cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
    t.land()
except KeyboardInterrupt:
    t.emergency()                   # i motori si spengono: il drone CADE
    raise
except Exception:
    t.stop()                        # hover
    t.land()
    raise
finally:
    t.streamoff()
    t.end()
```

⚠️ Nota sul colore: in `djitellopy` 2.5.0 `BackgroundFrameRead` usa `np.array(frame.to_image())`, cioè un'immagine PIL in RGB. L'esempio ufficiale `take-picture.py` salva direttamente con `cv2.imwrite` (quindi con colori invertiti). Se i colori sembrano sbagliati va invertita la conversione.

Altri metodi utili: `go_xyz_speed(x, y, z, speed)`, `send_rc_control(lr, fb, ud, yaw)` (da -100 a 100), `set_speed(x)`, `get_height()`, `get_distance_tof()`, `send_keepalive()`, `set_video_direction(Tello.CAMERA_DOWNWARD)` (camera verso il basso in scala di grigi 320x240, ⚠️ solo su alcuni firmware o modelli).

#### Kill switch da tastiera (thread separato)

```python
import threading, sys, termios, tty
def kill_switch(tello):
    fd = sys.stdin.fileno(); old = termios.tcgetattr(fd); tty.setcbreak(fd)
    try:
        while True:
            c = sys.stdin.read(1)
            if c == " ":  tello.stop(); print("HOVER")   # spazio = hover
            if c == "l":  tello.land()                   # l = land
            if c == "k":  tello.emergency(); print("KILL")  # k = motori off
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
threading.Thread(target=kill_switch, args=(t,), daemon=True).start()
```

⚠️ `djitellopy` serializza i comandi e attende la risposta (timeout 7 s, 20 s per `takeoff`). Un `stop` inviato mentre un `move_forward` bloccante è in corso potrebbe aspettare. Per un e-stop affidabile, usare un **socket UDP separato** che invia `"stop"` o `"emergency"` direttamente a `192.168.10.1:8889`:

```python
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.sendto(b"emergency", ("192.168.10.1", 8889))   # oppure b"stop" / b"land"
```

⚠️ Con un secondo socket la risposta del Tello arriva alla porta sorgente del secondo socket. Il comando viene comunque eseguito, e questo vale anche se il socket principale di djitellopy è occupato.

### 1.3 Tello EDU: station mode e swarm

```python
from djitellopy import Tello, TelloSwarm
t = Tello(); t.connect(); t.connect_to_wifi("SSID_ROUTER", "PASSWORD")   # il Tello si riavvia
# ...dopo il reboot, trovare gli IP dal DHCP del router
swarm = TelloSwarm.fromIps(["192.168.1.42", "192.168.1.43"])
swarm.connect(); swarm.takeoff()
swarm.move_up(50)                                              # in parallelo
swarm.sequential(lambda i, tl: tl.move_forward(i * 20 + 20))   # uno alla volta
swarm.parallel(lambda i, tl: tl.move_left(i * 50 + 20))
swarm.land(); swarm.end()
```

- `connect_to_wifi` e `ap` funzionano **solo su EDU**, così come i mission pad.
- **Video in station mode:** il README di `djitellopy` dice "video streaming is not available" (TODO). Il docstring di `streamon()` dice invece che "Tello EDUs support video streaming while connected to a WiFi-network via SDK 3". ⚠️ Con più droni tutti inviano video sulla porta 11111: serve SDK 3 con il comando `port`, oppure `set_network_ports`. Non verificato.
- Mission pad: `t.enable_mission_pads()`, poi `go_xyz_speed_mid(x, y, z, speed, mid)` per una localizzazione indoor **assoluta** rispetto al pad (serve luce buona). È ottimo per un geofence reale.

### 1.4 Limiti pratici del Tello indoor

- Usa un sensore ottico (VPS) verso il basso. Su pavimenti lucidi, uniformi o bui deriva. ⚠️ Bisogna chiedere o verificare il tipo di pavimento del museo.
- Autonomia di circa 13 minuti ⚠️ (dato del datasheet Ryze, non verificato oggi): servono **batterie di ricambio e un hub di ricarica**.
- Comandi `move` con distanza minima di 20 cm, quindi niente micro-correzioni. Per il tracking usare `rc`.
- `ccw` ha range 1–360 nel PDF (il docstring di `djitellopy` dice "1-3600", probabile refuso).

---

## 2. Bitcraze Crazyflie 2.x (`cflib`)

- Serve il dongle **Crazyradio (PA o 2.0)** e le udev rules su Linux (vedi `docs/installation/install.md` del repo).
- Per il volo "a comando" (MotionCommander) serve un **Flow deck v2**, oppure Lighthouse, Loco o mocap.
- Il firmware recente richiede **arming** esplicito (`supervisor.send_arming_request(True)`).
- Non ha camera, salvo l'**AI deck** opzionale (GAP8 e Wi-Fi). ⚠️ Lo streaming non l'ho approfondito.

```python
# cf_basic.py: pip install cflib
import time, cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.positioning.motion_commander import MotionCommander
from cflib.utils import uri_helper

URI = uri_helper.uri_from_env(default="radio://0/80/2M/E7E7E7E7E7")
cflib.crtp.init_drivers()
with SyncCrazyflie(URI, cf=Crazyflie(rw_cache="./cache")) as scf:
    scf.cf.supervisor.send_arming_request(True); time.sleep(1.0)
    try:
        with MotionCommander(scf, default_height=0.5) as mc:   # decollo automatico a 0,5 m
            time.sleep(1)
            mc.forward(0.5)          # metri
            mc.turn_left(90)         # gradi
            mc.up(0.2)
            time.sleep(1)
        # all'uscita dal with: atterraggio automatico
    except KeyboardInterrupt:
        scf.cf.supervisor.send_emergency_stop()   # kill motori
        raise
```

API di emergenza in `cflib`: `cf.supervisor.send_emergency_stop()`, `cf.supervisor.send_emergency_stop_watchdog()`, `cf.loc.send_emergency_stop()`, `cf.commander.send_stop_setpoint()`. Simulazione: ⚠️ esistono simulatori community (Crazyswarm2 o CrazySim), non provati.

---

## 3. DJI Mini, Air o Mavic (MSDK)

- **DJI Mobile SDK V5** (ultima versione 5.18.0 secondo il README del repo `dji-sdk/Mobile-SDK-Android-V5`) è **solo Android**: serve un'app in Kotlin o Java sul telefono collegato al radiocomando.
- Prodotti supportati (README V5): **Mini 3, Mini 3 Pro, Mini 4 Pro** (secondo Dronezine e DroneDJ, con Mini 4 Pro funziona **solo con radiocomando RC-N2**), Mavic 3 Enterprise, Mavic 3TA, Matrice 4D/4TD, M30, M350 e altri modelli enterprise.
- ⚠️ **Non supportati in V5** (o non elencati): Mini 2, Mini SE, Mini 4K, Air 2S, Air 3, Avata e i modelli più recenti. MSDK **V4** supportava alcuni modelli vecchi come Mini 2 e Mini SE ⚠️ (non verificato oggi).
- **Strategia per l'hackathon, se capita un DJI supportato:** usare l'app Sample MSDK, aggiungere un piccolo server WebSocket o HTTP nell'app Android ed esporre `takeoff`, `land` e virtual stick, poi farlo pilotare dal laptop e da Grok. Serve una **DJI developer app key**, va registrata prima. Stima realistica: **una giornata per chi conosce Android**. Sconsigliato se c'è un Tello disponibile.
- Indoor: senza GPS va in ATTI o usa il vision positioning. I DJI sono più pesanti e veloci dei Tello, quindi **rischio molto maggiore**.

## 4. Parrot (Anafi): Olympe

- Repo `Parrot-Developers/olympe`, Python su Linux. Supporta Anafi, Anafi USA e Anafi Ai ⚠️. Esiste il simulatore **Parrot Sphinx**.
- Snippet ⚠️ (dalla documentazione Olympe a memoria, **non verificato oggi**):

```python
import olympe
from olympe.messages.ardrone3.Piloting import TakeOff, Landing, moveBy
drone = olympe.Drone("192.168.42.1")     # ⚠️ IP diretto via Wi-Fi; via Skycontroller cambia
drone.connect()
assert drone(TakeOff()).wait().success()
drone(moveBy(0.5, 0, 0, 0)).wait()       # dx, dy, dz in metri e dpsi in radianti
drone(Landing()).wait()
drone.disconnect()
```

- I vecchi Parrot Mambo o Bebop si controllano con `pyparrot` ⚠️ (progetto non più mantenuto).

## 5. PX4 / ArduPilot (MAVLink)

### MAVSDK-Python: attenzione al rename

Il pacchetto PyPI `mavsdk` **ora è un'altra libreria** (binding nativo con API diversa). Il wrapper gRPC classico è diventato **`mavsdk-grpc`**, che si importa con `import mavsdk_grpc as mavsdk`. In alternativa si può fissare `mavsdk<4`.

```python
# pip install mavsdk-grpc
import asyncio
from mavsdk_grpc import System
from mavsdk_grpc.offboard import VelocityBodyYawspeed

async def run():
    drone = System()
    await drone.connect(system_address="udpin://0.0.0.0:14540")   # SITL PX4 di default
    async for s in drone.core.connection_state():
        if s.is_connected: break
    async for h in drone.telemetry.health():
        if h.is_global_position_ok and h.is_home_position_ok: break   # ⚠️ indoor senza GPS non arriva mai
    await drone.action.set_takeoff_altitude(1.0)
    await drone.action.arm()
    await drone.action.takeoff(); await asyncio.sleep(6)
    # offboard: inviare un setpoint PRIMA di start()
    await drone.offboard.set_velocity_body(VelocityBodyYawspeed(0, 0, 0, 0))
    await drone.offboard.start()
    await drone.offboard.set_velocity_body(VelocityBodyYawspeed(0.3, 0, 0, 0)); await asyncio.sleep(2)
    await drone.offboard.set_velocity_body(VelocityBodyYawspeed(0, 0, 0, 30)); await asyncio.sleep(2)
    await drone.offboard.stop()
    await drone.action.land()
    # emergenze: await drone.action.hold() | land() | kill() (motori OFF in volo) | terminate()

asyncio.run(run())
```

### pymavlink (ArduPilot, ⚠️ snippet da conoscenza, non testato oggi)

```python
from pymavlink import mavutil
m = mavutil.mavlink_connection("udpin:0.0.0.0:14550"); m.wait_heartbeat()
m.set_mode("GUIDED"); m.arducopter_arm(); m.motors_armed_wait()
m.mav.command_long_send(m.target_system, m.target_component,
    mavutil.mavlink.MAV_CMD_NAV_TAKEOFF, 0, 0, 0, 0, 0, 0, 0, 1.0)   # 1 m
# land: m.set_mode("LAND")
# kill: MAV_CMD_COMPONENT_ARM_DISARM con param1=0, param2=21196 (force disarm, anche in volo)
```

- **Indoor:** PX4 e ArduPilot hanno bisogno di una stima di posizione (optical flow più rangefinder, oppure mocap o VIO) per i modi a posizione, `takeoff` e offboard. Senza, solo modi manuali o di altitudine: **non adatto a un LLM**.
- **Simulazione:** PX4 SITL (`make px4_sitl gz_x500`) o ArduPilot SITL (`sim_vehicle.py -v ArduCopter`) ⚠️ (comandi standard, non eseguiti oggi). Sono l'ideale per provare prima la pipeline Grok, tool e drone.

---

## 6. Simulazione e mock prima del volo reale

- **Tello:** non esiste un simulatore ufficiale. Si scrive un `MockTello` con gli stessi metodi (`takeoff`, `move_forward`, `rotate_clockwise`, `land`, `get_frame_read`) che aggiorna una posa (x, y, z, yaw) e applica gli **stessi limiti del validatore**. Si sviluppa tutto il loop con Grok contro il mock e si passa al reale con `--real`.
- **Primo volo reale:** quota bassa (circa 1 m), velocità 20–30 cm/s, operatore umano con kill switch, area delimitata.

## Fonti

- Tello SDK 2.0 User Guide (PDF, verificato): https://dl-cdn.ryzerobotics.com/downloads/Tello/Tello%20SDK%202.0%20User%20Guide.pdf
- Tello SDK 1.3: https://dl-cdn.ryzerobotics.com/downloads/tello/20180910/Tello%20SDK%20Documentation%20EN_1.3.pdf
- `damiafuentes/DJITelloPy` (README, `djitellopy/tello.py`, `examples/simple-swarm.py`, `examples/take-picture.py`): https://github.com/damiafuentes/DJITelloPy ; docs: https://djitellopy.readthedocs.io/en/latest/
- `dji-sdk/Tello-Python`: https://github.com/dji-sdk/Tello-Python
- `bitcraze/crazyflie-lib-python` (esempi `step-by-step/sbs_motion_commander.py`, `cflib/crazyflie/supervisor.py`, `commander.py`): https://github.com/bitcraze/crazyflie-lib-python ; docs: https://www.bitcraze.io/documentation/repository/crazyflie-lib-python/master/
- DJI MSDK V5 (README, prodotti supportati, v5.18.0): https://github.com/dji-sdk/Mobile-SDK-Android-V5 ; https://developer.dji.com/doc/mobile-sdk-tutorial/en/
- Mini 4 Pro e RC-N2: https://www.dronezine.it/455349/dji-rilascia-msdk-per-mini-4-pro-solo-con-rc-n2-e-matrice-4d-e-4td/ , https://dronedj.com/2025/03/21/dji-mini-4-pro-msdk/
- Parrot Olympe: https://github.com/Parrot-Developers/olympe
- MAVSDK-Python / mavsdk-grpc (README, `examples/takeoff_and_land.py`, `examples/offboard_velocity_body.py`, `mavsdk/action.py`): https://github.com/mavlink/MAVSDK-Python ; migrazione: https://mavsdk.mavlink.io/main/en/python/migration.html
