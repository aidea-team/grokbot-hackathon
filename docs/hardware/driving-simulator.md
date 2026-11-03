# Simulatore di guida + Grok

> Verificato il: **2026-11-03**. ✅ = verificato su doc, README o spec · ⚠️ = non verificato o da provare sul posto.
> **Il software del simulatore del museo NON è noto.** Il sito dell'hackathon lo illustra come *"driving simulator with seat and steering wheel"*, cioè sedile e volante. Un articolo parla di "macchina da F1" ⚠️. Vedi `museum-inventory-sims.md`.

## 1. Strategia

- **Leggere la telemetria è facile in tutti i giochi.** Mandare input al gioco invece **non è previsto** quasi da nessuno: fa eccezione BeamNG.tech. Per gli altri serve un **controller virtuale** (`vgamepad`, §8), cioè un gamepad finto che il gioco vede come un joystick.
- Ruoli sensati per Grok:
  1. **Race engineer / coach vocale**: "come sto andando?", "dove perdo tempo?". Grok legge giro, settore, delta, gomme e carburante, e risponde in Grok Voice.
  2. **Telecronista** del giro, con eventi tipo sorpasso, giro veloce, uscita di pista.
  3. **Istruttore di guida sicura**, che riprende il "progetto guida sicura" del museo: velocità vs limite, frenate brusche.
  4. **Copilota "rally"** che detta le note.
  5. Su **BeamNG.tech**: Grok **guida** davvero, a livello alto, tramite l'AI del veicolo ("vai lì", "segui quella macchina", "50 km/h").
- Regola d'oro: **Grok non chiude il loop di sterzo**. Ha 0,5-2 s di latenza. Imposta obiettivi; il controllo fine resta al giocatore o all'AI del gioco.
- Lo stato va passato a Grok in forma compatta e solo al cambio di evento, come fine giro o settore, oppure su richiesta tramite il tool `get_car_state()`.
- **Conflitti di porte**: se il motion rig o un dashboard (SimHub ecc.) usa già l'UDP del gioco, bisogna **condividere** la porta: forwarding di SimHub, oppure un secondo target UDP se il gioco lo consente ⚠️. **Non scollegare il loro software.**

## 2. Assetto Corsa Competizione (ACC) e Assetto Corsa (AC): shared memory (Windows)
- ACC espone tre memory-mapped file (`Local\acpmf_physics`, `Local\acpmf_graphics`, `Local\acpmf_static`) ⚠️ (nomi dalla doc Kunos, non riletta oggi). AC "classico" usa gli stessi nomi con struct diverse ⚠️.
- Python: `pip install pyaccsharedmemory` (ACC). ✅ Campi verificati nel README:
  - `Physics.speed_kmh`, `Physics.gear`, `Physics.rpm`
  - `Graphics.completed_lap`, `Graphics.normalized_car_position` (posizione sullo spline del tracciato, 0..1)
  - `Graphics.number_of_laps` (valorizzato solo a fine sessione)
```python
from pyaccsharedmemory import accSharedMemory
import time
asm = accSharedMemory()
try:
    while True:
        sm = asm.read_shared_memory()
        if sm is not None:
            print(f"{sm.Physics.speed_kmh:6.1f} km/h  gear={sm.Physics.gear}  rpm={sm.Physics.rpm}  "
                  f"lap={sm.Graphics.completed_lap}  pos={sm.Graphics.normalized_car_position:.3f}")
        time.sleep(0.2)
finally:
    asm.close()
```
- ⚠️ La codifica della marcia (per esempio 0 = R, 1 = N) e gli altri campi vanno verificati nella doc del pacchetto.
- ACC ha anche una **Broadcasting API** UDP (configurata in `broadcasting.json`), pensata per overlay e regia ⚠️.
- AC "classico" ha **app Python in-game** (cartella `apps/python`), ma con un Python vecchio ⚠️.

## 3. iRacing: `pyirsdk` (Windows) ✅
- `pip install pyirsdk` (Python 3.7+). Fornisce sessione (WeekendInfo, SessionInfo), telemetria live e **broadcast** di comandi: camera, replay, chat, pit, telemetry. ✅
- I comandi pit sono comandi "da box" (carburante, gomme): non c'è controllo di sterzo o gas. ⚠️ API esatta dei metodi da vedere nei `tutorials` del repo.
```python
import irsdk, time
ir = irsdk.IRSDK()
ir.startup()
while ir.is_initialized and ir.is_connected:          # ⚠️ attribute names from the tutorials
    print(ir["Speed"] * 3.6, ir["Lap"], ir["LapDistPct"], ir["Gear"], ir["RPM"])   # Speed in m/s ⚠️
    time.sleep(0.5)
```

