# Modelli: Claude ↔ Grok

> **Verificato il:** 2026-11-03.
> **Lato Grok:** fonte primaria [../grok-api/models.md](../grok-api/models.md) (docs.x.ai letto il 2026-11-03). In più ho verificato oggi su docs.x.ai la pagina Pricing (sconto Batch, endpoint US +10%) e la pagina Rate Limits.
> **Lato Claude:** platform.claude.com/docs (Pricing, Rate limits, Vision, OpenAI SDK compatibility, Computer use) letto oggi, più il reference ufficiale `claude-api` (snapshot del 2026-10-06) per id, contesto e comportamento di thinking ed effort.
> ⚠️ indica cose non verificate o dedotte da me. Nessuna chiamata è stata fatta contro le API (non avevamo una key xAI).
> Per i concetti dell'API (Messages ↔ Responses, tool, caching, ecc.) vedi [api-platform.md](api-platform.md).

## TL;DR

| Se in Claude useresti… | In Grok usa… | Nota |
|---|---|---|
| **Claude Opus 5.5** (`claude-opus-5-5`) | **`grok-4.7`** | Sono entrambi modelli di punta con reasoning **non disattivabile**: si regola solo l'effort. Grok costa circa la metà in input e un terzo in output, ma ha 500k di contesto invece di 1M. |
| **Claude Sonnet 5.5** (`claude-sonnet-5-5`) | **`grok-4.3`** con `reasoning.effort` `low`/`medium` (default `low`), oppure `grok-4.7` a `low` | `grok-4.3` è il cavallo da tiro: 1M di contesto, $1.25/$2.50, ed è l'**unico** modello che accetta `effort: "none"`. |
| **Claude Haiku 5.5** (`claude-haiku-5-5`) | **`grok-4.3` + `effort: "none"`**, oppure **`grok-4.20-0309-non-reasoning`** | Il prezzo **non** è comparabile: Haiku 5.5 costa $0.10/$0.50, i Grok veloci costano $1.25/$2.50 (12× in input, 5× in output). |
| **Claude Fable 5.1** (`claude-fable-5-1`) | non c'è un equivalente diretto. Per il ragionamento più profondo: `grok-4.7` a `xhigh`; per la ricerca: `grok-4.20-multi-agent-0309` | Fable 5.1 sta un gradino sopra il listino Grok ($10/$50). Per l'hackathon non serve. |
| Opus o Sonnet "per il codice" | **`grok-build-0.1`** | Claude non ha un modello separato per il coding, xAI sì: 256k di contesto, $1/$2, niente Batch. |
| Opus 5.5 **fast mode** (`speed: "fast"`) | ⚠️ non c'è sull'API. "Grok 4.7 Fast" esiste **solo** in Cursor e Grok Build. Sull'API l'alternativa è `service_tier: "priority"` (2×) | Vedi [../grok-api/responses-and-chat.md](../grok-api/responses-and-chat.md) § Altri parametri avanzati. |
| (nessun modello vocale Claude) | **`grok-voice-3.0`** (`grok-voice-latest`) | Speech-to-speech realtime: [../voice/README.md](../voice/README.md). |
| (nessun modello Claude per immagini o video) | `grok-imagine-image-2.0`, `grok-imagine-video-1.5(-lite)` | [../bots-imagine/grok-imagine.md](../bots-imagine/grok-imagine.md). |

**Regola pratica per l'hackathon:** l'agente "pensante" (pianificatore) gira su `grok-4.7` a `low`/`medium`; il loop veloce (dialogo, camera, comandi frequenti) gira su `grok-4.3` + `none`; la voce passa da `grok-voice-3.0`. Il TTFT va misurato dal museo prima di decidere ([../grok-api/gotchas.md](../grok-api/gotchas.md) ha lo script di benchmark).

## Tabella affiancata: prezzi e contesto

Prezzi in USD per 1M token, endpoint globale, tariffa standard.

