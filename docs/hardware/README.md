# Hardware del museo: indice

> Ricerca del 2026-11-03. **Marche e modelli non sono pubblicati da nessuna parte**: i file coprono i candidati più probabili. Al giro di mer 9:00 confermare con lo staff ([../ideas/staff-questions.md](../ideas/staff-questions.md)) e poi aggiornare questi file.

## Cosa c'è (secondo pavia.grokbot.it e fonti pubbliche)

| Hardware | Cosa sappiamo | File |
|---|---|---|
| Cane robot | Modello ignoto. StartupItalia (letto solo da snippet ⚠️) parla di "cyberdog già presenti, in attesa di certificazione" → forse Xiaomi CyberDog; candidato principale nelle guide: Unitree Go2 | [robot-dog.md](robot-dog.md) |
| Droni | "A few drones", modello ignoto. Candidato più probabile per indoor: DJI/Ryze Tello (EDU) | [drones.md](drones.md) |
| Bracci robotici (3 cobot) | **Arm 1** + camera 1 (traccia C), **arm 2** + camera 2 (A), **arm 3** senza camera (04, 05). Utensile stampato forchetta/spintore/punta, niente gripper, solo vassoi fessurati. Slot da 30 minuti con lo staff. Modello ignoto | [robot-arm.md](robot-arm.md), [../event/tracks.md](../event/tracks.md) |
| Simulatore di volo | "Three-screen flight simulator on a motion platform" (alt text del sito), stanza dedicata; software ignoto (MSFS / X-Plane / FlightGear) | [flight-simulator.md](flight-simulator.md) |
| Simulatore di guida | "Seat and steering wheel", usato per un progetto di guida sicura con le scuole; software ignoto | [driving-simulator.md](driving-simulator.md) |
| Macchine d'epoca | C64, PET 2001, Amiga 1000, Apple Lisa, Olivetti Programma 101; **Ultimate 64 Elite MK2 con REST API**; "chattralino" (centralino con telefoni a disco + ChatGPT); Videotel via ESP32 | [retro-machines.md](retro-machines.md), [../event/museum.md](../event/museum.md) |

Inventario e fonti: [museum-inventory.md](museum-inventory.md) (cane, droni, braccio) e [museum-inventory-sims.md](museum-inventory-sims.md) (simulatori, macchine d'epoca, 15 domande allo staff).

## Guide

- [llm-robot-architecture.md](llm-robot-architecture.md): **leggere per primo**. Grok → validatore deterministico → executor, kill switch locale, tool JSON pronti per cane (10) e drone (7), codice del validatore, loop con Grok, mock driver, checklist di sicurezza.
- [robot-dog.md](robot-dog.md): riconoscere il modello in 10 minuti; Unitree Go2 (WebRTC `unitree_webrtc_connect`, SDK ufficiale su Ethernet per EDU, ROS2); Go1, Petoi Bittle, CyberDog, Spot; simulazione.
- [drones.md](drones.md): Tello/Tello EDU (SDK UDP, kill switch, swarm), Crazyflie, DJI MSDK, Parrot Olympe, PX4/ArduPilot (`mavsdk-grpc`), mock e simulatori.
- [flight-simulator.md](flight-simulator.md): MSFS/SimConnect (simvar, eventi autopilota), X-Plane 12 Web API e UDP, XPPython3, FlightGear; prodotti esistenti (SayIntentions, BeyondATC…); tool proposti per Grok.
- [driving-simulator.md](driving-simulator.md): telemetria ACC, iRacing, F1 23/24/25, BeamNG (unico in cui Grok può guidare davvero), Forza, ETS2; `vgamepad` per gli input.
- [cockpit-as-controller.md](cockpit-as-controller.md): volante/pedali/cloche come joystick (pygame) per guidare drone o cane, con dead-man switch.
- [retro-machines.md](retro-machines.md): BASIC V2, VICE + petcat, bridge C64 ↔ LLM **provato end-to-end in VICE** (monitor binario porta 6502), REST API Ultimate 64, telefoni a disco, Programma 101, DOSBox.

## Trappole da ricordare (dettagli nei file)

- **Go2:** firmware ≥ 1.1.15 richiede la chiave AES del proprietario; un solo client alla volta (chiudere l'app); comandi di velocità da ripetere in loop; **mai `Damp`** (il cane crolla).
- **Tello:** collegati al suo Wi-Fi si perde Internet (serve un secondo adattatore o un EDU in station mode); atterra da solo dopo 15 s senza comandi → keepalive mentre Grok pensa.
- **MSFS:** il wrapper Python `SimConnect` è solo Windows 64 bit e testato su MSFS 2020; heading/pitch/bank in radianti; aerei di terze parti spesso ignorano gli eventi AP standard.
- **X-Plane 12 Web API:** porta 8086, solo localhost → il codice gira sul PC del simulatore (oppure UDP 49000 in LAN).
- **VICE:** ogni comando al monitor binario ferma l'emulazione, mandare subito il comando di uscita; il pacchetto Ubuntu non ha le ROM.
