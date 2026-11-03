# Simulatore di volo + Grok

> Verificato il: **2026-11-03**. ✅ = verificato su doc ufficiale o README · ⚠️ = non verificato o da provare sul posto.
> **Il software del simulatore del museo NON è noto.** Il sito dell'hackathon lo illustra come *"three-screen flight simulator on a motion platform"*, cioè tre schermi su piattaforma mobile (vedi `museum-inventory-sims.md`). Questo documento copre MSFS, X-Plane e FlightGear.

## 1. Primi 10 minuti sul posto

1. Riconoscere il simulatore: logo, finestra, `Task Manager`. Annotare **versione esatta**, che per X-Plane decide quale API usare.
2. Riconoscere il motion rig: c'è un software di motion aperto? **Non toccarlo**, ma annotare quali porte usa.
3. Decidere **dove gira il nostro codice**:
   - **sul PC del simulatore**, che è la scelta più semplice: Python 64-bit su Windows, `pip install`;
   - **dal nostro laptop in LAN**: X-Plane UDP funziona via rete, SimConnect remoto richiede configurazione, la Web API di X-Plane oggi ascolta **solo su localhost** ⚠️.
4. Smoke test: leggere la quota e stamparla. Poi un solo comando innocuo, per esempio cambiare l'heading bug.

## 2. Architettura consigliata (Grok come copilota)

```
microfono ──► Grok Voice (realtime) ──tool call──► bridge Python ──► SimConnect / X-Plane API
                    ▲                                   │
                    └──── stato volo (JSON, 1-2 Hz) ◄───┘
```

- **Grok decide obiettivi di alto livello**: heading, quota, velocità, AP on/off, carrello, flap. **Non pilota le superfici a 30 Hz.** A tenere l'aereo pensa l'autopilota del simulatore.
- Il bridge ha una **whitelist** di azioni, valida i range (heading 0-359, quota per esempio 0-40000 ft, velocità ragionevoli) e logga tutto.
- Lo stato va passato a Grok in forma compatta: `{"alt_ft":3500,"ias_kt":110,"hdg":270,"vs_fpm":0,"ap":true,"gear_down":false,"on_ground":false}`.
- Tool suggeriti (lo schema JSON è da adattare al formato function-calling di Grok, vedi `docs/grok-api/`):
  - `get_flight_state()`
  - `set_autopilot(enabled: bool)`
  - `set_heading(deg: int)`
  - `set_altitude(ft: int)`
  - `set_speed(kt: int)`
  - `set_vertical_speed(fpm: int)`
  - `toggle_approach()`
  - `set_gear(down: bool)`
  - `set_flaps(direction: "up"|"down")`
- Idee demo: **copilota vocale** ("portaci a 5000 piedi, prua 090"), **istruttore** che commenta la telemetria, **ATC** in stile SayIntentions, **checklist parlata**, **guida turistica** ("cosa stiamo sorvolando?" usando lat/lon).
- **Sicurezza col motion rig**: nessun comando brusco con una persona a bordo, soprattutto inversioni o picchiate. Va previsto un tasto/parola di "stop" che disinserisce le nostre azioni, e l'arresto d'emergenza del rig resta allo staff.

## 3. Microsoft Flight Simulator 2020 / 2024: SimConnect

