# Il cockpit come controller: volante, pedali e cloche per pilotare drone e cane

> Verificato il: **2026-11-03**. ✅ = verificato su doc · ⚠️ = non verificato o da provare sul posto.
> Idea: le periferiche del simulatore di guida (volante, pedali) e del simulatore di volo (cloche o yoke, manetta, pedaliera) sono quasi sempre **USB HID game controller standard** ⚠️. Si possono leggere da Python e usare per pilotare il **drone** (`drones.md`) o il **cane robot** (`robot-dog.md`). Grok fa da **copilota vocale** sopra il controllo manuale: "Grok, atterra", "Grok, cosa vede la camera?", "Grok, torna alla base".

## 1. Perché è una bella demo (e perché è sicura)

- Unisce due hardware del museo, cioè cockpit e robot, ed è un "ponte tra epoche/oggetti" in stile Ctrl+Alt.
- **Il controllo continuo resta all'umano.** Grok interviene solo con primitive di alto livello in whitelist (`land`, `hover`, `return_home`, `describe_view`, `sit`) e passa dal validatore di `llm-robot-architecture.md`. Questo è il pattern "human in the loop" che il sito dell'hackathon cita tra i principi.
- **Dead-man switch naturale**:
  - **drone**: niente gas, cioè pedale dell'acceleratore rilasciato, significa `rc 0 0 0 0` (hover);
  - **cane**: niente pedale significa `StopMove`;
  - un pulsante del volante fa da **kill switch** locale, indipendente da Grok.

## 2. Leggere le periferiche da Python

### Dove far girare il codice
- **Su Windows nativo** (Python per Windows), non dentro WSL. In WSL2 le periferiche USB HID **non sono visibili** senza `usbipd-win` ⚠️. Su Linux nativo o Raspberry Pi i dispositivi compaiono come `/dev/input/js*` / `event*`.
- Se volante e pedali sono collegati al PC del simulatore e il gioco è aperto, il gioco **continua a leggerli** (DirectInput è condiviso) ⚠️. Per la demo conviene chiudere il gioco, oppure staccare l'USB e collegarla al nostro laptop, **col permesso dello staff**.

### pygame (consigliato) ✅
- Con `pygame.joystick` gli assi valgono da -1 a 1, i pulsanti sono booleani, gli hat restituiscono `(x, y)`. In pygame 2 c'è l'hotplug con gli eventi `JOYDEVICEADDED`/`JOYDEVICEREMOVED`: i joystick vanno indicizzati per `instance_id`. **La coda eventi va svuotata spesso** (`pygame.event.pump()`/`get()`). C'è anche `rumble()` (pygame 2.0.2+), che però sui volanti con force feedback DirectInput probabilmente non funziona ⚠️. ✅ (doc pygame)
- ⚠️ Senza finestra a fuoco SDL può ignorare gli eventi. Va impostato `SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS=1` **prima** di `pygame.init()` (hint SDL, non riverificato oggi).
- `pip install pygame` (oppure `pygame-ce`, API joystick equivalente ⚠️).

**Step 1: scoprire gli assi** (la mappatura cambia da modello a modello: G29, T300, yoke Honeycomb ecc. ⚠️)
```python
import os; os.environ["SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS"] = "1"
import pygame, time
pygame.init()
joys = {}
while True:
    for ev in pygame.event.get():
        if ev.type == pygame.JOYDEVICEADDED:
            j = pygame.joystick.Joystick(ev.device_index); joys[j.get_instance_id()] = j
            print("+", j.get_name(), "axes", j.get_numaxes(), "buttons", j.get_numbuttons(), "hats", j.get_numhats())
        elif ev.type == pygame.JOYBUTTONDOWN:
            print("button", ev.instance_id, ev.button)
    for j in joys.values():
        print(j.get_name()[:20], [round(j.get_axis(a), 2) for a in range(j.get_numaxes())], end="   \r")
    time.sleep(0.05)
```
Si muove un controllo alla volta e si annota quale asse cambia. ⚠️ I pedali spesso vanno da **+1 a riposo a -1 premuti**, oppure il contrario, a volte su un dispositivo USB separato. Sui Logitech, frizione e freno possono essere invertiti.

