# Le 10 tracce ufficiali

> Fonte: https://pavia.grokbot.it/tracks, scaricata il **2026-11-03 alle 23:30**, dopo la mail di Luca Bianchi ([raw/luca-bianchi-2026-11-03.md](raw/luca-bianchi-2026-11-03.md)). Copie salvate: [raw/tracks.html](raw/tracks.html) (HTML originale), [raw/tracks.txt](raw/tracks.txt) (testo integrale in inglese), [raw/home.txt](raw/home.txt) (home del sito), [raw/rules.txt](raw/rules.txt) (regole dei team).
> Le tracce sono "proposed": possono essere ritoccate prima dell'evento. Le voci "To be confirmed" dipendono da materiali ancora da raccogliere.
> Risorse pubbliche citate nelle tracce: [track-resources.md](track-resources.md). Bracci robotici: [../hardware/robot-arm.md](../hardware/robot-arm.md).

## Cosa cambia rispetto a quello che sapevamo

- **Le tracce non sono più 3 ma 10, e 6 usano hardware.** Le tracce A–D sono proposte da aziende sponsor, le 01–06 dagli organizzatori.
- **L'hardware vero sono i bracci robotici e il cane.** Ci sono **tre bracci** (arm 1, 2, 3), due camere (camera 1, 2) e il cane robot. **I simulatori di volo e di guida e i droni non compaiono in nessuna traccia**: sulla home restano come "And also".
- **I bracci non hanno gripper.** Montano un utensile stampato con **forchetta, spintore e punta**, e sollevano solo oggetti appoggiati su vassoi fessurati.
- **Bracci e cane si usano in slot da 30 minuti, sempre con lo staff.** Fuori dagli slot si lavora in simulazione o su video registrati.
- **Il cane potrebbe essere un Unitree:** la traccia D cita `unitree_sdk2_python` e `go2_ros2_sdk` "if the dog is a Unitree". Non è confermato.
- **La traccia D cita l'esempio ufficiale xAI `voice-agent-phone` (Twilio), la 04 `voice-agent-web`.** Grok Voice è al centro di entrambe.
- **Le regole comuni sono ora esplicite** (sotto). C'è anche un "common judging rubric" che sarà annunciato a parte e si somma ai criteri di ogni traccia.

## Regole valide per tutte le tracce

1. **Grok** (API, Grok Voice o Bot) **deve essere essenziale** al funzionamento della soluzione, non decorativo.
2. **La demo minima va mostrata entro giovedì alle 16:00, su un caso nuovo scelto dalla giuria.** Secondo la mail serve un "minimum demo video pitch" entro le 16:00, poi c'è la valutazione.
3. **Da consegnare:** una repository con README, i dati usati, **almeno un risultato misurato contro una baseline** e i limiti noti.
4. **Bracci e cane in slot da 30 minuti**, sempre con lo staff; fuori dagli slot simulazione o video. I bracci hanno solo l'utensile stampato (forchetta, spintore, punta) e sollevano solo oggetti su vassoi fessurati.
5. **Solo dati pubblici, sintetici o forniti dalle aziende** per l'evento.

## Panoramica

| # | Traccia | Proposta da | Hardware | Grok usato per | Team indicativi |
|---|---|---|---|---|---|
| **A** | CTRL+F: SEA, *See, Explore, Assist* | SEA Vision | Braccio 2 + camera 2, cane (1–2 slot) | Vision + linguaggio: trovare oggetti descritti, fotografati o fuori posto | 2–3 |
| **B** | B.R.C. Best Rice Company: Autonomous Company | Riso Scotti | Nessuno | Agenti back-office: ordini, DDT, fatture, contestazioni | Illimitati |
| **C** | Labelling from the Model Pack | Cristina Portinaro Cosmetics | Braccio 1 + camera 1 | Vision → specifica strutturata delle etichette, controllo di conformità | 2 a slot alterni |
| **D** | Robot Dog Patrol | Riello | Cane + smartphone come telecamere | Console in linguaggio naturale/voce, decisione, descrizione, allerta anche vocale | 1–2 |
| **01** | Research Radar | Organizzatori | Nessuno | Nomi dei cluster, report con fonti | Illimitati |
| **02** | GitHub Benchmark Arena | Organizzatori | Nessuno | Modello fisso per tutti i tool + giudice con rubrica | Illimitati |
| **03** | Agent Failure Lab | Organizzatori | Nessuno | Diagnosi dei fallimenti degli agenti dalle tracce | Illimitati |
| **04** | Voice Control | Organizzatori | Braccio 3 (senza camera) | Grok Voice realtime con function call sulle skill del braccio | 2 a slot alterni |
| **05** | Robot Skill Passport | Organizzatori | 15 min sul braccio 3 per il test finale | Tutorial da manuali e video, domande di verifica | Illimitati |
| **06** | LabOS | Organizzatori | Nessuno | Grok Bot custode: inventario e prenotazioni in chat | Illimitati |

