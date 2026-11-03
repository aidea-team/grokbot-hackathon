# Autenticazione, endpoint, Responses API, Chat Completions, streaming, reasoning

> **Verificato il:** 2026-11-03 su docs.x.ai e sull'OpenAPI spec (`https://docs.x.ai/openapi.json`).
> ⚠️ Gli snippet vengono dalla documentazione ufficiale, con alcuni adattamenti minimi segnalati. **Non li ho eseguiti contro l'API** perché non avevo una API key: vanno provati al primo avvio.

## Autenticazione e base URL

| Cosa | Valore |
|---|---|
| Console / API key | https://console.x.ai → API Keys (servono crediti caricati) |
| Variabile d'ambiente standard | `XAI_API_KEY` (la leggono xai-sdk, `@xai-official/sdk` e la CLI `grok`) |
| Header | `Authorization: Bearer $XAI_API_KEY` |
| Base URL inferenza (REST, compatibile OpenAI) | `https://api.x.ai/v1` |
| Host gRPC (xai-sdk Python) | `api.x.ai`, valore di default |
| US regionale | `https://us.api.x.ai/v1` (solo `grok-4.7` e `grok-4.6`, +10% di prezzo) |
| Management / Collections management | `https://management-api.x.ai` con una **Management API key** separata (`XAI_MANAGEMENT_API_KEY`) |
| WebSocket Responses | `wss://api.x.ai/v1/responses` |
| Status | https://status.x.ai |

## Endpoint principali (dall'OpenAPI)

| Metodo e path | Uso |
|---|---|
| `POST /v1/responses` | **API raccomandata**: testo, vision, tool, reasoning, stateful |
| `GET/DELETE /v1/responses/{id}` | Recuperare o cancellare una risposta salvata (conservata 30 giorni) |
| `GET /v1/responses/{id}/input_items` | Input items di una risposta salvata |
| `POST /v1/responses/compact` | Context compaction |
| `POST /v1/chat/completions` | **Legacy / deprecata** ma funzionante (formato OpenAI) |
| `GET /v1/chat/deferred-completion/{request_id}` | Deferred completions |
| `POST /v1/messages` | Compatibilità Anthropic: **"fully deprecated"** |
| `POST /v1/completions`, `POST /v1/complete` | Legacy, non supportati dai modelli reasoning |
| `GET /v1/models`, `/v1/language-models` | Elenco dei modelli disponibili per il team |
| `POST /v1/files`, `GET /v1/files/{id}`… | Files API |
| `POST /v1/tokenize-text` | Tokenizzazione |
| `GET /v1/api-key` | Info sulla key in uso (utile per debug) |

### Compatibilità con gli SDK
- **OpenAI SDK (Python/JS): sì.** Basta cambiare `base_url`/`baseURL` in `https://api.x.ai/v1` e usare `XAI_API_KEY`. Funzionano sia `client.responses.*` (raccomandato) sia `client.chat.completions.*` (legacy).
- **Anthropic SDK: sconsigliato.** L'endpoint `POST /v1/messages` esiste ancora, ma la reference dice testualmente *"The Anthropic SDK compatibility is fully deprecated. Please migrate to the Responses API or the gRPC API."* ⚠️ Non c'è una data di spegnimento: **non va usato** in hackathon.
- **Vercel AI SDK:** `@ai-sdk/xai`, con `xai.responses('grok-4.7')` per la Responses API e `xai('grok-4.7')` per Chat Completions.
- **xai-sdk Python (gRPC)** e **`@xai-official/sdk` (TS, sperimentale):** vedi [sdk-quickstart.md](sdk-quickstart.md).

## Responses API vs Chat Completions

La documentazione è netta: *"Use the Responses API. Chat Completions is deprecated."* Chat Completions non ha un campo per il reasoning cifrato, quindi nei multi-turn e nei tool loop il modello perde il ragionamento fatto nei turni precedenti. Inoltre i tool server-side (search, code, MCP) sono disponibili **solo** sulla Responses API.