### Requisiti
- SimConnect gira **solo su Windows**. ✅ (README Python-SimConnect)
- Wrapper Python: **`SimConnect`** su PyPI (repo `odwdinc/Python-SimConnect`), ultima release **0.4.26 del 15/06/2022**, Python >= 3.6, **serve Python a 64 bit** (con 32 bit si ottiene `OSError: [WinError 193]`). ✅ La DLL SimConnect è inclusa nel pacchetto ⚠️ (da verificare: in alternativa si prende dall'SDK MSFS).
- **MSFS 2024**: il wrapper è dichiarato per MSFS 2020. Per MSFS 2024 non c'è una conferma ufficiale, e in un thread un utente segnala script che "non fanno nulla". ⚠️ Provare subito. In alternativa: SimConnect SDK di MSFS 2024 da C#/C++, oppure altri wrapper Python (es. `pysimconnect` ⚠️ non valutato).
- **SimConnect remoto** (laptop in LAN): si edita `SimConnect.xml` sul PC del simulatore. Percorso Steam: `%APPDATA%\Microsoft Flight Simulator\`; versione Store: `%LOCALAPPDATA%\Packages\Microsoft.FlightSimulator_8wekyb3d8bbwe\LocalCache\`. Si aggiunge un blocco IPv4 con `Scope` `global` e lo stesso `Address`/`Port` va riportato nel `SimConnect.cfg` del client. ✅ (percorsi e campi dalla doc MSFS; ⚠️ l'esempio "global" esatto non è nella doc). In hackathon conviene **girare direttamente sul PC del simulatore**.

### Simvar utili (nomi del wrapper, unità come da `RequestList.py`) ✅
| Chiave | Unità | Note |
|---|---|---|
| `PLANE_ALTITUDE` | feet | quota MSL |
| `AIRSPEED_INDICATED` | knots | IAS |
| `GROUND_VELOCITY` | knots | |
| `VERTICAL_SPEED` | feet/minute | |
| `PLANE_PITCH_DEGREES`, `PLANE_BANK_DEGREES` | **radianti** (nonostante il nome) | segno del pitch: ⚠️ in SimConnect il muso su dà valori negativi, da verificare |
| `PLANE_HEADING_DEGREES_MAGNETIC` / `_TRUE` | **radianti** | |
| `PLANE_LATITUDE`, `PLANE_LONGITUDE` | gradi | |
| `GEAR_HANDLE_POSITION` | bool | |
| `FLAPS_HANDLE_INDEX` | number | |
| `SIM_ON_GROUND` | bool | |
| `AUTOPILOT_MASTER` | bool | |
| `AUTOPILOT_HEADING_LOCK_DIR` | gradi | heading selezionato |
| `AUTOPILOT_ALTITUDE_LOCK_VAR` | feet | quota selezionata |

### Eventi (Event ID dell'SDK MSFS) ✅
- **Autopilota**:
  - `AP_MASTER` (toggle), `AUTOPILOT_ON`, `AUTOPILOT_OFF`
  - `AP_HDG_HOLD` (toggle), `AP_HDG_HOLD_ON`, `HEADING_BUG_SET` (gradi, interi 0-360)
  - `AP_ALT_HOLD` (toggle), `AP_ALT_VAR_SET_ENGLISH` (feet)
  - `AP_AIRSPEED_HOLD` / `AP_PANEL_SPEED_HOLD` (toggle), `AP_SPD_VAR_SET` (knots)
  - `AP_VS_HOLD`, `AP_VS_VAR_SET_ENGLISH` (ft/min)
  - `AP_APR_HOLD` (approach: localizer e glideslope), `AP_NAV1_HOLD`
- **Carrello**: `GEAR_UP`, `GEAR_DOWN`, `GEAR_TOGGLE`. **Freno di stazionamento**: `PARKING_BRAKES`.
- **Flap**: `FLAPS_UP`, `FLAPS_DOWN`, `FLAPS_INCR`, `FLAPS_DECR`.
- **Superfici** (sconsigliato farle muovere all'LLM): `AXIS_ELEVATOR_SET` e `AXIS_AILERONS_SET` (da -16383 a 16384), `AXIS_RUDDER_SET`.
- La doc avverte che gli eventi AP **non valgono per gli elicotteri**. ✅
- ⚠️ Molti aerei di terze parti (Fenix, PMDG, FBW A32NX, iniBuilds) **ignorano** gli eventi standard e vogliono LVar o H-events. Per quelli servono **MobiFlight WASM module** (il wrapper non conosce gli eventi MobiFlight: bisogna creare un `Event` con l'ID, come dice il README ✅) oppure **FSUIPC7** (commerciale ⚠️). Per l'hackathon scegliamo un aereo default con autopilota standard (C172 G1000, TBM 930 ⚠️).

### Snippet Python (MSFS)
```python
# Windows + Python 64-bit + MSFS in volo.   pip install SimConnect
import math
from SimConnect import SimConnect, AircraftRequests, AircraftEvents

sm = SimConnect()
aq = AircraftRequests(sm, _time=200)   # cache dei valori: 200 ms
ae = AircraftEvents(sm)

def flight_state():
    rad = lambda k: math.degrees(aq.get(k) or 0.0)
    return {
        "alt_ft": round(aq.get("PLANE_ALTITUDE") or 0),
        "ias_kt": round(aq.get("AIRSPEED_INDICATED") or 0),
        "vs_fpm": round(aq.get("VERTICAL_SPEED") or 0),
        "hdg_mag": round(rad("PLANE_HEADING_DEGREES_MAGNETIC")) % 360,
        "pitch_deg": round(-rad("PLANE_PITCH_DEGREES"), 1),   # ⚠️ verificare il segno
        "bank_deg": round(rad("PLANE_BANK_DEGREES"), 1),
        "lat": aq.get("PLANE_LATITUDE"), "lon": aq.get("PLANE_LONGITUDE"),
        "on_ground": bool(aq.get("SIM_ON_GROUND")),
        "gear_down": bool(aq.get("GEAR_HANDLE_POSITION")),
        "ap_master": bool(aq.get("AUTOPILOT_MASTER")),
        "ap_hdg": aq.get("AUTOPILOT_HEADING_LOCK_DIR"),
        "ap_alt": aq.get("AUTOPILOT_ALTITUDE_LOCK_VAR"),
    }

def ev(name, *args):
    e = ae.find(name)
    if e is None:
        raise ValueError(f"evento sconosciuto: {name}")
    e(*args)

# --- tool chiamabili da Grok ---
def set_autopilot(enabled: bool):
    if bool(aq.get("AUTOPILOT_MASTER")) != enabled:
        ev("AP_MASTER")                      # toggle, perciò controlliamo prima lo stato

def set_heading(deg: int):
    ev("HEADING_BUG_SET", int(deg) % 360)
    ev("AP_HDG_HOLD_ON")

def set_altitude(ft: int):
    ft = max(0, min(int(ft), 40000))
    ev("AP_ALT_VAR_SET_ENGLISH", ft)
    ev("AP_ALT_HOLD")                         # ⚠️ toggle: su alcuni aerei va usato il VS/FLC

def set_speed(kt: int):
    ev("AP_SPD_VAR_SET", int(kt))
    ev("AP_AIRSPEED_HOLD")                    # ⚠️ toggle; molti GA non hanno autothrottle

def set_gear(down: bool):
    ev("GEAR_DOWN" if down else "GEAR_UP")

def set_flaps(direction: str):
    ev("FLAPS_INCR" if direction == "down" else "FLAPS_DECR")

if __name__ == "__main__":
    print(flight_state())
    set_heading(270)
    sm.exit()
```

## 4. X-Plane 12 (11): Web API, UDP, XPPython3

### 4a. Web API REST/WebSocket (X-Plane **12.1.1+**) ✅
- Il server web è integrato e ascolta su `http://localhost:8086` (porta modificabile con `--web_server_port=`).
- **Versioni dell'API**:
  - **v1** (12.1.1+): dataref
  - **v2** (12.1.4+): anche i comandi
  - **v3** (12.4.0+): anche l'inizializzazione del volo
- Con "Disable Incoming Traffic" (Settings, Network) ogni chiamata risponde 403.
- **Oggi ascolta solo connessioni locali**: l'accesso LAN con autorizzazione è in roadmap. ⚠️ Lo script quindi va eseguito sul PC del simulatore, oppure dietro un piccolo proxy.
- Gli **ID dei dataref e dei comandi cambiano a ogni sessione**: si risolvono per nome con `GET /api/v2/datarefs?filter[name]=...`.
- Endpoint:
  - `GET /datarefs/{id}/value`, `PATCH /datarefs/{id}/value` con body `{"data": ...}`
  - `POST /command/{id}/activate` con body `{"duration": 0.5}` (massimo 10 s)
  - I dataref di tipo `data` sono stringhe base64. Scrivere un dataref read-only restituisce 403 `dataref_is_readonly`.
- WebSocket `ws://localhost:8086/api/v2` con messaggi `dataref_subscribe_values`, `dataref_set_values` e `command_set_is_active`. Gli aggiornamenti arrivano come `dataref_update_values` a circa 10 Hz.

```python
# X-Plane 12.1.4+ in esecuzione sullo stesso PC.  pip install requests
import requests
BASE = "http://localhost:8086/api/v2"     # v3 se X-Plane >= 12.4.0, v1 se 12.1.1-12.1.3 (senza comandi)
_ids = {}

def _id(kind, name):                      # kind: "datarefs" | "commands"
    key = (kind, name)
    if key not in _ids:
        r = requests.get(f"{BASE}/{kind}", params={"filter[name]": name}, timeout=2)
        r.raise_for_status()
        _ids[key] = r.json()["data"][0]["id"]
    return _ids[key]

def get(name):
    return requests.get(f"{BASE}/datarefs/{_id('datarefs', name)}/value", timeout=2).json()["data"]

def set_(name, value):
    requests.patch(f"{BASE}/datarefs/{_id('datarefs', name)}/value", json={"data": value}, timeout=2).raise_for_status()

def cmd(name, duration=0.0):
    requests.post(f"{BASE}/command/{_id('commands', name)}/activate", json={"duration": duration}, timeout=2).raise_for_status()

# Nomi da DataRefs.txt / Commands.txt di X-Plane (⚠️ verificare sulla versione installata)
state = {
    "alt_m":   get("sim/flightmodel/position/elevation"),           # metri MSL
    "ias_kt":  get("sim/flightmodel/position/indicated_airspeed"),
    "pitch":   get("sim/flightmodel/position/theta"),
    "roll":    get("sim/flightmodel/position/phi"),
    "hdg_true": get("sim/flightmodel/position/psi"),
}
print(state)
set_("sim/cockpit2/autopilot/heading_dial_deg_mag_pilot", 270)     # ⚠️
set_("sim/cockpit2/autopilot/altitude_dial_ft", 5000)              # ⚠️
cmd("sim/autopilot/servos_toggle")        # AP on/off ⚠️
cmd("sim/autopilot/heading")              # HDG mode ⚠️
cmd("sim/flight_controls/landing_gear_toggle")   # ⚠️ (o landing_gear_down / _up)
```

### 4b. UDP legacy (X-Plane 11 e 12, anche da LAN)
- Porta di ascolto di X-Plane: **49000**. Beacon multicast: 49707. ✅ (XPPython3 docs, FlyAway)
- **X-Plane 12 parte con l'UDP disabilitato**: va abilitato "Accept incoming connections" in Settings, Network. ✅
- Pacchetti:
  - `RREF`: `struct.pack('<4sxii400s', b'RREF', freq_hz, index, dataref)`. La risposta è `b'RREF'` + pacchetto, seguito da coppie `(int index, float value)`.
  - `DREF`: `'<4sxf500s'` con valore e nome. Solo dataref scrivibili.
  - `CMND`: `b'CMND\x00' + nome_comando`.
- ⚠️ La documentazione bundled di X-Plane è considerata imprecisa (lo dice XPPython3): verificare con Wireshark se qualcosa non torna.

```python
import socket, struct
XP = ("127.0.0.1", 49000)                 # IP del PC con X-Plane
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.bind(("0.0.0.0", 0)); s.settimeout(2)
REFS = ["sim/flightmodel/position/elevation", "sim/flightmodel/position/indicated_airspeed",
        "sim/flightmodel/position/psi"]
for i, r in enumerate(REFS):              # 2 Hz; freq=0 per disiscriversi
    s.sendto(struct.pack("<4sxii400s", b"RREF", 2, i, r.encode()), XP)

def read_once():
    data, _ = s.recvfrom(2048)
    out = {}
    if data[:4] == b"RREF":
        for off in range(5, len(data), 8):
            idx, val = struct.unpack("<if", data[off:off + 8])
            out[REFS[idx]] = val
    return out

def dref(name, value):
    s.sendto(struct.pack("<4sxf500s", b"DREF", float(value), name.encode()), XP)

def cmnd(name):
    s.sendto(b"CMND\x00" + name.encode(), XP)

print(read_once())
dref("sim/cockpit2/autopilot/altitude_dial_ft", 6000)   # ⚠️
cmnd("sim/autopilot/servos_toggle")                     # ⚠️
```

### 4c. XPPython3 (plugin dentro X-Plane)
- Plugin che esegue Python **dentro** X-Plane: accesso completo a dataref e comandi e callback per frame. Utile per un server HTTP o WebSocket custom esposto in LAN, che aggira il limite localhost della Web API. ⚠️ Richiede installazione nel sim (cartella `Resources/plugins`) e il permesso dello staff. Doc: https://xppython3.readthedocs.io

## 5. FlightGear (fallback open source, gira anche sul nostro laptop)
- Avvio: `fgfs --telnet=5401` (interfaccia telnet al property tree) e/o `--httpd=8080`. ✅ (manuale fgfs)
- Comandi telnet: `get <path>`, `set <path> <value>`, `ls`, `cd`, `data` (modalità raw) ⚠️ (wiki Telnet_usage non raggiungibile, 403).
- Libreria pronta: `pip install flightgear-python` (`TelnetConnection`, `HTTPConnection`). ✅ (readthedocs)
- Property utili ⚠️:
  - stato: `/position/altitude-ft`, `/velocities/airspeed-kt`, `/orientation/heading-deg`, `/orientation/pitch-deg`, `/orientation/roll-deg`
  - comandi: `/controls/gear/gear-down`, `/controls/flight/flaps` (0..1)
  - autopilota generico: `/autopilot/settings/heading-bug-deg`, `/autopilot/settings/target-altitude-ft`, `/autopilot/locks/heading` = `dg-heading-hold`, `/autopilot/locks/altitude` = `altitude-hold`. Dipende dall'aereo: il C172P usa il KAP140.

```python
import socket
s = socket.create_connection(("127.0.0.1", 5401), timeout=2)
f = s.makefile("rw", newline="\r\n")
f.write("data\r\n"); f.flush()             # risposte senza prompt
def get(p): f.write(f"get {p}\r\n"); f.flush(); return f.readline().strip()
def set_(p, v): f.write(f"set {p} {v}\r\n"); f.flush()
print(get("/position/altitude-ft"), get("/velocities/airspeed-kt"))
set_("/autopilot/settings/heading-bug-deg", 270)
set_("/controls/gear/gear-down", "true")
```

## 6. Prodotti esistenti (per capire cosa NON reinventare e cosa differenzia)
| Prodotto | Cosa fa | Note |
|---|---|---|
| **SayIntentions.AI** | ATC AI vocale cloud, co-pilota AI (dal 2024) che gestisce le comunicazioni, Checklist V2 che "legge, risponde e manipola l'aereo", traffico AI "Living World" | MSFS 2020/2024 ✅, anche X-Plane (listing Aerosoft) ✅; free tier annunciato a gen 2026 ✅ |
| **BeyondATC** | ATC AI per MSFS: runway e SID/STAR in base al vento, direct-to, cambi di quota, iniezione traffico | MSFS 2024 compatibile ✅ |
| **SimVoice Copilot** | comandi vocali tradotti in azioni via SimConnect; modalità AI locale | commerciale ✅ |
| **CrewMate A350** | copilota virtuale open source per iniBuilds A350 | ✅ (2026) |
| **OpenSquawk** | prototipo di ATC AI via SimConnect | in sviluppo ✅ |
| Tiny Copilot (Fenix), VoiceAttack + plugin MSFS | callout e comandi vocali senza LLM | ✅ |

**Dove possiamo differenziarci in 36 ore**: un copilota **conversazionale realtime** (Grok Voice) con **tool calling** reale sull'autopilota, e magari una **personalità da museo**, per esempio "il pilota del 1988" che confronta MSFS di oggi con la scatola del Flight Simulator '88 esposta. Oppure il passaggio cross-device: la cloche del simulatore che pilota il drone (vedi `cockpit-as-controller.md`).

## Fonti
- Python-SimConnect (README, RequestList): https://github.com/odwdinc/Python-SimConnect · https://github.com/odwdinc/Python-SimConnect/blob/master/SimConnect/RequestList.py
- PyPI SimConnect 0.4.26: https://pypi.org/project/SimConnect/
- MSFS SDK, eventi autopilota: https://docs.flightsimulator.com/html/Programming_Tools/Event_IDs/Aircraft_Autopilot_Flight_Assist_Events.htm
- MSFS SDK, eventi carrello e freni: https://docs.flightsimulator.com/html/Programming_Tools/Event_IDs/Aircraft_Misc_Events.htm
- MSFS SDK, eventi comandi di volo e flap: https://docs.flightsimulator.com/html/Programming_Tools/Event_IDs/Aircraft_Flight_Control_Events.htm
- MSFS SDK, SimConnect.xml: https://docs.flightsimulator.com/html/Programming_Tools/SimConnect/SimConnect_XML_Definition.htm
- Thread "SimConnect script in Python" (MSFS 2024): https://forums.flightsimulator.com/t/simconnect-script-in-python/706526
- X-Plane Web API: https://developer.x-plane.com/article/x-plane-web-api/
- XPPython3, UDP: https://xppython3.readthedocs.io/en/latest/development/udp/index.html
- FlyAway Simulation, dataref via rete: https://flyawaysimulation.com/ask/answers/x-plane-datarefs-network-access/
- FlightGear: https://manpages.org/fgfs/1 · https://flightgear-python.readthedocs.io/en/latest/examples.html · https://wiki.flightgear.org/Telnet_usage (⚠️ 403 al momento della verifica)
- SayIntentions/BeyondATC: https://msfsaddons.com/2024/12/04/sayintentions-ai-and-beyondatc-fully-compatible-with-microsoft-flight-simulator-2024/ · https://msfsaddons.com/2024/09/05/sayintentions-ai-introduces-ai-powered-co-pilot-that-can-manage-communications-in-msfs/ · https://msfsaddons.com/2025/09/17/sayintentions-ai-brings-ai-driven-checklists-to-msfs-with-checklist-v2/ · https://msfsaddons.com/2026/01/04/sayintentions-ai-reveals-unified-universe-ambitions-and-upcoming-free-tier/ · https://msfsaddons.com/2025/07/15/beyondatc-details-upcoming-features-and-progress-in-july-2025-development-update/
- SimVoice Copilot: https://forums.flightsimulator.com/t/release-simvoice-copilot-1-0-12-0-now-with-english-and-spanish-support/770095
- CrewMate A350: https://msfsaddons.com/2026/03/15/crewmate-a350-a-free-open-source-virtual-copilot-for-the-inibuilds-a350-in-msfs/
