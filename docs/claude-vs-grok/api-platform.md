# Piattaforma API: Claude API ↔ Grok API

> **Verificato il:** 2026-11-03.
> **Lato Grok:** fonte primaria i file in [../grok-api/](../grok-api/README.md), [../voice/README.md](../voice/README.md) e [../bots-imagine/grok-imagine.md](../bots-imagine/grok-imagine.md). Oggi ho verificato in più su docs.x.ai: Batch API, Deferred, Citations, Pricing, Rate Limits, il reference Responses (`status`, `incomplete_details`), `POST /v1/tokenize-text`, il tool `shell` del TS SDK e la Web Search (che naviga anche le pagine).
> **Lato Claude:** platform.claude.com/docs letto oggi (Pricing, Rate limits, Vision, OpenAI SDK compatibility, Computer use), più il reference ufficiale `claude-api` (snapshot del 2026-10-06) per la forma delle richieste.
> ⚠️ indica cose non verificate, dedotte o in conflitto tra fonti. **Nessuno snippet è stato eseguito**: non avevamo una key xAI e non abbiamo chiamato l'API Claude.
> Il mapping dei modelli e dei prezzi è in [models.md](models.md). Claude Code, Agent SDK e il workflow di sviluppo sono trattati negli altri file di questa cartella.

## Tabella di mapping