| Chat Completions | Responses API |
|---|---|
| `messages` | `input` (stringa oppure array di item) |
| `max_tokens` | `max_output_tokens` (default 128.000, conta solo l'output visibile) |
| system message | `{"role":"system",...}` dentro `input`, oppure `instructions` (non usabile insieme a `previous_response_id`) |
| `choices[0].message.content` | `response.output_text` (helper dell'SDK OpenAI) oppure `output[]` con item di tipo `message` → `content[]` di tipo `output_text` |
| stateless | `store` (default **true**, conservazione 30 giorni) + `previous_response_id` |
| header `x-grok-conv-id` per la cache | `prompt_cache_key` |

### Parametri utili di `POST /v1/responses` (dalla reference)
`model`, `input`, `instructions`, `stream`, `store`, `previous_response_id`, `include` (es. `["reasoning.encrypted_content"]`), `reasoning: {effort}` oppure `reasoning_effort` (non standard), `tools`, `tool_choice`, `parallel_tool_calls`, `max_turns` (turni agentici dei tool server-side), `max_output_tokens`, `temperature` (0–2, campionato al massimo a 1), `top_p`, `top_k`, `min_p`, `text: {format: ...}` (structured output), `prompt_cache_key`, `service_tier` (`default` | `priority` | `fast`), `safety_identifier`, `guidelines` (moderazione custom).

Non supportati o solo per compatibilità: `background`, `metadata`, `truncation`. `logprobs` e `top_logprobs` vengono ignorati senza errore dai modelli ≥ grok-4.20.

## Snippet minimi

### curl (Responses)
```bash
curl https://api.x.ai/v1/responses \
  -H "Authorization: Bearer $XAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "grok-4.7",
    "input": "Fix this function and explain the bug: function median(a){a.sort();return a[a.length/2]}"
  }'
```

### Python, OpenAI SDK
```python
import os
import httpx
from openai import OpenAI

client = OpenAI(
    api_key=os.getenv("XAI_API_KEY"),
    base_url="https://api.x.ai/v1",
    timeout=httpx.Timeout(3600.0),  # i modelli reasoning possono essere lenti
)

response = client.responses.create(
    model="grok-4.7",
    input=[
        {"role": "system", "content": "You are Grok, an AI agent built to answer helpful questions."},
        {"role": "user", "content": "How big is the universe?"},
    ],
)
print(response.output_text)
print(response.id)  # da usare per continuare la conversazione
```

### TypeScript/JS, OpenAI SDK
```javascript
import OpenAI from "openai";

const client = new OpenAI({
  apiKey: process.env.XAI_API_KEY,
  baseURL: "https://api.x.ai/v1",
  timeout: 360000,
});

const response = await client.responses.create({
  model: "grok-4.7",
  input: [{ role: "user", content: "How big is the universe?" }],
});
console.log(response.output_text);
```

### Python, xai-sdk (gRPC)
```python
import os
from xai_sdk import Client
from xai_sdk.chat import user, system

client = Client(api_key=os.getenv("XAI_API_KEY"), timeout=3600)
chat = client.chat.create(model="grok-4.7")
chat.append(system("You are Grok, an AI agent built to answer helpful questions."))
chat.append(user("How big is the universe?"))
response = chat.sample()
print(response.content)
```

## Multi-turn

**Opzione A, stateful lato server:**
```python
second = client.responses.create(
    model="grok-4.7",
    previous_response_id=response.id,
    input=[{"role": "user", "content": "How do stars form?"}],
)
```

**Opzione B, history gestita da noi** (`store=False`, consigliata con immagini e per avere il controllo):
```python
second = client.responses.create(
    model="grok-4.7",
    input=[
        *response.output,  # passa TUTTI gli output item, inclusi i reasoning item cifrati
        {"role": "user", "content": "How do stars form?"},
    ],
    store=False,
    include=["reasoning.encrypted_content"],
)
```
- `grok-4.7` restituisce **sempre** `reasoning.encrypted_content` sulla Responses API, anche se `include` non lo chiede. Gli item vanno ripassati **invariati**: senza riordinarli, filtrarli o convertirli in messaggi Chat Completions. Altrimenti si perde il ragionamento e si rompe la prompt cache.
- xai-sdk: `chat.append(response)` aggiunge automaticamente gli output alla history. Con `store_messages=True` si salva lato server, `use_encrypted_content=True` restituisce il reasoning cifrato.

## Streaming

Si attiva con `stream: true` (SSE). Raccomandato sempre con i modelli reasoning e con i tool agentici.

**Python, OpenAI SDK, Responses:**
```python
stream = client.responses.create(model="grok-4.7", input="Explain PID control in 3 lines.", stream=True)
for event in stream:
    if event.type == "response.output_text.delta":
        print(event.delta, end="", flush=True)
    elif event.type in ("response.reasoning_text.delta", "response.reasoning_summary_text.delta"):
        pass  # riassunto del reasoning (grok-4.7)
    elif event.type in ("response.completed", "response.incomplete"):
        final = event.response
```

**JS, OpenAI SDK, Responses:**
```javascript
const stream = await client.responses.create({ model: "grok-4.7", input: "Hello", stream: true });
for await (const event of stream) {
  if (event.type === "response.output_text.delta") process.stdout.write(event.delta);
}
```

**xai-sdk:**
```python
for response, chunk in chat.stream():
    print(chunk.content, end="", flush=True)
# `response` accumula la risposta completa
```

**Chat Completions (legacy):** `client.chat.completions.create(..., stream=True)` e poi `chunk.choices[0].delta.content`. I chunk possono contenere anche `delta.reasoning_content`.

⚠️ Con lo streaming, le **function call arrivano intere in un solo chunk**: non vengono streamate a pezzi.

## Reasoning

| Model | `reasoning.effort` | Default | Disattivabile? |
|---|---|---|---|
| `grok-4.7`, `grok-4.6` | `low` / `medium` / `high` / `xhigh` | `high` | **No** |
| `grok-4.5` | `low` / `medium` / `high` (`xhigh` → `high`) | `high` | No |
| `grok-4.3` | `none` / `low` / `medium` / `high` / `xhigh` | `low` | **Sì (`none`)** |
| `grok-4.20-0309-non-reasoning` | — | — | non ragiona |
| `grok-4.20-multi-agent` | `low`/`medium` = 4 agenti, `high`/`xhigh` = 16 agenti | — | — |

```python
# OpenAI SDK, Responses
client.responses.create(model="grok-4.7", reasoning={"effort": "low"}, input="...")
# xai-sdk
client.chat.create(model="grok-4.7", reasoning_effort="low")
# Vercel AI SDK
generateText({ model: xai.responses('grok-4.7'), providerOptions: { xai: { reasoningEffort: 'low' } }, prompt: '...' })
```
- Con i modelli reasoning, `presencePenalty`, `frequencyPenalty` e `stop` **restituiscono un errore**.
- I reasoning token si pagano come output e contano nel TPM.
- La best practice ufficiale è impostare l'effort esplicitamente su ogni richiesta. Per i campionamenti si raccomandano `temperature=0.7` e `top_p=0.95`, scostandosi poco da questi valori.

## Altri parametri avanzati
- **Priority processing:** `service_tier: "priority"` riduce TTFT e latenza inter-token quando c'è carico. Costa **2x** e si paga solo se la risposta conferma `"service_tier": "priority"`. ⚠️ La reference accetta anche `"fast"` (*"Fast and Priority are interchangeable: the model's fast deployment and its rates where configured, else higher scheduling priority"*). Per `grok-4.7` la variante Fast **non** è sull'API pubblica, quindi `"fast"` dovrebbe equivalere a priority, ma non l'ho verificato.
- **Prompt caching:** è automatica. Conviene impostare `prompt_cache_key` (Responses) oppure l'header `x-grok-conv-id` (Chat Completions, xai-sdk via `metadata=(("x-grok-conv-id", id),)`) per instradare la conversazione sempre sullo stesso server. Il valore di `usage.input_tokens_details.cached_tokens` dovrebbe crescere a ogni turno.
- **WebSocket mode:** `wss://api.x.ai/v1/responses`, con messaggi `{"type":"response.create", ...}`, fino a circa -20% di latenza end-to-end nei loop con tanti tool. Una connessione elabora un turno alla volta e dura al massimo 59 minuti. C'è anche il warmup con `generate: false`.
- **Context compaction:** `POST /v1/responses/compact` (SDK OpenAI: `client.responses.compact(...)`) per conversazioni lunghe.
- **Cost tracking:** ogni risposta ha `usage.cost_in_usd_ticks` (nella reference compare anche `cost_in_nano_usd`).
- **Deferred / Batch:** per job asincroni. Batch -20% sui modelli 4.x, ma non serve per il real-time.

## Fonti
- https://docs.x.ai/developers/quickstart.md
- https://docs.x.ai/developers/model-capabilities/text/generate-text.md
- https://docs.x.ai/developers/model-capabilities/text/comparison.md
- https://docs.x.ai/developers/model-capabilities/legacy/chat-completions.md
- https://docs.x.ai/developers/model-capabilities/text/streaming.md
- https://docs.x.ai/developers/model-capabilities/text/reasoning.md
- https://docs.x.ai/developers/model-capabilities/text/best-practices.md
- https://docs.x.ai/developers/rest-api-reference/inference.md
- https://docs.x.ai/developers/rest-api-reference/inference/responses.md
- https://docs.x.ai/developers/rest-api-reference/inference/chat-completions.md
- https://docs.x.ai/developers/rest-api-reference/inference/legacy.md (Anthropic `/v1/messages` deprecato)
- https://docs.x.ai/developers/advanced-api-usage/priority-processing.md
- https://docs.x.ai/developers/advanced-api-usage/websocket-mode.md
- https://docs.x.ai/developers/advanced-api-usage/prompt-caching/maximizing-cache-hits.md
- https://docs.x.ai/developers/advanced-api-usage/context-compaction.md
- https://docs.x.ai/openapi.json
