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
