# Ctrl+Alt Museum / comPVter

> **Verificato il 2026-11-03** su ctrlalt.museum (pagine istituzionali, catalogo oggetti, blog ed eventi tramite le API WordPress pubbliche del sito), valoroso.it e sito dell'hackathon. ⚠️ = non verificato.

## In breve

- **Cos'è:** museo di retrocomputing a Pavia, gestito da **comPVter**, associazione culturale (APS) attiva dal 2008. Il 1/4/2026 ha festeggiato 18 anni. comPVter ha raccolto oltre 2.000 pezzi.
- **Fondatori del museo:** Dino Baldi, Alessio Carmine Scipione, **Beppe Leone** (Beppe Leone è anche host dell'hackathon su Luma).
- **Dove:** Via Riviera 39, 27100 Pavia, nell'ex cotonificio Dionigi Ghisio (bende per l'esercito fino agli anni '70). Loft industriale con soffitti fino a 12 m. ⚠️ Esiste anche una sede in **Via Gragnani 18**, che il sito dell'hackathon indica come indirizzo; vedi [hackathon.md](hackathon.md#logistica).
- **Numeri dichiarati:** oltre 1.500 oggetti esposti, oltre 1.800 m² su 3 padiglioni (il primo da oltre 650 m²; il terzo "in ristrutturazione, attivo nel 2026"), oltre 4.000 visitatori l'anno.
- **Sezioni:** Computing (retrocomputing), Gaming (retrogaming, molti pezzi funzionanti e provabili), Objects (macchine per scrivere, calcolatrici, fotografia digitale, telefonia).
- **Attività:** CoderDojo Pavia (oltre 30.000 ore di formazione gratuita dichiarate), serate sociali il giovedì, corsi di stampa 3D, summer camp, coworking ed eventi aziendali.
- **Contatti:** ctrlaltmuseum@gmail.com, +39 320 2318485 (anche WhatsApp, 9:30–16:30), 0382 477896, info.museum@compvter.it.

## Pezzi iconici (dal catalogo online)

**Computing:**
- **Olivetti Programma 101** ("first personal computer")
- **Commodore 64** con floppy drive
- **Commodore PET 2001** (1977)
- Commodore Amiga 1000
- Apple Lisa
- Apple Macintosh 128k
- Olivetti L1 M20
- Olivetti M24
- Data General MPT100
- HP Integral PC (1985, Unix portatile)
- Tatung Einstein

**Gaming:**
- Vectrex
- Atari Pong
- Intellivision
- Philips Videopack G7000
- Sony PS one
- Game Boy Pocket
- Game & Watch Mario Bros
- Xbox 360

**Objects:**
- Olivetti Valentine
- Olivetti Divisumma 24
- Flying Fish (calcolatrice meccanica)
- Apple QuickTake 150
- Canon ION RC260
- Kodak Disc 4000
- Nokia SU-1B Digital Pen
- Nokia Communicator 9210
- Palm Tungsten T3
- Motorola Teledrin SIP
- terminale **SIP ADF 258 (Videotel)**

⚠️ **Telefoni a rotella:** il catalogo online non ne mostra. La sezione Objects copre "telefonia e precursori" e il sito invita a donare telefoni d'epoca, ma un apparecchio a rotella specifico non risulta. Chiederlo allo staff.

### Hardware "moderno" utile per noi

- **Ultimate 64 Elite MK2**: scheda madre FPGA che ricostruisce il C64 in hardware (non emulazione), con HDMI e **Wi-Fi/rete**. Il museo ne ha almeno una (post "Suoni di bit", 23/4/2026), insieme a un THEC64 Maxi e a un C64 originale del 1982, più un User Port Adapter MIDI e la configurazione Dual SID.
  - Le schede Ultimate (firmware dalla 3.11) espongono una **REST API HTTP**: per esempio `POST /v1/runners:run_prg` carica ed esegue un PRG inviato in rete.
  - Esiste un MCP server open source per Ultimate 64 (`martijn-devrev/ultimate64mcp`).
  - ⚠️ Non verificato che l'unità del museo abbia la rete attiva, né quale firmware monti.
- **Terminale Videotel SIP ADF 258 con modulo ESP32** (dono di Francesco Sblendorio di Retrocampus, febbraio 2026): via Wi-Fi si collega a BBS (Retrocampus), Televideo RAI, news e Wikipedia. **Precedente diretto di "macchina d'epoca collegata a un servizio moderno" dentro il museo.**
- **Rete LoRaWAN + Meshtastic a 868 MHz** "comPVter – ctrlalt network", presentata il 28/5/2026: messaggi cifrati off-grid, sensori IoT, nodo GNSS RTK onocoy. Potrebbe servire per un'idea "Grok via mesh radio". ⚠️ Stato di copertura attuale non verificato.
- **Progetto CPV:** CPU a 1 byte costruita a transistor discreti (circa 2.500 NPN, 1.000 resistenze, 200 LED, circa 30 PCB) con l'ITIS Cardano. In costruzione a giugno 2026. ⚠️ Non sappiamo se è già esposta.
- **Hardware dell'hackathon** (sito, non dal catalogo): cane robot, simulatore di volo (disegnato su tre schermi e piattaforma mobile), braccio robotico, simulatore di guida (sedile e volante), alcuni droni. valoroso.it conferma che il museo "abbraccia la modernità" con simulatori di guida, stampanti 3D e robot. ⚠️ Marche e modelli non pubblicati: vedi [../ideas/staff-questions.md](../ideas/staff-questions.md).

## Progetti precedenti del museo con AI o LLM

- **Videotel e Retrocampus (feb 2026):** vedi sopra. **Francesco Sblendorio** ha fatto anche **ChatGPT sul Commodore 64 via BBS RetroCampus** (vedi [prior-art](../ideas/prior-art.md#d-llm--commodore-64--computer-depoca)). È un amico del museo: utile come riferimento e come possibile "giudice informale".
- **Serata OpenClaw (12/3/2026)**, guidata da "Alfredo M.": un'AI proattiva 24/7 con personalità, account Telegram o WhatsApp e workflow. È lo stesso tema dei Grok Bot "teammate". Luca Bianchi organizza l'OpenClaw Milano meetup.
- **Workshop "Work smarter with Claude"** (maggio 2026), **"Zona Pavese: Innovazione, AI e Progetto forgIA"** con Assolombarda (27/5/2026) e **LIDIA all'AWS Summit Milano 2026**, pubblicizzato dal museo (LIDIA è la piattaforma di cui Luca Bianchi è tech lead).
- **BirdNET-Pi** (feb 2026): riconoscimento automatico del canto degli uccelli su Raspberry Pi.
- ⚠️ Esiste un articolo di StartupItalia intitolato **"A Pavia i vecchi computer rinascono con ChatGPT. «In questo ex cotonificio oggi si respira il futuro»"**. Non sono riuscito a leggerlo (403): dal titolo, il museo ha già fatto o raccontato almeno un "vecchio computer + ChatGPT". Se scegliamo l'idea C64 o vintage, va letto per non rifare una cosa già vista.

## Implicazioni per noi

- Il pubblico (Beppe Leone e i soci comPVter) apprezza il **ponte tra epoche**: "Suoni di bit: il ponte tra le epoche" è il titolo di una loro serata. Un progetto che fa parlare Grok **attraverso** una macchina del museo (C64 o Ultimate 64, Videotel, P101 come "storia") parla la loro lingua.
- "Macchina d'epoca + LLM" però **non è nuovo**, nemmeno lì dentro (Videotel con ESP32, ChatGPT su BBS per C64). Per differenziarsi serve che Grok **agisca**, per esempio scrivendo ed eseguendo codice BASIC o 6502 in tempo reale sull'Ultimate 64 via REST, invece di limitarsi a chattare in un terminale.

## Fonti

- https://ctrlalt.museum/chi-siamo/ , https://ctrlalt.museum/il-museo/ , https://ctrlalt.museum/compvter/ , https://ctrlalt.museum/contatti/ , https://ctrlalt.museum/ticket/
- Catalogo: https://ctrlalt.museum/computing/ , https://ctrlalt.museum/gaming/ , https://ctrlalt.museum/objects/ , https://ctrlalt.museum/prodotto/olivetti-programma-101-first-personal-computer/ , https://ctrlalt.museum/prodotto/commodore-64-with-floppy-disk-drive/ , https://ctrlalt.museum/prodotto/vintage-computer-commodore-pet-2001-from-1977-2/
- Blog: https://ctrlalt.museum/suoni-di-bit-cronaca-di-una-serata-tra-passato-presente-e-futuro-con-il-c64/ , https://ctrlalt.museum/il-ritorno-del-videotel-un-tuffo-nel-passato-connesso-al-futuro-grazie-a-retrocampus/ , https://ctrlalt.museum/oltre-lo-schermo-la-serata-openclaw-e-il-futuro-delle-ai-vive/ , https://ctrlalt.museum/reti-libere-e-cittadinanza-attiva-compvter-lancia-la-doppia-infrastruttura-a-868-mhz-per-pavia-e-dintorni/ , https://ctrlalt.museum/progetto-cpv-una-cpu-a-misura-duomo-e-a-base-di-transistor-al-ctrlalt-museum/ , https://ctrlalt.museum/18-anni-di-compvter-il-nostro-decollo-verso-lincredibile/
- Eventi: https://ctrlalt.museum/visita-museo/aws-summit-milano-2026-lidia-ctrlalt-museum/ , https://ctrlalt.museum/visita-museo/summer-camp/
- valoroso.it: https://www.valoroso.it/en/Ctrl-Alt-Museum/
- API Ultimate 64: https://1541u-documentation.readthedocs.io/en/master/_sources/api/api_calls.rst.txt ; MCP: https://github.com/martijn-devrev/ultimate64mcp
- StartupItalia (⚠️ non letto): https://startupitalia.eu/startup/pavia-vecchi-computer-rinascono/
