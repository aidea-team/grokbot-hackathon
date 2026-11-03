# Modelli Grok disponibili (API)

> **Verificato il:** 2026-11-03 su docs.x.ai (pagine `.md` ufficiali scaricate e lette integralmente).
> I prezzi sono in USD per 1M token. I rate limit indicati sono quelli **Tier 0** (account nuovo, $0 spesi).

## TL;DR

| Uso | Model id da usare | Perché |
|---|---|---|
| Qualità massima, agentic, coding, vision | `grok-4.7` | Modello di punta. Reasoning **non disattivabile** (minimo `low`). |
| **Real-time / robot / bassa latenza** | `grok-4.3` con `reasoning.effort: "none"` | 1M di contesto, prezzo più basso, è l'unico modello documentato che accetta `none`. |
| Real-time senza reasoning (alternativa) | `grok-4.20-0309-non-reasoning` (alias `grok-4.20-non-reasoning`) | `Reasoning: No`, si presenta come modello con "industry-leading speed". |
| Agente di coding via API | `grok-build-0.1` | Modello specifico per il coding (early access), 256k di contesto. |
| Ricerca profonda multi-agente | `grok-4.20-multi-agent-0309` | Lento e con rate limit bassi: **non adatto** al real-time. |

⚠️ **"Grok 4.7" esiste davvero** e il model id è `grok-4.7` (con il punto). **Non esistono** sull'API pubblica varianti `grok-4.7-fast`, `grok-4.7-reasoning` o `grok-4.7-code`:
- **Grok 4.7 Fast** è lo stesso modello su un'infrastruttura più veloce ed è disponibile **solo in Cursor e Grok Build**, non sull'API pubblica xAI (fonte: pagina Grok 4.7 e Pricing).
- La variante "code" corrisponde al modello separato `grok-build-0.1`.
- Il reasoning di `grok-4.7` si regola con `reasoning.effort`, non scegliendo un model id diverso.

## Tabella modelli di testo (prezzi e contesto)

| Model id | Contesto | Input | Input in cache | Output | Input ≥200k | Output ≥200k |
|---|---|---|---|---|---|---|
| `grok-4.7` | 500k | $2.00 | $0.50 | $6.00 | $4.00 | $12.00 |
| `grok-4.6` | 500k | $2.00 | $0.50 | $6.00 | $4.00 | $12.00 |
| `grok-4.5` | 500k | $2.00 | $0.30 | $6.00 | $4.00 | $12.00 |
| `grok-4.3` | 1M | $1.25 | $0.20 | $2.50 | $2.50 | $5.00 |
| `grok-4.20-0309-reasoning` | 1M | $1.25 | $0.20 | $2.50 | $2.50 | $5.00 |
| `grok-4.20-0309-non-reasoning` | 1M | $1.25 | $0.20 | $2.50 | $2.50 | $5.00 |
| `grok-4.20-multi-agent-0309` | 1M | $1.25 | $0.20 | $2.50 | $2.50 | $5.00 |
| `grok-build-0.1` | 256k | $1.00 | $0.20 | $2.00 | $2.00 | $4.00 |

Il "long context pricing" funziona così: quando il prompt raggiunge i 200k token, **tutti** i token della richiesta vengono fatturati alla tariffa più alta.

## Capability per modello (dalle pagine di dettaglio `docs.x.ai/developers/models/<id>`)

| Model id | Modalità | Function calling | Structured outputs | Reasoning | `reasoning.effort` supportati (default) | Batch | Alias documentati |
|---|---|---|---|---|---|---|---|
| `grok-4.7` | text, image → text | Sì | Sì | Sì | `low`, `medium`, `high`, `xhigh` (**high**) | Sì | nessuno elencato |
| `grok-4.6` | text, image → text | Sì | Sì | Sì | `low`, `medium`, `high`, `xhigh` (**high**) | Sì | nessuno elencato |
| `grok-4.5` | text, image → text | Sì | Sì | Sì | `low`, `medium`, `high`, `xhigh`⚠️ (**high**) | Sì | `grok-4.5-latest`, `grok-build-latest` |
| `grok-4.3` | text, image → text | Sì | Sì | Sì | **`none`**, `low`, `medium`, `high`, `xhigh` (**low**) | Sì | `grok-4.3-latest` |
| `grok-4.20-0309-reasoning` | text, image → text | Sì | Sì | Sì | non elencati | Sì | `grok-4.20`, `grok-4.20-reasoning`, `grok-4.20-reasoning-latest`, `grok-4.20-0309`, … |
| `grok-4.20-0309-non-reasoning` | text, image → text | Sì | Sì | **No** | — | Sì | `grok-4.20-non-reasoning`, `grok-4.20-non-reasoning-latest`, … |
| `grok-4.20-multi-agent-0309` | text, image → text | Sì | Sì | Sì | `effort` = numero di agenti (4 o 16) | Sì | `grok-4.20-multi-agent`, `grok-4.20-multi-agent-latest`, … |
| `grok-build-0.1` | text, image → text | Sì | Sì | Sì | non elencati | **No** | `grok-code-fast-1`, `grok-code-fast`, `grok-code-fast-1-0825` |