**Step 2: mapping verso il drone (Tello `rc lr fb ud yaw`, da -100 a 100)**
```python
import os; os.environ["SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS"] = "1"
import pygame, time
from djitellopy import Tello            # see drones.md

AX_STEER, AX_GAS, AX_BRAKE = 0, 1, 2    # <- fill in from step 1
BTN_KILL, BTN_TAKEOFF, BTN_LAND = 0, 1, 2
MAX = 40                                # our indoor cap (rc accepts -100..100)

def pedal(v):                           # +1 released .. -1 pressed  ->  0..1   (⚠️ check the sign)
    return max(0.0, min(1.0, (1.0 - v) / 2.0))
def dz(v, d=0.08):
    return 0.0 if abs(v) < d else v

pygame.init(); j = pygame.joystick.Joystick(0)
t = Tello(); t.connect()
try:
    while True:
        pygame.event.pump()
        if j.get_button(BTN_KILL):
            t.emergency(); break                         # motors off: local kill switch
        if j.get_button(BTN_TAKEOFF): t.takeoff()
        if j.get_button(BTN_LAND):    t.land()
        gas, brake = pedal(j.get_axis(AX_GAS)), pedal(j.get_axis(AX_BRAKE))
        steer = dz(j.get_axis(AX_STEER))
        fb = int(MAX * (gas - brake))                    # throttle forward, brake backward
        yaw = int(MAX * steer)
        if gas < 0.05 and brake < 0.05:
            fb, yaw = 0, 0                               # dead-man: no pedal = hover
        t.send_rc_control(0, fb, 0, yaw)                 # lr=0, ud=0 (paddles/hat for altitude)
        time.sleep(0.05)                                 # 20 Hz
finally:
    t.send_rc_control(0, 0, 0, 0)
```
- Per il **cane robot** vale lo stesso schema con `Move(vx, vy, vyaw)` a 10 Hz e `StopMove` quando il pedale è rilasciato. Limiti da `robot-dog.md`: |vx| ≤ 0,4 m/s, |vyaw| ≤ 0,8 rad/s.
- Con la **cloche o lo yoke del simulatore di volo** la mappatura è naturale per il drone: pitch su `fb`, roll su `lr`, pedaliera su `yaw`, manetta su `ud` o sulla velocità.

### Alternative a pygame
- `inputs` (PyPI): eventi gamepad e joystick senza SDL ⚠️ (non verificato oggi).
- `hidapi` (`pip install hidapi`, `import hid`; `hid.enumerate()` elenca VID/PID): **report HID grezzi**. Utile se il dispositivo non si presenta come joystick, per esempio un pannello MobiFlight o bottoni custom. Il parsing è a carico nostro ⚠️.
- Linux: `evdev` (anche force feedback) ⚠️.

## 3. Grok sopra il controllo manuale

```
volante/pedali ──20 Hz──► loop locale (deadzone, limiti, dead-man, kill) ──► drone / cane
                                     ▲
microfono ─► Grok Voice ─tool call──┘  (solo: land, hover, return_home, describe_view, set_max_speed)
```
- Il loop locale ha **priorità**: se Grok chiama `land()`, il loop la esegue e per N secondi ignora i pedali, salvo il kill switch.
- `describe_view()`: frame dalla camera del drone o del cane → Grok Vision → risposta vocale ("davanti c'è una vetrina con un Commodore 64"). Vedi `../grok-api/vision.md`.
- `set_max_speed(pct)`: Grok può solo **ridurre** il limite, non alzarlo oltre il massimo del validatore.
- **Log JSONL** di input, tool call e latenze: alla giuria servono numeri, per esempio la latenza voce-azione e il numero di interventi del dead-man.

## 4. Domande allo staff (specifiche)
1. Marca e modello di volante, pedali, cambio, cloche/yoke, manetta, pedaliera. Sono USB diretti al PC o passano da una base (Fanatec, Simucube) con driver dedicati?
2. Possiamo staccarli dal PC del simulatore o usarli con il gioco chiuso?
3. Il drone o il cane si possono usare in un'area delimitata vicino al cockpit (raggio Wi-Fi del Tello, cavi)?

## Fonti
- pygame joystick: https://www.pygame.org/docs/ref/joystick.html
- Tello e DJITelloPy (comandi `rc`, keepalive, emergency): vedi `drones.md` e le sue fonti
- Cane robot (Move/StopMove, limiti): vedi `robot-dog.md`
- Architettura sicura LLM → robot: vedi `llm-robot-architecture.md`
- vgamepad (il percorso inverso: controller virtuale verso un gioco): https://github.com/yannbouteiller/vgamepad