| Concetto Anthropic | Equivalente Grok | Quanto è vicino | Per l'hackathon |
|---|---|---|---|
| `POST /v1/messages` (Messages API) | `POST /v1/responses` (**Responses API**) | ≈ stesso ruolo, forma OpenAI-Responses | Responses, sempre |
| `system` top-level | `instructions`, oppure `{"role":"system"}` dentro `input` | = | `system` in `input` (è compatibile con `store:false`) |
| Conversazione stateless (rimandi `messages`) | `store: false` + rimandare `input += response.output` | = | **stateless** (`store:false`) |
| Message Threads (beta `thread`) | `store: true` (default!) + `previous_response_id` | ≈ (su Grok è il default e dura 30 giorni) | da evitare con le immagini; ok per demo testuali |
| `max_tokens` (obbligatorio) | `max_output_tokens` (opzionale, default 128k, conta **solo** l'output visibile) | ≈ | impostarlo basso nel loop veloce |
| `stop_reason` | `status` (`completed`/`incomplete`) + `incomplete_details` + presenza di item `function_call` | ≈ | vedi [§ Stop reason](#stop-reason) |
| Streaming SSE (`message_start`, `content_block_delta`…) | SSE con eventi tipizzati `response.output_text.delta`, `response.completed`… | ≈ | `stream=True` |
| `input_json_delta` (eager input streaming) | ❌ le function call arrivano **intere** in un solo evento | ≠ | — |
| Tool `{name, description, input_schema}` | `{"type":"function", name, description, parameters}` (piatto) | = | |
| `tool_use` / `tool_result` (`tool_use_id`) | `function_call` / `function_call_output` (`call_id`) | = | |
| `tool_choice` `auto`/`any`/`tool`/`none` | `auto`/`required`/`{type:"function",name}`/`none` | = (su Grok il forcing **funziona**) | |
| `disable_parallel_tool_use: true` | `parallel_tool_calls: false` | = | **sempre** `false` sui robot |
| `strict: true` sul tool | sempre strict (implicito) | = | |
| Structured outputs `output_config.format` / `messages.parse(output_format=)` | `text.format` json_schema / `responses.parse(text_format=)` | = | |
| Adaptive thinking + `output_config.effort` | `reasoning.effort` | ≈ | `none` (4.3) o `low` (4.7) nel percorso caldo |
| Blocchi `thinking` con `signature` da ripassare invariati | item `reasoning` con `encrypted_content` da ripassare invariati | = | ripassare tutto `response.output` |
| `display: "summarized"` | eventi `response.reasoning_summary_text.delta` | ≈ | |
| Prompt caching `cache_control` (esplicito o top-level) | caching **automatico** + `prompt_cache_key` | ≈ (nessun breakpoint, nessun costo di scrittura) | `prompt_cache_key` per sessione |
| Compaction (beta, lato server) | `POST /v1/responses/compact` (endpoint esplicito) | ≈ | serve solo nelle sessioni lunghe |
| Message Batches (-50%) | Batch API `/v1/batches` (-20%) e Deferred completions | ≈ | serve solo per eval offline |
| Files API | Files API `/v1/files` | ≈ (su Grok allegare un file **attiva un tool a pagamento**) | |
| Citations sui `document` (`char_location`, `page_location`) | `citations` (URL) e inline citations **solo dai tool di ricerca** | ≠ | — |
| `count_tokens` | `POST /v1/tokenize-text` (solo testo) | ≈ debole | contare a posteriori con `usage` |
| Server tool `web_search` / `web_fetch` | `web_search` (naviga anche le pagine) + **`x_search`** | ≈ / Grok ha in più X | fuori dal percorso caldo |
| `code_execution` | `code_interpreter` (REST) / `code_execution()` (xai-sdk) | ≈ | |
| Memory tool (`memory_20250818`) | ❌ niente tool dedicato. Le alternative sono `store`/`previous_response_id`, Collections, o una function propria | ≠ | function `remember()` locale |
| MCP connector (`mcp_servers` + `mcp_toolset`) | Remote MCP `{"type":"mcp", server_url, server_label}` | = (molto più semplice su Grok) | robot come MCP dietro un tunnel |
| RAG: nessun vector store gestito | `file_search` + **Collections** | Grok ha in più | |
| Tool search, programmatic tool calling, advisor | ❌ | — | — |
| Bash tool (client) / Agent Skills | `shell` tool (client, TS SDK) con skill `SKILL.md` | ≈ ⚠️ | — |
| Vision: jpeg/png/gif/webp, PDF nativi | **solo jpg/png**, `detail`, niente PDF visivi | ≈ | JPEG + `detail:"low"` |
| Computer use (`computer_toolset_20260801`) | ❌ nell'API. Grok Bot ha un computer cloud, ma è un'app | ≠ | vision + function |
| Voce realtime: ❌ nell'API | **Grok Voice Agent** `wss://api.x.ai/v1/realtime` | Grok ha in più | [../voice/](../voice/README.md) |
| TTS / STT: ❌ | `/v1/tts`, `/v1/stt` (REST e WebSocket) | Grok ha in più | |
| Immagini e video: ❌ | **Grok Imagine** | Grok ha in più | [../bots-imagine/grok-imagine.md](../bots-imagine/grok-imagine.md) |
| Embeddings: ❌ (Anthropic rimanda a terzi) | `/v1/embeddings` ⚠️ | Grok ha in più ⚠️ | |
| SDK `anthropic` | `xai-sdk` (gRPC) oppure `openai` con `base_url` | ≈ | **`openai` + Responses** |
| OpenAI-compat di Anthropic (`/v1/chat/completions`) | Grok **è** OpenAI-compatibile in modo nativo | — | |
| Anthropic-compat di xAI (`/v1/messages`) | "fully deprecated" | — | **non usarla** |
| Fast mode / Priority Tier | `service_tier: "priority"` (2×) | ≈ | solo se c'è carico |
| `inference_geo: "us"` (1.1×) | `https://us.api.x.ai/v1` (1.1×) | = | globale (non esiste EU in nessuno dei due) |
| 429 `rate_limit_error`, 529 `overloaded_error` | 429 / gRPC `RESOURCE_EXHAUSTED`, 5xx / `UNAVAILABLE` | ≈ | backoff manuale sul 429 |
| `stop_reason: "refusal"` + `fallbacks` | nessuno stop reason dedicato. La violazione di policy viene bloccata e si paga comunque ($0.05 se bloccata prima) | ≠ ⚠️ | |

---

## 1. Messages API ↔ Responses API

| | Claude | Grok |
|---|---|---|
| Endpoint | `POST https://api.anthropic.com/v1/messages` | `POST https://api.x.ai/v1/responses` |
| Auth | `x-api-key` + `anthropic-version` (li gestisce l'SDK) | `Authorization: Bearer $XAI_API_KEY` |
| Input | `messages: [{role, content: [blocks]}]` | `input`: stringa oppure lista di item (`{role, content}`, `function_call_output`, item di output precedenti…) |
| System | `system="..."` top-level | `{"role":"system","content":...}` in `input` **oppure** `instructions`. `instructions` **non** si combina con `previous_response_id` |
| Testo in uscita | `response.content[i].text` (blocchi `text`) | `response.output_text` (helper dell'SDK OpenAI) oppure `output[]` → `message` → `output_text` |
| Stato | stateless (a parte la beta Message Threads) | **`store: true` di default** (30 giorni, `GET`/`DELETE /v1/responses/{id}`). `previous_response_id` continua la conversazione |
| Prefill dell'assistente | rimosso sui modelli 4.6+ (400) | non esiste nella Responses API ⚠️. Per il formato si usano structured output |
| Sampling | `temperature`/`top_p`/`top_k` danno 400 sui modelli recenti | `temperature` 0–2 (sopra 1 viene trattata come 1), `top_p`. Con i modelli reasoning `stop`, `presence_penalty` e `frequency_penalty` danno **errore** |
| Costo nella risposta | si calcola da `usage` | `usage.cost_in_usd_ticks` è già pronto: utile per i risultati quantitativi da mostrare alla giuria |

```python
# Claude
import anthropic
c = anthropic.Anthropic()
r = c.messages.create(
    model="claude-opus-5-5", max_tokens=1024,
    system="Sei il cane robot del museo. Rispondi in italiano, max 2 frasi.",
    messages=[{"role": "user", "content": "Ciao, chi sei?"}],
)
print(next(b.text for b in r.content if b.type == "text"))
```
```python
# Grok (SDK OpenAI, Responses API)
import os
from openai import OpenAI
g = OpenAI(api_key=os.environ["XAI_API_KEY"], base_url="https://api.x.ai/v1")
r = g.responses.create(
    model="grok-4.3", reasoning={"effort": "none"}, store=False,
    input=[
        {"role": "system", "content": "Sei il cane robot del museo. Rispondi in italiano, max 2 frasi."},
        {"role": "user", "content": "Ciao, chi sei?"},
    ],
)
print(r.output_text)
```

### Multi-turn: history lato client vs `previous_response_id`
- **Claude:** `messages.append({"role":"assistant","content": r.content})` e poi il turno user successivo. Bisogna ripassare sempre l'intero `content`, perché contiene i blocchi `thinking`.
- **Grok, stateless (consigliato):** `history += r.output` (include gli item `reasoning` cifrati, che vanno lasciati **invariati e nell'ordine originale**), poi il nuovo messaggio user, con `store=False`. È il modello mentale identico a Claude.
- **Grok, stateful:** `previous_response_id=r.id` e nell'`input` solo il nuovo messaggio. È comodo, ma i dati restano salvati 30 giorni e i docs **sconsigliano `store` con le immagini** (la richiesta può fallire).
- Dettagli e snippet: [../grok-api/responses-and-chat.md § Multi-turn](../grok-api/responses-and-chat.md).

**Per l'hackathon:** history client-side con `store=False`. È lo stesso pattern che conosci da Claude, funziona con le immagini e lascia tutto il controllo a noi (logging JSONL, replay, fixture per la giuria).

### Streaming
| Claude (SSE) | Grok Responses (SSE) |
|---|---|
| `message_start` | `response.created` |
| `content_block_delta` / `text_delta` | `response.output_text.delta` (`event.delta`) |
| `content_block_delta` / `thinking_delta` | `response.reasoning_summary_text.delta` / `response.reasoning_text.delta` |
| `content_block_delta` / `input_json_delta` | ❌ la `function_call` arriva **intera** (si vede quando l'item di output viene aggiunto o completato) |
| `message_delta` (con `stop_reason` e `usage`) + `message_stop` | `response.completed` / `response.incomplete` (`event.response` è la risposta finale) |
| helper `messages.stream()` → `text_stream`, `get_final_message()` | SDK OpenAI: si itera sugli eventi. xai-sdk: `for response, chunk in chat.stream()` |

```python
# Claude
with c.messages.stream(model="claude-opus-5-5", max_tokens=1024, messages=[{"role":"user","content":"Spiega il PID in 2 righe"}]) as s:
    for t in s.text_stream: print(t, end="", flush=True)
```
```python
# Grok
for ev in g.responses.create(model="grok-4.3", reasoning={"effort":"none"}, input="Spiega il PID in 2 righe", stream=True, store=False):
    if ev.type == "response.output_text.delta": print(ev.delta, end="", flush=True)
```
In Grok c'è anche la **WebSocket mode** (`wss://api.x.ai/v1/responses`): fino a circa -20% di latenza end-to-end nei loop con molti tool. Claude non ha un equivalente. Dettagli in [../grok-api/responses-and-chat.md](../grok-api/responses-and-chat.md).

### Stop reason
| Claude `stop_reason` | Grok (Responses) | Note |
|---|---|---|
| `end_turn` | `status: "completed"` senza item `function_call` in `output` | |
| `tool_use` | `status: "completed"` **con** item `function_call` in `output` | Grok non ha uno stop reason: bisogna scorrere `output` |
| `max_tokens` | `status: "incomplete"` + `incomplete_details` | ⚠️ il reference xAI non elenca i valori di `incomplete_details.reason`; per analogia con OpenAI ci si aspetta `max_output_tokens` |
| `stop_sequence` | — | `stop` dà errore con i modelli reasoning. Solo Chat Completions ha `finish_reason: "stop"` |
| `pause_turn` (loop dei server tool al limite) | ⚠️ non documentato. Il loop dei server tool si limita con `max_turns` (e `max_tool_calls`) | |
| `refusal` (+ `stop_details`, `fallbacks`) | nessun equivalente documentato | ⚠️ con Grok bisogna gestire errori e contenuti bloccati in modo generico |

---

## 2. Tool use ↔ function calling

Dettagli completi in [../grok-api/tools-and-structured-output.md](../grok-api/tools-and-structured-output.md). Qui servono solo le differenze rispetto a Claude.

| | Claude | Grok (Responses) |
|---|---|---|
| Definizione | `{"name","description","input_schema"}` | `{"type":"function","name","description","parameters"}` |
| Strict | `strict: true` opzionale (richiede `additionalProperties:false`) | **sempre strict**; `additionalProperties` è `false` di default |
| Chiamata | blocco `tool_use` con `id`, `name`, `input` (già un dict) | item `function_call` con `call_id`, `name`, `arguments` (**stringa JSON**: serve `json.loads`) |
| Risultato | blocco `tool_result` (`tool_use_id`, `content`, `is_error`) dentro un messaggio **user** | item `function_call_output` (`call_id`, `output` stringa) direttamente in `input`. **Non** c'è `is_error`: l'errore va messo nella stringa |
| Parallel | default on; tutti i `tool_result` in **un solo** messaggio user | default on; tutti i `function_call_output` in **una sola** richiesta |
| Disattivare il parallel | `tool_choice: {"type":"auto","disable_parallel_tool_use":true}` | `parallel_tool_calls: false` |
| Forzare | `any`/`tool` → **400 su Opus 5.5, Sonnet 5.5 e Fable 5.1** | `"required"` / `{"type":"function","name":"x"}` (xai-sdk: `required_tool("x")`) ✅ |
| Limiti | — | ⚠️ max 350 tool (guida) oppure 1000 (reference) |
| Tool runner dell'SDK | `client.beta.messages.tool_runner` + `@beta_tool` | ❌ in Python: il loop va scritto a mano (il TS ha `runTool()` in `@xai-official/sdk` e Vercel `stopWhen`) |

```python
# Claude: loop manuale
tools = [{"name": "robot_action", "description": "Execute ONE physical action.", "strict": True,
          "input_schema": {"type": "object", "additionalProperties": False,
                           "properties": {"action": {"type": "string", "enum": ["sit", "stand", "walk"]}},
                           "required": ["action"]}}]
msgs = [{"role": "user", "content": "Siediti"}]
r = c.messages.create(model="claude-opus-5-5", max_tokens=2048, tools=tools, messages=msgs,
                      tool_choice={"type": "auto", "disable_parallel_tool_use": True})
while r.stop_reason == "tool_use":
    msgs.append({"role": "assistant", "content": r.content})
    msgs.append({"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": b.id, "content": json.dumps(execute(b.input))}
        for b in r.content if b.type == "tool_use"]})
    r = c.messages.create(model="claude-opus-5-5", max_tokens=2048, tools=tools, messages=msgs)
```
```python
# Grok: stesso loop, stateless
tools = [{"type": "function", "name": "robot_action", "description": "Execute ONE physical action.",
          "parameters": {"type": "object",
                         "properties": {"action": {"type": "string", "enum": ["sit", "stand", "walk"]}},
                         "required": ["action"]}}]
inp = [{"role": "user", "content": "Siediti"}]
kw = dict(model="grok-4.7", reasoning={"effort": "low"}, tools=tools, parallel_tool_calls=False, store=False)
r = g.responses.create(input=inp, **kw)
while calls := [o for o in r.output if o.type == "function_call"]:
    inp += r.output                                   # include i reasoning item cifrati: non toccarli
    inp += [{"type": "function_call_output", "call_id": c_.call_id,
             "output": json.dumps(execute(json.loads(c_.arguments)))} for c_ in calls]
    r = g.responses.create(input=inp, **kw)
print(r.output_text)
```
Il pattern completo con validatore e whitelist è in [../grok-api/gotchas.md](../grok-api/gotchas.md) e [../hardware/llm-robot-architecture.md](../hardware/llm-robot-architecture.md).

### Structured outputs
| Claude | Grok |
|---|---|
| `client.messages.parse(..., output_format=Model)` → `response.parsed_output` | `g.responses.parse(..., text_format=Model)` → `resp.output_parsed` |
| `output_config={"format":{"type":"json_schema","schema":...}}` | `text={"format":{"type":"json_schema","name":...,"schema":...,"strict":True}}` |
| incompatibile con le citations | compatibile con i tool, anche server-side |
| sottoinsieme di JSON Schema documentato | sottoinsieme documentato: `additionalProperties` false di default, regex senza lookaround, `minItems`/`maxItems` ≤ 256… ([dettagli](../grok-api/tools-and-structured-output.md#supporto-json-schema-sottoinsieme)) |

**Per l'hackathon:** per i comandi al robot conviene il function calling con enum strette, `parallel_tool_calls=False` e un validatore locale. Gli structured output servono quando vuoi un singolo oggetto (per esempio un piano JSON da validare tutto insieme prima di eseguirlo).

---

## 3. Extended/adaptive thinking ↔ `reasoning.effort`

| | Claude 5.5 | Grok |
|---|---|---|
| Accensione | adaptive: Opus 5.5 e Fable 5.1 **sempre** on; Sonnet 5.5 si spegne con `between_tools`; Haiku 5.5 accetta `disabled` a effort ≤ high | `grok-4.7`/`4.6`: sempre on (minimo `low`); `grok-4.3`: `none` lo spegne; `grok-4.20-0309-non-reasoning`: mai |
| Parametro | `output_config={"effort": "low|medium|high|xhigh|max"}` | `reasoning={"effort": "none|low|medium|high|xhigh"}` (xai-sdk: `reasoning_effort=`) |
| `budget_tokens` | rimosso (400) | non esiste |
| Visibilità | `display`: `omitted` (default) / `summarized` / `updates` | riassunto via eventi `reasoning_summary_text`. Chat Completions espone `reasoning_content` |
| Replay | blocchi `thinking` firmati, invariati; modificare la history li invalida (preserved thinking) | item `reasoning` con `encrypted_content`, invariati; riordinarli o filtrarli fa perdere il ragionamento e la cache |
| Fatturazione | thinking = output | reasoning = output, e **conta nel TPM** |

```python
c.messages.create(model="claude-opus-5-5", max_tokens=4096, output_config={"effort": "low"}, messages=[...])
g.responses.create(model="grok-4.7", reasoning={"effort": "low"}, input=[...], store=False)
```
`grok-4.20-multi-agent-0309` usa `effort` per scegliere il numero di agenti (`low`/`medium` = 4, `high`/`xhigh` = 16).

---

## 4. Prompt caching, Batch, Files, Citations, token counting

### Prompt caching
| | Claude | Grok |
|---|---|---|
| Attivazione | `cache_control: {"type":"ephemeral"}` sui blocchi (max 4 breakpoint) oppure top-level (auto); TTL 5 min o 1 h | **automatica**, senza breakpoint |
| Instradamento | — | `prompt_cache_key="<sessione>"` (Responses) / header `x-grok-conv-id` (Chat Completions e xai-sdk `metadata`) |
| Costo | scrittura 1.25× (5m) o 2× (1h); lettura 0.05× (Opus e Sonnet 5.5) | scrittura **gratis**; lettura 25% (4.7) o 16% (4.3) dell'input |
| Verifica | `usage.cache_read_input_tokens` | `usage.input_tokens_details.cached_tokens` |
| Rate limit | i token letti dalla cache non contano nell'ITPM | i token in cache contano nel TPM |
| Regola comune | prefisso stabile: tool e system statici in testa, solo append | identica |

```python
c.messages.create(model="claude-opus-5-5", max_tokens=1024, cache_control={"type": "ephemeral"}, system=SYSTEM, messages=msgs)
g.responses.create(model="grok-4.3", reasoning={"effort": "none"}, prompt_cache_key="robodog-1", input=[SYSTEM_MSG, *history], store=False)
```

### Batch API
| | Claude Message Batches | Grok Batch API |
|---|---|---|
| Endpoint | `POST /v1/messages/batches` con `requests=[{custom_id, params}]` | `POST /v1/batches` (crea il contenitore) → `POST /v1/batches/{id}/requests` (ogni richiesta ha un `batch_request_id`; si può anche caricare un JSONL) → `GET /v1/batches/{id}` |
| Sconto | -50% | -20% (modelli 4.x; `grok-build-0.1` nessuno sconto) |
| Contenuto | solo Messages | chat/Responses, **anche immagini, video e MCP** (Imagine senza sconto) |
| Tempi | entro 24 h | "typically within 24 hours", best effort |
| Rate limit | limiti propri | le richieste non contano nei rate limit |
| Alternativa singola asincrona | — | **Deferred completions**: `GET /v1/chat/deferred-completion/{request_id}` (202 finché non è pronta, si ritira una sola volta entro 24 h). Immagini: `deferred: true` |

**Per l'hackathon:** il Batch serve solo per generare dataset o eval offline. In 36 ore conviene fare chiamate normali con `asyncio.gather`.

### Files API
| | Claude | Grok |
|---|---|---|
| Upload | `client.files.upload(...)` → `file_id` | `POST /v1/files` / xai-sdk `client.files.upload(...)`, TTL `expires_after` |
| Uso | blocco `document` (PDF, testo) o `image` con `source: {type:"file", file_id}`. Il modello legge il contenuto **direttamente** | `{"type":"input_file","file_id":...}`. **Attiva automaticamente `attachment_search`**: la richiesta diventa agentica e si paga come un tool ($5/1k). Servono modelli agentici (4.20, 4.5, 4.6, 4.7) |
| Limiti | 32 MB per richiesta per i PDF, 600 pagine | 512 MB per file; storage $0.025/GiB/giorno |
| Dettagli | — | [../grok-api/agentic-server-tools.md § Files API](../grok-api/agentic-server-tools.md) |

### Citations
- **Claude:** `citations: {enabled: true}` sui blocchi `document`. Ogni citazione ha `cited_text` e una posizione precisa (`char_location`, `page_location`, `content_block_location`). Serve per fare grounding su documenti **tuoi**.
- **Grok:** `response.citations` contiene l'elenco degli **URL** incontrati dai tool di ricerca (sempre presente). Le inline citations `[[N]](url)` più `annotations` sono attive di default sulla Responses API e opt-in su xai-sdk (`include=["inline_citations"]`).
- ⚠️ Lato Grok non ho trovato citazioni posizionali su documenti propri: per Collections e `file_search` non è documentato.
- **Verdetto:** se in Claude ti servirebbero le document citations, su Grok la cosa più vicina è Collections + `file_search` con un prompt che chieda di citare, poi da verificare.

### Token counting
- **Claude:** `client.messages.count_tokens(model, messages, tools, system…)` conta la richiesta **completa**, immagini e tool compresi.
- **Grok:** `POST /v1/tokenize-text` con `{model, text}` conta **solo testo**: niente tool né immagini. Il costo reale si legge a posteriori in `usage` (`input_tokens`, `cached_tokens`, `reasoning_tokens`, `cost_in_usd_ticks`).
- **Per l'hackathon:** basta loggare `usage` di ogni chiamata nel JSONL.

---

## 5. Server tools

| Claude (`type`) | Grok (`type` REST / xai-sdk) | Differenze | Prezzo Claude ↔ Grok |
|---|---|---|---|
| `web_search_20260209` | `web_search` / `web_search()` | Grok: `filters.allowed_domains` o `excluded_domains` (max 5), `enable_image_understanding`, `enable_image_search` | $10/1k ↔ $5/1k |
| `web_fetch_20260209` (solo URL già presenti nella conversazione) | nessun tool separato: `web_search` "browse web pages" | ⚠️ non c'è un fetch deterministico di un URL dato. Per quello serve una function propria | token ↔ incluso in web_search |
| — | **`x_search`** / `x_search()` | ricerca su post e profili di X, filtri per handle e date, video understanding | — ↔ $5/1k post + $10/1k profili |
| `code_execution_20260521` (bash e file nel container) | `code_interpreter` / `code_execution()` | Grok: sandbox Python **stateless**, senza rete | gratis con web search, altrimenti a tempo ↔ $5/1k |
| `memory_20250818` (client-side, operazioni su file) | ❌ | alternative: `store` + `previous_response_id`, Collections, oppure una function `remember()` propria | — |
| MCP connector: `mcp_servers=[{type:"url",url,name}]` + `tools=[{type:"mcp_toolset",mcp_server_name}]` + beta `mcp-client-2025-11-20` | `{"type":"mcp","server_url","server_label","allowed_tools","authorization"}`, GA | Grok: un solo blocco, niente beta; `require_approval` non supportato; server pubblico HTTPS (Streamable HTTP o SSE) | token ↔ token |
| (nessun RAG gestito) | `file_search` + `vector_store_ids` / `collections_search(collection_ids=)` | per creare le Collections serve la Management key o la console | — ↔ $2.50/1k |
| `tool_search_tool_*` (con `defer_loading`) | ❌ | — | |
| `image_generation`: ❌ | `{"type":"image_generation"}` | vedi § 9 | |
| `pause_turn` dopo 10 iterazioni | `max_turns` (consigliati 1–2 per lookup) | | |

Altri dettagli:
- **Output dei server tool:** con Claude arrivano come blocchi `*_tool_result` nel `content`. Con Grok **non** vengono restituiti di default: si vedono le invocazioni e `server_side_tool_usage`, e per gli output serve `include=[...]` su xai-sdk.
- **Chi esegue cosa:** `function_call` lo eseguiamo noi; `web_search_call`, `code_interpreter_call`, `file_search_call` e `mcp_call` sono server-side. Dettagli in [../grok-api/agentic-server-tools.md](../grok-api/agentic-server-tools.md).
- I server tool esistono **solo** sulla Responses API e su xai-sdk, non su Chat Completions.

**Per l'hackathon:**
- Robot come server **MCP** (Streamable HTTP dietro ngrok o cloudflared): lo stesso server lo usa sia la Responses API sia Grok Voice.
- `x_search` per il fattore "wow" legato a X.
- Niente server tool nel percorso real-time.

---

## 6. Vision e PDF

| | Claude | Grok |
|---|---|---|
| Formati | JPEG, PNG, GIF (primo frame), WebP | **solo jpg/jpeg, png** (⚠️ il TS SDK dice di rilevare WebP, ma i docs API no) |
| Limiti | 8000×8000 px; 600 immagini per richiesta; oltre 20 immagini il limite scende a circa 3000 px per lato; 128 MB per richiesta | 20 MiB per immagine, nessun limite di numero |
| Sorgente | `{"type":"image","source":{"type":"base64"|"url"|"file",...}}` | `{"type":"input_image","image_url":"data:image/jpeg;base64,..."|"https://...","detail":"low|high|auto"}` |
| Controllo del costo | nessun `detail`; costo `⌈w/28⌉×⌈h/28⌉` token, con ridimensionamento automatico | `detail` low/high/auto; ⚠️ costo in token **non documentato** (si legge in `usage`) |
| PDF | blocco `document` nativo (testo e pagine come immagini), citazioni per pagina | ❌ niente PDF visivo: solo tramite Files e `attachment_search` (testuale) ⚠️ |
| Stato | — | usare `store: false` con le immagini |

```python
# Claude
{"role": "user", "content": [
    {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}},
    {"type": "text", "text": "Cosa c'è davanti al robot?"}]}
# Grok
{"role": "user", "content": [
    {"type": "input_image", "image_url": f"data:image/jpeg;base64,{b64}", "detail": "low"},
    {"type": "input_text", "text": "Cosa c'è davanti al robot?"}]}
```
**Per l'hackathon:** frame JPEG 640–1024 px, `detail:"low"`, `grok-4.3` + `none` per la velocità (oppure `grok-4.7` per la precisione), un frame solo quando serve. Dettagli in [../grok-api/vision.md](../grok-api/vision.md).

---

## 7. Computer use

- **Claude:** `{"type":"computer_toolset_20260801"}`: un toolset client-side di 17 azioni (screenshot, click, type, zoom…) che esegue la nostra applicazione. Sui modelli 5.5 non serve un beta header. C'è anche un browser-use toolset.
- **Grok:** ❌ **nessun tool di computer use nell'API** (cercato in `llms.txt` dei docs xAI il 2026-11-03). Le cose più vicine:
  1. **vision + function calling fatto a mano:** screenshot → `input_image` → function `click(x,y)`/`type(text)` eseguita da noi. È lo stesso schema del toolset Claude, ma lo schema dei tool e lo scaling delle coordinate li gestiamo noi;
  2. tool **`shell`** (client-side, documentato nel TS SDK `@xai-official/sdk`): il modello scrive comandi shell che eseguiamo noi (`shell_call` → `shell_call_output`), con skill `SKILL.md` nell'`environment`. ⚠️ Il supporto su REST, OpenAI SDK e xai-sdk Python non è verificato;
  3. **Grok Bot** ha un "computer cloud" persistente, ma è un'app e non un'API ([../bots-imagine/README.md](../bots-imagine/README.md)).
- **Per l'hackathon:** per controllare l'interfaccia di un simulatore (volo o guida), vision + function con primitive semantiche (`set_throttle`, `press_key`) battono il click a coordinate.

---

## 8. Voce realtime, TTS, STT

- **Claude:** ⚠️ **nessuna API voce realtime, TTS o STT** nella documentazione della piattaforma (cercato il 2026-11-03). La modalità vocale esiste nelle app consumer, non come API. Lato API, l'OpenAI-compat di Anthropic restituisce 400 sugli `input_audio`. Con Claude bisogna comporre STT + LLM + TTS di terze parti.
- **Grok:** ha tutto in casa.
  - **Voice Agent** speech-to-speech `wss://api.x.ai/v1/realtime?model=grok-voice-latest`, compatibile con OpenAI Realtime, tool calling in sessione, $0.08/min;
  - **TTS** `/v1/tts` (REST e WebSocket, speech tag);
  - **STT** `/v1/stt`;
  - italiano supportato.
  - Dettagli: [../voice/README.md](../voice/README.md).
- **Per l'hackathon:** se la demo parla, la voce è il **vantaggio competitivo** di Grok: va usata nativa, non ricostruita con una catena STT → LLM → TTS.

---

## 9. Generazione di immagini e video

- **Claude:** nessun modello generativo di immagini o video. Può solo produrre file (grafici, docx…) dalla code execution.
- **Grok:** **Grok Imagine**.
  - Immagini sincrone con `POST /v1/images/generations` e `/edits` (`grok-imagine-image-2.0`, $0.04/img).
  - Video asincroni con `POST /v1/videos/generations` → polling `GET /v1/videos/{request_id}` (`grok-imagine-video-1.5-lite` $0.02/s).
  - C'è anche il tool `image_generation` dentro la Responses API.
  - Dettagli: [../bots-imagine/grok-imagine.md](../bots-imagine/grok-imagine.md).
- ⚠️ L'SDK OpenAI `images.edit()` **non funziona** con xAI (usa multipart): servono xai-sdk o HTTP diretto.

---

## 10. SDK e compatibilità

| Esigenza | Claude | Grok |
|---|---|---|
| SDK ufficiale Python | `anthropic` (REST) | `xai-sdk` 1.21.0 (**gRPC**, Python ≥ 3.10; API "chat": `chat.create` → `append` → `sample`/`stream`) |
| SDK ufficiale TS | `@anthropic-ai/sdk` | `@xai-official/sdk` 0.2.7 (sperimentale, `store:false` di default) |
| Via SDK OpenAI | `base_url="https://api.anthropic.com/v1/"`, solo `chat.completions`. Anthropic lo dichiara "per test e confronto, non production": `strict` ignorato, niente prompt caching, niente thinking in uscita | `base_url="https://api.x.ai/v1"`: **è il percorso principale**, `responses.*` completo (server tool, reasoning, parse) |
| Via SDK Anthropic | — | `POST /v1/messages` su xAI esiste ma è **"fully deprecated"**: non usarlo e non puntare l'SDK `anthropic` su xAI |
| Vercel AI SDK | `@ai-sdk/anthropic` | `@ai-sdk/xai` → `xai.responses('grok-4.7')` |
| Timeout e retry | default 10 min, `max_retries=2` (429, 5xx, connessione) | SDK OpenAI: come OpenAI. xai-sdk: timeout solo sul client (default 1620 s), retry **solo** su `UNAVAILABLE`, **non** sul 429 |
| Docs per l'agente | `claude-api` skill / platform.claude.com `.md` | docs MCP `https://docs.x.ai/api/mcp`, `.md` su ogni pagina, `llms.txt` |

**Per l'hackathon:** Python + `openai` (Responses API) con `base_url` xAI è l'opzione con meno sorprese per Claude Code, che conosce bene l'SDK OpenAI. Si passa a `xai-sdk` solo se serve qualcosa che c'è solo lì: Collections management, `include=["inline_citations"]`, `get_tool_call_type`. Snippet in [../grok-api/sdk-quickstart.md](../grok-api/sdk-quickstart.md).

---

## 11. Rate limit, tier, errori, regioni

| | Claude | Grok |
|---|---|---|
| Limiti | RPM / ITPM / OTPM per modello; tier Evaluation → Start → Build → Scale → Custom; spend cap mensile per tier ($500 / $1k / $200k) | RPS / TPM per modello; tier T0–T4 in base alla spesa cumulativa ($0/$50/$250/$1k/$5k); voce limitata per sessioni concorrenti (T0: 10) |
| Header | `anthropic-ratelimit-*`, `retry-after` | ⚠️ non documentati nella pagina Rate Limits; i limiti si vedono in console → Models |
| Rate limit | 429 `rate_limit_error` (anche lo spend cap, senza `retry-after`) | 429 / gRPC `RESOURCE_EXHAUSTED` (xai-sdk non lo ritenta) |
| Sovraccarico | **529 `overloaded_error`** | nessun 529 documentato: 5xx / gRPC `UNAVAILABLE` (xai-sdk lo ritenta fino a 5 volte) |
| Altri | 400, 401, 402 billing, 403, 404, 413, 500 | 400 (schema), 401, 403, 404 (model id), **422** (campo malformato), WS `previous_response_not_found` |
| Policy | `stop_reason: "refusal"` (HTTP 200) + `fallbacks` server-side | contenuto bloccato; si paga comunque (fee $0.05 se bloccato prima della generazione) ⚠️ |
| Regione | `inference_geo: "global"` (default) o `"us"` (1.1×) | globale `api.x.ai` o `us.api.x.ai` (1.1×, solo 4.7 e 4.6). **Nessun EU** documentato su nessuno dei due |
| Conservazione | stateless di default; Files e Batches conservati | **`store: true` di default (30 giorni)** → impostare `store: false` |
| Status | status.claude.com | https://status.x.ai |

**Per l'hackathon:**
- Tabella completa degli errori Grok: [../grok-api/gotchas.md](../grok-api/gotchas.md).
- Un wrapper unico con backoff esponenziale su 429 e 5xx e timeout corto nel loop veloce: 5–20 s, con fallback su una risposta scriptata.
- Loggare `usage.cost_in_usd_ticks` e la latenza.

---

## Fonti

**Grok (primarie, nel repo):** [../grok-api/README.md](../grok-api/README.md), [models.md](../grok-api/models.md), [responses-and-chat.md](../grok-api/responses-and-chat.md), [tools-and-structured-output.md](../grok-api/tools-and-structured-output.md), [vision.md](../grok-api/vision.md), [agentic-server-tools.md](../grok-api/agentic-server-tools.md), [gotchas.md](../grok-api/gotchas.md), [sdk-quickstart.md](../grok-api/sdk-quickstart.md), [../voice/README.md](../voice/README.md), [../bots-imagine/grok-imagine.md](../bots-imagine/grok-imagine.md).

**Grok (verificate oggi):**
- https://docs.x.ai/llms.txt (ricerca di "computer", "batch", "citation", "tokenize", "memory")
- https://docs.x.ai/developers/advanced-api-usage/batch-api.md
- https://docs.x.ai/developers/advanced-api-usage/deferred-chat-completions.md
- https://docs.x.ai/developers/tools/citations.md
- https://docs.x.ai/developers/tools/web-search.md
- https://docs.x.ai/developers/pricing.md
- https://docs.x.ai/developers/rate-limits.md
- https://docs.x.ai/developers/rest-api-reference/inference/responses.md
- https://docs.x.ai/developers/rest-api-reference/inference/other.md (`/v1/tokenize-text`)
- https://github.com/xai-org/xai-sdk-ts (README, tool `shell`)

**Claude (verificate oggi):**
- https://platform.claude.com/docs/en/about-claude/pricing.md
- https://platform.claude.com/docs/en/api/rate-limits.md
- https://platform.claude.com/docs/en/build-with-claude/vision.md
- https://platform.claude.com/docs/en/cli-sdks-libraries/libraries/openai-sdk (OpenAI SDK compatibility)
- https://platform.claude.com/docs/en/agents-and-tools/tool-use/computer-use-tool.md

**Claude (dal reference `claude-api` del 2026-10-06, rimandi ai docs):**
- https://platform.claude.com/docs/en/build-with-claude/adaptive-thinking.md
- https://platform.claude.com/docs/en/build-with-claude/effort.md
- https://platform.claude.com/docs/en/build-with-claude/prompt-caching.md
- https://platform.claude.com/docs/en/build-with-claude/streaming.md
- https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview.md
- https://platform.claude.com/docs/en/build-with-claude/batch-processing.md
- https://platform.claude.com/docs/en/build-with-claude/files.md
- https://platform.claude.com/docs/en/build-with-claude/token-counting.md
- https://platform.claude.com/docs/en/api/errors.md

**Voce Claude:** nessuna pagina ufficiale trovata. Le uniche fonti sono secondarie: https://visionagents.ai/integrations/llm/anthropic ("Anthropic does not currently offer a realtime speech-to-speech model") e articoli sulla voice mode delle app consumer. ⚠️