## 4. F1 23 / 24 / 25 (EA/Codemasters): UDP telemetry ✅
- Nel gioco: Settings → Telemetry: **UDP Telemetry On**, IP del nostro PC, **porta 20777**, send rate (per esempio 20-60 Hz), **UDP Format**. Per F1 25 una guida F1Laps consiglia il formato **2024** ("backwards compatible") ⚠️. Si legge `packet_format` nell'header per sapere cosa arriva.
- **Header di 29 byte** (little endian): `packet_format u16, game_year u8, game_major u8, game_minor u8, packet_version u8, packet_id u8, session_uid u64, session_time f32, frame_identifier u32, overall_frame_identifier u32, player_car_index u8, secondary_player_car_index u8`. ✅ Massimo **22 auto**. ✅
- **Packet ID** (F1 25): 0 Motion, 1 Session, **2 Lap Data**, 3 Event, 4 Participants, 5 Car Setups, **6 Car Telemetry**, 7 Car Status, 8 Final Classification, 9 Lobby, 10 Car Damage, 11 Session History, 12 Tyre Sets, 13 Motion Ex, 14 Time Trial, 15 Lap Positions. ✅ (crate `f1-game-library-models-25`)
- `CarTelemetryData`: 60 byte per auto. `LapData`: 57 byte per auto. ✅ (struct dal crate; dimensioni calcolate e coerenti con la spec F1 24: 29 + 22×57 + 2 = 1285 byte)
```python
import socket, struct
HDR = struct.Struct("<HBBBBBQfIIBB")                        # 29 bytes
TEL = struct.Struct("<HfffBbHBBH4H4B4BH4f4B")               # 60 bytes per car
LAP = struct.Struct("<IIHBHBHBHBfffBBBBBBBBBBBBBBBHHBfB")   # 57 bytes per car

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(("0.0.0.0", 20777))
while True:
    data, _ = s.recvfrom(2048)
    fmt, year, _, _, _, pid, _, t, _, _, me, _ = HDR.unpack_from(data, 0)
    if pid == 6:                                              # Car Telemetry
        speed, thr, steer, brk, clutch, gear, rpm, drs, *_ = TEL.unpack_from(data, HDR.size + me * TEL.size)
        print(f"[{fmt}] {speed} km/h thr={thr:.2f} brk={brk:.2f} gear={gear} rpm={rpm} drs={drs}")
    elif pid == 2:                                            # Lap Data
        f = LAP.unpack_from(data, HDR.size + me * LAP.size)
        last_ms, cur_ms, lap_dist, pos, lap_num = f[0], f[1], f[10], f[13], f[14]
        print(f"lap {lap_num} P{pos} cur={cur_ms/1000:.1f}s last={last_ms/1000:.3f}s dist={lap_dist:.0f}m")
```
- ⚠️ La spec ufficiale EA (forum EA, "F1 25 UDP Specification") era 403 alla verifica: le struct vengono dal crate Rust che la implementa. Se `fmt` vale 2024, i layout restano compatibili? ⚠️ Da verificare.

## 5. BeamNG.drive / BeamNG.tech: `beamngpy` (l'unico con controllo vero) ✅
- `pip install beamngpy`. **BeamNGpy 1.36 ↔ BeamNG.tech 0.39**. La tabella di compatibilità ufficiale elenca **solo BeamNG.tech**, non BeamNG.drive. ✅ ⚠️ Con BeamNG.drive (Steam) potrebbe non funzionare o funzionare parzialmente: chiedere quale versione hanno. BeamNG.tech va richiesto a BeamNG (licenza ricerca o education).
- API ✅ (reference ufficiale):
  - `BeamNGpy(host, port, home=..., user=...)`, poi `.open(launch=True)`
  - `Scenario(...)`, `Vehicle(...)`
  - `vehicle.control(steering=-1..1, throttle=0..1, brake=0..1, parkingbrake, clutch, gear=-1/0/1..)`
  - `vehicle.set_shift_mode("arcade"|"realistic_automatic"|...)`
  - `vehicle.ai.set_mode("disabled"|"random"|"traffic"|"span"|"manual"|"chase"|"flee"|"stopping")`
  - `vehicle.ai.set_speed(m_s, mode="limit"|"set")`
  - `vehicle.sensors.attach(name, sensor)`, poi `vehicle.sensors.poll()` e lettura con `vehicle.sensors[name][key]`
  - `vehicle.state["pos"|"dir"|"vel"]`, aggiornato dal poll