| Modello | Contesto | Output max | Input | Cache read | Cache write | Output | Long context |
|---|---|---|---|---|---|---|---|
| **Claude Fable 5.1** | 1M | 128K | $10.00 | $0.25 | $12.50 (5m) / $20 (1h) | $50.00 | prezzo pieno su tutto il contesto |
| **Claude Opus 5.5** | 1M | 128K | $4.00 | $0.20 | $5.00 (5m) / $8 (1h) | $20.00 | prezzo pieno su tutto il contesto |
| **Claude Sonnet 5.5** | 1M | 128K | $2.00 | $0.10 | $2.50 (5m) / $4 (1h) | $10.00 | prezzo pieno su tutto il contesto |
| **Claude Haiku 5.5** | 1M | 128K | $0.10 | $0.01 | $0.125 (5m) / $0.20 (1h) | $0.50 | sopra i 100k di prompt: $0.50 / $2.50 |
| **`grok-4.7`** | 500k | "nessun limite", `max_output_tokens` default 128k | $2.00 | $0.50 | **gratis** (cache automatica) | $6.00 | dai 200k di prompt **tutto** costa 2×: $4 / $12 |
| `grok-4.6` | 500k | come 4.7 | $2.00 | $0.50 | gratis | $6.00 | come 4.7 |
| **`grok-4.3`** | 1M | default 128k | $1.25 | $0.20 | gratis | $2.50 | dai 200k: $2.50 / $5 |
| **`grok-4.20-0309-non-reasoning`** | 1M | default 128k | $1.25 | $0.20 | gratis | $2.50 | dai 200k: $2.50 / $5 |
| `grok-4.20-0309-reasoning` | 1M | default 128k | $1.25 | $0.20 | gratis | $2.50 | dai 200k: $2.50 / $5 |
| `grok-4.20-multi-agent-0309` | 1M | default 128k | $1.25 | $0.20 | gratis | $2.50 | dai 200k: $2.50 / $5 |
| **`grok-build-0.1`** | 256k | default 128k | $1.00 | $0.20 | gratis | $2.00 | dai 200k: $2 / $4 |

### Modificatori di prezzo

