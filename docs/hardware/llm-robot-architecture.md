# Architettura LLM → robot: Grok come pianificatore, codice deterministico come guardiano

> **Verificato il:** 2026-11-03. Formato tool verificato sulla doc xAI function calling (Responses API), modello `grok-4.7` come negli esempi della doc e sul sito evento. Per i dettagli su Grok API e Voice vedi `docs/grok-api/` e `docs/voice/`, curati da un altro agente.
> **Legenda:** ⚠️ = non verificato oppure dedotto.

## 1. Principio

> **L'LLM decide *cosa* fare, il codice decide *se* e *come* farlo.**
> Grok non invia mai velocità o comandi raw all'hardware. Chiama **primitive whitelisted** con parametri limitati. Un **validatore deterministico** può rifiutarle. Un **kill switch umano** scavalca tutto senza passare dall'LLM.

```
 voce / testo                                  ┌─────────────── KILL SWITCH ───────────────┐
     │                                         │ tastiera (spazio = stop, k = kill)        │
     ▼                                         │ keyword vocale locale ("stop", "fermo")   │
┌──────────┐  tool_call(JSON)  ┌────────────┐  │ telecomando fisico in mano all'operatore  │
│  Grok    │ ────────────────► │ Validatore │  └──────────────┬────────────────────────────┘
│ (planner)│ ◄──────────────── │ (regole)   │                 │ preempt (stop immediato)
└──────────┘ result / rifiuto  └─────┬──────┘                 ▼
     ▲                                │ ok         ┌──────────────────────────┐
     │ frame camera, stato            ▼            │ Executor (una azione per │
     └──────────────────────── ┌────────────┐ ───► │ volta, timeout, watchdog)│
                               │ Telemetria │      └───────────┬──────────────┘
                               └────────────┘                  ▼
                                                     Driver: Mock | Go2 | Tello | ...
```

### Regole di progetto