```python
from beamngpy import BeamNGpy, Scenario, Vehicle
from beamngpy.sensors import Electrics

bng = BeamNGpy("localhost", 25252, home=r"C:\BeamNG.tech")     # path of the installation
bng.open(launch=True)
scenario = Scenario("west_coast_usa", "grok_drive")
car = Vehicle("ego", model="etk800", license="GROK")
scenario.add_vehicle(car, pos=(-717, 101, 118), rot_quat=(0, 0, 0.3826834, 0.9238795))
scenario.make(bng); bng.scenario.load(scenario); bng.scenario.start()
car.sensors.attach("electrics", Electrics())

# --- tools for Grok (high level) ---
def get_car_state():
    car.sensors.poll()
    e = car.sensors["electrics"]
    return {"pos": car.state["pos"], "vel": car.state["vel"],
            "wheelspeed_ms": e.get("wheelspeed"), "gear": e.get("gear"), "rpm": e.get("rpm")}   # ⚠️ electrics keys
def drive_like_traffic(max_kmh: float):
    car.ai.set_mode("traffic"); car.ai.set_speed(max_kmh / 3.6, mode="limit")
def stop():
    car.ai.set_mode("stopping")
def manual(steering: float, throttle: float, brake: float):     # local loop/tests only, not straight from the LLM
    car.ai.set_mode("disabled"); car.control(steering=steering, throttle=throttle, brake=brake)
```
- I sensori disponibili includono camera, lidar, IMU e ultrasuoni. ✅ La **camera** permette di passare frame a Grok Vision ("cosa vedi davanti?") ⚠️ (vedi `../grok-api/vision.md`).

## 6. rFactor 2 / Le Mans Ultimate
- Telemetria via **shared memory** con il plugin `rF2SharedMemoryMapPlugin` (TheIronWolf) e lettori Python della community ⚠️ (non verificato oggi). LMU è basato sullo stesso motore ⚠️. Da approfondire solo se sul posto c'è uno di questi.

## 7. Forza Motorsport / Forza Horizon: "Data Out" UDP
- Nel gioco: Settings → HUD/Gameplay → **Data Out** On, IP e porta a scelta ⚠️ (percorso del menu non verificato).
- **Forza Horizon 6**: pacchetto fisso da **324 byte**. Comincia con `S32 IsRaceOn` (1 in gara, 0 nei menu) e `U32 TimestampMS`. `Speed` è un float **in m/s**. FH6 aggiunge `CarGroup`, `SmashableVelDiff` e `SmashableMass` e **non** ha `TireWear` né `TrackOrdinal` del formato "Dash" di Forza Motorsport. ✅ (doc Forza, letta solo dagli snippet: pagina 403)
- Offset usati dalla community per FH4/FH5 a 324 byte: `Speed` @256, `LapNumber` u16 @312, `RacePosition` u8 @314, `Accel` u8 @315, `Brake` u8 @316, `Gear` u8 @319 ⚠️. **Con FH6 gli offset cambiano**: ricontarli dalla doc FH6 e controllare sempre `len(data)`.
```python
import socket, struct
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.bind(("0.0.0.0", 5300))   # port set in the game
while True:
    d, _ = s.recvfrom(1024)
    is_race_on, ts = struct.unpack_from("<iI", d, 0)
    if len(d) == 324 and is_race_on:
        speed = struct.unpack_from("<f", d, 256)[0]            # ⚠️ FH4/FH5 offset
        print(f"{speed*3.6:.0f} km/h lap={struct.unpack_from('<H', d, 312)[0]} pos={d[314]}")
```

## 8. Euro Truck Simulator 2 / American Truck Simulator
- **SCS Telemetry SDK**: il plugin `scs-sdk-plugin` (fork RenCloud) va messo in `bin/win_x64/plugins/` ed espone la **shared memory `Local\SCSTelemetry`**. Il layout è in `scs-telemetry/inc/scs-telemetry-common.hpp` e **cambia tra revisioni**. ✅ Lato input fornisce **solo lettura**: non c'è un canale per guidare il camion.
- Più comodo: **Funbit ets2-telemetry-server**, che serve un JSON REST su `http://localhost:25555/api/ets2/telemetry`. Campi tipo `game.connected`, `truck.speed`, `navigation.speedLimit`, `navigation.estimatedDistance`. Supporta ETS2 1.15+ e ATS. ✅ Ultima versione 3.2.5, manutenzione scarsa ⚠️.
```python
import requests, time
while True:
    t = requests.get("http://localhost:25555/api/ets2/telemetry", params={"_": time.time()}, timeout=1).json()
    if t["game"]["connected"]:
        print(f'{t["truck"]["speed"]:.0f} km/h  limit={t["navigation"]["speedLimit"]}  '
              f'ETA dist={t["navigation"]["estimatedDistance"]}')
    time.sleep(0.5)
```
- ETS2 è perfetto per l'idea **"istruttore guida sicura"**: c'è il limite di velocità in telemetria.