### Chi usa quale hardware

| Hardware | Tracce | Note |
|---|---|---|
| Braccio 1 + camera 1 | C | 2 team a slot alterni |
| Braccio 2 + camera 2 | A | 2 team a slot alterni |
| Braccio 3 (senza camera) | 04 (dedicato), 05 (15 min per il test finale) | 2 team a slot alterni per la 04 |
| Cane robot | D (1–2 team), A (1–2 slot riservati) | Solo con lo staff presente |
| Simulatori, droni | Nessuna traccia | Sulla home come "And also": fuori dalle tracce ⚠️ |

---

## Tracce proposte da aziende

### A · CTRL+F: SEA, *See, Explore, Assist* (SEA Vision)

- **In una frase:** come si gioca a "Dov'è Wally?" quando Wally cambia ogni volta e si nasconde in una stanza vera?
- **Contesto:** l'oggetto da trovare cambia e si nasconde nello spazio reale. Il sistema deve lavorare con le persone per mappare e identificare oggetti partendo da una foto, da una descrizione o perché qualcosa è "fuori posto".
- **Da costruire:** un sistema di visione, eventualmente con il braccio o il cane, che riceve un oggetto da cercare, lo trova nella scena e lo mostra a una persona.
- **Materiale fornito:** una postazione con tavolo e 20–30 oggetti di uso comune; camera 2; braccio 2 con l'utensile stampato (si usa la punta); 1–2 slot sul cane per cercare nelle sale del museo ⚠️ da confermare. Risorsa pubblica: **YOLO-World**, un detector che trova oggetti da una descrizione testuale (GPL-3.0).
- **Uso di Grok:** capire la richiesta (testo, voce, foto) e confrontarla con quello che vede la camera; spiegare perché un oggetto è fuori posto; chiedere chiarimenti quando la richiesta è ambigua.
- **Demo minima:** due modalità, provate dalla giuria su richieste nuove.
  - *Find this:* data una descrizione o una foto, il sistema evidenzia l'oggetto nell'immagine e il braccio lo indica.
  - *What changed:* data una scena di riferimento, il sistema segnala l'oggetto aggiunto, tolto o spostato.
- **Stretch goal:** il braccio solleva con la forchetta un oggetto su un vassoio; il cane esplora una stanza e torna con la posizione; dialogo vocale; mappa della stanza con gli oggetti trovati.
- **Fuori scope:** addestrare un detector da zero; navigazione autonoma del cane in spazi non preparati.
- **Valutazione:** criteri di SEA Vision: originalità, quanto il team fa suo il tema, demo funzionante ("Amaze us!"). **Misure:** oggetti trovati su 10 richieste nuove della giuria; tempo medio per trovarli; falsi allarmi in modalità *What changed*.
- **Hardware e posti:** braccio 2 con camera 2 per 2 team a slot alterni; 1–2 slot sul cane. Quando l'hardware non è libero si lavora su video registrati della postazione. 2–3 team.
- **Mentor:** Claudio Peroni (mercoledì e giovedì, è **anche in giuria**); Michele Antolini (giovedì).

### B · B.R.C. Best Rice Company: Autonomous Company (Riso Scotti)

- **In una frase:** come può un'azienda alimentare tradizionale gestire ordini, fatture e contestazioni senza lavoro manuale ripetitivo?
- **Contesto:** Riso Scotti vuole ripensare i processi come un'azienda tech. Il punto critico è il dialogo con la grande distribuzione: ordini complessi, DDT, fatture, contestazioni. La produzione entra nella simulazione come eventi, non con robot.
- **Da costruire:** un back office "zero-touch" su dati sintetici, più un concept architetturale di come i dati fluiscono dalla fabbrica all'amministrazione.
- **Materiale fornito:** nessun documento di Riso Scotti. Si parte da risorse pubbliche e il team genera con Grok le mail di contestazione. Risorse: messaggi EDI ORDERS, DESADV e INVOIC di esempio in **EdiFabric/EDIFACT-Examples**; fatture elettroniche italiane con **python-a38**; clausole contrattuali annotate in **CUAD**; una baseline di riconciliazione con file di esempio dei casi tipici di contestazione: **threeway**.
- **Uso di Grok:** agenti che leggono ordini e documenti, verificano le quantità contro il magazzino, preparano la fattura, confrontano ordine, consegna e fattura e propongono come risolvere una contestazione **citando i documenti** su cui si basano.
- **Demo minima:** un processo end-to-end su un ordine nuovo (ricezione, verifica disponibilità, eventi simulati di produzione e spedizione, fattura, riconciliazione); su almeno una contestazione (consegna parziale, prezzo diverso, merce contestata) una proposta di risoluzione con le prove; ogni decisione sopra una soglia passa da una persona.
- **Stretch goal:** controllo qualità visivo del chicco di riso su immagini, ad esempio da GrainSet (licenza da verificare); pianificazione predittiva della produzione; dashboard delle eccezioni.
- **Fuori scope:** collegarsi a un ERP reale; dati reali dei clienti; robot e linee di produzione.
- **Valutazione:** ordini riconciliati correttamente su un test set, **meglio della baseline deterministica**; contestazioni risolte con le prove giuste; casi passati a una persona quando serve; ogni azione tracciabile al documento da cui viene.
- **Hardware e posti:** nessun hardware, team illimitati. **Mentor:** qualcuno di Riso Scotti ⚠️ da confermare. Talk "Riso Scotti meets the Hackathon" mercoledì alle 18:30.