Note:
- **Tutti** i modelli di testo attuali accettano immagini in input (vision). I dettagli sono in [vision.md](vision.md).
- `grok-4.7`: knowledge cutoff maggio 2026, "nessun limite di output testuale". Il default di `max_output_tokens` sulla Responses API è 128.000.
- ⚠️ `grok-4.5`: la pagina del modello elenca `xhigh` tra gli effort supportati, ma la pagina Reasoning dice che su `grok-4.5` `xhigh` viene trattato come `high`. Le due pagine non sono coerenti.
- ⚠️ La pagina "Grok 4.7" elenca come API solo la "Responses API", ma la documentazione stessa usa `grok-4.7` anche su `/v1/chat/completions` (Streaming, Rate limits, Structured outputs). Chat Completions quindi funziona, ma è **deprecata** (vedi [responses-and-chat.md](responses-and-chat.md)).
- ⚠️ `grok-4.20-0309-reasoning`: la pagina non dice se accetta `reasoning.effort`.

### Pattern degli alias
- `<modelname>` punta all'ultima versione stabile.
- `<modelname>-latest` punta all'ultima versione in assoluto.
- `<modelname>-<date>` punta a una release fissa che non cambia.

## Modelli ritirati (attenzione agli esempi vecchi trovati online)

Dal **15 maggio 2026** questi slug sono ritirati. **Continuano a rispondere**, ma vengono reindirizzati e fatturati con il prezzo del modello di destinazione:

| Slug vecchio | Servito da |
|---|---|
| `grok-4-1-fast-reasoning`, `grok-4-fast-reasoning`, `grok-4-0709` | `grok-4.3` con effort `low` |
| `grok-4-1-fast-non-reasoning`, `grok-4-fast-non-reasoning`, `grok-3` | `grok-4.3` con effort `none` |
| `grok-code-fast-1` | `grok-build-0.1` |
| `grok-imagine-image-pro` → `grok-imagine-image-quality` | dal 2 novembre 2026 → `grok-imagine-image-2.0` |

Se Claude Code propone `grok-4-1-fast`, `grok-3-mini`, `grok-2-vision` o slug simili, vanno sostituiti con quelli della tabella in alto. L'SDK Python 1.21.0 ha ancora questi nomi nei type hint, ma sono obsoleti.

## Rate limit (RPS = richieste/secondo, TPM = token/minuto)

| Model | T0 | T1 ($50) | T2 ($250) | T3 ($1k) | T4 ($5k) |
|---|---|---|---|---|---|
| `grok-4.7` / `4.6` / `4.5` | 150 RPS, 50M TPM | 172 / 53M | 208 / 60M | 312 / 74M | 500 / 100M |
| `grok-4.3`, `grok-4.20-*` (non multi-agent), `grok-build-0.1` | 37 RPS, 10M TPM | 50 / 15M | 75 / 25M | 125 / 45M | 208 / 85M |
| `grok-4.20-multi-agent-0309` | 9 RPS, 2.5M TPM | 12 / 3.7M | 18 / 6.2M | 31 / 11M | 56 / 21M |

- Il tier dipende dalla spesa cumulativa dal 1/1/2026, non scende mai ed è visibile in console → Models.
- RPS = RPM/48, con un minimo di 2. Quando si supera il limite l'API risponde **HTTP 429** (gRPC: `RESOURCE_EXHAUSTED`).
- I token in cache e i reasoning token **contano** nel TPM.

## Regioni ed endpoint

| Endpoint | Base URL | Modelli | Prezzo |
|---|---|---|---|
| Globale | `https://api.x.ai/v1` | tutti | standard |
| US regionale | `https://us.api.x.ai/v1` (xai-sdk: `api_host="us.api.x.ai"`) | solo `grok-4.7` e `grok-4.6` | +10% |

- ⚠️ **Non esiste un endpoint EU documentato.** `grok-4.3` riporta tra le regioni `eu-west-1`, ma non c'è un base URL EU. Per noi in Italia la latenza di rete verso l'endpoint globale **non è documentata**: va misurata sul posto.
- Disponibilità reale per il proprio team: `GET https://api.x.ai/v1/models` oppure `GET /v1/language-models`, oppure la pagina Models della console.

## Altri modelli (fuori dal mio ambito, solo per riferimento)
- Immagini e video (Imagine): `grok-imagine-image-2.0` ($0.04/img), `grok-imagine-image` ($0.02), `grok-imagine-video-1.5` ($0.08/s), `grok-imagine-video-1.5-lite` ($0.02/s), `grok-imagine-video` ($0.05/s).
- Voce: `grok-voice-3.0` (speech-to-speech, $0.08/min, alias `grok-voice-latest`), `grok-voice-2.0` (deprecato), STT `grok-voice-transcribe-2.0`, TTS $15/1M caratteri. Vedi `docs/voice/`.
- ⚠️ Esistono endpoint `/v1/embeddings` e `/v1/embedding-models` nell'OpenAPI e nei docs compare `grok-embedding-small`, ma non ho verificato né modello né prezzo.

## Fonti
- https://docs.x.ai/developers/models.md
- https://docs.x.ai/developers/grok-4-7.md
- https://docs.x.ai/developers/models/grok-4.7.md, …/grok-4.6.md, …/grok-4.5.md, …/grok-4.3.md, …/grok-4.20-0309-reasoning.md, …/grok-4.20-0309-non-reasoning.md, …/grok-4.20-multi-agent-0309.md, …/grok-build-0.1.md
- https://docs.x.ai/developers/pricing.md
- https://docs.x.ai/developers/rate-limits.md
- https://docs.x.ai/developers/model-capabilities/text/reasoning.md
- https://docs.x.ai/developers/migration/may-15-retirement.md
- https://docs.x.ai/developers/advanced-api-usage/regions.md
- https://docs.x.ai/developers/release-notes.md
- https://x.ai/news/grok-4-7 (annuncio del 21 settembre 2026)