## 9. Mandare input a giochi che non lo prevedono: controller virtuale
- `pip install vgamepad` emula un pad **Xbox 360 / DS4**. Su Windows installa da solo il driver **ViGEmBus 1.17.333**; su Linux usa `uinput`. ✅ ⚠️ Il progetto ViGEmBus a monte è stato ritirato dall'autore: funziona, ma non viene più aggiornato (non riverificato oggi).
```python
import vgamepad as vg, time
pad = vg.VX360Gamepad()
pad.left_joystick_float(x_value_float=-0.3, y_value_float=0.0)   # steer left 30%
pad.right_trigger_float(value_float=0.5)                          # throttle 50%
pad.update(); time.sleep(1)
pad.reset(); pad.update()                                         # ⚠️ reset() as in README examples
```
- Il gioco va configurato per accettare il pad virtuale **in aggiunta al volante**. Rischio: due periferiche che si contendono gli assi. **Da usare solo per demo brevi, a gioco in pausa o in sessione di test, mai con una persona sul motion rig.**

## 10. Prodotti esistenti
| Prodotto | Cosa fa | Note |
|---|---|---|
| **Simulator-Controller** (SeriousOldMan) | pit crew AI con GPT: race engineer, strategist, spotter, driving coach; AC, ACC, rF2, iRacing, AMS2 | open source, Windows/AutoHotkey ✅ |
| **AI-based Virtual Race Engineer** (boxthislap.org) | chatbot vocale da race engineer, pit stop automatici (iRacing Black Box) | community ✅ |
| **gt7-engineer** | GT7: domanda vocale, telemetria, GPT-4o, TTS; circa 0,01-0,02 $ a gara | hobby, buon riferimento architetturale ✅ |
| Crew Chief | spotter e ingegnere vocale classico, senza LLM | ⚠️ non riverificato |

**Come distinguerci**: Grok Voice realtime (barge-in, italiano) con tool calling su telemetria **e** azioni reali: su BeamNG guida, su F1/iRacing gestisce i box. Oppure il "cross-device": il volante del museo che pilota il cane o il drone (vedi `cockpit-as-controller.md`).

## Fonti
- PyAccSharedMemory: https://github.com/rrennoir/PyAccSharedMemory
- pyirsdk: https://github.com/kutu/pyirsdk
- F1 25: https://forums.ea.com/blog/f1-games-game-info-hub-en/f1%c2%ae-25-udp-specification/12187347 (⚠️ 403) · https://docs.rs/f1-game-library-models-25/latest/f1_game_library_models_25/ · https://docs.rs/f1-game-library-models-25/0.5.0/src/f1_game_library_models_25/packets/car_telemetry.rs.html · https://docs.rs/f1-game-library-models-25/0.5.0/src/f1_game_library_models_25/packets/lap_data.rs.html · https://www.f1laps.com/faqs/f1-25-udp-telemetry-settings/
- BeamNGpy: https://github.com/BeamNG/BeamNGpy · https://documentation.beamng.com/api/beamngpy/master/beamngpy.html · https://documentation.beamng.com/api/beamngpy/master/compatibility.html
- Forza Data Out: https://support.forza.net/hc/en-us/articles/51744149102611-Forza-Horizon-6-Data-Out-Documentation (⚠️ 403, letto dagli snippet) · https://support.forza.net/hc/en-us/articles/21742934024211-Forza-Motorsport-Data-Out-Documentation
- ETS2: https://github.com/RenCloud/scs-sdk-plugin · https://github.com/Funbit/ets2-telemetry-server
- vgamepad: https://github.com/yannbouteiller/vgamepad
- Simulator-Controller: https://www.sourcepulse.org/projects/1844515 · Virtual race engineer: https://boxthislap.org/ai-based-virtual-race-engineer-for-sim-racing · gt7-engineer: https://www.gtplanet.net/forum/threads/opensource-ai-race-engineer-for-gran-turismo-7.431931/
