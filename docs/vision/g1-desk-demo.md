# Demo "il G1 va alla scrivania": percezione, loop agentico, dashboard

> **Stato: progetto, nessun codice scritto** (deciso il 2026-11-04). Quello che c'è già è solo [SAM 3 su Roboflow](sam3.md) e gli script di prova in `src/vision/`. Tutto il resto di questa pagina è il piano. Le soglie sono da calibrare, i tempi sono quelli misurati su una foto vera.

## L'idea

Un umanoide (Unitree G1, oggi solo in MuJoCo, vedi `src/g1/`) **cammina fino a una scrivania con un PC**, ci si ferma davanti (potenzialmente si siede) e da lì **muove un altro robot con i comandi WASD**. Sul desktop, in parallelo, una **dashboard** mostra cosa vede il modello: il frame con le maschere di sedia, scrivania e PC, aggiornate ogni pochi secondi.

## La domanda tecnica: serve SAM 3 nel loop?

**No per camminare, sì per la dashboard e per fermarsi con precisione.**

| | Solo immagine nel loop di Grok | Immagine + riga di percezione da SAM 3 |
|---|---|---|
| Camminare verso la scrivania | Basta, a passi piccoli (gira, avanza 0,5 m, riguarda) | Più stabile |
| "A che distanza sono?" | Debole: nel nostro test i box di Grok erano sballati (il "desk" copriva quasi tutto il frame) | Numeri veri dalla maschera |
| Fermarsi davanti al PC | Ad occhio | Soglia sull'area della maschera |
| Costo / latenza | Nessuna aggiunta | Nessuna aggiunta al loop, se SAM 3 gira in parallelo |

Poiché la dashboard richiede comunque SAM 3, **un solo worker serve entrambi**: pubblica alla dashboard e passa al loop una riga di testo. Il loop agentico resta utilizzabile anche senza worker (degrada a "solo immagine"), ed è proprio il confronto che ci dà la baseline.

## Soluzione finale

```
camera G1 ──► ultimo frame ─────────────┐
                 │                      ▼
                 │             ┌─────────────────┐   tool call   ┌───────────┐   ┌────────┐
                 │             │ loop agentico   │──────────────►│ validatore │──►│ robot  │
                 │             │ (Grok, vede il  │               └───────────┘   │ G1/sim │
                 │             │ frame + riga    │◄── riga di percezione          └────────┘
                 │             │ di percezione)  │        ▲
                 │             └─────────────────┘        │
                 ▼                                         │
        worker di percezione (async, ogni ~3-5 s) ─────────┘
        frame → SAM 3 → maschere → ultimo risultato in memoria
                 │
                 └──► websocket ──► dashboard (frame + maschere colorate + etichette, latenza, stato missione)
```

- **Loop agentico:** a ogni passo riceve il frame corrente e l'**ultimo** risultato del worker (non aspetta mai SAM 3). Sceglie una primitiva piccola, passa dal validatore, il robot la esegue.
- **Worker di percezione:** prende l'ultimo frame ogni ~3-5 s, chiama `sam3/concept_segment` con i prompt `desk`, `chair`, `laptop` (o `computer`), tiene l'ultimo risultato in memoria. Una chiamata dura circa 3,8 s totali (1,1 s sul server), quindi **non può stare dentro ogni passo**.
- **Riga di percezione** (proposta di formato, per ogni concetto trovato):
  `desk: x=0.60 area=36% | computer: x=0.70 area=8%`
  `x` = centroide della maschera, 0 = bordo sinistro, 1 = destro (direzione). `area` = % del frame coperta (proxy della distanza: cresce avvicinandosi). I box non ci sono nella risposta di SAM 3: il centroide si calcola dai poligoni.
- **Condizione di arrivo:** il PC è visibile, `x` vicino a 0,5 e `area` sopra una soglia. **La soglia non è misurata**: va calibrata con qualche frame reale o simulato prima di fidarsi.
- **WASD sull'altro robot:** è un tool `drive_other_robot(key)` (w/a/s/d, nient'altro) che manda comandi via API all'altro robot. Il G1 che "preme i tasti" è scena: la policy di locomozione del G1 non sa sedersi né manipolare. Sedersi si salta o si fa come animazione.
- **Dashboard:** pagina web separata dal controllo, collegata in websocket al worker. Mostra il frame con le maschere (il rendering c'è già in `sam3_segment.py`, funzione `render`), le etichette con confidenza, la latenza dell'ultima chiamata e lo stato della missione (camminata / arrivato / WASD). Serve solo a mostrare: non comanda niente.

## Procedimento (ordine di lavoro)

1. **Prova di SAM 3 sul render del G1.** Finora l'abbiamo provato solo su una foto reale: su MuJoCo potrebbe andare peggio. Basta uno screenshot della camera del G1 con una scrivania nella scena.
2. **Worker di percezione** con ultimo-risultato-in-memoria e log JSONL (latenza, istanze, area).
3. **Dashboard** in websocket sopra il worker (si può fare e mostrare prima ancora di collegare il loop).
4. **Integrare la riga di percezione nel loop** dell'agente (oggi il G1 non ha nessuna integrazione con l'agente: va fatta).
5. **Calibrare la soglia di arrivo** e confrontare **solo immagine** contro **immagine + percezione** (baseline richiesta dalla giuria): percentuale di arrivi riusciti, numero di passi, tempo, stop troppo presto o troppo tardi, su N prove nello stesso scenario.
6. **Tool `drive_other_robot`** e scena finale.

## Limiti e cose non verificate

- Soglie di area e di allineamento: da misurare.
- SAM 3 su immagini simulate: non provato.
- Il G1 non sa sedersi né premere tasti; nel simulatore c'è solo locomozione di alto livello.
- Un tempo di 3-5 s per aggiornare la percezione va bene per una scrivania ferma, non per ostacoli che si muovono: per quelli serve il frame nel loop.
- La chiave Roboflow è gratuita e con crediti mensili limitati (vedi [sam3.md](sam3.md)): il worker deve avere un tetto di chiamate.

## Sicurezza

Vale [robot-safety](../hardware/llm-robot-architecture.md): l'LLM chiama solo primitive in whitelist, tra LLM e robot sta un validatore deterministico (oggi **rimosso di proposito, lo riscrive Francesco**: il piano non dipende dalla percezione per essere sicuro), kill switch locale indipendente dall'LLM, prima mock/simulatore. La riga di percezione è solo un suggerimento al modello, mai un comando; `drive_other_robot` accetta solo w/a/s/d con durata fissa, e passa dallo stesso validatore.

## Fonti
- [sam3.md](sam3.md): API, risposta, risultati sulla foto di prova.
- Test con Grok vision su box: `src/vision/detect_test.py`, risultato in `logs/vision/` (locale).