| Modificatore | Claude | Grok |
|---|---|---|
| **Batch** | -50% su tutti i modelli | **-20%** sui modelli 4.x elencati; `grok-build-0.1` e i modelli Imagine non hanno sconto. Vedi [api-platform.md § Batch](api-platform.md#batch-api) |
| **Inferenza solo USA** | `inference_geo: "us"` → 1.1× (4.6 e successivi) | `https://us.api.x.ai/v1` → 1.1× (solo `grok-4.7` e `grok-4.6`) |
| **Più velocità** | Fast mode su Opus 5.5: $8/$40 (2×), fino a 2.5× token/s in output, solo Claude API | `service_tier: "priority"`: 2×, TTFT e latenza tra token più bassi **sotto carico**. Non accelera il modello |
| **Reasoning token** | il thinking si paga come output | il reasoning si paga come output **e conta nel TPM** |
| **Tool server-side** | web search $10/1k; web fetch gratis (solo token); code execution gratis se usato con web search/fetch, altrimenti a tempo | web search $5/1k, X search $5/1k post + $10/1k profili, code exec $5/1k, collections $2.50/1k, file attachment $5/1k, MCP solo token |

Due conseguenze pratiche:
- Su **Grok non si paga la scrittura in cache** e la cache è automatica. Su Claude la scrittura costa 1.25× ma la lettura costa pochissimo (0.05× su Opus e Sonnet 5.5, 0.025× su Fable 5.1). Con Grok la lettura costa il 25% dell'input su `grok-4.7` e il 16% su `grok-4.3`.
- Su **Grok i token in cache contano nel TPM** del rate limit, su Claude no (per quasi tutti i modelli contano solo i token non in cache).

## Mapping per tier: differenze che contano nel codice

### Opus 5.5 ↔ grok-4.7 (punta)
| | Claude Opus 5.5 | grok-4.7 |
|---|---|---|
| Reasoning | sempre attivo: `thinking: {type: "disabled"}` dà **400** | sempre attivo: il minimo è `effort: "low"` (⚠️ cosa succeda passando `"none"` non è documentato) |
| Controllo | `output_config.effort`: `low`/`medium`/`high`/`xhigh`/`max`, **default `medium`** | `reasoning.effort`: `low`/`medium`/`high`/`xhigh`, **default `high`** |
| Forzare un tool | `tool_choice` `any`/`tool` → **400** su Opus 5.5 | `tool_choice: "required"` o `{type:"function", name}` documentati ✅ |
| Input | testo, immagini (jpeg/png/gif/webp), **PDF nativi** | testo, immagini (**solo jpg/png**). PDF solo tramite Files e attachment search |
| Cutoff | ⚠️ giugno 2026 (dato di sistema del modello, non verificato sui docs) | maggio 2026 |
| Uso nell'hackathon | — (lo usiamo solo dentro Claude Code per sviluppare) | pianificatore robot, vision accurata, agentic con tool server-side |

### Sonnet 5.5 ↔ grok-4.3 (workhorse)
| | Claude Sonnet 5.5 | grok-4.3 |
|---|---|---|
| Spegnere il reasoning | `thinking: {type: "between_tools"}` (`disabled` dà 400) | **`reasoning.effort: "none"`** |
| Effort | `low`..`max`, default `high` | `none`/`low`/`medium`/`high`/`xhigh`, default **`low`** |
| Contesto | 1M | 1M |
| Rate limit (tier base) | Start: 4.000 RPM, 2M ITPM, 400k OTPM | T0: 37 RPS (≈1.776 RPM), 10M TPM |

### Haiku 5.5 ↔ grok-4.3 `none` / grok-4.20-0309-non-reasoning (veloce)
- **Haiku 5.5** ha thinking adattivo attivo di default, `disabled` accettato a effort ≤ `high`, effort di default `medium`.
- Lato Grok ci sono due candidati da confrontare con il benchmark TTFT:
  - `grok-4.3` + `effort: "none"`: stesso modello del workhorse, quindi lo stesso prompt funziona su entrambi i percorsi;
  - `grok-4.20-0309-non-reasoning`: non ragiona per niente, ed è presentato come "industry-leading speed".
- ⚠️ Nessuno dei due provider documenta TTFT o token/s.

### Coding: nessun Claude dedicato ↔ grok-build-0.1
- `grok-build-0.1` (alias del vecchio `grok-code-fast-1`): 256k di contesto, $1/$2, **non** supporta il Batch, in early access.
- Serve se a runtime il progetto deve **generare codice** (per esempio un programma BASIC per il C64 o uno script per il drone). Per il resto `grok-4.7` è più generale.
- Lo sviluppo vero e proprio lo fa Claude Code: è l'ambito degli altri documenti di questa cartella.

### Multi-agent: subagent / Managed Agents multiagent ↔ grok-4.20-multi-agent-0309
- Lato Grok il multi-agent è **un modello**: `effort` sceglie 4 o 16 agenti, e il risultato è un'unica risposta.
- È lento e ha rate limit bassi (T0: 9 RPS): **non adatto al real-time**. Ha senso solo per la ricerca offline.

## Rate limit affiancati (tier di partenza)

| | Claude (Start tier) | Grok (Tier 0, $0 spesi) |
|---|---|---|
| Unità | RPM, ITPM, OTPM per modello (token bucket) | RPS (= RPM/48, minimo 2) e TPM per modello |
| Opus 5.5 ↔ grok-4.7 | 4.000 RPM · 2M ITPM · 400k OTPM | 150 RPS · 50M TPM |
| Sonnet/Haiku 5.5 ↔ grok-4.3 / 4.20 / build | 4.000 RPM · 2M ITPM · 400k OTPM | 37 RPS · 10M TPM |
| Cache e rate limit | i token letti dalla cache **non** contano nell'ITPM | i token in cache **contano** nel TPM |
| Come si sale di tier | automatico in base allo storico (Evaluation → Start → Build → Scale → Custom); spend cap mensile per tier | spesa cumulativa dal 1/1/2026: $50, $250, $1k, $5k. Il tier non scende mai |
| Errore | 429 `rate_limit_error` con `retry-after` | 429 (gRPC `RESOURCE_EXHAUSTED`) |

## Raccomandazioni per ruolo (Grok come cervello a runtime)

| Ruolo nel progetto | Modello Grok | Impostazioni | Perché |
|---|---|---|---|
| **Pianificatore robot** (scompone il compito e sceglie le primitive) | `grok-4.7` | `effort: "low"` (o `medium` se sbaglia), function calling, `parallel_tool_calls: false`, `store: false` | È l'equivalente di Opus: affidabile sui tool, e `low` è indicato dai docs per "latency-sensitive agentic use and simple tool calling" |
| **Loop veloce** (dialogo, comandi ripetuti, reazioni) | `grok-4.3` | `effort: "none"`, prompt e tool statici in testa, `prompt_cache_key` fisso | L'unico modello con reasoning spento e 1M di contesto. In alternativa `grok-4.20-0309-non-reasoning`: si sceglie con il benchmark |
| **Vision dalla camera** (veloce) | `grok-4.3` | `effort: "none"`, `detail: "low"`, JPEG 640–1024 px, `store: false` | Latenza bassa; jpg/png soltanto |
| **Vision accurata** (riconoscere oggetti o testo, contare) | `grok-4.7` | `effort: "low"`, `detail: "high"` | Più qualità, più latenza |
| **Voce** | `grok-voice-3.0` | `server_vad`, tool `function` | Speech-to-speech nativo: [../voice/README.md](../voice/README.md) |
| **Generazione di codice a runtime** | `grok-build-0.1` (oppure `grok-4.7`) | structured output o tool | Modello dedicato al coding |
| **Info live** (web, X) fuori dal percorso caldo | `grok-4.7` o `grok-4.3` + `web_search`/`x_search` | `max_turns: 1-2`, streaming | Ogni tool server-side aggiunge almeno un giro di inferenza |
| **Valutazione offline / dataset per la giuria** | `grok-4.3` via Batch | Batch API | -20%, i batch non contano nei rate limit, risultati entro circa 24 h ⚠️ (troppo lento per l'evento; usare chiamate normali in parallelo) |
| **Ricerca profonda una tantum** | `grok-4.20-multi-agent-0309` | `effort` = 4 o 16 agenti | Solo fuori dal real-time |

## Id da NON usare (trappole quando Claude Code scrive il codice)
- Su xAI: `grok-4-1-fast-*`, `grok-4-fast-*`, `grok-3`, `grok-3-mini`, `grok-2-vision-*`, `grok-code-fast-1` sono ritirati e reindirizzati ([../grok-api/models.md](../grok-api/models.md) § Modelli ritirati). Non esistono `grok-4.7-fast`, `grok-4.7-reasoning` né `grok-4-7` con il trattino.
- Lato Claude: niente suffissi di data sugli id 5.x. Si scrive `claude-opus-5-5`, non `claude-opus-5-5-2026…`.
- Verifica live: `GET https://api.x.ai/v1/models` ↔ `GET https://api.anthropic.com/v1/models`. Il Models API di Claude restituisce anche `max_input_tokens` e `capabilities`; quello di xAI restituisce l'elenco dei modelli abilitati per il team.

## Fonti
- Grok: [../grok-api/models.md](../grok-api/models.md) e le fonti citate lì; https://docs.x.ai/developers/pricing.md (Batch API Pricing, US Regional Endpoint Pricing, letto oggi); https://docs.x.ai/developers/rate-limits.md (letto oggi); https://docs.x.ai/developers/advanced-api-usage/batch-api.md.
- Claude: https://platform.claude.com/docs/en/about-claude/pricing.md (letto oggi: prezzi base, cache, batch, long context, fast mode, data residency, web search e fetch, code execution); https://platform.claude.com/docs/en/api/rate-limits.md (letto oggi); https://platform.claude.com/docs/en/about-claude/models/overview.md; https://platform.claude.com/docs/en/build-with-claude/adaptive-thinking.md e https://platform.claude.com/docs/en/build-with-claude/effort.md (comportamento di thinking ed effort, dal reference `claude-api` del 2026-10-06).
