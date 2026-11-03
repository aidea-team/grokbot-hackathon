# Sito evento: pavia.grokbot.it (+ Luma)

> Verificato il **2026-11-03** scaricando le pagine pubbliche `/`, `/tracks`, `/rules`, `/register` di pavia.grokbot.it e la pagina Luma.
> ⚠️ = non verificato o incoerente tra le fonti.

## TL;DR

- **Evento**: "Grok Hackathon at the Museum", **4–5 novembre 2026**, Ctrl+Alt Museum, Pavia. Hosted by "SpaceXAI for Milan, Italy".
- **Brief**: *"Pick a piece of hardware, an API, connect it to Grok (the API, Grok Voice, or the bot framework), and by Thursday afternoon show something that didn't work when you started."*
- **Hardware disponibile**: cane robot, simulatore di volo, braccio robotico, simulatore di guida, qualche drone. Lo staff del museo gestisce l'hardware.
- **Pitch e valutazione**: giovedì 5/11, **16:00–19:00**. Criteri di valutazione: **"To be announced"** (al 2026-11-03 non ancora pubblicati).
- **Consegna** (dalla pagina Tracks): repo GitHub con README e istruzioni, **demo di 5 minuti**, dataset/fixture, risultati quantitativi, limiti, breve roadmap. UI consigliata ma non obbligatoria.
- **API credits provided**; portare il laptop.

## Il dominio grokbot.it

- `grokbot.it` (root) e `www.grokbot.it` **non hanno record A** (DNS su AWS Route 53, nessun sito servito) al 2026-11-03.
- L'unico sottodominio trovato è **`pavia.grokbot.it`**, app Next.js ospitata su Vercel (stesso contenuto di `grok-hackathon-pavia.vercel.app`).
- ⚠️ Non ho trovato altri sottodomini (crt.sh non ha restituito certificati). Possibile che ne esistano senza certificato pubblico indicizzato.
- Nota: il dominio delle email dei Bot è `mail.grokbot.com` (diverso da `grokbot.it`, è un dominio ufficiale del prodotto Grok Bot).

## Programma (Rome time, CET)

| Giorno | Ora | Cosa |
|---|---|---|
| Mer 4/11 | 09:00 | Kick-off, hardware tour, formazione team, inizio build |
| Mer 4/11 | 18:00 | Ctrl+Alt Ecosystem presentation (*invitation only*) |
| Notte | — | Hacking tutta la notte, museo aperto ai partecipanti |
| Gio 5/11 | 09:00 | Talk di **Ralph Johnson (SpaceXAI)**: "Grok models, API, Grok Voice, Grok Bots" |
| Gio 5/11 | 09:00–16:00 | Build, con Ralph ai tavoli |
| Gio 5/11 | 16:00–19:00 | **Valutazione progetti e pitch** |
| Gio 5/11 | 21:00 | Chiusura |

Luma aggiunge: lo **Startup Weekend Milano–Pavia** inizia la mattina dopo (6/11) e prosegue fino all'8/11.

## Cosa si può usare (sezione "You can use" del sito, con i link ufficiali)

| Strumento | Descrizione sul sito | Link |
|---|---|---|
| Grok API | Grok 4.7 per chat, reasoning e codice, function calling e structured outputs | https://docs.x.ai/overview |
| Search and code tools | Web search, X search, code execution, ricerca sui propri documenti | https://docs.x.ai/developers/tools/overview |
| Grok Voice | Agenti speech-to-speech real-time, TTS, STT | https://docs.x.ai/developers/model-capabilities/audio/voice |
| Grok Imagine | Generare/editare immagini e video da testo | https://docs.x.ai/developers/model-capabilities/imagine |
| Grok Build | Coding agent da terminale, usabile anche da script ed editor | https://docs.x.ai/build/overview |
| Grok Bot | "AI teammates with their own computer that work across your apps" | https://x.ai/news/introducing-grok-bot |
| Cursor | Coding agent desktop/terminale, cloud agents paralleli, Grok 4.7 tra i modelli | https://cursor.com/docs |

## Tracks proposte ("Proposed", possono essere rifinite prima dell'evento)

Principio comune: **ogni insight deve essere verificabile**.

1. **Research Radar** — mappare l'evoluzione di un campo scientifico. Input: topic + periodo + finestra di confronto. Output: cluster di topic, timeline, grafo paper–citazioni, sommario dei movimenti recenti. Elemento distintivo: modalità **"What changed?"** fra due finestre temporali. MVP: un dominio, una fonte (arXiv/OpenAlex/PubMed), 500–2.000 record, 5–12 cluster, ≥3 insight con fonti, mini-dashboard. Valutazione indicativa: qualità del retrieval, coerenza cluster, correttezza date, quota di claim con fonte valida.
2. **GitHub Benchmark Arena** — trovare repo open-source su un tema, installarli in sandbox, confrontarli su task comuni con metriche riproducibili e leaderboard storica. MVP: 3 repo, 10–20 task, adapter comune, ≥2 run per tool salvando commit SHA/config/log, leaderboard e ≥1 failure riproducibile. Rischi: mai eseguire repo sconosciuti sull'host; LLM judge da calibrare. Valutazione indicativa: riproducibilità, correttezza adapter, trasparenza scoring, sicurezza.
3. **Agent Failure Lab** — osservare trace di agenti, classificare i fallimenti, ipotizzare la causa, proporre fix verificati con nuovi run e regression benchmark. Tassonomia iniziale: Planning, Tool use, Retrieval/context, Reasoning/decision, Execution, Verification. MVP: 15–30 trace (anche sintetiche) con ≥4 categorie e ground truth, parser + timeline + classificatore, 2 remediation, replay su 5–10 task con metriche before/after.

