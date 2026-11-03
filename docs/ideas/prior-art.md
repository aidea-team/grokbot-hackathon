# Prior art per le nostre idee

> **Verificato il 2026-11-03.** Metadati dei paper (titolo, autori, data) presi dall'API di arXiv; progetti e prodotti da pagine web e stampa di settore. Scopo: sapere cosa esiste già e come differenziarci. Le idee citate sono in [ideas.md](ideas.md). ⚠️ = non verificato o ricerca incompleta. "Non trovato" vuol dire che non l'ho trovato io, non che non esista.

## Sintesi: dove c'è spazio

| Idea (ideas.md) | Quanto è "già visto" | Cosa ci differenzia |
|---|---|---|
| [Il cane impara un trucco](ideas.md#trucco) (LLM scrive codice robot live) | **Molto studiato in ricerca** (Code as Policies, ChatGPT for Robotics, VoxPoser, SayTap). Pochissimo **dal vivo su un quadrupede commerciale con un LLM vocale** | Grok 4.7 che **scrive, valida in sandbox ed esegue** una skill nuova a voce, la salva in una libreria e la riusa; numeri di successo e latenza; replay del codice |
| [Mayday: Grok prende i comandi](ideas.md#mayday) | ATC e copiloti AI per MSFS esistono (SayIntentions, BeyondATC). **Un LLM che gestisce un'emergenza e atterra un aereo di linea in un sim consumer: non trovato** ⚠️ | Grok decide e agisce via autopilota (modi AP, flap, carrello) con telemetria in tempo reale; spiega a voce; human override. Rischio: latenza e controllo fine |
| [Abbiamo hackerato il nostro robot con un foglio A4](ideas.md#injection) | **Area calda nel 2025-26** (CHAI, PPIA, RoboPAIR sul Go2, BadRobot). Dimostrato in paper, quasi mai live davanti a un pubblico | Attacco **e difesa** misurati prima e dopo, su hardware del museo e con Grok. Combacia con la traccia "Agent Failure Lab" (diagnosi, replay, fix verificato) |
| [Ghost in the Commodore](ideas.md#c64) / [Grok contro il 1983](ideas.md#scacchi) | ChatGPT su C64 via BBS (Sblendorio, **amico del museo**), LLM offline su cartuccia, llama2.c64 | Grok che **scrive ed esegue** BASIC o 6502 sul C64 vero (Ultimate 64 REST API) e "vede" lo schermo; non solo chat |
| [Pronto, parlo con il 1965?](ideas.md#telefono) / [Chiama il cane](ideas.md#chiama) | **Telefono a rotella + ChatGPT è molto comune** (decine di build maker) | Novità bassa da solo. Va bene come **interfaccia** verso altro (chiamare il cane o il museo), con Grok Voice e la sua soglia VAD per telefonia |
| [Il cane guida per chi non vede](ideas.md#guida) | Ricerca attiva: Binghamton (AAAI-26), Glasgow RoboGuide, SJTU, RDog (CHI'24) | Grok Voice + visione che **narra e dialoga**; c'è rischio etico e di sicurezza se si promette troppo |
| [Sciame da una frase](ideas.md#sciame) / droni a voce | TypeFly (Tello + GPT-4), ChatGPT for Robotics (AirSim + drone vero), Swarm-GPT (coreografie di sciami), CognitiveDrone (VLA) | Rotta o coreografia generata a voce **e verificata** (geofence, simulazione prima del volo) |
| [Il navigatore che legge il futuro](ideas.md#rally) / simulatore di guida | Molta ricerca LLM e guida (LMDrive, DriveLM, GPT-Driver, Talk2Drive) | ⚠️ "Copilota da rally" con note e telemetria: non cercato a fondo |

## (a) LLM che scrivono codice per robot in tempo reale

- **Code as Policies** (Liang, Huang, Xia et al., Google; arXiv 2209.07753, set. 2022). Con pochi esempi, un LLM per codice scrive "policy code" Python componendo le API del robot. Introduce la generazione gerarchica, cioè la definizione ricorsiva delle funzioni mancanti. Blog: "Robots That Write Their Own Code".
- **ChatGPT for Robotics: Design Principles and Model Abilities** (Vemprala, Bonatti, Bucker, Kapoor, Microsoft; arXiv 2306.17582, 2023). ChatGPT genera codice su una libreria di funzioni di alto livello; demo su drone reale e in AirSim; rilasciato PromptCraft-Robotics.
- **VoxPoser** (Huang et al.; arXiv 2307.05973, lug. 2023). L'LLM scrive programmi che compongono mappe 3D di valore e vincoli, poi un pianificatore genera la traiettoria. Manipolazione zero-shot.
- **SayTap: Language to Quadrupedal Locomotion** (Tang, Yu, Tan, Zen, Google; arXiv 2306.07580). Su un **quadrupede**, l'LLM produce schemi di contatto dei piedi come interfaccia verso il controller di locomozione.
- **Gemini Robotics** (Google DeepMind; arXiv 2503.20020, mar. 2025). Modelli VLA end-to-end e Gemini Robotics-ER per il ragionamento incarnato. È un'altra strada: niente generazione di codice.
- **Progetti per Unitree Go2:**
  - `unitree-go2-mcp-server` (lpigeon): l'LLM traduce comandi in istruzioni ROS2
  - write-up WSO2 di un agente vocale sul Jetson del Go2 con API realtime OpenAI e 5 tool
  - guide HackMD per Go2 EDU + OpenAI
  - ⚠️ nessun progetto con **Grok** trovato
- **Differenziazione:** in letteratura ci sono librerie di primitive predefinite e valutazioni offline. Noi possiamo mostrare dal vivo:
  1. richiesta a voce di un "trucco" che non esiste
  2. Grok 4.7 scrive il codice
  3. validazione automatica (limiti di velocità e angoli, dry-run in sim o mock)
  4. esecuzione
  5. skill salvata e richiamabile
  6. log e replay del codice generato, con il tasso di successo su N tentativi

  Qui ci si allinea a "Evidence first" e "Realistic scope".

## (b) Copiloti e ATC AI per flight simulator; LLM che pilota o atterra

- **SayIntentions.AI:**
  - ATC AI in cloud per MSFS, X-Plane e altri; beta pubblica da dicembre 2023
  - piena compatibilità con MSFS 2024 e EFB integrato
  - voci premium in 15 lingue, clonazione della voce, integrazioni SimBrief, Navigraph e ActiveSky
  - **Checklist V2** (set. 2025): un copilota AI che legge, risponde e "flips switches" durante le checklist
  - roadmap di giugno 2026: VFR flight following, "AI flight mentors"
- **BeyondATC:**
  - ATC AI per MSFS, early access da maggio 2024
  - selezione dinamica di pista e SID/STAR in base al vento, oltre 250 voci AI
  - aggiornamento di luglio 2025: integrazione GSX e nuovo sistema di traffico
  - ⚠️ non dichiarano se e quale LLM usano
- **MCP server e SDK:**
  - **simconnect-mcp** (robin24, PyPI): MCP che collega agenti AI a MSFS via SimConnect (lettura e scrittura di SimVar e L-var, eventi, riposizionamento dell'aereo)
  - un secondo MCP per MSFS 2024 con 23 tool, autopilota compreso
  - per X-Plane: **NASA XPlaneConnect** (UDP) e **pyxpudp** (X-Plane 12); ⚠️ nessun MCP X-Plane confermato
- **Aereo controllato in modo autonomo:**
  - **Aurora ALIAS** (DARPA, 2017): braccio robotico più visione artificiale che atterra un 737 in un simulatore usando l'autoland; **non è un LLM**
  - **LLM-Land** (Cai, Wu, Zhou; arXiv 2505.06399, 2025): atterraggio di **droni** "context-aware" con LLM, in Gazebo e ROS
  - "The Large Language Model Pilot" (conferenza a Linköping, 2025): un LLM nel loop decisionale di un UAV simulato
  - ⚠️ **Nessun caso documentato trovato di un LLM che gestisce un'emergenza e atterra un aereo di linea in MSFS o X-Plane.** Possibile spazio di novità. Probabilmente esistono video amatoriali che non ho trovato
- **Differenziazione rispetto a SayIntentions:** loro fanno ATC e copilota "di bordo" (radio, checklist). Noi faremmo Grok **comandante in emergenza**: legge la telemetria, decide (diversione, configurazione), agisce sull'autopilota e spiega a voce con Grok Voice. Pilota umano sempre in override; a fine volo un report con i numeri (scostamento dal glide path, velocità all'atterraggio).

## (c) Prompt injection fisica o visiva contro robot, auto e droni

- **CHAI: Command Hijacking against embodied AI** (Burbano, Ortiz, Sun, Yang et al., UC Santa Cruz e Johns Hopkins; arXiv 2510.00181, 30/9/2025).
  - Testo ingannevole su cartelli nella scena, ottimizzato per dirottare i VLM.
  - Scenari: atterraggio d'emergenza di un drone, guida autonoma, tracking aereo, **veicolo robotico reale**.
  - Risultati riportati: 81,8% contro auto con GPT-4o in simulazione, fino al 95,5% sul tracking con droni, oltre l'87% sul robot reale (dati degli autori).
  - Ripreso da Schneier ("Prompt Injection Via Road Signs", feb. 2026).
- **Physical Prompt Injection Attacks on Large Vision-Language Models (PPIA)** (Ling, Hu, Liu, Han et al.; arXiv 2601.17383, 24/1/2026). Attacco black-box e indipendente dalla domanda dell'utente: istruzioni tipografiche **stampate** nella scena fisica, senza accesso al modello né all'input testuale.
- **When Prompts Control Robots: Prompt Injection Attacks in Multi-Agent Robotic Systems** (Nagaraja, Bagari, Bahsi; arXiv 2608.00747, 1/8/2026). Iniezione indiretta tramite testo nell'ambiente (avviso sul bancone, cartello sul muro) e contaminazione tra agenti.
- **Jailbreaking LLM-Controlled Robots / RoboPAIR** (Robey, Ravichandran, Kumar, Hassani, UPenn; arXiv 2410.13691, ott. 2024). Jailbreak automatico; **primo jailbreak di un robot commerciale: Unitree Go2** (GPT-3.5, black-box via testo), più Clearpath Jackal e NVIDIA Dolphins. Successi vicini al 100%. **Se il cane del museo è un Go2 il parallelo è diretto.**
- **BadRobot: Jailbreaking Embodied LLM Agents in the Physical World** (Zhang et al.; arXiv 2407.20242, 2024).
- **Differenziazione:** i paper mostrano l'attacco offline. Noi possiamo mostrare dal vivo, sul robot del museo con Grok:
  1. il foglio A4 che dirotta il comportamento
  2. una difesa: separazione tra canali "istruzione" e "percezione", rilevazione del testo nella scena, policy di conferma umana, Grok Bot con approvazioni
  3. la ripetizione dell'attacco, con il tasso di successo prima e dopo su N prove

  È la traccia "Agent Failure Lab" incarnata e rispetta "Security by design". ⚠️ Serve il consenso del museo: niente danni all'hardware, attacco confinato.

## (d) LLM + Commodore 64 / computer d'epoca

- **ChatGPT su C64 via BBS RetroCampus** (Francesco Sblendorio): un computer ponte tra i client BBS e ChatGPT; riservato ai Patreon. Lo stesso Sblendorio ha dato al museo il modulo ESP32 per il Videotel (vedi [../event/museum.md](../event/museum.md)).
- **Cartuccia LLM offline per C64** (Zmysłowski e Jędrzejczyk, Security Fest 2025): LLM locale addestrato su oltre 400 libri sul C64, dialogo via terminale seriale (Novaterm).
- **Llama2.c64:** porting di Llama 2 (minuscolo) sul C64 con 2 MB di REU. Hackaday: "LLM Ported To The C64, Kinda".
- Proposta di un client OpenAI per "C64 Ultimate" sul forum OpenAI. Nei commenti: il TLS su un 8 bit è impraticabile, meglio un terminale seriale verso un ponte.
- **Ultimate 64 REST API** (firmware ≥3.11: `runners:run_prg`, `load_prg`, `run_crt`) e **MCP server Ultimate64** (martijn-devrev) permettono a un agente di caricare ed eseguire programmi sul C64 FPGA in rete. Il museo ha un Ultimate 64 Elite MK2 (⚠️ da verificare che sia in rete).
- **StartupItalia:** "A Pavia i vecchi computer rinascono con ChatGPT" (⚠️ non letto, 403). Il tema è già stato raccontato proprio per questo museo.
- **Differenziazione:** "chattare col C64" è già fatto. Il salto è **Grok che programma il C64**: scrive BASIC o assembler, lo carica via REST, osserva il risultato (cattura video o screenshot dell'Ultimate) e corregge in loop. Oppure gioca contro un software del 1983.

## (e) Droni comandati da linguaggio naturale

- **TypeFly: Flying Drones with Large Language Model** (Chen, Yu, Zhong, Yale; arXiv 2312.14950, dic. 2023 – set. 2024). Drone (DJI Tello) + edge server + GPT-4. L'LLM scrive in un mini-linguaggio, **MiniSpec**, invece di Python, per ridurre costo e latenza: fino a 2x di risparmio e il 62% di tempo di risposta in meno, secondo gli autori.
- **ChatGPT for Robotics** (sopra): drone reale e AirSim.
- **Swarm-GPT** (Jiao, Patel, Khurana et al.; arXiv 2312.01059, dic. 2023): LLM + pianificazione sicura del moto per **coreografie di sciami** di droni da linguaggio naturale.
- **CognitiveDrone** (Lykov et al.; arXiv 2503.01378, mar. 2025): modello VLA per UAV con benchmark di task cognitivi.
- **LLMs to Enhance Multi-task Drone Operations in Simulated Environments** (Feng et al.; arXiv 2601.08405, gen. 2026): CodeT5 fine-tuned + AirSim.
- **LLM-Land** (sopra).
- **Differenziazione:** Grok Voice per comandi a voce in tempo reale e Grok 4.7 che genera un piano. Il piano passa da un **verificatore** (geofence indoor, quota, distanze, simulazione o anteprima 3D) prima del volo; replay e metriche. ⚠️ Lo spazio di volo indoor del museo va chiarito.

## (f) Robot dog come cane guida

- **Binghamton University**, "From Woofs to Words: Towards Intelligent Robotic Guide Dogs with Verbal Communication", **AAAI-26**: cane robot che usa LLM per proporre il percorso prima di partire e narrare l'ambiente durante il tragitto. ⚠️ La valutazione riportata è uno studio simulato; date di pubblicazione contrastanti (apr. o lug. 2026).
- **University of Glasgow, RoboGuide**: quadrupede AI per persone con disabilità visiva in ambienti interni (musei, ospedali), finanziato EPSRC/UKRI.
- **Shanghai Jiao Tong University**: robot guida con LLM e comandi vocali (oltre il 90% di riconoscimento dichiarato).
- **RDog** (CHI '24): sistema di guida quadrupede per navigazione e ostacoli, prima dell'era LLM.
- **Differenziazione:** il tema è "nobile" ma già coperto in ricerca. Su questo è difficile battere i paper in 30 ore. Lo spazio c'è per un **"museum guide dog"**: il cane accompagna un visitatore (anche bendato, con supervisione) tra i pezzi del museo, li descrive con Grok Voice e risponde alle domande. È anche uno degli spunti degli organizzatori ("A bot that walks visitors through the museum collection"). ⚠️ Non promettere di sostituire un cane guida: sicurezza ed etica.

## (g) Telefoni a rotella + LLM

- **Zoltan:** assistente vocale su telefono a rotella dal 2018, poi aggiornato a ChatGPT. Grandstream HT801 (da analogico a VoIP) + Raspberry Pi; risponde con accento tedesco in tema col produttore.
- **Pollux Labs, "Retro Calling":** hotline ChatGPT su telefono a rotella con Raspberry Pi, STT + TTS, cronologia tra le chiamate; codice MIT su Hackster.io.
- **Nico Tangara** (dicembre 2025): telefono a rotella ibrido tra lettore musicale e chat vocale AI (voce ChatGPT, Whisper, Google TTS).
- Varianti con Google Gemini (Raspberry Pi), "Hey Kiri" (Bengaluru, cab e domotica), Agora Rotary Dial Phone (web, Three.js).
- **Differenziazione:** il "telefono + LLM" in sé è un cliché maker. Ha senso se:
  1. il numero composto **seleziona l'epoca o il personaggio** del museo (es. "componi 1965" per parlare con la Programma 101), con contenuti verificati sulla collezione
  2. il telefono è il **telecomando** di un robot ("Chiama il cane")
  3. si sfrutta **Grok Voice** (STT con `vad_threshold` regolabile "utile per telefonia narrowband", voci custom)

  ⚠️ Il museo non mostra telefoni a rotella nel catalogo online: verificare che ce ne sia uno utilizzabile.

## Extra: simulatore di guida + LLM

- In CARLA: **LMDrive** (CVPR 2024, guida end-to-end closed-loop con istruzioni in linguaggio), **DriveLM** (Graph VQA + guida), **GPT-Driver** e **LanguageMPC** (LLM come planner), **SimLingo** (vincitore della CARLA Challenge 2024), **LimSim++** (MLLM come "driver agent").
- Su veicoli reali: **Talk2Drive / Personalized Autonomous Driving with LLMs: Field Experiments** (Cui et al.; arXiv 2312.09397), con comandi verbali su un'auto vera. **CARA**: agente conversazionale in auto basato su ChatGPT, studio al simulatore.
- ⚠️ Copilota "da rally" (note di percorso generate in tempo reale dalla telemetria): non cercato a fondo.

## Fonti

**Paper (arXiv):**
- https://arxiv.org/abs/2209.07753
- https://arxiv.org/abs/2306.17582
- https://arxiv.org/abs/2307.05973
- https://arxiv.org/abs/2306.07580
- https://arxiv.org/abs/2503.20020
- https://arxiv.org/abs/2510.00181
- https://arxiv.org/abs/2601.17383
- https://arxiv.org/abs/2608.00747
- https://arxiv.org/abs/2410.13691
- https://arxiv.org/abs/2407.20242
- https://arxiv.org/abs/2312.14950
- https://arxiv.org/abs/2312.01059
- https://arxiv.org/abs/2503.01378
- https://arxiv.org/abs/2601.08405
- https://arxiv.org/abs/2505.06399
- https://arxiv.org/abs/2312.07488 (LMDrive)
- https://arxiv.org/abs/2503.09594 (SimLingo)
- https://arxiv.org/abs/2312.09397

**Blog e stampa:**
- https://research.google/blog/robots-that-write-their-own-code/
- https://www.microsoft.com/en-us/research/group/autonomous-systems-group-robotics/articles/chatgpt-for-robotics/
- https://www.schneier.com/blog/archives/2026/02/prompt-injection-via-road-signs.html
- https://www.theregister.com/2024/11/16/chatbots_run_robots/

**Flight sim:**
- https://msfsaddons.com/2024/12/04/sayintentions-ai-and-beyondatc-fully-compatible-with-microsoft-flight-simulator-2024/
- https://msfsaddons.com/2025/09/17/sayintentions-ai-brings-ai-driven-checklists-to-msfs-with-checklist-v2/
- https://www.simflight.com/2026/06/13/ai-revolution-in-the-cockpit-sayintentions-ai-unveils-massive-feature-roadmap/
- https://msfsaddons.com/2025/07/15/beyondatc-details-upcoming-features-and-progress-in-july-2025-development-update/
- https://pypi.org/project/simconnect-mcp/
- https://pypi.org/project/pyxpudp/
- https://avweb.com/news/robot-copilot-lands-737/
- https://ecp.ep.liu.se/index.php/ft/article/view/1196

**Robot dog:**
- https://playbooks.com/mcp/lpigeon-unitree-go2
- https://wso2.com/library/blogs/how-we-gave-life-to-an-ai-agent-with-unitree-go2-robot/
- https://www.binghamton.edu/news/story/6168/these-ai-powered-guide-dogs-dont-just-lead-they-talk
- https://www.verdict.co.uk/university-of-glasgows-robot-guide-dog-leads-the-way-in-assistive-technology/
- https://cacm.acm.org/news/guide-dogs-are-expensive-and-scarce-could-robots-do-their-job

**C64:**
- https://www.valoroso.it/en/tag/chatgpt-sul-commodore-64/
- https://theoasisbbs.com/10-things-to-know-about-the-commodore-64-ai-module-from-security-fest-2025/
- https://community.openai.com/t/proposal-developer-integration-openai-api-client-for-the-commodore-64-ultimate/1366869
- https://1541u-documentation.readthedocs.io/en/master/_sources/api/api_calls.rst.txt
- https://github.com/martijn-devrev/ultimate64mcp

**Telefoni a rotella:**
- https://www.hackster.io/news/vintage-rotary-phone-becomes-home-assistant-with-chatgpt-057c566602b7
- https://hackster.io/pollux-labs/retro-calling-chatgpt-on-your-rotary-phone-731b91
- https://www.designboom.com/technology/vintage-rotary-telephone-analog-digital-hybrid-music-player-ai-voice-chat-nico-tangara-12-07-2025
- https://www.pcguide.com/news/raspberry-pi-transforms-vintage-rotary-phone-into-ai-assistant-using-google-gemini/