### C · Labelling from the Model Pack (Cristina Portinaro Cosmetics)

- **In una frase:** un robot può imparare a etichettare un prodotto nuovo guardando una sola confezione campione?
- **Contesto:** nei piccoli lotti di cosmetica di lusso le etichette sono stampate su fogli fustellati e applicate a mano, di solito due per confezione: fronte (logo e nome) e retro (INCI e diciture legali). Le posizioni cambiano da prodotto a prodotto (fronte, retro, tappo, fondo) e la confezione campione sul tavolo mostra la combinazione giusta. **Un INCI sbagliato è un problema di conformità**, non solo estetico.
- **Da costruire:** un sistema che legge la confezione campione, ripete il ciclo di lavoro con un braccio e scarta le confezioni non conformi, senza riaddestramento per ogni prodotto.
- **Materiale fornito:** confezioni ed etichette di Cristina Portinaro Cosmetics, oppure flaconi o scatole vuote con etichette fittizie su fogli adesivi pretagliati (una confezione campione per formato ed esempi difettosi: etichetta storta, piegata o sbagliata); camera 1; braccio 1 con l'utensile stampato, con le confezioni su vassoi fessurati. Risorse pubbliche: immagini di etichette storte, piegate e con bolle in **Bottle_defect** (CC BY 4.0); nomi INCI ufficiali nel database UE **CosIng**; dimostrazioni e policy per bracci in **LeRobot**.
- **Uso di Grok:** leggere le foto della confezione campione e trasformarle in una **specifica** (quale etichetta, su quale faccia, dove, con che tolleranza); verificare che il foglio corrisponda al prodotto; giudicare la conformità con una spiegazione.
- **Demo minima, in tre passi:**
  1. *Leggere il campione:* dalle foto della confezione campione Grok produce la specifica in formato strutturato.
  2. *Ciclo:* il braccio sposta una confezione dall'area sinistra all'area di lavoro, sollevandola sul vassoio con la forchetta o spingendola, la fa inquadrare dalla camera, poi la porta a destra se è conforme o la spinge nella scatola degli scarti sul bordo del tavolo se non lo è. Le etichette le applica a mano il team.
  3. *Prodotto nuovo:* la giuria porta una confezione campione mai vista e il sistema produce specifica e controlli senza nuovo addestramento.
