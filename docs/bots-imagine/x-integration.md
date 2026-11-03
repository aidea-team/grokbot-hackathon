# Integrazione con X (leggere post, menzioni, rispondere, postare media)

> Verificato il **2026-11-03** su docs.x.com (pagine `.md`), docs.x.ai/developers/tools/x-search e docs.x.ai/grok-bot/*.
> Endpoint provati con chiave non valida (risposte 401/403 coerenti), SDK `xdk` 0.10.6 (Python) e `@xdevplatform/xdk` 0.6.6 (TS) ispezionati. Nessuna chiamata autenticata eseguita.
> ⚠️ = non verificato.

## TL;DR: quale strada scegliere

| Bisogno | Strada più veloce | Account necessari | Costo indicativo |
|---|---|---|---|
| **Leggere/cercare** post su X e farli ragionare a Grok | Tool **`x_search`** della Grok API (Responses API) | Solo xAI API key | **$5 / 1k post** + **$10 / 1k profili** + token |
| Leggere X da un Bot | Grok Bot: lettura pubblica inclusa | Piano con Grok Bot | Usage del piano |
| **Postare** (testo/immagini/video), **rispondere** a menzioni | **X API v2** pay-per-use (`POST /2/tweets`, `POST /2/media/upload`) | X developer account + app con OAuth user context | **$0.015/post** ($0.20 se il testo contiene URL!) |
| Leggere le **proprie menzioni** | `GET /2/users/{id}/mentions` (Owned Read) | X developer account | **$0.001/post** |
| Menzioni **in tempo reale** | X Activity API, evento `post.mention.create` via webhook/stream | X developer account | $0.005/evento |
| Provare tutto da terminale | **`xurl`** (CLI ufficiale, OAuth incluso) | X developer account | come sopra |
| Far usare X a un agente (Grok Build, Cursor) | **X MCP** `https://api.x.com/mcp` via `xurl mcp` | X developer account | come sopra |

Consiglio hackathon: **lettura con `x_search`** (zero setup X) + **scrittura con X API** solo se la demo deve davvero pubblicare. Il tag **@bot** di Grok Bot non funziona per account X con paese UE (vedi [grok-bots.md](grok-bots.md#integrazione-x-dentro-grok-bot)).

## 1. Lettura via Grok API: tool `x_search`

Grok cerca su X lato server e risponde con citazioni.

- Endpoint: `POST https://api.x.ai/v1/responses` con `tools: [{"type": "x_search", ...}]` (anche Vercel AI SDK `xai.tools.xSearch()`, xAI SDK Python `xai_sdk.tools.x_search()`).
- Funzioni interne che il modello decide di chiamare: `x_keyword_search` (operatori avanzati, Top/Latest), `x_semantic_search`, `x_user_search`, `x_thread_fetch`.
- Parametri:

| Parametro | Note |
|---|---|
| `allowed_x_handles` | max 20 (10 in AI SDK), senza `@`; non combinabile con `excluded_x_handles` |
| `excluded_x_handles` | max 20 |
| `from_date` / `to_date` | `YYYY-MM-DD` (to_date escluso). Altri formati vengono ignorati. Nell'xAI SDK Python sono `datetime` |
| `enable_image_understanding` | default `false`, costa image token |
| `enable_video_understanding` | default `false`, solo X Search |

- Costi: **$5 per 1k post** fetchati (inclusi parent/quoted, non deduplicati tra ricerche) e **$10 per 1k profili** + token del modello. Contatori in `usage.server_side_tool_usage_details.x_posts_fetched` / `x_users_fetched`.
- Contenere i costi: restringere handle e date, `max_turns` (es. 2).
- ⚠️ È un tool "agentico": non garantisce di restituire *tutti* i post che matchano. Per liste esaustive/deterministiche usare la X API.

## 2. X API v2 (developer.x.com / docs.x.com)

### Accesso e "tier" (situazione attuale)
- **Non ci sono più tier fissi (Free/Basic/Pro)** nelle docs correnti: la X API è **pay-per-usage a crediti**, senza abbonamento. Si comprano crediti nel **Developer Console** (https://console.x.com), si imposta auto-recharge e spending limit. Tetto: **3M Post read/mese** in pay-per-use; oltre → Enterprise.
- Incentivi (in rollout): **$20** gratis dopo il primo acquisto di crediti con la prima carta + match del primo auto-recharge **fino a $50** (scadono dopo 3 mesi). Acquistando crediti X si ottengono anche **crediti xAI API gratuiti** (10–20% sopra $200 di spesa nel ciclo) se colleghi il team xAI.
- Gotcha da xurl README: se l'OAuth riesce ma le letture danno `client-forbidden` / `client-not-enrolled`, sposta l'app nel package **Pay-per-use** e nell'ambiente **Production** (Apps → Manage apps → Move to package).

### Prezzi per operazione (estratto, docs.x.com pricing)
| Operazione | Costo |
|---|---|
| Posts: Read | $0.005 / post |
| User: Read | $0.010 / utente |
| **Owned Reads** (tue menzioni, tuoi post, follower, bookmark...) | **$0.001 / risorsa** |
| **Post: Create** | **$0.015 / richiesta** |
| **Post: Create (with URL)** | **$0.200 / richiesta** ⚠️ evitare link nel testo |
| Post: Create (summoned) | $0.010 / richiesta (⚠️ significato di "summoned" non spiegato nella pagina) |
| Media Metadata | $0.005 / richiesta |
| Counts: Recent | $0.005 / richiesta |
| Evento webhook `post.create` / menzioni via XAA | $0.005 / evento |

Deduplicazione: la stessa risorsa letta più volte nello stesso giorno UTC si paga una volta (soft guarantee). ⚠️ Il costo dell'upload media (`/2/media/upload`) non compare esplicitamente in tabella.

### Autenticazione
| Metodo | Quando |
|---|---|
| **Bearer token (app-only)** | Sola lettura di dati pubblici (search recent, lookup) |
| **OAuth 1.0a User Context** | Postare come un account (4 valori: API key/secret + access token/secret, app con permessi Read+Write). Il modo più rapido per un account "bot" del team |
| **OAuth 2.0 Authorization Code + PKCE** | User context con scope (`tweet.read tweet.write users.read media.write offline.access`) |

Verificato: `POST /2/tweets` e `POST /2/media/upload` con bearer app-only rispondono **403** "Supported authentication types are [OAuth 1.0a User Context, OAuth 2.0 User Context]".

### Endpoint chiave
| Azione | Endpoint | Auth | Note |
|---|---|---|---|
| Ricerca recente | `GET /2/tweets/search/recent?query=...` | Bearer | **ultimi 7 giorni**, operatori (`from:`, `lang:`, `-is:retweet`, ...) |
| Ricerca full archive | `GET /2/tweets/search/all` | Bearer | dal 2006 |
| Menzioni di un utente | `GET /2/users/{id}/mentions` | Bearer o user | `since_id` per polling incrementale; Owned Read se `{id}` è il proprietario dell'app |
| Chi sono | `GET /2/users/me` | user | serve per ottenere il proprio `id` |
| Upload media | `POST /2/media/upload` (JSON: `media` base64 + `media_category`) | user (`media.write`) | categorie `tweet_image`, `tweet_video`, `tweet_gif`, ... Per video/grandi file: chunked `/2/media/upload/initialize` → `/{id}/append` → `/{id}/finalize` → status |
| Crea post / reply | `POST /2/tweets` | user (`tweet.write`) | `text`, `media.media_ids` (max **4 foto** o 1 GIF o 1 video), `reply.in_reply_to_tweet_id`, `made_with_ai` (bool) |
| Quote post | `POST /2/tweets` con `quote_tweet_id` | — | **solo Enterprise**, non pay-per-use |
| Real-time | X Activity API (`post.mention.create`, `post.reply.create`, ...) via webhook o stream persistente | — | Filtered Stream per keyword/operatori |

Limiti media (account non Premium): immagine 5 MB, GIF 15 MB, video su post 0.5 s–20 min / 8 GB. I limiti seguono lo status Premium dell'**utente che posta**, non il piano API. Un upload riuscito può comunque essere rifiutato al momento del post.

### SDK ufficiali (XDK)
- Python: `pip install xdk` (0.10.6 al 2026-11-03, Python ≥3.8). `from xdk import Client`.
- TypeScript: `npm i @xdevplatform/xdk` (0.6.6).
- Metodi verificati per introspezione (Python): `client.posts.search_recent(...)`, `client.posts.create(CreateRequest(...))`, `client.users.get_me()`, **`client.users.get_mentions(id, since_id=...)`**, `client.media.upload(UploadRequest(media=<b64>, media_category="tweet_image"))`, `client.media.initialize_upload/append_upload/finalize_upload/get_upload_status`.
- ⚠️ **Errore nelle docs X**: il quickstart menzioni usa `client.posts.get_user_mentions(...)` (Python) / `client.posts.getUserMentions(...)` (TS), che **non esistono** nelle versioni attuali; i metodi corretti sono `client.users.get_mentions` / `client.users.getMentions`.

### xurl (CLI, la via più rapida per testare)
```bash
npm install -g @xdevplatform/xurl          # oppure brew / install.sh / go install
xurl auth apps add my-app --client-id ID --client-secret SECRET
xurl auth oauth2 --app my-app               # login browser (o --headless)
xurl /2/users/me
xurl -X POST /2/tweets -d '{"text":"Hello from Pavia"}'
xurl media upload poster.jpg                # restituisce media_id
xurl -X POST /2/tweets -d '{"text":"con immagine","media":{"media_ids":["MEDIA_ID"]}}'
xurl webhook start                          # webhook temporaneo via ngrok per test
```

### X MCP (per agenti: Grok Build, Cursor, Claude...)
- Server MCP hosted **`https://api.x.com/mcp`**; si collega con il bridge `npx -y @xdevplatform/xurl mcp https://api.x.com/mcp` (OAuth2 PKCE, redirect `http://localhost:8080/callback`) oppure, solo lettura, con header `Authorization: Bearer <app-only token>`.
- Capability dichiarate: fetch post, likers/reposters/quoters, conteggi, full-archive search, user search, news, timeline e **menzioni**, bookmark, trend, **Articles** (bozza/pubblica).
- ⚠️ La pagina non elenca la **creazione di post normali** tra le capability: per postare usare REST/xurl.
- Config Grok Build (`~/.grok/config.toml`) — vedi [grok-build.md](grok-build.md#x-mcp-in-grok-build).

## 3. Pattern "rispondere alle menzioni" (bot classico)

1. Polling ogni 30–60 s di `GET /2/users/{me}/mentions?since_id=<ultimo>` (Owned Read, $0.001/post).
2. Per ogni menzione: Grok API (es. `grok-4.7`, eventualmente con `x_search` per contesto o Imagine per creare un'immagine).
3. Upload media → `POST /2/tweets` con `reply.in_reply_to_tweet_id` ($0.015/post; **niente URL nel testo**).
4. Alternativa real-time: X Activity API `post.mention.create` via webhook.

Codice: [code-samples.md](code-samples.md#6-x-api-post-con-immagine-generata).

⚠️ Policy: le X Developer Guidelines regolano gli account automatizzati (etichettatura bot, risposte non richieste). Non lette in dettaglio: https://docs.x.com/developer-guidelines.md

## Fonti

- https://docs.x.com/llms.txt
- https://docs.x.com/x-api/getting-started/pricing
- https://docs.x.com/x-api/getting-started/free-credits
- https://docs.x.com/make-your-first-request
- https://docs.x.com/fundamentals/authentication/overview
- https://docs.x.com/x-api/posts/search/quickstart/recent-search
- https://docs.x.com/x-api/posts/timelines/quickstart/user-mention-quickstart
- https://docs.x.com/x-api/posts/create-post
- https://docs.x.com/x-api/media/upload-media
- https://docs.x.com/x-api/media/quickstart/best-practices
- https://docs.x.com/x-api/activity/introduction
- https://docs.x.com/tools/mcp
- https://docs.x.com/xdks/python/install , https://docs.x.com/xdks/python/authentication
- https://github.com/xdevplatform/xurl (README)
- https://docs.x.ai/developers/tools/x-search
- https://docs.x.ai/developers/pricing (Tool Invocation Costs)
- https://docs.x.ai/grok-bot/computer-and-apps (sezione "Search and read X", plugin X)
- https://docs.x.ai/grok-bot/tag-on-x