Principi condivisi: Reproducibility · Evidence first · Human in the loop · Security by design · Realistic scope ("una pipeline end-to-end robusta su un caso stretto batte una demo ampia ma fragile").

**What to deliver** (pagina /tracks):
- Repository GitHub con README e istruzioni di esecuzione
- Demo di 5 minuti
- Dataset o test fixture
- Risultati quantitativi
- Descrizione dei limiti
- Breve roadmap
- UI raccomandata ma non obbligatoria se si dimostra una CLI o un'API

⚠️ Le tracks sono orientate a software/ricerca, mentre il brief generale parla di hardware: non è chiaro se sia obbligatorio scegliere una track. Il sito dice: "Sources, stack and numbers mentioned in the tracks are design suggestions, not rigid requirements." Conviene chiedere al kick-off.

## Giuria (pavia.grokbot.it/#jury)

- Luca Bianchi
- Lorenzo Cerri
- Alessandro Rano
- Alberto Giusti
- Claudio Peroni
- Ralph Johnson (SpaceXAI team)
- Federico Pellegrini

**Evaluation criteria: "To be announced — We will publish this here and on Luma."** (al 2026-11-03). Gli unici criteri disponibili sono quelli *indicativi* per track (vedi sopra).

**Premi**: ⚠️ nessun premio menzionato né sul sito né su Luma.

## Host

- Sito: Luca Bianchi, Federico Pellegrini, Marco D'Angelo.
- Luma: Luca Bianchi, Federico Pellegrini, Marco D'Angelo, Beppe Leone, marco pagani.
- Citazione in homepage (Luca Bianchi): "Some of you were at the Café Cursor evenings in Milano. This one is a bit different."

## Regole team (pagina /rules)

1. Login con la **stessa email usata su Luma**; solo ospiti **approvati** (non waitlist/pending). Codice OTP a 6 cifre via email, niente password.
2. Registra un team (ottieni un codice segreto), unisciti con un codice, o segnati "looking for a team". Registrare un team dà priorità per la conferma.
3. **Team da 4 a 6**: con <4 il team non conta come formato; a 6 si chiude automaticamente.
4. Un solo team per persona; si può uscire prima del lock. Se il creatore esce, subentra il membro entrato per primo.
5. **Lock team: 2 novembre 2026, 23:59 (Rome)** — coincide con la chiusura registrazioni. Dopo nessuno può entrare/uscire/registrarsi.
6. **Posti garantiti** ai membri di team con ≥4 persone; i posti restanti (fino a 100 totali) per ordine di registrazione Luma.
- Codici: 8 caratteri, mai 0, 1, I, O; maiuscole/spazi/trattini ignorati. Il team lead può rigenerare il codice.
- Nessuna email automatica dal portale sul posto: conferme dagli organizzatori (controllare Luma e inbox).

## Info pratiche

- Capienza **100**, registrazione su approvazione. Stato al 2026-11-03: **evento pieno, waitlist aperta** (Luma: 149 "going").
- Laptop obbligatorio. **API credits provided** (⚠️ non specificato quali: presumibilmente crediti xAI API; non è detto che includano accesso a Grok Bot o X API).
- A 200 m dalla stazione di Pavia, ~25 min di treno da Milano Rogoredo.
- Museo: Ctrl+Alt Museum, museo di retro computing gestito da comPVter (nonprofit), https://ctrlalt.museum

## Incoerenze tra sito e Luma ⚠️

| Tema | pavia.grokbot.it | Luma |
|---|---|---|
| Dimensione team | **4–6** | "Teams of **1 to 4**" |
| Indirizzo | **Via Gragnani, 18**, 27100 Pavia | **Via Riviera, 39**, 27100 Pavia |
| Brand | SpaceXAI | SpaceXSI (organizzatore) e SpaceXAI (testo) |

Per il regolamento dei team fa fede il portale (è quello che applica il lock). Per l'indirizzo, verificare su ctrlalt.museum o chiedere agli host.

## Nota sui brand

Le fonti usano due grafie: **SpaceXAI** (sito evento, GitHub `xai-org`, README di Grok Build) e **SpaceXSI** (docs.x.ai, footer x.ai "© 2026 SpaceX Super Intelligence LLC", Luma). Il dominio resta `x.ai` / `api.x.ai` / `console.x.ai`.

## Fonti

- https://pavia.grokbot.it/ (homepage, sezioni brief, hardware, schedule, teams, jury, venue)
- https://pavia.grokbot.it/tracks
- https://pavia.grokbot.it/rules
- https://grok-hackathon-pavia.vercel.app (mirror identico)
- https://luma.com/spacexai-z1ys
- https://ctrlalt.museum
- https://x.ai/news/introducing-grok-bot