- **Stretch goal:** un controllo dopo ogni etichetta, così il retro non si spreca se il fronte è difettoso; accorgersi quando un foglio finisce; imparare il ciclo da un video di un membro del team che etichetta.
- **Fuori scope:** staccare e applicare le etichette con il braccio; prendere confezioni senza vassoio; velocità di produzione.
- **Valutazione:** specifica corretta rispetto al campione; confezioni non conformi scartate e conformi accettate (**l'errore più grave è accettare una confezione sbagliata**); ciclo completato senza intervento; risultato sulla confezione nuova portata dalla giuria.
- **Hardware e posti:** braccio 1 con camera 1, 2 team a slot alterni; fuori dagli slot si lavora su foto e video della postazione. **Mentor:** qualcuno di Cristina Portinaro Cosmetics che decide cosa è conforme ⚠️ da confermare.

### D · Robot Dog Patrol (Riello)

- **In una frase:** un cane robot può diventare la pattuglia che va a controllare quando una telecamera vede qualcosa di strano?
- **Contesto:** un'azienda con un sito di circa 55.000 m² vuole affiancare un cane robot alla videosorveglianza: pattuglie programmabili, controlli mirati quando una telecamera segnala un'anomalia, controllo dalla guardiola, da un PC o da uno smartphone, allerte automatiche alla vigilanza o al custode. Le sale del museo fanno da sito.
- **Da costruire:** il flusso **evento → missione → controllo → allerta**, con una console di controllo e un log di tutto quello che succede.
- **Materiale fornito:** il cane robot del museo, a slot; 2–3 smartphone o laptop usati come telecamere di sorveglianza, più la camera del cane se ce l'ha; una piantina delle sale disponibili; un simulatore del cane, se il modello lo permette ⚠️ da confermare. Risorse pubbliche: gli SDK **unitree_sdk2_python** e **go2_ros2_sdk** se il cane è un Unitree; eventi camera con **Frigate**; la chiamata di allerta con l'esempio xAI **voice-agent-phone** (richiede Twilio).
- **Uso di Grok:** una console in linguaggio naturale, scritta o con Grok Voice ("pattuglia la sala 2"); valutare l'evento della camera e decidere se mandare il cane; descrivere ciò che il cane inquadra; comporre l'allerta, anche come chiamata vocale.
- **Demo minima, in tre passi:**
  1. Una pattuglia programmata tra 3 punti di una sala.
  2. Uno smartphone usato come telecamera rileva un'anomalia inscenata (una persona in un'area vietata, un oggetto abbandonato) e Grok manda il cane sul posto.
  3. Il cane inquadra la scena, Grok la descrive e parte un'allerta verso un numero di test. Ogni evento finisce nel log.

  Senza uno slot sul cane, lo stesso flusso gira con un cane simulato.
- **Stretch goal:** console sullo smartphone; priorità tra più eventi contemporanei; riconoscimento dei falsi allarmi; report di fine turno.
- **Fuori scope:** sirene, deterrenti o altri moduli montati sul cane; riprese del sito reale; chiamate reali alla vigilanza o alla polizia; navigazione autonoma su 55.000 m².
- **Valutazione:** **tempo tra l'evento e l'arrivo del cane**; anomalie inscenate verificate correttamente; falsi allarmi inoltrati; chiarezza dell'allerta; completezza del log.
- **Hardware e posti:** cane robot, **1–2 team**, solo con lo staff presente; 1–2 slot sono riservati alla traccia A. **Mentor:** qualcuno di Riello ⚠️ da confermare.

---

## Tracce aperte (organizzatori)

### 01 · Research Radar, *Mapping the Evolution of Scientific Knowledge*

- **In una frase:** come sta cambiando un campo di ricerca?
- **Contesto:** la ricerca evolve troppo in fretta per seguirla a mano. Le ricerche per keyword danno liste di paper, ma raramente mostrano come emergono nuovi sottotemi, quali approcci convergono e quali risultati hanno davvero cambiato il quadro. Utenti: ricercatori, R&D, investitori deep-tech, team di innovazione.
- **Da costruire:** dato un tema e un intervallo di tempo, un sistema che raccoglie pubblicazioni da fonti aperte, individua i filoni principali, ricostruisce le relazioni tra paper e segnala quali direzioni accelerano o rallentano. Elemento distintivo: la modalità **"What changed?"**, che confronta due finestre temporali e dichiara anche le variazioni dovute alla copertura delle fonti.
- **Materiale fornito:** un tema, un periodo principale (ad esempio 24 mesi), una finestra di confronto, filtri opzionali. Fonti aperte: arXiv, OpenAlex, PubMed/Europe PMC. Risorse: il client Python **pyalex** per OpenAlex (dati CC0, libreria MIT); **BERTopic** per i temi nel tempo.
- **Uso di Grok:** dare nomi leggibili ai cluster; scrivere il report in modo che ogni affermazione abbia una fonte linkata; segnalare l'incertezza. I nomi dei cluster sono ipotesi derivate dai dati, non etichette predefinite.
- **Demo minima:** un dominio e una fonte, 500–1.000 record con una query riproducibile; 5–10 cluster con nomi leggibili, paper di esempio e timeline; un confronto tra due finestre con almeno 3 insight sostenuti da fonti; una mini-dashboard filtrabile per periodo e cluster. Esempio: "reinforcement learning", ultimi 90 giorni contro i 90 precedenti, con cluster come offline RL o RL per agenti e la crescita relativa di ciascuno.
- **Stretch goal:** deduplicazione tra fonti; grafo interattivo delle citazioni; novelty score; alert ricorrenti; confronto tra autori e laboratori; ricerca conversazionale con fonti; temi suggeriti vicini alle aziende (AI per il controllo qualità alimentare, robot che imparano da una dimostrazione).
- **Fuori scope:** estrarre testi completi senza averne i diritti; sostenere che più paper significhino più qualità o impatto.
- **Valutazione:** qualità del retrieval su un campione annotato; coerenza dei cluster valutata a mano; correttezza delle date; quota di affermazioni del report con una fonte valida; utilità dei trend rispetto a una baseline semplice.
- **Hardware e posti:** nessun hardware, team illimitati. Mentor ⚠️ da confermare.

