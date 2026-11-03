# Grok API core (testo, multimodale, agentic): indice e TL;DR

> **Verificato il:** 2026-11-03, il giorno prima del "Grok Hackathon at the Museum" (Ctrl+Alt Museum, Pavia, 4–5 novembre 2026).
> **Metodo:** ho scaricato e letto le pagine markdown ufficiali di docs.x.ai (indice `llms.txt`), l'OpenAPI spec, i README GitHub di `xai-org` e l'annuncio di Grok 4.7 su x.ai; ho installato `xai-sdk 1.21.0` e `openai 3.42.1` per controllare le firme.
> ⚠️ **Nessuno snippet è stato eseguito contro l'API**, perché non avevo una `XAI_API_KEY`. Vanno provati subito con la key dell'evento (vedi "Primi 5 minuti").
> Il simbolo ⚠️ indica cose non verificate, ambigue o in conflitto tra le pagine dei docs.

## File della cartella

| File | Contenuto |
|---|---|
| [models.md](models.md) | Model id esatti, contesto, prezzi, capability, rate limit, alias, modelli ritirati, regioni |
| [responses-and-chat.md](responses-and-chat.md) | Auth, base URL, endpoint, Responses API e Chat Completions, compatibilità SDK OpenAI/Anthropic, streaming, multi-turn, reasoning, priority, cache, WebSocket |
| [tools-and-structured-output.md](tools-and-structured-output.md) | Function calling (formati, `tool_choice`, parallel), structured outputs (JSON Schema, Pydantic, Zod) |
| [vision.md](vision.md) | Image input: formati, limiti, base64, `detail`, snippet Python/JS |
| [agentic-server-tools.md](agentic-server-tools.md) | Web search, X search, code execution, Files, Collections, Remote MCP: come si abilitano, limiti, costi |
| [sdk-quickstart.md](sdk-quickstart.md) | xai-sdk Python, OpenAI SDK, Vercel AI SDK, `@xai-official/sdk` TS; setup del docs MCP in Claude Code |
| [grok-build.md](grok-build.md) | Grok Build (CLI/TUI/headless/ACP), config, plugin ufficiale per Claude Code |
| [gotchas.md](gotchas.md) | Errori comuni, trappole, limiti numerici, **latenza per robot real-time**, snippet di benchmark e pattern di controllo robot |

## TL;DR: cosa usare per cosa

