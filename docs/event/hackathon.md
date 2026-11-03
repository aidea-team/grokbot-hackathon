# Grok Hackathon at the Museum: regole, agenda, giuria, speaker

> **Verificato il 2026-11-03** su: pagina Luma (dati JSON della pagina), sito pavia.grokbot.it (home, /rules, /tracks), email Luma ricevute da Federico Romeo, profili LinkedIn pubblici. Il dettaglio del sito (tracce, tool, copy) è in [grokbot-site.md](grokbot-site.md); i dati di calendario in [calendar-and-luma.md](calendar-and-luma.md).
> Legenda: ⚠️ = non verificato o fonti in conflitto.

## TL;DR per il team

1. **Il brief vince sulle tracce.** Brief ufficiale: "scegli un hardware (o un'API), collegalo a Grok (API, Grok Voice o bot framework) e giovedì pomeriggio mostraci qualcosa che non funzionava quando hai cominciato". Le 3 tracce sul sito (Research Radar, GitHub Benchmark Arena, Agent Failure Lab) sono software puro ed etichettate "proposed, may be refined".
2. **Criteri di giudizio: "To be announced"** (sito e Luma, al 3/11). Le uniche indicazioni scritte sono i "principi condivisi" delle tracce: *Reproducibility, Evidence first, Human in the loop, Security by design, Realistic scope*, più un elenco di cose da consegnare (vedi sotto).
3. **Team da 3: niente posto garantito via team.** Il sito chiede team da 4 a 6 e solo i team con almeno 4 persone hanno posto garantito; Luma e la mail di ottobre dicono "Teams of 1 to 4". La mail di Luca Bianchi del 26/10 dice che chi è senza team "can still come: first-come, first-served, up to the venue capacity". **Romeo risulta approvato su Luma (mail dell'8/10).** ⚠️ Per Rios e Puddu non ho trovato la conferma: va controllata.
4. **Arrivare per le 9:00 di mercoledì.** Il calendario Google dice 10:00, ma è sbagliato di un'ora (vedi Logistica).
5. **Speaker confermato: Ralph Johnson (SpaceXAI)**, al posto di Nick Miller citato nella prima versione. Probabilmente è un Field Engineer di SpaceXAI con base in UK (dettagli sotto). È anche **in giuria**.

## Agenda (ora di Roma, CET = UTC+1)

| Quando | Cosa | Note |
|---|---|---|
| Mer 4/11 09:00 | Kick-off, giro dell'hardware, formazione team, inizio build | Luma `start_at` = 08:00Z = 09:00 CET |
| Mer 4/11 18:00 | Ctrl+Alt Ecosystem presentation | Il sito dice "**Invitation only**" |
| Mer notte | Hacking tutta la notte | "The museum stays open to participants" |
| Gio 5/11 09:00 | Talk di Ralph Johnson: modelli Grok, API, Grok Voice, Grok Bots | |
| Gio 5/11 09:00–16:00 | Build, con Ralph ai tavoli | |
| Gio 5/11 16:00–19:00 | Valutazione progetti e pitch | |
| Gio 5/11 21:00 | Closing | La mail Luma dell'8/10 lo chiamava "**Awards ceremony**". Fine evento su Luma: 22:30 |

## Regole e formato

- **Team:** il sito pavia.grokbot.it dice **da 4 a 6**: "a team needs at least 4 people to count as formed", si chiude da solo a 6. Luma e la mail dell'8/10 dicono **da 1 a 4**. ⚠️ Conflitto: per il punteggio conta quello che diranno al kick-off.
- **Lock dei team / fine registrazione:** sito, 2/11 ore 23:59 (Roma). La mail di Luca Bianchi del 26/10 diceva 31/10 ore 23:59. Il lock è comunque già passato.
- **Posti:** massimo 100. I membri di team con almeno 4 persone hanno posto garantito; gli altri prendono i posti rimasti in ordine di registrazione su Luma. Su Luma risultano 149 "going", evento pieno con waitlist.
- **Login al portale:** con l'email usata su Luma (codice OTP a 6 cifre); accedono solo gli ospiti approvati.
- **Laptop obbligatorio. Crediti API forniti** (⚠️ importo non dichiarato).
- **Cosa consegnare** (sezione "What to deliver" della pagina /tracks; ⚠️ scritta per le tracce, ma è l'unica checklist ufficiale):
  - repo GitHub con README e istruzioni per farlo girare
  - **demo da 5 minuti**
  - dataset o fixture di test
  - **risultati quantitativi**
  - descrizione dei limiti
  - breve roadmap
  - "A UI is recommended but not mandatory if a CLI or API can be demonstrated."
- **Spunti dati dagli organizzatori** (mail Luma dell'8/10, ⚠️ assenti dalla pagina attuale):
  - parlare al cane robot e farlo andare da qualche parte
  - passare la telemetria del simulatore di volo a Grok e ottenere un copilota che commenta l'atterraggio (o lo schianto)
  - pianificare la rotta di un drone descrivendola a voce
  - un bot che guida i visitatori nella collezione del museo

  Sono idee "di base": per distinguersi conviene andare oltre (vedi [../ideas/ideas.md](../ideas/ideas.md)).
- **Hardware** (sito): cane robot, simulatore di volo, braccio robotico, simulatore di guida, alcuni droni. Lo staff del museo gestisce l'hardware. Il braccio robotico c'è solo sul sito, non su Luma. ⚠️ Le illustrazioni del sito mostrano un "three-screen flight simulator on a motion platform" e un simulatore di guida "with seat and steering wheel", ma sono disegni stilizzati (testo alt delle immagini): marche e modelli non sono dichiarati.
- **Premi: non dichiarati** da nessuna parte. ⚠️

## Criteri di giudizio

**Ufficiali: "To be announced. We will publish this here and on Luma."** Al 3/11 sera non c'è ancora nulla.

Indizi utili, in ordine di affidabilità:

1. **Principi condivisi delle tracce** (sito): Reproducibility (fonti, versioni, parametri e risultati tracciati); Evidence first (separare misure oggettive, giudizi di un LLM e interpretazioni); Human in the loop; Security by design; Realistic scope ("A robust end-to-end pipeline on a narrow use case is better than a broad but fragile demo").
2. **Il brief:** "show us something that didn't work when you started". Contano la dimostrazione dal vivo e il prima/dopo.
3. **Il profilo di Luca Bianchi** (organizzatore e giurato), dal suo LinkedIn pubblico: insiste su tracciabilità, log immutabili, replay "che mostrano cosa è cambiato e perché", pragmatismo. Coincide con "Evidence first".
4. **Criteri usati in altri hackathon Grok Bot** (community SpaceXSI), per esempio il Grok Bot Community Engineering London Hackathon del 22/10/2026: *Technical execution; How much Grok Bot and Cursor architected it; Use of community context; 10x–20x improvement; Real-world usefulness; Demo quality*. ⚠️ È un altro evento: vale solo come indicazione di cosa piace agli ambassador SpaceXAI, cioè **usare in modo visibile Grok Bot, Grok Build e Cursor** per costruire.

Lettura operativa: una demo live che funziona su hardware vero, con **numeri** (latenza, tasso di successo, prima/dopo), un **log o replay** di cosa ha fatto Grok, un "kill switch" umano dichiarato e le feature SpaceXAI usate e mostrate (Voice, Bot, Imagine, Build).

## Giuria (pavia.grokbot.it/#jury)

Il sito dà solo i nomi; foto vera solo per Bianchi e Johnson, iniziali colorate per gli altri (arancione: Cerri, Rano, Peroni; blu: Giusti, Pellegrini; ⚠️ il significato dei colori non è dichiarato).

| Giurato | Chi è (fonti pubbliche) | Cosa probabilmente apprezza | Affidabilità |
|---|---|---|---|
| **Luca Bianchi** | Organizzatore e host Luma. Pavia. CTIO e architetto in MESA, tech lead di **LIDIA** (piattaforma legal-tech AI in produzione); progetti "Agentic Due Diligence" e "Agentic Disclosure". AWS Serverless Hero (2020), organizza ServerlessDays Milano, Cursor Meetup Milano, OpenClaw Milano; da anni coinvolto in comPVter. Ha scritto di aver fatto girare "nine named agents on Grok Bot". | Architetture agentiche in produzione, tracciabilità, replay, event log, scope realistico, uso serio di Grok Bot | Alta (LinkedIn pubblico, Luma, sito museo) |
| **Federico Pellegrini** | Co-organizzatore e host Luma (username `fedep`, fuso orario Europe/Zurich). | ⚠️ Non determinabile | ⚠️ Profilo LinkedIn non leggibile; nessuna bio trovata |
| **Ralph Johnson** | "SpaceXAI team", speaker. Molto probabilmente è il Ralph Johnson del LinkedIn `ralph-johnson-939572195`: **Field Engineer at SpaceXAI** da circa ottobre 2026, Greater Guildford (UK), oltre 25 anni in pre-sales, ex Snowflake, circa 5 anni in MongoDB. In un post cita "Cursor, Grok Bot" che risolvono "real customer issues"; ha messo like al post "Grok 4.7 is here". | Casi d'uso concreti "da cliente", Grok Bot + Cursor, prodotti SpaceXAI usati bene | ⚠️ Media: l'abbinamento nome-profilo è mio, gli organizzatori non hanno pubblicato link |
| **Lorenzo Cerri** | ⚠️ Probabilmente il manager Energy/Sustainability/HSE di **Riso Scotti**, che è tra i sostenitori dell'evento | Utilità industriale concreta, efficienza, sostenibilità | ⚠️ Bassa (omonimia possibile) |
| **Alessandro Rano** | ⚠️ Nessun risultato. Forse legato a uno sponsor (SICAM, SeaVision, Coherency, Spazio Robot?) | | ⚠️ |
| **Alberto Giusti** | ⚠️ Esiste un Alberto Giusti co-founder e General Partner di P3Ventures (Torino, business angel). Non confermato che sia lui | Se è lui: potenziale di business, modello scalabile | ⚠️ Bassa |
| **Claudio Peroni** | ⚠️ Nessun risultato | | ⚠️ |

**Host Luma non in giuria:**
- **Marco D'Angelo:** founder di Radixia (sponsor), Cloud Ecosystem Open Source, Huawei Open Source, ex Microsoft, organizzatore di conferenze.
- **Beppe Leone:** co-fondatore del Ctrl+Alt Museum e di comPVter.
- **Marco Pagani:** ⚠️ nessuna informazione.

**Sponsor e partner** (sito): organizzato da SpaceXAI e Ctrl+Alt Museum; sostenitori Radixia, Pavia – Open your mind (POYM), SICAM, Riso Scotti, Coherency, SeaVision, Spazio Robot.

## Speaker: Ralph Johnson o Nick Miller?

- **Ralph Johnson è confermato** su pagina Luma, sito (Speaker + Jury) e schedule ("Talk by Ralph Johnson (SpaceXAI)"), al 3/11.
- **Nick Miller** compariva nella mail Luma dell'8/10 ("Nick Miller from the SpaceXAI team on site") e nella descrizione copiata nel calendario Google. È stato sostituito. ⚠️ Nessun profilo pubblico di un Nick Miller in SpaceXAI trovato.
- Il Ralph Johnson più probabile (vedi tabella giuria) è un **Field Engineer**, cioè tecnico pre-sales/customer-facing, non un ricercatore. Il ruolo combacia con il compito dichiarato: aiutare ai tavoli. Ha un passato in MongoDB, dove ha partecipato a hackathon, e Luca Bianchi organizza la community MongoDB/Serverless: possibile contatto comune. ⚠️
- Implicazione: gli argomenti che lo interessano sono quelli del suo talk (modelli, API, Grok Voice, Grok Bots) e i casi "cliente reale". Conviene fargli vedere presto una cosa che usa **Grok Voice + Grok Bot**.

## Logistica

- **Indirizzo: ⚠️ due indirizzi.** Luma e il sito del museo (pagina Contatti) dicono **Via Riviera 39, Pavia**; pavia.grokbot.it dice **Via Gragnani 18, Pavia**. Il museo ha entrambe le sedi: una pagina del museo sul Summer Camp cita "ritiro presso il Ctrl+Alt Museum **Gragnani 18**". Sono vicine e il museo dichiara "5 minuti a piedi dalla stazione". Andare in Via Riviera 39 (indirizzo di Luma) e controllare cartelli e il canale Telegram.
- **Treno:** Milano Rogoredo → Pavia in circa 25–30 min (linea S13 Trenord e regionali/RE). Il museo è a circa 200 m (o 5 min a piedi) dalla stazione. ⚠️ Orari dell'ultimo treno contrastanti tra le fonti (22:39 o 23:39 da Pavia): verificare su app Trenord o ViaggiaTreno, soprattutto per il rientro di giovedì sera dopo le 22:30.
- **Notte:** il museo resta aperto ai partecipanti tra mercoledì e giovedì. ⚠️ Nessuna info su docce, brandine o cibo notturno.
- **Orari nel calendario Google: sbagliati.** L'evento in calendario va dalle 10:00 del 4/11 alle 23:30 del 5/11 (+01:00); Luma va dalle 08:00Z alle 21:30Z, cioè **dalle 09:00 del 4/11 alle 22:30 del 5/11 CET**. Probabile errore di fuso: l'evento è stato importato a ottobre, quando era ancora in vigore l'ora legale.
- **Canale Telegram** per contattare organizzatori e altri builder: `#pavia` su https://t.me/spacexai_italia/231 (dalla mail di Luca Bianchi del 26/10).
- **Biglietto:** pass Luma; è consigliato il check-in con l'app Luma.
- **Orari normali del museo** (per contesto): visite solo sabato e domenica su prenotazione, 9:00–12:30 e 14:00–17:30. Telefono e WhatsApp +39 320 2318485.

## Startup Weekend Milano–Pavia (6–8 novembre)

- Luma: "Startup Weekend Milano–Pavia starts the morning after the closing, Nov 6, and runs through the 8th."
- Eventbrite: "Startup Weekend Pavia 2026" (Activators Pavia), 6–8 novembre 2026 al **Ctrl+Alt Museum**, Via Riviera 39. **Lo stato è "Posticipato"**.
- La home di startupweekendpavia.it mostra già **"Marzo 2027"** (venue CTRL+ALT Museum).
- ⚠️ **Quasi certamente è stato rinviato a marzo 2027**: non contare sul 6–8 novembre senza conferma. Format Techstars, 54 ore, pitch venerdì sera, giuria domenica pomeriggio; il programma in pagina è quello dell'edizione 2025, con premi speciali beSharp "Cloud Project of the Year" ed EHL Innovation Hub "Human centricity".

## Eventi simili precedenti (contesto)

- **Café Cursor / Cursor Meetup Milano** (stesso calendario Luma "SpaceXSI for Milan, Italy", ex "SpaceXAI for Milan"):
  - Cursor Meetup Milano 16/09/2025 (Prima Assicurazioni)
  - Cursor Meetup Milano #02 23/10/2025
  - Cursor Meetup Milano #3 20/01/2026 (Viale Cassala 22)
  - Cafè Cursor Milano 26/02/2026 (Cafezal, Viale Premuda 14; 187 iscritti)
  - Cafè Cursor Milano 01/07/2026 (323 iscritti)

  Pavia è il primo evento del calendario con formato hackathon e hardware.
- **Grok Hackathon Padova** (25/09/2026): serata da 2,5 h, team da 2, track Mobile (Cursor iOS) e Laptop, voto finale; premi $200 di crediti Cursor a ciascun vincitore, $20 a tutti. ⚠️ Vincitori non trovati.
- **Rete globale "SpaceXSI Community" su Luma:** decine di "Grok Bot Meetup / Build Day / Hackathon" a ottobre e novembre 2026 (Tokyo, Boston, Toronto, Londra, Vienna, Seoul…). Tokyo (11/10) era centrata su team di bot Grok Bot che collaborano; Londra (22/10) aveva i criteri citati sopra. Hackathon con hardware nella community Cursor: "Cursor Robotics Hackathon Almaty" (Physical AI, 8/7/2026) e "Cursor Melbourne Hardware Hack" (ESP32, 24/5/2026). ⚠️ Vincitori non pubblicati.
- **SpaceXAI Grokathon 2026** (ufficiale, 12 ore; vincitori annunciati il 13/08/2026):
  - 1° posto **Nova**, decompilatore di binari in C leggibile, provato su una ROM Game Boy e sul runtime della centralina di un'auto del 1995 (team Theo C, Supratik Panuganti, Henry Zhang)
  - finalisti **Signal**, simulazione sociale, e **ThinkVoice**, Grok Voice + sensori cerebrali per scegliere suggerimenti di parlato silenzioso (⚠️ piazzamenti di 2° e 3° da fonti secondarie)

  Lezione: hanno vinto progetti "hardcore" e tecnicamente sorprendenti, uno dei quali usa Grok Voice con hardware. ⚠️ Le regole del Grokathon vietavano hardware ingombrante (robot dog, droni), secondo un estratto di ricerca non verificato direttamente (x.ai risponde 403).

## Fonti

- Luma evento: https://luma.com/spacexai-z1ys (dati letti dal JSON della pagina il 2026-11-03)
- Calendario Luma Milano: https://luma.com/spacexai-milan
- Sito: https://pavia.grokbot.it , https://pavia.grokbot.it/rules , https://pavia.grokbot.it/tracks , https://pavia.grokbot.it/#jury
- Email Luma a Federico Romeo: "Grok Hackathon at the Museum: 5 November, Pavia" (8/10/2026), "Registrazione approvata…" (8/10/2026), "Build your dream team for Grok Bot Hackathon Pavia" (Luca Bianchi, 26/10/2026), "…inizia domani" (3/11/2026)
- Luca Bianchi LinkedIn: https://it.linkedin.com/in/lucabianchipavia ; WeAreDevelopers: https://www.wearedevelopers.com/@luca-bianchi
- Ralph Johnson LinkedIn (probabile): https://uk.linkedin.com/in/ralph-johnson-939572195
- Lorenzo Cerri (Riso Scotti): https://www.linkedin.com/in/lorenzo-cerri-6822781a/ , https://www.esg360.it/energy-transformation/riso-scotti-la-strada-dellefficientamento-passa-dalla-concretezza/
- Alberto Giusti (P3Ventures, ⚠️ omonimia): https://www.economyup.it/giornalista/alberto-giusti/
- Museo, contatti e indirizzo: https://ctrlalt.museum/contatti/ ; Summer Camp (indirizzo Gragnani 18): https://ctrlalt.museum/visita-museo/summer-camp/
- Trenord S13: https://www.trenord.it/en/routes-and-timetables/journey/our-lines/pavia-milano-passante-milano-bovisa-s13-line
- Startup Weekend Pavia: https://startupweekendpavia.it , https://www.eventbrite.it/e/biglietti-startup-weekend-pavia-2026-1996099951689
- Grok Hackathon Padova: https://luma.com/cursor-v5ch ; Grok Bot Tokyo: https://luma.com/grokbot-hackathon-tokyo ; Grok Bot London Community Engineering: https://luma.com/eveur09a ; Cursor Robotics Almaty: https://luma.com/cursor-s3t1 ; Melbourne Hardware Hack: https://luma.com/qf7urg29
- Grokathon 2026: https://runtimewire.com/article/spacexai-grokathon-nova-binary-decompiler , https://digg.com/tech/ul7ogqrl