### 02 · GitHub Benchmark Arena, *Continuous Evaluation of Emerging Open-Source Tools*

- **In una frase:** quali tool nuovi funzionano davvero?
- **Contesto:** escono framework e librerie nuovi ogni settimana, con promesse difficili da confrontare. Stelle su GitHub e demo promozionali non misurano affidabilità né prestazioni su carichi reali. Utenti: sviluppatori, platform engineer, team di infrastruttura AI, CTO, ricercatori applicati.
- **Da costruire:** dato un tema software, un sistema che trova repository open source rilevanti, li installa e li esegue in un ambiente controllato, li confronta su task comuni con metriche riproducibili e tiene una classifica nel tempo. Elemento distintivo: rieseguire i confronti quando un repository cambia o ne arriva uno nuovo, mantenendo gli esperimenti confrontabili.
- **Materiale fornito:** una categoria (ad esempio agent harness), una query GitHub, requisiti minimi, una suite di task, un budget di tempo. Risorse: task per agenti con tool e utente simulato in **tau-bench** e **tau2-bench** (MIT). Container isolati con Docker sui laptop dei team.
- **Uso di Grok:** è il **modello fisso** usato da tutti i tool confrontati, così la classifica misura i tool e non i modelli; per le risposte aperte fa da **giudice** con una rubrica calibrata su esempi, affiancato da controlli deterministici.
- **Demo minima:** 3 repository compatibili scelti a mano; 10 task con un adapter comune e una baseline esplicita; almeno 2 run per tool, salvando commit, configurazione e log; una classifica con confronto per metrica e almeno un fallimento riproducibile. Esempio: 3 agent harness sugli stessi 10 task, misurando successo, durata, chiamate, token e costo stimato.
- **Stretch goal:** scoperta automatica di nuovi repository; intervalli di confidenza; regressioni tra versioni; run schedulati con notifiche.
- **Fuori scope:** eseguire codice sconosciuto fuori dai container; usare un giudice LLM come unica fonte di verità senza esempi annotati.
- **Valutazione:** riproducibilità dei run; correttezza degli adapter; copertura e qualità dei task; trasparenza del punteggio; robustezza agli errori di installazione; sicurezza dell'esecuzione.
- **Hardware e posti:** nessun hardware, team illimitati. Mentor ⚠️ da confermare.

### 03 · Agent Failure Lab, *Understanding Why AI Agents Fail*

- **In una frase:** perché un agente fallisce, e come si migliora?
- **Contesto:** quando un agente fallisce, il risultato finale raramente dice se la causa è un piano sbagliato, una ricerca incompleta, un tool usato male o un loop. Analizzare a mano tracce lunghe è lento e non scala. Utenti: team che costruiscono agenti, QA, MLOps, AI product engineering.
- **Da costruire:** un sistema che legge le tracce di esecuzione degli agenti, classifica i fallimenti, individua la causa più plausibile e propone correzioni **verificate con nuovi run**. Elemento distintivo: una correzione conta solo se migliora un test senza regressioni evidenti.
- **Materiale fornito:** un task, un risultato atteso o un test di successo, una traccia strutturata (messaggi, tool call, output, tempi, costi), la configurazione dell'agente. Risorse: tracce annotate con 14 modalità di fallimento in **MAST-Data** (codice in **MAST**); fallimenti attribuiti ad agente e step in **Who&When**. Le tracce prodotte dai team delle tracce A, B, C e D sono casi reali, se le condividono.
- **Uso di Grok:** fa da **diagnosta**: legge la traccia e propone categoria e causa citando gli step, con un livello di confidenza. Accanto ci sono regole deterministiche per timeout, loop e test falliti.
- **Demo minima:** 15–20 tracce, anche sintetiche, con almeno 4 categorie di errore e una ground truth annotata; parser, timeline e classificatore con evidenze per step; 2 correzioni concrete (ad esempio un retry controllato e un controllo obbligatorio prima della risposta finale); un replay su 5 task con successi, regressioni, tempi e costi prima e dopo.
- **Stretch goal:** tracce lette in diretta; raggruppamento dei fallimenti ricorrenti; test di regressione generati; correzioni proposte con approvazione umana; confronto tra agenti e versioni.
- **Categorie di partenza:**
  - *Plan:* incompleto, dipendenze trascurate.
  - *Tool use:* tool sbagliato, parametri sbagliati.
  - *Context:* fonti insufficienti, contesto perso.
  - *Reasoning:* inferenze non supportate, scelte premature.
  - *Execution:* timeout, crash, limiti di risorse.
  - *Verification:* output non controllato, test non eseguiti, successo dichiarato a torto.