| Bisogno | Scelta |
|---|---|
| Endpoint | `https://api.x.ai/v1` + `Authorization: Bearer $XAI_API_KEY` (compatibile con l'SDK OpenAI) |
| API | **Responses API** (`POST /v1/responses`). Chat Completions è deprecata; Anthropic `/v1/messages` è "fully deprecated" |
| SDK Python | `pip install xai-sdk` (gRPC, completo) **oppure** `openai` con `base_url` |
| SDK TS/JS | `openai` con `baseURL`, oppure `ai` + `@ai-sdk/xai` (`xai.responses('grok-4.7')`); `@xai-official/sdk` è sperimentale |
| Massima qualità, vision, agentic | `grok-4.7`, con `reasoning.effort` `low`/`medium`/`high`(default)/`xhigh` |
| **Bassa latenza (robot, dialogo veloce)** | `grok-4.3` con `reasoning: {effort: "none"}` oppure `grok-4.20-0309-non-reasoning`. Poi misurare il TTFT ([gotchas.md](gotchas.md)) |
| Comandi al robot | Function calling (Responses: tool "piatto") oppure structured output con JSON Schema; `parallel_tool_calls: false`; validazione locale |
| Vedere con la camera | `input_image` con data URL base64 JPEG, `detail: "low"`, `store: false` |
| Info live (web/X) | Tool server-side `web_search` / `x_search` (solo Responses API e xai-sdk): $5/1k chiamate, $5/1k post X. Da tenere **fuori** dal percorso real-time |
| Esporre il robot come tool remoto | Remote MCP (`{"type":"mcp","server_url":...,"server_label":...}`), con il server raggiungibile via HTTPS pubblico |
| Coding agent | Noi usiamo Claude Code. Grok Build (`grok`) è opzionale, con plugin ufficiale `xai-org/grok-build-plugin-cc` |

## I 10 fatti chiave
1. Model id di punta: **`grok-4.7`**. Contesto 500k, $2 / $0.50 (cache) / $6 per 1M token (sotto i 200k), cutoff maggio 2026, input testo e immagini, reasoning non disattivabile.
2. Sull'API **non esistono** `grok-4.7-fast`, `-reasoning` o `-code`. "Grok 4.7 Fast" (2x prezzo) è solo in Cursor e Grok Build; il modello di coding via API è `grok-build-0.1`.
3. Modello veloce ed economico: **`grok-4.3`**, 1M di contesto, $1.25 / $2.50, unico con `reasoning.effort: "none"`. Default `low`.
4. Base URL: `https://api.x.ai/v1`. US regionale: `https://us.api.x.ai/v1` (solo 4.7 e 4.6, +10%). Nessun endpoint EU documentato.
5. La Responses API è quella raccomandata. `store` è true di default (30 giorni), `previous_response_id` per continuare. `grok-4.7` restituisce sempre `reasoning.encrypted_content`, da ripassare invariato.
6. Function calling sulla Responses API: `{"type":"function","name",...,"parameters"}` → `function_call` → `function_call_output` con `call_id`. Parallel attivo di default. Argomenti sempre strict.
7. Structured outputs: `text.format` / `response_format` con `json_schema`; `additionalProperties` è false di default. Pydantic con `responses.parse(text_format=...)` (OpenAI) oppure `chat.parse(Model)` (xai-sdk).
8. Vision: jpg/png, 20 MiB, base64 data URL o URL pubblico, `detail` low/high/auto. Supportata da tutti i modelli 4.x attuali.
9. Tool server-side (Responses API e xai-sdk): `web_search`, `x_search`, `code_interpreter` (xai-sdk `code_execution`), `file_search` (xai-sdk `collections_search`), `mcp`. Si possono limitare i turni con `max_turns`.
10. Rate limit Tier 0: `grok-4.7` 150 RPS / 50M TPM; `grok-4.3` 37 RPS / 10M TPM. Sopra il limite si riceve 429. Il TPM conta anche i token in cache e quelli di reasoning.

## Primi 5 minuti all'evento
```bash
export XAI_API_KEY="xai-..."
curl -s https://api.x.ai/v1/models -H "Authorization: Bearer $XAI_API_KEY" | grep '"id"'   # quali modelli abbiamo davvero
claude mcp add --transport http xai-docs https://docs.x.ai/api/mcp                        # docs ufficiali dentro Claude Code
pip install xai-sdk openai        # e/o: npm install openai ai @ai-sdk/xai zod
```
Poi va lanciato il mini-benchmark TTFT di [gotchas.md](gotchas.md), per scegliere il modello in base alla latenza misurata dal museo.

## Nota sul brand
I docs ufficiali, l'annuncio di Grok 4.7 e l'SDK TS usano **"SpaceXSI"**. Il footer di x.ai riporta "© 2026 SpaceX Super Intelligence LLC". Nelle descrizioni dei repo GitHub (`xai-sdk-python`, `xai-sdk-ts`, `grok-build`) e in alcune pagine compare ancora **"SpaceXAI"**, e la classe TS `SpaceXAI` è un alias deprecato di `SpaceXSI`. Domini, env var e pacchetti restano `x.ai` / `XAI_API_KEY` / `xai-sdk`. ⚠️ Nel brief dell'evento si parla di "SpaceXAI": è probabilmente il nome precedente o colloquiale.

## Incertezze principali (dettagli nei singoli file)
- ⚠️ TTFT e tokens/s dei modelli non sono documentati, e non c'è un endpoint EU: la latenza da Pavia va misurata.
- ⚠️ Il costo in token delle immagini (risoluzione e tiling) non è documentato.
- ⚠️ `service_tier: "fast"` è accettato dalla reference ed è "intercambiabile" con `priority`, ma per `grok-4.7` non è chiaro cosa faccia sull'API pubblica.
- ⚠️ Limite sul numero di tool per richiesta: 350 nella guida, 1000 nella reference.
- ⚠️ `grok-4.5` e `xhigh`: la pagina del modello dice che è supportato, la pagina Reasoning dice che viene trattato come `high`.
- ⚠️ Nella forma `tool_choice` della guida c'è solo la versione Chat Completions; per la Responses l'OpenAPI indica `{type:"function", name}`.
- ⚠️ Default del modello in Grok Build: `grok-4.7` secondo una pagina, `grok-build` secondo l'esempio di config.
- ⚠️ Nessuno snippet eseguito live.

## Fonti (principali)
- https://docs.x.ai/llms.txt (indice di tutte le pagine; aggiungendo `.md` a ogni URL si ottiene il markdown)
- https://docs.x.ai/developers/quickstart.md
- https://docs.x.ai/developers/models.md · https://docs.x.ai/developers/grok-4-7.md · https://docs.x.ai/developers/pricing.md · https://docs.x.ai/developers/rate-limits.md
- https://docs.x.ai/developers/release-notes.md
- https://docs.x.ai/openapi.json · https://docs.x.ai/api/mcp (docs MCP)
- https://github.com/xai-org/xai-sdk-python · https://github.com/xai-org/xai-sdk-ts · https://github.com/xai-org/xai-cookbook · https://github.com/xai-org/grok-build-plugin-cc
- https://x.ai/news/grok-4-7
