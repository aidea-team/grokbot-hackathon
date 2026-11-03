# Inventario hardware del Ctrl+Alt Museum: cane robot e droni

> **Verificato il:** 2026-11-03 (il giorno prima dell'evento)
> **Ambito di questo file:** cane robot, droni e, di passaggio, il braccio robotico. I simulatori di guida e di volo sono descritti nei file dell'altro agente.
> **Legenda:** ⚠️ = non verificato oppure dedotto.

## TL;DR

- **Nessuna fonte pubblica indica marca o modello** del cane robot o dei droni. Le pagine ufficiali dicono solo "A robotic dog" e "A few drones". Per i droni il sito non mostra nemmeno un'illustrazione.
- **Sul sito ufficiale c'è anche un braccio robotico** ("A robotic arm"), che il brief del team non menziona. Va chiesto allo staff alla kick-off. Il museo lo usava già nei laboratori didattici ("programmare un braccio robotico").
- **Tra gli sponsor c'è "Spazio Robot"** (logo nel repo del sito evento). ⚠️ Non ho trovato informazioni su chi sia, né se abbia fornito lui il cane o i droni. È un'ipotesi plausibile da verificare sul posto.
- L'illustrazione "robot-dog.png" del sito è un line-art generico di quadrupede, simile a Unitree Go2 o a Spot. ⚠️ Non prova nulla sul modello reale: è un disegno stilizzato.
- Il supporto hardware è dichiarato: *"Museum staff handle the hardware side and support builders."*

## Cosa dicono le fonti ufficiali dell'evento

| Fonte | Hardware elencato | Note |
|---|---|---|
| Luma (registrazione) | robotic dog, driving simulator, flight simulator, a few drones | Hosts: Luca Bianchi, Federico Pellegrini, Marco D'Angelo, Beppe Leone, marco pagani |
| pavia.grokbot.it (sito evento) | robotic dog, flight simulator, **robotic arm**, driving simulator, a few drones | "Real access, not a demo behind a rope." |
| Repo del sito `aletheia/grok-bot-hackathon`, file `lib/event.ts` | `id: "robot-dog" \| "driving-sim" \| "flight-sim" \| "robotic-arm" \| "drones"` | I droni non hanno immagine. Il simulatore di volo è descritto come "three-screen flight simulator on a motion platform" (alt text del disegno) |

### Dettagli logistici utili, dal repo e da Luma

- **Indirizzo:** discordante tra le fonti. Luma riporta "Via Riviera, 39". Sito e repo riportano "Via Gragnani, 18" (una PR si intitola "Fix venue address: Via Gragnani, 18"). Entrambe le fonti dicono "200 m dalla stazione di Pavia". ⚠️ Probabilmente è lo stesso complesso (l'ex cotonificio) con due ingressi.
- **Programma:** mer 4/11 alle 09:00 kick-off e **hardware tour**, poi si lavora tutta la notte. Gio 5/11 alle 09:00 talk di Ralph Johnson (SpaceXAI), build fino alle 16:00, valutazione e pitch dalle 16:00 alle 19:00, chiusura alle 21:00.
- **Stack Grok indicato dagli organizzatori:** Grok API (`grok-4.7`, function calling e structured outputs), Grok Voice (speech-to-speech realtime), Grok Imagine, Grok Build, Grok Bot, Cursor.
- **Giuria** (solo nomi): Luca Bianchi, Lorenzo Cerri, Alessandro Rano, Alberto Giusti, Claudio Peroni, Ralph Johnson, Federico Pellegrini.
- **Sponsor:** Radixia, Pavia – Open your mind, SICAM, Riso Scotti, Coherency, SeaVision, Spazio Robot.
- Le "tracks" pubblicate (Research Radar, GitHub Benchmark Arena e una terza) sono **software** e marcate `status: "proposed"`. ⚠️ Non è chiaro come si combinino con il brief hardware ("Pick a piece of hardware, an API, connect it to Grok").

## Cosa si sa del museo (comPVter / Ctrl+Alt Museum)

- È un museo di retro computing gestito dall'associazione no-profit comPVter. Le sezioni sono Computing, Gaming e Objects, su "1.800 metri" e tre padiglioni, in un ex cotonificio.
- **Robotica:** il museo propone "laboratori di robotica in cui pilotare rover" e, per le classi superiori, "programmare un braccio robotico" (CSV Lombardia, open day). Secondo un riassunto di ricerca, il museo punta a diventare un centro di competenza sulla robotica. ⚠️ Non ho letto la fonte primaria di questa affermazione.
- **Simulatore di guida:** citato nell'open day 2022 dentro un progetto di guida sicura.
- **Simulatore di volo:** "un vero e realistico simulatore di volo" al Summer Camp 2025 (Il Ticino).
- **Nessuna fonte** cita un cane robot o droni del museo prima di questo evento. Potrebbero essere arrivati da poco o essere in prestito da uno sponsor. ⚠️
- comPVter: presidente Dino Baldi, segretaria Laura Brandolini (Il Giorno, articolo sull'inaugurazione).
- Il sito compvter.it non era raggiungibile (connessione rifiutata il 2026-11-03).

## Ricerche fatte senza risultato

- "Ctrl+Alt Museum" insieme a cane robot, Unitree o drone: nessun risultato.
- "comPVter" insieme a Unitree o a robot: nessun risultato.
- Post LinkedIn o X di Luca Bianchi o Federico Pellegrini sull'hardware: non trovati (la ricerca web non indicizza bene i post LinkedIn).
- Thread sul forum Cursor dell'evento: solo l'annuncio, senza dettagli hardware.
- Il calendario eventi su ctrlalt.museum viene caricato via JS e non è leggibile.

## Implicazioni pratiche

1. **Prepararsi su più strade.** Le guide `robot-dog.md` e `drones.md` coprono i candidati più probabili. Con budget e uso da museo, per il cane la scelta più probabile è un Unitree Go2 (Air o Pro) ⚠️ (ipotesi), per i droni un DJI/Ryze Tello o Tello EDU ⚠️ (ipotesi: sono i droni didattici indoor più diffusi).
2. **Alla kick-off (mer 09:00) fare subito l'hardware tour** con la checklist di domande in `llm-robot-architecture.md` (sezione "Domande allo staff").
3. **Chiedere del braccio robotico:** potrebbe essere l'hardware meno conteso.

## Fonti

- Luma, Grok Hackathon at the Museum: https://luma.com/spacexai-z1ys
- Sito evento: https://pavia.grokbot.it
- Repo del sito evento (file `lib/event.ts`, `lib/tracks.ts`, `public/assets/hardware/*`, `public/assets/sponsors/spazio-robot.png`): https://github.com/aletheia/grok-bot-hackathon
- PR "Fix venue address: Via Gragnani, 18": https://github.com/aletheia/grok-bot-hackathon/pull/10
- PR #13 (logo della sede, speaker): https://github.com/aletheia/grok-bot-hackathon/pull/13
- Annuncio sul forum Cursor: https://forum.cursor.com/t/new-event-grok-hackathon-at-the-museum/173708
- Ctrl+Alt Museum: https://ctrlalt.museum
- CSV Lombardia, open day del Ctrl+Alt Museum: https://www.csvlombardia.it/pavia/post/open-day-del-ctrlalt-museum-di-compvter-a-pavia/
- Il Ticino, Summer Camp 2025: https://ilticino.it/2025/08/09/un-successo-il-summer-camp-al-ctrlalt-museum-di-pavia/
- Il Giorno, inaugurazione: https://www.ilgiorno.it/pavia/cronaca/ctrl-alt-museo-computer-9fdcf236
- Altre listing: https://allai.events/event/grok-hackathon-at-the-museum, https://hackathonhub.eu/events/grok-hackathon-at-the-museum-pavia-2026
