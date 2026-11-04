# G1 U2 (Unitree) in MuJoCo

Umanoide Unitree G1 simulato, comandabile da browser con **WASD**. Solo comandi di **alto livello** (velocità x, y, imbardata):
le gambe le muove la **policy di locomozione standard di Unitree** (`unitree_rl_gym`, `deploy/pre_train/g1/motion.pt`),
non nostro codice di controllo.

## Avvio

- Dentro la chat (switch **G1 U2** in alto): `mjpython src/chat/app.py` → <http://127.0.0.1:8765/g1/>
- Da solo: `python src/g1/g1_app.py --port 8766` → <http://127.0.0.1:8766>

La fisica parte alla prima apertura della pagina e il rendering si ferma quando nessuno guarda.
Tasti: **W/S** avanti/indietro, **A/D** gira, **Q/E** passo laterale, **Maiusc** più veloce, **Spazio/Esc** stop, **R** rialzati (reset).
Trascina l'immagine per ruotare la vista, rotella per lo zoom. Test: `python tests/test_g1.py`.

## Com'è fatto

- `assets/g1_12dof.xml` + `meshes/`: modello G1 con 12 giunti alle gambe e busto/braccia fissi (da `unitree_rl_gym`, BSD-3). È il modello su cui la policy è stata addestrata: **le braccia non si muovono**.
- `assets/motion.pt` è l'originale; `assets/motion_weights.npz` ne contiene i pesi (LSTM 47→64, MLP 64→32→12, ELU). `g1_policy.py` li esegue in numpy, **senza torch** (scarto massimo vs torch: 1e-6).
- `g1_world.py`: stessa pipeline di `deploy_mujoco.py` (policy a 50 Hz, PD a 500 Hz, kp/kd/default di `g1.yaml`); comando con rampa e watchdog di 0,4 s (se il browser tace, il robot si ferma); rilevamento caduta (bacino < 0,45 m) e reset. Il rendering ha un thread suo.
- Limiti dei comandi: vx ±0,8 m/s, vy ±0,4 m/s, ω ±1,0 rad/s. Misurati: 0,5 → ~0,44 m/s, 0,8 → ~0,73 m/s, ω 0,8 → ~41°/s.

## Non fatto / da sapere

- Solo simulatore: nessun driver per il G1 vero (SDK Unitree `LocoClient`/DDS non toccato).
- Nessuna integrazione con la chat/agente Grok: oggi è solo manuale. Il G1 vero ha 29 giunti e la sua policy di fabbrica: questa è la stessa famiglia di policy ma non quella del robot reale.
