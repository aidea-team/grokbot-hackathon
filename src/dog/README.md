# src/dog: Unitree Go1

Driver del cane Unitree Go1 del museo, più un hello world che lo fa avanzare di circa 1 m.

| File | Cosa fa |
|---|---|
| `driver.py` | `MockDriver` (default, senza rete) e `Go1Driver` (`free-dog-sdk`, comandi high-level UDP). Interfaccia: `connect()`, `walk(vx, vyaw, seconds)`, `stop()`, `halt()`, `close()`. Limiti rigidi in `validate_walk()`: \|vx\| ≤ 0.4 m/s, \|vyaw\| ≤ 0.6 rad/s, al massimo 10 s per comando. |
| `walk1m.py` | Hello world: avanti di `--distance` m a `--speed` m/s, poi fermo in piedi. |

Ogni evento (connessione, richiesta con il verdetto del validatore, fine camminata, stop, kill switch) finisce in `logs/dog-AAAAMMGG.jsonl`.

## Uso

```bash
source .venv/bin/activate
python src/dog/walk1m.py                    # mock
python src/dog/walk1m.py --real             # cane vero: chiede di scrivere "go"
python src/dog/walk1m.py --real --distance 0.5 --speed 0.15
```

**Kill switch:** premi INVIO (o Ctrl+C) e il cane passa a velocità zero, fermo in piedi. Il telecomando fisico resta comunque in mano a qualcuno.

## Prerequisiti per `--real`

1. `./scripts/setup.sh` già lanciato **con Internet**: clona `free-dog-sdk` in `vendor/`.
2. Cane acceso e in piedi.
3. PC sul Wi-Fi del cane `Unitree_Go…`, password `00000000`. Il PC prende un IP `192.168.12.x` e il cane risponde su `192.168.12.1` (`ping 192.168.12.1`).
4. Se l'IP è diverso, mettilo in `.env` come `GO1_ADDR=...`.

## Note

- `free-dog-sdk` (Bin4ry) è un reverse engineering della `unitree_legged_sdk` e **non ha le safety features** dell'originale. Per questo i limiti stanno nel nostro `driver.py`.
- Non esponiamo `DAMPING` (spegne i motori: il cane cade), `BACKFLIP`, `JUMPYAW` e simili.
- Il metro è stimato (velocità × tempo): la velocità reale può essere diversa. Misuratela col metro e annotate qui il fattore di correzione.
- Stato: provato in mock e contro un finto cane UDP in locale (pacchetti `VEL_WALK` e `IDLE` corretti). **Non ancora provato sul Go1 vero.**

## Unitree Go2 (stessa architettura, non ancora provato)

Nella webapp (`src/chat`) lo switch **Go1 | Go2** in alto sceglie il robot. Il Go2 ha gli stessi stati, kill switch, watchdog e log JSONL del Go1 (è lo stesso `RealBody`, con un altro set di comandi).

| File | Cosa fa |
|---|---|
| `go2_commands.py` | Un'unica definizione di tool, validazione ed esecuzione per mock e cane vero: `walk`, `strafe` (passo laterale, solo Go2), `turn`, `stand`, `stand_up`, `lie_down`, `recovery`, `sit`, `rise_sit`, `hello`, `stretch`, `dance` 1/2. **Senza** `Damp` (mai) e senza flip (gli `api_id` cambiano fra firmware). |
| `go2_driver.py` | `Go2MockDriver` (default, senza rete), `Go2Driver` + `Go2Link` (WebRTC con `unitree_webrtc_connect`, importata solo all'arm), telecamera frontale (`Go2Camera`) e vista dall'alto sintetica per il mock. |
| `../chat/go2_bodies.py` | I due body (mock e vero) per l'hub. |

- **Mock Go2:** cinematico (nessuna fisica), l'immagine al modello è una vista dall'alto *sintetica*, non una telecamera. Serve a provare chat, tool e odometria. Non esiste la modalità *both* per il Go2.
- **Cane vero:** `mjpython src/chat/app.py --real` (lo lancia un umano), poi Go2 → real → checklist. Prerequisiti: `.venv/bin/pip install unitree_webrtc_connect`, **chiudere l'app Unitree Go** (un solo client WebRTC), Wi-Fi del cane (o `GO2_ADDR` in `.env`), `GO2_AES_KEY` se firmware ≥ 1.1.15.
- `Move` è un comando di velocità ripetuto a 20 Hz e chiuso da `StopMove`; i trick sono one-shot (si invia una volta, poi si aspetta). Il kill switch invia `StopMove` subito, dal thread chiamante. Dopo un trick di postura il driver manda `BalanceStand` prima di muoversi.
- **Da verificare sul Go2 vero (marcato `VERIFY` nel codice):** segno di `z` (sinistra positivo?), durate dei trick (stime), `BalanceStand` prima di `Move`, topic/campo della batteria (`LOW_STATE` → `bms_state.soc`), resa della telecamera. Il JEV non è disponibile per il Go2 (è tarato sul Go1).
- Test senza hardware: `python tests/test_go2.py` (finto link WebRTC).
