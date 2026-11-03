# Ctrl+Alt Museum: cosa sappiamo dell'hardware (simulatori, macchine d'epoca)

> Verificato il: **2026-11-03** (ricerca web, siti ufficiali e articoli). Ambito: simulatore di volo, simulatore di guida, macchine d'epoca. Il cane robot e i droni sono in file separati scritti da un altro agente.
> Legenda: ✅ = verificato su fonte citata · ⚠️ = non verificato, dedotto o da fonte singola/indiretta.

## TL;DR

- Il sito dell'hackathon (pavia.grokbot.it) elenca: **robotic dog, flight simulator, robotic arm, driving simulator, "a few drones"**. ✅ Nella pagina Luma il braccio robotico non compare. ✅
- Il sito dell'hackathon accompagna le schede con **disegni stilizzati**, non con foto. Gli `alt` delle immagini dicono:
  - volo: *"three-screen flight simulator on a motion platform"*, cioè tre schermi su piattaforma mobile ✅ (è il testo dell'alt; ⚠️ non sappiamo se rappresenta fedelmente l'impianto reale)
  - guida: *"driving simulator with seat and steering wheel"*, cioè sedile e volante ✅ (stesso caveat ⚠️)
- **Nessuna fonte pubblica dice quale software usano i simulatori** (MSFS, X-Plane, Assetto Corsa…). ⚠️ Va chiesto allo staff appena arriviamo.
- Secondo StartupItalia (2026, letto solo attraverso gli snippet di ricerca perché la pagina è dietro Cloudflare) in uno dei padiglioni c'è **"una stanza interamente dedicata a un simulatore di volo"**. ⚠️
- Al Summer Camp 2025 il museo ha fatto provare *"un vero e realistico simulatore di volo"*, presentato da **due studenti di ingegneria spaziale del Politecnico di Milano**. ✅ Quindi potrebbe essere un impianto curato da loro: chiedere chi lo gestisce. ⚠️
- Il simulatore di guida compare almeno dal 2022 nell'offerta per le scuole: *"laboratori di matematica e simulatore di guida (che può essere inserito in un progetto di guida sicura)"*. ✅ Un sommario di ricerca parla di una *"macchina da F1 con simulatore di guida"*, ma **non ho trovato la fonte primaria**. ⚠️
- **Il museo ha già fatto parlare telefoni d'epoca con un LLM**: il progetto **"chattralino"**, cioè *"l'integrazione tra un centralino analogico, telefoni a ghiera e ChatGPT, con un'interfaccia completamente conversazionale"*. ✅ (sito comPVter). StartupItalia aggiunge che *"il Commodore parla grazie a ChatGPT"* e che c'è traduzione vocale, anche in mandarino. ⚠️ (solo snippet)
- StartupItalia citerebbe anche dei **"cyberdog" già presenti, in attesa di certificazione**. ⚠️ (solo snippet; è utile all'agente che segue il cane robot)

## Il museo

| Dato | Valore | Fonte |
|---|---|---|
| Gestore | comPVter APS, attiva dal 2008 | ✅ ctrlalt.museum/compvter |
| Sede storica | ex cotonificio Dionigi Ghisio, **Via Riviera 39**, Pavia | ✅ Il Giorno 2022, Wikipedia |
| Indirizzo indicato per l'hackathon | **Via Gragnani 18**, 27100 Pavia | ✅ pavia.grokbot.it. ⚠️ Non è chiaro se sia un altro ingresso, un altro padiglione o un cambio di sede: verificare prima di partire |
| Pezzi | "oltre 2.000" raccolti (Il Giorno 2022, pagina comPVter); "+1500 oggetti in esposizione" (pagina Il Museo) | ✅ |
| Funzionanti | "il 95%" dopo riparazione (2022) | ✅ Il Giorno |
| Spazio | "+1800 mq", tre padiglioni; il terzo "sarà attivo nel 2026" | ✅ ctrlalt.museum/il-museo |
| Persone citate | Dino Baldi (presidente, 2022; autore di post 2026), Laura Brandolini (segretaria, 2022), Beppe Leone (cofondatore/coordinatore; tra gli host dell'hackathon) | ✅ Il Giorno, Luma; ⚠️ i ruoli attuali vanno ricontrollati |
| Host dell'hackathon | Luca Bianchi, Federico Pellegrini, Marco D'Angelo (+ Beppe Leone e marco pagani su Luma) | ✅ |
| Contatti | info.museum@compvter.it, 0382.477896 | ✅ ctrlalt.museum |

## Macchine d'epoca citate sul sito (sezione Computing, selezione)

Tutte confermate da schede prodotto su ctrlalt.museum ✅. Lo stato di funzionamento **non è indicato** sulle schede ⚠️.

- **Commodore 64 con floppy 1541** (1982)
- **Olivetti Programma 101** (1966 secondo la scheda)
- Olivetti M24, Olivetti L1 M20
- Commodore Amiga 1000, Apple Lisa, Apple Macintosh 128k, Data General MPT100
- Gaming: Vectrex, Intellivision, Atari Pong, Philips Videopac G7000, PS one, Game Boy Pocket, Game & Watch
- Curiosità: nella collezione c'è la scatola di **Microsoft Flight Simulator del 1988** ✅ (ctrlalt.museum/prodotto/flight-simulator-videogame-box-2/). Si presta a uno storytelling "dal Flight Simulator dell'88 al copilota Grok".
- Altri progetti in corso: "Progetto CPV" (una CPU a transistor "a misura d'uomo"), rete LoRa a 868 MHz per Pavia, robot Olivetti Sigma (talk del 2022). ✅

Per il resto della collezione e per l'hardware "moderno" (**Ultimate 64 Elite MK2** con REST API, terminale **Videotel con ESP32**, rete LoRa/Meshtastic) vedi `../event/museum.md`.

## Implicazioni per noi

1. **Software dei simulatori sconosciuto**: prepariamo adattatori per MSFS (SimConnect), X-Plane (Web API/UDP) e un fallback FlightGear per il volo, e per ACC/AC, F1, iRacing, BeamNG ed ETS2 per la guida (vedi `flight-simulator.md` e `driving-simulator.md`). Teniamo il codice dietro un'interfaccia comune (`get_state()`, `set_target()`), così cambiamo backend in 10 minuti.
2. **Piattaforma mobile**: se c'è un motion rig, quasi certamente un software di motion (SimTools, FlyPT Mover, Sim Racing Studio o simili ⚠️) legge già la telemetria. Attenzione ai **conflitti di porta UDP** (vedi i file dei simulatori) e alla **sicurezza**: l'LLM non deve mai comandare la piattaforma.
3. **Chattralino**: è il precedente più vicino al nostro "Grok Voice su telefono d'epoca". Chiedere se possiamo riusarne l'hardware (centralino, interfaccia audio) e sostituire ChatGPT con Grok Voice.
4. **C64 reale**: se l'Ultimate 64 Elite MK2 è in rete, la sua REST API permette lo stesso bridge a mailbox provato in VICE. Altrimenti va chiesto se esistono Kung Fu Flash o SD2IEC; come ultima strada si lavora in VICE (vedi `retro-machines.md`, codice testato).

## Domande da fare allo staff (simulatori e macchine d'epoca)

**Simulatore di volo**
1. Quale software e quale versione (MSFS 2020/2024, X-Plane 11/12 e versione esatta, Prepar3D, FlightGear, DCS)? Gira su un PC Windows dedicato? Possiamo installare Python e add-on?
2. È un motion rig? Che software di motion usa e quali porte/protocolli? Chi lo spegne in emergenza?
3. Periferiche: yoke o cloche, throttle, pedaliere, pannelli autopilota (MobiFlight, Honeycomb, Logitech)? Sono USB HID standard?
4. Rete: possiamo collegare un nostro laptop in LAN al PC del simulatore (SimConnect remoto, X-Plane UDP)? Ci sono firewall?
5. Aerei preferiti e scenari pronti (un aereo con autopilota completo: C172 G1000, A320, 737)?
6. È il simulatore presentato dagli studenti del Politecnico al Summer Camp 2025? Saranno presenti?

**Simulatore di guida**
7. Quale gioco (Assetto Corsa, ACC, AC EVO, iRacing, F1 24/25, BeamNG, rFactor 2/LMU, ETS2, Forza)? Account e licenze attivi?
8. Volante, pedaliera e cambio: marca e modello (Logitech G29/G923, Thrustmaster, Fanatec)? Force feedback?
9. Possiamo usare il cockpit **fuori dal gioco**, come controller USB del nostro PC (per pilotare un drone o il cane)? Possiamo staccare il cavo USB dal PC del simulatore?
10. È la "macchina da F1" citata in alcuni articoli? C'è motion?

**Macchine d'epoca**
11. Quali macchine possiamo **accendere e usare**: C64 e 1541, Olivetti M24 (MS-DOS), altri? Ci sono SD2IEC, Kung Fu Flash, 1541 Ultimate, WiC64 o modem WiFi?
12. Il "chattralino": come è costruito (centralino, interfaccia telefono-PC, ATA/SIP, Asterisk)? Possiamo collegarci? Funziona ancora?
13. Il "Commodore che parla con ChatGPT": su quale hardware e con quale collegamento (seriale, userport, emulatore)?
14. Ci sono telefoni a disco liberi da smontare o collegare (con il loro permesso) e adattatori audio USB?
15. Regole di conservazione: cosa non si può toccare, aprire o alimentare?

## Fonti

- Sito hackathon (hardware, alt delle immagini, indirizzo, persone): https://pavia.grokbot.it
- Evento Luma "Grok Hackathon at the Museum": https://luma.com/spacexai-z1ys
- Museo: https://ctrlalt.museum · https://ctrlalt.museum/il-museo/ · https://ctrlalt.museum/computing/ · https://ctrlalt.museum/gaming/
- comPVter e chattralino: https://ctrlalt.museum/compvter-associazione-di-promozione-sociale/ · https://ctrlalt.museum/compvter/
- Scheda C64: https://ctrlalt.museum/prodotto/commodore-64-with-floppy-disk-drive/
- Scheda Programma 101: https://ctrlalt.museum/prodotto/olivetti-programma-101-first-personal-computer/
- Scatola Flight Simulator 1988: https://ctrlalt.museum/prodotto/flight-simulator-videogame-box-2/
- StartupItalia, "A Pavia i vecchi computer rinascono con ChatGPT" (⚠️ 403/Cloudflare, contenuto letto solo dagli snippet di ricerca): https://startupitalia.eu/startup/pavia-vecchi-computer-rinascono/
- Il Ticino, Summer Camp 2025 (simulatore di volo, studenti PoliMi): https://ilticino.it/2025/08/09/un-successo-il-summer-camp-al-ctrlalt-museum-di-pavia/
- CSV Lombardia, Open day 2022 (simulatore di guida, guida sicura): https://www.csvlombardia.it/pavia/post/open-day-del-ctrlalt-museum-di-compvter-a-pavia/
- Il Giorno, inaugurazione 2022: https://www.ilgiorno.it/pavia/cronaca/ctrl-alt-museo-computer-9fdcf236
- Valoroso.it ("driving simulators, 3D printers, robots"): https://valoroso.it/en/ctrl-alt-museum
- Wikipedia: https://it.wikipedia.org/wiki/Ctrl+Alt_Museum
- UniPV News, CoderDojo (droni e robot nei laboratori): https://www.unipv.news/notizie/grande-successo-i-laboratori-coderdojo-pavia-del-27-settembre