- **Fuori scope:** presentare una diagnosi di Grok come prova causale senza un esperimento che la verifichi.
- **Valutazione:** accuratezza della classificazione su tracce annotate; precisione nel trovare lo step rilevante; qualità e verificabilità delle spiegazioni; correzioni efficaci; regressioni introdotte; costo aggiuntivo.
- **Hardware e posti:** nessun hardware, team illimitati. Mentor ⚠️ da confermare.

### 04 · Voice Control

- **In una frase:** si può controllare un braccio robotico parlando, con richieste naturali in italiano?
- **Contesto:** in un laboratorio o su una linea di produzione, chi non programma robot dovrebbe poter richiamare operazioni pronte senza scrivere codice né usare il teach pendant. La voce libera le mani, ma deve essere sicura: conferme prima dei movimenti e uno stop sempre disponibile.
- **Da costruire:** un assistente vocale che capisce la richiesta, sceglie tra **3–5 skill predefinite** del braccio, chiede conferma, esegue e riferisce cosa ha fatto.
- **Materiale fornito:** braccio 3 con l'utensile stampato e vassoi fessurati; skill di base (vai a una posa, indica, solleva il vassoio, appoggia, spingi) **scritte dal team** con il software dei bracci; il microfono del laptop. Risorse pubbliche: l'SDK ufficiale **xai-sdk-python** e l'esempio **voice-agent-web** di un agente vocale nel browser.
- **Uso di Grok:** **Grok Voice in tempo reale**, con function call alle skill del braccio; conferma vocale prima di ogni movimento; riconoscere "stop" in qualsiasi momento.
- **Demo minima:** la giuria detta 5 comandi nuovi, tra cui una richiesta ambigua (il sistema chiede chiarimenti) e uno "stop" che ferma subito il braccio. Ogni comando corrisponde a una skill, con conferma prima del movimento e un report finale.
- **Stretch goal:** sequenze di più skill ("solleva il vassoio e portalo a destra"); **registrare una nuova skill a voce**; più lingue.
- **Fuori scope:** traiettorie libere dettate a voce; movimenti senza conferma.
- **Valutazione:** comandi eseguiti correttamente su 10; **tempo tra la fine della frase e l'inizio del movimento**; gestione dei comandi ambigui o fuori portata; uno stop affidabile in qualsiasi momento.
- **Hardware e posti:** braccio 3 dedicato, senza camera; 2 team a slot alterni. Fuori dagli slot si lavora con un **braccio simulato** che riceve gli stessi comandi. Mentor ⚠️ da confermare.

### 05 · Robot Skill Passport