1. **Whitelist di primitive** piccole e reversibili (stand, sit, move limitato, turn, hover, land, snapshot, speak). **Niente** flip, jump, handstand, `Damp`, `emergency` lato LLM.
2. **Parametri limitati due volte:** nello schema JSON (`minimum`, `maximum`, `enum`) **e** nel validatore, perché lo schema è solo un suggerimento al modello.
3. **Stato esplicito** (state machine): `GROUNDED`, `STANDING` o `FLYING`, `MOVING`, `STOPPED_BY_HUMAN`. Ogni tool è valido solo in certi stati.
4. **Geofence:** posa stimata in 2D o 3D, aggiornata a ogni comando (dead reckoning). Un movimento che porterebbe fuori dal box viene rifiutato. Per il Tello EDU c'è la localizzazione con mission pad.
5. **Una azione alla volta:** `parallel_tool_calls: false` (parametro supportato dall'API xAI) e una coda seriale nell'executor.
6. **Durata limitata** per ogni azione (≤ 3 s per il cane, ≤ 150 cm per il drone). Grok concatena più chiamate se vuole andare più lontano: ogni passo viene rivalidato.
7. **Watchdog / dead-man:** se l'executor non riceve un heartbeat dall'app (UI aperta, operatore presente) per N secondi, esegue `stop`. Il Tello in più atterra da solo dopo 15 s senza comandi.
8. **Il kill switch non passa dall'LLM:** è un thread locale con priorità massima che chiama direttamente il driver (`StopMove` / `stop`, `StandDown` / `land`, `emergency`).
9. **Il rifiuto è un risultato:** il validatore restituisce `{"ok": false, "reason": "..."}` a Grok, così il modello può ripianificare ("non posso andare avanti di 3 m, il limite è 1 m").
10. **Prima la simulazione:** stessa interfaccia `Driver` per Mock e reale. Flag `--real` e conferma da tastiera prima di armare.
11. **Log di tutto** (tool call, validazione, esito, timestamp) per il debug e per il pitch.

## 2. Tool definitions pronte per Grok

Formato **Responses API xAI**, verificato su docs.x.ai: `{"type":"function","name","description","parameters"}`, root `parameters` con `"type":"object"`, al massimo 350 tool.
- Per **Chat Completions** (stile OpenAI) lo stesso oggetto va annidato: `{"type":"function","function":{"name":..., "description":..., "parameters":...}}`. ⚠️ Formato non riletto oggi nella doc xAI.
- Per **Grok Voice realtime** (`wss://api.x.ai/v1/realtime`) i tool vanno in `session.update` → `session.tools`. ⚠️ Secondo fonti di terze parti (Mastra, Pipecat) il formato è lo stesso flat, le chiamate arrivano come `response.function_call_arguments.done` e i risultati si rimandano con `conversation.item.create` (item `function_call_output`) seguito da `response.create`. Da verificare in `docs/voice/`.

### 2.1 Cane robot (`tools_dog.json`)

```json
[
  {
    "type": "function",
    "name": "dog_stand_up",
    "description": "Make the robot dog stand up and balance. Required before any movement or gesture.",
    "parameters": { "type": "object", "properties": {}, "additionalProperties": false }
  },
  {
    "type": "function",
    "name": "dog_sit",
    "description": "Make the robot dog sit down. It stays powered.",
    "parameters": { "type": "object", "properties": {}, "additionalProperties": false }
  },
  {
    "type": "function",
    "name": "dog_lie_down",
    "description": "Make the robot dog lie down in a controlled way. Use at the end of a session.",
    "parameters": { "type": "object", "properties": {}, "additionalProperties": false }
  },
  {
    "type": "function",
    "name": "dog_stop",
    "description": "Immediately stop any movement; the dog keeps standing. Always safe to call.",
    "parameters": { "type": "object", "properties": {}, "additionalProperties": false }
  },
  {
    "type": "function",
    "name": "dog_walk",
    "description": "Walk for a short, bounded time with the given body velocity, then stop automatically. For longer paths call it several times and check the camera between steps.",
    "parameters": {
      "type": "object",
      "properties": {
        "forward_mps":  { "type": "number", "minimum": -0.3, "maximum": 0.4, "description": "Forward (+) / backward (-) speed in m/s" },
        "lateral_mps":  { "type": "number", "minimum": -0.3, "maximum": 0.3, "description": "Left (+) / right (-) speed in m/s" },
        "duration_s":   { "type": "number", "minimum": 0.2,  "maximum": 3.0, "description": "Duration in seconds" }
      },
      "required": ["forward_mps", "lateral_mps", "duration_s"],
      "additionalProperties": false
    }
  },
  {
    "type": "function",
    "name": "dog_turn",
    "description": "Turn in place by approximately the given angle. Positive = left (counter-clockwise).",
    "parameters": {
      "type": "object",
      "properties": { "angle_deg": { "type": "number", "minimum": -180, "maximum": 180 } },
      "required": ["angle_deg"],
      "additionalProperties": false
    }
  },
  {
    "type": "function",
    "name": "dog_gesture",
    "description": "Perform a short on-the-spot gesture. The dog must be standing.",
    "parameters": {
      "type": "object",
      "properties": { "gesture": { "type": "string", "enum": ["hello", "stretch", "dance1", "dance2"] } },
      "required": ["gesture"],
      "additionalProperties": false
    }
  },
  {
    "type": "function",
    "name": "dog_look",
    "description": "Take a photo with the dog's front camera. The image is attached to the next message so you can describe it or plan.",
    "parameters": { "type": "object", "properties": {}, "additionalProperties": false }
  },
  {
    "type": "function",
    "name": "dog_say",
    "description": "Speak a short sentence through the dog's speaker.",
    "parameters": {
      "type": "object",
      "properties": { "text": { "type": "string", "maxLength": 200 } },
      "required": ["text"],
      "additionalProperties": false
    }
  },
  {
    "type": "function",
    "name": "robot_status",
    "description": "Get current state: posture, estimated position in the play area, battery, last error.",
    "parameters": { "type": "object", "properties": {}, "additionalProperties": false }
  }
]
```

Mappatura sul Go2 (vedi `robot-dog.md`):
- `stand_up` → `StandUp` + `BalanceStand`
- `sit` → `Sit`
- `lie_down` → `StandDown`
- `stop` → `StopMove`
- `walk` → loop di `Move(x, y, 0)` a 10 Hz, poi `StopMove`
- `turn` → `Move(0, 0, ±0.6)` per `|angle| / 0.6 rad` secondi ⚠️ (approssimato: si calibra al primo test)
- `gesture` → `Hello`, `Stretch`, `Dance1`, `Dance2`
- `look` → frame WebRTC in JPEG
- `say` → TTS Grok in WAV, poi `MediaPlayer` sulla peer connection

### 2.2 Drone (`tools_drone.json`)

```json
[
  {
    "type": "function",
    "name": "drone_takeoff",
    "description": "Take off and hover at about 1 m. Only when landed and the operator has armed the system.",
    "parameters": { "type": "object", "properties": {}, "additionalProperties": false }
  },
  {
    "type": "function",
    "name": "drone_land",
    "description": "Land in place.",
    "parameters": { "type": "object", "properties": {}, "additionalProperties": false }
  },
  {
    "type": "function",
    "name": "drone_hover",
    "description": "Stop and hover in place immediately. Always safe to call.",
    "parameters": { "type": "object", "properties": {}, "additionalProperties": false }
  },
  {
    "type": "function",
    "name": "drone_move",
    "description": "Fly a short straight segment relative to the drone's current heading. Movements that would leave the safe flight box are rejected.",
    "parameters": {
      "type": "object",
      "properties": {
        "direction":   { "type": "string", "enum": ["forward", "back", "left", "right", "up", "down"] },
        "distance_cm": { "type": "integer", "minimum": 20, "maximum": 150 }
      },
      "required": ["direction", "distance_cm"],
      "additionalProperties": false
    }
  },
  {
    "type": "function",
    "name": "drone_rotate",
    "description": "Rotate in place. Positive = clockwise.",
    "parameters": {
      "type": "object",
      "properties": { "degrees": { "type": "integer", "minimum": -180, "maximum": 180 } },
      "required": ["degrees"],
      "additionalProperties": false
    }
  },
  {
    "type": "function",
    "name": "drone_look",
    "description": "Capture a frame from the drone camera; the image is attached to the next message.",
    "parameters": { "type": "object", "properties": {}, "additionalProperties": false }
  },
  {
    "type": "function",
    "name": "robot_status",
    "description": "Get state: landed/flying, estimated position in the flight box, height, battery.",
    "parameters": { "type": "object", "properties": {}, "additionalProperties": false }
  }
]
```

Mappatura sul Tello:
- `takeoff` / `land` / `hover` → `takeoff`, `land`, `stop`
- `move` → `forward/back/left/right/up/down x`
- `rotate` → `cw` / `ccw`
- `look` → `get_frame_read().frame`

L'`emergency` (motori off) **non** è esposto a Grok: lo usa solo l'umano.

> Nota sulle immagini: l'output di un tool è testo. Per `*_look`, l'host restituisce `{"ok": true, "note": "image attached"}` e aggiunge il JPEG come **input immagine** nel turno successivo. ⚠️ Il formato dell'input immagine per Grok è documentato in `docs/grok-api/`.

## 3. Validatore deterministico (Python, indipendente dall'hardware)

```python
# safety.py
from dataclasses import dataclass, field
import math, time

@dataclass
class Limits:
    box_x: tuple = (-1.5, 1.5)      # metri, area di gioco misurata sul posto
    box_y: tuple = (-1.5, 1.5)
    box_z: tuple = (0.3, 1.6)       # solo drone
    max_step_m: float = 1.5
    max_walk_s: float = 3.0
    max_vx: float = 0.4; max_vy: float = 0.3; max_vyaw: float = 0.8
    min_battery: int = 25
    max_session_s: float = 300      # dopo 5 min si chiede conferma all'operatore

@dataclass
class Pose:
    x: float = 0.0; y: float = 0.0; z: float = 0.0; yaw_deg: float = 0.0

@dataclass
class SafetyState:
    mode: str = "GROUNDED"          # GROUNDED | READY (in piedi / in volo) | HALTED
    pose: Pose = field(default_factory=Pose)
    battery: int = 100
    armed_by_human: bool = False
    t_start: float = field(default_factory=time.time)

ALLOWED = {                          # tool → stati in cui è ammesso
    "dog_stand_up": {"GROUNDED"}, "dog_sit": {"READY"}, "dog_lie_down": {"READY", "GROUNDED"},
    "dog_stop": {"READY", "GROUNDED", "HALTED"}, "dog_walk": {"READY"}, "dog_turn": {"READY"},
    "dog_gesture": {"READY"}, "dog_look": {"READY", "GROUNDED"}, "dog_say": {"READY", "GROUNDED"},
    "drone_takeoff": {"GROUNDED"}, "drone_land": {"READY"}, "drone_hover": {"READY", "HALTED"},
    "drone_move": {"READY"}, "drone_rotate": {"READY"}, "drone_look": {"READY", "GROUNDED"},
    "robot_status": {"READY", "GROUNDED", "HALTED"},
}
DIR = {"forward": (1, 0, 0), "back": (-1, 0, 0), "left": (0, 1, 0), "right": (0, -1, 0),
       "up": (0, 0, 1), "down": (0, 0, -1)}

class Rejected(Exception): pass

def _inside(L, x, y, z=None):
    ok = L.box_x[0] <= x <= L.box_x[1] and L.box_y[0] <= y <= L.box_y[1]
    return ok and (z is None or L.box_z[0] <= z <= L.box_z[1])

def validate(name: str, args: dict, S: SafetyState, L: Limits) -> Pose | None:
    """Restituisce la posa prevista dopo il comando; solleva Rejected con il motivo."""
    if name not in ALLOWED:                    raise Rejected(f"unknown tool {name}")
    if S.mode == "HALTED" and name not in ("dog_stop", "drone_hover", "robot_status"):
        raise Rejected("halted by human operator: wait for re-arm")
    if S.mode not in ALLOWED[name]:            raise Rejected(f"{name} not allowed in state {S.mode}")
    if name in ("dog_stand_up", "drone_takeoff"):
        if not S.armed_by_human:               raise Rejected("operator has not armed the system")
        if S.battery < L.min_battery:          raise Rejected(f"battery {S.battery}% < {L.min_battery}%")
    if time.time() - S.t_start > L.max_session_s: raise Rejected("session time exceeded: operator must confirm")

    p = S.pose; yaw = math.radians(p.yaw_deg)
    if name == "drone_takeoff": return Pose(p.x, p.y, 1.0, p.yaw_deg)   # Tello: hover a circa 1 m ⚠️ da misurare
    if name == "drone_land":    return Pose(p.x, p.y, 0.0, p.yaw_deg)
    if name == "dog_walk":
        vx, vy, d = float(args["forward_mps"]), float(args["lateral_mps"]), float(args["duration_s"])
        if abs(vx) > L.max_vx or abs(vy) > L.max_vy or not (0 < d <= L.max_walk_s):
            raise Rejected("velocity/duration out of limits")
        dx, dy = vx * d, vy * d
        nx = p.x + dx * math.cos(yaw) - dy * math.sin(yaw)
        ny = p.y + dx * math.sin(yaw) + dy * math.cos(yaw)
        if not _inside(L, nx, ny):             raise Rejected("would leave the play area")
        return Pose(nx, ny, 0, p.yaw_deg)
    if name == "drone_move":
        ux, uy, uz = DIR[args["direction"]]; d = int(args["distance_cm"]) / 100
        if not (0.2 <= d <= L.max_step_m):     raise Rejected("distance out of limits")
        nx = p.x + d * (ux * math.cos(yaw) - uy * math.sin(yaw))
        ny = p.y + d * (ux * math.sin(yaw) + uy * math.cos(yaw))
        nz = p.z + d * uz
        if not _inside(L, nx, ny, nz):         raise Rejected("would leave the flight box")
        return Pose(nx, ny, nz, p.yaw_deg)
    if name in ("dog_turn", "drone_rotate"):
        a = float(args.get("angle_deg", args.get("degrees", 0)))
        if abs(a) > 180:                       raise Rejected("angle out of limits")
        sign = 1 if name == "dog_turn" else -1   # drone: positivo = orario
        return Pose(p.x, p.y, p.z, (p.yaw_deg + sign * a) % 360)
    return None
```

⚠️ Il dead reckoning deriva: dopo qualche comando la posa stimata non corrisponde più a quella reale. Il box va tenuto **più piccolo** dell'area fisica (margine di almeno 1 m). Con il Tello EDU si può riallineare la posa con i mission pad, con il Go2 con l'odometria (`rt/utlidar/robot_pose`, ⚠️ non testato).

## 4. Executor, kill switch e loop con Grok

```python
# agent.py: schema minimo (Responses API xAI tramite SDK OpenAI-compatibile ⚠️)
import json, os, threading
from openai import OpenAI
from safety import SafetyState, Limits, validate, Rejected

client = OpenAI(api_key=os.environ["XAI_API_KEY"], base_url="https://api.x.ai/v1")
TOOLS = json.load(open("tools_drone.json"))
S, L = SafetyState(), Limits()
lock = threading.Lock()                 # una sola azione fisica alla volta
driver = ...                            # MockDriver() oppure TelloDriver(), con la stessa interfaccia

SYSTEM = """You control a small indoor drone in a museum. Use ONLY the provided tools.
Move in small steps, call drone_look before moving toward something you can't see,
and land when the task is done or if anything is unclear. If a tool is rejected, explain
why to the user and propose a safe alternative. Never insist on a rejected action."""

def dispatch(name, args):
    if S.mode == "HALTED" and name not in ("drone_hover", "dog_stop", "robot_status"):
        return {"ok": False, "reason": "halted by operator"}
    try:
        new_pose = validate(name, args, S, L)
    except Rejected as e:
        return {"ok": False, "reason": str(e)}
    with lock:
        result = driver.execute(name, args)          # bloccante, con timeout interno
    if result.get("ok") and new_pose: S.pose = new_pose
    if name in ("drone_takeoff", "dog_stand_up") and result.get("ok"): S.mode = "READY"
    if name in ("drone_land", "dog_lie_down") and result.get("ok"):    S.mode = "GROUNDED"
    return result

def run(user_text):
    resp = client.responses.create(model="grok-4.7", tools=TOOLS, parallel_tool_calls=False,
        input=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": user_text}])
    for _ in range(12):                                  # limite di passi
        calls = [it for it in resp.output if it.type == "function_call"]
        if not calls:
            return resp.output_text
        outs = [{"type": "function_call_output", "call_id": c.call_id,
                 "output": json.dumps(dispatch(c.name, json.loads(c.arguments or "{}")))} for c in calls]
        resp = client.responses.create(model="grok-4.7", tools=TOOLS, parallel_tool_calls=False,
                                       input=outs, previous_response_id=resp.id)
    driver.execute("drone_hover", {}); return "step limit reached, hovering"

def kill_switch():                                       # thread con priorità sul loop
    while True:
        c = input()
        if c.strip() == "":  S.mode = "HALTED"; driver.halt()       # INVIO = stop / hover
        if c.strip() == "k": S.mode = "HALTED"; driver.kill()       # k = emergency (motori off)
        if c.strip() == "a": S.armed_by_human = True; S.mode = "GROUNDED" if S.mode == "HALTED" else S.mode
threading.Thread(target=kill_switch, daemon=True).start()
```

Note:
- `driver.halt()` e `driver.kill()` **non devono prendere `lock`**: vanno sempre eseguiti, anche durante un'azione. Per il Tello si usa il socket UDP separato (vedi `drones.md` §1.2), per il Go2 un `StopMove` sulla stessa connessione WebRTC, che è asincrona. ⚠️ Per il Go2 va verificato che un `StopMove` interrompa il loop `Move` in corso: il loop deve controllare `S.mode` a ogni iterazione.
- **Keyword vocale locale:** se si usa Grok Voice, va controllata anche la trascrizione in ingresso (o un piccolo keyword spotter offline) **prima** di passarla all'LLM. Se compare "stop", "fermo", "basta" o "atterra" si chiama subito `driver.halt()`. Non si aspetta il round trip del modello: la latenza di rete più quella del modello può superare un secondo.
- **Telecomando fisico** (Go2) o app ufficiale pronta (Tello): sempre in mano a un operatore che non sta scrivendo codice.

## 5. Simulazione prima del reale

```python
class MockDriver:
    def __init__(self): self.log = []
    def execute(self, name, args):
        self.log.append((name, args)); print("[MOCK]", name, args)
        return {"ok": True}
    def halt(self): print("[MOCK] HALT")
    def kill(self): print("[MOCK] KILL")
```

Fasi:
1. Grok con `MockDriver`: si provano prompt avversari ("vola fino al soffitto", "fai un flip", "corri verso la gente") e si verifica che il validatore rifiuti.
2. Hardware reale **a terra** o con il cane sdraiato: si provano connessione, `look`, `say`, `status`.
3. Movimento reale con limiti ridotti al 50% e operatore con kill switch.
4. Demo.

Per Go2 esiste `unitree_mujoco` (via `unitree_sdk2`), per PX4/ArduPilot c'è SITL. Dettagli in `robot-dog.md` e `drones.md`.

## 6. Checklist di sicurezza (prima di ogni sessione)

- [ ] Area delimitata (nastro o transenne), **nessuno dentro** tranne l'operatore. Lontano da vetrine e reperti del museo.
- [ ] Drone: soffitto e lampade a distanza; niente tende o cavi sospesi; luce sufficiente e pavimento non uniforme per il sensore ottico; paraeliche montate.
- [ ] Cane: pavimento non scivoloso, niente scale o gradini nell'area, cavi a terra fissati.
- [ ] Batteria ≥ 30% all'avvio (soglia del validatore al 25%). Batterie di ricambio cariche.
- [ ] Operatore dedicato con telecomando o app e kill switch da tastiera provato **prima** di decollare o alzarsi.
- [ ] `--real` solo dopo aver eseguito la stessa sequenza in mock.
- [ ] App ufficiale chiusa (Go2: un solo client WebRTC), ma disponibile su un telefono come piano B.
- [ ] Limiti del validatore misurati sull'area reale (box più piccolo di almeno 1 m per lato).
- [ ] Log attivi. Nessuna API key nel codice committato.
- [ ] Un solo team alla volta sull'hardware condiviso (concordarlo con lo staff).

## 7. Domande da fare allo staff (hardware tour, mer 09:00)

**Cane robot**
1. Marca, modello e variante esatta (per esempio Go2 Air, Pro o EDU)? **Versione firmware?**
2. A quale account Unitree è associato? Potete recuperare la **chiave AES** per WebRTC (firmware ≥ 1.1.15), con `unitree-fetch-aes-key`?
3. C'è il telecomando? Chi lo tiene durante i test? Cosa fa l'e-stop sul telecomando?
4. Possiamo usare la modalità STA (cane sul vostro Wi-Fi) o solo AP? Qual è l'IP?
5. (EDU) Possiamo collegarci via Ethernet o al Jetson di bordo?
6. Quante batterie ci sono e quanto dura la ricarica? Quanti team lo useranno e con quali turni?
7. Ci sono motion o "trick" vietati? (Per noi: niente flip o salti.)
8. Ci sono un'area designata e il tipo di pavimento?

**Droni**
1. Quali modelli e quanti (Tello o Tello EDU? altri)? Firmware aggiornato (serve per `streamon`)?
2. Quante batterie e caricatori? Ci sono paraeliche? Mission pad (EDU)?
3. Dove si può volare? Altezza del soffitto, rete di protezione o gabbia?
4. È ammesso il volo autonomo da codice? Chi è il pilota responsabile?
5. C'è un router Wi-Fi dedicato per la station mode o lo swarm (EDU)? Il Wi-Fi del museo isola i client (client isolation)?
6. Ci sono vincoli assicurativi o regolamentari (indoor, sotto i 250 g, ma comunque in un luogo pubblico)?

**Generale**
1. Il **braccio robotico** elencato sul sito: quale modello e come si controlla? È libero?
2. Chi è il referente tecnico per ciascun dispositivo durante la notte?
3. Ci sono dongle Wi-Fi USB, cavi Ethernet o hub disponibili?
4. Possiamo installare app o librerie sui dispositivi (per esempio un'app Android per i DJI)?

## Fonti

- xAI function calling (formato tool, `tool_choice`, `parallel_tool_calls`, `function_call_output`, `previous_response_id`, modello `grok-4.7`): https://docs.x.ai/docs/guides/function-calling
- xAI Voice (endpoint `wss://api.x.ai/v1/realtime`, `session.update`): https://docs.x.ai/developers/model-capabilities/audio/voice
- Grok Voice e function call, fonti di terze parti (⚠️): https://mastra.ai/reference/voice/xai-realtime , https://docs.pipecat.ai/server/services/s2s/grok , https://docs.inworld.ai/realtime/usage/using-realtime-models
- Sito evento (stack Grok elencato): https://pavia.grokbot.it
- Tello SDK 2.0 (autolanding dopo 15 s, `stop` / `emergency`): https://dl-cdn.ryzerobotics.com/downloads/Tello/Tello%20SDK%202.0%20User%20Guide.pdf
- Go2 WebRTC (un solo client, comandi sport): https://github.com/legion1581/unitree_webrtc_connect
- Vedi anche le fonti in `robot-dog.md` e `drones.md`.
