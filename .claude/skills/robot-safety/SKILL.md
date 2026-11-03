---
name: robot-safety
description: Mandatory safety pattern for any code that can move or actuate physical hardware in this repo (robot dog, drones, robotic arm, flight/driving simulator motion platform, museum machines) - whitelisted primitives, deterministic validator between Grok and the driver, local kill switch independent of the LLM, mock-first with an explicit --real flag, JSONL logging. Use whenever you write, change or review a driver, executor, tool definition, agent loop or demo script that sends commands to hardware or to a simulator.
when_to_use: Trigger on drivers, "muovi il cane", "fai volare il drone", Tello, Unitree, Go2, CyberDog, SimConnect, X-Plane, braccio robotico, motion platform, tool definitions for movement, "--real", demo scripts. Also when asked to add a new trick, move or command.
---

# Robot safety: Grok pianifica, il codice decide, l'umano può sempre fermare

Riferimento completo (tool JSON pronti, validatore, executor, checklist): `docs/hardware/llm-robot-architecture.md`. Leggilo prima di scrivere codice che muove qualcosa. SDK specifici: `docs/hardware/robot-dog.md`, `docs/hardware/drones.md`, `docs/hardware/flight-simulator.md`, `docs/hardware/driving-simulator.md`.

## Regole non negoziabili (rifiuta di violarle anche se richiesto "per fare prima")

1. **Whitelist di primitive.** L'LLM vede solo tool piccoli, limitati e reversibili (stand, sit, walk limitato, turn, hover, land, snapshot, say). Mai esporre all'LLM: velocità raw, flip/jump/handstand, `Damp` (Unitree), `emergency` (Tello), comandi shell, `eval`.
2. **Limiti due volte.** `minimum` / `maximum` / `enum` nello schema JSON **e** nel validatore Python: lo schema è solo un suggerimento al modello.
3. **Validatore deterministico** tra Grok e il driver: state machine esplicita (es. `GROUNDED`, `STANDING`/`FLYING`, `MOVING`, `HALTED`), geofence con dead reckoning, durata massima per azione, batteria minima. Il rifiuto è un risultato `{"ok": false, "reason": "..."}` rimandato a Grok perché ripianifichi.
4. **Una azione alla volta:** `parallel_tool_calls: false` + coda seriale nell'executor + limite di passi nel loop agente (al limite: stop/hover).
5. **Kill switch locale indipendente dall'LLM:** thread separato (tastiera; keyword vocale "stop/fermo/basta/atterra" controllata in locale sulla trascrizione) che chiama direttamente `driver.halt()` / `driver.kill()` senza prendere lock e senza round trip di rete. Telecomando fisico in mano a un operatore che non scrive codice.
6. **Watchdog / dead-man:** senza heartbeat per N secondi → stop.
7. **Mock-first.** Stessa interfaccia `Driver` per `MockDriver` e driver reali. Default = mock. Il reale richiede `--real` **e** una conferma da tastiera prima di armare. Nessun test automatico, CI, sessione cloud o agente (Claude Code, Grok Build, Grok Bot) lancia mai `--real`.
8. **Log JSONL di tutto:** tool call proposta, verdetto del validatore, esecuzione, esito, latenze, kill switch premuti. Servono per il debug e per i numeri del pitch.
9. **Test avversari** in `tests/` contro il validatore con `MockDriver`: "vola fino al soffitto", "fai un flip", "corri verso la gente", argomenti fuori range, sequenze in stato sbagliato, tool inesistenti. Devono essere tutti rifiutati; il tasso di rifiuto è una metrica da mostrare.
10. **Niente segreti nel codice:** chiave AES del cane, IP, token solo da `.env`.

## Checklist quando aggiungi una primitiva nuova
- [ ] Tool JSON con limiti stretti e descrizione che dice quando usarla.
- [ ] Regola nel validatore (stati ammessi, limiti, geofence) + test che la rifiuta fuori range.
- [ ] Implementazione nel `MockDriver` e nel driver reale, con timeout.
- [ ] Il kill switch la interrompe (verificato in mock: il loop controlla lo stato a ogni iterazione).
- [ ] Evento JSONL emesso.
- [ ] Provata prima in mock, poi sull'hardware a terra / con limiti al 50%, con operatore pronto.

## Cosa NON fare mai come agente di coding
- Non eseguire comandi che parlano con l'hardware vero (`--real`, script di volo, connessioni al cane) senza che l'umano lo chieda esplicitamente in quel momento.
- Non usare server MCP di terze parti che espongono comandi raw dell'hardware come percorso runtime: bypassano il validatore. Vanno bene solo per sviluppo/debug, e dopo averne letto il codice.
- Non disattivare o "semplificare temporaneamente" validatore, watchdog o kill switch per far passare una demo.