- **In una frase:** chi non ha mai usato un robot può imparare da un tutorial generato automaticamente, e dimostrarlo?
- **Contesto:** la formazione sui robot si basa su manuali lunghi e su persone che li sanno già usare. Manca un percorso breve, con una verifica che dica se la persona ha davvero imparato.
- **Da costruire:** un generatore di tutorial che, da manuali e video, produce passi brevi con immagini chiave e una checklist verificabile, più un "passaporto" che registra le competenze acquisite da ogni persona.
- **Materiale fornito:** i manuali dei bracci, disponibili online; video delle operazioni di base (accensione, movimento manuale, aggancio del vassoio, arresto di emergenza) registrati dal team durante gli slot. Risorsa pubblica per prototipare prima dei video veri: dataset di dimostrazioni con video in **LeRobot**.
- **Uso di Grok:** leggere manuali e frame dei video; scrivere i passi; generare le domande di verifica e valutare le risposte; segnalare quando un passo del tutorial non ha riscontro nel manuale.
- **Demo minima:** un tutorial per 2 operazioni reali; una persona che non conosce i bracci lo segue davanti alla giuria; la checklist registra cosa ha fatto bene e cosa no; il passaporto mostra le competenze acquisite.
- **Stretch goal:** verifica pratica con lo smartphone (ad esempio: ha premuto l'arresto di emergenza?); tutorial in più lingue; aggiornamenti automatici quando cambia il manuale.
- **Fuori scope:** certificazioni di sicurezza reali; usare il robot senza lo staff.
- **Valutazione:** tempo ed errori della persona con e senza tutorial; nessun passo inventato rispetto al manuale; chiarezza della checklist.
- **Hardware e posti:** niente hardware da costruire; 15 minuti sul braccio 3 per il test finale; team illimitati. Mentor ⚠️ da confermare.

### 06 · LabOS

- **In una frase:** un custode digitale può tenere in ordine un laboratorio di robotica: cosa c'è, dov'è, chi lo usa e quando?
- **Contesto:** nei laboratori condivisi si perde tempo con inventario, prenotazioni delle macchine e regole d'uso. Le informazioni stanno in fogli di calcolo sparsi e nella testa di chi gestisce il laboratorio.
- **Da costruire:** un custode in chat che gestisce inventario, calendario e prenotazioni, applica le regole del laboratorio e tiene lo storico.
- **Materiale fornito:** l'inventario reale dell'hackathon (bracci, cane, camere, gripper) e gli slot delle postazioni come caso reale ⚠️ da confermare. Risorsa pubblica: **eLabFTW**, software open source (AGPL-3.0) con inventario, calendario di prenotazione e API, usabile come base.
- **Uso di Grok:** un **Grok Bot** che prende prenotazioni in linguaggio naturale, controlla conflitti e regole, risponde a domande come "dov'è il gripper a ventosa?", manda promemoria e libera gli slot.
- **Demo minima:** un inventario consultabile; un calendario; prenotare e cancellare in chat; almeno 3 regole applicate (niente sovrapposizioni, slot da 30 minuti, staff presente); uno storico delle operazioni. Il test della giuria include richieste in conflitto.
- **Stretch goal:** diventare **lo strumento che i team usano per prenotare gli slot giovedì mattina**; promemoria automatici; collegamento ai log delle macchine.
- **Fuori scope:** controllo fisico degli accessi; integrazione con sistemi aziendali.
- **Valutazione:** richieste gestite correttamente su un test set, comprese quelle in conflitto; regole mai violate; tempo per completare una prenotazione.
- **Hardware e posti:** nessun hardware, team illimitati. Mentor ⚠️ da confermare.

---

## Agenda aggiornata (home del sito + mail del 3/11)

| Quando | Cosa |
|---|---|
| Mer 09:00 | Check-in e kick-off: giro dell'hardware, formazione team, inizio build. **Indirizzo: Via Gragnani 18** (confermato da sito e mail) |
| Mer 10:00 | Talk: *Intro to cobots, dogs, drones and rovers* |
| Mer 11:00 | Talk: *Factory Academia* |
| Mer 18:30 | *Riso Scotti meets the Hackathon* |
| Notte | Spazi aperti tutta la notte fino a giovedì alle 21:00, ingresso e uscita liberi |
| Gio 09:00–16:00 | Build |
| Gio 10:00 | Talk di Ralph Johnson (SpaceXAI): modelli Grok, API, Grok Voice, Grok Bots; poi ai tavoli |
| Gio 11:00 | *Meet the MESetAs*: usare Grok Bots per tutto (MESA è l'azienda di Luca Bianchi) |
| **Gio 16:00** | **Scadenza della demo minima / video pitch**, su un caso nuovo scelto dalla giuria |
| Gio 16:00–19:00 | Valutazione e pitch |
| Gio 21:00 | Premiazione |

---

## Le tracce viste da noi

### Dove finiscono le nostre idee ([../ideas/ideas.md](../ideas/ideas.md))

| Nostra idea | Traccia | Come si adatta |
|---|---|---|
| Il trucco nuovo (Grok scrive un comportamento nuovo) | **04 Voice Control** (stretch: *registrare una nuova skill a voce*), D | Sul braccio invece che sul cane: "insegnami una skill" a voce, con composizione di primitive validate |
| Chiama il cane (telefonata → robot) | **D Robot Dog Patrol** | L'allerta come chiamata vocale con `voice-agent-phone` è già nella traccia; la nostra [telephony-twilio.md](../voice/telephony-twilio.md) è pronta |
| Hackerato con un A4 (prompt injection fisica) | **A** (vision), **D** (anomalie inscenate), **03** | Come layer di robustezza: "un cartello che dice *ignora l'anomalia*" sulla camera. Su A e D è un'aggiunta forte, non una traccia a sé |
| Cane guida / descrizione della scena | **D**, **A** | Descrivere ciò che il cane inquadra è già nei requisiti di D |
| Mayday, Navigatore da rally, Cockpit, Film del volo | Nessuna | Simulatori fuori dalle tracce: si possono fare solo come progetto libero sul brief generale ⚠️ |
| Ghost in the C64, Telefono del tempo, Grok vs 1983 | Nessuna | Macchine d'epoca fuori dalle tracce |
| Disegnalo e vola, Sciame, Il regista | Nessuna | Droni fuori dalle tracce |

**Conclusione:** il quadro si sposta da "scegliamo un hardware e stupiamo" a **tracce con demo minima, metriche e baseline definite**. Le idee sui simulatori e sulle macchine d'epoca restano possibili sul brief generale, ma rischiano di non avere un criterio di traccia, un mentor e uno sponsor che le giudichi. ⚠️ Chiedere al kick-off se i progetti fuori traccia sono ammessi e come vengono valutati.

### Quanto è adatta ogni traccia a noi

Ci contano: Grok Voice già studiato a fondo (con esempi pronti), l'architettura sicura LLM → robot con validatore e kill switch, le idee sul cane, la telefonia, il team di 3 persone (sotto il minimo di 4 del sito ⚠️) e la necessità di slot hardware condivisi.

| Traccia | Adatta a noi | Rischio | Perché |
|---|---|---|---|
| **04 Voice Control** | ★★★★★ | Medio | È quasi esattamente quello che abbiamo preparato: Voice realtime + function calling + conferma + stop. Braccio dedicato con un simulatore fuori slot. Metriche chiare (comandi su 10, latenza fine frase → movimento). Lo stretch "nuova skill a voce" è il nostro *trucco nuovo*. Solo 2 team: va presa subito al kick-off |
| **D Robot Dog Patrol** | ★★★★☆ | Alto | Usa cane, Voice, telefonia, vision e log: tutto quello che abbiamo documentato. Ma ha 1–2 team, slot del cane condivisi con A e modello del cane non confermato. Metrica chiave: tempo evento → arrivo |
| **A CTRL+F: SEA** | ★★★☆☆ | Medio | La vision di Grok più YOLO-World è fattibile. Il giudice-mentor Claudio Peroni è in giuria. Ci serve il braccio 2 a slot |
| **03 Agent Failure Lab** | ★★★☆☆ | Basso | Senza hardware, team illimitati, molto vicina al nostro lavoro (agenti, tracce, eval). Meno "wow", ma si allinea ai principi "Evidence first" e ai gusti di Luca Bianchi |
| **06 LabOS** | ★★☆☆☆ | Basso | È l'unica che chiede esplicitamente un **Grok Bot**, e SpaceXSI spinge molto i Bot (talk "Using Grok Bots for everything"). Potrebbe diventare lo strumento reale delle prenotazioni di giovedì |
| **C Labelling** | ★★☆☆☆ | Alto | Braccio più vision più conformità: interessante, ma con molto lavoro fisico di setup |
| **02, 01, 05, B** | ★★☆☆☆ | Basso | Software puro o tutorial: lontani da quello che abbiamo preparato |

### Raccomandazione

1. **Prima scelta: 04 Voice Control.** Arrivare alle 9:00 e prenotare subito uno dei 2 posti. Pitch: "voce in italiano → skill validate → conferma → movimento, con stop garantito e misurato", più lo stretch *insegnagli una skill nuova a voce* (il nostro "trucco nuovo"). Docs pronti: [../voice/](../voice/README.md), [../hardware/llm-robot-architecture.md](../hardware/llm-robot-architecture.md), [../hardware/robot-arm.md](../hardware/robot-arm.md).
2. **Alternativa: D Robot Dog Patrol**, se il cane è un Unitree accessibile e c'è posto. Console vocale, Frigate o una camera da smartphone come sensore, Grok che decide e descrive, allerta con chiamata Twilio.
3. **Aggiunta differenziante su entrambe:** una suite di **attacchi avversari** (comandi ambigui, "stop" sussurrato, prompt injection vocale o visiva) con una tabella "prima/dopo", come risultato misurato contro una baseline.
4. **Visibilità SpaceXSI:** un Grok Bot che fa una parte vera del lavoro, ad esempio il report di fine run o il log delle sessioni, come suggerito in [../claude-vs-grok/claude-code-workflow.md](../claude-vs-grok/claude-code-workflow.md).

### Da chiedere al kick-off

- [ ] Con un team da 3 si può partecipare e scegliere una traccia con hardware? Come si assegnano i posti nelle tracce 04, D, A e C (chi prima arriva? estrazione?)
- [ ] Modello dei bracci (arm 1, 2, 3) e "software dei bracci" con cui si scrivono le skill: SDK Python? Simulatore fornito?
- [ ] Modello del cane: è Unitree? Che firmware? Il simulatore esiste?
- [ ] I progetti fuori traccia (simulatori, droni, macchine d'epoca) sono ammessi? Come vengono giudicati?
- [ ] Il "common judging rubric": quando esce? Il video pitch delle 16:00 ha una durata massima?
- [ ] Come si prenotano gli slot da 30 minuti?
