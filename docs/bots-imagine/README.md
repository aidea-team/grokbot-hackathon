# Grok Bots, integrazione X, Grok Imagine, Grok Build — indice e TL;DR

> Ricerca per il **Grok Hackathon at the Museum** (Ctrl+Alt Museum, Pavia, 4–5 novembre 2026). Verificato il **2026-11-03**.
> Fonti principali: docs.x.ai (pagine in formato `.md`), docs.x.com, github.com/xai-org, pavia.grokbot.it, Luma. ⚠️ = non verificato.

## File

| File | Contenuto |
|---|---|
| [grok-bots.md](grok-bots.md) | Grok Bot ("bot framework"): cos'è, computer cloud, skill/routine, **webhook trigger**, MCP custom, esecuzione locale, X, accesso e limiti |
| [x-integration.md](x-integration.md) | Leggere/cercare X con `x_search`, X API pay-per-use (costi, auth, endpoint mentions/search/post/media), xurl, X MCP |
| [grok-imagine.md](grok-imagine.md) | Imagine API: modelli, prezzi, endpoint immagini/video, parametri, async/polling, editing/extension/reference |
| [grok-build.md](grok-build.md) | Grok Build (`grok` CLI): installazione, auth, headless JSON, ACP, MCP, permessi, pattern "robot che si scrive il codice" |
| [code-samples.md](code-samples.md) | 10 snippet Python/JS + curl, controllati su SDK reali (sintassi, firme, dry-run) |
| [../event/grokbot-site.md](../event/grokbot-site.md) | Tutto da pavia.grokbot.it e Luma: programma, tracks, giuria, regole, deliverable, incoerenze |

## TL;DR in 12 punti

1. **"Bot framework" = Grok Bot**, un'**app** (desktop + mobile) di teammate AI su un **computer cloud persistente** (browser, terminale, `/workspace`), lanciata l'11/08/2026, gira nel cloud **Cursor** con login account Cursor. **Non ha un SDK/API per creare o pilotare Bot da codice.**
2. Gli agganci programmatici di Grok Bot sono: **routine con webhook** (`POST` + `Authorization: Bearer <key>`, `200` = run avviato), **MCP server custom** (per URL o comando), **esecuzione di comandi sul laptop** (con approvazione), trigger **email** (`@mail.grokbot.com`), **Slack**, GitHub/Linear/Sentry/PagerDuty, **schedule** (min 5 min). Limiti: 50 routine/Bot, 300 run/h totali.
3. Il Bot **legge X pubblico** senza account; il plugin X (DM, bookmark, timeline) richiede **crediti X API**. Il **tag @bot su X non funziona per account UE** (Italia inclusa).
4. Accesso a Grok Bot: The X Subscription **Premium $30/mese** o superiore, piani Cursor a pagamento, SuperGrok/X Premium+ collegati, o trial. ⚠️ Non confermato che i crediti dell'hackathon includano Grok Bot (altre build night SpaceXAI davano 1 mese di Cursor Pro con Grok Bot).
5. Per **leggere X** la via più veloce è il tool **`x_search`** della Grok API (`/v1/responses`): **$5/1k post** + token, filtri per handle e date, nessun account X.
6. Per **postare/rispondere** serve la **X API v2 pay-per-use** (niente più tier fissi): **$0.015/post**, **$0.20/post con URL**, letture $0.005/post, **proprie menzioni $0.001**; auth **OAuth 1.0a o OAuth 2.0 PKCE** (bearer app-only → 403 sulle write). SDK `xdk` / CLI `xurl`.
7. **Imagine immagini**: `POST /v1/images/generations` | `/edits`, **sincroni**, `grok-imagine-image-2.0` **$0.04/img**, fino a 10 per richiesta, edit fino a 5 immagini, 1k/2k, molte aspect ratio. `grok-imagine-image-quality` **ritirato il 2/11/2026**.
8. **Imagine video**: `POST /v1/videos/generations` → `request_id` → poll `GET /v1/videos/{id}`; **1–15 s**, 480p/720p/1080p, audio con lip-sync; `grok-imagine-video-1.5` $0.08/s, **`-1.5-lite` $0.02/s**, `grok-imagine-video` $0.05/s (unico con **edit** ≤8.7 s ed **extension** +2–10 s). "Up to several minutes" per clip.
9. URL di output **temporanei**: scaricare subito o usare `storage_options.public_url` per un link permanente.
10. **Grok Build** = CLI `grok` open source (Apache-2.0), TUI + **headless** (`grok -p ... --output-format json`) + **ACP**; auth browser o `XAI_API_KEY`; ha `/imagine` e `/imagine-video`; si collega a X via MCP (`api.x.com/mcp`).
11. Per una demo hardware **in tempo reale** conviene la **Grok API diretta** (function calling, `x_search`, Imagine, Voice); Grok Bot è più adatto come **orchestratore asincrono** (riceve eventi via webhook, lavora su app/web, produce bozze/report).
12. Il brand è scritto in due modi: **SpaceXAI** (sito evento, GitHub) e **SpaceXSI** (docs, x.ai, Luma). Gli host tecnici restano `x.ai`, `api.x.ai`, `console.x.ai`.

## Architetture rapide consigliate

```text
A) Hardware → Grok API (real-time)
   sensore/camera ──► script Python ──► Grok 4.7 (function calling) ──► comandi al robot
                                   └─► Imagine (edit foto / clip 5 s) ──► X API POST /2/tweets

B) Hardware → Grok Bot (asincrono, "teammate")
   evento robot ──POST webhook──► routine Grok Bot ──► lavoro su web/app (Gmail, Slack, Sheets, X read)
                                                └─► MCP server tuo (tunnel) ──► azione sul robot

C) Robot che si fa scrivere il codice
   voce/testo ──► `grok -p "<task>" --cwd robot/ --output-format json` ──► test in simulatore ──► esecuzione
```

## Domande da fare al kick-off / a Ralph Johnson (SpaceXAI)

- I "API credits provided" sono **crediti xAI API**? Quanti per team? Includono **Grok Bot** (codice Cursor Pro?) o **X API**?
- Esiste un'API/SDK pubblica o in beta per Grok Bot oltre ai webhook delle routine?
- Il tag **@bot** può essere abilitato per account X italiani durante l'evento?
- Criteri di valutazione finali e premi (sul sito: "To be announced").
- Le **tracks** sono obbligatorie o il brief hardware è libero?

## Fonti principali

- https://docs.x.ai/llms.txt (indice completo docs; ogni pagina disponibile aggiungendo `.md`)
- https://docs.x.ai/grok-bot/overview
- https://docs.x.ai/developers/model-capabilities/imagine
- https://docs.x.ai/build/overview
- https://docs.x.ai/developers/pricing
- https://docs.x.com/x-api/getting-started/pricing
- https://github.com/xai-org
- https://pavia.grokbot.it
- https://luma.com/spacexai-z1ys
